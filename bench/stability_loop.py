"""stability_loop — 1-hour S1+S5 stability soak driver (MEAS-07).

Plan 03-04 implements the rubric's "60min S1+S5 loop" stability dimension.
This module is the harness: spawn an MCP, drive it through Stage-1
(Greenhouse markdown extraction) + Stage-5 (Ashby form fill) against the
loopback snapshot fixture server, log per-iteration timing + RSS, enforce
a per-tool-call 30s timeout, and after the configured duration tear down
the MCP and verify via :mod:`bench.orphan_audit` that no MCP processes
survived.

The MCP is driven directly via ``mcp.client.stdio`` + ``ClientSession`` —
the same pattern :mod:`bench.tools_inventory` and
:mod:`bench.measure_cold_start` use. We do NOT spawn a Claude Code session
per iteration (that would inflate wall-clock by ~100×); the
TOOL_RECIPES table hardcodes the tool names + arguments derived from each
MCP's ``tools_inventory.json`` snapshot (already on disk for all 7 MCPs
after Phase 3 plan 03-01 task 2).

Per-iteration log line format (in ``stability.log``)::

    <iso-utc> iteration=N s1=<status> s5=<status> s1_ms=N s5_ms=N|null rss_kb=N notes="<...>"

``stability_metadata.json`` carries the rolled-up summary used by Phase 4
synthesis (see the ``StabilityResult`` dataclass for the full shape).

Special-case handling (per 03-CONTEXT.md ``decisions`` block):

  * **lightpanda** — read-only MCP; S5 (form fill) is N/A. ``mode='read-only'``
    skips S5 each iteration and marks ``s5=N/A_READONLY``.
  * **cloakbrowser** — loopback-only contract per SAFETY-04. The
    ``fixture_base_url`` is run through :func:`assert_local_only` BEFORE
    the loop starts. Non-loopback URLs raise immediately.
  * **firecrawl** / **browser-use-agent** — ``mode='skip'`` writes the
    ``stability_metadata.json`` SKIPPED record without spawning anything.
    Used because firecrawl is cloud (can't reach loopback) and
    browser-use-agent is gated on ``LLM_KEY_ABSENT`` since Phase 2.

CLI
---
    python -m bench.stability_loop <MCP_NAME> \\
        --duration-minutes 60 \\
        --sleep-s 30 \\
        --fixture-base-url http://127.0.0.1:8765 \\
        --out-dir results/2026-05-26/<mcp> \\
        --mode {full,read-only,skip} \\
        [--skip-reason CLOUD_NO_LOOPBACK] \\
        [--wallclock-decision selective_top3_60min_rest_30min]
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import re
import shlex
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from bench.cloakbrowser_guard import assert_local_only, HostnameNotAllowedError
from bench.tools_inventory import DEFAULT_MCP_JSON, load_mcp_spec, McpSpec
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


# ─── Constants ──────────────────────────────────────────────────────────


# Per-tool-call timeout (rubric requirement).
PER_TOOL_TIMEOUT_S = 30.0

# After 5 consecutive iteration-level crashes, give up and report
# completion_status=CRASHED with the partial log.
MAX_CONSECUTIVE_CRASHES = 5


# ─── TOOL_RECIPES table ─────────────────────────────────────────────────
#
# Each MCP gets two stage recipes: s1 (Greenhouse markdown extract) and
# s5 (Ashby form fill). A recipe is a list of (tool_name, arguments_dict)
# tuples; the URL is injected via str.format(GH_URL=...) or str.format(
# ASHBY_URL=...). Read-only MCPs (lightpanda) only need s1.
#
# Tool names come from each MCP's tools_inventory.json captured during
# Phase 2 and verified in Phase 3 plan 03-01 task 2. They must match
# verbatim.
#
# For MCPs that need stateful page_ids across calls inside one iteration
# (cloakbrowser), the runtime threads the previous call's result into
# subsequent calls via the special placeholder ``{page_id}`` — see
# ``_call_stage``. The state dict resets between iterations.

# Pinned fixture sample URLs. The fixture server (scripts/serve_fixtures.sh)
# serves out of fixtures/snapshots/, so paths are relative to that root.
GH_PATH = "/greenhouse_2026-05-22/anthropic/jobs/5023394008.html"
ASHBY_PATH = "/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html"


# Form-fill payload for S5 (six fields, matches Phase 2 stage_walk.md).
ASHBY_FORM_FIELDS: list[dict[str, str]] = [
    {"name": "first_name", "value": "Test"},
    {"name": "last_name", "value": "Applicant"},
    {"name": "email", "value": "test@example.com"},
    {"name": "phone", "value": "+15555550100"},
    {"name": "linkedin", "value": "https://linkedin.com/in/test"},
    {"name": "website", "value": "https://example.com"},
]


TOOL_RECIPES: dict[str, dict[str, list[tuple[str, dict]]]] = {
    "playwright": {
        "s1": [
            ("browser_navigate", {"url": "{GH_URL}"}),
            ("browser_snapshot", {}),
        ],
        "s5": [
            ("browser_navigate", {"url": "{ASHBY_URL}"}),
            ("browser_fill_form", {
                "fields": [
                    # Playwright's fill_form takes a list of {name, type, ref, value}.
                    # We use minimal ref'd identifiers; the snapshot fixture has stable
                    # placeholder field names — Playwright will best-effort match.
                    {"name": f["name"], "type": "textbox", "ref": f["name"], "value": f["value"]}
                    for f in ASHBY_FORM_FIELDS
                ]
            }),
        ],
    },
    "chrome-devtools": {
        "s1": [
            ("navigate_page", {"url": "{GH_URL}"}),
            ("take_snapshot", {}),
        ],
        "s5": [
            ("navigate_page", {"url": "{ASHBY_URL}"}),
            ("fill_form", {
                "elements": [
                    {"uid": f["name"], "value": f["value"]}
                    for f in ASHBY_FORM_FIELDS
                ]
            }),
        ],
    },
    "lightpanda": {
        # Read-only — S1 only. The mode='read-only' path bypasses any S5
        # recipe; we omit the key so the dispatcher fails loud if someone
        # tries to run lightpanda in mode='full'.
        "s1": [
            ("navigate", {"url": "{GH_URL}"}),
            ("markdown", {}),
        ],
    },
    "cloakbrowser": {
        # Stateful: cloak_launch returns a page_id that subsequent calls
        # need. The runtime extracts the id and injects it via {page_id}.
        "s1": [
            ("cloak_launch", {}),
            ("cloak_navigate", {"page_id": "{page_id}", "url": "{GH_URL}"}),
            ("cloak_read_page", {"page_id": "{page_id}"}),
            ("cloak_close_page", {"page_id": "{page_id}"}),
        ],
        "s5": [
            ("cloak_launch", {}),
            ("cloak_navigate", {"page_id": "{page_id}", "url": "{ASHBY_URL}"}),
        ] + [
            ("cloak_type", {"page_id": "{page_id}", "selector": f"[name={f['name']!r}]", "text": f["value"]})
            for f in ASHBY_FORM_FIELDS
        ] + [
            ("cloak_close_page", {"page_id": "{page_id}"}),
        ],
    },
    "obscura": {
        "s1": [
            ("browse_page", {"url": "{GH_URL}"}),
        ],
        "s5": [
            ("browse_interact", {
                "url": "{ASHBY_URL}",
                "actions": [{"type": "fill", "selector": f"[name='{f['name']}']", "value": f["value"]}
                            for f in ASHBY_FORM_FIELDS],
            }),
        ],
    },
    "browser-use-direct": {
        "s1": [
            ("browser_navigate", {"url": "{GH_URL}"}),
            ("browser_extract_content", {"query": "main content"}),
        ],
        "s5": [
            ("browser_navigate", {"url": "{ASHBY_URL}"}),
        ] + [
            ("browser_type", {"text": f["value"], "index": idx})
            for idx, f in enumerate(ASHBY_FORM_FIELDS)
        ],
    },
}


# ─── Data classes ───────────────────────────────────────────────────────


@dataclass
class LogLine:
    """One row of stability.log.

    s5_ms is None when the iteration was read-only (lightpanda).
    Notes carries any short status remark (exception class name, etc.).
    """
    timestamp: str
    iteration_n: int
    s1_status: str
    s5_status: str
    s1_ms: Optional[int]
    s5_ms: Optional[int]
    rss_kb: int
    notes: str = ""


@dataclass
class StabilityResult:
    """Rolled-up summary written to stability_metadata.json."""
    mcp: str
    captured_at: str
    configured_duration_minutes: float
    actual_duration_minutes: float
    completion_status: str  # COMPLETED | COMPLETED_WITH_ORPHANS | TIMED_OUT | CRASHED | SKIPPED
    skip_reason: Optional[str]
    iterations_completed: int
    iterations_failed: dict[str, int]
    rss_first_kb: int
    rss_max_kb: int
    rss_growth_kb: int
    orphan_audit_survivors: int
    wallclock_decision: str
    loopback_only_verified: bool
    fixture_base_url: str
    notes: list[str] = field(default_factory=list)


# ─── Log-line format / parse ────────────────────────────────────────────


_LOG_LINE_RE = re.compile(
    r"^(?P<ts>\S+)\s+"
    r"iteration=(?P<iter>\d+)\s+"
    r"s1=(?P<s1>\S+)\s+"
    r"s5=(?P<s5>\S+)\s+"
    r"s1_ms=(?P<s1ms>\S+)\s+"
    r"s5_ms=(?P<s5ms>\S+)\s+"
    r"rss_kb=(?P<rss>\d+)"
    r"(?:\s+notes=\"(?P<notes>[^\"]*)\")?"
    r"\s*$"
)


def format_log_line(line: LogLine) -> str:
    """Render a LogLine into the canonical stability.log row.

    Null-able ints (s1_ms/s5_ms) render as the literal ``null`` when None,
    matching the JSON convention so a downstream parser doesn't have to
    handle "" or "-".
    """
    s1_ms = "null" if line.s1_ms is None else str(int(line.s1_ms))
    s5_ms = "null" if line.s5_ms is None else str(int(line.s5_ms))
    notes = line.notes.replace("\"", "'")
    return (
        f"{line.timestamp} iteration={line.iteration_n} "
        f"s1={line.s1_status} s5={line.s5_status} "
        f"s1_ms={s1_ms} s5_ms={s5_ms} rss_kb={line.rss_kb} "
        f"notes=\"{notes}\""
    )


def parse_log_line(text: str) -> LogLine:
    """Inverse of :func:`format_log_line`.

    Used by Test 2 round-trip and by Phase 4 synthesis when re-reading
    stability.log for the matrix.
    """
    m = _LOG_LINE_RE.match(text.strip())
    if not m:
        raise ValueError(f"stability_loop: cannot parse log line: {text!r}")

    def _int_or_none(s: str) -> Optional[int]:
        return None if s == "null" else int(s)

    return LogLine(
        timestamp=m["ts"],
        iteration_n=int(m["iter"]),
        s1_status=m["s1"],
        s5_status=m["s5"],
        s1_ms=_int_or_none(m["s1ms"]),
        s5_ms=_int_or_none(m["s5ms"]),
        rss_kb=int(m["rss"]),
        notes=m["notes"] or "",
    )


# ─── Real-MCP plumbing (test seams) ─────────────────────────────────────
#
# These four functions are the test seams the unit tests patch out. They
# encapsulate the side effects (spawning processes, calling ps, snapshot
# diffs) so the loop can be exercised against a synthetic clock.


def _spawn_mcp(mcp: str, out_dir: Path) -> tuple[Any, int]:
    """Spawn the MCP via stdio_client and return (session_context, pid).

    This is a unit-test seam. The production path (:func:`run_real`) bypasses
    it and constructs the stdio_client context itself so the async-with
    lifetime is correct. The synthetic test path just expects a (handle, pid)
    tuple — tests monkey-patch this to return ``(None, fake_pid)``.

    In the (theoretical) case where the test path doesn't patch it, we
    return ``(None, 0)`` so the loop runs RSS sampling against a non-existent
    PID (which simply returns 0). The real loop goes through ``run_real``.
    """
    return (None, 0)


def _teardown_mcp(handle: Any) -> None:
    """Tear down the MCP spawned by :func:`_spawn_mcp`.

    In production the stdio_client context handles teardown; this seam
    exists for tests to assert teardown was called.
    """
    return None


def _snapshot_before(path: Path) -> None:
    """Take a ps snapshot before the stability run."""
    subprocess.run(
        [sys.executable, "-m", "bench.orphan_audit", "--snapshot-only", str(path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _diff_after(before_path: Path, after_path: Path, log_path: Path) -> int:
    """Take the after snapshot + diff. Return survivor count."""
    subprocess.run(
        [sys.executable, "-m", "bench.orphan_audit", "--snapshot-only", str(after_path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    result = subprocess.run(
        [sys.executable, "-m", "bench.orphan_audit",
         "--before-snapshot", str(before_path),
         "--after-snapshot", str(after_path),
         "--log", str(log_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    # orphan_audit exit code: 0 if 0 survivors, 1 otherwise. The number of
    # survivors is in the log file under ORPHANS=<n>; parse it back.
    try:
        log_text = log_path.read_text(encoding="utf-8")
        m = re.search(r"^ORPHANS=(\d+)", log_text, re.MULTILINE)
        if m:
            return int(m.group(1))
    except OSError:
        pass
    return 0 if result.returncode == 0 else 1


def _sample_rss_kb(pid: int) -> int:
    """Return the RSS (in KB) of `pid` via ``ps -o rss=``.

    Returns 0 if the process is gone or ps fails — the loop treats that
    as "no growth signal this iteration" rather than crashing.
    """
    if pid <= 0:
        return 0
    try:
        out = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return int(out) if out else 0
    except (ValueError, FileNotFoundError):
        return 0


async def _call_stage(
    stage: str,
    recipe: list[tuple[str, dict]],
    base_url: str,
    session: Optional[ClientSession] = None,
) -> tuple[str, int, Optional[str]]:
    """Execute one stage's recipe against an open ClientSession.

    Returns (status, elapsed_ms, error_str_or_None).

    status is one of PASS, FAIL, TIMEOUT, CRASH. The per-call timeout is
    PER_TOOL_TIMEOUT_S; on ``asyncio.TimeoutError`` we return TIMEOUT and
    record elapsed_ms = int(PER_TOOL_TIMEOUT_S * 1000).
    """
    if session is None:
        # Test path: the test patches out _call_stage entirely, so this
        # production-only branch is only ever hit in production.
        raise RuntimeError(
            "stability_loop._call_stage called without an active session "
            "— tests should monkey-patch this function entirely"
        )

    gh_url = f"{base_url}{GH_PATH}"
    ashby_url = f"{base_url}{ASHBY_PATH}"

    # Stateful placeholder for cloakbrowser's page_id.
    state: dict[str, Any] = {"page_id": None}

    t_start = time.perf_counter()
    try:
        for tool_name, raw_args in recipe:
            # Render URL + page_id placeholders.
            args = _render_args(raw_args, gh_url=gh_url, ashby_url=ashby_url, state=state)

            async def _one_call():
                return await session.call_tool(tool_name, args)

            try:
                result = await asyncio.wait_for(_one_call(), timeout=PER_TOOL_TIMEOUT_S)
            except asyncio.TimeoutError:
                elapsed_ms = int((time.perf_counter() - t_start) * 1000)
                return ("TIMEOUT", elapsed_ms, f"timeout on {tool_name}")

            # Update state from result (e.g. extract page_id for cloakbrowser).
            _maybe_update_state(state, tool_name, result)

        elapsed_ms = int((time.perf_counter() - t_start) * 1000)
        return ("PASS", elapsed_ms, None)
    except Exception as exc:  # noqa: BLE001 — surface every failure mode
        elapsed_ms = int((time.perf_counter() - t_start) * 1000)
        return ("FAIL", elapsed_ms, f"{type(exc).__name__}: {exc}")


def _render_args(
    raw_args: dict[str, Any],
    *,
    gh_url: str,
    ashby_url: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Substitute URL + page_id placeholders into a recipe's argument dict."""
    out: dict[str, Any] = {}
    for k, v in raw_args.items():
        if isinstance(v, str):
            try:
                out[k] = v.format(GH_URL=gh_url, ASHBY_URL=ashby_url, page_id=state.get("page_id") or "")
            except (KeyError, IndexError):
                out[k] = v
        else:
            out[k] = v
    return out


