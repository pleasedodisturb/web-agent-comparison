#!/usr/bin/env python3
"""Walk per-MCP evidence directories and emit results/<date>/scores.json.

The aggregator is the bridge between the per-MCP evidence directories
produced by `scripts/run_mcp_session.sh` and the locked
`scoring/score.py` consumer. It reads:

  results/<date>/<mcp>/raw_stream.jsonl  ← Claude session events (01-04)
  results/<date>/<mcp>/raw.jsonl         ← Per-attempt retry records (01-05)
  results/<date>/<mcp>/stage_s{1..8}.*   ← Per-stage outputs / FAILED / NA sentinels
  results/<date>/<mcp>/cold_start.json   ← (stub OK for Phase 1, plan 01-06)
  results/<date>/<mcp>/tokens.json       ← (stub OK for Phase 1, plan 01-06)
  results/<date>/<mcp>/orphan_audit.log  ← Process-group leak audit (01-04)
  results/<date>/<mcp>/transcript.md     ← Human-readable session text

And emits:

  results/<date>/scores.json             ← In score.py's shape, PLUS additive
                                            `attempts` and `attribution` fields

The output is BACKWARDS-COMPATIBLE with `scoring/score.py` — score.py
reads `scores` + `stages` and ignores unknown fields. The additive
fields (`attempts` + `attribution`) are consumed by report-side tooling
that wants per-stage `n/3` and per-dimension failure tags.

Usage
-----
    python scripts/aggregate_scores.py results/2026-05-22/

The script also accepts a single `<mcp>` directory for ad-hoc testing,
but the canonical entry point is the date-level directory which
contains one subdirectory per MCP.

N/A semantics
-------------
Read-only MCPs (`lightpanda`, `firecrawl`) score `"N/A"` (string, not 0)
on `interaction_depth` and on stages S4-S8. `scripts/score_with_na.py`
then drops those cells from the weighted denominator. The list of
read-only MCPs is hard-coded here because it's a candidate-category
property, not a per-run discovery.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from bench.failure_taxonomy import FailureTag, attribute_failure  # noqa: E402

# ─── MCP categorization ────────────────────────────────────────────────
#
# Read-only MCPs don't do interactive stages (S4-S8) by category. They
# score N/A on those — not zero. The list is a fairness-policy
# statement, sourced from PROJECT.md's stack-research table:
#
#   lightpanda: Zig JS engine, fetch-mode read-only
#   firecrawl:  cloud markdown scraper, no interactive surface

READ_ONLY_MCPS = {"lightpanda", "firecrawl"}

INTERACTIVE_STAGES = ("S4", "S5", "S6", "S7", "S8")
READ_ONLY_STAGES = ("S1", "S2", "S3")
ALL_STAGES = READ_ONLY_STAGES + INTERACTIVE_STAGES

# Rubric thresholds — keep in sync with scoring/rubric.md.
# We honour the locked rubric but derive numeric scores from artifacts
# the harness produces.

SPEED_THRESHOLDS_S = (10.0, 30.0)        # <10s → 10; 10-30s → 5; >30s → 0
TOKEN_THRESHOLDS_BYTES = (10_240, 51_200)  # <10KB → 10; 10-50KB → 5; >50KB → 0


# ─── Helpers — read each evidence file ─────────────────────────────────


def _safe_read_json(path: Path) -> dict:
    """Return parsed JSON or {} if the file is missing / unreadable."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _read_jsonl(path: Path) -> list[dict]:
    """Return a list of JSON objects, one per line. Tolerates bad lines."""
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _stage_artifact_exists(mcp_dir: Path, stage: str) -> bool:
    """A stage 'passed' if any artifact named stage_s<N>.* exists.

    Recognized extensions: yml, md, png, txt, json. A sentinel file
    `stage_s<N>.FAILED` indicates the stage was attempted but failed;
    `stage_s<N>.NA` indicates it was N/A by design (read-only MCPs).
    """
    stage_num = stage.lower()  # "s1"
    for ext in ("yml", "md", "png", "txt", "json"):
        if (mcp_dir / f"stage_{stage_num}.{ext}").exists():
            return True
    return False


