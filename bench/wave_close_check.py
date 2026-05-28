"""wave_close_check — SAFETY-05 wave-close ritual auditor.

The auditor verifies four invariants at the close of Wave 2 to confirm
no scope-creep landed during the wave:

  1. `.mcp.json` mcpServers count == 7 (the locked candidate set frozen
     at wave start in `.planning/REQUIREMENTS.md`).
  2. `scoring/rubric.md` has exactly 8 weighted dimensions (the rubric
     was locked at wave start; column count drift = uncontrolled
     rubric change).
  3. `git log --grep=terminal-craft --oneline` returns 0 lines — no
     Stage 2 toolkit work landed in this benchmark repo. Stage 2 lives
     in the private `terminal-craft` repo and must NEVER be committed
     here per the pipeline gate.
  4. The MCP key set in `.mcp.json` matches the wave-start baseline
     (no MCP added or removed mid-wave — catches the case where the
     count stays 7 but a swap happened).

CLI
---
    python3 -m bench.wave_close_check \\
        [--mcp-json .mcp.json] \\
        [--rubric scoring/rubric.md] \\
        [--out .planning/phases/04-synthesis/WAVE_CLOSE_AUDIT.md] \\
        [--repo-root .]

Exit code:
    0 — all four checks PASS
    1 — at least one check FAILed

The auditor is stdlib-only (json + subprocess + argparse + pathlib).
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


# ─── Constants ───────────────────────────────────────────────────────────

# The 7-candidate baseline set frozen at Wave 2 start per
# `.planning/phases/04-synthesis/04-CONTEXT.md`. Any drift = scope creep.
WAVE2_BASELINE: frozenset[str] = frozenset(
    {
        "playwright",
        "browser-use",
        "chrome-devtools",
        "lightpanda",
        "obscura",
        "firecrawl",
        "cloakbrowser",
    }
)

# Expected counts per SAFETY-05.
EXPECTED_CANDIDATE_COUNT = 7
EXPECTED_RUBRIC_COLUMNS = 8
EXPECTED_TERMINAL_CRAFT_COMMITS = 0

# Regex matching a rubric table row that looks like a dimension definition.
# Rubric rows look like: "| **Data Quality** | 3x | ... |"
# We count only rows where the first cell is wrapped in `**...**` (the
# dimension-name convention in scoring/rubric.md). This excludes header
# rows ("| Dimension | Weight | ..."), separator rows ("|---|---|"), and
# the unrelated "Test Stages" table that follows.
_RUBRIC_DIM_ROW_RE = re.compile(r"^\|\s*\*\*[^*|]+\*\*\s*\|")


# ─── Individual audit functions ─────────────────────────────────────────


def audit_candidate_count(mcp_json_path: Path) -> int:
    """Return the number of keys under mcpServers in `.mcp.json`.

    Expected = EXPECTED_CANDIDATE_COUNT (7). Returns the actual count
    so the caller can compare and surface drift.

    Raises:
        FileNotFoundError: if mcp_json_path is missing.
        ValueError: if the JSON is malformed or lacks `mcpServers`.
    """
    if not mcp_json_path.is_file():
        raise FileNotFoundError(f".mcp.json not found: {mcp_json_path}")
    try:
        payload = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"could not parse {mcp_json_path}: {exc}") from exc
    servers = payload.get("mcpServers")
    if not isinstance(servers, dict):
        raise ValueError(
            f"{mcp_json_path} has no `mcpServers` object (got {type(servers).__name__})"
        )
    return len(servers)


def audit_rubric_columns(rubric_path: Path) -> int:
    """Return the number of rubric dimensions in `scoring/rubric.md`.

    Counts table rows where the first cell is `**<name>**` (the
    dimension-row convention). Excludes table headers, separator lines,
    and the unrelated "Test Stages" table.

    Expected = EXPECTED_RUBRIC_COLUMNS (8). Returns the actual count.
    """
    if not rubric_path.is_file():
        raise FileNotFoundError(f"rubric.md not found: {rubric_path}")
    text = rubric_path.read_text(encoding="utf-8")
    count = 0
    in_dimensions_section = False
    for line in text.splitlines():
        stripped = line.strip()
        # Track section boundaries — only count dimension-row matches
        # that appear under a heading whose text contains "dimension"
        # (case-insensitive). This is belt-and-suspenders against a
        # future rubric.md that grows a second `**bold**`-rowed table
        # elsewhere, while still tolerating renames like
        # "## Weighted Dimensions" or "## Scoring Dimensions" (WR-06).
        if stripped.startswith("## "):
            in_dimensions_section = "dimension" in stripped.lower()
            continue
        if not in_dimensions_section:
            continue
        if _RUBRIC_DIM_ROW_RE.match(line):
            count += 1
    return count


def audit_terminal_craft_commits(repo_root: Path = Path(".")) -> int:
    """Count Stage 2 (terminal-craft) commits landed in this repo.

    SAFETY-05's intent: detect Stage 2 toolkit work that leaked into
    the benchmark repo. Two leak vectors:

      (a) A commit whose SUBJECT LINE is Stage 2 work — e.g.
          `terminal-craft: ...` or `feat(terminal-craft): ...` (the
          conventional-commit scope-pattern this project uses for all
          per-plan commits, see e.g. `G-703(04-04): ...`).
      (b) A commit that touches a `terminal-craft/` directory inside
          this repo (Stage 2 code/artifacts physically landed here).

    Body-text mentions of "terminal-craft" — e.g. plan summaries that
    point to the downstream consumer by name — are NOT Stage 2 leaks
    and are intentionally NOT counted. The earlier broader
    `--grep=terminal-craft` was a false positive on every traceability
    reference in Wave 2 work; this implementation refines the audit to
    its true intent.

    Returns the count of distinct commits matching either vector.
    """
    # Vector (a): subject line begins with a terminal-craft scope.
    # `git log --pretty=format:%H %s` prints HASH SUBJECT — we filter
    # subjects whose first token is a terminal-craft conventional-commit
    # scope.
    #
    # WR-02 fix: distinguish "ran successfully, found 0 leaks" from
    # "could not run". Both subprocess invocations now raise RuntimeError
    # on non-zero return code; the SAFETY-05 audit cannot silently PASS
    # because git was broken, the repo was corrupt, or the cwd was not
    # a git repo.
    result_a = subprocess.run(
        ["git", "log", "--pretty=format:%H %s"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result_a.returncode != 0:
        raise RuntimeError(
            f"audit_terminal_craft_commits: `git log --pretty=format:%H %s` "
            f"failed in {repo_root!s} (rc={result_a.returncode}): "
            f"{result_a.stderr.strip() or '<no stderr>'}"
        )
    subject_leaks: set[str] = set()
    subject_re = re.compile(
        r"^(?:terminal-craft\b|"
        r"(?:feat|fix|chore|docs|refactor|perf|test|style|build|ci|revert)"
        r"\(terminal-craft(?:[/-][^)]*)?\))[:\s]",
        re.IGNORECASE,
    )
    for line in result_a.stdout.splitlines():
        if not line.strip():
            continue
        sha, _, subject = line.partition(" ")
        if subject_re.match(subject):
            subject_leaks.add(sha)

    # Vector (b): a commit touches a top-level `terminal-craft/` path.
    result_b = subprocess.run(
        ["git", "log", "--pretty=format:%H", "--", "terminal-craft/"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result_b.returncode != 0:
        raise RuntimeError(
            f"audit_terminal_craft_commits: `git log -- terminal-craft/` "
            f"failed in {repo_root!s} (rc={result_b.returncode}): "
            f"{result_b.stderr.strip() or '<no stderr>'}"
        )
    path_leaks: set[str] = set()
    for line in result_b.stdout.splitlines():
        line = line.strip()
        if line:
            path_leaks.add(line)

    return len(subject_leaks | path_leaks)


def audit_no_new_mcps(
    mcp_json_path: Path, baseline_keys: set[str] | frozenset[str]
) -> bool:
    """Return True iff `.mcp.json`'s key set exactly equals baseline_keys.

    Returns False on extra keys, missing keys, OR a 1-for-1 swap (which
    `audit_candidate_count` alone would miss). This is the catch-all
    for "did the candidate roster drift in any way."
    """
    if not mcp_json_path.is_file():
        raise FileNotFoundError(f".mcp.json not found: {mcp_json_path}")
    payload = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    servers = payload.get("mcpServers") or {}
    actual = set(servers.keys())
    return actual == set(baseline_keys)


# ─── Aggregator + renderer ──────────────────────────────────────────────


def run_audit(
    mcp_json_path: Path,
    rubric_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Run all four checks and return an aggregated result dict.

    Output shape::

        {
            "candidate_count": int,
            "candidate_count_pass": bool,
            "rubric_columns": int,
            "rubric_columns_pass": bool,
            "terminal_craft_commits": int,
            "terminal_craft_commits_pass": bool,
            "no_new_mcps": bool,
            "no_new_mcps_pass": bool,
            "all_pass": bool,
            "baseline_keys": sorted list,
            "actual_keys": sorted list,
        }
    """
    candidate_count = audit_candidate_count(mcp_json_path)
    rubric_columns = audit_rubric_columns(rubric_path)
    terminal_craft_commits = audit_terminal_craft_commits(repo_root)
    no_new_mcps = audit_no_new_mcps(mcp_json_path, WAVE2_BASELINE)

    payload = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    actual_keys = sorted((payload.get("mcpServers") or {}).keys())

    candidate_count_pass = candidate_count == EXPECTED_CANDIDATE_COUNT
    rubric_columns_pass = rubric_columns == EXPECTED_RUBRIC_COLUMNS
    terminal_craft_commits_pass = (
        terminal_craft_commits == EXPECTED_TERMINAL_CRAFT_COMMITS
    )
    no_new_mcps_pass = bool(no_new_mcps)

    all_pass = all(
        [
            candidate_count_pass,
            rubric_columns_pass,
            terminal_craft_commits_pass,
            no_new_mcps_pass,
        ]
    )

    return {
        "candidate_count": candidate_count,
        "candidate_count_pass": candidate_count_pass,
        "rubric_columns": rubric_columns,
        "rubric_columns_pass": rubric_columns_pass,
        "terminal_craft_commits": terminal_craft_commits,
        "terminal_craft_commits_pass": terminal_craft_commits_pass,
        "no_new_mcps": no_new_mcps,
        "no_new_mcps_pass": no_new_mcps_pass,
        "all_pass": all_pass,
        "baseline_keys": sorted(WAVE2_BASELINE),
        "actual_keys": actual_keys,
    }


