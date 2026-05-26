"""measure_cold_start — MEAS-01 3-segment cold-start latency measurer.

Plan 03-03 implements the cold-start half of the Phase-1 deferred bundle:
for each MCP under test, spawn the server cold (after ``pkill -f``) and
warm (immediately following), median of ≥5 runs each, with three timing
segments per run:

  * ``t_resolve``      — process spawn → stdio_client streams ready.
  * ``t_spawn``        — streams ready → ``session.initialize()`` returns.
  * ``t_first_useful`` — ``initialize`` returned → ``session.list_tools()``
                         returns.

Timing decomposition rationale
------------------------------
The MCP Python SDK's high-level ``stdio_client`` doesn't expose a hook for
"first byte of stdout received from the child" — it manages the read pipe
internally. The 03-03-PLAN.md context documents the pragmatic
decomposition we adopt:

  * ``t_resolve``      = time entering ``stdio_client.__aenter__()`` (process
                         spawn + initial protocol exchange to set up the
                         read/write streams).
  * ``t_spawn``        = time inside ``await session.initialize()``.
  * ``t_first_useful`` = time inside ``await session.list_tools()``.

This is faithful enough for cross-MCP comparison and avoids
re-implementing the JSON-RPC read loop. We document the approximation in
``metadata.timing_decomposition``.

Cache-eviction strategy
-----------------------
Between cold runs we ``pkill -f <pattern>`` against a small allowlist of
per-MCP patterns. We do NOT escalate to ``sudo purge`` (per global
constraint and 03-CONTEXT.md decisions). We document this with
``metadata.cache_eviction = "process_only"``.

CLI
---
    python -m bench.measure_cold_start <MCP_NAME> --out <PATH> \\
        [--n-runs 5] [--timeout-s 30] [--skip-pkill]

For the browser-use dual-mode case, two output filenames may share the
same underlying probe; we measure once against the ``browser-use`` .mcp.json
key and let the caller (Makefile / harness) copy the result into both
``browser-use-direct/`` and ``browser-use-agent/`` directories.

Special cases
-------------
  * **firecrawl**       — cold-start measures the LOCAL Node-process spawn
                          time of ``firecrawl-mcp``; it does NOT include
                          the cloud roundtrip. Documented in
                          ``metadata.notes``.
  * **lightpanda**      — handshake-version-mismatch issue is unrelated to
                          spawn timing; we record handshake version where
                          available.
  * **cloakbrowser**    — loopback-only contract irrelevant here (no
                          navigation involved, only initialize + tools/list).
  * **browser-use**     — 03-01 confirmed the v0.12.7 initialize-timeout is
                          fixed. We still tolerate TimeoutError per run.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

# Reuse the .mcp.json loader and StdioServerParameters wiring from
# tools_inventory.py — we extend the same proven spawn pattern.
from bench.tools_inventory import DEFAULT_MCP_JSON, load_mcp_spec, McpSpec
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


# ─── PKILL allowlist (safety contract per Test 5) ───────────────────────
#
# Each entry is a list of substring patterns that uniquely identify the
# MCP's process(es) WITHOUT matching the host benchmark harness (Python
# interpreter, bash, .venv, etc.). The Test 5 contract enforces:
#
#   * every pattern is at least 3 chars,
#   * never contains "*" (no wildcards — pkill -f matches substrings,
#     wildcards would be too greedy),
#   * never matches "python", "bash", or ".venv" (those are us).
#
# The patterns target the binary name + its npm/uv wrapper script
# combination, which is what shows up in `ps -axo command=` on macOS.

PKILL_PATTERNS: dict[str, list[str]] = {
    "playwright":      ["playwright-mcp", "@playwright/mcp"],
    "chrome-devtools": ["chrome-devtools-mcp"],
    "lightpanda":      ["lightpanda mcp", "lightpanda-x86", "lightpanda-aarch"],
    "obscura":         ["obscura-mcp"],
    "firecrawl":       ["firecrawl-mcp"],
    "cloakbrowser":    ["cloakbrowsermcp"],
    "browser-use":     ["browser-use --mcp"],
}


# ─── Pure helpers (test surface) ────────────────────────────────────────


def pkill_for_mcp(mcp_key: str, *, skip: bool = False) -> int:
    """Send SIGTERM to any process whose command matches a per-MCP pattern.

    Parameters
    ----------
    mcp_key
        Key from :data:`PKILL_PATTERNS`. Unknown keys raise ``ValueError``
        per the safety contract.
    skip
        If True, return 0 immediately without invoking ``pkill``. The
        ``--skip-pkill`` CLI flag wires through to this.

    Returns
    -------
    int
        Best-effort count of patterns that matched at least one process
        (pkill exits 0 on at least-one match, 1 on no matches, >1 on
        errors). We count successful exit codes per pattern as "matched".

    Raises
    ------
    ValueError
        If ``mcp_key`` is not in the allowlist, or if any allowlisted
        pattern is empty/whitespace. Defence-in-depth against a corrupted
        PKILL_PATTERNS dict.
    """
    if skip:
        return 0

    if mcp_key not in PKILL_PATTERNS:
        raise ValueError(
            f"pkill_for_mcp: {mcp_key!r} is not in PKILL_PATTERNS allowlist; "
            f"available: {sorted(PKILL_PATTERNS.keys())}"
        )

    patterns = PKILL_PATTERNS[mcp_key]
    matched_count = 0
    for pat in patterns:
        if not pat or not pat.strip():
            # Corruption guard — should never happen with the
            # hard-coded module-level table, but Test 5 enforces it.
            raise ValueError(
                f"pkill_for_mcp: empty pattern in PKILL_PATTERNS[{mcp_key!r}]"
            )
        # Use -f (full command line, not just process name) — MCP servers
        # often appear as `node /path/to/.bin/playwright-mcp` so the
        # short name alone wouldn't match.
        try:
            rc = subprocess.run(
                ["pkill", "-f", pat],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode
            if rc == 0:
                matched_count += 1
        except FileNotFoundError:
            # pkill not on PATH — extremely unlikely on macOS/Linux but
            # we don't want to crash the measurement loop over it.
            pass

    # Give the OS a moment to reap the process group and release any
    # listening sockets. 200 ms is empirically enough for Node MCPs on
    # macOS arm64; longer would inflate the wall-clock budget needlessly.
    time.sleep(0.2)
    return matched_count


# Type alias for clarity; one sample row in the output JSON.
SegmentSample = dict[str, Any]


def compute_segment_medians(samples: list[SegmentSample]) -> dict[str, Any]:
    """Return median values across a list of samples (ignoring error rows).

    Each successful sample is expected to carry ``t_resolve_ms``,
    ``t_spawn_ms``, ``t_first_useful_ms``, and ``total_ms``. Error rows
    (those with an ``"error"`` key) are skipped.

    When all samples fail, every field returns ``None`` — the caller can
    surface a ``status: SPAWN_FAILED`` rather than crash.
    """
    valid = [s for s in samples if "error" not in s and "total_ms" in s]
    if not valid:
        return {
            "t_resolve_ms": None,
            "t_spawn_ms": None,
            "t_first_useful_ms": None,
            "total_ms": None,
        }
    out: dict[str, Any] = {}
    for key in ("t_resolve_ms", "t_spawn_ms", "t_first_useful_ms", "total_ms"):
        out[key] = statistics.median([s[key] for s in valid])
    return out


def _min_max_across(samples: list[SegmentSample]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (min, max) dicts per-segment across successful samples."""
    valid = [s for s in samples if "error" not in s and "total_ms" in s]
    if not valid:
        none_dict = {
            "t_resolve_ms": None,
            "t_spawn_ms": None,
            "t_first_useful_ms": None,
            "total_ms": None,
        }
        return none_dict, dict(none_dict)
    mins: dict[str, Any] = {}
    maxes: dict[str, Any] = {}
    for key in ("t_resolve_ms", "t_spawn_ms", "t_first_useful_ms", "total_ms"):
        vals = [s[key] for s in valid]
        mins[key] = min(vals)
        maxes[key] = max(vals)
    return mins, maxes


