"""Unit tests for the Phase 1 calibration band math.

The calibration gate (scripts/verify_calibration.sh) compares an observed
Playwright composite against the **harness re-baseline** of 8.33 with a
±0.5 tolerance. The math of "is this score in the band?" needs to be
verifiable without a real Playwright run — otherwise we can't unit-test
the harness's go/no-go logic.

## Re-baseline rationale (2026-05-26, user-approved Option C)

The 2026-03-31 published Playwright composite is **9.07** — computed by
`scoring/score.py` against a human-judged 8-dimension scores dict (the
`Playwright MCP` row in `results/scores.json`). That number is the
historical record and remains unchanged.

The Phase 1 harness re-scores the SAME 2026-03 evidence through
`scripts/aggregate_scores.py` + `scripts/score_with_na.py`, which use
heuristic scorers for 4 dimensions (Speed, Token Efficiency, Setup
Complexity, Error Handling) whose real measurement is deferred to Phase 3.
On the same 2026-03 evidence those heuristics produce **8.33** (see
`results/2026-03-31_rebaseline/scores.json`). This is the apples-to-apples
target the calibration gate uses to validate that the new harness reproduces
its own measurement contract — NOT to retroactively change the 2026-03
published number.

What this file proves:

  1. The 2026-03 Playwright row's dimension scores feed back through
     `scoring.score.compute_composite()` to exactly 9.07 — i.e.
     `scoring/score.py` has not drifted since the 2026-03 wave.
     (SACROSANCT contract — preserved verbatim.)
  2. The N/A-aware wrapper (`scripts/score_with_na.py`) returns the SAME
     composite on a row with no N/A cells — so Phase 1 calibration is
     not biased by the Phase 2 fairness layer.
  3. The `in_band()` helper inside `scripts/verify_calibration.sh` (whose
     pure-Python equivalent lives here) accepts everything in
     [7.83, 8.83] inclusive and rejects everything outside.

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
# the math test fails loudly if the published row is ever edited. This is
# the SACROSANCT contract: score.py + this row → 9.07, forever.
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

# The 2026-03-31 published composite via scoring/score.py (human-judged).
# This is the HISTORICAL number — never changes.
PUBLISHED_2026_03_COMPOSITE = 9.07

# The HARNESS RE-BASELINE composite — the same 2026-03 evidence re-scored
# through scripts/aggregate_scores.py + scripts/score_with_na.py. Captures
# the heuristic-scorer verdict on the published evidence, accounting for
# the 4 deferred-measurement scorers (Speed, Token Efficiency, Setup
# Complexity, Error Handling) that return neutral defaults during Phase 1.
# See results/2026-03-31_rebaseline/scores.json for the regenerable artifact.
CALIBRATION_TARGET = 8.33
CALIBRATION_TOLERANCE = 0.5
LOWER_BAND = round(CALIBRATION_TARGET - CALIBRATION_TOLERANCE, 2)  # 7.83
UPPER_BAND = round(CALIBRATION_TARGET + CALIBRATION_TOLERANCE, 2)  # 8.83


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
    """Anchor: the 2026-03 Playwright dimension scores compose to 9.07.

    This is the SACROSANCT contract — `scoring/score.py` + the published
    2026-03 row → 9.07, forever. The calibration target moved from 9.07
    to 8.33 in the 2026-05-26 re-baseline (user-approved Option C), but
    the score.py math against the published row did NOT change. These
    tests anchor that invariant against any future drift in score.py.
    """

    def test_score_py_reproduces_9_07(self) -> None:
        """`scoring/score.py` is the source of truth for the 2026-03 number."""
        composite = compute_composite(PLAYWRIGHT_2026_03)
        # The literal published number. If score.py is ever edited and
        # this value drifts, the entire wave's comparability with the
        # 2026-03 publish is broken — fail loudly.
        self.assertEqual(composite, PUBLISHED_2026_03_COMPOSITE)
        self.assertEqual(composite, 9.07)

    def test_score_with_na_matches_score_py_no_na(self) -> None:
        """The N/A-aware wrapper produces identical math when no cells are N/A."""
        score_py = compute_composite(PLAYWRIGHT_2026_03)
        na_aware = score_with_na.compute_na_aware_composite(PLAYWRIGHT_2026_03)
        # Both must equal each other AND the published 2026-03 composite.
        self.assertEqual(score_py, na_aware)
        self.assertEqual(score_py, PUBLISHED_2026_03_COMPOSITE)
        self.assertEqual(na_aware, 9.07)


class TestBandLogic(unittest.TestCase):
    """The ±0.5 band logic around the re-baseline target 8.33.

    Band: 7.83 ≤ score ≤ 8.83 = PASS, else FAIL. The target moved from
    the published 9.07 to the harness re-baseline 8.33 in 2026-05-26
    (user-approved Option C) to reflect that 4 of the 8 scorers return
    neutral defaults during Phase 1 — re-scoring the 2026-03 evidence
    through the same heuristics produces 8.33, which is the apples-to-
    apples target the gate uses.
    """

    def test_exact_target_in_band(self) -> None:
        self.assertTrue(in_band(8.33))

    def test_lower_bound_inclusive(self) -> None:
        self.assertTrue(in_band(7.83))

    def test_upper_bound_inclusive(self) -> None:
        self.assertTrue(in_band(8.83))

    def test_just_below_lower_bound_rejected(self) -> None:
        self.assertFalse(in_band(7.82))

    def test_just_above_upper_bound_rejected(self) -> None:
        self.assertFalse(in_band(8.84))

    def test_far_below_rejected(self) -> None:
        self.assertFalse(in_band(6.0))

    def test_far_above_rejected(self) -> None:
        self.assertFalse(in_band(10.0))

    def test_zero_rejected(self) -> None:
        """Degenerate case: an empty/failed scoring run returns 0.0 — must FAIL."""
        self.assertFalse(in_band(0.0))

    def test_2026_05_actual_in_band(self) -> None:
        """The 2026-05-25 actual composite 7.93 must land in the re-baseline band.

        This test is the headline proof that the re-baseline resolves the
        original calibration FAIL. Before re-baseline: 7.93 outside [8.57, 9.57]
        → FAIL. After re-baseline: 7.93 inside [7.83, 8.83] → PASS.
        """
        self.assertTrue(in_band(7.93))


class TestBandConstantsArePinned(unittest.TestCase):
    """The re-baseline constants 7.83 / 8.33 / 8.83 are themselves pinned.

    If the constants in this file ever drift (e.g. someone changes the
    tolerance to 0.4 to make a failing run "pass"), this test fails
    loudly. The numbers come from the 2026-05-26 user-approved Option C
    re-baseline (re-running 2026-03 evidence through aggregate_scores.py
    + score_with_na.py); see `results/2026-03-31_rebaseline/scores.json`
    and `scoring/rubric_notes.md` "Calibration Re-Baseline (2026-05-26)"
    for the audit trail.
    """

    def test_target_is_8_33(self) -> None:
        self.assertEqual(CALIBRATION_TARGET, 8.33)

    def test_tolerance_is_half(self) -> None:
        self.assertEqual(CALIBRATION_TOLERANCE, 0.5)

    def test_lower_band_is_7_83(self) -> None:
        self.assertEqual(LOWER_BAND, 7.83)

    def test_upper_band_is_8_83(self) -> None:
        self.assertEqual(UPPER_BAND, 8.83)

    def test_published_2026_03_constant_is_9_07(self) -> None:
        """The published 2026-03 composite is preserved as a constant.

        The published number does NOT change in the re-baseline — only
        the harness's internal target does. This invariant is pinned
        independently so a future edit can't conflate the two.
        """
        self.assertEqual(PUBLISHED_2026_03_COMPOSITE, 9.07)


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
