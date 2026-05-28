"""process_group — setsid-based process-group helpers for the MCP harness.

The web-agent-comparison harness spawns each MCP under test as a child of a
Claude Code session. MCPs frequently fork sub-processes (Chromium, Node,
Python helpers) that survive the parent if not actively reaped. The 2026-05
testbench documented multiple cases where a wedged MCP left chromium
processes resident for hours; Pitfall 9 ("orphan accumulation") is the
documented failure mode and the 1hr stability soak test in Phase 3 is a lie
without process-group cleanup.

This module is the foundation of Phase 1's defence:

  * `spawn_setsid` runs the child in a new session (= new process group, =
    setsid(2) semantics) via `subprocess.Popen(start_new_session=True)`. The
    returned Popen object exposes `pid`; the process-group id is the same
    integer (since the child is the group leader).

  * `kill_group` sends SIGTERM to the whole group, sleeps a grace period,
    then SIGKILL. Both signals are routed via `os.killpg`, which is the only
    portable way to nuke an entire process tree without manually walking
    `pgrep -P` (which races descendants).

  * `snapshot_ps` shells out to BSD `ps` (macOS) / GNU `ps` (Linux) and
    returns a list of dicts. The shell-out is intentional: cross-platform
    /proc parsing is fragile, `ps -axo ...` is portable.

This file is imported by `bench.orphan_audit` (the CLI that compares
before/after snapshots) and by `scripts/run_mcp_session.sh` (via a small
inline Python invocation). Keep the API tiny and predictable.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from typing import Optional


def spawn_setsid(
    argv: list[str],
    env: Optional[dict[str, str]] = None,
    cwd: Optional[str] = None,
    stdin: int = subprocess.DEVNULL,
    stdout: int = subprocess.PIPE,
    stderr: int = subprocess.PIPE,
) -> subprocess.Popen[bytes]:
    """Spawn `argv` in a brand-new session (a.k.a. a new process group).

    `start_new_session=True` is Python's portable wrapper around
    `setsid(2)`: it makes the child the leader of a new session and a new
    process group, so the child's PID equals its PGID. Any sub-process the
    child spawns inherits the PGID by default (until something inside calls
    `setpgid` or `setsid` itself), so `os.killpg(pgid, sig)` reliably
    delivers the signal to every descendant.

    Parameters
    ----------
    argv
        Argument vector; argv[0] is the executable.
    env
        Override environment. Pass `None` to inherit; pass an empty dict to
        get an empty env (rarely what you want).
    cwd
        Working directory for the child. `None` inherits.
    stdin, stdout, stderr
        Standard `subprocess` file descriptor handling. Defaults capture
        stdout/stderr to pipes and detach stdin to /dev/null — appropriate
        for an MCP we'll talk to via JSON-RPC over stdout-tail, not stdin.

    Returns
    -------
    subprocess.Popen
        The Popen handle. `.pid` is both the PID and the PGID.
    """
    return subprocess.Popen(
        argv,
        env=env,
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
        close_fds=True,
    )


def pgid_of(pid: int) -> int:
    """Return the process-group id for `pid`.

    Thin wrapper over `os.getpgid` so callers don't import `os` just for
    this. Raises `ProcessLookupError` if the process is gone (race with
    cleanup is the usual cause).
    """
    return os.getpgid(pid)


def kill_group(pgid: int, grace_s: float = 5.0) -> None:
    """Send SIGTERM to a process group, wait `grace_s`, then SIGKILL.

    Both signals are sent via `os.killpg(pgid, sig)` so the entire group
    receives them. The second call swallows `ProcessLookupError` since a
    clean SIGTERM leaves nothing for SIGKILL to find — that's the happy
    path, not an error.

    Parameters
    ----------
    pgid
        Process-group id to kill. Typically the PID of a process spawned by
        `spawn_setsid` (PID == PGID for session leaders).
    grace_s
        Seconds between SIGTERM and SIGKILL. 5s is enough for a
        well-behaved Node/Python MCP to flush logs; longer wastes wall-
        clock on cleanup; shorter risks losing tail-end log lines that the
        evidence directory wants.
    """
    # SIGTERM is the graceful shutdown signal — well-behaved children flush
    # buffers and exit. `ProcessLookupError` here means the group is already
    # gone, which is fine.
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return

    # Sleep for the grace window. We don't poll the group's liveness during
    # the wait because there's no portable way to ask "is process group N
    # empty?" — the closest signal is `kill(-pgid, 0)` which racily returns
    # 0 if any group member is alive. The simpler and equally-safe approach
    # is the fixed grace + SIGKILL; the SIGKILL is harmless if the group is
    # already gone.
    time.sleep(grace_s)

    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        # Group is gone — exactly what we wanted.
        return


def snapshot_ps() -> list[dict[str, str | int]]:
    """Return a list of {pid, ppid, pgid, rss, command} dicts for every process.

    Shells out to `ps -axo pid,ppid,pgid,rss,command` which is the same
    column set on macOS BSD ps and GNU ps. The first line is the header
    (`PID PPID PGID RSS COMMAND`); we skip it.

    `rss` is in kilobytes (POSIX convention; both BSD and GNU agree).
    `command` may contain spaces — we split on whitespace for the first
    four columns and treat the rest as a single command string.

    Returns
    -------
    list[dict]
        One dict per process. `pid`/`ppid`/`pgid`/`rss` are ints;
        `command` is a str.
    """
    out = subprocess.run(
        ["ps", "-axo", "pid,ppid,pgid,rss,command"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    rows: list[dict[str, str | int]] = []
    for i, line in enumerate(out.splitlines()):
        if i == 0:
            # Header row.
            continue
        # Use `split(maxsplit=4)` to keep the command column intact even
        # when it contains spaces (which it always does for real processes).
        parts = line.strip().split(None, 4)
        if len(parts) < 5:
            # Defensive: pad with empty command for processes whose
            # COMMAND column is somehow blank (kernel threads on Linux).
            parts += [""] * (5 - len(parts))
        try:
            rows.append(
                {
                    "pid": int(parts[0]),
                    "ppid": int(parts[1]),
                    "pgid": int(parts[2]),
                    "rss": int(parts[3]),
                    "command": parts[4],
                }
            )
        except ValueError:
            # Skip rows that don't parse — usually a transient race where a
            # process exited mid-snapshot and ps emitted a partial line.
            continue
    return rows


def write_ps_snapshot(path: str) -> int:
    """Write a ps snapshot to `path` and return the row count.

    Format: one process per line, fields tab-separated:
        pid\tppid\tpgid\trss\tcommand

    This is what `bench/orphan_audit.py` reads back via `read_ps_snapshot`.
    Keeping the format trivially-parseable (no JSON, no escaping) means a
    human can `cat` the file during debugging and instantly see the shape.
    """
    rows = snapshot_ps()
    with open(path, "w", encoding="utf-8") as f:
        f.write("pid\tppid\tpgid\trss\tcommand\n")
        for r in rows:
            f.write(f"{r['pid']}\t{r['ppid']}\t{r['pgid']}\t{r['rss']}\t{r['command']}\n")
    return len(rows)


def read_ps_snapshot(path: str) -> list[dict[str, str | int]]:
    """Inverse of `write_ps_snapshot`: parse the tab-separated dump."""
    rows: list[dict[str, str | int]] = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0:
                # Header.
                continue
            parts = line.rstrip("\n").split("\t", 4)
            if len(parts) < 5:
                parts += [""] * (5 - len(parts))
            try:
                rows.append(
                    {
                        "pid": int(parts[0]),
                        "ppid": int(parts[1]),
                        "pgid": int(parts[2]),
                        "rss": int(parts[3]),
                        "command": parts[4],
                    }
                )
            except ValueError:
                continue
    return rows
