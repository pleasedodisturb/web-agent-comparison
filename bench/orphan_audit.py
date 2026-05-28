"""orphan_audit — pre/post `ps` diff with MCP-aware survivor killing.

Pitfall 9 ("orphan accumulation") names the canonical failure mode of an
MCP harness: a wedged Chromium / Node / Python helper outlives the Claude
Code session that spawned it, accumulates across runs, and silently
inflates RSS until the host OOMs or the 1hr stability soak measures the
sum of N broken runs instead of one clean one.

This module is the defence. It runs in two modes:

  * `--snapshot-only <path>` — dump the current `ps` table to `<path>`.
    The harness calls this BEFORE spawning the MCP-driving Claude Code
    session, and AGAIN immediately after the session exits.

  * `--before-snapshot <p1> --after-snapshot <p2> --pgid <int> --log <path>`
    Diff the two snapshots: any PID present in `after` but not `before`
    that ALSO matches either the target PGID or the MCP-cmdline regex is
    flagged as a survivor. Each survivor is killed with SIGKILL and a
    `KILLED pid=... cmd=...` line is written to the log. Exit code: 0 if
    survivors == 0; 1 otherwise.

The exit code is what `scripts/run_mcp_session.sh` keys off to decide
whether to flag the run as `harness_leaked=true` per Pitfall 9. In Phase 1
we LOG-and-CONTINUE (the plan explicitly says don't fail the run on
orphans yet — we want to surface the gap on Playwright before tightening);
later phases tighten this to a hard fail.

The cmdline regex is intentionally broad: any process whose command line
mentions one of the seven candidate MCPs (or chromium/playwright) gets
killed, even if its PGID rotated away from the original session leader.
That's the conservative choice — false-positive over-kills inside the
harness window are cheap; false-negative leaks are exactly the bug we're
defending against.
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import sys
from datetime import datetime, timezone

from bench.process_group import read_ps_snapshot, write_ps_snapshot


# Patterns matching commands the harness must own. If any of these appear
# in a process's command line AND that process appeared during the harness
# window (i.e. is in `after` but not `before`), it's a survivor.
#
# We include both MCP names (playwright, obscura, ...) and their typical
# child-process markers (chromium, node, browser_main, headless_shell).
# Better to over-kill our own harness leaks than to leak.
MCP_CMDLINE_PATTERNS: tuple[str, ...] = (
    r"playwright[-_]mcp",
    r"chrome-devtools-mcp",
    r"obscura[-_]mcp",
    r"firecrawl[-_]mcp",
    r"cloakbrowsermcp",
    r"browser[-_]use",
    r"lightpanda",
    r"chromium",
    r"playwright",
    r"headless[-_]shell",
    r"chrome_crashpad_handler",
)

_MCP_RE = re.compile("|".join(MCP_CMDLINE_PATTERNS), re.IGNORECASE)


def _now_iso() -> str:
    """UTC ISO-8601 with `Z` suffix for log lines."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _diff_pids(
    before: list[dict[str, str | int]],
    after: list[dict[str, str | int]],
    target_pgid: int | None,
) -> list[dict[str, str | int]]:
    """Return rows in `after` whose pid is not in `before` AND match the filter.

    Filter: pgid == target_pgid OR command matches the MCP regex.
    """
    before_pids = {int(r["pid"]) for r in before}
    survivors: list[dict[str, str | int]] = []
    for row in after:
        pid = int(row["pid"])
        if pid in before_pids:
            continue
        pgid_match = target_pgid is not None and int(row["pgid"]) == target_pgid
        cmd_match = bool(_MCP_RE.search(str(row["command"])))
        if pgid_match or cmd_match:
            survivors.append(row)
    return survivors


