"""Tests for scripts/aggregate_scores.py.

Feeds a fixture results dir under tests/fixtures/results_sample/2026-05-22/
through the aggregator, then asserts the emitted scores.json:

  - Has the score.py-consumable shape (`scores` + `stages` per MCP).
  - Carries the additive extension fields (`attempts` + `attribution`).
  - Honours read-only MCP semantics: lightpanda → interaction_depth=N/A.
  - Round-trips through score_with_na.compute_na_aware_composite.

The fixture is built once at module-load and re-used across tests. It
exercises both an interactive MCP (playwright, all 8 stages) and a
read-only MCP (lightpanda, S1-S3 only with a FAILED on S2).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "results_sample" / "2026-05-22"

# Load the aggregator module by file path — scripts/ isn't a package.
_AGG_PATH = _REPO_ROOT / "scripts" / "aggregate_scores.py"
_spec = importlib.util.spec_from_file_location("aggregate_scores", _AGG_PATH)
agg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agg)


class TestFixturePresence(unittest.TestCase):
    """Sanity: the fixture dir is present and shaped as expected."""

    def test_fixture_dir_exists(self) -> None:
        self.assertTrue(FIXTURE_DIR.exists())
        self.assertTrue((FIXTURE_DIR / "playwright").is_dir())
        self.assertTrue((FIXTURE_DIR / "lightpanda").is_dir())

    def test_playwright_has_raw_stream(self) -> None:
        self.assertTrue((FIXTURE_DIR / "playwright" / "raw_stream.jsonl").exists())

    def test_lightpanda_has_failed_sentinel_s2(self) -> None:
        self.assertTrue((FIXTURE_DIR / "lightpanda" / "stage_s2.FAILED").exists())


class TestAggregateMCPPlaywright(unittest.TestCase):
    """Per-MCP aggregation: the playwright happy-path fixture."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.entry = agg.aggregate_mcp(FIXTURE_DIR / "playwright")

    def test_top_level_keys(self) -> None:
        self.assertIn("scores", self.entry)
        self.assertIn("stages", self.entry)
        self.assertIn("attempts", self.entry)
        self.assertIn("attribution", self.entry)

    def test_all_eight_dimensions_present(self) -> None:
        scores = self.entry["scores"]
        for dim in (
            "data_quality",
            "reliability",
            "speed",
            "token_efficiency",
            "interaction_depth",
            "js_rendering",
            "setup_complexity",
            "error_handling",
        ):
            self.assertIn(dim, scores)

    def test_interaction_depth_is_numeric_for_interactive_mcp(self) -> None:
        """Playwright is NOT read-only → interaction_depth must be a number."""
        self.assertIsInstance(self.entry["scores"]["interaction_depth"], int)

    def test_stages_use_pass_fail_na_strings(self) -> None:
        stages = self.entry["stages"]
        self.assertEqual(set(stages.keys()), {f"S{i}" for i in range(1, 9)})
        for v in stages.values():
            self.assertIsInstance(v, str)

    def test_attempts_s7_shows_retry(self) -> None:
        """The fixture raw.jsonl for S7 has 2 attempts (1 fail, 1 pass)."""
        s7 = self.entry["attempts"]["S7"]
        self.assertEqual(s7["total"], 2)
        self.assertEqual(s7["passes"], 1)
        self.assertEqual(s7["tag"], "transient")

    def test_attribution_empty_when_all_scores_geq_5(self) -> None:
        """No sub-score < 5 → attribution dict is empty."""
        self.assertEqual(self.entry["attribution"], {})


