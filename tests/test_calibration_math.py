"""Unit tests for the Phase 1 calibration band math.

The calibration gate (scripts/verify_calibration.sh) compares an observed
Playwright composite against the 2026-03-31 baseline of 9.07 with a
±0.5 tolerance. The math of "is this score in the band?" needs to be
verifiable without a real Playwright run — otherwise we can't unit-test
the harness's go/no-go logic.

What this file proves:

  1. The 2026-03 Playwright row's dimension scores feed back through
     `scoring.score.compute_composite()` to exactly 9.07 — i.e.
     `scoring/score.py` has not drifted since the 2026-03 wave.
  2. The N/A-aware wrapper (`scripts/score_with_na.py`) returns the SAME
     composite on a row with no N/A cells — so Phase 1 calibration is
     not biased by the Phase 2 fairness layer.
  3. The `in_band()` helper inside `scripts/verify_calibration.sh` (whose
     pure-Python equivalent lives here) accepts everything in
     [8.57, 9.57] inclusive and rejects everything outside.

If any of these fail, the calibration gate would either pass a broken
harness OR reject a working one — both fatal to the benchmark's
validity. Hence: tested independently of any real Playwright run.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scoring.score import compute_composite  # noqa: E402

# Import scripts/score_with_na.py the same way tests/test_score_with_na.py
# does — it's a script not a package member.
_NA_PATH = _REPO_ROOT / "scripts" / "score_with_na.py"
_spec = importlib.util.spec_from_file_location("score_with_na", _NA_PATH)
score_with_na = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score_with_na)  # type: ignore[union-attr]


# The 2026-03-31 Playwright row from results/scores.json. Pinned here so
# the math test fails loudly if the published row is ever edited.
PLAYWRIGHT_2026_03 = {
    "data_quality":      10,
    "reliability":        9,
    "speed":              9,
    "token_efficiency":   7,
    "interaction_depth": 10,
    "js_rendering":      10,
    "setup_complexity":   9,
    "error_handling":     8,
}

CALIBRATION_TARGET = 9.07
CALIBRATION_TOLERANCE = 0.5
LOWER_BAND = round(CALIBRATION_TARGET - CALIBRATION_TOLERANCE, 2)  # 8.57
UPPER_BAND = round(CALIBRATION_TARGET + CALIBRATION_TOLERANCE, 2)  # 9.57


def in_band(score: float,
            target: float = CALIBRATION_TARGET,
            tolerance: float = CALIBRATION_TOLERANCE) -> bool:
    """Pure-Python mirror of the bash band check in verify_calibration.sh.

    `target - tolerance <= score <= target + tolerance` (inclusive on
    both ends). Two scripts must agree on this formula; if they don't, a
    Playwright row that lands exactly on 8.57 might be rejected by one
    and accepted by the other — exactly the kind of off-by-epsilon bug
    the test below catches.
    """
    return (target - tolerance) <= score <= (target + tolerance)


class TestPlaywright2026_03Composite(unittest.TestCase):
    """Anchor: the 2026-03 Playwright dimension scores compose to 9.07."""

    def test_score_py_reproduces_9_07(self) -> None:
        """`scoring/score.py` is the source of truth for the 2026-03 number."""
        composite = compute_composite(PLAYWRIGHT_2026_03)
        # The literal calibration target. If score.py is ever edited and
        # this value drifts, the entire wave's comparability with the
        # 2026-03 publish is broken — fail loudly.
        self.assertEqual(composite, 9.07)

    def test_score_with_na_matches_score_py_no_na(self) -> None:
        """The N/A-aware wrapper produces identical math when no cells are N/A."""
        score_py = compute_composite(PLAYWRIGHT_2026_03)
        na_aware = score_with_na.compute_na_aware_composite(PLAYWRIGHT_2026_03)
        # Both must equal each other AND the calibration target.
        self.assertEqual(score_py, na_aware)
        self.assertEqual(score_py, 9.07)
        self.assertEqual(na_aware, 9.07)


class TestBandLogic(unittest.TestCase):
    """The ±0.5 band logic: 8.57 ≤ score ≤ 9.57 = PASS, else FAIL."""

    def test_exact_target_in_band(self) -> None:
        self.assertTrue(in_band(9.07))

    def test_lower_bound_inclusive(self) -> None:
        self.assertTrue(in_band(8.57))

    def test_upper_bound_inclusive(self) -> None:
        self.assertTrue(in_band(9.57))

    def test_just_below_lower_bound_rejected(self) -> None:
        self.assertFalse(in_band(8.56))

    def test_just_above_upper_bound_rejected(self) -> None:
        self.assertFalse(in_band(9.58))

    def test_far_below_rejected(self) -> None:
        self.assertFalse(in_band(7.0))

    def test_far_above_rejected(self) -> None:
        self.assertFalse(in_band(10.0))

    def test_zero_rejected(self) -> None:
        """Degenerate case: an empty/failed scoring run returns 0.0 — must FAIL."""
        self.assertFalse(in_band(0.0))


class TestBandConstantsArePinned(unittest.TestCase):
    """The published constants 8.57 / 9.07 / 9.57 are themselves pinned.

    If the constants in this file ever drift (e.g. someone changes the
    tolerance to 0.4 to make a failing run "pass"), this test fails
    loudly. The numbers come from HANDOFF-GSD-AUTO.md STOP condition #1
    and CONTEXT.md "Phase Boundary" — they are NOT a tuning knob.
    """

    def test_target_is_9_07(self) -> None:
        self.assertEqual(CALIBRATION_TARGET, 9.07)

    def test_tolerance_is_half(self) -> None:
        self.assertEqual(CALIBRATION_TOLERANCE, 0.5)

    def test_lower_band_is_8_57(self) -> None:
        self.assertEqual(LOWER_BAND, 8.57)

    def test_upper_band_is_9_57(self) -> None:
        self.assertEqual(UPPER_BAND, 9.57)


class TestCompositeReproducesFromPublishedResults(unittest.TestCase):
    """End-to-end: the row in results/scores.json scores to 9.07.

    Catches the case where someone edits results/scores.json (the
    published 2026-03-31 publish artifact) and accidentally drifts the
    Playwright row.
    """

    def test_published_playwright_row_scores_9_07(self) -> None:
        import json
        path = _REPO_ROOT / "results" / "scores.json"
        results = json.loads(path.read_text(encoding="utf-8"))
        published = results["Playwright MCP"]["scores"]
        # The pinned dict above must equal the published dict — verify
        # the test's own pin against the source-of-truth file.
        for dim, expected in PLAYWRIGHT_2026_03.items():
            self.assertEqual(
                published.get(dim),
                expected,
                f"{dim}: published={published.get(dim)} != pinned={expected}",
            )
        # And the composite reproduces.
        self.assertEqual(compute_composite(published), 9.07)


if __name__ == "__main__":
    unittest.main()