def _stage_status(mcp_dir: Path, stage: str) -> str:
    """One of: PASS | FAIL | NA | UNTESTED.

    PASS: an artifact file exists for the stage.
    FAIL: a sentinel `stage_s<N>.FAILED` file exists.
    NA:   a sentinel `stage_s<N>.NA` file exists.
    UNTESTED: none of the above.
    """
    stage_num = stage.lower()
    if (mcp_dir / f"stage_{stage_num}.NA").exists():
        return "NA"
    if (mcp_dir / f"stage_{stage_num}.FAILED").exists():
        return "FAIL"
    if _stage_artifact_exists(mcp_dir, stage):
        return "PASS"
    return "UNTESTED"


def _attempts_by_stage(mcp_dir: Path) -> dict[str, list[dict]]:
    """Group per-attempt records by stage.

    `raw.jsonl` may carry a `stage` field on each record (set by the
    per-stage runner). If absent, all records are bucketed under the
    catch-all key `"_unstaged"`.
    """
    raw_path = mcp_dir / "raw.jsonl"
    records = _read_jsonl(raw_path)
    by_stage: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        stage = rec.get("stage", "_unstaged")
        by_stage[str(stage).upper()].append(rec)
    return dict(by_stage)


def _summarize_attempts(records: list[dict]) -> dict[str, Any]:
    """Return `{passes, total, tag}` for one stage's attempts.

    `tag` is the FailureTag of the LAST failure (or None if all passed),
    suitable for the matrix's notes column.
    """
    if not records:
        return {"passes": 0, "total": 0, "tag": None}
    passes = sum(1 for r in records if r.get("passed"))
    total = len(records)
    last_failure_tag = None
    for r in records:
        if not r.get("passed"):
            last_failure_tag = r.get("tag")
    return {"passes": passes, "total": total, "tag": last_failure_tag}


# ─── Dimension scorers ─────────────────────────────────────────────────
#
# Each scorer returns either an int 0-10 OR the string "N/A". The
# aggregator threads the choice between number and "N/A" through to the
# emitted scores.json.


def _score_speed(cold_start: dict) -> int | str:
    """Speed dimension from cold_start.json's t_first_useful (seconds).

    Rubric: <10s → 10, 10-30s → 5, >30s → 0.
    Returns 5 (the partial-credit default) if cold_start.json is empty
    or stubbed (`{"deferred": "..."}`) — we don't want to dock a
    candidate on missing measurement during Phase 1.
    """
    if not cold_start or cold_start.get("deferred"):
        return 5  # Phase 1 stub — neutral
    t_first = cold_start.get("t_first_useful_s") or cold_start.get("t_first_useful")
    if not isinstance(t_first, (int, float)):
        return 5
    if t_first < SPEED_THRESHOLDS_S[0]:
        return 10
    if t_first < SPEED_THRESHOLDS_S[1]:
        return 5
    return 0


def _score_token_efficiency(tokens: dict) -> int | str:
    """Token efficiency from tokens.json's payload bytes (the headline scope).

    Rubric: <10KB → 10, 10-50KB → 5, >50KB → 0.
    Returns 5 (partial-credit default) if the file is empty or stubbed.
    """
    if not tokens or tokens.get("deferred"):
        return 5
    payload = tokens.get("payload_bytes") or tokens.get("payload")
    if not isinstance(payload, (int, float)):
        return 5
    if payload < TOKEN_THRESHOLDS_BYTES[0]:
        return 10
    if payload < TOKEN_THRESHOLDS_BYTES[1]:
        return 5
    return 0


def _score_reliability(stage_statuses: dict[str, str], orphan_survivors: int) -> int:
    """Reliability from per-stage PASS rate and orphan-process survivors.

    Start at 10. Each non-PASS stage among the stages this MCP CAN
    attempt docks 1. Orphan-process survivors dock 1 (Phase 1 logs-and-
    continues per plan 01-04 but the signal still goes here).
    """
    # Stages the MCP actually attempted (PASS|FAIL|NA — we exclude UNTESTED
    # because UNTESTED means we never tried, which is a harness issue not
    # a reliability issue).
    attempted = [s for s, st in stage_statuses.items() if st != "UNTESTED"]
    if not attempted:
        return 0
    fails = sum(1 for s in attempted if stage_statuses[s] == "FAIL")
    score = 10 - fails
    if orphan_survivors > 0:
        score -= 1
    return max(0, score)