def _maybe_update_state(state: dict[str, Any], tool_name: str, result: Any) -> None:
    """Extract page_id from cloak_launch results (cloakbrowser stateful flow)."""
    if tool_name != "cloak_launch":
        return
    # MCP CallToolResult shape varies — try common shapes.
    try:
        # 1.16 SDK: result.content is a list of TextContent; the launch
        # response typically returns a JSON blob with {"page_id": "..."}.
        for piece in getattr(result, "content", []):
            text = getattr(piece, "text", None)
            if not text:
                continue
            try:
                obj = json.loads(text)
                if isinstance(obj, dict) and "page_id" in obj:
                    state["page_id"] = obj["page_id"]
                    return
            except (ValueError, TypeError):
                continue
    except Exception:  # noqa: BLE001
        return


# ─── Core async loop ────────────────────────────────────────────────────


async def run_stability_loop(
    *,
    mcp: str,
    duration_minutes: float,
    sleep_s: float,
    fixture_base_url: str,
    out_dir: Path,
    mode: str = "full",
    wallclock_decision: str = "selective_top3_60min_rest_30min",
) -> StabilityResult:
    """Drive an MCP through S1+S5 (or S1 only, for read-only) for ``duration_minutes``.

    Test seams: ``_call_stage``, ``_sample_rss_kb``, ``_spawn_mcp``,
    ``_teardown_mcp``, ``_snapshot_before``, ``_diff_after``.

    Returns a :class:`StabilityResult` and writes both ``stability.log``
    (per-iteration rows) and ``stability_metadata.json`` (the rolled-up
    summary) under ``out_dir``.

    Cloakbrowser short-circuit: if mcp=='cloakbrowser', validate the
    fixture base URL via :func:`assert_local_only` BEFORE entering the
    loop. Non-loopback raises :class:`HostnameNotAllowedError` and
    nothing is written.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Loopback enforcement for cloakbrowser (Test 5) ─────────────────
    loopback_only_verified = False
    if mcp == "cloakbrowser":
        # Raises HostnameNotAllowedError if not loopback. The caller's
        # test asserts no stability.log is written.
        assert_local_only(fixture_base_url)
        loopback_only_verified = True

    log_path = out_dir / "stability.log"
    metadata_path = out_dir / "stability_metadata.json"
    orphan_log_path = out_dir / "stability_orphan_audit.log"
    snap_before = out_dir / ".stability_ps_before.tsv"
    snap_after = out_dir / ".stability_ps_after.tsv"

    captured_at = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    # ── Pre-run ps snapshot (orphan audit baseline). ───────────────────
    _snapshot_before(snap_before)

    # ── Spawn the MCP. ──────────────────────────────────────────────────
    # Synchronous seam — production path goes through run_real (which
    # builds the stdio_client context itself); this function is only used
    # by the unit-tested code path.
    handle, pid = _spawn_mcp(mcp, out_dir)

    # Use mocked session in tests; in production this loop is invoked
    # via _run_real with an open session.
    return await _drive_loop(
        mcp=mcp,
        duration_minutes=duration_minutes,
        sleep_s=sleep_s,
        fixture_base_url=fixture_base_url,
        out_dir=out_dir,
        mode=mode,
        wallclock_decision=wallclock_decision,
        session=None,
        pid=pid,
        handle=handle,
        captured_at=captured_at,
        loopback_only_verified=loopback_only_verified,
        log_path=log_path,
        metadata_path=metadata_path,
        orphan_log_path=orphan_log_path,
        snap_before=snap_before,
        snap_after=snap_after,
    )


async def _drive_loop(
    *,
    mcp: str,
    duration_minutes: float,
    sleep_s: float,
    fixture_base_url: str,
    out_dir: Path,
    mode: str,
    wallclock_decision: str,
    session: Optional[ClientSession],
    pid: int,
    handle: Any,
    captured_at: str,
    loopback_only_verified: bool,
    log_path: Path,
    metadata_path: Path,
    orphan_log_path: Path,
    snap_before: Path,
    snap_after: Path,
) -> StabilityResult:
    """The actual loop. Split out so tests can patch the seams cleanly."""

    iterations_completed = 0
    iterations_failed = {"s1": 0, "s5": 0, "s5_skipped_readonly": 0}
    rss_first_kb = 0
    rss_max_kb = 0
    consecutive_crashes = 0
    notes: list[str] = []
    completion_status = "COMPLETED"

    recipe_block = TOOL_RECIPES.get(mcp, {})
    s1_recipe = recipe_block.get("s1", [])
    s5_recipe = recipe_block.get("s5", [])

    duration_s = duration_minutes * 60.0
    t0 = time.perf_counter()
    log_lines: list[str] = []

    try:
        with log_path.open("w", encoding="utf-8") as log_fh:
            while True:
                elapsed = time.perf_counter() - t0
                if elapsed >= duration_s:
                    break

                ts = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                # ── S1 (always) ────────────────────────────────────────
                try:
                    s1_status, s1_ms, s1_err = await _call_stage(
                        "s1", s1_recipe, fixture_base_url, session=session
                    )
                except asyncio.TimeoutError:
                    s1_status = "TIMEOUT"
                    s1_ms = int(PER_TOOL_TIMEOUT_S * 1000)
                    s1_err = "asyncio.TimeoutError"
                if s1_status in ("FAIL", "TIMEOUT", "CRASH"):
                    iterations_failed["s1"] += 1

                # ── S5 (mode-dependent) ────────────────────────────────
                if mode == "read-only":
                    s5_status = "N/A_READONLY"
                    s5_ms: Optional[int] = None
                    s5_err: Optional[str] = None
                    iterations_failed["s5_skipped_readonly"] += 1
                else:
                    try:
                        s5_status, s5_int, s5_err = await _call_stage(
                            "s5", s5_recipe, fixture_base_url, session=session
                        )
                        s5_ms = s5_int
                    except asyncio.TimeoutError:
                        s5_status = "TIMEOUT"
                        s5_ms = int(PER_TOOL_TIMEOUT_S * 1000)
                        s5_err = "asyncio.TimeoutError"
                    if s5_status in ("FAIL", "TIMEOUT", "CRASH"):
                        iterations_failed["s5"] += 1

                rss_kb = _sample_rss_kb(pid)
                if iterations_completed == 0:
                    rss_first_kb = rss_kb
                if rss_kb > rss_max_kb:
                    rss_max_kb = rss_kb

                notes_field = ""
                if s1_err:
                    notes_field = (s1_err[:80])
                elif s5_err:
                    notes_field = (s5_err[:80])

                line = LogLine(
                    timestamp=ts,
                    iteration_n=iterations_completed,
                    s1_status=s1_status,
                    s5_status=s5_status,
                    s1_ms=s1_ms,
                    s5_ms=s5_ms,
                    rss_kb=rss_kb,
                    notes=notes_field,
                )
                log_fh.write(format_log_line(line) + "\n")
                log_fh.flush()
                log_lines.append(format_log_line(line))

                # Crash-burst tracker: 5 consecutive CRASH iterations -> bail.
                if s1_status == "CRASH" or s5_status == "CRASH":
                    consecutive_crashes += 1
                    if consecutive_crashes >= MAX_CONSECUTIVE_CRASHES:
                        completion_status = "CRASHED"
                        notes.append(
                            f"hit {MAX_CONSECUTIVE_CRASHES} consecutive CRASH iterations; "
                            f"breaking out early at iter={iterations_completed}"
                        )
                        iterations_completed += 1
                        break
                else:
                    consecutive_crashes = 0

                iterations_completed += 1

                # Sleep between iterations. The synthetic clock used by
                # tests overrides asyncio.sleep so this fast-forwards.
                await asyncio.sleep(sleep_s)
    except Exception as exc:  # noqa: BLE001
        completion_status = "CRASHED"
        notes.append(f"loop exception: {type(exc).__name__}: {exc}")
        notes.append(traceback.format_exc()[:200])

    actual_duration_minutes = (time.perf_counter() - t0) / 60.0

    # ── Teardown the MCP. ────────────────────────────────────────────────
    try:
        _teardown_mcp(handle)
    except Exception:  # noqa: BLE001
        pass

    # ── Post-run orphan audit. ──────────────────────────────────────────
    orphan_survivors = _diff_after(snap_before, snap_after, orphan_log_path)
    if orphan_survivors > 0 and completion_status == "COMPLETED":
        completion_status = "COMPLETED_WITH_ORPHANS"

    rss_growth_kb = max(0, rss_max_kb - rss_first_kb)

    result = StabilityResult(
        mcp=mcp,
        captured_at=captured_at,
        configured_duration_minutes=duration_minutes,
        actual_duration_minutes=round(actual_duration_minutes, 2),
        completion_status=completion_status,
        skip_reason=None,
        iterations_completed=iterations_completed,
        iterations_failed=iterations_failed,
        rss_first_kb=rss_first_kb,
        rss_max_kb=rss_max_kb,
        rss_growth_kb=rss_growth_kb,
        orphan_audit_survivors=orphan_survivors,
        wallclock_decision=wallclock_decision,
        loopback_only_verified=loopback_only_verified,
        fixture_base_url=fixture_base_url,
        notes=notes,
    )

    _write_metadata(metadata_path, result)
    return result


def _write_metadata(path: Path, result: StabilityResult) -> None:
    """Serialise a StabilityResult to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mcp": result.mcp,
        "captured_at": result.captured_at,
        "configured_duration_minutes": result.configured_duration_minutes,
        "actual_duration_minutes": result.actual_duration_minutes,
        "completion_status": result.completion_status,
        "skip_reason": result.skip_reason,
        "iterations_completed": result.iterations_completed,
        "iterations_failed": result.iterations_failed,
        "rss_first_kb": result.rss_first_kb,
        "rss_max_kb": result.rss_max_kb,
        "rss_growth_kb": result.rss_growth_kb,
        "orphan_audit_survivors": result.orphan_audit_survivors,
        "wallclock_decision": result.wallclock_decision,
        "loopback_only_verified": result.loopback_only_verified,
        "fixture_base_url": result.fixture_base_url,
        "notes": result.notes,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ─── Skip-mode driver (firecrawl + browser-use-agent) ───────────────────


