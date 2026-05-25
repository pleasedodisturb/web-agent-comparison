"""stub_writers — emit deferred-marker evidence files for Phase 1 runs.

Phase 1 of the web-agent-comparison benchmark deliberately defers three
measurements to follow-up work:

  * `tls.json`       — JA3 / JA4 fingerprint capture (deferred to G-710 per
                       the 2026-05-22 scope cut documented in
                       `.planning/phases/01-harness-foundation/01-CONTEXT.md`).
  * `cold_start.json` — the full 3-segment (resolve / spawn / first-useful)
                       cold-start measurement lands in Phase 3 (MEAS-01). Phase
                       1 emits a shape-locked stub so the aggregator's
                       `_safe_read_json` path doesn't have to special-case a
                       missing file.
  * `stability.log`   — the 60-minute S1+S5 loop lands in Phase 3 (MEAS-07);
                       Phase 1 emits a single-line stub.

These stubs exist for one reason: **lock the evidence-directory contract** so
`scripts/aggregate_scores.py` (already shipped in plan 01-05) can rely on
finding the files. The aggregator already recognizes the `{"deferred": ...}`
shape and assigns the neutral mid-band score (5/10) for the affected
dimensions — see `_score_speed` and `_score_token_efficiency` in
`scripts/aggregate_scores.py`. That treatment is the contract this module
upholds.

Public API
----------
    write_tls_stub(out_dir)
    write_cold_start_stub(out_dir, mcp_name)
    write_stability_stub(out_dir)
    write_stubs(out_dir, mcp_name)   # convenience wrapper that calls all three

CLI
---
    python -m bench.stub_writers <OUT_DIR> [--mcp-name <name>]

The CLI is what `scripts/run_mcp_session.sh` invokes after the Claude Code
session ends. It is idempotent — if a stub already exists with content that
parses correctly, it is left alone; otherwise it is (re)written. Re-running
the CLI never destroys a real measurement file, because every stub we write
contains the `{"deferred": ...}` marker and the CLI refuses to clobber a file
that does NOT contain that marker.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# The Linear ticket the deferred work tracks back to. Hard-coded here (not
# pulled from env) because the evidence directory is a public artifact and
# the ticket reference is part of the auditable provenance trail.
DEFERRED_TICKET = "G-710"

# A short, human-readable reason the stub exists. Surfaced in every stub
# file so a reader of the evidence directory understands at a glance why
# the field is null.
TLS_REASON = (
    "TLS fingerprint capture (JA3/JA4) cut from v1 per 2026-05-22 scope cut."
)
COLD_START_REASON = (
    "Full 3-segment cold-start measurement deferred to Phase 3 (MEAS-01); "
    "Phase 1 ships the directory contract only."
)
STABILITY_REASON = (
    "60-min S1+S5 stability loop deferred to Phase 3 (MEAS-07); "
    "Phase 1 ships the directory contract only."
)


# ─── Helpers ──────────────────────────────────────────────────────────────


def _is_deferred_stub(path: Path) -> bool:
    """Return True if the file exists and contains the deferred marker.

    The aggregator and the stub-writer treat any file with `"deferred":
    "<ticket>"` as a stub. Used by the CLI to decide whether overwriting
    is safe (overwriting a stub is fine; overwriting a real measurement
    file is not).
    """
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    # Allow either JSON ({"deferred": "..."}) or plain-text logs that
    # mention the deferred marker (the stability.log case).
    if '"deferred"' in text:
        return True
    if "STUB —" in text or "deferred to" in text.lower():
        return True
    return False


def _atomic_write_text(path: Path, content: str) -> None:
    """Write `content` to `path` atomically.

    A `.tmp.<pid>` sibling file is written first, then renamed. This
    prevents a half-written stub from being observed by a concurrent
    aggregator process. The atomicity guarantee is filesystem-level
    (POSIX rename(2)).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{Path(__file__).stat().st_ino}")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


# ─── Stub writers ─────────────────────────────────────────────────────────


