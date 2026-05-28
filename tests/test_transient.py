"""Tests for bench.transient — the 3-pass-of-3 retry gate.

Covers:
  - Transient failure that eventually succeeds → 3 attempts recorded,
    each classified TRANSIENT for the failures, passed=True for the
    final attempt.
  - Transient failure that never succeeds → 3 attempts recorded, all
    failures.
  - Non-transient failure → 1 attempt recorded, no retry.
  - max_attempts boundary conditions.
  - median_pass / passed_majority helpers.
  - write_attempts_to_jsonl persistence.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench.failure_taxonomy import FailureTag
from bench.transient import (
    Attempt,
    median_pass,
    passed_majority,
    retry_stage,
    write_attempts_to_jsonl,
)


def make_eventually_succeeding(after_n_failures: int, transient_msg: str = "ECONNRESET"):
    """Return a callable that raises a transient error N times then succeeds."""
    state = {"calls": 0}

    def fn():
        state["calls"] += 1
        if state["calls"] <= after_n_failures:
            raise RuntimeError(transient_msg)
        return {"ok": True, "calls": state["calls"]}

    return fn, state


def make_always_failing(msg: str):
    """Return a callable that always raises `msg`."""
    state = {"calls": 0}

    def fn():
        state["calls"] += 1
        raise RuntimeError(msg)

    return fn, state


class TestRetryStage(unittest.TestCase):
    def test_transient_then_success_records_all_attempts(self) -> None:
        """ECONNRESET on attempts 1-2, success on attempt 3 → 3 attempts logged."""
        fn, state = make_eventually_succeeding(after_n_failures=2)

        attempts = retry_stage(fn, max_attempts=3, sleep_between_s=0)

        self.assertEqual(len(attempts), 3)
        self.assertFalse(attempts[0].passed)
        self.assertFalse(attempts[1].passed)
        self.assertTrue(attempts[2].passed)
        self.assertEqual(attempts[0].tag, FailureTag.TRANSIENT)
        self.assertEqual(attempts[1].tag, FailureTag.TRANSIENT)
        self.assertIsNone(attempts[2].tag)
        self.assertEqual(state["calls"], 3)

    def test_transient_never_succeeds_records_three_attempts(self) -> None:
        """ECONNRESET on every attempt → exactly 3 attempts, all transient."""
        fn, state = make_always_failing("ECONNRESET while reading")

        attempts = retry_stage(fn, max_attempts=3, sleep_between_s=0)

        self.assertEqual(len(attempts), 3)
        self.assertTrue(all(not a.passed for a in attempts))
        self.assertTrue(all(a.tag == FailureTag.TRANSIENT for a in attempts))
        self.assertEqual(state["calls"], 3)

    def test_non_transient_failure_stops_after_one_attempt(self) -> None:
        """ValueError (TOOL_BUG) → STOP, 1 attempt only, transient_only=True."""
        fn, state = make_always_failing("AttributeError: unexpected None")

        attempts = retry_stage(fn, max_attempts=3, sleep_between_s=0)

        self.assertEqual(len(attempts), 1)
        self.assertFalse(attempts[0].passed)
        self.assertEqual(attempts[0].tag, FailureTag.TOOL_BUG)
        self.assertEqual(state["calls"], 1)

    def test_target_flag_failure_stops_after_one_attempt(self) -> None:
        """HTTP 404 (TARGET_FLAG) is not retried by default."""
        fn, state = make_always_failing("HTTP 404 from greenhouse.io")

        attempts = retry_stage(fn, max_attempts=3, sleep_between_s=0)

        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].tag, FailureTag.TARGET_FLAG)
        self.assertEqual(state["calls"], 1)

    def test_first_attempt_success_returns_one_attempt(self) -> None:
        """No failures → 1 attempt, passed=True, no retries."""

        def fn():
            return {"first": "try"}

        attempts = retry_stage(fn, max_attempts=3, sleep_between_s=0)

        self.assertEqual(len(attempts), 1)
        self.assertTrue(attempts[0].passed)
        self.assertIsNone(attempts[0].tag)
        self.assertEqual(attempts[0].attempt_no, 1)

    def test_transient_only_false_retries_everything(self) -> None:
        """transient_only=False → even ValueError gets max_attempts tries."""
        fn, state = make_always_failing("AttributeError: oops")

        attempts = retry_stage(
            fn, max_attempts=3, sleep_between_s=0, transient_only=False
        )

        self.assertEqual(len(attempts), 3)
        self.assertEqual(state["calls"], 3)
        # Tag still classifies as TOOL_BUG; we just didn't honour the
        # transient-only stop signal.
        self.assertTrue(all(a.tag == FailureTag.TOOL_BUG for a in attempts))

    def test_max_attempts_one_no_retry(self) -> None:
        fn, state = make_always_failing("ECONNRESET")

        attempts = retry_stage(fn, max_attempts=1, sleep_between_s=0)

        self.assertEqual(len(attempts), 1)
        self.assertEqual(state["calls"], 1)

    def test_max_attempts_zero_raises(self) -> None:
        with self.assertRaises(ValueError):
            retry_stage(lambda: None, max_attempts=0, sleep_between_s=0)

    def test_attempt_records_duration(self) -> None:
        """Each Attempt carries a duration_s field that's >= 0."""

        def fn():
            return 1

        attempts = retry_stage(fn, max_attempts=1, sleep_between_s=0)
        self.assertGreaterEqual(attempts[0].duration_s, 0)


