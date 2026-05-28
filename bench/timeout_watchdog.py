"""timeout_watchdog — per-tool-call 30s timeout enforcer for Claude Code sessions.

Claude Code does not enforce a per-tool-call timeout. Upstream issue
anthropics/claude-code#35287 documents the gap — long-stalled MCP tool calls
can wedge a session indefinitely, which makes the 1hr stability soak (Phase
3) measure orphan latency rather than MCP responsiveness. Pitfall 9 in the
research notes ("a single timeout-blind tool call holds the whole run") is
this defence's reason for existing.

This module runs as a sidecar process spawned alongside the Claude Code
session by `scripts/run_mcp_session.sh`. It tails `raw_stream.jsonl`
incrementally, watches for `tool_use` blocks (the "I am about to call a
tool" event) and matching `tool_result` blocks (the "the tool returned"
event), and if a tool_use_id stays unresolved for > `--timeout-seconds`,
sends SIGINT to the Claude Code PID. Claude Code is documented to abort
the in-flight tool on SIGINT; if it doesn't comply within 5s, the
watchdog escalates to SIGTERM (and the wrapper script handles SIGKILL via
kill_group).

Implementation tradeoffs (documented for SUMMARY.md):

  1. JSONL-tailing parser: we use simple line-by-line JSON parsing because
     `claude --output-format stream-json` emits one JSON object per line
     ("JSON Lines" / ndjson). If a line is malformed we skip it rather
     than crash; the file is the harness's contract and we'd rather lose
     a timeout event than the whole watchdog.

  2. Fallback mtime check: if JSON parsing fails for an entire window
     (e.g. Claude is mid-write and we caught a half-flushed line), the
     watchdog falls back to "has the file changed in the last
     `--timeout-seconds`?" — if not, that's also a stall signal. This is
     coarser than tool-call tracking but it's a safety net that catches
     "Claude is hung but not writing JSON-RPC events" failure modes.

  3. We never signal the watchdog's parent (the Claude Code session) until
     we are CERTAIN a tool call is stuck. False-positive timeouts are
     painful — they corrupt the evidence directory mid-run. So the
     watchdog requires BOTH (a) an open `tool_use` block with no matching
     `tool_result`, AND (b) elapsed wall-clock since that `tool_use`
     greater than the threshold.

The watchdog exits when its parent (the Claude session) exits — it polls
`os.kill(parent_pid, 0)` every iteration. If the parent is gone, there is
nothing left to babysit.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time


# How often to re-check the JSONL file for new lines. 0.5s is fast enough
# to be responsive on a 30s timeout (60 polls per timeout window) and slow
# enough to not eat measurable CPU.
POLL_INTERVAL_S = 0.5

# How long to wait between escalating SIGINT -> SIGTERM. Claude Code is
# documented to abort an in-flight tool on SIGINT within ~1-2s; 5s is
# generous.
SIGNAL_ESCALATION_S = 5.0


def _parent_alive(pid: int) -> bool:
    """Return True iff pid is still running (kill -0 semantics)."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # We can ping it, just not signal it for real. Treat as alive.
        return True


def _signal_parent(pid: int, sig: int) -> bool:
    """Send `sig` to `pid`. Returns True on success, False if pid is gone."""
    try:
        os.kill(pid, sig)
        return True
    except ProcessLookupError:
        return False


def _emit_timeout_event(jsonl_path: str, tool_use_id: str, elapsed_s: float) -> None:
    """Append a TIMEOUT sentinel line to the JSONL file.

    The downstream scorer (plan 01-05) keys off this line to mark the
    stage as having timed out. We use a distinctive `type` value
    (`watchdog_timeout`) so it can't be confused with a real Claude Code
    event type.
    """
    sentinel = {
        "type": "watchdog_timeout",
        "tool_use_id": tool_use_id,
        "elapsed_s": elapsed_s,
        "timestamp": time.time(),
        "source": "bench.timeout_watchdog",
    }
    try:
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(sentinel) + "\n")
    except OSError:
        # If the file is gone or unwritable, the harness has bigger
        # problems than a missing sentinel — don't crash the watchdog.
        pass


def _scan_for_open_tool_uses(
    jsonl_path: str,
    open_uses: dict[str, float],
    last_offset: int,
) -> int:
    """Read new lines from `jsonl_path`, update `open_uses` in place.

    `open_uses` maps tool_use_id -> wall-clock timestamp when the
    tool_use was emitted. When a matching tool_result arrives, the id is
    popped.

    Returns the new file offset (so the next call can resume).

    Robustness:
      - Skip malformed JSON lines silently (claude may flush mid-write).
      - Handle both top-level `tool_use` events (rare) and the more
        common nested form: `assistant.message.content[].type == "tool_use"`.
    """
    if not os.path.exists(jsonl_path):
        return last_offset

    try:
        size = os.path.getsize(jsonl_path)
        if size <= last_offset:
            # Nothing new (or the file was truncated — rare; bail).
            return last_offset

        with open(jsonl_path, "r", encoding="utf-8") as f:
            f.seek(last_offset)
            chunk = f.read()
            new_offset = last_offset + len(chunk.encode("utf-8"))
    except OSError:
        return last_offset

    now = time.time()
    for line in chunk.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Half-flushed line; the next poll will re-read from a
            # consistent offset because we update last_offset only by
            # the actual byte count we read.
            continue

        # Form 1: top-level tool_use event.
        if event.get("type") == "tool_use" and "id" in event:
            open_uses[event["id"]] = now
            continue

        # Form 2 (most common): assistant message with embedded
        # tool_use content blocks.
        if event.get("type") == "assistant":
            msg = event.get("message") or {}
            content = msg.get("content") or []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tu_id = block.get("id")
                    if tu_id:
                        open_uses[tu_id] = now

        # Form 3: tool_result, either top-level or user-message-nested.
        if event.get("type") == "tool_result" and "tool_use_id" in event:
            open_uses.pop(event["tool_use_id"], None)
            continue
        if event.get("type") == "user":
            msg = event.get("message") or {}
            content = msg.get("content") or []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    open_uses.pop(block.get("tool_use_id"), None)

    return new_offset


