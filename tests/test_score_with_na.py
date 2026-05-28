"""Tests for scripts/score_with_na.py.

Proves the N/A-aware wrapper is doing real math — not just shadowing
scoring/score.py. The contract is:

  - Rows with NO N/A cells: same composite as score.py.
  - Rows WITH N/A cells: the N/A cell drops from the denominator,
    NOT counted as zero (which is what score.py's .get(dim, 0) does).

Phase 1's calibration (Playwright) hits Test A — Phase 2's read-only
MCPs (lightpanda, firecrawl) hit Test B.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# The wrapper under test. We import via importlib because the script
# lives at scripts/score_with_na.py and isn't a regular package member.
import importlib.util

_NA_PATH = _REPO_ROOT / "scripts" / "score_with_na.py"
_spec = importlib.util.spec_from_file_location("score_with_na", _NA_PATH)
score_with_na = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score_with_na)

from scoring.score import DIMENSIONS, compute_composite  # noqa: E402


class TestNoNACellsMatchesScorePy(unittest.TestCase):
    """A row with all 8 dimensions scored produces the SAME composite as score.py."""

    def test_playwright_synthetic_matches_score_py(self) -> None:
        """Test A from PLAN task 8: no N/A cells → identical to score.py."""
        playwright = {
            "data_quality": 10,
            "reliability": 9,
            "speed": 9,
            "token_efficiency": 7,
            "interaction_depth": 10,
            "js_rendering": 10,
            "setup_complexity": 9,
            "error_handling": 8,
        }

        # score.py computes (10*3 + 9*3 + 9*2 + 7*2 + 10*2 + 10*1 + 9*1 + 8*1) / 15
        #                 = (30 + 27 + 18 + 14 + 20 + 10 + 9 + 8) / 15
        #                 = 136 / 15
        #                 = 9.066... → 9.07 rounded
        score_py = compute_composite(playwright)
        na_aware = score_with_na.compute_na_aware_composite(playwright)

        self.assertEqual(score_py, 9.07)
        self.assertEqual(na_aware, 9.07)
        self.assertEqual(score_py, na_aware)


class TestNACellDropsFromDenominator(unittest.TestCase):
    """Test B from PLAN task 8 — the headline N/A-vs-zero math."""

    def test_all_fives_with_one_na_yields_five(self) -> None:
        """8 dims at 5, but interaction_depth=N/A (weight 2). N/A-aware = 5.0; score.py drops to 4.33."""
        synth = {
            "data_quality": 5,
            "reliability": 5,
            "speed": 5,
            "token_efficiency": 5,
            "interaction_depth": "N/A",  # weight=2
            "js_rendering": 5,
            "setup_complexity": 5,
            "error_handling": 5,
        }

        na_aware = score_with_na.compute_na_aware_composite(synth)

        # N/A-aware: (5*3 + 5*3 + 5*2 + 5*2 + 5*1 + 5*1 + 5*1) / 13 = 65/13 = 5.00
        # The dropped weight-2 dim leaves denom=13 (15-2).
        self.assertEqual(na_aware, 5.0)

        # score.py's behaviour on a literal "N/A" string in the scores dict
        # is UNDEFINED — `scores.get(dim, 0)` returns "N/A" (key present), then
        # `"N/A" * 2 = "N/AN/A"` (string-repeat), then `sum()` blows up with
        # TypeError. Demonstrate that exact failure so future readers see the
        # wrapper's reason to exist:
        with self.assertRaises(TypeError):
            compute_composite(synth)

        # The real Phase-2 path WITHOUT this wrapper would be: aggregator strips
        # N/A dims before passing to score.py. In that case score.py uses
        # .get(dim, 0) → 0, computing (5*13)/15 = 4.333... = 4.33. THAT is the
        # mathematical bias the N/A wrapper exists to correct.
        synth_with_na_stripped = {
            k: v for k, v in synth.items() if v != "N/A"
        }
        score_py_with_strip = compute_composite(synth_with_na_stripped)

        # score.py treats the missing dim as 0 → composite ≠ 5.0
        self.assertAlmostEqual(score_py_with_strip, 4.33, places=2)
        self.assertNotEqual(na_aware, score_py_with_strip)

        # Sanity: the spread between the two is exactly the bias the N/A
        # wrapper exists to correct.
        self.assertGreater(na_aware - score_py_with_strip, 0.5)

    def test_lightpanda_phase2_synthetic(self) -> None:
        """Lightpanda-like row: S4-S8 → interaction_depth=N/A.

        Lightpanda is js-light: it doesn't do interactive stages by design.
        Its interaction_depth slot is the canonical Phase 2 N/A cell.
        """
        lightpanda = {
            "data_quality": 7,
            "reliability": 7,
            "speed": 10,
            "token_efficiency": 6,
            "interaction_depth": "N/A",  # weight=2 drops from denom
            "js_rendering": 2,
            "setup_complexity": 7,
            "error_handling": 5,
        }

        na_aware = score_with_na.compute_na_aware_composite(lightpanda)
        # numerator = 7*3 + 7*3 + 10*2 + 6*2 + 2*1 + 7*1 + 5*1 = 21+21+20+12+2+7+5 = 88
        # denom = 15 - 2 = 13
        # composite = 88/13 = 6.769... → 6.77
        self.assertAlmostEqual(na_aware, 6.77, places=2)

    def test_missing_key_treated_as_na(self) -> None:
        """A dimension missing from the scores dict drops from the denominator.

        Matches score.py's `.get(dim, 0)` shape EXCEPT we drop instead of
        zero-fill. The wrapper's job.
        """
        partial = {
            "data_quality": 8,
            "reliability": 8,
            # speed missing entirely
            "token_efficiency": 8,
            "interaction_depth": 8,
            "js_rendering": 8,
            "setup_complexity": 8,
            "error_handling": 8,
        }
        # Missing 'speed' (weight 2) drops; remaining = 13 weight @ 8 = 8.0
        na_aware = score_with_na.compute_na_aware_composite(partial)
        self.assertEqual(na_aware, 8.0)

    def test_all_na_returns_zero(self) -> None:
        """Degenerate case: every dim N/A → 0.0 (no signal to score)."""
        nothing = {dim: "N/A" for dim in DIMENSIONS}
        self.assertEqual(score_with_na.compute_na_aware_composite(nothing), 0.0)

    def test_na_case_insensitive(self) -> None:
        """Accept 'n/a', 'N/A', 'NA', 'n_a', None — all sentinels for drop."""
        for sentinel in ["N/A", "n/a", "NA", "n_a"]:
            scores = {dim: 5 for dim in DIMENSIONS}
            scores["interaction_depth"] = sentinel
            self.assertEqual(
                score_with_na.compute_na_aware_composite(scores),
                5.0,
                f"sentinel {sentinel!r} did not drop from denom",
            )

        # None also counts
        scores = {dim: 5 for dim in DIMENSIONS}
        scores["interaction_depth"] = None
        self.assertEqual(score_with_na.compute_na_aware_composite(scores), 5.0)


class TestRealResultsJsonStillScores(unittest.TestCase):
    """End-to-end: feed the existing results/scores.json through the wrapper.

    Confirms that the wrapper handles the 2026-03 published shape without
    blowing up — the playwright row has no N/A cells so its composite must
    match score.py's exactly.
    """

    def test_existing_scores_json_playwright_composite(self) -> None:
        import json

        path = _REPO_ROOT / "results" / "scores.json"
        results = json.loads(path.read_text())

        # The "Playwright MCP" row in the existing file has 8 numeric scores.
        playwright = results["Playwright MCP"]["scores"]

        score_py = compute_composite(playwright)
        na_aware = score_with_na.compute_na_aware_composite(playwright)
        self.assertEqual(score_py, na_aware)
        # Calibration target reference: 2026-03-31 wave published 9.07.
        # Confirm at least one of these matches that target so the test
        # fails if score.py drifts.
        self.assertEqual(score_py, 9.07)


class TestFormatTableMirrorsScorePy(unittest.TestCase):
    """The N/A-aware comparison table preserves score.py's layout."""

    def test_table_has_header_and_composite_row(self) -> None:
        results = {
            "TestAgent": {
                "scores": {dim: 5 for dim in DIMENSIONS},
                "stages": {f"S{i}": "PASS" for i in range(1, 9)},
            }
        }
        table = score_with_na.format_comparison_table(results)
        self.assertIn("Dimension (weight)", table)
        self.assertIn("TestAgent", table)
        self.assertIn("Weighted Composite (N/A-aware)", table)

    def test_stage_matrix_renders_na_strings(self) -> None:
        results = {
            "Lightpanda": {
                "scores": {},
                "stages": {
                    "S1": "PASS",
                    "S4": "N/A",
                    "S5": "N/A",
                },
            }
        }
        m = score_with_na.format_stage_matrix(results)
        self.assertIn("Lightpanda", m)
        self.assertIn("N/A", m)


if __name__ == "__main__":
    unittest.main()
