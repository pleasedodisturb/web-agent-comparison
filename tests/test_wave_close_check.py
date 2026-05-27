"""test_wave_close_check — unit tests for the SAFETY-05 wave-close auditor.

The auditor (`bench/wave_close_check.py`) verifies four invariants at
Wave 2 close:

  1. `.mcp.json` mcpServers count == 7 (the locked candidate set)
  2. `scoring/rubric.md` has exactly 8 rubric dimensions
  3. `git log --grep=terminal-craft --oneline` returns 0 lines
     (no Stage 2 toolkit leak in this repo)
  4. The MCP key set in `.mcp.json` matches the wave-start baseline
     (no MCP added or removed mid-wave)

Tests run via:
    python3 -m pytest tests/test_wave_close_check.py -v
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from bench.wave_close_check import (
    WAVE2_BASELINE,
    audit_candidate_count,
    audit_no_new_mcps,
    audit_rubric_columns,
    audit_terminal_craft_commits,
    main,
    render_audit_md,
    run_audit,
)


# ─── Fixture builders ───────────────────────────────────────────────────


def _write_mcp_json(path: Path, keys: list[str]) -> None:
    payload = {"mcpServers": {k: {"command": k, "args": []} for k in keys}}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


_BASELINE_KEYS = [
    "playwright",
    "browser-use",
    "chrome-devtools",
    "lightpanda",
    "obscura",
    "firecrawl",
    "cloakbrowser",
]


_RUBRIC_8_DIMS = """# Web Agent Scoring Rubric

## Dimensions (8 total, weighted)

| Dimension | Weight | 0 (Fail) | 5 (Partial) | 10 (Perfect) |
|-----------|--------|----------|-------------|---------------|
| **Data Quality** | 3x | a | b | c |
| **Reliability** | 3x | a | b | c |
| **Speed** | 2x | a | b | c |
| **Token Efficiency** | 2x | a | b | c |
| **Interaction Depth** | 2x | a | b | c |
| **JS Rendering** | 1x | a | b | c |
| **Setup Complexity** | 1x | a | b | c |
| **Error Handling** | 1x | a | b | c |

## Composite Score

`sum(...)` blah blah.

## Test Stages

| ID | Stage | Type |
|----|-------|------|
| S1 | Foo | Read-only |
"""


_RUBRIC_7_DIMS = """# Truncated Rubric

## Dimensions

| Dimension | Weight | 0 (Fail) | 5 (Partial) | 10 (Perfect) |
|-----------|--------|----------|-------------|---------------|
| **Data Quality** | 3x | a | b | c |
| **Reliability** | 3x | a | b | c |
| **Speed** | 2x | a | b | c |
| **Token Efficiency** | 2x | a | b | c |
| **Interaction Depth** | 2x | a | b | c |
| **JS Rendering** | 1x | a | b | c |
| **Setup Complexity** | 1x | a | b | c |

