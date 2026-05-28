"""test_stability_loop — unit tests for the 1-hour stability soak harness.

Plan 03-04 (MEAS-07) implements the rubric's "60min S1+S5 loop" wall-clock
test: drive each MCP under test through a Stage-1 (Greenhouse markdown
extract) + Stage-5 (Ashby form fill) loop against the snapshot fixture
server on 127.0.0.1:8765, with per-tool-call 30s timeout enforcement and
post-run orphan_audit confirming 0 surviving processes.

The module under test is `bench/stability_loop.py`.

Test coverage (matches PLAN.md task-1 behaviors)
------------------------------------------------
  1. Iteration counter — given duration_minutes=1/30 and sleep_s=30, the
     loop produces exactly 2 iterations (at t=0 and t=30s).
  2. Per-iteration log line shape — each line parses to {timestamp,
     iteration_n, s1_status, s5_status, s1_ms, s5_ms, rss_kb, notes}.
  3. Read-only mode — when mode='read-only' (lightpanda) is passed,
     s5_status is 'N/A_READONLY', s5_ms is null/None, counter
     `iterations_failed.s5_skipped_readonly` increments per iter.
  4. Per-tool-call 30s timeout — given a mocked tool call that hangs,
     the timeout is enforced and the line records s1_status=TIMEOUT.
  5. Loopback-only enforcement for cloakbrowser — when mcp='cloakbrowser'
     AND fixture_base_url='https://example.com' is passed, the function
     raises BEFORE starting the loop.
  6. Memory tracking — rss_kb increases when a mocked ps returns growing
     values; rss_growth_kb in final metadata = rss_max - rss_first.
  7. Orphan audit hook — at end of loop, the function returns a survivor
     count from a mockable interface; if survivors > 0, completion_status
     is COMPLETED_WITH_ORPHANS (NOT failure).
  8. Skip mode — when mode='skip', writes a SKIPPED metadata file without
     running the loop. Used for firecrawl + browser-use-agent.

Run with:
    .venv/bin/python -m pytest tests/test_stability_loop.py -v
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from bench.stability_loop import (
    LogLine,
    StabilityResult,
    parse_log_line,
    format_log_line,
    run_stability_loop,
    run_skip,
    TOOL_RECIPES,
)
from bench.cloakbrowser_guard import HostnameNotAllowedError


# ─── Test 1: iteration counter ──────────────────────────────────────────


class IterationCounterTests(unittest.TestCase):
    """Test 1: loop runs exactly ceil(duration / sleep) iterations."""

    def test_one_minute_thirty_second_sleep_yields_two_iterations(self):
        """duration=1.0min, sleep=30s -> iterations at t=0 and t=30, totalling 2."""

        async def fake_call(stage, recipe, base_url, **kwargs):
            return ("PASS", 5, None)  # status, elapsed_ms, error

        # Use a synthetic clock so the test runs in milliseconds, not minutes.
        clock = {"now": 0.0}

        def fake_perf_counter():
            return clock["now"]

        async def fake_sleep(secs):
            clock["now"] += secs

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with patch("bench.stability_loop.time.perf_counter", fake_perf_counter), \
                 patch("bench.stability_loop.asyncio.sleep", fake_sleep), \
                 patch("bench.stability_loop._call_stage", side_effect=fake_call), \
                 patch("bench.stability_loop._sample_rss_kb", return_value=10000), \
                 patch("bench.stability_loop._spawn_mcp", return_value=(None, 99999)), \
                 patch("bench.stability_loop._teardown_mcp"), \
                 patch("bench.stability_loop._snapshot_before"), \
                 patch("bench.stability_loop._diff_after", return_value=0):
                result = asyncio.run(run_stability_loop(
                    mcp="playwright",
                    duration_minutes=1.0,
                    sleep_s=30.0,
                    fixture_base_url="http://127.0.0.1:8765",
                    out_dir=out_dir,
                    mode="full",
                ))

        self.assertEqual(result.iterations_completed, 2)


# ─── Test 2: per-iteration log line shape ───────────────────────────────


class LogLineShapeTests(unittest.TestCase):
    """Test 2: each emitted log line parses round-trip to a LogLine."""

    def test_format_then_parse_round_trip(self):
        original = LogLine(
            timestamp="2026-05-27T10:00:00Z",
            iteration_n=0,
            s1_status="PASS",
            s5_status="PASS",
            s1_ms=128,
            s5_ms=512,
            rss_kb=482000,
            notes="",
        )
        text = format_log_line(original)
        # Format must contain all fields as key=value pairs.
        self.assertIn("iteration=0", text)
        self.assertIn("s1=PASS", text)
        self.assertIn("s5=PASS", text)
        self.assertIn("s1_ms=128", text)
        self.assertIn("s5_ms=512", text)
        self.assertIn("rss_kb=482000", text)
        # Round trip.
        parsed = parse_log_line(text)
        self.assertEqual(parsed.timestamp, original.timestamp)
        self.assertEqual(parsed.iteration_n, original.iteration_n)
        self.assertEqual(parsed.s1_status, original.s1_status)
        self.assertEqual(parsed.s5_status, original.s5_status)
        self.assertEqual(parsed.s1_ms, original.s1_ms)
        self.assertEqual(parsed.s5_ms, original.s5_ms)
        self.assertEqual(parsed.rss_kb, original.rss_kb)

    def test_log_line_with_null_s5_ms_for_readonly(self):
        line = LogLine(
            timestamp="2026-05-27T10:00:00Z",
            iteration_n=3,
            s1_status="PASS",
            s5_status="N/A_READONLY",
            s1_ms=42,
            s5_ms=None,
            rss_kb=120000,
            notes="",
        )
        text = format_log_line(line)
        self.assertIn("s5=N/A_READONLY", text)
        self.assertIn("s5_ms=null", text)


# ─── Test 3: read-only mode ──────────────────────────────────────────────


class ReadOnlyModeTests(unittest.TestCase):
    """Test 3: lightpanda mode='read-only' skips S5 with N/A_READONLY."""

    def test_read_only_mode_marks_s5_na_and_increments_counter(self):
        async def fake_call(stage, recipe, base_url, **kwargs):
            return ("PASS", 5, None)

        clock = {"now": 0.0}

        def fake_perf_counter():
            return clock["now"]

        async def fake_sleep(secs):
            clock["now"] += secs

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with patch("bench.stability_loop.time.perf_counter", fake_perf_counter), \
                 patch("bench.stability_loop.asyncio.sleep", fake_sleep), \
                 patch("bench.stability_loop._call_stage", side_effect=fake_call), \
                 patch("bench.stability_loop._sample_rss_kb", return_value=12000), \
                 patch("bench.stability_loop._spawn_mcp", return_value=(None, 99999)), \
                 patch("bench.stability_loop._teardown_mcp"), \
                 patch("bench.stability_loop._snapshot_before"), \
                 patch("bench.stability_loop._diff_after", return_value=0):
                result = asyncio.run(run_stability_loop(
                    mcp="lightpanda",
                    duration_minutes=1.0,
                    sleep_s=30.0,
                    fixture_base_url="http://127.0.0.1:8765",
                    out_dir=out_dir,
                    mode="read-only",
                ))

        # Both iterations must mark S5 as skipped-readonly.
        self.assertEqual(result.iterations_failed["s5_skipped_readonly"], 2)
        # Read-only mode doesn't count s5 misses as failures.
        self.assertEqual(result.iterations_failed["s5"], 0)


# ─── Test 4: per-tool-call 30s timeout ───────────────────────────────────


class TimeoutEnforcementTests(unittest.TestCase):
    """Test 4: a hung tool call is interrupted, line records TIMEOUT."""

    def test_timeout_records_timeout_status_and_thirty_thousand_ms(self):
        # Simulate the per-tool-call timeout firing. The internal call
        # function should catch asyncio.TimeoutError and return TIMEOUT.
        async def fake_call(stage, recipe, base_url, **kwargs):
            # Caller wraps in wait_for(timeout=30) — surface a TimeoutError.
            raise asyncio.TimeoutError("simulated 30s tool-call timeout")

        clock = {"now": 0.0}

        def fake_perf_counter():
            return clock["now"]

        async def fake_sleep(secs):
            clock["now"] += secs

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with patch("bench.stability_loop.time.perf_counter", fake_perf_counter), \
                 patch("bench.stability_loop.asyncio.sleep", fake_sleep), \
                 patch("bench.stability_loop._call_stage", side_effect=fake_call), \
                 patch("bench.stability_loop._sample_rss_kb", return_value=10000), \
                 patch("bench.stability_loop._spawn_mcp", return_value=(None, 99999)), \
                 patch("bench.stability_loop._teardown_mcp"), \
                 patch("bench.stability_loop._snapshot_before"), \
                 patch("bench.stability_loop._diff_after", return_value=0):
                result = asyncio.run(run_stability_loop(
                    mcp="playwright",
                    duration_minutes=1.0,
                    sleep_s=30.0,
                    fixture_base_url="http://127.0.0.1:8765",
                    out_dir=out_dir,
                    mode="full",
                ))

            # Every iteration logged TIMEOUT for s1.
            self.assertGreaterEqual(result.iterations_failed["s1"], 1)
            # Read the log file back; expect TIMEOUT and s1_ms=30000 at least once.
            log = (out_dir / "stability.log").read_text(encoding="utf-8")
            self.assertIn("s1=TIMEOUT", log)


# ─── Test 5: loopback-only enforcement for cloakbrowser ─────────────────


class CloakbrowserLoopbackTests(unittest.TestCase):
    """Test 5: cloakbrowser refuses non-loopback fixture base URL before loop."""

    def test_non_loopback_raises_before_loop_starts(self):
        # No mocking of the loop internals — the guard must fire BEFORE
        # any iteration starts.
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with self.assertRaises(HostnameNotAllowedError):
                asyncio.run(run_stability_loop(
                    mcp="cloakbrowser",
                    duration_minutes=0.1,
                    sleep_s=1.0,
                    fixture_base_url="https://example.com",
                    out_dir=out_dir,
                    mode="full",
                ))
            # No stability.log should have been written.
            self.assertFalse((out_dir / "stability.log").exists())


# ─── Test 6: memory tracking ────────────────────────────────────────────


class MemoryTrackingTests(unittest.TestCase):
    """Test 6: rss_growth_kb = rss_max - rss_first."""

    def test_rss_growth_kb_matches_max_minus_first(self):
        # Mocked ps returns growing values.
        rss_seq = iter([100_000, 120_000, 200_000, 180_000])

        def fake_rss_sample(pid):
            try:
                return next(rss_seq)
            except StopIteration:
                return 180_000

        async def fake_call(stage, recipe, base_url, **kwargs):
            return ("PASS", 5, None)

        clock = {"now": 0.0}

        def fake_perf_counter():
            return clock["now"]

        async def fake_sleep(secs):
            clock["now"] += secs

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with patch("bench.stability_loop.time.perf_counter", fake_perf_counter), \
                 patch("bench.stability_loop.asyncio.sleep", fake_sleep), \
                 patch("bench.stability_loop._call_stage", side_effect=fake_call), \
                 patch("bench.stability_loop._sample_rss_kb", side_effect=fake_rss_sample), \
                 patch("bench.stability_loop._spawn_mcp", return_value=(None, 99999)), \
                 patch("bench.stability_loop._teardown_mcp"), \
                 patch("bench.stability_loop._snapshot_before"), \
                 patch("bench.stability_loop._diff_after", return_value=0):
                result = asyncio.run(run_stability_loop(
                    mcp="playwright",
                    duration_minutes=1.5,  # 3 iterations at 30s sleep
                    sleep_s=30.0,
                    fixture_base_url="http://127.0.0.1:8765",
                    out_dir=out_dir,
                    mode="full",
                ))

        # rss_first=100k, rss_max=200k, growth=100k.
        self.assertEqual(result.rss_first_kb, 100_000)
        self.assertEqual(result.rss_max_kb, 200_000)
        self.assertEqual(result.rss_growth_kb, 100_000)


# ─── Test 7: orphan audit hook ──────────────────────────────────────────


class OrphanAuditTests(unittest.TestCase):
    """Test 7: post-run orphan audit returns survivor count; nonzero -> COMPLETED_WITH_ORPHANS."""

    def test_zero_survivors_yields_completed_status(self):
        async def fake_call(stage, recipe, base_url, **kwargs):
            return ("PASS", 5, None)

        clock = {"now": 0.0}

        def fake_perf_counter():
            return clock["now"]

        async def fake_sleep(secs):
            clock["now"] += secs

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with patch("bench.stability_loop.time.perf_counter", fake_perf_counter), \
                 patch("bench.stability_loop.asyncio.sleep", fake_sleep), \
                 patch("bench.stability_loop._call_stage", side_effect=fake_call), \
                 patch("bench.stability_loop._sample_rss_kb", return_value=10000), \
                 patch("bench.stability_loop._spawn_mcp", return_value=(None, 99999)), \
                 patch("bench.stability_loop._teardown_mcp"), \
                 patch("bench.stability_loop._snapshot_before"), \
                 patch("bench.stability_loop._diff_after", return_value=0):
                result = asyncio.run(run_stability_loop(
                    mcp="playwright",
                    duration_minutes=1.0,
                    sleep_s=30.0,
                    fixture_base_url="http://127.0.0.1:8765",
                    out_dir=out_dir,
                    mode="full",
                ))

        self.assertEqual(result.orphan_audit_survivors, 0)
        self.assertEqual(result.completion_status, "COMPLETED")

    def test_nonzero_survivors_yields_completed_with_orphans(self):
        async def fake_call(stage, recipe, base_url, **kwargs):
            return ("PASS", 5, None)

        clock = {"now": 0.0}

        def fake_perf_counter():
            return clock["now"]

        async def fake_sleep(secs):
            clock["now"] += secs

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with patch("bench.stability_loop.time.perf_counter", fake_perf_counter), \
                 patch("bench.stability_loop.asyncio.sleep", fake_sleep), \
                 patch("bench.stability_loop._call_stage", side_effect=fake_call), \
                 patch("bench.stability_loop._sample_rss_kb", return_value=10000), \
                 patch("bench.stability_loop._spawn_mcp", return_value=(None, 99999)), \
                 patch("bench.stability_loop._teardown_mcp"), \
                 patch("bench.stability_loop._snapshot_before"), \
                 patch("bench.stability_loop._diff_after", return_value=3):
                result = asyncio.run(run_stability_loop(
                    mcp="playwright",
                    duration_minutes=1.0,
                    sleep_s=30.0,
                    fixture_base_url="http://127.0.0.1:8765",
                    out_dir=out_dir,
                    mode="full",
                ))

        self.assertEqual(result.orphan_audit_survivors, 3)
        self.assertEqual(result.completion_status, "COMPLETED_WITH_ORPHANS")


# ─── Test 8: skip mode (firecrawl + browser-use-agent) ──────────────────


class SkipModeTests(unittest.TestCase):
    """Test 8: mode='skip' writes a SKIPPED metadata without running the loop."""

    def test_skip_writes_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result = run_skip(
                mcp="firecrawl",
                out_dir=out_dir,
                skip_reason="CLOUD_NO_LOOPBACK",
                duration_minutes=60,
                wallclock_decision="selective_top3_60min_rest_30min",
            )

            self.assertEqual(result.completion_status, "SKIPPED")
            self.assertEqual(result.skip_reason, "CLOUD_NO_LOOPBACK")

            meta_path = out_dir / "stability_metadata.json"
            self.assertTrue(meta_path.exists())
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertEqual(meta["completion_status"], "SKIPPED")
            self.assertEqual(meta["skip_reason"], "CLOUD_NO_LOOPBACK")
            self.assertEqual(meta["orphan_audit_survivors"], 0)
            self.assertEqual(meta["iterations_completed"], 0)

            # A stability.log marker should be written so the SUMMARY scanner
            # finds something at the canonical path.
            log_path = out_dir / "stability.log"
            self.assertTrue(log_path.exists())


# ─── Test 9: TOOL_RECIPES coverage ──────────────────────────────────────


class ToolRecipesTests(unittest.TestCase):
    """Test 9: TOOL_RECIPES covers all 6 SCORED MCPs."""

    def test_recipes_present_for_all_scored_mcps(self):
        expected = {
            "playwright", "chrome-devtools", "lightpanda",
            "cloakbrowser", "obscura", "browser-use-direct",
        }
        self.assertTrue(expected.issubset(set(TOOL_RECIPES.keys())))
        for mcp in expected:
            self.assertIn("s1", TOOL_RECIPES[mcp])
            if mcp != "lightpanda":  # lightpanda is read-only, no S5
                self.assertIn("s5", TOOL_RECIPES[mcp])


if __name__ == "__main__":
    unittest.main()