# ─── Single-run timing (injectable for tests) ───────────────────────────


async def measure_one_run(
    *,
    open_streams_coro_factory: Callable[[], Awaitable[Any]],
    initialize_coro_factory: Callable[[], Awaitable[Any]],
    list_tools_coro_factory: Callable[[], Awaitable[Any]],
) -> SegmentSample:
    """Time the three async stages and return a SegmentSample.

    The three callables are factories that return fresh awaitables each
    call. This indirection is the test seam — production callers wire
    the real ``stdio_client`` / ``ClientSession`` operations; tests pass
    ``asyncio.sleep``-based fakes.

    The three timing anchors are captured with ``time.perf_counter_ns()``,
    which is monotonic and high-resolution. We convert to milliseconds
    at the end and round to int to keep the JSON readable.
    """
    t0 = time.perf_counter_ns()
    await open_streams_coro_factory()
    t1 = time.perf_counter_ns()
    await initialize_coro_factory()
    t2 = time.perf_counter_ns()
    await list_tools_coro_factory()
    t3 = time.perf_counter_ns()

    t_resolve_ms = max(1, round((t1 - t0) / 1_000_000))
    t_spawn_ms = max(1, round((t2 - t1) / 1_000_000))
    t_first_useful_ms = max(1, round((t3 - t2) / 1_000_000))
    total_ms = max(1, round((t3 - t0) / 1_000_000))
    return {
        "t_resolve_ms": t_resolve_ms,
        "t_spawn_ms": t_spawn_ms,
        "t_first_useful_ms": t_first_useful_ms,
        "total_ms": total_ms,
    }


