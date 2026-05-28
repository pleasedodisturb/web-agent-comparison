"""test_measure_tokens — unit tests for the 3-scope token efficiency aggregator.

Plan 03-02 (MEAS-02) splits "token efficiency" into three scopes that the
2026-03 wave conflated:

  * `schema`  — tokens Claude pays just to know an MCP's `tools/list`,
                counted via the Anthropic SDK `count_tokens()` API
                (free, no billing impact).
  * `payload` — bytes of the JSON-RPC `tool_use.input` + `tool_result.content`
                wire payloads, parsed from Phase 2's `raw_stream.jsonl`.
                Byte-count, not token-count (proxy for cost).
  * `turn`    — `usage.input_tokens` + `usage.output_tokens` extracted from
                the `result`-typed stream-json envelopes already captured
                in Phase 1.

`bench/measure_tokens.py` reads the existing Phase-2 evidence (raw_stream.jsonl
+ tools_inventory.json) and the Phase-1 stub (`tokens.json` carrying the turn
block), then overwrites the stub with the 3-scope dict.

Test coverage
-------------
  1. ``payload_bytes`` summation from a fixture stream with two tool_use
     blocks (`input`) and two tool_result blocks (`content`).
  2. ``turn`` recovery from a terminal ``{"type":"result","usage":{...}}``
     envelope.
  3. ``schema_tokens`` via a mocked count_tokens callable. The mock is
     injected (Phase-3 keeps the live Anthropic client at the CLI boundary
     only), and the test asserts that the tools list was converted to
     Anthropic's ``tools=`` schema shape.
  4. Median-across-passes for payload bytes (three passes, S1 = [100,200,300]
     → S1 median = 200).
  5. SKIPPED handling — a per-MCP directory carrying only ``SKIPPED.md``
     yields a tokens.json with ``status: SKIPPED`` and no count_tokens call.
  6. Phase-1 stub overwrite — an existing tokens.json with
     ``{"deferred":"phase-3","turn":{...}}`` is replaced by the 3-scope
     dict, the ``deferred`` key is removed, and the existing ``turn`` block
     is reused as-is (no need to re-extract from raw_stream).

Run with:
    .venv/bin/python -m pytest tests/test_measure_tokens.py -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from bench.measure_tokens import (
    aggregate_mcp,
    build_anthropic_tools_schema,
    extract_payload_bytes_per_pass,
    extract_turn_usage_from_jsonl,
    median_payload_bytes,
)


# ─── Fixture builders ────────────────────────────────────────────────────


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(line) for line in lines) + "\n",
        encoding="utf-8",
    )


def _assistant_tool_use(tool_id: str, name: str, input_blob: dict | None = None) -> dict:
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


def _user_tool_result(tool_id: str, content: object) -> dict:
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": content,
                }
            ],
        },
    }


def _result_envelope(usage: dict) -> dict:
    return {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 1234,
        "usage": usage,
        "uuid": "00000000-0000-0000-0000-000000000000",
    }


def _write_stage_marker(stage_n: int, suffix: str = "yml") -> dict:
    """Build a Write tool_use marker that closes stage S<n>.

    Reuses Plan 03-01's marker convention. The stage path matches
    ``stage_s<N>.<ext>`` so stage attribution snaps to S<n>.
    """
    return _assistant_tool_use(
        tool_id=f"wr-s{stage_n}",
        name="Write",
        input_blob={
            "file_path": f"results/2026-05-26/x/PASS1/stage_s{stage_n}.{suffix}",
            "content": "",
        },
    )


# ─── Tests ───────────────────────────────────────────────────────────────


class PayloadByteCountTests(unittest.TestCase):
    """Test 1: payload bytes — sum of tool_use.input + tool_result.content."""

    def test_two_tool_uses_and_two_results(self):
        with tempfile.TemporaryDirectory() as td:
            jsonl = Path(td) / "raw_stream.jsonl"
            _write_jsonl(
                jsonl,
                [
                    _assistant_tool_use("t1", "navigate", {"url": "x"}),
                    _write_stage_marker(1),
                    _user_tool_result("t1", "result text"),
                    _assistant_tool_use("t2", "click", {"selector": "#go"}),
                    _write_stage_marker(2),
                    _user_tool_result("t2", "ok"),
                ],
            )
            per_stage = extract_payload_bytes_per_pass(jsonl)
            # Stage attribution mirrors 03-01's Write-marker logic: the
            # tool_use BEFORE and INCLUDING the Write attribute to that
            # stage; tool_result events get the same stage as the
            # most-recently-closed Write boundary (which is what the
            # implementation does — "current stage" snapshot).
            # We just need the payload bytes to add up correctly for
            # both inputs and contents.
            total = sum(per_stage.values()) if isinstance(per_stage, dict) else 0
            # Sanity: at minimum, the byte count is len(json.dumps()
            # encoded) of each of the four payloads we put in. The
            # implementation may also count the Write input file_path
            # — that's fine, we just assert > zero and > the bare
            # input/content sizes.
            min_expected = (
                len(json.dumps({"url": "x"}).encode("utf-8"))
                + len(json.dumps("result text").encode("utf-8"))
                + len(json.dumps({"selector": "#go"}).encode("utf-8"))
                + len(json.dumps("ok").encode("utf-8"))
            )
            self.assertGreaterEqual(total, min_expected)

    def test_payload_bytes_attributed_per_stage(self):
        """A tool_use BEFORE stage_s1 Write attributes to S1; one before s2 → S2."""
        with tempfile.TemporaryDirectory() as td:
            jsonl = Path(td) / "raw_stream.jsonl"
            _write_jsonl(
                jsonl,
                [
                    _assistant_tool_use("t1", "navigate", {"url": "https://a.example"}),
                    _write_stage_marker(1),
                    _assistant_tool_use("t2", "click", {"selector": "#x"}),
                    _write_stage_marker(2),
                ],
            )
            per_stage = extract_payload_bytes_per_pass(jsonl)
            self.assertIn("S1", per_stage)
            self.assertIn("S2", per_stage)
            # S1 contains navigate(url) input bytes; S2 contains click(selector).
            self.assertGreater(per_stage["S1"], 0)
            self.assertGreater(per_stage["S2"], 0)


class TurnUsageRecoveryTests(unittest.TestCase):
    """Test 2: turn — extract usage block from terminal `result` envelope."""

    def test_recovers_usage_block_intact(self):
        with tempfile.TemporaryDirectory() as td:
            jsonl = Path(td) / "raw_stream.jsonl"
            usage = {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 30,
                "cache_read_input_tokens": 200,
            }
            _write_jsonl(
                jsonl,
                [
                    _assistant_tool_use("t1", "navigate", {"url": "x"}),
                    _result_envelope(usage),
                ],
            )
            recovered = extract_turn_usage_from_jsonl(jsonl)
            self.assertEqual(recovered["input_tokens"], 100)
            self.assertEqual(recovered["output_tokens"], 50)
            self.assertEqual(recovered["cache_creation_input_tokens"], 30)

    def test_no_result_envelope_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            jsonl = Path(td) / "raw_stream.jsonl"
            _write_jsonl(jsonl, [_assistant_tool_use("t1", "navigate", {})])
            self.assertIsNone(extract_turn_usage_from_jsonl(jsonl))


class SchemaTokenCountTests(unittest.TestCase):
    """Test 3: schema_tokens via mocked count_tokens callable.

    The aggregator accepts a ``count_tokens_fn`` dependency-inject hook so
    tests can avoid hitting the live Anthropic API. The CLI wires this up
    to ``anthropic.Anthropic().messages.count_tokens`` at runtime.
    """

    def test_build_tools_schema_uses_inventory_keys(self):
        inventory = {
            "tools": [
                {
                    "name": "navigate",
                    "description_excerpt": "Go to URL",
                    "input_schema_keys": ["url"],
                    "category": "navigation",
                },
                {
                    "name": "click",
                    "description_excerpt": "Click selector",
                    "input_schema_keys": ["selector", "button"],
                    "category": "interaction",
                },
            ]
        }
        schema = build_anthropic_tools_schema(inventory)
        self.assertEqual(len(schema), 2)
        self.assertEqual(schema[0]["name"], "navigate")
        self.assertEqual(schema[0]["description"], "Go to URL")
        self.assertIn("input_schema", schema[0])
        self.assertEqual(schema[0]["input_schema"]["type"], "object")
        # The properties dict carries keys (even if value-types are unknown
        # at probe time, the keys are what we have from tools_inventory).
        self.assertIn("url", schema[0]["input_schema"]["properties"])
        self.assertIn("selector", schema[1]["input_schema"]["properties"])
        self.assertIn("button", schema[1]["input_schema"]["properties"])

    def test_schema_count_via_mock(self):
        """The mock receives the tools schema converted from inventory."""
        with tempfile.TemporaryDirectory() as td:
            mcp_dir = Path(td) / "mockmcp"
            (mcp_dir / "PASS1").mkdir(parents=True)

            inventory = {
                "mcp": "mockmcp",
                "status": "OK",
                "tool_count": 1,
                "tools": [
                    {
                        "name": "navigate",
                        "description_excerpt": "Go",
                        "input_schema_keys": ["url"],
                        "category": "navigation",
                    }
                ],
            }
            (mcp_dir / "tools_inventory.json").write_text(json.dumps(inventory))

            # Empty pass jsonl so we don't need to fabricate full payload data.
            (mcp_dir / "PASS1" / "raw_stream.jsonl").write_text("")

            # Mocked count_tokens: returns 250 for the with-tools call and
            # 50 for the baseline (empty tools). Delta = 200 = schema_tokens.
            calls: list[dict] = []

            def fake_count_tokens(**kwargs):
                calls.append(kwargs)
                if kwargs.get("tools"):
                    obj = MagicMock()
                    obj.input_tokens = 250
                    return obj
                obj = MagicMock()
                obj.input_tokens = 50
                return obj

            result = aggregate_mcp(
                mcp_dir,
                count_tokens_fn=fake_count_tokens,
                model="claude-test",
            )
            # Two calls: baseline (no tools) + with-tools.
            self.assertEqual(len(calls), 2)
            with_tools_call = next(c for c in calls if c.get("tools"))
            # The mocked function MUST have been called with a tools= list
            # that mirrors our inventory.
            self.assertEqual(len(with_tools_call["tools"]), 1)
            self.assertEqual(with_tools_call["tools"][0]["name"], "navigate")
            self.assertEqual(result["schema_tokens"], 200)
            self.assertEqual(result["schema_source"], "anthropic.count_tokens")
            self.assertEqual(result["schema_model"], "claude-test")


class MedianAcrossPassesTests(unittest.TestCase):
    """Test 4: median across 3 passes for payload bytes per stage."""

    def test_median_payload_three_passes(self):
        passes = {
            "PASS1": {"S1": 100, "S2": 50},
            "PASS2": {"S1": 200, "S2": 75},
            "PASS3": {"S1": 300, "S2": 100},
        }
        med = median_payload_bytes(passes)
        self.assertEqual(med["S1"], 200)
        self.assertEqual(med["S2"], 75)

    def test_median_missing_stage_treats_as_zero(self):
        """Plan 03-01 convention: missing-tool = 0 for median."""
        passes = {
            "PASS1": {"S1": 100, "S5": 999},
            "PASS2": {"S1": 200},  # no S5
            "PASS3": {"S1": 300},  # no S5
        }
        med = median_payload_bytes(passes)
        self.assertEqual(med["S1"], 200)
        # Two zeros + one 999 → median 0.
        self.assertEqual(med["S5"], 0)


class SkippedHandlingTests(unittest.TestCase):
    """Test 5: SKIPPED.md only → tokens.json with status=SKIPPED, no count_tokens."""

    def test_skipped_md_only(self):
        with tempfile.TemporaryDirectory() as td:
            mcp_dir = Path(td) / "skippedmcp"
            mcp_dir.mkdir()
            (mcp_dir / "SKIPPED.md").write_text(
                "LLM_KEY_ABSENT: browser-use agent mode requires ANTHROPIC_API_KEY\n"
            )

            calls: list[dict] = []

            def fake_count_tokens(**kwargs):
                calls.append(kwargs)
                obj = MagicMock()
                obj.input_tokens = 0
                return obj

            result = aggregate_mcp(
                mcp_dir,
                count_tokens_fn=fake_count_tokens,
                model="claude-test",
            )
            self.assertEqual(result["status"], "SKIPPED")
            # No count_tokens calls — there's no tools_inventory and no
            # PASS dirs to measure.
            self.assertEqual(len(calls), 0)
            # Turn is null because no raw_stream to extract from.
            self.assertIsNone(result.get("median_turn_input_tokens"))


class StubOverwriteTests(unittest.TestCase):
    """Test 6: Phase-1 deferred stub overwrite, reusing the captured turn block."""

    def test_existing_stub_turn_reused(self):
        with tempfile.TemporaryDirectory() as td:
            mcp_dir = Path(td) / "stubmcp"
            (mcp_dir / "PASS1").mkdir(parents=True)

            # No inventory, no schema attempt:
            existing_stub = {
                "mcp": "stubmcp",
                "scope": "turn",
                "deferred": "phase-3",
                "reason": "...",
                "turn": {
                    "input_tokens": 999,
                    "output_tokens": 11,
                    "cache_read_input_tokens": 5,
                },
                "schema_bytes": None,
                "payload_bytes": None,
            }
            (mcp_dir / "tokens.json").write_text(json.dumps(existing_stub))

            # PASS1 raw_stream HAS NO result envelope — extraction would
            # return None — but the stub's turn block must be preserved.
            (mcp_dir / "PASS1" / "raw_stream.jsonl").write_text("")

            result = aggregate_mcp(
                mcp_dir,
                count_tokens_fn=None,  # --skip-schema path
                model="claude-test",
            )
            # The stub's turn block survives as PASS1's turn (since no
            # result envelope was found in raw_stream).
            self.assertIn("turn_tokens_per_pass", result)
            self.assertEqual(
                result["turn_tokens_per_pass"]["PASS1"]["input_tokens"], 999
            )
            # `deferred` key removed.
            self.assertNotIn("deferred", result)


if __name__ == "__main__":
    unittest.main()
