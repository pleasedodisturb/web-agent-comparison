"""Tests for bench.failure_taxonomy.

Covers the 5 named transient categories from CONTEXT.md plus the
non-transient classifier branches (target-flag, env-mismatch, tool-bug).
"""

from __future__ import annotations

import unittest

from bench.failure_taxonomy import (
    FailureTag,
    TRANSIENT_PATTERNS,
    attribute_failure,
    is_transient,
)


class TestIsTransient(unittest.TestCase):
    """The 5 named CONTEXT.md transient categories must each classify as transient."""

    def test_websocket_1001(self) -> None:
        self.assertTrue(is_transient("WebSocket closed with code 1001 going away"))

    def test_websocket_1006(self) -> None:
        self.assertTrue(is_transient("Abnormal closure: WebSocket code 1006"))

    def test_econnreset(self) -> None:
        self.assertTrue(is_transient("Error: ECONNRESET during read"))
        self.assertTrue(is_transient("connection reset by peer"))

    def test_mcp_initialize_timeout(self) -> None:
        self.assertTrue(is_transient("MCP server initialize timeout after 30s"))
        self.assertTrue(is_transient("initialize JSON-RPC timeout on the MCP stdio pipe"))

    def test_http_429_503(self) -> None:
        self.assertTrue(is_transient("HTTP 429 Too Many Requests from greenhouse.io"))
        self.assertTrue(is_transient("Got HTTP 503 Service Unavailable"))

    def test_chromium_sigkill(self) -> None:
        self.assertTrue(is_transient("Chromium killed by SIGKILL"))
        self.assertTrue(is_transient("SIGTERM chromium subprocess"))

    def test_npm_registry(self) -> None:
        self.assertTrue(is_transient("npm registry unreachable: ENETUNREACH"))

    def test_app_nap(self) -> None:
        self.assertTrue(is_transient("App Nap stalled session for 60s"))

    def test_eagain(self) -> None:
        self.assertTrue(is_transient("write failed: EAGAIN"))
        self.assertTrue(is_transient("resource temporarily unavailable"))

    def test_accepts_exception_instance(self) -> None:
        """is_transient should accept Exception objects, not just strings."""
        exc = RuntimeError("ECONNRESET while reading response")
        self.assertTrue(is_transient(exc))

    def test_case_insensitive(self) -> None:
        """Patterns must be case-insensitive — vendors capitalize differently."""
        self.assertTrue(is_transient("econnreset"))
        self.assertTrue(is_transient("websocket 1006"))

    def test_non_transient_returns_false(self) -> None:
        self.assertFalse(is_transient("AttributeError: 'NoneType' has no attribute 'page'"))
        self.assertFalse(is_transient("zsh: command not found: obscura-mcp"))
        self.assertFalse(is_transient("HTTP 404 Not Found"))

    def test_pattern_count_is_at_least_minimum(self) -> None:
        """Sanity check: the documented minimum patterns must be present."""
        # CONTEXT.md mandates a specific minimum set; check the count is
        # at least the 5 categories times the number of variants we ship.
        self.assertGreaterEqual(len(TRANSIENT_PATTERNS), 9)


class TestAttributeFailure(unittest.TestCase):
    """attribute_failure must dispatch through the documented priority order."""

    def test_transient_wins_over_other_signals(self) -> None:
        # A message that contains BOTH a 429 (transient) AND a 404
        # (target-flag) must classify as transient — transient is the
        # highest priority because the response could change on retry.
        msg = "HTTP 429 Too Many Requests; also saw 404 earlier"
        self.assertEqual(attribute_failure(msg), FailureTag.TRANSIENT)

    def test_econnreset_classifies_transient(self) -> None:
        tag = attribute_failure("ECONNRESET while reading from MCP stdio")
        self.assertEqual(tag, FailureTag.TRANSIENT)

    def test_http_404_classifies_target_flag(self) -> None:
        tag = attribute_failure("HTTP 404 from greenhouse.io/jobs/123")
        self.assertEqual(tag, FailureTag.TARGET_FLAG)

    def test_target_unreachable_classifies_target_flag(self) -> None:
        tag = attribute_failure("target unreachable: dns lookup failed")
        self.assertEqual(tag, FailureTag.TARGET_FLAG)

    def test_command_not_found_classifies_env_mismatch(self) -> None:
        tag = attribute_failure("zsh: command not found: obscura-mcp")
        self.assertEqual(tag, FailureTag.ENV_MISMATCH)

    def test_arch_mismatch_classifies_env_mismatch(self) -> None:
        tag = attribute_failure("incompatible platform: binary is x86_64 on arm64 host")
        self.assertEqual(tag, FailureTag.ENV_MISMATCH)

    def test_missing_binary_classifies_env_mismatch(self) -> None:
        tag = attribute_failure("missing binary: ENOENT /usr/local/bin/lightpanda")
        self.assertEqual(tag, FailureTag.ENV_MISMATCH)

    def test_attribute_error_classifies_tool_bug_by_default(self) -> None:
        """Default (unmatched) failures point the finger at the MCP under test."""
        tag = attribute_failure("AttributeError: 'NoneType' object has no attribute 'page'")
        self.assertEqual(tag, FailureTag.TOOL_BUG)

    def test_generic_traceback_classifies_tool_bug(self) -> None:
        tag = attribute_failure("TypeError: unexpected keyword argument 'ref'")
        self.assertEqual(tag, FailureTag.TOOL_BUG)

    def test_accepts_exception_instance(self) -> None:
        """attribute_failure must accept Exception objects, not just strings."""
        exc = ValueError("unexpected None")
        # ValueError default text classifies as TOOL_BUG (the default).
        self.assertEqual(attribute_failure(exc), FailureTag.TOOL_BUG)

    def test_failure_tag_is_str_enum(self) -> None:
        """FailureTag must be string-compatible so it round-trips through JSON."""
        self.assertEqual(FailureTag.TRANSIENT.value, "transient")
        self.assertEqual(FailureTag.TOOL_BUG.value, "tool-bug")
        self.assertEqual(FailureTag.ENV_MISMATCH.value, "env-mismatch")
        self.assertEqual(FailureTag.TARGET_FLAG.value, "target-flag")

    def test_priority_order_target_beats_env(self) -> None:
        """Target-flag (404) wins over env-mismatch (command not found) when both appear."""
        # Both signals present: a 404 from a missing binary path. The
        # priority order docs say TARGET_FLAG > ENV_MISMATCH.
        msg = "HTTP 404 returned; command not found"
        # is_transient is False → falls to target-flag.
        self.assertEqual(attribute_failure(msg), FailureTag.TARGET_FLAG)


if __name__ == "__main__":
    unittest.main()