# ─── Real run: drives stdio_client + ClientSession with timing anchors ──


async def _run_one_real(spec: McpSpec, timeout_s: float) -> SegmentSample:
    """Run one real spawn-initialize-list_tools cycle and time it.

    Uses three anchor points around the SDK calls:

      * t0 = before entering ``stdio_client(...)`` context manager.
      * t1 = streams ready (entered the inner ``ClientSession`` ctx).
      * t2 = ``session.initialize()`` returned.
      * t3 = ``session.list_tools()`` returned.

    The whole probe is wrapped in ``asyncio.wait_for(..., timeout_s)``
    so a wedged MCP doesn't stall the measurement loop. On timeout the
    caller catches ``asyncio.TimeoutError`` and records an error row.

    Note on cleanup: ``stdio_client.__aexit__`` is responsible for
    SIGTERM'ing the child process group (the SDK uses anyio's process
    group semantics). Phase-3 stability runs verify orphan-cleanup;
    here we just trust the SDK's teardown.
    """
    server_params = StdioServerParameters(
        command=spec.command,
        args=spec.args,
        env=spec.env,
    )

    async def _probe() -> SegmentSample:
        t0 = time.perf_counter_ns()
        async with stdio_client(server_params) as (read, write):
            t1 = time.perf_counter_ns()
            async with ClientSession(read, write) as session:
                await session.initialize()
                t2 = time.perf_counter_ns()
                await session.list_tools()
                t3 = time.perf_counter_ns()
        # nanoseconds → milliseconds, integer rounding for JSON readability
        return {
            "t_resolve_ms": max(1, round((t1 - t0) / 1_000_000)),
            "t_spawn_ms": max(1, round((t2 - t1) / 1_000_000)),
            "t_first_useful_ms": max(1, round((t3 - t2) / 1_000_000)),
            "total_ms": max(1, round((t3 - t0) / 1_000_000)),
        }

    return await asyncio.wait_for(_probe(), timeout=timeout_s)


# ─── Outer loop: cold runs, warm runs, median, JSON shape ───────────────