class TestMedianPass(unittest.TestCase):
    def test_two_of_three_passes_returns_two_three(self) -> None:
        attempts = [
            Attempt(attempt_no=1, passed=True, tag=None, duration_s=0.1),
            Attempt(attempt_no=2, passed=False, tag=FailureTag.TRANSIENT, duration_s=0.1),
            Attempt(attempt_no=3, passed=True, tag=None, duration_s=0.1),
        ]
        self.assertEqual(median_pass(attempts), (2, 3))

    def test_empty_list_returns_zero_zero(self) -> None:
        self.assertEqual(median_pass([]), (0, 0))

    def test_all_failures_returns_zero_total(self) -> None:
        attempts = [
            Attempt(attempt_no=i, passed=False, tag=FailureTag.TRANSIENT, duration_s=0.1)
            for i in (1, 2, 3)
        ]
        self.assertEqual(median_pass(attempts), (0, 3))

    def test_passed_majority_two_of_three_true(self) -> None:
        attempts = [
            Attempt(attempt_no=1, passed=True, tag=None, duration_s=0.1),
            Attempt(attempt_no=2, passed=False, tag=FailureTag.TRANSIENT, duration_s=0.1),
            Attempt(attempt_no=3, passed=True, tag=None, duration_s=0.1),
        ]
        self.assertTrue(passed_majority(attempts))

    def test_passed_majority_one_of_three_false(self) -> None:
        attempts = [
            Attempt(attempt_no=1, passed=False, tag=FailureTag.TRANSIENT, duration_s=0.1),
            Attempt(attempt_no=2, passed=False, tag=FailureTag.TRANSIENT, duration_s=0.1),
            Attempt(attempt_no=3, passed=True, tag=None, duration_s=0.1),
        ]
        self.assertFalse(passed_majority(attempts))

    def test_passed_majority_empty_false(self) -> None:
        self.assertFalse(passed_majority([]))


class TestWriteAttemptsToJsonl(unittest.TestCase):
    def test_appends_one_line_per_attempt(self) -> None:
        attempts = [
            Attempt(attempt_no=1, passed=False, tag=FailureTag.TRANSIENT, duration_s=0.42,
                    error="RuntimeError: ECONNRESET"),
            Attempt(attempt_no=2, passed=True, tag=None, duration_s=1.23),
        ]
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "raw.jsonl"
            write_attempts_to_jsonl(attempts, target)

            lines = target.read_text().strip().splitlines()
            self.assertEqual(len(lines), 2)

            r0 = json.loads(lines[0])
            self.assertEqual(r0["attempt_no"], 1)
            self.assertEqual(r0["passed"], False)
            self.assertEqual(r0["tag"], "transient")
            self.assertEqual(r0["duration_s"], 0.42)
            self.assertEqual(r0["error"], "RuntimeError: ECONNRESET")

            r1 = json.loads(lines[1])
            self.assertEqual(r1["attempt_no"], 2)
            self.assertTrue(r1["passed"])
            self.assertIsNone(r1["tag"])

    def test_append_mode_preserves_existing_content(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "raw.jsonl"
            first = [Attempt(attempt_no=1, passed=True, tag=None, duration_s=0.1)]
            second = [Attempt(attempt_no=1, passed=True, tag=None, duration_s=0.2)]
            write_attempts_to_jsonl(first, target)
            write_attempts_to_jsonl(second, target)

            lines = target.read_text().strip().splitlines()
            self.assertEqual(len(lines), 2)

    def test_creates_parent_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "nested" / "deeper" / "raw.jsonl"
            attempts = [Attempt(attempt_no=1, passed=True, tag=None, duration_s=0.1)]
            write_attempts_to_jsonl(attempts, target)
            self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
