#!/usr/bin/env python3
"""N/A-aware composite wrapper around scoring/score.py.

`scoring/score.py` is SACROSANCT — preserving its 2026-03 comparability
contract means we cannot change how it computes composites. But the
fairness layer for Phase 2 requires that read-only MCPs (lightpanda,
firecrawl) score `N/A` on interactive stages (S4-S8) AND that those
N/A cells DROP from the weighted denominator rather than counting as
zero. score.py's `compute_composite` uses `scores.get(dim, 0)` which
treats `"N/A"` as zero by default — that's the part this wrapper
overrides.

The wrapper imports DIMENSIONS from score.py (so the weights stay
single-sourced) and recomputes the composite locally with N/A-aware
semantics. The output format mirrors score.py's so the published
report stays consistent.

Usage
-----
    python scripts/score_with_na.py                  # default results/scores.json
    python scripts/score_with_na.py path/to/scores.json

CLI mirrors `scoring/score.py`. For rows with no N/A cells (e.g.
Phase 1's Playwright calibration), this produces IDENTICAL composites
to score.py — the N/A logic is dormant and only activates when a row
carries an explicit `"N/A"` value.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Import from scoring/score.py — DIMENSIONS is the single source of truth
# for weights. We add the repo root to sys.path so this script can be
# run directly (`python scripts/score_with_na.py`) without requiring
# `pip install -e .` or a package layout.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scoring.score import DIMENSIONS  # noqa: E402  — sys.path tweak above

# Sentinel string the aggregator writes into scores.json for N/A cells.
# Anything matching this (case-insensitive) gets dropped from the
# denominator. We also treat Python None the same way for callers who
# pre-process scores.json before feeding it here.
NA_SENTINEL = "N/A"


def _is_na(value: object) -> bool:
    """Return True if `value` represents a missing-by-design measurement."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip().upper() in {"N/A", "NA", "N_A"}:
        return True
    return False


def compute_na_aware_composite(scores: dict) -> float:
    """Weighted composite that drops N/A cells from the denominator.

    For each dimension in DIMENSIONS:
      - If the score is N/A (per `_is_na`), skip — does not contribute
        to numerator or denominator.
      - If the score is a number, add `value * weight` to the numerator
        and `weight` to the denominator.
      - If the score is missing from the dict entirely, treat it as
        N/A (skip) — matches `score.py`'s `scores.get(dim, 0)` behaviour
        EXCEPT we drop rather than zero-fill. This is the intentional
        deviation that justifies this wrapper's existence.

    Returns 0.0 if every dimension is N/A (degenerate case; total weight
    is zero).
    """
    weighted = 0.0
    total_weight = 0.0

    for dim, meta in DIMENSIONS.items():
        if dim not in scores:
            # Missing key — drop (treat as N/A).
            continue
        v = scores[dim]
        if _is_na(v):
            continue
        try:
            weighted += float(v) * meta["weight"]
        except (TypeError, ValueError):
            # Non-numeric, non-N/A → treat as N/A to be safe and surface
            # the bad row via the printed output.
            continue
        total_weight += meta["weight"]

    if total_weight == 0:
        return 0.0
    return round(weighted / total_weight, 2)


def format_comparison_table(results: dict) -> str:
    """N/A-aware variant of score.format_comparison_table.

    Identical layout to score.py — readers should see the same shape
    whether they ran score.py or score_with_na.py. The difference is
    only in the composite row when N/A cells are present.
    """
    agents = list(results.keys())
    header = "| Dimension (weight) | " + " | ".join(agents) + " |"
    sep = "|" + "---|" * (len(agents) + 1)

    rows = [header, sep]
    for dim, meta in DIMENSIONS.items():
        label = f"**{meta['label']}** ({meta['weight']}x)"
        vals = " | ".join(
            str(results[a]["scores"].get(dim, "N/A")) for a in agents
        )
        rows.append(f"| {label} | {vals} |")

    # N/A-aware composite row.
    composites = " | ".join(
        f"**{compute_na_aware_composite(results[a]['scores'])}**" for a in agents
    )
    rows.append(f"| **Weighted Composite (N/A-aware)** | {composites} |")

    return "\n".join(rows)


def format_stage_matrix(results: dict) -> str:
    """Pass-through that mirrors score.format_stage_matrix layout.

    Identical to score.py — stages dict already uses 'N/A' strings, so
    no special handling needed here. We re-implement (not import) to
    keep score.py untouched if its formatting ever evolves.
    """
    agents = list(results.keys())
    stages = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]

    header = "| Stage | " + " | ".join(agents) + " |"
    sep = "|" + "---|" * (len(agents) + 1)

    rows = [header, sep]
    for stage in stages:
        vals = " | ".join(
            str(results[a].get("stages", {}).get(stage, "N/A")) for a in agents
        )
        rows.append(f"| {stage} | {vals} |")

    return "\n".join(rows)


def main() -> None:
    default_path = _REPO_ROOT / "results" / "scores.json"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path

    if not path.exists():
        print(f"No results file at {path}")
        print("Expected JSON format (same as scoring/score.py):")
        print(json.dumps({
            "AgentName": {
                "scores": {dim: 0 for dim in DIMENSIONS},
                "stages": {f"S{i}": "PASS/FAIL/N_A" for i in range(1, 9)},
            }
        }, indent=2))
        sys.exit(1)

    results = json.loads(path.read_text())

    print("## Scoring Comparison (N/A-aware)\n")
    print(format_comparison_table(results))
    print()
    print("## Stage Results\n")
    print(format_stage_matrix(results))

    # N/A-aware ranking.
    ranked = sorted(
        results.items(),
        key=lambda x: compute_na_aware_composite(x[1]["scores"]),
        reverse=True,
    )
    print("\n## Final Ranking (N/A-aware)\n")
    for i, (agent, data) in enumerate(ranked, 1):
        score = compute_na_aware_composite(data["scores"])
        print(f"{i}. **{agent}** — {score}/10")


if __name__ == "__main__":
    main()