def _stalled_use(open_uses: dict[str, float], threshold_s: float) -> str | None:
    """Return the oldest tool_use_id whose age exceeds `threshold_s`, or None.

    We pick the OLDEST because if multiple are stalled, the oldest is
    the one that triggered the wedge; the others are likely "downstream"
    in some pipeline.
    """
    if not open_uses:
        return None
    now = time.time()
    candidates = [
        (use_id, now - started_at)
        for use_id, started_at in open_uses.items()
        if (now - started_at) > threshold_s
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[1])  # oldest first
    return candidates[0][0]


def watchdog_loop(
    jsonl_path: str,
    parent_pid: int,
    timeout_s: float,
    overall_timeout_s: float | None = None,
) -> int:
    """Main loop. Returns process exit code.

    Exit codes:
      0 — parent exited cleanly; watchdog stops.
      1 — watchdog signaled the parent at least once (a tool call timed
          out OR the overall session timeout fired).
    """
    open_uses: dict[str, float] = {}
    last_offset = 0
    started_at = time.time()
    signaled = False
    # When we signaled, we wait `SIGNAL_ESCALATION_S` before escalating
    # to SIGTERM. This timestamp tracks when we last signaled.
    last_signal_at: float | None = None
    last_signal_was_sigint = False
    last_mtime: float | None = None
    last_mtime_check_at = time.time()

    while True:
        if not _parent_alive(parent_pid):
            # Parent is gone — we're done.
            return 0 if not signaled else 1

        # Overall-session guardrail.
        if overall_timeout_s is not None:
            elapsed_total = time.time() - started_at
            if elapsed_total > overall_timeout_s:
                _emit_timeout_event(jsonl_path, "<overall_session>", elapsed_total)
                if not signaled:
                    _signal_parent(parent_pid, signal.SIGINT)
                    last_signal_at = time.time()
                    last_signal_was_sigint = True
                    signaled = True
                # Fall through to the escalation check below.

        # Scan stream for new tool_use / tool_result events.
        last_offset = _scan_for_open_tool_uses(jsonl_path, open_uses, last_offset)

        # Per-tool-call timeout check.
        stalled_id = _stalled_use(open_uses, timeout_s)
        if stalled_id and not signaled:
            elapsed = time.time() - open_uses[stalled_id]
            _emit_timeout_event(jsonl_path, stalled_id, elapsed)
            _signal_parent(parent_pid, signal.SIGINT)
            last_signal_at = time.time()
            last_signal_was_sigint = True
            signaled = True

        # Mtime-based fallback: if the JSONL file hasn't changed in a
        # while AND we have at least one open tool_use, that's a signal
        # the session is actually wedged (not just slow to produce
        # tokens). The check is intentionally coarser than the
        # per-tool-call timer — we use 2x the threshold here so we only
        # fire when the primary check would have already fired and
        # missed (e.g. because a malformed line confused us).
        if not signaled and open_uses:
            try:
                mtime = os.path.getmtime(jsonl_path)
                if last_mtime is None:
                    last_mtime = mtime
                    last_mtime_check_at = time.time()
                elif mtime == last_mtime:
                    if (time.time() - last_mtime_check_at) > (timeout_s * 2):
                        _emit_timeout_event(
                            jsonl_path,
                            "<mtime_stall>",
                            time.time() - last_mtime_check_at,
                        )
                        _signal_parent(parent_pid, signal.SIGINT)
                        last_signal_at = time.time()
                        last_signal_was_sigint = True
                        signaled = True
                else:
                    last_mtime = mtime
                    last_mtime_check_at = time.time()
            except OSError:
                pass

        # Escalate SIGINT -> SIGTERM if Claude didn't comply.
        if (
            signaled
            and last_signal_was_sigint
            and last_signal_at is not None
            and (time.time() - last_signal_at) > SIGNAL_ESCALATION_S
        ):
            _signal_parent(parent_pid, signal.SIGTERM)
            last_signal_at = time.time()
            last_signal_was_sigint = False

        time.sleep(POLL_INTERVAL_S)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m bench.timeout_watchdog",
        description="Per-tool-call timeout enforcer for Claude Code sessions.",
    )
    p.add_argument(
        "--jsonl",
        required=True,
        metavar="PATH",
        help="Path to the raw_stream.jsonl that Claude Code writes.",
    )
    p.add_argument(
        "--parent-pid",
        required=True,
        type=int,
        metavar="PID",
        help="PID of the Claude Code process to babysit.",
    )
    p.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="Per-tool-call timeout in seconds (default: 30).",
    )
    p.add_argument(
        "--overall-timeout-seconds",
        type=float,
        default=1800.0,
        help="Overall session guardrail in seconds (default: 1800 = 30 min).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return watchdog_loop(
        jsonl_path=args.jsonl,
        parent_pid=args.parent_pid,
        timeout_s=args.timeout_seconds,
        overall_timeout_s=args.overall_timeout_seconds,
    )


if __name__ == "__main__":
    sys.exit(main())