def run_skip(
    *,
    mcp: str,
    out_dir: Path,
    skip_reason: str,
    duration_minutes: float = 0.0,
    wallclock_decision: str = "selective_top3_60min_rest_30min",
    fixture_base_url: str = "http://127.0.0.1:8765",
) -> StabilityResult:
    """Write a SKIPPED stability_metadata.json without running the loop.

    Used for firecrawl (cloud, can't reach loopback) and browser-use-agent
    (LLM_KEY_ABSENT since Phase 2). Also writes a one-line stability.log
    marker so SUMMARY scanners find content at the canonical path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    captured_at = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    result = StabilityResult(
        mcp=mcp,
        captured_at=captured_at,
        configured_duration_minutes=duration_minutes,
        actual_duration_minutes=0.0,
        completion_status="SKIPPED",
        skip_reason=skip_reason,
        iterations_completed=0,
        iterations_failed={"s1": 0, "s5": 0, "s5_skipped_readonly": 0},
        rss_first_kb=0,
        rss_max_kb=0,
        rss_growth_kb=0,
        orphan_audit_survivors=0,
        wallclock_decision=wallclock_decision,
        loopback_only_verified=False,
        fixture_base_url=fixture_base_url,
        notes=[f"SKIPPED reason={skip_reason}"],
    )

    _write_metadata(out_dir / "stability_metadata.json", result)
    # Stability log marker — JSON one-liner so downstream scanners can
    # detect the SKIPPED status without parsing the metadata file.
    (out_dir / "stability.log").write_text(
        json.dumps({"status": "SKIPPED", "reason": skip_reason, "mcp": mcp}) + "\n",
        encoding="utf-8",
    )
    return result


# ─── Production entry: real session + drive loop ────────────────────────


async def run_real(
    *,
    mcp: str,
    duration_minutes: float,
    sleep_s: float,
    fixture_base_url: str,
    out_dir: Path,
    mode: str,
    wallclock_decision: str,
) -> StabilityResult:
    """Production path: open a real stdio_client + ClientSession and drive the loop.

    The test-targeted ``run_stability_loop`` calls into ``_drive_loop``
    with ``session=None`` and mocked _call_stage; this function opens a
    real session and threads it through.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    loopback_only_verified = False
    if mcp == "cloakbrowser":
        assert_local_only(fixture_base_url)
        loopback_only_verified = True

    captured_at = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    log_path = out_dir / "stability.log"
    metadata_path = out_dir / "stability_metadata.json"
    orphan_log_path = out_dir / "stability_orphan_audit.log"
    snap_before = out_dir / ".stability_ps_before.tsv"
    snap_after = out_dir / ".stability_ps_after.tsv"

    _snapshot_before(snap_before)

    # Route browser-use-direct to the shared browser-use spawn.
    routed = "browser-use" if mcp == "browser-use-direct" else mcp
    spec = load_mcp_spec(routed)
    server_params = StdioServerParameters(
        command=spec.command,
        args=spec.args,
        env=spec.env,
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                try:
                    await asyncio.wait_for(session.initialize(), timeout=PER_TOOL_TIMEOUT_S)
                except asyncio.TimeoutError:
                    return _write_initialize_timeout(
                        mcp=mcp, out_dir=out_dir, captured_at=captured_at,
                        duration_minutes=duration_minutes, wallclock_decision=wallclock_decision,
                        fixture_base_url=fixture_base_url,
                        loopback_only_verified=loopback_only_verified,
                    )

                # The stdio_client manages the child PID internally; we
                # discover it via ps for RSS sampling.
                pid = _discover_mcp_pid(spec.command)

                return await _drive_loop(
                    mcp=mcp,
                    duration_minutes=duration_minutes,
                    sleep_s=sleep_s,
                    fixture_base_url=fixture_base_url,
                    out_dir=out_dir,
                    mode=mode,
                    wallclock_decision=wallclock_decision,
                    session=session,
                    pid=pid,
                    handle=None,
                    captured_at=captured_at,
                    loopback_only_verified=loopback_only_verified,
                    log_path=log_path,
                    metadata_path=metadata_path,
                    orphan_log_path=orphan_log_path,
                    snap_before=snap_before,
                    snap_after=snap_after,
                )
    except Exception as exc:  # noqa: BLE001
        # MCP spawn failed entirely — write a CRASHED record.
        return _write_spawn_failed(
            mcp=mcp, out_dir=out_dir, captured_at=captured_at,
            duration_minutes=duration_minutes, wallclock_decision=wallclock_decision,
            fixture_base_url=fixture_base_url,
            loopback_only_verified=loopback_only_verified,
            error=f"{type(exc).__name__}: {exc}",
        )


def _discover_mcp_pid(command: str) -> int:
    """Best-effort: find the PID of the MCP we just spawned via stdio_client.

    The SDK doesn't expose the child PID directly. We grep ps for the
    command name; if multiple match, return the highest PID (most
    recently spawned). Returns 0 if no match — RSS sampling will return 0.
    """
    try:
        out = subprocess.run(
            ["pgrep", "-f", command],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
        pids = [int(p) for p in out.split() if p.isdigit()]
        return max(pids) if pids else 0
    except (FileNotFoundError, ValueError):
        return 0


def _write_initialize_timeout(**kwargs) -> StabilityResult:
    """Helper: write a CRASHED record when initialize() timed out."""
    result = StabilityResult(
        mcp=kwargs["mcp"],
        captured_at=kwargs["captured_at"],
        configured_duration_minutes=kwargs["duration_minutes"],
        actual_duration_minutes=0.0,
        completion_status="CRASHED",
        skip_reason=None,
        iterations_completed=0,
        iterations_failed={"s1": 0, "s5": 0, "s5_skipped_readonly": 0},
        rss_first_kb=0,
        rss_max_kb=0,
        rss_growth_kb=0,
        orphan_audit_survivors=0,
        wallclock_decision=kwargs["wallclock_decision"],
        loopback_only_verified=kwargs["loopback_only_verified"],
        fixture_base_url=kwargs["fixture_base_url"],
        notes=[f"INITIALIZE_TIMEOUT after {PER_TOOL_TIMEOUT_S}s"],
    )
    _write_metadata(Path(kwargs["out_dir"]) / "stability_metadata.json", result)
    (Path(kwargs["out_dir"]) / "stability.log").write_text(
        json.dumps({"status": "INITIALIZE_TIMEOUT", "mcp": kwargs["mcp"]}) + "\n",
        encoding="utf-8",
    )
    return result


def _write_spawn_failed(**kwargs) -> StabilityResult:
    """Helper: write a CRASHED record when the MCP failed to spawn."""
    result = StabilityResult(
        mcp=kwargs["mcp"],
        captured_at=kwargs["captured_at"],
        configured_duration_minutes=kwargs["duration_minutes"],
        actual_duration_minutes=0.0,
        completion_status="CRASHED",
        skip_reason=None,
        iterations_completed=0,
        iterations_failed={"s1": 0, "s5": 0, "s5_skipped_readonly": 0},
        rss_first_kb=0,
        rss_max_kb=0,
        rss_growth_kb=0,
        orphan_audit_survivors=0,
        wallclock_decision=kwargs["wallclock_decision"],
        loopback_only_verified=kwargs["loopback_only_verified"],
        fixture_base_url=kwargs["fixture_base_url"],
        notes=[f"SPAWN_FAILED: {kwargs['error']}"],
    )
    _write_metadata(Path(kwargs["out_dir"]) / "stability_metadata.json", result)
    (Path(kwargs["out_dir"]) / "stability.log").write_text(
        json.dumps({"status": "SPAWN_FAILED", "error": kwargs["error"], "mcp": kwargs["mcp"]}) + "\n",
        encoding="utf-8",
    )
    return result


# ─── CLI ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.stability_loop",
        description=(
            "MEAS-07: 1-hour S1+S5 stability soak driver. Loops the snapshot "
            "fixture Greenhouse (S1) + Ashby (S5) stages against an MCP, "
            "with per-tool-call 30s timeout, RSS tracking, and post-run "
            "orphan_audit. Writes stability.log + stability_metadata.json."
        ),
    )
    parser.add_argument("mcp_name", type=str, help="MCP key from .mcp.json or browser-use-direct.")
    parser.add_argument("--duration-minutes", type=float, default=60.0)
    parser.add_argument("--sleep-s", type=float, default=30.0)
    parser.add_argument("--fixture-base-url", type=str, default="http://127.0.0.1:8765")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=["full", "read-only", "skip"], default="full")
    parser.add_argument("--skip-reason", type=str, default="")
    parser.add_argument(
        "--wallclock-decision",
        type=str,
        default="selective_top3_60min_rest_30min",
        help="Tag the run with the wallclock decision identifier (strict_60min, selective_top3_60min_rest_30min, reduced_30min_all).",
    )
    args = parser.parse_args(argv)

    if args.mode == "skip":
        result = run_skip(
            mcp=args.mcp_name,
            out_dir=args.out_dir,
            skip_reason=args.skip_reason or "UNSPECIFIED",
            duration_minutes=args.duration_minutes,
            wallclock_decision=args.wallclock_decision,
            fixture_base_url=args.fixture_base_url,
        )
        print(
            f"stability_loop: {args.mcp_name} SKIPPED reason={result.skip_reason}",
            file=sys.stderr,
        )
        return 0

    try:
        result = asyncio.run(run_real(
            mcp=args.mcp_name,
            duration_minutes=args.duration_minutes,
            sleep_s=args.sleep_s,
            fixture_base_url=args.fixture_base_url,
            out_dir=args.out_dir,
            mode=args.mode,
            wallclock_decision=args.wallclock_decision,
        ))
    except HostnameNotAllowedError as exc:
        print(f"stability_loop: REFUSED — {exc}", file=sys.stderr)
        return 3

    print(
        f"stability_loop: {args.mcp_name} status={result.completion_status} "
        f"iters={result.iterations_completed} actual_min={result.actual_duration_minutes:.2f} "
        f"rss_growth_kb={result.rss_growth_kb} survivors={result.orphan_audit_survivors}",
        file=sys.stderr,
    )
    # Exit codes: 0 = COMPLETED or COMPLETED_WITH_ORPHANS; nonzero = CRASHED/TIMED_OUT.
    return 0 if result.completion_status in ("COMPLETED", "COMPLETED_WITH_ORPHANS", "SKIPPED") else 2


if __name__ == "__main__":
    sys.exit(main())