class TestAggregateMCPLightpanda(unittest.TestCase):
    """Read-only MCP aggregation: lightpanda has interaction_depth=N/A."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.entry = agg.aggregate_mcp(FIXTURE_DIR / "lightpanda")

    def test_interaction_depth_is_na_string(self) -> None:
        self.assertEqual(self.entry["scores"]["interaction_depth"], "N/A")

    def test_interactive_stages_marked_na(self) -> None:
        """S4-S8 should be N/A in the stages field for a read-only MCP."""
        for s in ("S4", "S5", "S6", "S7", "S8"):
            self.assertEqual(self.entry["stages"][s], "N/A",
                             f"Stage {s} should be N/A for read-only MCP")

    def test_s2_failed_status(self) -> None:
        """stage_s2.FAILED sentinel → stages['S2'] starts with FAIL."""
        self.assertTrue(self.entry["stages"]["S2"].startswith("FAIL"))

    def test_js_rendering_low_when_s2_fail(self) -> None:
        """S2 FAIL → js_rendering = 2 per the scorer rubric."""
        self.assertEqual(self.entry["scores"]["js_rendering"], 2)

    def test_attribution_tags_low_js_rendering(self) -> None:
        """js_rendering<5 → attribution['js_rendering'] is tagged."""
        attr = self.entry["attribution"]
        self.assertIn("js_rendering", attr)
        # The S2 attempt failed with tag=tool-bug per the fixture.
        self.assertEqual(attr["js_rendering"], "tool-bug")


class TestAggregateDateDir(unittest.TestCase):
    """Top-level walker: aggregate_date_dir produces a dict keyed by MCP."""

    def test_walks_subdirs_returns_dict(self) -> None:
        results = agg.aggregate_date_dir(FIXTURE_DIR)
        self.assertEqual(set(results.keys()), {"playwright", "lightpanda"})
        self.assertIn("scores", results["playwright"])
        self.assertIn("scores", results["lightpanda"])

    def test_raises_for_missing_dir(self) -> None:
        with self.assertRaises(FileNotFoundError):
            agg.aggregate_date_dir(_REPO_ROOT / "does" / "not" / "exist")

    def test_skips_hidden_subdirs(self) -> None:
        """Hidden directories (starting with .) must be skipped."""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / ".hidden_dir").mkdir()
            (base / "real_mcp").mkdir()
            (base / "real_mcp" / "stage_s1.md").touch()
            results = agg.aggregate_date_dir(base)
            self.assertNotIn(".hidden_dir", results)
            self.assertIn("real_mcp", results)


class TestCLIEntrypoint(unittest.TestCase):
    """End-to-end: invoke the script as a subprocess and read scores.json."""

    def test_cli_writes_scores_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "scores.json"
            # Use the project venv python for parity with the rest of the harness.
            py = _REPO_ROOT / ".venv" / "bin" / "python"
            if not py.exists():
                py = Path(sys.executable)
            rc = subprocess.call(
                [
                    str(py),
                    str(_AGG_PATH),
                    str(FIXTURE_DIR),
                    "--out",
                    str(out_path),
                ],
                env={**os.environ, "PYTHONPATH": str(_REPO_ROOT)},
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out_path.exists())

            data = json.loads(out_path.read_text())
            self.assertIn("playwright", data)
            self.assertIn("lightpanda", data)
            self.assertEqual(len(data["playwright"]["scores"]), 8)


class TestEmittedShapeIsScorePyCompatible(unittest.TestCase):
    """The emitted scores.json must be readable by scoring/score.py.

    score.py iterates `results.items()` and accesses `data["scores"]` +
    `data["stages"]` — our additive fields (`attempts`, `attribution`)
    must NOT break that contract.
    """

    def test_score_py_compute_composite_runs(self) -> None:
        """score.py's compute_composite must accept the aggregator's playwright row.

        Note: score.py is UNDEFINED on rows containing literal "N/A" strings (it
        crashes on `"N/A" * weight`). That's exactly why scripts/score_with_na.py
        exists — it overrides the N/A handling. This test only asserts score.py
        is happy with the all-numeric (no-N/A-cell) playwright row, which is the
        Phase 1 calibration target.
        """
        from scoring.score import compute_composite

        results = agg.aggregate_date_dir(FIXTURE_DIR)
        score = compute_composite(results["playwright"]["scores"])
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 10.0)

    def test_score_py_format_table_works_on_filtered_subset(self) -> None:
        """format_comparison_table works on the no-N/A subset (Phase 1 happy path)."""
        from scoring.score import format_comparison_table

        results = agg.aggregate_date_dir(FIXTURE_DIR)
        # Phase 1 calibration runs only Playwright — the N/A-bearing rows
        # belong to Phase 2 and route through score_with_na.py.
        playwright_only = {"playwright": results["playwright"]}
        table = format_comparison_table(playwright_only)
        self.assertIn("playwright", table)


class TestNAAwareComposite(unittest.TestCase):
    """Aggregator output composites cleanly through scripts/score_with_na.py."""

    def test_lightpanda_composite_drops_na_dim(self) -> None:
        # Load score_with_na as a module so we can call its functions.
        sw_path = _REPO_ROOT / "scripts" / "score_with_na.py"
        spec = importlib.util.spec_from_file_location("score_with_na", sw_path)
        sw = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sw)

        results = agg.aggregate_date_dir(FIXTURE_DIR)
        lightpanda_scores = results["lightpanda"]["scores"]
        self.assertEqual(lightpanda_scores["interaction_depth"], "N/A")

        composite = sw.compute_na_aware_composite(lightpanda_scores)
        # Sanity: composite is in range and weight-2 (interaction_depth) was dropped.
        self.assertGreater(composite, 0.0)
        self.assertLess(composite, 10.0)


if __name__ == "__main__":
    unittest.main()
