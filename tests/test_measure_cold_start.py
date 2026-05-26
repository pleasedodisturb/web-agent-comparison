"""test_measure_cold_start — unit tests for the 3-segment cold-start measurer.

Plan 03-03 (MEAS-01) implements per-MCP cold-start latency with the
3-segment split (``t_resolve`` / ``t_spawn`` / ``t_first_useful``) for
both cold and warm cache, median of ≥5 runs.

The module under test is `bench/measure_cold_start.py` — see that file
for the timing decomposition rationale (the SDK's high-level
``stdio_client`` doesn't expose a hook for "first byte of stdout", so we
use a pragmatic three-anchor decomposition documented in 03-03-PLAN.md
context).

Test coverage
-------------
  1. Single-run timing returns positive numbers for every segment + total.
  2. Median computation — given 5 samples, medians (per-segment + total)
     are the middle value.
  3. Cold vs warm — pkill is invoked before each cold sample but NOT
     before warm samples.
  4. Failure mode — when one of the 5 runs raises asyncio.TimeoutError,
     the samples list keeps the 4 successful entries plus an error
     record, and the median is computed over the 4 valid samples.
  5. pkill safety — refuses to invoke pkill with an empty or wildcard
     pattern, refuses an unknown MCP key.
  6. SKIPPED MCP — when every probe errors, the resulting JSON carries
     status=SPAWN_FAILED with the error message; no crash.

Run with:
    .venv/bin/python -m pytest tests/test_measure_cold_start.py -v
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bench.measure_cold_start import (
    PKILL_PATTERNS,
    SegmentSample,
    compute_segment_medians,
    measure_one_run,
    measure_mcp,
    pkill_for_mcp,
    write_cold_start_json,
)


# ─── Test 1: single-run timing ──────────────────────────────────────────


class SingleRunTimingTests(unittest.TestCase):
    """Test 1: one run returns positive numbers across all three segments."""

    def test_measure_one_run_returns_three_segment_dict(self):
        """A successful run yields t_resolve_ms / t_spawn_ms / t_first_useful_ms / total_ms."""

        # We stub the async stages with three fake awaitables, each
        # introducing a measurable sleep. The implementation has to call
        # them in order and time the boundaries with perf_counter_ns.
        async def fake_open_streams():
            await asyncio.sleep(0.005)  # ~5 ms — t_resolve segment

        async def fake_initialize():
            await asyncio.sleep(0.010)  # ~10 ms — t_spawn segment

        async def fake_list_tools():
            await asyncio.sleep(0.008)  # ~8 ms — t_first_useful segment

        sample = asyncio.run(
            measure_one_run(
                open_streams_coro_factory=fake_open_streams,
                initialize_coro_factory=fake_initialize,
                list_tools_coro_factory=fake_list_tools,
            )
        )

        self.assertIsInstance(sample, dict)
        # All segments + total are positive numbers (rounded ms).
        for key in ("t_resolve_ms", "t_spawn_ms", "t_first_useful_ms", "total_ms"):
            self.assertIn(key, sample)
            self.assertGreater(sample[key], 0)
        # Total >= sum of segments (rounding can make it equal; never less).
        seg_sum = (
            sample["t_resolve_ms"]
            + sample["t_spawn_ms"]
            + sample["t_first_useful_ms"]
        )
        # Allow 1ms rounding slack — perf_counter_ns is monotonic so
        # the total cannot be strictly less than the sum of segments.
        self.assertGreaterEqual(sample["total_ms"] + 1, seg_sum)


# ─── Test 2: median across samples ──────────────────────────────────────


class MedianComputationTests(unittest.TestCase):
    """Test 2: median per-segment over a list of successful samples."""

    def test_median_of_five_samples(self):
        samples = [
            {"t_resolve_ms": 10, "t_spawn_ms": 100, "t_first_useful_ms": 50, "total_ms": 160},
            {"t_resolve_ms": 20, "t_spawn_ms": 200, "t_first_useful_ms": 60, "total_ms": 280},
            {"t_resolve_ms": 30, "t_spawn_ms": 300, "t_first_useful_ms": 70, "total_ms": 400},
            {"t_resolve_ms": 40, "t_spawn_ms": 400, "t_first_useful_ms": 80, "total_ms": 520},
            {"t_resolve_ms": 50, "t_spawn_ms": 500, "t_first_useful_ms": 90, "total_ms": 640},
        ]
        med = compute_segment_medians(samples)
        # Median of 1..5 → middle index = 3.
        self.assertEqual(med["t_resolve_ms"], 30)
        self.assertEqual(med["t_spawn_ms"], 300)
        self.assertEqual(med["t_first_useful_ms"], 70)
        self.assertEqual(med["total_ms"], 400)

    def test_median_ignores_error_records(self):
        """Samples with an ``error`` key are excluded from the median."""
        samples = [
            {"t_resolve_ms": 10, "t_spawn_ms": 100, "t_first_useful_ms": 50, "total_ms": 160},
            {"error": "TimeoutError"},
            {"t_resolve_ms": 30, "t_spawn_ms": 300, "t_first_useful_ms": 70, "total_ms": 400},
            {"t_resolve_ms": 50, "t_spawn_ms": 500, "t_first_useful_ms": 90, "total_ms": 640},
        ]
        med = compute_segment_medians(samples)
        # Median of the 3 valid samples (10, 30, 50) → 30.
        self.assertEqual(med["t_resolve_ms"], 30)
        self.assertEqual(med["t_spawn_ms"], 300)

    def test_median_returns_none_when_all_samples_fail(self):
        samples = [{"error": "A"}, {"error": "B"}]
        med = compute_segment_medians(samples)
        self.assertIsNone(med["t_resolve_ms"])
        self.assertIsNone(med["t_total_ms"]) if "t_total_ms" in med else None
        self.assertIsNone(med["total_ms"])


# ─── Test 3: cold vs warm separation ────────────────────────────────────


class ColdVsWarmTests(unittest.TestCase):
    """Test 3: pkill runs before each cold sample but NOT before warm samples."""

    def test_pkill_called_for_cold_runs_only(self):
        """measure_mcp invokes pkill once per cold run and zero times for warm runs."""
        # Use a stub measure_one_run that yields a fixed dict so the loop
        # body completes without spawning real MCP processes.
        async def fake_run(*_args, **_kwargs):
            return {"t_resolve_ms": 10, "t_spawn_ms": 20, "t_first_useful_ms": 30, "total_ms": 60}

        pkill_calls: list[str] = []

        def fake_pkill(mcp_key: str, *, skip: bool = False) -> int:
            pkill_calls.append(mcp_key)
            return 0  # number of patterns matched (mock)

        with patch("bench.measure_cold_start._run_one_real", fake_run), \
             patch("bench.measure_cold_start.pkill_for_mcp", fake_pkill):
            result = asyncio.run(
                measure_mcp(
                    mcp_key="playwright",
                    n_runs=3,
                    timeout_s=30.0,
                    skip_pkill=False,
                )
            )

        # 3 cold runs → 3 pkill calls; 3 warm runs → 0 additional pkill calls.
        self.assertEqual(len(pkill_calls), 3)
        self.assertEqual(pkill_calls, ["playwright"] * 3)
        # Result carries both cold and warm sample blocks.
        self.assertIn("cold", result)
        self.assertIn("warm", result)
        self.assertEqual(len(result["cold"]["samples"]), 3)
        self.assertEqual(len(result["warm"]["samples"]), 3)

    def test_skip_pkill_flag_suppresses_pkill_for_cold_too(self):
        """When --skip-pkill is passed, pkill is never invoked."""
        async def fake_run(*_args, **_kwargs):
            return {"t_resolve_ms": 1, "t_spawn_ms": 2, "t_first_useful_ms": 3, "total_ms": 6}

        pkill_calls: list[str] = []

        def fake_pkill(mcp_key: str, *, skip: bool = False) -> int:
            if not skip:
                pkill_calls.append(mcp_key)
            return 0

        with patch("bench.measure_cold_start._run_one_real", fake_run), \
             patch("bench.measure_cold_start.pkill_for_mcp", fake_pkill):
            asyncio.run(
                measure_mcp(
                    mcp_key="playwright",
                    n_runs=2,
                    timeout_s=30.0,
                    skip_pkill=True,
                )
            )

        self.assertEqual(pkill_calls, [])


# ─── Test 4: failure mode mid-loop ───────────────────────────────────────


class PartialFailureTests(unittest.TestCase):
    """Test 4: if run 3 of 5 raises TimeoutError, the 4 good samples are kept."""

    def test_one_failure_does_not_abort_remaining_runs(self):
        call_count = {"n": 0}

        async def flaky_run(*_args, **_kwargs):
            call_count["n"] += 1
            if call_count["n"] == 3:
                raise asyncio.TimeoutError("simulated initialize timeout")
            return {"t_resolve_ms": 5, "t_spawn_ms": 10, "t_first_useful_ms": 15, "total_ms": 30}

        with patch("bench.measure_cold_start._run_one_real", flaky_run), \
             patch("bench.measure_cold_start.pkill_for_mcp", lambda *a, **k: 0):
            result = asyncio.run(
                measure_mcp(
                    mcp_key="playwright",
                    n_runs=5,
                    timeout_s=1.0,
                    skip_pkill=True,
                )
            )

        # 5 cold + 5 warm = 10 calls total; the 3rd cold call fails.
        # Implementation does cold first, then warm.
        cold_samples = result["cold"]["samples"]
        # All 5 cold entries appear (failed one carries an error record).
        self.assertEqual(len(cold_samples), 5)
        # Exactly one error record across cold samples.
        errors = [s for s in cold_samples if "error" in s]
        self.assertEqual(len(errors), 1)
        # Median is computed over the 4 successful entries.
        self.assertEqual(result["cold"]["median"]["total_ms"], 30)


# ─── Test 5: pkill safety / allowlist ───────────────────────────────────


class PkillSafetyTests(unittest.TestCase):
    """Test 5: PKILL_PATTERNS is an allowlist; unknown / wildcard keys are refused."""

    def test_pkill_patterns_covers_all_mcps(self):
        """Every .mcp.json key (plus browser-use variants) has a pattern."""
        # The PKILL_PATTERNS dict must define patterns for each MCP we
        # measure. browser-use-direct + browser-use-agent route to the
        # shared "browser-use" key.
        for mcp in ("playwright", "chrome-devtools", "lightpanda",
                    "obscura", "firecrawl", "cloakbrowser", "browser-use"):
            self.assertIn(mcp, PKILL_PATTERNS)
            # Every pattern is non-empty and non-wildcard.
            for pat in PKILL_PATTERNS[mcp]:
                self.assertGreater(len(pat), 2)
                self.assertNotIn("*", pat)
                # Must not match our own Python interpreter or shell.
                self.assertNotIn("python", pat.lower())
                self.assertNotIn("bash", pat.lower())
                self.assertNotIn(".venv", pat.lower())

    def test_pkill_for_mcp_refuses_unknown_key(self):
        """pkill_for_mcp raises on an MCP key not in the allowlist."""
        with self.assertRaises(ValueError):
            pkill_for_mcp("not-a-real-mcp-key")

    def test_pkill_for_mcp_skip_flag_returns_zero(self):
        """The skip=True flag is a no-op, returns 0 (no patterns matched)."""
        result = pkill_for_mcp("playwright", skip=True)
        self.assertEqual(result, 0)

    def test_pkill_for_mcp_never_invokes_with_empty_pattern(self):
        """An entry with a blank pattern is treated as a hard error."""
        # Simulate a corrupted PKILL_PATTERNS entry.
        with patch.dict("bench.measure_cold_start.PKILL_PATTERNS",
                        {"corrupted-mcp": ["", "valid-pattern"]}, clear=False):
            with self.assertRaises(ValueError):
                pkill_for_mcp("corrupted-mcp")


# ─── Test 6: SPAWN_FAILED graceful exit ─────────────────────────────────


class SpawnFailedTests(unittest.TestCase):
    """Test 6: all probes erroring → status=SPAWN_FAILED, JSON written."""

    def test_all_runs_failing_writes_spawn_failed_status(self):
        async def always_fail(*_args, **_kwargs):
            raise RuntimeError("simulated spawn error: binary missing")

        with patch("bench.measure_cold_start._run_one_real", always_fail), \
             patch("bench.measure_cold_start.pkill_for_mcp", lambda *a, **k: 0):
            result = asyncio.run(
                measure_mcp(
                    mcp_key="playwright",
                    n_runs=2,
                    timeout_s=1.0,
                    skip_pkill=True,
                )
            )

        # No successful samples in cold or warm.
        self.assertEqual(result["status"], "SPAWN_FAILED")
        # The error message includes our injected detail.
        self.assertIn("simulated spawn error", json.dumps(result))
        # No median values (all None).
        self.assertIsNone(result["cold"]["median"]["total_ms"])
        self.assertIsNone(result["warm"]["median"]["total_ms"])

    def test_write_cold_start_json_writes_atomically(self):
        """write_cold_start_json writes valid JSON parseable by json.load."""
        payload = {
            "mcp": "playwright",
            "status": "OK",
            "cold": {"samples": [], "median": {"total_ms": None}, "n_runs": 0},
            "warm": {"samples": [], "median": {"total_ms": None}, "n_runs": 0},
            "metadata": {"cache_eviction": "process_only"},
        }
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "subdir" / "cold_start.json"
            write_cold_start_json(out, payload)
            self.assertTrue(out.exists())
            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(loaded["mcp"], "playwright")


if __name__ == "__main__":
    unittest.main()