def _score_data_quality(stage_statuses: dict[str, str]) -> int:
    """Data quality from S1-S3 (read-only) PASS rate.

    All 3 PASS → 10; 2 PASS → 7; 1 PASS → 3; 0 PASS → 0. (Smooth-ish curve
    that matches the rubric's "all fields present" vs "core fields" vs
    "missing fields" anchors.)
    """
    passes = sum(1 for s in READ_ONLY_STAGES if stage_statuses.get(s) == "PASS")
    return {0: 0, 1: 3, 2: 7, 3: 10}[passes]


def _score_interaction_depth(
    mcp_name: str, stage_statuses: dict[str, str]
) -> int | str:
    """Interaction depth from S4-S8 PASS rate, OR N/A for read-only MCPs."""
    if mcp_name in READ_ONLY_MCPS:
        return "N/A"
    passes = sum(1 for s in INTERACTIVE_STAGES if stage_statuses.get(s) == "PASS")
    return {0: 0, 1: 2, 2: 4, 3: 6, 4: 8, 5: 10}[passes]


def _score_js_rendering(stage_statuses: dict[str, str]) -> int:
    """JS rendering — driven by S2 (Ashby React SPA) outcome.

    PASS → 10 (full SPA), FAIL → 2 (no JS), NA → 5 (neutral),
    UNTESTED → 5 (neutral).
    """
    s2 = stage_statuses.get("S2", "UNTESTED")
    return {"PASS": 10, "FAIL": 2, "NA": 5, "UNTESTED": 5}[s2]


def _score_setup_complexity(mcp_dir: Path) -> int:
    """Setup complexity — neutral default, can be refined per-MCP later.

    Returns 7 (partial-credit-plus) until plan 01-07 wires real signals
    from `versions.json` / `MACHINE.md`. Encoded so the matrix renders
    plausible values during Phase 1 calibration.
    """
    # Future hook: read versions.json and dock points per manual step.
    return 7


def _score_error_handling(transcript: str) -> int:
    """Error handling from transcript `[error]` / `retry` / `fail` density.

    Rough heuristic: fewer than 3 error-tagged lines → 8; 3-10 → 5;
    >10 → 2. Neutral 7 if the transcript is empty.
    """
    if not transcript:
        return 7
    pattern = re.compile(r"\b(error|retry|fail(?:ed|ure)?)\b", re.IGNORECASE)
    hits = len(pattern.findall(transcript))
    if hits < 3:
        return 8
    if hits < 10:
        return 5
    return 2


# ─── Per-MCP aggregator ────────────────────────────────────────────────


def _orphan_survivor_count(mcp_dir: Path) -> int:
    """Count orphan-process survivor lines from orphan_audit.log.

    Looks for either:
      - `.harness_leaked` sentinel file (created by run_mcp_session.sh
        when the audit reported survivors), OR
      - lines in orphan_audit.log that explicitly say "leaked" or
        "SURVIVED" (uppercase / verbatim — the audit module writes those
        keys verbatim per `bench/orphan_audit.py`).

    Lines that merely contain the word "orphan" (e.g. "orphan_audit
    clean") do NOT count — that would false-positive on the success
    case.
    """
    if (mcp_dir / ".harness_leaked").exists():
        return 1
    log = mcp_dir / "orphan_audit.log"
    if not log.exists():
        return 0
    text = log.read_text(encoding="utf-8", errors="replace")
    # Stricter regex: word "leaked" anywhere, or capitalized SURVIVED.
    return len(re.findall(r"\b(?:leaked|SURVIVED)\b", text))