def _kill_survivors(
    survivors: list[dict[str, str | int]],
    log_lines: list[str],
) -> int:
    """SIGKILL each survivor, append a log line per kill. Returns kill count."""
    killed = 0
    for row in survivors:
        pid = int(row["pid"])
        cmd = str(row["command"])
        try:
            os.kill(pid, signal.SIGKILL)
            killed += 1
            log_lines.append(f"KILLED pid={pid} pgid={row['pgid']} cmd={cmd}")
        except ProcessLookupError:
            # Already exited between snapshot and kill — fine, that's the
            # outcome we wanted. Note it so a reader of the log can tell
            # the difference between "we killed it" and "it died on its
            # own during the audit window".
            log_lines.append(f"GONE pid={pid} pgid={row['pgid']} cmd={cmd}")
        except PermissionError:
            # Should never happen for processes we spawned, but if the user
            # ran the harness with reduced privileges it's diagnostic.
            log_lines.append(
                f"PERMISSION_DENIED pid={pid} pgid={row['pgid']} cmd={cmd}"
            )
    return killed


def cmd_snapshot_only(path: str) -> int:
    """`--snapshot-only` entry point.

    Dumps the current `ps` table to `path`. Used as the BEFORE snapshot
    (taken just before the harness spawns Claude Code) and as the AFTER
    snapshot (taken immediately after Claude Code exits).
    """
    n = write_ps_snapshot(path)
    print(f"orphan_audit: snapshot wrote {n} rows to {path}", file=sys.stderr)
    return 0


def cmd_diff(
    before_path: str,
    after_path: str,
    pgid: int | None,
    log_path: str,
) -> int:
    """`--before-snapshot ... --after-snapshot ...` entry point.

    Reads both snapshots, computes the survivor set, kills each, writes
    the log file. Exit code: 0 if survivors == 0; 1 otherwise so the
    harness can flag the run as `harness_leaked`.
    """
    before = read_ps_snapshot(before_path)
    after = read_ps_snapshot(after_path)
    survivors = _diff_pids(before, after, pgid)

    log_lines: list[str] = []
    log_lines.append(f"# orphan_audit run at {_now_iso()}")
    log_lines.append(f"BEFORE_PATH={before_path}")
    log_lines.append(f"AFTER_PATH={after_path}")
    log_lines.append(f"TARGET_PGID={pgid if pgid is not None else 'unset'}")
    log_lines.append(f"BEFORE_COUNT={len(before)}")
    log_lines.append(f"AFTER_COUNT={len(after)}")
    log_lines.append(f"DIFF_COUNT={len(survivors)}")

    killed = _kill_survivors(survivors, log_lines)

    log_lines.append(f"KILLED_COUNT={killed}")
    log_lines.append(f"ORPHANS={len(survivors)}")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")

    print(
        f"orphan_audit: survivors={len(survivors)} killed={killed} log={log_path}",
        file=sys.stderr,
    )
    return 0 if len(survivors) == 0 else 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m bench.orphan_audit",
        description="Pre/post ps diff for the MCP harness; kills survivors.",
    )
    p.add_argument(
        "--snapshot-only",
        metavar="PATH",
        help="Dump current ps table to PATH and exit (no diff, no kill).",
    )
    p.add_argument(
        "--before-snapshot",
        metavar="PATH",
        help="Path to the pre-run ps snapshot (written by an earlier --snapshot-only).",
    )
    p.add_argument(
        "--after-snapshot",
        metavar="PATH",
        help="Path to the post-run ps snapshot.",
    )
    p.add_argument(
        "--pgid",
        type=int,
        default=None,
        help="Process-group id of the harnessed session. Survivors matching this PGID OR the MCP cmdline regex get killed.",
    )
    p.add_argument(
        "--log",
        metavar="PATH",
        help="Path to write the audit log.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.snapshot_only is not None:
        return cmd_snapshot_only(args.snapshot_only)

    if not (args.before_snapshot and args.after_snapshot and args.log):
        print(
            "orphan_audit: --before-snapshot, --after-snapshot, and --log are required for diff mode",
            file=sys.stderr,
        )
        return 2

    return cmd_diff(args.before_snapshot, args.after_snapshot, args.pgid, args.log)


if __name__ == "__main__":
    sys.exit(main())
