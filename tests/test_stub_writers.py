"""test_stub_writers — verify the Phase-1 deferred-marker stubs.

The stubs from `bench.stub_writers` lock the evidence-directory contract.
The aggregator (`scripts/aggregate_scores.py`) only treats them as
"deferred — score neutrally" if the JSON contains the literal
`"deferred"` key with the ticket string, so these tests assert on that
exact shape — not just "file exists".

Run with:
    .venv/bin/python -m unittest tests.test_stub_writers -v
or:
    uv run python -m unittest tests.test_stub_writers
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench.stub_writers import (
    DEFERRED_TICKET,
    _is_deferred_stub,
    main,
    write_cold_start_stub,
    write_stability_stub,
    write_stubs,
    write_tls_stub,
)


class TLSStubTests(unittest.TestCase):
    """write_tls_stub emits canonical {"deferred": "G-710", ...} JSON."""

    def test_writes_file_at_expected_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            path = write_tls_stub(out)
            self.assertEqual(path, out / "tls.json")
            self.assertTrue(path.exists())

    def test_payload_is_valid_json_with_deferred_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_tls_stub(out)
            data = json.loads((out / "tls.json").read_text())
            self.assertEqual(data["deferred"], DEFERRED_TICKET)
            self.assertIn("reason", data)
            self.assertIn("see", data)
            # Provenance URL should point at the right Linear org.
            self.assertIn(DEFERRED_TICKET, data["see"])

    def test_aggregator_compatible_shape(self) -> None:
        """The aggregator's `_score_speed`/`_score_token_efficiency` keys
        off the literal `deferred` field. Assert that key is present and
        truthy so a neutral mid-band score is awarded."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_tls_stub(out)
            data = json.loads((out / "tls.json").read_text())
            self.assertTrue(data.get("deferred"))


class ColdStartStubTests(unittest.TestCase):
    """write_cold_start_stub emits null-valued 3-segment shape."""

    def test_includes_all_segment_fields_as_null(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_cold_start_stub(out, "playwright")
            data = json.loads((out / "cold_start.json").read_text())
            # Future-Phase-3 shape — nulls present so aggregator sees the
            # contract not a missing key.
            for field in (
                "t_resolve_ms",
                "t_spawn_ms",
                "t_first_useful_ms",
                "warm_cache",
            ):
                self.assertIn(field, data)
                self.assertIsNone(data[field])
            self.assertEqual(data["n_runs"], 0)
            self.assertEqual(data["deferred"], DEFERRED_TICKET)

    def test_records_mcp_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_cold_start_stub(out, "lightpanda")
            data = json.loads((out / "cold_start.json").read_text())
            self.assertEqual(data["mcp"], "lightpanda")


class StabilityStubTests(unittest.TestCase):
    """write_stability_stub emits a single readable line."""

    def test_writes_nonempty_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_stability_stub(out)
            log = (out / "stability.log").read_text()
            self.assertTrue(log.strip())  # non-empty
            self.assertIn(DEFERRED_TICKET, log)
            self.assertIn("STUB", log)

    def test_log_ends_with_newline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_stability_stub(out)
            log = (out / "stability.log").read_text()
            self.assertTrue(log.endswith("\n"))


class WriteStubsConvenienceTests(unittest.TestCase):
    """write_stubs wraps all three writers."""

    def test_emits_all_three_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            written = write_stubs(out, "playwright")
            self.assertEqual(set(written.keys()), {"tls", "cold_start", "stability"})
            for path in written.values():
                self.assertTrue(path.exists(), f"missing: {path}")


class IsDeferredStubTests(unittest.TestCase):
    """_is_deferred_stub correctly identifies stubs vs real files."""

    def test_recognizes_json_stub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_tls_stub(out)
            self.assertTrue(_is_deferred_stub(out / "tls.json"))

    def test_recognizes_text_stub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_stability_stub(out)
            self.assertTrue(_is_deferred_stub(out / "stability.log"))

    def test_rejects_real_measurement_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            real_path = out / "tls.json"
            real_path.write_text(
                json.dumps({"ja3": "abc123def", "ja4": "h2-1234"}) + "\n"
            )
            self.assertFalse(_is_deferred_stub(real_path))

    def test_missing_file_is_not_stub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.assertFalse(_is_deferred_stub(out / "nonexistent.json"))


class CLITests(unittest.TestCase):
    """python -m bench.stub_writers <dir>."""

    def test_cli_writes_all_three(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "playwright"
            rc = main([str(out)])
            self.assertEqual(rc, 0)
            for fname in ("tls.json", "cold_start.json", "stability.log"):
                self.assertTrue((out / fname).exists(), f"missing: {fname}")

    def test_cli_refuses_to_clobber_real_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "playwright"
            out.mkdir()
            # Plant a real-looking tls.json.
            (out / "tls.json").write_text(
                json.dumps({"ja3": "real_fingerprint_here"}) + "\n"
            )
            rc = main([str(out)])
            self.assertEqual(rc, 1)  # refusal exit code
            # Real file untouched.
            data = json.loads((out / "tls.json").read_text())
            self.assertEqual(data, {"ja3": "real_fingerprint_here"})

    def test_cli_force_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "playwright"
            out.mkdir()
            (out / "tls.json").write_text(
                json.dumps({"ja3": "real_fingerprint_here"}) + "\n"
            )
            rc = main([str(out), "--force"])
            self.assertEqual(rc, 0)
            # Now it's a stub.
            data = json.loads((out / "tls.json").read_text())
            self.assertEqual(data["deferred"], DEFERRED_TICKET)

    def test_cli_idempotent_on_existing_stub(self) -> None:
        """Re-running over a stub directory just rewrites the stubs."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "playwright"
            self.assertEqual(main([str(out)]), 0)
            # Second run on top of stubs is fine — they're stubs, not real.
            self.assertEqual(main([str(out)]), 0)

    def test_cli_defaults_mcp_name_to_dir_basename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "chrome-devtools"
            rc = main([str(out)])
            self.assertEqual(rc, 0)
            data = json.loads((out / "cold_start.json").read_text())
            self.assertEqual(data["mcp"], "chrome-devtools")


if __name__ == "__main__":
    unittest.main()