def aggregate_mcp(mcp_dir: Path) -> dict[str, Any]:
    """Return the scores.json entry for one MCP directory."""
    mcp_name = mcp_dir.name

    # Per-stage statuses (PASS/FAIL/NA/UNTESTED).
    stage_statuses = {s: _stage_status(mcp_dir, s) for s in ALL_STAGES}

    # For read-only MCPs, stamp the interactive stages as NA explicitly
    # so downstream readers don't see UNTESTED for stages that aren't
    # supposed to be tested.
    if mcp_name in READ_ONLY_MCPS:
        for s in INTERACTIVE_STAGES:
            if stage_statuses[s] == "UNTESTED":
                stage_statuses[s] = "NA"

    # Per-attempt records (from bench.transient.write_attempts_to_jsonl).
    attempts_by_stage = _attempts_by_stage(mcp_dir)
    attempts_summary = {
        s: _summarize_attempts(attempts_by_stage.get(s, []))
        for s in ALL_STAGES
    }

    # Evidence files.
    cold_start = _safe_read_json(mcp_dir / "cold_start.json")
    tokens = _safe_read_json(mcp_dir / "tokens.json")
    transcript_path = mcp_dir / "transcript.md"
    transcript_text = (
        transcript_path.read_text(encoding="utf-8", errors="replace")
        if transcript_path.exists()
        else ""
    )
    orphan_survivors = _orphan_survivor_count(mcp_dir)

    # Score each dimension.
    scores: dict[str, Any] = {
        "data_quality": _score_data_quality(stage_statuses),
        "reliability": _score_reliability(stage_statuses, orphan_survivors),
        "speed": _score_speed(cold_start),
        "token_efficiency": _score_token_efficiency(tokens),
        "interaction_depth": _score_interaction_depth(mcp_name, stage_statuses),
        "js_rendering": _score_js_rendering(stage_statuses),
        "setup_complexity": _score_setup_complexity(mcp_dir),
        "error_handling": _score_error_handling(transcript_text),
    }

    # Failure attribution: for any sub-rubric score < 5 that isn't N/A,
    # tag it with the most-recent failure category for the dimension's
    # closest-related stage.
    attribution: dict[str, str] = {}
    dim_to_stage = {
        "data_quality": "S1",
        "reliability": "S1",   # any failed stage; use S1 as proxy
        "interaction_depth": "S4",
        "js_rendering": "S2",
    }
    for dim, score in scores.items():
        if score == "N/A":
            continue
        if not isinstance(score, (int, float)):
            continue
        if score >= 5:
            continue
        # Find a related stage's last failure tag, fallback to TOOL_BUG.
        stage = dim_to_stage.get(dim)
        tag = None
        if stage and attempts_summary.get(stage, {}).get("tag"):
            tag = attempts_summary[stage]["tag"]
        if not tag:
            tag = FailureTag.TOOL_BUG.value
        attribution[dim] = tag

    # Render the stages dict score.py expects.
    stages_field = {
        s: _render_stage_text(stage_statuses[s], attempts_summary[s])
        for s in ALL_STAGES
    }

    return {
        "scores": scores,
        "stages": stages_field,
        "attempts": attempts_summary,
        "attribution": attribution,
    }


def _render_stage_text(status: str, attempt: dict[str, Any]) -> str:
    """Compose the per-cell string score.py prints in its stage matrix.

    Examples:
      PASS (3/3)         — all 3 attempts passed
      PASS (2/3 transient) — passed majority, one transient failure
      FAIL (0/3 tool-bug)
      N/A
      UNTESTED
    """
    passes = attempt.get("passes", 0)
    total = attempt.get("total", 0)
    tag = attempt.get("tag")
    suffix_parts: list[str] = []
    if total > 0:
        suffix_parts.append(f"{passes}/{total}")
    if tag:
        suffix_parts.append(str(tag))
    suffix = f" ({' '.join(suffix_parts)})" if suffix_parts else ""

    if status == "NA":
        return "N/A"
    return f"{status}{suffix}"


# ─── Top-level walker ──────────────────────────────────────────────────


def aggregate_date_dir(date_dir: Path) -> dict[str, Any]:
    """Walk every subdirectory under `date_dir` and aggregate per-MCP."""
    if not date_dir.exists() or not date_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {date_dir}")

    results: dict[str, Any] = {}
    for entry in sorted(date_dir.iterdir()):
        if not entry.is_dir():
            continue
        # Skip hidden / metadata dirs.
        if entry.name.startswith("."):
            continue
        results[entry.name] = aggregate_mcp(entry)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate per-MCP evidence dirs into a scores.json.",
    )
    parser.add_argument(
        "date_dir",
        type=Path,
        help="Path to results/<date>/ with one subdir per MCP",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: <date_dir>/scores.json)",
    )
    args = parser.parse_args()

    date_dir: Path = args.date_dir
    out_path: Path = args.out or (date_dir / "scores.json")

    results = aggregate_date_dir(date_dir)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")

    print(f"==> wrote {out_path} ({len(results)} MCP(s))", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
