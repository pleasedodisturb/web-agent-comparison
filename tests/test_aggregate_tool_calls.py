"""test_aggregate_tool_calls — unit tests for the tool-call count aggregator.

The aggregator walks `results/<date>/<mcp>/PASS{1,2,3}/raw_stream.jsonl`,
counts `tool_use` events from `assistant`-type lines (NOT stream_event,
which would double-count), optionally attributes them to S1-S8 stages via
`Write` events targeting `stage_s*.*` paths, and emits a per-MCP
`tool_call_counts.json`.

Tests cover:

  - Flat counting (default `--stage-attribution=none`): three tool_use
    events with two distinct names produce the expected counts dict.
  - Stage attribution by Write-marker: tool_use events landing BEFORE a
    `Write(stage_s1.yml)` attribute to S1, events BETWEEN `stage_s1.yml`
    and `stage_s2.yml` Writes attribute to S2, etc.
  - Median across passes: three pass dirs with diverging counts produce
    the integer median for each stage/tool.
  - SKIPPED MCP: directory with only `SKIPPED.md` (no PASS* dirs)
    yields a `status: SKIPPED` JSON without crashing.

Run with:
    .venv/bin/python -m pytest tests/test_aggregate_tool_calls.py -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench.aggregate_tool_calls import (
    aggregate_mcp,
    attribute_stages,
    count_tool_uses_in_jsonl,
    median_of_counts,
)


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    """Write one JSON object per line — the shape Claude session stream uses."""
    path.write_text(
        "\n".join(json.dumps(line) for line in lines) + "\n",
        encoding="utf-8",
    )


def _assistant_tool_use(tool_id: str, name: str, input_blob: dict | None = None) -> dict:
    """Build a minimal `assistant`-typed line carrying one tool_use block."""
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": name,
                    "input": input_blob or {},
                }
            ],
        },
    }


def _block(tool_id: str, name: str, input_blob: dict | None = None) -> dict:
    """Build a single tool_use content block (the unwrapped shape).

    `attribute_stages` operates on these unwrapped blocks — they're what
    `aggregate_mcp` extracts before calling it.
    """
    return {
        "type": "tool_use",
        "id": tool_id,
        "name": name,
        "input": input_blob or {},
    }


def _stream_event_tool_use(tool_id: str, name: str) -> dict:
    """Build the duplicate stream_event line that the SDK emits alongside.

    These MUST NOT be double-counted by the aggregator — only the
    `assistant`-typed lines are canonical.
    """
    return {
        "type": "stream_event",
        "event": {
            "type": "content_block_start",
            "index": 2,
            "content_block": {
                "type": "tool_use",
                "id": tool_id,
                "name": name,
                "input": {},
            },
        },
    }


class CountToolUsesTests(unittest.TestCase):
    """Test 1 — flat counting (no stage attribution)."""

    def test_three_tool_uses_two_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "raw_stream.jsonl"
            _write_jsonl(
                jsonl,
                [
                    _assistant_tool_use("t1", "mcp__playwright__browser_navigate"),
                    _assistant_tool_use("t2", "mcp__playwright__browser_click"),
                    _assistant_tool_use("t3", "mcp__playwright__browser_click"),
                ],
            )
            counts = count_tool_uses_in_jsonl(jsonl)
            self.assertEqual(
                counts,
                {
                    "mcp__playwright__browser_navigate": 1,
                    "mcp__playwright__browser_click": 2,
                },
            )

    def test_stream_events_not_double_counted(self) -> None:
        """The aggregator MUST count assistant blocks only.

        stream_event lines carry duplicate `content_block_start` events
        with the same tool_use id — counting both would inflate the
        totals 2x and corrupt the headline (Playwright batch-fill claim
        becomes 2 calls instead of 1).
        """
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "raw_stream.jsonl"
            _write_jsonl(
                jsonl,
                [
                    _stream_event_tool_use("t1", "mcp__playwright__browser_navigate"),
                    _assistant_tool_use("t1", "mcp__playwright__browser_navigate"),
                    _stream_event_tool_use("t2", "mcp__playwright__browser_click"),
                    _assistant_tool_use("t2", "mcp__playwright__browser_click"),
                ],
            )
            counts = count_tool_uses_in_jsonl(jsonl)
            self.assertEqual(
                counts,
                {
                    "mcp__playwright__browser_navigate": 1,
                    "mcp__playwright__browser_click": 1,
                },
            )

    def test_malformed_line_skipped(self) -> None:
        """A non-JSON line is logged and skipped per stop_conditions."""
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "raw_stream.jsonl"
            jsonl.write_text(
                json.dumps(_assistant_tool_use("t1", "Foo")) + "\n"
                + "{not valid json\n"
                + json.dumps(_assistant_tool_use("t2", "Bar")) + "\n",
                encoding="utf-8",
            )
            counts = count_tool_uses_in_jsonl(jsonl)
            self.assertEqual(counts, {"Foo": 1, "Bar": 1})


class StageAttributionTests(unittest.TestCase):
    """Test 2 — Write-marker stage attribution."""

    def test_write_markers_partition_tool_uses(self) -> None:
        """Tool uses up to & including stage_sN Write -> Sn; between Sn & Sn+1 -> Sn+1.

        Per plan: "tool_use events BEFORE that Write attribute to the
        just-written stage" — that means the click/navigate calls that
        FED the snapshot land in S1 (along with the S1 Write itself).
        """
        events = [
            _block("t1", "mcp__cdp__navigate"),  # idx 0 -> S1
            _block("t2", "mcp__cdp__snapshot"),  # idx 1 -> S1
            _block("w1", "Write",
                   {"file_path": "/x/y/stage_s1.yml", "content": "..."}),  # idx 2 -> S1
            _block("t3", "mcp__cdp__click"),  # idx 3 -> S2
            _block("t4", "mcp__cdp__navigate"),  # idx 4 -> S2
            _block("w2", "Write",
                   {"file_path": "/x/y/stage_s2.yml", "content": "..."}),  # idx 5 -> S2
            _block("t5", "mcp__cdp__snapshot"),  # idx 6 -> unattributed
        ]
        per_stage = attribute_stages(events)
        self.assertEqual(per_stage["S1"], {
            "mcp__cdp__navigate": 1,
            "mcp__cdp__snapshot": 1,
            "Write": 1,
        })
        self.assertEqual(per_stage["S2"], {
            "mcp__cdp__click": 1,
            "mcp__cdp__navigate": 1,
            "Write": 1,
        })
        self.assertEqual(per_stage.get("unattributed", {}), {"mcp__cdp__snapshot": 1})

    def test_failed_and_na_suffixes_also_mark_stages(self) -> None:
        """`.FAILED` and `.NA` stage markers count too — firecrawl/lightpanda need this."""
        events = [
            _block("t1", "mcp__firecrawl__scrape"),
            _block("w1", "Write",
                   {"file_path": "/x/y/stage_s1.FAILED", "content": "..."}),
            _block("t2", "mcp__firecrawl__scrape"),
            _block("w2", "Write",
                   {"file_path": "/x/y/stage_s2.NA", "content": "..."}),
        ]
        per_stage = attribute_stages(events)
        self.assertIn("S1", per_stage)
        self.assertIn("S2", per_stage)
        self.assertEqual(per_stage["S1"]["mcp__firecrawl__scrape"], 1)
        self.assertEqual(per_stage["S2"]["mcp__firecrawl__scrape"], 1)

    def test_no_stage_markers_yields_unattributed(self) -> None:
        events = [
            _block("t1", "Foo"),
            _block("t2", "Bar"),
        ]
        per_stage = attribute_stages(events)
        self.assertEqual(per_stage, {"unattributed": {"Foo": 1, "Bar": 1}})


class MedianAcrossPassesTests(unittest.TestCase):
    """Test 3 — integer median across PASS{1,2,3} counters."""

    def test_per_stage_median(self) -> None:
        passes = {
            "PASS1": {"S1": {"navigate": 2}, "S5": {"fill": 6}},
            "PASS2": {"S1": {"navigate": 3}, "S5": {"fill": 4}},
            "PASS3": {"S1": {"navigate": 5}, "S5": {"fill": 1}},
        }
        median = median_of_counts(passes)
        # median([2,3,5]) = 3 ; median([6,4,1]) = 4
        self.assertEqual(median["S1"]["navigate"], 3)
        self.assertEqual(median["S5"]["fill"], 4)

    def test_per_stage_median_handles_missing_keys(self) -> None:
        """If a tool only appears in 2 of 3 passes, treat missing as 0."""
        passes = {
            "PASS1": {"S1": {"click": 2, "navigate": 1}},
            "PASS2": {"S1": {"click": 4}},  # no navigate
            "PASS3": {"S1": {"click": 6, "navigate": 3}},
        }
        median = median_of_counts(passes)
        # navigate: [1, 0, 3] -> median 1
        # click: [2, 4, 6] -> median 4
        self.assertEqual(median["S1"]["navigate"], 1)
        self.assertEqual(median["S1"]["click"], 4)


class SkippedMcpTests(unittest.TestCase):
    """Test 4 — SKIPPED.md handling."""

    def test_skipped_mcp_emits_status_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mcp_dir = Path(tmp) / "browser-use-agent"
            mcp_dir.mkdir()
            (mcp_dir / "SKIPPED.md").write_text(
                "# browser-use-agent — SKIPPED (LLM API key absent)\n\n"
                "- **reason:** LLM_KEY_ABSENT\n",
                encoding="utf-8",
            )
            result = aggregate_mcp(mcp_dir, stage_attribution="marker")
            self.assertEqual(result["mcp"], "browser-use-agent")
            self.assertEqual(result["status"], "SKIPPED")
            self.assertIn("LLM", result.get("reason", ""))
            self.assertNotIn("passes", result)

    def test_skipped_mcp_writes_file_to_disk(self) -> None:
        """The aggregate_mcp result is written by the CLI; verify it serializes."""
        with tempfile.TemporaryDirectory() as tmp:
            mcp_dir = Path(tmp) / "browser-use-agent"
            mcp_dir.mkdir()
            (mcp_dir / "SKIPPED.md").write_text("reason line\n", encoding="utf-8")
            result = aggregate_mcp(mcp_dir, stage_attribution="none")
            # Round-trip JSON should preserve the dict.
            blob = json.dumps(result)
            self.assertIn("SKIPPED", blob)


class EndToEndTests(unittest.TestCase):
    """Verify aggregate_mcp on a tiny full-shape fixture (1 PASS, 2 stages)."""

    def test_single_pass_full_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mcp_dir = Path(tmp) / "tinymcp"
            (mcp_dir / "PASS1").mkdir(parents=True)
            _write_jsonl(
                mcp_dir / "PASS1" / "raw_stream.jsonl",
                [
                    _assistant_tool_use("t1", "mcp__tiny__navigate"),
                    _assistant_tool_use(
                        "w1",
                        "Write",
                        {"file_path": str(mcp_dir / "stage_s1.yml"), "content": "..."},
                    ),
                    _assistant_tool_use("t2", "mcp__tiny__fill_form"),
                    _assistant_tool_use(
                        "w2",
                        "Write",
                        {"file_path": str(mcp_dir / "stage_s5.yml"), "content": "..."},
                    ),
                ],
            )
            result = aggregate_mcp(mcp_dir, stage_attribution="marker")
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["mcp"], "tinymcp")
            self.assertEqual(result["stage_attribution_mode"], "marker")
            # PASS1 should partition into S1 (navigate + Write) and S5 (fill_form + Write).
            self.assertIn("PASS1", result["passes"])
            self.assertEqual(
                result["passes"]["PASS1"]["S1"]["mcp__tiny__navigate"], 1,
            )
            self.assertEqual(
                result["passes"]["PASS1"]["S5"]["mcp__tiny__fill_form"], 1,
            )
            # total per pass = 4 (navigate + Write + fill_form + Write)
            self.assertEqual(result["total_calls_per_pass"]["PASS1"], 4)


if __name__ == "__main__":
    unittest.main()
