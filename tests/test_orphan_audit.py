"""test_orphan_audit — unit tests for the orphan-audit pre/post diff CLI.

We exercise two scenarios:

1. `_diff_pids` correctly identifies a survivor when the after-snapshot
   contains a process matching either the target PGID or the MCP cmdline
   regex. We synthesize the snapshots in-memory rather than spawning real
   processes for this test — it's a pure-function check, no kill required.

2. End-to-end: spawn a real `sleep` under setsid, take a before-snapshot,
   take an after-snapshot, run the audit with the spawned process's PGID,
   verify the survivor is in the diff and gets SIGKILL'd. This is the
   integration test the plan calls for.

The synthetic test runs in <100ms; the integration test sleeps briefly to
let the spawned process appear in `ps`. Both are unittest-style so `uv run
python -m unittest tests.test_orphan_audit` is the verify command.
"""

from __future__ import annotations

import os
import signal
import tempfile
import time
import unittest

from bench.orphan_audit import _diff_pids, cmd_diff, cmd_snapshot_only
from bench.process_group import (
    kill_group,
    pgid_of,
    snapshot_ps,
    spawn_setsid,
    write_ps_snapshot,
)


def _is_alive(pid: int) -> bool:
    """Return True iff `pid` still exists (kill -0 semantics)."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


class DiffPidsTest(unittest.TestCase):
    """Pure-function tests on `_diff_pids` with synthetic snapshots."""

    def test_pid_in_before_is_not_flagged(self) -> None:
        before = [{"pid": 100, "ppid": 1, "pgid": 100, "rss": 1024, "command": "chromium"}]
        after = [{"pid": 100, "ppid": 1, "pgid": 100, "rss": 1024, "command": "chromium"}]
        self.assertEqual(_diff_pids(before, after, target_pgid=100), [])

    def test_new_pid_matching_pgid_is_flagged(self) -> None:
        before: list = []
        after = [{"pid": 200, "ppid": 100, "pgid": 100, "rss": 2048, "command": "/bin/sh -c sleep 99"}]
        survivors = _diff_pids(before, after, target_pgid=100)
        self.assertEqual(len(survivors), 1)
        self.assertEqual(int(survivors[0]["pid"]), 200)

    def test_new_pid_matching_cmd_regex_is_flagged(self) -> None:
        # PGID doesn't match the target — only the cmdline regex does.
        # This is the "rogue Chromium under a different group" case.
        before: list = []
        after = [
            {
                "pid": 300,
                "ppid": 1,
                "pgid": 99999,
                "rss": 4096,
                "command": "/Applications/Chromium.app/Contents/MacOS/chromium --headless",
            }
        ]
        survivors = _diff_pids(before, after, target_pgid=100)
        self.assertEqual(len(survivors), 1)

    def test_new_pid_unrelated_is_ignored(self) -> None:
        # A new process that's not in the PGID and not an MCP-related
        # command must NOT be flagged — we don't kill the user's editor.
        before: list = []
        after = [{"pid": 400, "ppid": 1, "pgid": 99999, "rss": 8192, "command": "vim"}]
        self.assertEqual(_diff_pids(before, after, target_pgid=100), [])

    def test_cmd_regex_is_case_insensitive(self) -> None:
        before: list = []
        after = [
            {"pid": 500, "ppid": 1, "pgid": 99999, "rss": 1024, "command": "PLAYWRIGHT-MCP"}
        ]
        self.assertEqual(len(_diff_pids(before, after, target_pgid=100)), 1)


class IntegrationTest(unittest.TestCase):
    """End-to-end: spawn a real sleep, audit, kill, verify clean."""

    def test_spawned_sleep_is_detected_and_killed(self) -> None:
        # Realistic harness flow: take a before-snapshot, spawn a sleep
        # under setsid with an MCP-matching cmdline, take an after-snapshot,
        # diff. Only the newly-spawned process should appear as a
        # survivor (real harness runs may have pre-existing chromium
        # processes on the host — those are in `before` and are correctly
        # excluded by the set-difference).
        #
        # We pre-snapshot first, then spawn, so the diff isolates exactly
        # one new PID.
        with tempfile.TemporaryDirectory() as tmp:
            before_path = os.path.join(tmp, "before.tsv")
            after_path = os.path.join(tmp, "after.tsv")
            log_path = os.path.join(tmp, "orphan_audit.log")

            # Real before-snapshot — captures everything currently
            # running, including any pre-existing chromium / playwright
            # processes the dev host may have.
            write_ps_snapshot(before_path)

            # Spawn the synthetic survivor. We use `/bin/sh -c` so the
            # command line contains the MCP-matching token "lightpanda"
            # — that way the cmdline-regex branch is exercised too, not
            # just the PGID branch.
            proc = spawn_setsid(
                ["/bin/sh", "-c", "exec -a lightpanda-test-orphan sleep 30"]
            )
            try:
                # Wait briefly for `ps` to see the process.
                time.sleep(0.2)
                self.assertTrue(_is_alive(proc.pid), "sleep died before audit")
                spawned_pgid = pgid_of(proc.pid)

                # Real after-snapshot — captures the same baseline PLUS
                # our synthetic survivor.
                write_ps_snapshot(after_path)

                rc = cmd_diff(before_path, after_path, spawned_pgid, log_path)
                self.assertEqual(rc, 1, f"expected survivors but got rc={rc}")

                with open(log_path, "r", encoding="utf-8") as f:
                    log_text = f.read()
                # The log must mention our spawned process — either by
                # pid or by the lightpanda-test-orphan token we baked
                # into the cmdline.
                self.assertTrue(
                    f"pid={proc.pid}" in log_text
                    or "lightpanda-test-orphan" in log_text,
                    f"audit log did not mention spawned pid {proc.pid}:\n{log_text}",
                )

                # Wait for the Popen to reap the zombie. macOS `kill -0`
                # returns success on a zombie process (it has a PID and a
                # signalable state until waited on), so we can't poll
                # liveness with os.kill alone — we have to call
                # proc.wait() to drain the zombie. A successful SIGKILL
                # shows up as returncode == -SIGKILL (-9).
                proc.wait(timeout=5)
                self.assertEqual(
                    proc.returncode,
                    -signal.SIGKILL,
                    f"expected sleep killed by SIGKILL, got rc={proc.returncode}",
                )
            finally:
                # Belt-and-suspenders cleanup — in case the audit didn't
                # kill (test failure path) we still don't want a 30s
                # sleep accumulating on the test host.
                try:
                    kill_group(pgid_of(proc.pid), grace_s=0.1)
                except ProcessLookupError:
                    pass
                # Reap the Popen so it doesn't show up as a zombie.
                try:
                    proc.wait(timeout=2)
                except Exception:
                    try:
                        os.kill(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                # Close the pipes Popen opened so the file descriptors
                # don't leak between tests (silences ResourceWarning).
                for stream in (proc.stdout, proc.stderr, proc.stdin):
                    if stream is not None:
                        try:
                            stream.close()
                        except Exception:
                            pass

    def test_snapshot_only_writes_nonempty_file(self) -> None:
        """`--snapshot-only` mode writes a file with at least the header + 1 row."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ps.tsv")
            rc = cmd_snapshot_only(path)
            self.assertEqual(rc, 0)
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # Header + at least the running test process.
            self.assertGreater(len(lines), 1)
            self.assertTrue(lines[0].startswith("pid"))

    def test_clean_window_returns_zero(self) -> None:
        """If nothing new appeared, diff exits 0 and orphans=0."""
        # Take two snapshots back-to-back with nothing newly spawned.
        # The diff should find no MCP-related new PIDs.
        with tempfile.TemporaryDirectory() as tmp:
            before_path = os.path.join(tmp, "before.tsv")
            after_path = os.path.join(tmp, "after.tsv")
            log_path = os.path.join(tmp, "orphan_audit.log")

            write_ps_snapshot(before_path)
            # Tiny delay so any short-lived processes settle.
            time.sleep(0.05)
            write_ps_snapshot(after_path)

            # Use a PGID that nothing on this host could realistically own
            # — INT32 max minus a small offset is safe (kernel PIDs are
            # nowhere near this on macOS / Linux desktop sessions).
            rc = cmd_diff(before_path, after_path, 2147483600, log_path)
            self.assertEqual(rc, 0, "expected clean window (rc=0)")

            with open(log_path, "r", encoding="utf-8") as f:
                log_text = f.read()
            self.assertIn("ORPHANS=0", log_text)


if __name__ == "__main__":
    unittest.main()