async def measure_mcp(
    *,
    mcp_key: str,
    n_runs: int = 5,
    timeout_s: float = 30.0,
    skip_pkill: bool = False,
    spec: McpSpec | None = None,
) -> dict[str, Any]:
    """Run cold + warm sweeps for one MCP and return the cold_start.json dict.

    Parameters
    ----------
    mcp_key
        Key in :data:`PKILL_PATTERNS` AND in ``.mcp.json``. For the
        browser-use dual-mode case, callers pass ``"browser-use"``; the
        Makefile copies the resulting file into both
        ``browser-use-direct/`` and ``browser-use-agent/`` directories.
    n_runs
        Number of samples per scope (cold and warm). Default 5 per the
        plan's "median of ≥5" requirement.
    timeout_s
        Per-run timeout. A wedged ``initialize`` aborts after this many
        seconds and records an error row.
    skip_pkill
        If True, no pkill is invoked between cold samples. Useful for
        local debugging.
    spec
        Pre-resolved McpSpec. If None, we load from .mcp.json (the
        production path).

    Returns
    -------
    dict
        cold_start.json-shaped dict. The caller writes it to disk via
        :func:`write_cold_start_json`.
    """
    captured_at = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    # ── Cold sweep: pkill before each run, then measure.
    cold_samples: list[SegmentSample] = []
    for i in range(n_runs):
        pkill_for_mcp(mcp_key, skip=skip_pkill)
        try:
            if spec is not None:
                sample = await _run_one_real(spec, timeout_s)
            else:
                # In tests _run_one_real is monkey-patched, so the spec
                # argument isn't actually consumed. Pass a sentinel-like
                # value when no real spec is needed.
                sample = await _run_one_real(spec, timeout_s)  # type: ignore[arg-type]
            sample["run"] = i + 1
            cold_samples.append(sample)
        except asyncio.TimeoutError as exc:
            cold_samples.append({"run": i + 1, "error": f"INITIALIZE_TIMEOUT: {exc}"})
        except Exception as exc:  # noqa: BLE001 — surface every failure mode
            cold_samples.append({"run": i + 1, "error": f"{type(exc).__name__}: {exc}"})

    # ── Warm sweep: NO pkill, immediately follow.
    warm_samples: list[SegmentSample] = []
    for i in range(n_runs):
        try:
            if spec is not None:
                sample = await _run_one_real(spec, timeout_s)
            else:
                sample = await _run_one_real(spec, timeout_s)  # type: ignore[arg-type]
            sample["run"] = i + 1
            warm_samples.append(sample)
        except asyncio.TimeoutError as exc:
            warm_samples.append({"run": i + 1, "error": f"INITIALIZE_TIMEOUT: {exc}"})
        except Exception as exc:  # noqa: BLE001
            warm_samples.append({"run": i + 1, "error": f"{type(exc).__name__}: {exc}"})

    cold_median = compute_segment_medians(cold_samples)
    cold_min, cold_max = _min_max_across(cold_samples)
    warm_median = compute_segment_medians(warm_samples)
    warm_min, warm_max = _min_max_across(warm_samples)

    cold_ok = any("error" not in s for s in cold_samples)
    warm_ok = any("error" not in s for s in warm_samples)
    status = "OK" if (cold_ok or warm_ok) else "SPAWN_FAILED"

    return {
        "mcp": mcp_key,
        "captured_at": captured_at,
        "status": status,
        "n_runs": n_runs,
        "cold": {
            "samples": cold_samples,
            "median": cold_median,
            "min": cold_min,
            "max": cold_max,
            "n_runs": n_runs,
        },
        "warm": {
            "samples": warm_samples,
            "median": warm_median,
            "min": warm_min,
            "max": warm_max,
            "n_runs": n_runs,
        },
        "metadata": {
            "cache_eviction": "process_only",
            "timing_decomposition": (
                "t_resolve = stdio_client.__aenter__ to streams ready; "
                "t_spawn = session.initialize() duration; "
                "t_first_useful = session.list_tools() duration"
            ),
            "measurement_method": "python.mcp.client.stdio + time.perf_counter_ns",
            "host": _host_descriptor(),
            "notes": [
                "sudo purge not invoked; 'cold' approximates first-spawn-of-shell-session "
                "after pkill -f, not uncached-filesystem.",
            ],
        },
    }


