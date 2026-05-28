"""Failure-attribution taxonomy for the web-agent MCP benchmark.

Every sub-rubric score < 5 carries a tag explaining WHY: one of
`tool-bug`, `env-mismatch`, `target-flag`, `transient`. This module
defines the classifier and the transient-failure pattern set used by
`bench.transient.retry_stage` to decide whether to retry a stage.

Design contract — see `.planning/phases/01-harness-foundation/01-CONTEXT.md`:

  > Retry gate + transient taxonomy — `bench/transient.py` implements
  > 3-pass-of-3 with explicit transient classifier (WebSocket 1001/1006,
  > ECONNRESET, MCP `initialize` timeout, HTTP 429/503, Chromium SIGKILL).

This module is the classifier half of that contract; `bench/transient.py`
is the retry-loop half. They are split so the classifier can be reused
by `scripts/aggregate_scores.py` when it tags sub-rubric scores < 5.

Pure-Python, no third-party deps — keep it cheap to import from inside
both the watchdog and the score aggregator.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Union

# ─── Transient pattern set ─────────────────────────────────────────────
#
# Every regex below must be one of the categories enumerated in the
# CONTEXT.md decision. Adding to this list expands what the retry gate
# considers a transient (retry-eligible) failure rather than a recorded
# reliability hit. Adding a pattern is a fairness-policy change — do not
# loosen this list without updating `scoring/rubric_notes.md` too.
#
# Patterns are case-insensitive; we compile them with re.IGNORECASE in
# `is_transient`.

TRANSIENT_PATTERNS: list[str] = [
    # WebSocket close codes 1001 (going away) and 1006 (abnormal close).
    # These cover the BrowserMCP mid-session disconnect class that tanked
    # the 2026-03 wave's Reliability score for that MCP.
    r"WebSocket.*(1001|1006)",
    r"(1001|1006).*WebSocket",
    # TCP-layer reset by the peer. Common when target site rate-limits
    # or an upstream load balancer recycles a connection.
    r"ECONNRESET",
    r"connection reset by peer",
    # MCP lifecycle `initialize` JSON-RPC timeout. Documented for
    # browser-use 0.12.x in browser-tools.md 2026-05-21; tagged transient
    # because the next attempt usually succeeds on a fresh stdio pipe.
    r"MCP.*initialize.*timeout",
    r"initialize.*timeout.*MCP",
    # Target-site soft-fail: 429 Too Many Requests, 503 Service
    # Unavailable. Word-boundaries so we don't accidentally match
    # something like `4291` in a hex dump.
    r"HTTP.*\b(429|503)\b",
    r"\b(429|503)\b.*HTTP",
    # OS killed our Chromium child. On macOS this often comes from App
    # Nap when the laptop closes; on Linux from the OOM killer.
    r"Chromium.*SIGKILL",
    r"SIGKILL.*Chromium",
    r"SIGTERM.*chromium",
    # npm registry hiccup during a cold-cache run (rare but real;
    # caught in the 2026-05 dry-run).
    r"npm registry.*unreachable",
    r"npm.*ETIMEDOUT",
    # macOS App Nap stalls long-running sessions. Logged transient so
    # the retry gate doesn't bake an OS power-management quirk into the
    # candidate's reliability column.
    r"App Nap",
    # EAGAIN: resource temporarily unavailable. Usually transient pipe
    # backpressure during heavy stream-json output.
    r"EAGAIN",
    r"resource temporarily unavailable",
]


_COMPILED_TRANSIENT = [re.compile(p, re.IGNORECASE) for p in TRANSIENT_PATTERNS]


# ─── Failure-attribution tag enum ──────────────────────────────────────
#
# Every sub-rubric score < 5 in `scores.json` carries one of these tags
# in the `attribution` map. Keys are short kebab-case so they're
# readable in the published matrix's notes column.


class FailureTag(str, Enum):
    """The four categories of failure-attribution for sub-rubric scores < 5."""

    TOOL_BUG = "tool-bug"          # The MCP did something we didn't expect (default).
    ENV_MISMATCH = "env-mismatch"  # Wrong binary arch, missing dep, command not found.
    TARGET_FLAG = "target-flag"    # The target site refused us (404, bot block, gone).
    TRANSIENT = "transient"        # Matches TRANSIENT_PATTERNS — retry-eligible.


# Secondary patterns used to discriminate between non-transient tags.
# These run AFTER the transient check fails (so `transient` always wins).

_TARGET_FLAG_PATTERNS = [
    re.compile(r"\b(404|410)\b", re.IGNORECASE),
    re.compile(r"target.*unreachable", re.IGNORECASE),
    re.compile(r"fixture.*404", re.IGNORECASE),
    re.compile(r"page not found", re.IGNORECASE),
    re.compile(r"bot.{0,20}(block|detect|challenge)", re.IGNORECASE),
    re.compile(r"cloudflare.*challenge", re.IGNORECASE),
    re.compile(r"captcha", re.IGNORECASE),
]

_ENV_MISMATCH_PATTERNS = [
    re.compile(r"\barm64\b", re.IGNORECASE),
    re.compile(r"\bx86_64\b", re.IGNORECASE),
    re.compile(r"architecture", re.IGNORECASE),
    re.compile(r"missing.*binary", re.IGNORECASE),
    re.compile(r"command not found", re.IGNORECASE),
    re.compile(r"no such file or directory", re.IGNORECASE),
    re.compile(r"executable not found", re.IGNORECASE),
    re.compile(r"incompatible.*platform", re.IGNORECASE),
    # uv tool / npm install bombs
    re.compile(r"ENOENT", re.IGNORECASE),
]


# ─── Public API ────────────────────────────────────────────────────────


def _coerce_to_str(exc_or_log: Union[str, BaseException]) -> str:
    """Accept either a string or an exception; return the string form."""
    if isinstance(exc_or_log, BaseException):
        # Combine class name + message so an `AttributeError: ...` keeps
        # the class hint when it gets classified.
        return f"{type(exc_or_log).__name__}: {exc_or_log}"
    return str(exc_or_log)


def is_transient(exc_or_log: Union[str, BaseException]) -> bool:
    """Return True if the message matches any TRANSIENT_PATTERNS regex.

    Used by both `retry_stage` (to decide whether to keep retrying) and
    `aggregate_scores.py` (to tag the row).
    """
    s = _coerce_to_str(exc_or_log)
    return any(pat.search(s) for pat in _COMPILED_TRANSIENT)


def attribute_failure(exc_or_log: Union[str, BaseException]) -> FailureTag:
    """Classify a failure into one of four FailureTag values.

    Priority (top wins):
      1. TRANSIENT — matches any TRANSIENT_PATTERNS regex
      2. TARGET_FLAG — 404/410, "target unreachable", bot-block language
      3. ENV_MISMATCH — arch mismatch, missing binary, command not found
      4. TOOL_BUG — default; "the MCP did something we didn't expect"

    The default is TOOL_BUG by design: an unclassified failure should
    point the finger at the MCP (the thing under test), not at the
    environment or the target. The benchmark's job is to surface
    MCP-quality differences; if we cannot prove otherwise, the MCP wears
    the failure.
    """
    s = _coerce_to_str(exc_or_log)

    if is_transient(s):
        return FailureTag.TRANSIENT

    for pat in _TARGET_FLAG_PATTERNS:
        if pat.search(s):
            return FailureTag.TARGET_FLAG

    for pat in _ENV_MISMATCH_PATTERNS:
        if pat.search(s):
            return FailureTag.ENV_MISMATCH

    return FailureTag.TOOL_BUG


__all__ = [
    "FailureTag",
    "TRANSIENT_PATTERNS",
    "is_transient",
    "attribute_failure",
]
