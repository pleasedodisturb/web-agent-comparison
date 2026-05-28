"""test_tools_inventory — unit tests for the tools/list categorization.

The MCP-spawn path is covered by an integration smoke test in
`tests/test_run_mcp_session_smoke.sh` (which we re-touch in plan 01-06
when the run script wires this module in). The unit tests here cover
the pure-function pieces:

  - `categorize_tool` — keyword-to-bucket mapping for a representative
    sample of tool names from the 7 candidate MCPs.
  - `load_mcp_spec`   — `.mcp.json` parsing + error paths.
  - `_empty_categories` — every bucket present, zero-valued.
  - `inventory_mcp` failure paths — by feeding a bogus mcp_name and
    asserting the error shape.

Plus a single live-spawn test for playwright (skipped if the binary is
not on PATH) so CI fails loudly if the MCP SDK regresses.

Run with:
    .venv/bin/python -m unittest tests.test_tools_inventory -v
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from bench.tools_inventory import (
    CATEGORY_NAMES,
    DEFAULT_MCP_JSON,
    _empty_categories,
    categorize_tool,
    inventory_mcp,
    load_mcp_spec,
)


class CategorizeToolTests(unittest.TestCase):
    """Hand-picked representative tool names from each of the 7 MCPs."""

    def test_navigation_bucket(self) -> None:
        for name in ("browser_navigate", "page_goto", "navigate_page",
                     "go_back", "reload"):
            self.assertEqual(categorize_tool(name), "navigation", name)

    def test_interaction_bucket(self) -> None:
        for name in ("browser_click", "browser_type", "browser_fill_form",
                     "click", "press_key", "select_option", "hover",
                     "drag_drop", "submit_form", "scroll", "wait_for_selector"):
            self.assertEqual(categorize_tool(name), "interaction", name)

    def test_capture_bucket(self) -> None:
        for name in ("browser_take_screenshot", "screenshot", "save_pdf",
                     "record_video"):
            self.assertEqual(categorize_tool(name), "capture", name)

    def test_diagnostics_bucket(self) -> None:
        for name in ("get_console_messages", "list_network_requests",
                     "evaluate_script", "performance_start_trace",
                     "page_evaluate", "console_log"):
            self.assertEqual(categorize_tool(name), "diagnostics", name)

    def test_inspection_bucket(self) -> None:
        # tools/list-style introspection. Note: "snapshot", "read", "extract",
        # "markdown" are common across the read-only MCPs.
        for name in ("browser_snapshot", "cloak_snapshot", "page_snapshot",
                     "read_page", "extract_text", "scrape", "to_markdown",
                     "list_pages", "find_element"):
            self.assertEqual(categorize_tool(name), "inspection", name)

    def test_other_bucket_catchall(self) -> None:
        # Genuinely unfamiliar names should land in 'other'.
        for name in ("foo_bar", "unknown_action", "thaumaturgy"):
            self.assertEqual(categorize_tool(name), "other", name)

    def test_case_insensitive(self) -> None:
        self.assertEqual(categorize_tool("BROWSER_NAVIGATE"), "navigation")
        self.assertEqual(categorize_tool("Click_Element"), "interaction")


class EmptyCategoriesTests(unittest.TestCase):
    def test_all_six_buckets_present(self) -> None:
        empty = _empty_categories()
        self.assertEqual(set(empty.keys()), set(CATEGORY_NAMES))
        self.assertTrue(all(v == 0 for v in empty.values()))
        # Sanity: exactly 6 buckets per the rubric.
        self.assertEqual(len(empty), 6)


class LoadMcpSpecTests(unittest.TestCase):
    """Reads the project-scope .mcp.json."""

    def test_loads_known_mcp(self) -> None:
        # Playwright is always present in the project .mcp.json per
        # CONTEXT.md "Project-scope .mcp.json with all 7 MCPs".
        spec = load_mcp_spec("playwright")
        self.assertEqual(spec.name, "playwright")
        self.assertTrue(spec.command)  # non-empty

    def test_unknown_mcp_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            load_mcp_spec("definitely-not-a-real-mcp-9999")

    def test_missing_config_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_mcp_spec("playwright", mcp_json_path=Path("/tmp/definitely-not-here.json"))

    def test_from_custom_config(self) -> None:
        # Write a small fake .mcp.json and load from it.
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "mcp.json"
            cfg.write_text(json.dumps({
                "mcpServers": {
                    "fakemcp": {"command": "/bin/echo", "args": ["hello"]},
                }
            }))
            spec = load_mcp_spec("fakemcp", mcp_json_path=cfg)
            self.assertEqual(spec.command, "/bin/echo")
            self.assertEqual(spec.args, ["hello"])


class InventoryMcpFailureTests(unittest.TestCase):
    """inventory_mcp's error shape matches what the harness expects."""

    def test_unknown_mcp_returns_config_error(self) -> None:
        result = inventory_mcp("definitely-not-a-real-mcp")
        self.assertEqual(result["status"], "MCP_CONFIG_ERROR")
        self.assertEqual(result["tool_count"], 0)
        self.assertEqual(set(result["categories"].keys()), set(CATEGORY_NAMES))

    def test_missing_config_returns_config_error(self) -> None:
        result = inventory_mcp(
            "playwright",
            mcp_json_path=Path("/tmp/definitely-not-here.json"),
        )
        self.assertEqual(result["status"], "MCP_CONFIG_ERROR")

    def test_unspawnable_binary_returns_rpc_error(self) -> None:
        """Pointing at /bin/false simulates a binary that immediately
        exits — the MCP SDK should surface this as a connection error.
        We expect status=SPAWN_OR_RPC_ERROR, NOT a crash."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "mcp.json"
            cfg.write_text(json.dumps({
                "mcpServers": {
                    "broken": {"command": "/bin/false", "args": []},
                }
            }))
            result = inventory_mcp("broken", mcp_json_path=cfg, timeout_s=5.0)
            # Status will be SPAWN_OR_RPC_ERROR (the SDK can't talk to a
            # dead child) or INITIALIZE_TIMEOUT (if it sits before
            # noticing). Either is acceptable — both classify as
            # tool-bug for FAIRNESS-06.
            self.assertIn(result["status"],
                          ("SPAWN_OR_RPC_ERROR", "INITIALIZE_TIMEOUT"))
            self.assertEqual(result["tool_count"], 0)


@unittest.skipIf(
    shutil.which("playwright-mcp") is None,
    "playwright-mcp not on PATH — skipping live-spawn smoke",
)
class LivePlaywrightInventoryTest(unittest.TestCase):
    """End-to-end against the real playwright-mcp binary.

    Verifies the SDK plumbing and the tool count, which per RESEARCH §1
    should be in the ~28-tool range for Playwright MCP 0.0.75. We use a
    loose lower bound (>=10) so an upstream patch that adds or removes a
    handful of tools doesn't break the test, but a fundamental break
    (zero tools, timeout) is caught.
    """

    def test_playwright_reports_a_reasonable_tool_count(self) -> None:
        result = inventory_mcp("playwright", timeout_s=30.0)
        self.assertEqual(result.get("status"), "OK",
                         f"Playwright probe failed: {result}")
        # RESEARCH §1 cites ~28 tools for Playwright MCP. Use >=10 as
        # the lower bound to tolerate minor patch-level churn.
        self.assertGreaterEqual(result["tool_count"], 10,
                                f"Suspiciously few tools: {result['tool_count']}")
        # The six-bucket sum equals tool_count.
        self.assertEqual(sum(result["categories"].values()),
                         result["tool_count"])
        # Tools include at least one navigation entry.
        self.assertGreater(result["categories"]["navigation"], 0,
                           f"No navigation tools? {result['categories']}")


if __name__ == "__main__":
    unittest.main()
