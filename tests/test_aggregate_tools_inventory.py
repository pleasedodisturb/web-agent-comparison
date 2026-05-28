"""test_aggregate_tools_inventory — unit tests for the tools-surface rollup.

The aggregator walks `results/<date>/<mcp>/tools_inventory.json` for every
per-MCP subdirectory and emits `TOOLS_INVENTORY_SUMMARY.md` — a side-by-side
6-category breakdown. Gaps are surfaced both in stderr and as a "Gaps"
section in the doc.

Tests cover:

  - Markdown table emission for the happy path (3 MCPs, all OK).
  - Missing-file detection (1 MCP lacks tools_inventory.json).
  - Status surfacing for non-OK probes (INITIALIZE_TIMEOUT row).
  - Roll-up consistency: sum(categories) == tool_count per row.

Run with:
    .venv/bin/python -m pytest tests/test_aggregate_tools_inventory.py -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench.aggregate_tools_inventory import (
    collect_inventories,
    find_gaps,
    render_markdown,
)


def _write_inventory(
    mcp_dir: Path,
    *,
    status: str = "OK",
    tool_count: int = 10,
    categories: dict[str, int] | None = None,
) -> None:
    mcp_dir.mkdir(parents=True, exist_ok=True)
    inv = {
        "mcp": mcp_dir.name,
        "captured_at": "2026-05-27T00:00:00Z",
        "status": status,
        "tool_count": tool_count,
        "categories": categories or {
            "navigation": 2,
            "interaction": 4,
            "capture": 1,
            "diagnostics": 2,
            "inspection": 1,
            "other": 0,
        },
        "tools": [],
    }
    (mcp_dir / "tools_inventory.json").write_text(
        json.dumps(inv, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class CollectInventoriesTests(unittest.TestCase):
    def test_collects_all_present_inventories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name in ("playwright", "obscura", "lightpanda"):
                _write_inventory(base / name)
            rows = collect_inventories(base)
            names = [r["mcp"] for r in rows]
            self.assertEqual(sorted(names), ["lightpanda", "obscura", "playwright"])
            # Each row should preserve status, tool_count, categories.
            for row in rows:
                self.assertEqual(row["status"], "OK")
                self.assertEqual(row["tool_count"], 10)

    def test_missing_inventory_records_missing_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_inventory(base / "playwright")
            _write_inventory(base / "obscura")
            (base / "lightpanda").mkdir()  # no tools_inventory.json
            rows = collect_inventories(base)
            light = [r for r in rows if r["mcp"] == "lightpanda"][0]
            self.assertEqual(light["status"], "MISSING")
            self.assertEqual(light["tool_count"], 0)


class FindGapsTests(unittest.TestCase):
    def test_missing_status_counts_as_gap(self) -> None:
        rows = [
            {"mcp": "playwright", "status": "OK"},
            {"mcp": "obscura", "status": "INITIALIZE_TIMEOUT"},
            {"mcp": "lightpanda", "status": "MISSING"},
            {"mcp": "firecrawl", "status": "OK"},
        ]
        gaps = find_gaps(rows)
        names = [g["mcp"] for g in gaps]
        self.assertIn("obscura", names)
        self.assertIn("lightpanda", names)
        self.assertNotIn("playwright", names)
        self.assertNotIn("firecrawl", names)


class RenderMarkdownTests(unittest.TestCase):
    def test_renders_side_by_side_table(self) -> None:
        rows = [
            {
                "mcp": "playwright",
                "status": "OK",
                "tool_count": 23,
                "categories": {
                    "navigation": 2, "interaction": 11, "capture": 1,
                    "diagnostics": 5, "inspection": 1, "other": 3,
                },
            },
            {
                "mcp": "obscura",
                "status": "OK",
                "tool_count": 13,
                "categories": {
                    "navigation": 1, "interaction": 5, "capture": 2,
                    "diagnostics": 2, "inspection": 2, "other": 1,
                },
            },
        ]
        md = render_markdown(rows, generated_at="2026-05-27T00:00:00Z")
        # Header columns present.
        self.assertIn("| MCP", md)
        self.assertIn("| navigation", md)
        self.assertIn("| interaction", md)
        self.assertIn("| capture", md)
        self.assertIn("| diagnostics", md)
        self.assertIn("| inspection", md)
        self.assertIn("| other", md)
        # Rows present (rendered with backticked MCP names).
        self.assertIn("`playwright`", md)
        self.assertIn("`obscura`", md)
        # Methodology footer present.
        self.assertIn("Methodology", md)

    def test_status_surfacing_for_non_ok(self) -> None:
        rows = [
            {
                "mcp": "browser-use",
                "status": "INITIALIZE_TIMEOUT",
                "tool_count": 0,
                "categories": {
                    "navigation": 0, "interaction": 0, "capture": 0,
                    "diagnostics": 0, "inspection": 0, "other": 0,
                },
            },
        ]
        md = render_markdown(rows, generated_at="2026-05-27T00:00:00Z")
        self.assertIn("INITIALIZE_TIMEOUT", md)
        # Gaps section should also flag the row.
        self.assertIn("Gaps", md)


class ConsistencyTests(unittest.TestCase):
    def test_sum_of_categories_equals_tool_count(self) -> None:
        """OK rows must satisfy sum(categories.values()) == tool_count.

        This is a contract on the per-MCP tools_inventory.json producer
        (bench/tools_inventory.py). The aggregator should surface any
        violation as a warning in the rendered Markdown.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            # consistent
            _write_inventory(
                base / "good",
                tool_count=10,
                categories={
                    "navigation": 2, "interaction": 4, "capture": 1,
                    "diagnostics": 2, "inspection": 1, "other": 0,
                },
            )
            # inconsistent (sum=10, tool_count=12)
            _write_inventory(
                base / "bad",
                tool_count=12,
                categories={
                    "navigation": 2, "interaction": 4, "capture": 1,
                    "diagnostics": 2, "inspection": 1, "other": 0,
                },
            )
            rows = collect_inventories(base)
            md = render_markdown(rows, generated_at="2026-05-27T00:00:00Z")
            # The inconsistent row should be flagged in the doc.
            self.assertIn("inconsistent", md.lower())


if __name__ == "__main__":
    unittest.main()
