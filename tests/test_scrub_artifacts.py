"""Tests for bench/scrub_artifacts.

Uses unittest (per PLAN.md task 4) so we can run via:
    uv run python -m unittest tests.test_scrub_artifacts -v

Each test spawns the CLI in a subprocess so we exercise the real exit-code
contract that downstream callers (CI, pre-commit, etc.) rely on.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def run_scrub(target: Path) -> subprocess.CompletedProcess[str]:
    """Run `python -m bench.scrub_artifacts <target>` and capture output."""
    return subprocess.run(
        [sys.executable, "-m", "bench.scrub_artifacts", str(target)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


class ScrubArtifactsTests(unittest.TestCase):
    def test_jane_testworth_only_passes(self) -> None:
        """A directory containing only the mock applicant name must exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "ok"
            target.mkdir()
            (target / "stage_s5.md").write_text(
                "Jane Testworth filled the form.\n"
                "Some product name like FormHero appears here.\n"
                "## Notes\nA single CapitalizedWord is fine.\n",
                encoding="utf-8",
            )
            result = run_scrub(target)
            self.assertEqual(
                result.returncode,
                0,
                msg=f"Expected exit 0; got {result.returncode}.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}",
            )

    def test_john_smith_fails_with_flag(self) -> None:
        """A directory with a non-allow-listed two-word name must exit 1."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bad"
            target.mkdir()
            (target / "stage_s1.md").write_text(
                "Applicant: John Smith.\n",
                encoding="utf-8",
            )
            result = run_scrub(target)
            self.assertEqual(
                result.returncode,
                1,
                msg=f"Expected exit 1; got {result.returncode}.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}",
            )
            self.assertIn(
                "John Smith",
                result.stderr,
                msg=f"Expected 'John Smith' in stderr; got: {result.stderr}",
            )
            self.assertIn(
                "FLAG:",
                result.stderr,
                msg=f"Expected 'FLAG:' prefix in stderr; got: {result.stderr}",
            )

    def test_missing_path_fails(self) -> None:
        """A nonexistent target path must exit 1, not crash."""
        result = run_scrub(Path("/tmp/definitely-does-not-exist-xyz-12345"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not exist", result.stderr)

    def test_extends_allow_list_via_flag(self) -> None:
        """`--allow` file extends the default allow-list."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "ok"
            target.mkdir()
            (target / "PROVENANCE.md").write_text(
                "Source: Greenhouse Software (vendor name appears).\n"
                "Captured by Eng Team.\n",
                encoding="utf-8",
            )
            allow_file = tmp_path / "allow.txt"
            allow_file.write_text(
                "# Vendor names that legitimately appear in PROVENANCE.md\n"
                "Greenhouse Software\n"
                "Eng Team\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bench.scrub_artifacts",
                    str(target),
                    "--allow",
                    str(allow_file),
                ],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )
            self.assertEqual(
                result.returncode,
                0,
                msg=f"Expected exit 0 with allow-list extension; got {result.returncode}.\n"
                f"stderr: {result.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