## Next Section
"""


# ─── Tests ──────────────────────────────────────────────────────────────


class TestCandidateCount(unittest.TestCase):
    def test_baseline_7_keys_returns_7(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.json"
            _write_mcp_json(path, _BASELINE_KEYS)
            self.assertEqual(audit_candidate_count(path), 7)

    def test_extra_key_returns_8(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.json"
            _write_mcp_json(path, _BASELINE_KEYS + ["sneaky-extra"])
            self.assertEqual(audit_candidate_count(path), 8)

    def test_missing_key_returns_6(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.json"
            _write_mcp_json(path, _BASELINE_KEYS[:-1])
            self.assertEqual(audit_candidate_count(path), 6)


class TestRubricColumns(unittest.TestCase):
    def test_8_dims_returns_8(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rubric.md"
            path.write_text(_RUBRIC_8_DIMS, encoding="utf-8")
            self.assertEqual(audit_rubric_columns(path), 8)

    def test_7_dims_returns_7(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rubric.md"
            path.write_text(_RUBRIC_7_DIMS, encoding="utf-8")
            self.assertEqual(audit_rubric_columns(path), 7)

    def test_real_rubric_returns_8(self):
        """Smoke against the actual committed scoring/rubric.md."""
        real = Path(__file__).resolve().parent.parent / "scoring" / "rubric.md"
        if real.is_file():
            self.assertEqual(audit_rubric_columns(real), 8)


def _ok(stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout=stdout, stderr=""
    )


def _git_log_side_effect(
    subject_stdout: str, path_stdout: str
):
    """Build a side_effect that returns different output per git invocation.

    First call (--pretty=format:%H %s) → subject_stdout
    Second call (-- terminal-craft/)   → path_stdout
    """

    def _se(argv, *args, **kwargs):
        if "--" in argv and "terminal-craft/" in argv:
            return _ok(path_stdout)
        return _ok(subject_stdout)

    return _se


class TestTerminalCraftCommits(unittest.TestCase):
    def test_no_matches_returns_0(self):
        with mock.patch(
            "bench.wave_close_check.subprocess.run",
            side_effect=_git_log_side_effect("", ""),
        ):
            self.assertEqual(audit_terminal_craft_commits(Path(".")), 0)

    def test_body_only_mention_does_not_count(self):
        """Subject-line body mentions for traceability should NOT match.

        E.g., a commit "G-703(04-04): generate recommendations.md (Stage 2
        unblock gate)" mentions terminal-craft in the body but the subject
        is plan work, not Stage 2 leak.
        """
        subject_log = (
            "abc1234 G-703(04-04): generate recommendations.md\n"
            "def5678 G-703: add HANDOFF.md\n"
            "ghi9012 Fix stray terminal-craft reference and README typo\n"
        )
        with mock.patch(
            "bench.wave_close_check.subprocess.run",
            side_effect=_git_log_side_effect(subject_log, ""),
        ):
            self.assertEqual(audit_terminal_craft_commits(Path(".")), 0)

    def test_conventional_commit_scope_counts(self):
        subject_log = (
            "abc1234 G-703(04-04): plan work\n"
            "def5678 feat(terminal-craft): bring in S2 toolkit\n"
            "ghi9012 fix(terminal-craft/scoring): bug\n"
        )
        with mock.patch(
            "bench.wave_close_check.subprocess.run",
            side_effect=_git_log_side_effect(subject_log, ""),
        ):
            self.assertEqual(audit_terminal_craft_commits(Path(".")), 2)

    def test_terminal_craft_prefix_subject_counts(self):
        subject_log = "abc1234 terminal-craft: import toolkit code\n"
        with mock.patch(
            "bench.wave_close_check.subprocess.run",
            side_effect=_git_log_side_effect(subject_log, ""),
        ):
            self.assertEqual(audit_terminal_craft_commits(Path(".")), 1)

    def test_path_touched_counts(self):
        with mock.patch(
            "bench.wave_close_check.subprocess.run",
            side_effect=_git_log_side_effect("", "abc1234\ndef5678\n"),
        ):
            self.assertEqual(audit_terminal_craft_commits(Path(".")), 2)

    def test_subject_and_path_overlap_dedupes(self):
        """The same commit hitting both vectors should count once."""
        with mock.patch(
            "bench.wave_close_check.subprocess.run",
            side_effect=_git_log_side_effect(
                "abc1234 feat(terminal-craft): code\n",
                "abc1234\n",
            ),
        ):
            self.assertEqual(audit_terminal_craft_commits(Path(".")), 1)


class TestNoNewMcps(unittest.TestCase):
    def test_baseline_match_returns_true(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.json"
            _write_mcp_json(path, _BASELINE_KEYS)
            self.assertTrue(audit_no_new_mcps(path, WAVE2_BASELINE))

    def test_extra_key_returns_false(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.json"
            _write_mcp_json(path, _BASELINE_KEYS + ["intruder"])
            self.assertFalse(audit_no_new_mcps(path, WAVE2_BASELINE))

    def test_missing_key_returns_false(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.json"
            _write_mcp_json(path, _BASELINE_KEYS[:-1])
            self.assertFalse(audit_no_new_mcps(path, WAVE2_BASELINE))


class TestRunAudit(unittest.TestCase):
    def _stage(self, tmp: str, mcp_keys: list[str], rubric_text: str) -> tuple[Path, Path]:
        mcp_path = Path(tmp) / "mcp.json"
        rubric_path = Path(tmp) / "rubric.md"
        _write_mcp_json(mcp_path, mcp_keys)
        rubric_path.write_text(rubric_text, encoding="utf-8")
        return mcp_path, rubric_path

    def test_all_pass_when_baseline(self):
        with TemporaryDirectory() as tmp:
            mcp_path, rubric_path = self._stage(tmp, _BASELINE_KEYS, _RUBRIC_8_DIMS)
            with mock.patch(
                "bench.wave_close_check.subprocess.run",
                side_effect=_git_log_side_effect("", ""),
            ):
                result = run_audit(mcp_path, rubric_path, Path("."))
        self.assertEqual(result["candidate_count"], 7)
        self.assertEqual(result["rubric_columns"], 8)
        self.assertEqual(result["terminal_craft_commits"], 0)
        self.assertTrue(result["no_new_mcps"])
        self.assertTrue(result["all_pass"])

    def test_fail_when_extra_mcp(self):
        with TemporaryDirectory() as tmp:
            mcp_path, rubric_path = self._stage(
                tmp, _BASELINE_KEYS + ["extra"], _RUBRIC_8_DIMS
            )
            with mock.patch(
                "bench.wave_close_check.subprocess.run",
                side_effect=_git_log_side_effect("", ""),
            ):
                result = run_audit(mcp_path, rubric_path, Path("."))
        self.assertEqual(result["candidate_count"], 8)
        self.assertFalse(result["no_new_mcps"])
        self.assertFalse(result["all_pass"])

    def test_fail_when_rubric_truncated(self):
        with TemporaryDirectory() as tmp:
            mcp_path, rubric_path = self._stage(tmp, _BASELINE_KEYS, _RUBRIC_7_DIMS)
            with mock.patch(
                "bench.wave_close_check.subprocess.run",
                side_effect=_git_log_side_effect("", ""),
            ):
                result = run_audit(mcp_path, rubric_path, Path("."))
        self.assertEqual(result["rubric_columns"], 7)
        self.assertFalse(result["all_pass"])

    def test_fail_when_terminal_craft_commit_present(self):
        with TemporaryDirectory() as tmp:
            mcp_path, rubric_path = self._stage(tmp, _BASELINE_KEYS, _RUBRIC_8_DIMS)
            with mock.patch(
                "bench.wave_close_check.subprocess.run",
                side_effect=_git_log_side_effect(
                    "abc1 feat(terminal-craft): leak\n",
                    "",
                ),
            ):
                result = run_audit(mcp_path, rubric_path, Path("."))
        self.assertEqual(result["terminal_craft_commits"], 1)
        self.assertFalse(result["all_pass"])


class TestRenderAuditMd(unittest.TestCase):
    def _good_audit(self) -> dict:
        return {
            "candidate_count": 7,
            "rubric_columns": 8,
            "terminal_craft_commits": 0,
            "no_new_mcps": True,
            "all_pass": True,
            "baseline_keys": sorted(WAVE2_BASELINE),
            "actual_keys": sorted(WAVE2_BASELINE),
        }

    def test_md_contains_safety_05_reference(self):
        md = render_audit_md(self._good_audit(), "2026-05-28T00:00:00Z")
        self.assertIn("SAFETY-05", md)

    def test_md_contains_timestamp(self):
        md = render_audit_md(self._good_audit(), "2026-05-28T00:00:00Z")
        self.assertIn("2026-05-28T00:00:00Z", md)

    def test_md_contains_pass_for_all_checks_when_passing(self):
        md = render_audit_md(self._good_audit(), "2026-05-28T00:00:00Z")
        # Every check name should appear, paired with PASS
        for check in (
            "candidate_count",
            "rubric_columns",
            "terminal_craft_commits",
            "no_new_mcps",
        ):
            self.assertIn(check, md)
        # Status column has PASS at least 4 times for the 4 checks
        self.assertGreaterEqual(md.count("PASS"), 4)

    def test_md_marks_fail_when_a_check_fails(self):
        audit = self._good_audit()
        audit["candidate_count"] = 8
        audit["no_new_mcps"] = False
        audit["all_pass"] = False
        md = render_audit_md(audit, "2026-05-28T00:00:00Z")
        self.assertIn("FAIL", md)


class TestCli(unittest.TestCase):
    def test_cli_rc0_when_all_pass(self):
        with TemporaryDirectory() as tmp:
            mcp_path = Path(tmp) / "mcp.json"
            rubric_path = Path(tmp) / "rubric.md"
            out_path = Path(tmp) / "audit.md"
            _write_mcp_json(mcp_path, _BASELINE_KEYS)
            rubric_path.write_text(_RUBRIC_8_DIMS, encoding="utf-8")
            with mock.patch(
                "bench.wave_close_check.subprocess.run",
                side_effect=_git_log_side_effect("", ""),
            ):
                rc = main([
                    "--mcp-json", str(mcp_path),
                    "--rubric", str(rubric_path),
                    "--out", str(out_path),
                ])
            self.assertEqual(rc, 0)
            self.assertTrue(out_path.is_file())
            content = out_path.read_text(encoding="utf-8")
            self.assertIn("SAFETY-05", content)
            self.assertIn("PASS", content)

    def test_cli_rc1_when_check_fails(self):
        with TemporaryDirectory() as tmp:
            mcp_path = Path(tmp) / "mcp.json"
            rubric_path = Path(tmp) / "rubric.md"
            out_path = Path(tmp) / "audit.md"
            _write_mcp_json(mcp_path, _BASELINE_KEYS + ["extra"])
            rubric_path.write_text(_RUBRIC_8_DIMS, encoding="utf-8")
            with mock.patch(
                "bench.wave_close_check.subprocess.run",
                side_effect=_git_log_side_effect("", ""),
            ):
                rc = main([
                    "--mcp-json", str(mcp_path),
                    "--rubric", str(rubric_path),
                    "--out", str(out_path),
                ])
            self.assertNotEqual(rc, 0)
            content = out_path.read_text(encoding="utf-8")
            self.assertIn("FAIL", content)

    def test_cli_help_exits_0(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--help"])
        # argparse --help exits with code 0
        self.assertEqual(ctx.exception.code, 0)


class TestBaseline(unittest.TestCase):
    def test_baseline_is_exactly_7_locked_candidates(self):
        self.assertEqual(len(WAVE2_BASELINE), 7)
        self.assertEqual(
            WAVE2_BASELINE,
            {
                "playwright",
                "browser-use",
                "chrome-devtools",
                "lightpanda",
                "obscura",
                "firecrawl",
                "cloakbrowser",
            },
        )


if __name__ == "__main__":
    unittest.main()
