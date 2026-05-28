"""test_capture_versions — verify the reproducibility-manifest captor.

Two test surfaces:

  1. Pure-function tests against the helpers (`_sha256_file`,
     `render_markdown`, `_collect_handshake_versions`,
     `_capture_mcp` against a synthetic `.mcp.json`).
  2. End-to-end live capture — runs the CLI against a tempdir results
     root and asserts:
       - versions.json + versions.lock.md exist
       - JSON parses, contains host/tooling/mcps
       - at least one MCP has a 64-char lowercase hex SHA256
       - the Markdown contains the "Reproducibility Manifest" header

Run with:
    .venv/bin/python -m unittest tests.test_capture_versions -v
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from bench.capture_versions import (
    _capture_mcp,
    _collect_handshake_versions,
    _sha256_file,
    _which,
    capture,
    capture_host,
    capture_tooling,
    main,
    render_markdown,
)

# Hex pattern for SHA256 validation.
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class Sha256FileTests(unittest.TestCase):
    def test_hashes_a_known_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"hello world")
            path = f.name
        try:
            expected = hashlib.sha256(b"hello world").hexdigest()
            self.assertEqual(_sha256_file(path), expected)
        finally:
            Path(path).unlink()

    def test_returns_none_for_missing_file(self) -> None:
        self.assertIsNone(_sha256_file("/definitely/not/here/xyz"))

    def test_expands_tilde(self) -> None:
        # Write into HOME to verify the ~ collapsing roundtrips through
        # the hasher.
        import os
        home = os.environ.get("HOME")
        if not home:
            self.skipTest("HOME not set")
        with tempfile.NamedTemporaryFile(mode="wb", dir=home, suffix=".sha_test",
                                          delete=False) as f:
            f.write(b"x" * 100)
            path = f.name
        try:
            # _which would collapse, but here we test _sha256_file directly.
            collapsed = "~" + path[len(home):]
            self.assertEqual(_sha256_file(collapsed), _sha256_file(path))
        finally:
            Path(path).unlink()


class WhichTests(unittest.TestCase):
    def test_returns_none_for_missing(self) -> None:
        self.assertIsNone(_which("definitely-not-on-path-xyzzy"))

    def test_resolves_known_binary(self) -> None:
        # `sh` is always present on Unix.
        path = _which("sh")
        self.assertIsNotNone(path)
        # Either /bin/sh or ~/.../sh — both are acceptable.


class CaptureHostTests(unittest.TestCase):
    def test_returns_os_kernel_arch(self) -> None:
        host = capture_host()
        self.assertIn("os", host)
        self.assertIn("kernel_version", host)
        self.assertIn("arch", host)
        # No PII fields slipped in.
        for forbidden in ("hostname", "user", "uid", "mac_address"):
            self.assertNotIn(forbidden, host)


class CaptureToolingTests(unittest.TestCase):
    def test_returns_expected_keys(self) -> None:
        tooling = capture_tooling()
        self.assertEqual(
            set(tooling.keys()),
            {"claude_code", "node", "npm", "python", "uv"},
        )

    def test_values_are_str_or_none(self) -> None:
        tooling = capture_tooling()
        for k, v in tooling.items():
            self.assertTrue(v is None or isinstance(v, str), f"{k}: {v!r}")


class CollectHandshakeVersionsTests(unittest.TestCase):
    def test_returns_empty_for_missing_dir(self) -> None:
        result = _collect_handshake_versions(Path("/tmp/definitely-not-here-xyz"))
        self.assertEqual(result, {})

    def test_scrapes_handshake_versions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Two MCPs with tools_inventory.json.
            for name, version in [("playwright", "1.0.0"),
                                   ("lightpanda", "0.1.0")]:
                d = root / name
                d.mkdir()
                (d / "tools_inventory.json").write_text(
                    json.dumps({
                        "mcp": name,
                        "status": "OK",
                        "version_handshake": version,
                        "tool_count": 5,
                    })
                )
            # And one without (firecrawl).
            (root / "firecrawl").mkdir()
            result = _collect_handshake_versions(root)
            self.assertEqual(result, {"playwright": "1.0.0", "lightpanda": "0.1.0"})

    def test_ignores_bad_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "broken"
            d.mkdir()
            (d / "tools_inventory.json").write_text("{not valid json")
            self.assertEqual(_collect_handshake_versions(root), {})


class CaptureMcpTests(unittest.TestCase):
    def test_captures_known_binary_sha(self) -> None:
        # `sh` is universally present on macOS / Linux.
        result = _capture_mcp("fake-sh", "sh", handshake_versions={})
        self.assertEqual(result["command"], "sh")
        self.assertIsNotNone(result["binary_path"])
        # SHA256 should be 64 hex chars.
        self.assertIsNotNone(result["sha256"])
        self.assertRegex(result["sha256"], SHA256_RE)

    def test_missing_binary_produces_none_sha(self) -> None:
        result = _capture_mcp("ghost", "definitely-not-on-path-xyzzy",
                              handshake_versions={})
        self.assertIsNone(result["binary_path"])
        self.assertIsNone(result["sha256"])

    def test_flags_version_mismatch(self) -> None:
        # Construct a synthetic case: handshake says some weird string,
        # binary self-report says something else — the lightpanda
        # canonical case (binary "0.3.0" vs handshake "0.1.0"). We use
        # "lightpanda" as the key because it's wired to BINARY_VERSION_ARGV
        # (subcommand-style 'lightpanda version'). For the test we point
        # `command` at /usr/bin/true so the binary probe returns nothing,
        # then we rely on the handshake-only branch to record the version
        # and flag the mismatch when binary_self_report is empty/none.
        result = _capture_mcp(
            "lightpanda",
            "sh",  # innocuous binary; its `sh version` will fail
            handshake_versions={"lightpanda": "DEFINITELY_NOT_REAL_VERSION_42"},
        )
        # The handshake version is always recorded.
        self.assertEqual(
            result.get("handshake_protocol_version"),
            "DEFINITELY_NOT_REAL_VERSION_42",
        )
        # When binary_self_report is None or empty, the mismatch flag
        # MUST NOT be set (we don't know if it would have matched).
        # When binary_self_report is set to a different string, the flag
        # IS set. Since `sh version` returns help text containing things
        # like "GNU", this should trigger mismatch.
        binary_str = result.get("binary_self_report") or ""
        if binary_str:
            self.assertTrue(
                result.get("version_mismatch", False),
                f"expected mismatch flag with binary={binary_str!r}, "
                f"got: {result}",
            )


class RenderMarkdownTests(unittest.TestCase):
    def test_includes_header_and_sections(self) -> None:
        manifest = {
            "captured_at": "2026-05-22T12:00:00Z",
            "date": "2026-05-22",
            "host": {"os": "Darwin", "kernel_version": "25.5.0",
                     "arch": "arm64", "macos_version": "15.5"},
            "tooling": {"claude_code": "v2.1.81", "node": "v22.0.0",
                        "npm": "10.0.0", "python": "Python 3.12.0",
                        "uv": "uv 0.7.0"},
            "mcps": {
                "playwright": {
                    "command": "playwright-mcp",
                    "binary_path": "/opt/homebrew/bin/playwright-mcp",
                    "sha256": "a" * 64,
                    "package_version": "0.0.75",
                    "package_name": "@playwright/mcp",
                },
            },
        }
        md = render_markdown(manifest)
        self.assertIn("# Reproducibility Manifest", md)
        self.assertIn("2026-05-22", md)
        self.assertIn("## Host", md)
        self.assertIn("## Tooling", md)
        self.assertIn("## MCPs", md)
        self.assertIn("playwright", md)
        self.assertIn("0.0.75", md)
        # Short SHA: first 16 chars rendered.
        self.assertIn("a" * 16, md)

    def test_renders_mismatch_block_when_present(self) -> None:
        manifest = {
            "date": "2026-05-22",
            "host": {}, "tooling": {},
            "mcps": {
                "lightpanda": {
                    "command": "lightpanda",
                    "binary_path": "~/bin/lightpanda",
                    "sha256": "b" * 64,
                    "binary_self_report": "0.3.0",
                    "handshake_protocol_version": "0.1.0",
                    "version_mismatch": True,
                },
            },
        }
        md = render_markdown(manifest)
        self.assertIn("## Version mismatches", md)
        self.assertIn("lightpanda", md)
        self.assertIn("0.3.0", md)
        self.assertIn("0.1.0", md)
        self.assertIn("**MISMATCH**", md)

    def test_no_mismatch_section_when_clean(self) -> None:
        manifest = {
            "date": "2026-05-22",
            "host": {}, "tooling": {},
            "mcps": {
                "playwright": {
                    "command": "playwright-mcp",
                    "binary_path": "/opt/homebrew/bin/playwright-mcp",
                    "sha256": "c" * 64,
                    "package_version": "0.0.75",
                },
            },
        }
        md = render_markdown(manifest)
        self.assertNotIn("## Version mismatches", md)


class CaptureTopLevelTests(unittest.TestCase):
    """capture() runs every section captor and returns the combined dict."""

    def test_returns_expected_top_level_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = capture("2026-05-22", Path(tmp))
            self.assertIn("captured_at", result)
            self.assertEqual(result["date"], "2026-05-22")
            self.assertIn("host", result)
            self.assertIn("tooling", result)
            self.assertIn("mcps", result)
            # MCPs is keyed by the .mcp.json server keys.
            self.assertIn("playwright", result["mcps"])


class CLITests(unittest.TestCase):
    """python -m bench.capture_versions ..."""

    def test_cli_writes_both_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc = main(["--date", "2099-12-31", "--results-root", tmp])
            self.assertEqual(rc, 0)
            json_path = Path(tmp) / "2099-12-31" / "versions.json"
            md_path = Path(tmp) / "2099-12-31" / "versions.lock.md"
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

    def test_versions_json_has_required_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            main(["--date", "2099-12-31", "--results-root", tmp])
            json_path = Path(tmp) / "2099-12-31" / "versions.json"
            data = json.loads(json_path.read_text())
            self.assertIn("host", data)
            self.assertIn("tooling", data)
            self.assertIn("mcps", data)

    def test_at_least_one_mcp_has_valid_sha256(self) -> None:
        """Per plan 01-06 acceptance: assert SHA field is 64-char hex
        for at least one installed MCP. Playwright per HANDOFF is
        always installed on the test machine."""
        # Skip on machines where no MCP binaries are installed.
        any_present = any(
            shutil.which(cmd) for cmd in
            ["playwright-mcp", "chrome-devtools-mcp", "lightpanda",
             "browser-use", "firecrawl-mcp", "obscura-mcp", "cloakbrowsermcp"]
        )
        if not any_present:
            self.skipTest("No MCP binaries installed on this machine")

        with tempfile.TemporaryDirectory() as tmp:
            main(["--date", "2099-12-31", "--results-root", tmp])
            data = json.loads(
                (Path(tmp) / "2099-12-31" / "versions.json").read_text()
            )
            with_sha = [
                (name, info["sha256"])
                for name, info in data["mcps"].items()
                if info.get("sha256")
            ]
            self.assertTrue(with_sha,
                            f"No MCP got a SHA256; mcps={data['mcps']}")
            for name, sha in with_sha:
                self.assertRegex(sha, SHA256_RE,
                                 f"{name}: bad SHA256 {sha!r}")


if __name__ == "__main__":
    unittest.main()