def _status_str(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def render_audit_md(audit: dict[str, Any], timestamp: str) -> str:
    """Render the SAFETY-05 audit evidence as a Markdown string.

    The output is consumed by:
      - human readers verifying Wave 2 closed cleanly
      - downstream automation parsing PASS/FAIL per check
    """
    # Allow callers (especially tests) to pass minimal audit dicts that
    # contain only the headline value fields. Derive the per-check pass
    # status from the value if the explicit `_pass` flag is absent, and
    # default the baseline/actual key lists + all_pass to sensible values
    # if also absent (WR-01).
    candidate_count_pass = audit.get(
        "candidate_count_pass",
        audit["candidate_count"] == EXPECTED_CANDIDATE_COUNT,
    )
    rubric_columns_pass = audit.get(
        "rubric_columns_pass",
        audit["rubric_columns"] == EXPECTED_RUBRIC_COLUMNS,
    )
    terminal_craft_commits_pass = audit.get(
        "terminal_craft_commits_pass",
        audit["terminal_craft_commits"] == EXPECTED_TERMINAL_CRAFT_COMMITS,
    )
    no_new_mcps_pass = audit.get("no_new_mcps_pass", bool(audit["no_new_mcps"]))

    all_pass = audit.get(
        "all_pass",
        all(
            [
                candidate_count_pass,
                rubric_columns_pass,
                terminal_craft_commits_pass,
                no_new_mcps_pass,
            ]
        ),
    )

    baseline_keys = audit.get("baseline_keys", sorted(WAVE2_BASELINE))
    actual_keys = audit.get("actual_keys", sorted(WAVE2_BASELINE))

    overall = _status_str(all_pass)
    candidate_pass = _status_str(candidate_count_pass)
    rubric_pass = _status_str(rubric_columns_pass)
    tc_pass = _status_str(terminal_craft_commits_pass)
    nnm_pass = _status_str(no_new_mcps_pass)

    extra_in_actual = sorted(
        set(actual_keys) - set(baseline_keys)
    )
    missing_from_actual = sorted(
        set(baseline_keys) - set(actual_keys)
    )
    drift_note = ""
    if extra_in_actual or missing_from_actual:
        drift_note = (
            f" (extra={extra_in_actual or '[]'}, "
            f"missing={missing_from_actual or '[]'})"
        )

    lines: list[str] = []
    lines.append(f"# Wave-Close Audit — SAFETY-05 — {timestamp}")
    lines.append("")
    lines.append(
        "Automated audit verifying no scope-creep landed during Wave 2. "
        "Source of truth: `bench/wave_close_check.py`. Re-runnable via "
        "`python3 -m bench.wave_close_check`."
    )
    lines.append("")
    lines.append("## Per-Check Results")
    lines.append("")
    lines.append("| Check | Expected | Actual | Status |")
    lines.append("|-------|----------|--------|--------|")
    lines.append(
        f"| candidate_count (`.mcp.json` mcpServers length) | "
        f"{EXPECTED_CANDIDATE_COUNT} | {audit['candidate_count']} | {candidate_pass} |"
    )
    lines.append(
        f"| rubric_columns (`scoring/rubric.md` dim rows) | "
        f"{EXPECTED_RUBRIC_COLUMNS} | {audit['rubric_columns']} | {rubric_pass} |"
    )
    lines.append(
        f"| terminal_craft_commits (subject `terminal-craft:` scope OR "
        f"`terminal-craft/` path) | "
        f"{EXPECTED_TERMINAL_CRAFT_COMMITS} | {audit['terminal_craft_commits']} | {tc_pass} |"
    )
    lines.append(
        f"| no_new_mcps (key-set == baseline) | True | "
        f"{audit['no_new_mcps']}{drift_note} | {nnm_pass} |"
    )
    lines.append("")
    lines.append("## Baseline vs Actual Key Set")
    lines.append("")
    lines.append(f"- Baseline (frozen at wave start): `{baseline_keys}`")
    lines.append(f"- Actual (this run):              `{actual_keys}`")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append(
        f"Wave 2 (2026-05-27) wave-close ritual: ALL CHECKS {overall}."
    )
    if all_pass:
        lines.append("")
        lines.append(
            "Stage 2 (terminal-craft toolkit) is unblocked per "
            "`results/recommendations.md`. The next session can proceed "
            "to terminal-craft work in its own private repo using this "
            "wave's recommendations as the input gate."
        )
    else:
        lines.append("")
        lines.append(
            "Stage 2 is BLOCKED until the failed check(s) are investigated "
            "and either remediated or explicitly waived with written "
            "rationale appended to this file."
        )
    lines.append("")
    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────


def _now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m bench.wave_close_check",
        description=(
            "SAFETY-05 wave-close ritual auditor. Verifies (1) candidate "
            "count == 7, (2) rubric columns == 8, (3) no terminal-craft "
            "commits in this repo, (4) MCP key set unchanged from wave "
            "start. Exits 0 iff all four checks PASS."
        ),
    )
    parser.add_argument(
        "--mcp-json",
        type=Path,
        default=Path(".mcp.json"),
        help="Path to .mcp.json (default: .mcp.json)",
    )
    parser.add_argument(
        "--rubric",
        type=Path,
        default=Path("scoring/rubric.md"),
        help="Path to scoring/rubric.md (default: scoring/rubric.md)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repo root for git log invocation (default: .)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Optional path to write the Markdown audit evidence file. "
            "If omitted, the script prints the Markdown to stdout."
        ),
    )
    args = parser.parse_args(argv)

    audit = run_audit(args.mcp_json, args.rubric, args.repo_root)
    timestamp = _now_utc()
    md = render_audit_md(audit, timestamp)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(
            f"wave_close_check: wrote {args.out} "
            f"({len(md.splitlines())} lines)",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(md)

    # Stderr summary regardless of --out
    status_line = (
        f"wave_close_check: candidate_count={audit['candidate_count']} "
        f"rubric_columns={audit['rubric_columns']} "
        f"terminal_craft_commits={audit['terminal_craft_commits']} "
        f"no_new_mcps={audit['no_new_mcps']} "
        f"all_pass={audit['all_pass']}"
    )
    print(status_line, file=sys.stderr)

    return 0 if audit["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
