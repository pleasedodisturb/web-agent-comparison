"""Tests for prompts/stage_walk.md S9-S26 cell balance (Phase 6 DESIGN-01/02).

Enforces the v1.1 stage-walk extension contract:

  - Exactly 18 cells matching ``^## S(\\d+) — `` for N in 9..26 exist
    (DESIGN-01 stage count).
  - Each S9-S26 cell carries a ``**Type:** (read|drive)`` tag, with the
    read/drive counts balanced at 9:9 ± 1 (DESIGN-01 parity).
  - The S16 cell body explicitly references >= 3 pages so the pagination
    contract is testable in-prompt (DESIGN-02 multi-page).

This file is created in Wave 0 BEFORE the S9-S26 cells are appended to
the prompt. The first two assertions skip when the S9-S26 cell count is
zero so Wave 0 passes; once Wave 4 (06-11) appends the cells, the same
tests assert against the new content.

Style: mirrors tests/test_aggregate_scores.py (unittest.TestCase,
``if __name__ == "__main__": unittest.main()``).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROMPT_PATH = _REPO_ROOT / "prompts" / "stage_walk.md"

# Match a cell header like "## S9 — Title here" or "## S26 — Title".
# The em-dash (U+2014) is the established v1.0 cell-header separator.
_CELL_HEADER_RE = re.compile(r"^## S(\d+) — ", re.MULTILINE)

# Match a `**Type:** read` or `**Type:** drive` tag inside a cell body.
_TYPE_TAG_RE = re.compile(r"^\*\*Type:\*\* (read|drive)\s*$", re.MULTILINE)


def _load_prompt() -> str:
    """Return the full text of prompts/stage_walk.md (UTF-8)."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _extract_cells(text: str) -> dict[int, str]:
    """Return {stage_number: cell_body_text} for every ## SN cell in text.

    Cells are bounded by the next ## SN header or end-of-file. The body
    INCLUDES the header line so a per-cell regex over the body can match
    metadata anywhere within the cell.
    """
    matches = list(_CELL_HEADER_RE.finditer(text))
    if not matches:
        return {}
    cells: dict[int, str] = {}
    for idx, m in enumerate(matches):
        stage_num = int(m.group(1))
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        cells[stage_num] = text[start:end]
    return cells


class TestStageWalkS9S26Cells(unittest.TestCase):
    """Cell-count + read/drive balance + S16 multi-page contract."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _load_prompt()
        cls.cells = _extract_cells(cls.text)
        cls.s9_s26_cells = {n: body for n, body in cls.cells.items() if 9 <= n <= 26}
        cls.s9_s26_count = len(cls.s9_s26_cells)

    def test_prompt_file_exists(self) -> None:
        """Sanity: prompts/stage_walk.md must exist at the expected path."""
        self.assertTrue(_PROMPT_PATH.is_file(),
                        f"prompts/stage_walk.md not found at {_PROMPT_PATH}")

    def test_s9_s26_cells_exist(self) -> None:
        """Exactly 18 cells for stages 9..26 (DESIGN-01).

        Pre-Wave-4 (S9-S26 cells not yet appended), this assertion
        skips so Wave 0 passes. Post-Wave-4 the count must be exactly 18.
        """
        if self.s9_s26_count == 0:
            self.skipTest("S9-S26 cells not yet appended (pre-Wave-4 state)")
        self.assertEqual(self.s9_s26_count, 18,
                         f"expected 18 cells for S9-S26, found {self.s9_s26_count}: "
                         f"{sorted(self.s9_s26_cells.keys())}")
        # Also assert the stage numbers are exactly {9..26}, no gaps,
        # no extras.
        self.assertEqual(set(self.s9_s26_cells.keys()), set(range(9, 27)),
                         f"S9-S26 stage numbers must be exactly 9..26, "
                         f"got {sorted(self.s9_s26_cells.keys())}")

    def test_read_drive_balance(self) -> None:
        """Each S9-S26 cell has a Type: read|drive tag; balance 9:9 +- 1.

        DESIGN-01 calls for read/drive parity. The plan allows a tolerance
        of +- 1 (so 8:10 or 10:8 is acceptable; 7:11 is not).
        """
        if self.s9_s26_count == 0:
            self.skipTest("S9-S26 cells not yet appended (pre-Wave-4 state)")

        read_count = 0
        drive_count = 0
        untyped: list[int] = []
        for stage_num, body in sorted(self.s9_s26_cells.items()):
            match = _TYPE_TAG_RE.search(body)
            if match is None:
                untyped.append(stage_num)
                continue
            if match.group(1) == "read":
                read_count += 1
            else:
                drive_count += 1

        self.assertEqual(untyped, [],
                         f"S9-S26 cells missing '**Type:** read|drive' tag: {untyped}")
        # Balance: |read - drive| <= 2 (so 9:9, 8:10, 10:8 all pass).
        diff = abs(read_count - drive_count)
        self.assertLessEqual(diff, 2,
                             f"read/drive balance off: read={read_count} drive="
                             f"{drive_count} (DESIGN-01 requires 9:9 +- 1)")

    def test_s16_multi_page(self) -> None:
        """S16 cell must mention >= 3 pages (DESIGN-02 pagination contract)."""
        if self.s9_s26_count == 0 or 16 not in self.s9_s26_cells:
            self.skipTest("S16 cell not yet appended (pre-Wave-4 state)")

        s16_body = self.s9_s26_cells[16]
        # Patterns acceptable: "across 5 pages", "pages 1-5", "3+ pages",
        # "three pages", ">= 3 pages". Case-insensitive.
        patterns = [
            r"across\s+\d+\s+pages",
            r"pages\s+1\s*[-–]\s*\d",
            r"\d+\+\s*pages",
            r"\bthree\b[^\n]*pages",
            r">=\s*3\s*pages",
            r"5\s+pages",
        ]
        combined = re.compile("|".join(patterns), re.IGNORECASE)
        self.assertIsNotNone(
            combined.search(s16_body),
            f"S16 cell does not reference >= 3 pages (DESIGN-02 contract). "
            f"Body excerpt: {s16_body[:300]!r}",
        )


if __name__ == "__main__":
    unittest.main()
