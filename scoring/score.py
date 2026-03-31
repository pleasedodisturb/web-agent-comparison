#!/usr/bin/env python3
"""Compute weighted scores for web agent comparison.

Usage:
    python3 score.py results.json
    python3 score.py  # uses default path
"""

import json
import sys
from pathlib import Path

DIMENSIONS = {
    "data_quality":      {"weight": 3, "label": "Data Quality"},
    "reliability":       {"weight": 3, "label": "Reliability"},
    "speed":             {"weight": 2, "label": "Speed"},
    "token_efficiency":  {"weight": 2, "label": "Token Efficiency"},
    "interaction_depth": {"weight": 2, "label": "Interaction Depth"},
    "js_rendering":      {"weight": 1, "label": "JS Rendering"},
    "setup_complexity":  {"weight": 1, "label": "Setup Complexity"},
    "error_handling":    {"weight": 1, "label": "Error Handling"},
}

TOTAL_WEIGHT = sum(d["weight"] for d in DIMENSIONS.values())


def compute_composite(scores: dict[str, float]) -> float:
    weighted = sum(
        scores.get(dim, 0) * meta["weight"]
        for dim, meta in DIMENSIONS.items()
    )
    return round(weighted / TOTAL_WEIGHT, 2)


def format_comparison_table(results: dict) -> str:
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

    # Composite row
    composites = " | ".join(
        f"**{compute_composite(results[a]['scores'])}**" for a in agents
    )
    rows.append(f"| **Weighted Composite** | {composites} |")

    return "\n".join(rows)


def format_stage_matrix(results: dict) -> str:
    agents = list(results.keys())
    stages = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]

    header = "| Stage | " + " | ".join(agents) + " |"
    sep = "|" + "---|" * (len(agents) + 1)

    rows = [header, sep]
    for stage in stages:
        vals = " | ".join(
            results[a]["stages"].get(stage, "N/A") for a in agents
        )
        rows.append(f"| {stage} | {vals} |")

    return "\n".join(rows)


def main():
    default_path = Path(__file__).parent.parent / "results" / "scores.json"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path

    if not path.exists():
        print(f"No results file at {path}")
        print("Expected JSON format:")
        print(json.dumps({
            "AgentName": {
                "scores": {dim: 0 for dim in DIMENSIONS},
                "stages": {f"S{i}": "PASS/FAIL/N_A" for i in range(1, 9)},
            }
        }, indent=2))
        sys.exit(1)

    results = json.loads(path.read_text())

    print("## Scoring Comparison\n")
    print(format_comparison_table(results))
    print()
    print("## Stage Results\n")
    print(format_stage_matrix(results))

    # Ranking
    ranked = sorted(
        results.items(),
        key=lambda x: compute_composite(x[1]["scores"]),
        reverse=True,
    )
    print("\n## Final Ranking\n")
    for i, (agent, data) in enumerate(ranked, 1):
        score = compute_composite(data["scores"])
        print(f"{i}. **{agent}** — {score}/10")


if __name__ == "__main__":
    main()
