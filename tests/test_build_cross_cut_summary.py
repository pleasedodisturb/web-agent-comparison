"""test_build_cross_cut_summary — unit tests for Phase-3 synthesis aggregator.

The aggregator (`bench/build_cross_cut_summary.py`) walks
`results/<date>/<mcp>/` and joins five cross-cutting artifacts
(`cold_start.json`, `tokens.json`, `stability_metadata.json`,
`tool_call_counts.json`, `tools_inventory.json`) into a single
`CROSS_CUT_SUMMARY.md` consumed by Phase 4 synthesis.

Tests cover:
  - Test 1: master-table — 2-MCP fixture renders a master table with
    expected per-MCP rows + columns.
  - Test 2: missing-file handling — MCP missing cold_start.json renders
    MISSING placeholder, not crash.
  - Test 3: SKIPPED handling — stability_metadata with
    completion_status=SKIPPED renders SKIPPED row with reason.
  - Test 4: empirical finding template — playwright S5 vs chrome-devtools
    S5 batch-fill comparison generates a CONFIRMED/REFUTED verdict.
  - Test 5: source manifest — every per-MCP file path appears in §9.
  - Test 6: browser-use dual rows — direct and agent both appear in
    the master table; agent row shows SKIPPED status; tools_inventory
    tool_count inherits from direct's shared binary inventory.

Run with:
    .venv/bin/python -m pytest tests/test_build_cross_cut_summary.py -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench.build_cross_cut_summary import (
    aggregate_results,
    build_summary,
    render_master_table,
    render_empirical_findings,
)


# ─── Fixture builders ───────────────────────────────────────────────────


def _cold_start(mcp: str, cold_total: int, warm_total: int) -> dict:
    return {
        "captured_at": "2026-05-26T22:53:06Z",
        "mcp": mcp,
        "status": "OK",
        "n_runs": 5,
        "cold": {
            "median": {
                "t_resolve_ms": 3,
                "t_spawn_ms": cold_total - 6,
                "t_first_useful_ms": 3,
                "total_ms": cold_total,
            },
            "max": {"total_ms": cold_total + 20},
            "min": {"total_ms": cold_total - 5},
            "n_runs": 5,
            "samples": [],
        },
        "warm": {
            "median": {
                "t_resolve_ms": 2,
                "t_spawn_ms": warm_total - 5,
                "t_first_useful_ms": 3,
                "total_ms": warm_total,
            },
            "max": {"total_ms": warm_total + 5},
            "min": {"total_ms": warm_total - 5},
            "n_runs": 5,
            "samples": [],
        },
        "metadata": {"cache_eviction": "process_only"},
    }


def _tokens_ok(mcp: str, payload: int, input_t: int, output_t: int) -> dict:
    return {
        "captured_at": "2026-05-26T22:42:00Z",
        "mcp": mcp,
        "status": "OK",
        "scope": "schema+payload+turn",
        "schema_tokens": None,
        "headline_payload_bytes": payload,
        "median_total_payload_bytes": payload,
        "median_turn_input_tokens": input_t,
        "median_turn_output_tokens": output_t,
        "median_payload_bytes_per_stage": {
            "S1": payload // 2,
            "S5": payload // 10,
        },
        "payload_bytes_per_stage": {},
        "turn_tokens_per_pass": {},
        "notes": [],
    }


def _tokens_skipped(mcp: str) -> dict:
    return {
        "captured_at": "2026-05-26T22:42:00Z",
        "mcp": mcp,
        "status": "SKIPPED",
        "scope": "skipped",
        "headline_payload_bytes": None,
        "median_total_payload_bytes": None,
        "median_turn_input_tokens": None,
        "median_turn_output_tokens": None,
        "median_payload_bytes_per_stage": {},
        "schema_tokens": None,
        "reason": "- **reason:** LLM_KEY_ABSENT",
        "payload_bytes_per_stage": {},
        "turn_tokens_per_pass": {},
        "notes": [],
    }


def _stability_completed(mcp: str, iters: int, rss_first: int, rss_max: int) -> dict:
    return {
        "mcp": mcp,
        "captured_at": "2026-05-27T00:00:00Z",
        "completion_status": "COMPLETED",
        "configured_duration_minutes": 15.0,
        "actual_duration_minutes": 15.1,
        "iterations_completed": iters,
        "iterations_failed": {"s1": 0, "s5": 0, "s5_skipped_readonly": 0},
        "rss_first_kb": rss_first,
        "rss_max_kb": rss_max,
        "rss_growth_kb": rss_max - rss_first,
        "orphan_audit_survivors": 0,
        "loopback_only_verified": False,
        "fixture_base_url": "http://127.0.0.1:8765",
        "wallclock_decision": "executor_reduced_top3_15min_rest_7min",
        "skip_reason": None,
        "notes": [],
    }


def _stability_skipped(mcp: str, reason: str) -> dict:
    return {
        "mcp": mcp,
        "captured_at": "2026-05-26T23:10:00Z",
        "completion_status": "SKIPPED",
        "configured_duration_minutes": 0.0,
        "actual_duration_minutes": 0.0,
        "iterations_completed": 0,
        "iterations_failed": {"s1": 0, "s5": 0, "s5_skipped_readonly": 0},
        "rss_first_kb": 0,
        "rss_max_kb": 0,
        "rss_growth_kb": 0,
        "orphan_audit_survivors": 0,
        "loopback_only_verified": False,
        "fixture_base_url": "http://127.0.0.1:8765",
        "wallclock_decision": "selective_top3_60min_rest_30min",
        "skip_reason": reason,
        "notes": [f"SKIPPED reason={reason}"],
    }


def _tcc_ok(mcp: str, total: int, s5_calls: int) -> dict:
    return {
        "mcp": mcp,
        "status": "OK",
        "stage_attribution_mode": "marker",
        "median_total_calls": total,
        "median_total_per_stage": {
            "S1": 14,
            "S2": 6,
            "S3": 1,
            "S4": 4,
            "S5": s5_calls,
            "S6": 1,
            "S7": 1,
            "S8": 1,
            "unattributed": 2,
        },
        "median_per_stage": {
            "S5": {
                f"mcp__{mcp}__fill": s5_calls - 1 if s5_calls > 1 else 0,
                "Write": 1,
            },
        },
        "passes": {},
        "total_calls_per_pass": {"PASS1": total, "PASS2": total, "PASS3": total},
        "interesting": {"s5_calls_per_field_filled": None},
    }


def _tcc_skipped(mcp: str) -> dict:
    return {
        "mcp": mcp,
        "status": "SKIPPED",
        "stage_attribution_mode": "marker",
        "reason": "- **reason:** LLM_KEY_ABSENT",
    }


def _tools_inventory(mcp: str, count: int, categories: dict | None = None) -> dict:
    return {
        "args": [],
        "captured_at": "2026-05-26T22:32:00Z",
        "command": mcp,
        "mcp": mcp,
        "protocol_version": "2025-06-18",
        "status": "OK",
        "tool_count": count,
        "categories": categories or {
            "navigation": 2,
            "interaction": 5,
            "capture": 1,
            "diagnostics": 1,
            "inspection": 2,
            "other": count - 11 if count > 11 else 0,
        },
        "tools": [],
        "version_handshake": "1.0.0",
    }


def _write_mcp_dir(
    base: Path,
    mcp: str,
    *,
    cold_start: dict | None = None,
    tokens: dict | None = None,
    stability: dict | None = None,
    tcc: dict | None = None,
    inventory: dict | None = None,
    skipped_md: str | None = None,
) -> Path:
    d = base / mcp
    d.mkdir(parents=True, exist_ok=True)
    if cold_start is not None:
        (d / "cold_start.json").write_text(json.dumps(cold_start), encoding="utf-8")
    if tokens is not None:
        (d / "tokens.json").write_text(json.dumps(tokens), encoding="utf-8")
    if stability is not None:
        (d / "stability_metadata.json").write_text(json.dumps(stability), encoding="utf-8")
    if tcc is not None:
        (d / "tool_call_counts.json").write_text(json.dumps(tcc), encoding="utf-8")
    if inventory is not None:
        (d / "tools_inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
    if skipped_md is not None:
        (d / "SKIPPED.md").write_text(skipped_md, encoding="utf-8")
    return d


def _write_scores(base: Path, scores: dict) -> None:
    (base / "scores.json").write_text(json.dumps(scores), encoding="utf-8")


# ─── Tests ─────────────────────────────────────────────────────────────


class MasterTableTests(unittest.TestCase):
    """Test 1 — Master table renders one row per MCP with expected columns."""

    def test_two_mcps_render_master_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_mcp_dir(
                base, "alpha",
                cold_start=_cold_start("alpha", 200, 198),
                tokens=_tokens_ok("alpha", 60000, 55, 20000),
                stability=_stability_completed("alpha", 30, 144000, 162000),
                tcc=_tcc_ok("alpha", 50, 4),
                inventory=_tools_inventory("alpha", 23),
            )
            _write_mcp_dir(
                base, "beta",
                cold_start=_cold_start("beta", 13, 12),
                tokens=_tokens_ok("beta", 16000, 27, 8000),
                stability=_stability_completed("beta", 30, 51000, 55000),
                tcc=_tcc_ok("beta", 34, 1),
                inventory=_tools_inventory("beta", 20),
            )
            _write_scores(base, {
                "alpha": {"status": "OK", "scores": {}, "stages": {}, "capability": "tool-only"},
                "beta": {"status": "OK", "scores": {}, "stages": {}, "capability": "js-light"},
            })

            data = aggregate_results(base)
            self.assertEqual(len(data["mcps"]), 2)
            mcp_names = {m["mcp"] for m in data["mcps"]}
            self.assertEqual(mcp_names, {"alpha", "beta"})

            md = render_master_table(data)
            # Master table header columns we care about
            for header in (
                "MCP",
                "Cold-start",
                "Payload",
                "Stability",
                "Tool count",
            ):
                self.assertIn(header, md, f"header {header!r} missing in master table")
            # Both rows present
            self.assertIn("alpha", md)
            self.assertIn("beta", md)
            # Numeric values present
            self.assertIn("200", md)
            self.assertIn("13", md)
            self.assertIn("23", md)
            self.assertIn("20", md)


class MissingFileTests(unittest.TestCase):
    """Test 2 — missing cold_start.json renders MISSING, not crash."""

    def test_missing_cold_start_renders_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_mcp_dir(
                base, "gamma",
                # No cold_start
                tokens=_tokens_ok("gamma", 40000, 50, 10000),
                stability=_stability_completed("gamma", 30, 80000, 84000),
                tcc=_tcc_ok("gamma", 40, 3),
                inventory=_tools_inventory("gamma", 20),
            )
            _write_scores(base, {"gamma": {"status": "OK", "scores": {}, "stages": {}}})

            data = aggregate_results(base)
            self.assertEqual(len(data["mcps"]), 1)
            row = data["mcps"][0]
            self.assertEqual(row["mcp"], "gamma")
            # The cold_start dimension should be flagged MISSING
            self.assertEqual(row["cold_start"]["status"], "MISSING")
            # Source manifest tracks the gap
            self.assertIn("gamma/cold_start.json", data.get("missing_files", []))

            md = build_summary(data)
            # Doesn't crash, renders MISSING marker
            self.assertIn("MISSING", md)
            # Master table still has the row
            self.assertIn("gamma", md)


class SkippedHandlingTests(unittest.TestCase):
    """Test 3 — stability_metadata with SKIPPED renders reason in cell."""

    def test_stability_skipped_renders_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_mcp_dir(
                base, "delta",
                cold_start=_cold_start("delta", 171, 169),
                tokens=_tokens_ok("delta", 0, 0, 0),
                stability=_stability_skipped("delta", "LOOPBACK_UNREACHABLE"),
                tcc=_tcc_ok("delta", 0, 0),
                inventory=_tools_inventory("delta", 24),
            )
            _write_scores(base, {"delta": {"status": "OK", "scores": {}, "stages": {}}})

            data = aggregate_results(base)
            row = data["mcps"][0]
            self.assertEqual(row["stability"]["status"], "SKIPPED")
            self.assertEqual(row["stability"]["skip_reason"], "LOOPBACK_UNREACHABLE")

            md = build_summary(data)
            # Must show SKIPPED + the reason somewhere
            self.assertIn("SKIPPED", md)
            self.assertIn("LOOPBACK_UNREACHABLE", md)


class EmpiricalFindingsTests(unittest.TestCase):
    """Test 4 — empirical finding templates produce verdicts grounded in data."""

    def test_batch_fill_finding_compares_s5_counts(self) -> None:
        """Playwright batch-fill claim: S5 median tool-calls vs other MCPs.

        Hypothesis: playwright should fill multiple fields in ~1 call;
        other MCPs require ~1 call/field. Aggregator must:
          1. Find playwright's S5 total
          2. Compute median of other MCPs' S5 totals
          3. Emit a CONFIRMED/REFUTED verdict
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            # Playwright: S5 = 2 (low, batch-fill)
            _write_mcp_dir(
                base, "playwright",
                cold_start=_cold_start("playwright", 200, 200),
                tokens=_tokens_ok("playwright", 50000, 55, 20000),
                stability=_stability_completed("playwright", 30, 140000, 160000),
                tcc=_tcc_ok("playwright", 30, 2),  # S5=2
                inventory=_tools_inventory("playwright", 23),
            )
            # Other: S5 = 7 (high, per-field-fill)
            _write_mcp_dir(
                base, "chrome-devtools",
                cold_start=_cold_start("chrome-devtools", 360, 360),
                tokens=_tokens_ok("chrome-devtools", 60000, 55, 21000),
                stability=_stability_completed("chrome-devtools", 14, 220000, 220000),
                tcc=_tcc_ok("chrome-devtools", 40, 7),  # S5=7
                inventory=_tools_inventory("chrome-devtools", 29),
            )
            _write_scores(base, {
                "playwright": {"status": "OK", "scores": {}, "stages": {}},
                "chrome-devtools": {"status": "OK", "scores": {}, "stages": {}},
            })

            data = aggregate_results(base)
            findings_md = render_empirical_findings(data)
            # Playwright finding mentions both S5 counts and a verdict
            self.assertIn("Playwright", findings_md)
            self.assertIn("batch-fill", findings_md.lower())
            self.assertIn("2", findings_md)
            self.assertIn("7", findings_md)
            # Verdict appears (CONFIRMED because playwright is meaningfully lower)
            self.assertTrue(
                "CONFIRMED" in findings_md or "REFUTED" in findings_md
                or "INCOMPLETE" in findings_md or "NO_EVIDENCE" in findings_md,
                "expected verdict marker in findings",
            )

    def test_no_evidence_finding_when_playwright_tcc_missing(self) -> None:
        """When playwright tcc is NO_EVIDENCE, finding renders NO_EVIDENCE."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_mcp_dir(
                base, "playwright",
                cold_start=_cold_start("playwright", 200, 200),
                tokens={"status": "NO_EVIDENCE", "mcp": "playwright",
                        "headline_payload_bytes": None,
                        "median_payload_bytes_per_stage": {},
                        "median_turn_input_tokens": None,
                        "median_turn_output_tokens": None,
                        "schema_tokens": None,
                        "scope": "no-evidence",
                        "notes": []},
                stability=_stability_completed("playwright", 30, 140000, 160000),
                tcc={"mcp": "playwright", "status": "NO_EVIDENCE",
                     "stage_attribution_mode": "marker",
                     "reason": "No PASS dirs"},
                inventory=_tools_inventory("playwright", 23),
            )
            _write_scores(base, {"playwright": {"status": "OK", "scores": {}, "stages": {}}})
            data = aggregate_results(base)
            findings_md = render_empirical_findings(data)
            self.assertIn("NO_EVIDENCE", findings_md)


class SourceManifestTests(unittest.TestCase):
    """Test 5 — every per-MCP source file cited in §9 Source Manifest."""

    def test_source_manifest_lists_all_consumed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_mcp_dir(
                base, "epsilon",
                cold_start=_cold_start("epsilon", 200, 200),
                tokens=_tokens_ok("epsilon", 50000, 55, 20000),
                stability=_stability_completed("epsilon", 30, 80000, 84000),
                tcc=_tcc_ok("epsilon", 40, 3),
                inventory=_tools_inventory("epsilon", 20),
            )
            _write_scores(base, {"epsilon": {"status": "OK", "scores": {}, "stages": {}}})

            data = aggregate_results(base)
            md = build_summary(data)

            # Source manifest should list the five file paths for epsilon
            for fname in (
                "epsilon/cold_start.json",
                "epsilon/tokens.json",
                "epsilon/stability_metadata.json",
                "epsilon/tool_call_counts.json",
                "epsilon/tools_inventory.json",
            ):
                self.assertIn(fname, md, f"manifest missing {fname}")


class BrowserUseDualRowsTests(unittest.TestCase):
    """Test 6 — browser-use-direct + browser-use-agent both appear."""

    def test_agent_row_skipped_but_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            # direct: full data
            _write_mcp_dir(
                base, "browser-use-direct",
                cold_start=_cold_start("browser-use-direct", 668, 671),
                tokens=_tokens_ok("browser-use-direct", 120000, 62, 20000),
                stability=_stability_completed("browser-use-direct", 14, 178000, 184000),
                tcc=_tcc_ok("browser-use-direct", 51, 1),
                inventory=_tools_inventory("browser-use-direct", 16),
            )
            # agent: cold-start data (shared binary), but tokens/tcc/stability SKIPPED
            _write_mcp_dir(
                base, "browser-use-agent",
                cold_start=_cold_start("browser-use-agent", 668, 671),
                tokens=_tokens_skipped("browser-use-agent"),
                stability=_stability_skipped("browser-use-agent", "LLM_KEY_ABSENT"),
                tcc=_tcc_skipped("browser-use-agent"),
                inventory=_tools_inventory("browser-use-agent", 16),
                skipped_md="# browser-use-agent SKIPPED\n- reason: LLM_KEY_ABSENT\n",
            )
            _write_scores(base, {
                "browser-use-direct": {"status": "OK", "scores": {}, "stages": {}},
                "browser-use-agent": {"status": "SKIPPED",
                                       "skip_reason": "LLM_KEY_ABSENT",
                                       "scores": {}, "stages": {}},
            })

            data = aggregate_results(base)
            mcp_names = [m["mcp"] for m in data["mcps"]]
            self.assertIn("browser-use-direct", mcp_names)
            self.assertIn("browser-use-agent", mcp_names)

            agent_row = next(m for m in data["mcps"] if m["mcp"] == "browser-use-agent")
            # Cold-start measurable (shared binary)
            self.assertEqual(agent_row["cold_start"]["status"], "OK")
            # Tokens SKIPPED
            self.assertEqual(agent_row["tokens"]["status"], "SKIPPED")
            # Stability SKIPPED
            self.assertEqual(agent_row["stability"]["status"], "SKIPPED")
            # Tools inventory still OK (shared binary)
            self.assertEqual(agent_row["inventory"]["status"], "OK")

            md = build_summary(data)
            # Both rows must be in the rendered markdown
            self.assertIn("browser-use-direct", md)
            self.assertIn("browser-use-agent", md)


if __name__ == "__main__":
    unittest.main()
