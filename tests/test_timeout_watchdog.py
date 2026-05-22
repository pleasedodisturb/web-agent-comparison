"""test_timeout_watchdog — unit tests for the per-tool-call timeout watchdog.

We exercise the watchdog's pure helpers directly (parser, stall
detection) and run one end-to-end happy-path test where a synthetic
JSONL file emits a `tool_use` with no matching `tool_result` and the
watchdog signals a stub parent process via SIGINT.

The watchdog's main loop is long-lived; we run it as a subprocess with a
short timeout (1s) against a synthetic JSONL to keep tests under a
second of wall-clock.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from bench.timeout_watchdog import (
    _scan_for_open_tool_uses,
    _stalled_use,
    watchdog_loop,
)


def _write_jsonl(path: str, events: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def _append_jsonl(path: str, events: list[dict]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


class ScanTest(unittest.TestCase):
    """Tests on `_scan_for_open_tool_uses` — pure-ish, file-driven."""

    def test_tool_use_block_is_recorded(self) -> None:
        """Nested tool_use in an assistant message updates open_uses."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "stream.jsonl")
            _write_jsonl(
                path,
                [
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "tool_use", "id": "tu_001", "name": "x"}
                            ]
                        },
                    }
                ],
            )
            open_uses: dict[str, float] = {}
            offset = _scan_for_open_tool_uses(path, open_uses, 0)
            self.assertIn("tu_001", open_uses)
            self.assertGreater(offset, 0)

    def test_tool_result_closes_open_use(self) -> None:
        """A tool_result event pops the matching tool_use_id."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "stream.jsonl")
            _write_jsonl(
                path,
                [
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "tool_use", "id": "tu_001", "name": "x"}
                            ]
                        },
                    },
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "tu_001",
                                    "content": "ok",
                                }
                            ]
                        },
                    },
                ],
            )
            open_uses: dict[str, float] = {}
            _scan_for_open_tool_uses(path, open_uses, 0)
            self.assertNotIn("tu_001", open_uses)

    def test_malformed_lines_are_skipped(self) -> None:
        """A garbage line in the middle does not crash the scanner."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "stream.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "type": "assistant",
                            "message": {
                                "content": [
                                    {"type": "tool_use", "id": "tu_001", "name": "x"}
                                ]
                            },
                        }
                    )
                    + "\n"
                )
                f.write("not valid json {][\n")
                f.write(
                    json.dumps(
                        {
                            "type": "assistant",
                            "message": {
                                "content": [
                                    {"type": "tool_use", "id": "tu_002", "name": "y"}
                                ]
                            },
                        }
                    )
                    + "\n"
                )
            open_uses: dict[str, float] = {}
            _scan_for_open_tool_uses(path, open_uses, 0)
            # Both surrounding valid events should be processed.
            self.assertIn("tu_001", open_uses)
            self.assertIn("tu_002", open_uses)

    def test_incremental_read_resumes_from_offset(self) -> None:
        """Second call only reads new bytes appended after the first call."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "stream.jsonl")
            _write_jsonl(
                path,
                [
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "tool_use", "id": "tu_first", "name": "x"}
                            ]
                        },
                    }
                ],
            )
            open_uses: dict[str, float] = {}
            offset_1 = _scan_for_open_tool_uses(path, open_uses, 0)
            self.assertIn("tu_first", open_uses)

            # Pop it and re-scan: a fresh scan from offset_1 should NOT
            # re-add the same id (we've already consumed those bytes).
            open_uses.pop("tu_first")
            offset_2 = _scan_for_open_tool_uses(path, open_uses, offset_1)
            self.assertNotIn("tu_first", open_uses)
            self.assertEqual(offset_2, offset_1)

            # Now append a new event and re-scan — only the new id arrives.
            _append_jsonl(
                path,
                [
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "tool_use", "id": "tu_second", "name": "y"}
                            ]
                        },
                    }
                ],
            )
            _scan_for_open_tool_uses(path, open_uses, offset_2)
            self.assertIn("tu_second", open_uses)
            self.assertNotIn("tu_first", open_uses)


class StalledUseTest(unittest.TestCase):
    """Tests on `_stalled_use` — pure function over the open_uses dict."""

    def test_no_stalled_returns_none(self) -> None:
        # Fresh tool_use, well under the threshold.
        open_uses = {"tu_001": time.time()}
        self.assertIsNone(_stalled_use(open_uses, threshold_s=10.0))

    def test_stalled_returns_id(self) -> None:
        # Tool_use started 20s ago, threshold 5s.
        open_uses = {"tu_001": time.time() - 20.0}
        self.assertEqual(_stalled_use(open_uses, threshold_s=5.0), "tu_001")

    def test_oldest_stalled_returned_first(self) -> None:
        now = time.time()
        open_uses = {
            "tu_new": now - 6.0,    # 6s old
            "tu_old": now - 30.0,   # 30s old
            "tu_mid": now - 15.0,   # 15s old
        }
        self.assertEqual(_stalled_use(open_uses, threshold_s=5.0), "tu_old")

    def test_empty_dict_returns_none(self) -> None:
        self.assertIsNone(_stalled_use({}, threshold_s=5.0))


class IntegrationTest(unittest.TestCase):
    """End-to-end: spawn a stub parent, run the watchdog, verify SIGINT delivery."""

    def test_watchdog_signals_parent_on_stalled_tool_use(self) -> None:
        # Spawn a long-running Python stub that traps SIGINT and exits
        # with rc=42. We use Python rather than `/bin/sh trap` because
        # shell-level traps don't fire until the foreground builtin
        # finishes — and `sleep 60` is an external command, so SIGINT
        # to the shell doesn't interrupt the shell's wait until the
        # watchdog escalates to SIGTERM. Python's signal module
        # delivers SIGINT promptly via KeyboardInterrupt.
        stub_code = (
            "import signal, sys, time;"
            "signal.signal(signal.SIGINT, lambda *_: sys.exit(42));"
            "time.sleep(60)"
        )
        stub = subprocess.Popen(
            [sys.executable, "-c", stub_code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            with tempfile.TemporaryDirectory() as tmp:
                jsonl_path = os.path.join(tmp, "stream.jsonl")
                # Pre-populate the JSONL with one open tool_use stamped
                # well in the past — the watchdog should detect this on
                # its very first scan iteration.
                with open(jsonl_path, "w", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "type": "assistant",
                                "message": {
                                    "content": [
                                        {
                                            "type": "tool_use",
                                            "id": "tu_stalled",
                                            "name": "test",
                                        }
                                    ]
                                },
                            }
                        )
                        + "\n"
                    )

                # Run the watchdog as a subprocess. We use the in-process
                # call would block the test; the subprocess form mirrors
                # how the real harness invokes it. Use a TINY timeout so
                # the test runs fast.
                #
                # Trick: the tool_use timestamp the watchdog records is
                # "when the watchdog first saw it" (wall-clock now), not
                # "when the event was emitted". So the stalled
                # detection only fires after `timeout_s` seconds. Use
                # 0.5s so the test completes in ~1s.
                watchdog = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "bench.timeout_watchdog",
                        "--jsonl",
                        jsonl_path,
                        "--parent-pid",
                        str(stub.pid),
                        "--timeout-seconds",
                        "0.5",
                        "--overall-timeout-seconds",
                        "10",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                )
                try:
                    # Wait for the stub to receive SIGINT and exit (42).
                    rc = stub.wait(timeout=10)
                    self.assertEqual(
                        rc,
                        42,
                        f"stub did not receive SIGINT — exited rc={rc}",
                    )

                    # Watchdog should now notice the parent is gone and
                    # exit on its own.
                    wrc = watchdog.wait(timeout=5)
                    self.assertIn(
                        wrc,
                        (0, 1),
                        f"watchdog exited unexpectedly with rc={wrc}",
                    )

                    # Sentinel must have been appended to the JSONL.
                    with open(jsonl_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    self.assertIn("watchdog_timeout", text)
                finally:
                    try:
                        watchdog.terminate()
                        watchdog.wait(timeout=2)
                    except Exception:
                        pass
        finally:
            try:
                stub.kill()
                stub.wait(timeout=2)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