def write_tls_stub(out_dir: Path) -> Path:
    """Write `<out_dir>/tls.json` as a deferred-marker stub.

    Shape (matches the contract the aggregator's `_score_*` helpers look
    for; the `deferred` key triggers the neutral mid-band treatment):

        {
          "deferred": "G-710",
          "reason": "TLS fingerprint capture (JA3/JA4) cut from v1 ...",
          "see": "https://linear.app/.../G-710"
        }

    Returns
    -------
    pathlib.Path
        The path of the file written, so callers can log it.
    """
    out_dir = Path(out_dir)
    path = out_dir / "tls.json"
    payload: dict[str, Any] = {
        "deferred": DEFERRED_TICKET,
        "reason": TLS_REASON,
        "see": f"https://linear.app/abandoned-yachts/issue/{DEFERRED_TICKET}",
    }
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def write_cold_start_stub(out_dir: Path, mcp_name: str) -> Path:
    """Write `<out_dir>/cold_start.json` as a deferred-marker stub.

    The shape matches what Phase 3's real 3-segment measurement will emit
    (so consumers don't have to learn two shapes), with every numeric
    field set to `null`:

        {
          "mcp": "<mcp_name>",
          "t_resolve_ms": null,
          "t_spawn_ms": null,
          "t_first_useful_ms": null,
          "warm_cache": null,
          "n_runs": 0,
          "deferred": "G-710",
          "reason": "... deferred to Phase 3 (MEAS-01) ..."
        }

    Parameters
    ----------
    out_dir
        Per-MCP evidence directory (e.g. `results/2026-05-22/playwright/`).
    mcp_name
        The MCP's `.mcp.json` key, embedded in the JSON so a reader of
        the file in isolation can tell which MCP it belongs to.
    """
    out_dir = Path(out_dir)
    path = out_dir / "cold_start.json"
    payload: dict[str, Any] = {
        "mcp": mcp_name,
        "t_resolve_ms": None,
        "t_spawn_ms": None,
        "t_first_useful_ms": None,
        "warm_cache": None,
        "n_runs": 0,
        "deferred": DEFERRED_TICKET,
        "reason": COLD_START_REASON,
        "see": f"https://linear.app/abandoned-yachts/issue/{DEFERRED_TICKET}",
    }
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def write_stability_stub(out_dir: Path) -> Path:
    """Write `<out_dir>/stability.log` as a single-line deferred stub.

    Plain text (not JSON) because Phase 3's real stability loop writes a
    line-per-iteration log that humans grep. The stub is a single line
    so the file exists and a `wc -l` doesn't return 0 (which some readers
    might interpret as "ran but failed every iteration").
    """
    out_dir = Path(out_dir)
    path = out_dir / "stability.log"
    # Single line, newline-terminated. Mentions both the ticket and the
    # phase so either grep pattern surfaces the file.
    content = (
        f"STUB — 60-min S1+S5 loop deferred to {DEFERRED_TICKET} "
        f"(full run lands in Phase 3 / MEAS-07)\n"
    )
    _atomic_write_text(path, content)
    return path


def write_stubs(out_dir: Path, mcp_name: str) -> dict[str, Path]:
    """Write all three Phase-1 deferred stubs at once.

    Convenience wrapper for `scripts/run_mcp_session.sh`. Returns the
    paths written, keyed by short name (`tls`, `cold_start`, `stability`)
    so the caller can log or assert on them.
    """
    return {
        "tls": write_tls_stub(out_dir),
        "cold_start": write_cold_start_stub(out_dir, mcp_name),
        "stability": write_stability_stub(out_dir),
    }


# ─── CLI ──────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.stub_writers",
        description=(
            "Emit Phase-1 deferred-marker stub files (tls.json, "
            "cold_start.json, stability.log) into a per-MCP evidence "
            "directory. Idempotent — never overwrites a real measurement file."
        ),
    )
    parser.add_argument(
        "out_dir",
        type=Path,
        help="Per-MCP evidence directory (e.g. results/2026-05-22/playwright/)",
    )
    parser.add_argument(
        "--mcp-name",
        type=str,
        default="",
        help="MCP key from .mcp.json, embedded in cold_start.json (optional; "
             "defaults to the basename of out_dir)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite even files that don't carry the deferred marker. "
             "DANGEROUS — only use when re-initializing an evidence dir.",
    )
    args = parser.parse_args(argv)

    out_dir: Path = args.out_dir
    mcp_name: str = args.mcp_name or out_dir.name

    # Safety: refuse to clobber a real measurement file.
    for fname in ("tls.json", "cold_start.json", "stability.log"):
        target = out_dir / fname
        if target.exists() and not _is_deferred_stub(target) and not args.force:
            print(
                f"stub_writers: refusing to overwrite real measurement file: "
                f"{target} (re-run with --force to override)",
                file=sys.stderr,
            )
            return 1

    written = write_stubs(out_dir, mcp_name)
    for label, path in written.items():
        print(f"stub_writers: wrote {label} -> {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