def _host_descriptor() -> str:
    """Short host string for the metadata block.

    Includes platform, machine arch, and Python version — enough for a
    reader to know "this was measured on M-series macOS arm64 Python 3.12"
    without leaking hostnames or usernames.
    """
    return (
        f"{platform.system()} {platform.release()} "
        f"{platform.machine()} python={platform.python_version()}"
    )


# ─── JSON writer ────────────────────────────────────────────────────────


def write_cold_start_json(out_path: Path, payload: dict[str, Any]) -> None:
    """Write the payload to ``out_path`` as pretty JSON, parent-mkdir'd."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# ─── CLI ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.measure_cold_start",
        description=(
            "MEAS-01: measure 3-segment cold-start latency for one MCP. "
            "Spawns the MCP via mcp.client.stdio, times "
            "stdio_client+initialize+tools/list across N cold runs "
            "(pkill -f between) and N warm runs (no pkill), then writes "
            "cold_start.json with per-segment medians."
        ),
    )
    parser.add_argument(
        "mcp_name",
        type=str,
        help=(
            "MCP key. Accepts the .mcp.json keys (playwright, "
            "browser-use, chrome-devtools, lightpanda, obscura, "
            "firecrawl, cloakbrowser) AND the two browser-use variants "
            "(browser-use-direct, browser-use-agent) — both route to "
            "the shared browser-use spawn."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output path for cold_start.json.",
    )
    parser.add_argument(
        "--n-runs",
        type=int,
        default=5,
        help="Samples per scope (cold AND warm). Default 5.",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=30.0,
        help="Per-run timeout. Default 30s (matches tools_inventory.py).",
    )
    parser.add_argument(
        "--skip-pkill",
        action="store_true",
        help="Skip pkill between cold runs (debug only — cold becomes a no-op then).",
    )
    parser.add_argument(
        "--mcp-json",
        type=Path,
        default=DEFAULT_MCP_JSON,
        help="Path to .mcp.json (default: project-scope .mcp.json).",
    )
    args = parser.parse_args(argv)

    # Route browser-use-direct / browser-use-agent to the shared spawn key.
    routed_name = args.mcp_name
    mode_note: str | None = None
    if args.mcp_name in ("browser-use-direct", "browser-use-agent"):
        routed_name = "browser-use"
        mode_note = (
            f"variant={args.mcp_name}: cold-start measured against shared "
            f"'browser-use' MCP binary; direct vs agent only diverges at "
            f"agent-session time, not at spawn."
        )

    try:
        spec = load_mcp_spec(routed_name, args.mcp_json)
    except (FileNotFoundError, KeyError) as exc:
        # Refuse to invent a missing MCP — write a SPAWN_FAILED record.
        payload = {
            "mcp": args.mcp_name,
            "status": "SPAWN_FAILED",
            "error": f"MCP_CONFIG_ERROR: {exc}",
        }
        write_cold_start_json(args.out, payload)
        print(f"measure_cold_start: {args.mcp_name} -> {args.out} (status=SPAWN_FAILED)", file=sys.stderr)
        return 2

    payload = asyncio.run(
        measure_mcp(
            mcp_key=routed_name,
            n_runs=args.n_runs,
            timeout_s=args.timeout_s,
            skip_pkill=args.skip_pkill,
            spec=spec,
        )
    )
    # Re-tag the mcp field to the variant name the caller asked for,
    # so the per-directory file is self-describing.
    payload["mcp"] = args.mcp_name
    if mode_note is not None:
        payload.setdefault("metadata", {})
        payload["metadata"]["mode"] = mode_note

    write_cold_start_json(args.out, payload)

    print(
        f"measure_cold_start: {args.mcp_name} -> {args.out} "
        f"(status={payload.get('status')}, "
        f"cold_median_total_ms={payload.get('cold', {}).get('median', {}).get('total_ms')}, "
        f"warm_median_total_ms={payload.get('warm', {}).get('median', {}).get('total_ms')})",
        file=sys.stderr,
    )

    # Exit codes: 0 = at least one successful run somewhere; 2 = all failed.
    return 0 if payload.get("status") == "OK" else 2


if __name__ == "__main__":
    sys.exit(main())
