"""test_build_report — unit tests for the Phase-4 public comparison report builder.

The builder (`bench/build_report.py`) reads `results/<date>/scores.json` +
`cross_cut_data.json` + per-MCP `DEEP_ANALYSIS.md` files and assembles the
public scored comparison report.

Tests cover the 13 behaviors specified by plan 04-03 Task 1:

  - Test 1: build_report emits all 7 MCP names
  - Test 2: SKIPPED row renders composite as "SKIPPED" (not "0.0")
  - Test 3: sandbox callout injection — idempotent, regex-recognised, distance-aware
  - Test 4: stage matrix distinguishes N/A vs UNTESTED vs SKIPPED
  - Test 5: methodology disclaimer header includes run date + "not intrinsic tool quality"
  - Test 6: methodology body section includes "## Methodology" + MACHINE.md + rubric + fixtures + REPRODUCIBILITY.md
  - Test 7: 2026-03 → 2026-05 overlay shows 9.07 → 7.93
  - Test 8: Linear traceability footer cites G-703 + references G-710
  - Test 9: Negative Results section lists all 5 known negative findings
  - Test 10: 8-dim weighted score table has 7 MCP rows + composite column
  - Test 11: obscura + browser-use-direct stability annotations show "transport-only"
  - Test 12: browser-use dual-mode rendering — Direct mode + Agent mode subsections
  - Test 13: partial-run disclosure names browser-use-agent (NOT firecrawl)

Run with:
    python3 -m pytest tests/test_build_report.py -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench.build_report import (
    aggregate_scores,
    aggregate_cross_cut,
    build_report,
    inject_sandbox_callouts,
    load_deep_analysis,
    load_skipped_narrative,
    render_capability_view,
    render_deep_analysis,
    render_executive_summary,
    render_linear_traceability_footer,
    render_methodology_disclaimer,
    render_methodology_section,
    render_negative_results,
    render_overlay_2026_03_2026_05,
    render_score_table,
    render_stage_matrix,
)


# ─── Fixture builders ───────────────────────────────────────────────────


RUBRIC_WEIGHTS = {
    "data_quality": 3,
    "reliability": 3,
    "speed": 2,
    "token_efficiency": 2,
    "interaction_depth": 2,
    "js_rendering": 1,
    "setup_complexity": 1,
    "error_handling": 1,
}


def _scored_row(
    *,
    capability: str,
    mode: str,
    scores: dict,
    stages: dict,
    attribution: dict | None = None,
    sandbox_only: bool = False,
) -> dict:
    row = {
        "capability": capability,
        "mode": mode,
        "scores": scores,
        "stages": stages,
        "attribution": attribution or {},
    }
    if sandbox_only:
        row["sandbox_only"] = True
    return row


def _skipped_row(*, capability: str, mode: str, reason: str, evidence: str) -> dict:
    return {
        "capability": capability,
        "mode": mode,
        "status": "SKIPPED",
        "skip_reason": reason,
        "skip_evidence": evidence,
        "scores": {k: "N/A" for k in RUBRIC_WEIGHTS},
        "stages": {f"S{i}": "N/A" for i in range(1, 9)},
        "attribution": {},
    }


def _full_scores_fixture() -> dict:
    """Return a fixture mirroring the real scores.json shape for all 8 rows."""
    return {
        "playwright": _scored_row(
            capability="tool-only",
            mode="default",
            scores={
                "data_quality": 10, "reliability": 9, "speed": 5,
                "token_efficiency": 5, "interaction_depth": 10,
                "js_rendering": 10, "setup_complexity": 7, "error_handling": 5,
            },
            stages={f"S{i}": "PASS" for i in range(1, 9)},
        ),
        "chrome-devtools": _scored_row(
            capability="tool-only",
            mode="default",
            scores={
                "data_quality": 10, "reliability": 5, "speed": 5,
                "token_efficiency": 5, "interaction_depth": 0,
                "js_rendering": 10, "setup_complexity": 7, "error_handling": 2,
            },
            stages={
                "S1": "PASS", "S2": "PASS", "S3": "PASS",
                "S4": "FAIL", "S5": "FAIL", "S6": "FAIL", "S7": "FAIL", "S8": "FAIL",
            },
            attribution={"error_handling": "tool-bug", "interaction_depth": "tool-bug"},
        ),
        "browser-use-direct": _scored_row(
            capability="LLM-augmented",
            mode="direct",
            scores={
                "data_quality": 10, "reliability": 5, "speed": 5,
                "token_efficiency": 5, "interaction_depth": 2,
                "js_rendering": 10, "setup_complexity": 7, "error_handling": 2,
            },
            stages={
                "S1": "PASS", "S2": "PASS", "S3": "PASS",
                "S4": "FAIL", "S5": "FAIL", "S6": "FAIL", "S7": "FAIL", "S8": "PASS",
            },
            attribution={"error_handling": "tool-bug", "interaction_depth": "tool-bug"},
        ),
        "browser-use-agent": _skipped_row(
            capability="LLM-augmented",
            mode="agent",
            reason="LLM_KEY_ABSENT",
            evidence="results/2026-05-26/browser-use-agent/SKIPPED.md",
        ),
        "cloakbrowser": _scored_row(
            capability="stealth-specialist",
            mode="sandbox-loopback",
            scores={
                "data_quality": 10, "reliability": 10, "speed": 5,
                "token_efficiency": 5, "interaction_depth": 10,
                "js_rendering": 10, "setup_complexity": 7, "error_handling": 8,
            },
            stages={f"S{i}": "PASS" for i in range(1, 9)},
            sandbox_only=True,
        ),
        "obscura": _scored_row(
            capability="stealth-specialist",
            mode="no-stealth-flag",
            scores={
                "data_quality": 0, "reliability": 6, "speed": 5,
                "token_efficiency": 5, "interaction_depth": 0,
                "js_rendering": 2, "setup_complexity": 7, "error_handling": 2,
            },
            stages={f"S{i}": "FAIL" for i in range(1, 9)},
            attribution={
                "data_quality": "tool-bug", "error_handling": "tool-bug",
                "interaction_depth": "tool-bug", "js_rendering": "tool-bug",
            },
        ),
        "firecrawl": _scored_row(
            capability="cloud",
            mode="markdown",
            scores={
                "data_quality": 0, "reliability": 7, "speed": 5,
                "token_efficiency": 5, "interaction_depth": "N/A",
                "js_rendering": 2, "setup_complexity": 7, "error_handling": 5,
            },
            stages={
                "S1": "FAIL", "S2": "FAIL", "S3": "FAIL",
                "S4": "N/A", "S5": "N/A", "S6": "N/A", "S7": "N/A", "S8": "N/A",
            },
            attribution={"data_quality": "env-mismatch", "js_rendering": "env-mismatch"},
        ),
        "lightpanda": _scored_row(
            capability="js-light",
            mode="default",
            scores={
                "data_quality": 7, "reliability": 9, "speed": 5,
                "token_efficiency": 5, "interaction_depth": "N/A",
                "js_rendering": 2, "setup_complexity": 7, "error_handling": 5,
            },
            stages={
                "S1": "PASS", "S2": "FAIL", "S3": "PASS",
                "S4": "N/A", "S5": "N/A", "S6": "N/A", "S7": "N/A", "S8": "N/A",
            },
            attribution={"js_rendering": "tool-bug"},
        ),
    }


def _full_cross_cut_fixture() -> dict:
    return {
        "results_date_dir": "results/2026-05-26",
        "metadata": {"generator": "bench.build_cross_cut_summary", "n_mcps": 8},
        "missing_files": [],
        "mcps": [
            {
                "mcp": "cloakbrowser",
                "cold_start": {"status": "OK", "cold_median_total_ms": 235, "warm_median_total_ms": 240},
                "tokens": {"status": "OK", "headline_payload_bytes": 77228, "median_turn_input_tokens": 63, "median_turn_output_tokens": 24476},
                "stability": {"status": "COMPLETED", "iterations_completed": 30, "rss_first_kb": 84032, "rss_max_kb": 84032, "rss_growth_kb": 0, "orphan_audit_survivors": 0, "wallclock_decision": "executor_reduced_top3_15min_rest_7min", "skip_reason": None},
                "tcc": {"status": "OK", "median_total_calls": 53, "median_total_per_stage": {"S1": 18, "S2": 6, "S3": 1, "S4": 7, "S5": 6, "S6": 4, "S7": 3, "unattributed": 5}},
                "inventory": {"status": "OK", "tool_count": 20, "categories": {"capture": 1, "diagnostics": 1, "inspection": 3, "interaction": 6, "navigation": 3, "other": 6}},
            },
            {
                "mcp": "playwright",
                "cold_start": {"status": "OK", "cold_median_total_ms": 197, "warm_median_total_ms": 198},
                "tokens": {"status": "NO_EVIDENCE"},
                "stability": {"status": "COMPLETED", "iterations_completed": 30, "rss_first_kb": 143936, "rss_max_kb": 162352, "rss_growth_kb": 18416, "orphan_audit_survivors": 0, "wallclock_decision": "executor_reduced_top3_15min_rest_7min", "skip_reason": None},
                "tcc": {"status": "NO_EVIDENCE"},
                "inventory": {"status": "OK", "tool_count": 23, "categories": {"capture": 1, "diagnostics": 5, "inspection": 1, "interaction": 11, "navigation": 2, "other": 3}},
            },
            {
                "mcp": "lightpanda",
                "cold_start": {"status": "OK", "cold_median_total_ms": 13, "warm_median_total_ms": 12},
                "tokens": {"status": "OK", "headline_payload_bytes": 44633, "median_turn_input_tokens": 48, "median_turn_output_tokens": 11046},
                "stability": {"status": "COMPLETED", "iterations_completed": 30, "rss_first_kb": 51344, "rss_max_kb": 55888, "rss_growth_kb": 4544, "orphan_audit_survivors": 0, "wallclock_decision": "executor_reduced_top3_15min_rest_7min", "skip_reason": None},
                "tcc": {"status": "OK", "median_total_calls": 34, "median_total_per_stage": {"S1": 14, "S2": 11, "S3": 1, "S4": 1, "S5": 1, "S6": 1, "S7": 1, "S8": 1, "unattributed": 2}},
                "inventory": {"status": "OK", "tool_count": 20, "categories": {"capture": 0, "diagnostics": 1, "inspection": 2, "interaction": 7, "navigation": 2, "other": 8}},
            },
            {
                "mcp": "browser-use-direct",
                "cold_start": {"status": "OK", "cold_median_total_ms": 668, "warm_median_total_ms": 671},
                "tokens": {"status": "OK", "headline_payload_bytes": 120059, "median_turn_input_tokens": 62, "median_turn_output_tokens": 20173},
                "stability": {"status": "COMPLETED", "iterations_completed": 14, "rss_first_kb": 178352, "rss_max_kb": 183968, "rss_growth_kb": 5616, "orphan_audit_survivors": 0, "wallclock_decision": "executor_reduced_top3_15min_rest_7min", "skip_reason": None},
                "tcc": {"status": "OK", "median_total_calls": 51, "median_total_per_stage": {"S1": 22, "S2": 6, "S3": 1, "S4": 4, "S5": 1, "S6": 1, "S7": 1, "S8": 0, "unattributed": 4}},
                "inventory": {"status": "OK", "tool_count": 16, "categories": {"capture": 1, "diagnostics": 0, "inspection": 5, "interaction": 3, "navigation": 2, "other": 5}},
            },
            {
                "mcp": "chrome-devtools",
                "cold_start": {"status": "OK", "cold_median_total_ms": 358, "warm_median_total_ms": 361},
                "tokens": {"status": "OK", "headline_payload_bytes": 62318, "median_turn_input_tokens": 55, "median_turn_output_tokens": 20942},
                "stability": {"status": "COMPLETED", "iterations_completed": 14, "rss_first_kb": 220016, "rss_max_kb": 220048, "rss_growth_kb": 32, "orphan_audit_survivors": 0, "wallclock_decision": "executor_reduced_top3_15min_rest_7min", "skip_reason": None},
                "tcc": {"status": "OK", "median_total_calls": 39, "median_total_per_stage": {"S1": 18, "S2": 9, "S3": 1, "S4": 6, "S5": 1, "S6": 1, "S7": 1, "S8": 1, "unattributed": 2}},
                "inventory": {"status": "OK", "tool_count": 29, "categories": {"capture": 1, "diagnostics": 10, "inspection": 3, "interaction": 10, "navigation": 1, "other": 4}},
            },
            {
                "mcp": "firecrawl",
                "cold_start": {"status": "OK", "cold_median_total_ms": 171, "warm_median_total_ms": 169},
                "tokens": {"status": "OK", "headline_payload_bytes": 0, "median_turn_input_tokens": None, "median_turn_output_tokens": None},
                "stability": {"status": "SKIPPED", "skip_reason": "LOOPBACK_UNREACHABLE"},
                "tcc": {"status": "OK", "median_total_calls": 0, "median_total_per_stage": {}},
                "inventory": {"status": "OK", "tool_count": 24, "categories": {"capture": 0, "diagnostics": 0, "inspection": 5, "interaction": 0, "navigation": 1, "other": 18}},
            },
            {
                "mcp": "obscura",
                "cold_start": {"status": "OK", "cold_median_total_ms": 158, "warm_median_total_ms": 158},
                "tokens": {"status": "OK", "headline_payload_bytes": 16394, "median_turn_input_tokens": 27, "median_turn_output_tokens": 8356},
                "stability": {"status": "COMPLETED", "iterations_completed": 14, "rss_first_kb": 19888, "rss_max_kb": 21040, "rss_growth_kb": 1152, "orphan_audit_survivors": 0, "wallclock_decision": "executor_reduced_top3_15min_rest_7min", "skip_reason": None},
                "tcc": {"status": "OK", "median_total_calls": 19, "median_total_per_stage": {"S1": 10, "S2": 1, "S3": 1, "S4": 1, "S5": 1, "S6": 1, "S7": 1, "S8": 1, "unattributed": 1}},
                "inventory": {"status": "OK", "tool_count": 4, "categories": {"capture": 0, "diagnostics": 0, "inspection": 1, "interaction": 0, "navigation": 0, "other": 3}},
            },
            {
                "mcp": "browser-use-agent",
                "cold_start": {"status": "OK", "cold_median_total_ms": 668, "warm_median_total_ms": 671},
                "tokens": {"status": "SKIPPED"},
                "stability": {"status": "SKIPPED", "skip_reason": "LLM_KEY_ABSENT"},
                "tcc": {"status": "SKIPPED"},
                "inventory": {"status": "OK", "tool_count": 16, "categories": {"capture": 1, "diagnostics": 0, "inspection": 5, "interaction": 3, "navigation": 2, "other": 5}},
            },
        ],
    }


def _write_fixtures(tmp: Path) -> tuple[Path, Path, Path, Path]:
    """Write scores, cross-cut, capability, and a deep-dir into tmp; return paths."""
    scores_path = tmp / "scores.json"
    scores_path.write_text(json.dumps(_full_scores_fixture()), encoding="utf-8")

    cross_path = tmp / "cross_cut_data.json"
    cross_path.write_text(json.dumps(_full_cross_cut_fixture()), encoding="utf-8")

    cap_path = tmp / "CAPABILITY_MATRIX.md"
    cap_path.write_text(
        "# Capability Matrix — 2026-05-26\n\n"
        "| MCP | Composite |\n|---|---|\n"
        "| `playwright` | 7.93 |\n"
        "| `cloakbrowser` | 8.33 |\n\n"
        "**Sandbox only — do not point at authenticated sessions.**\n",
        encoding="utf-8",
    )

    deep_dir = tmp / "deep"
    deep_dir.mkdir()
    for mcp in ("chrome-devtools", "lightpanda", "obscura", "firecrawl", "cloakbrowser"):
        (deep_dir / mcp).mkdir()
        (deep_dir / mcp / "DEEP_ANALYSIS.md").write_text(
            f"# {mcp} — Deep Analysis\n\n"
            f"## Strengths\n- Strong S1-S3 surface\n- Tool count adequate\n- Clean error handling\n\n"
            f"## Weaknesses\n- React-clobber on S4\n- No batch-fill primitive\n- Limited screenshot fidelity\n\n"
            f"## Verdict\nMedian composite documented above.\n\n"
            f"## Interesting angle\nTokens captured.\n",
            encoding="utf-8",
        )
    (deep_dir / "browser-use-direct").mkdir()
    (deep_dir / "browser-use-direct" / "DEEP_ANALYSIS.md").write_text(
        "# browser-use (direct mode) — Deep Analysis\n\n"
        "## Strengths\n- Works without LLM key for S1-S3+S8\n- Tool surface 16-deep\n- Reasonable cold-start\n\n"
        "## Weaknesses\n- React-clobber on S4-S7\n- No eval/CDP primitive\n- Modest interaction_depth=2\n\n"
        "## Verdict\nComposite 5.87 — 3rd in matrix.\n",
        encoding="utf-8",
    )
    (deep_dir / "browser-use-agent").mkdir()
    (deep_dir / "browser-use-agent" / "SKIPPED.md").write_text(
        "# browser-use-agent — SKIPPED (LLM API key absent)\n\n"
        "- **reason:** LLM_KEY_ABSENT\n"
        "- **what was verified before skipping:** initialize handshake OK in both modes\n"
        "- **what a follow-up run would need to do:**\n"
        "  1. Unlock rbw\n"
        "  2. Retrieve a real LLM key\n"
        "  3. Re-run plan 02-05 Task 2\n",
        encoding="utf-8",
    )
    return scores_path, cross_path, cap_path, deep_dir


# ─── Tests ──────────────────────────────────────────────────────────────


class TestBuildReport(unittest.TestCase):

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        self.scores_path, self.cross_path, self.cap_path, self.deep_dir = _write_fixtures(self.tmp)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # Test 1 — all 7 MCP names present
    def test_01_all_mcps_named(self) -> None:
        out = build_report(
            self.scores_path, self.cross_path, self.cap_path,
            self.deep_dir, "2026-05-27", None,
        )
        for mcp in [
            "playwright", "browser-use", "chrome-devtools",
            "lightpanda", "obscura", "firecrawl", "cloakbrowser",
        ]:
            self.assertIn(mcp, out, f"missing MCP name: {mcp}")

    # Test 2 — SKIPPED row renders composite as "SKIPPED", not "0.0"
    def test_02_skipped_composite_not_zero(self) -> None:
        scores = aggregate_scores(self.scores_path)
        table = render_score_table(scores, RUBRIC_WEIGHTS)
        # Locate the browser-use-agent row
        agent_lines = [ln for ln in table.splitlines() if "browser-use-agent" in ln]
        self.assertTrue(agent_lines, "browser-use-agent row missing from score table")
        agent_row = agent_lines[0]
        self.assertIn("SKIPPED", agent_row)
        # The composite cell must NOT read "0.0" or "0.00"
        self.assertNotIn("| 0.0 ", agent_row)
        self.assertNotIn("| 0.00 ", agent_row)

    # Test 3 — sandbox-callout injection idempotency + recognition
    def test_03a_inject_seed(self) -> None:
        out = inject_sandbox_callouts("cloakbrowser is fast.")
        self.assertRegex(out.lower(), r"sandbox[- ]?only")

    def test_03b_idempotent(self) -> None:
        seed = "cloakbrowser is fast.\nAnother line.\nMore cloakbrowser content.\n"
        once = inject_sandbox_callouts(seed)
        twice = inject_sandbox_callouts(once)
        self.assertEqual(once, twice, "inject_sandbox_callouts is NOT idempotent")

    def test_03c_no_double_injection_near_existing_callout(self) -> None:
        # If the recognised callout already lives within 5 lines, do not inject again
        input_md = (
            "cloakbrowser is the stealth specialist.\n"
            "**Sandbox only — do not point at authenticated sessions.**\n"
            "More content here.\n"
        )
        out = inject_sandbox_callouts(input_md)
        # Count the canonical recognition occurrences — should still be 1
        import re
        n = len(re.findall(r"sandbox[- ]?only", out, re.IGNORECASE))
        self.assertEqual(n, 1, f"expected 1 sandbox-only mention, got {n}")

    def test_03d_capability_matrix_variant_recognised(self) -> None:
        # CAPABILITY_MATRIX.md uses "**Sandbox only — do not point at authenticated sessions.**"
        # with a trailing period — the regex must match it.
        input_md = (
            "cloakbrowser reference here.\n"
            "**Sandbox only — do not point at authenticated sessions.**\n"
        )
        out = inject_sandbox_callouts(input_md)
        import re
        n = len(re.findall(r"sandbox[- ]?only", out, re.IGNORECASE))
        self.assertEqual(n, 1, "trailing-period CAPABILITY_MATRIX variant not recognised")

    # Test 4 — stage matrix distinguishes N/A vs UNTESTED vs SKIPPED
    def test_04_stage_matrix_cells_distinct(self) -> None:
        scores = aggregate_scores(self.scores_path)
        matrix = render_stage_matrix(scores)
        self.assertIn("N/A", matrix)
        self.assertIn("SKIPPED", matrix)
        # Confirm SKIPPED row (browser-use-agent) does not show as N/A in a cell while
        # being labelled SKIPPED in status — i.e. distinct string forms exist somewhere.
        agent_lines = [ln for ln in matrix.splitlines() if "browser-use-agent" in ln]
        self.assertTrue(agent_lines, "browser-use-agent row missing from stage matrix")
        # The agent row must include SKIPPED at least once
        self.assertTrue(any("SKIPPED" in ln for ln in agent_lines))

    # Test 5 — methodology disclaimer header
    def test_05_methodology_disclaimer_header(self) -> None:
        out_str = render_methodology_disclaimer("2026-05-27")
        self.assertIn("2026-05-27", out_str)
        self.assertIn("not intrinsic tool quality", out_str.lower().replace(
            "tool-quality", "tool quality"
        ))
        # Accept dict input too
        out_dict = render_methodology_disclaimer({"run_date": "2026-05-27"})
        self.assertIn("2026-05-27", out_dict)

    def test_05_methodology_disclaimer_rejects_empty_date(self) -> None:
        """WR-07: refuse to emit a malformed header when date is missing."""
        for bad in (None, "", "   ", {}, {"run_date": ""}, {"run_date": None}):
            with self.assertRaises(ValueError):
                render_methodology_disclaimer(bad)

    # Test 6 — methodology body section
    def test_06a_methodology_h2_heading(self) -> None:
        out = render_methodology_section({})
        self.assertIn("## Methodology", out)

    def test_06b_methodology_machine_md_citation(self) -> None:
        out = render_methodology_section({})
        self.assertIn("results/2026-05-27/MACHINE.md", out)

    def test_06c_methodology_mentions_rubric(self) -> None:
        out = render_methodology_section({})
        self.assertIn("scoring/rubric.md", out)

    def test_06d_methodology_mentions_loopback(self) -> None:
        out = render_methodology_section({})
        self.assertRegex(out, r"loopback|REPRO-04")

    def test_06e_methodology_mentions_reproducibility(self) -> None:
        out = render_methodology_section({})
        self.assertIn("docs/REPRODUCIBILITY.md", out)

    # Test 7 — 2026-03 → 2026-05 overlay
    def test_07_overlay_has_baseline_and_current(self) -> None:
        scores = aggregate_scores(self.scores_path)
        out = render_overlay_2026_03_2026_05(scores)
        self.assertIn("9.07", out)
        self.assertIn("7.93", out)

    # Test 8 — Linear footer
    def test_08_linear_footer(self) -> None:
        out = render_linear_traceability_footer()
        self.assertIn("G-703", out)
        self.assertIn("G-710", out)

    # Test 9 — Negative Results section
    def test_09_negative_results_complete(self) -> None:
        scores = aggregate_scores(self.scores_path)
        cross_cut = aggregate_cross_cut(self.cross_path)
        out = render_negative_results(scores, cross_cut)
        # All 5 negative-result bullets must be present (case-insensitive textual hits)
        lower = out.lower()
        self.assertIn("firecrawl", lower)
        self.assertIn("loopback", lower)
        self.assertIn("obscura", lower)
        self.assertRegex(lower, r"macos|stealth|sec-ch-ua")
        self.assertIn("browser-use-agent", lower)
        self.assertIn("llm_key_absent", lower)
        self.assertIn("chrome-devtools", lower)
        self.assertRegex(lower, r"devtools|unexercised|inventoried")
        self.assertIn("playwright", lower)
        self.assertRegex(lower, r"2026-05-25|cross-cut|date gap")

    # Test 10 — 8-dim weighted score table shape
    def test_10_score_table_shape(self) -> None:
        scores = aggregate_scores(self.scores_path)
        out = render_score_table(scores, RUBRIC_WEIGHTS)
        # 7 candidate MCPs by name (browser-use rolled up as a single name OR
        # browser-use-direct + browser-use-agent dual rows — accept either as long
        # as cloakbrowser carries SANDBOX-ONLY annotation)
        for mcp in [
            "playwright", "chrome-devtools",
            "lightpanda", "obscura", "firecrawl", "cloakbrowser",
        ]:
            self.assertIn(mcp, out, f"missing MCP row: {mcp}")
        # Either direct or agent or both browser-use variants in the table
        self.assertRegex(out, r"browser-use")
        # Cloakbrowser must carry SANDBOX annotation
        cloak_lines = [ln for ln in out.splitlines() if "cloakbrowser" in ln]
        self.assertTrue(cloak_lines)
        self.assertTrue(
            any("SANDBOX" in ln.upper() for ln in cloak_lines),
            "cloakbrowser row missing SANDBOX annotation",
        )
        # Composite column present in header
        self.assertRegex(out, r"Composite|composite")

    # Test 11 — stability annotation on obscura + browser-use-direct
    def test_11_transport_only_annotation(self) -> None:
        # The annotation may live in render_score_table or a dedicated render — verify
        # it shows up in the final build_report output.
        out = build_report(
            self.scores_path, self.cross_path, self.cap_path,
            self.deep_dir, "2026-05-27", None,
        )
        self.assertIn("transport-only", out.lower())

    # Test 12 — browser-use dual-mode rendering
    def test_12a_direct_mode_subsection(self) -> None:
        scores = aggregate_scores(self.scores_path)
        out = render_deep_analysis(scores, self.deep_dir, "browser-use")
        self.assertIn("### Direct mode", out)

    def test_12b_agent_mode_subsection(self) -> None:
        scores = aggregate_scores(self.scores_path)
        out = render_deep_analysis(scores, self.deep_dir, "browser-use")
        self.assertIn("### Agent mode", out)

    def test_12c_skipped_in_agent_mode(self) -> None:
        scores = aggregate_scores(self.scores_path)
        out = render_deep_analysis(scores, self.deep_dir, "browser-use")
        self.assertIn("SKIPPED", out)

    def test_12d_agent_section_lifts_skipped_md(self) -> None:
        scores = aggregate_scores(self.scores_path)
        out = render_deep_analysis(scores, self.deep_dir, "browser-use")
        # Should mention either LLM_KEY_ABSENT, "what was verified", or "re-run"
        self.assertRegex(out, r"LLM_KEY_ABSENT|what was verified|re-run")

    # Test 13 — partial-run disclosure names browser-use-agent
    def test_13_partial_run_disclosure_names_browser_use_agent(self) -> None:
        scores = aggregate_scores(self.scores_path)
        out = render_executive_summary(scores, partial_run_flag=True)
        self.assertIn("browser-use-agent", out)
        # And not the wrong attribution (firecrawl is SCORED 4.23, not SKIPPED)
        self.assertNotIn(
            "Partial run: firecrawl SKIPPED", out,
            "executive summary mis-attributes SKIPPED to firecrawl",
        )

    # WR-05 — build_report creates parent directory
    def test_wr05_build_report_creates_parent_directory(self) -> None:
        nested_out = self.tmp / "nested" / "dirs" / "report.md"
        self.assertFalse(nested_out.parent.is_dir())
        build_report(
            self.scores_path, self.cross_path, self.cap_path,
            self.deep_dir, "2026-05-27", nested_out,
        )
        self.assertTrue(nested_out.is_file())


if __name__ == "__main__":
    unittest.main()
