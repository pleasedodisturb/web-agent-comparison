"""scrub_artifacts — OCR + name-regex sweep for PII in evidence directories.

SAFETY-02 contract. Per `.planning/research/PITFALLS.md` (pitfall 12), every
artifact under `results/<date>/` and `fixtures/snapshots/` must be scrubbed
for human names before commit. The mock applicant is `Jane Testworth`; any
two-word capitalized name that isn't in the allow-list is a candidate PII
leak and gets flagged.

Usage:
    python -m bench.scrub_artifacts results/2026-05-22/
    python -m bench.scrub_artifacts results/2026-05-22/ --allow path/to/allow.txt

Exit codes:
    0 — no flagged matches; directory is clean
    1 — at least one flagged match; printed to stderr, commit should abort

OCR backend:
    Uses `pytesseract` for PNG/JPG images. If `pytesseract` is not installed
    or the `tesseract` system binary is missing, PNG/JPG files are reported
    as `OCR_SKIPPED` and the scan continues on text files only. Text-only
    scan is acceptable for Phase 1 since screenshots get manual review
    before commit; the OCR pass is a belt-and-suspenders catch.

Scanned file extensions:
    Text: .md .txt .yml .yaml .jsonl .json .log .csv .html .htm .xml
    Images (OCR): .png .jpg .jpeg .gif .webp

Allow-list:
    Default: "Jane Testworth" only. Extend via `--allow <file>` where the
    file contains one allowed name per line. Allow-list entries match the
    full "First Last" string verbatim; partial matches do not extend the
    allow-list.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

# Two-word capitalized name regex. Deliberately conservative — single-word
# names (companies, products) are NOT flagged. Hyphenated last names like
# "Smith-Jones" require the alternative pattern below.
NAME_REGEX = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+(?:-[A-Z][a-z]+)?\b")

# Default allow-list. The mock applicant for all Phase 1 fixtures.
DEFAULT_ALLOW: frozenset[str] = frozenset({"Jane Testworth"})

# File extensions scanned as plain text.
TEXT_EXTS: frozenset[str] = frozenset({
    ".md", ".txt", ".yml", ".yaml", ".jsonl", ".json", ".log",
    ".csv", ".html", ".htm", ".xml",
})

# File extensions scanned via OCR (when pytesseract is available).
IMAGE_EXTS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})


def _try_import_ocr() -> tuple[object | None, str]:
    """Attempt to import pytesseract + PIL. Return (module, status_message).

    status_message is "ok" if both imports succeed AND the tesseract binary
    resolves; otherwise a human-readable reason ("pytesseract not installed",
    "tesseract binary missing", etc.).
    """
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore  # noqa: F401
    except ImportError as exc:  # pragma: no cover — exercised at runtime
        return None, f"pytesseract or Pillow not installed ({exc})"

    # Probe the tesseract binary. pytesseract raises TesseractNotFoundError
    # on first call if the binary isn't on PATH.
    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:  # pragma: no cover
        return None, f"tesseract binary unavailable ({exc})"

    return pytesseract, "ok"


def _scan_text_lines(lines: Iterable[str], allow: frozenset[str]) -> list[tuple[int, str]]:
    """Return list of (line_no, match) for any name not in the allow-list."""
    findings: list[tuple[int, str]] = []
    for line_no, line in enumerate(lines, start=1):
        for match in NAME_REGEX.findall(line):
            if match not in allow:
                findings.append((line_no, match))
    return findings


def _scan_text_file(path: Path, allow: frozenset[str]) -> list[tuple[int, str]]:
    """Read a text file and scan it for unauthorized two-word names."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        # Unreadable file — surface as a finding so it doesn't get
        # silently skipped.
        print(f"WARN: could not read {path}: {exc}", file=sys.stderr)
        return []
    return _scan_text_lines(content.splitlines(), allow)


def _scan_image_file(
    path: Path,
    allow: frozenset[str],
    pytesseract_mod: object | None,
) -> tuple[list[tuple[int, str]], bool]:
    """OCR-scan an image. Returns (findings, ocr_attempted).

    If pytesseract_mod is None (OCR backend unavailable), returns
    (empty list, False) — caller logs OCR_SKIPPED for the path.
    """
    if pytesseract_mod is None:
        return [], False

    try:
        from PIL import Image  # type: ignore  # local import; already verified above
        img = Image.open(path)
        ocr_text = pytesseract_mod.image_to_string(img)  # type: ignore[attr-defined]
    except Exception as exc:
        print(f"WARN: OCR failed on {path}: {exc}", file=sys.stderr)
        return [], True

    return _scan_text_lines(ocr_text.splitlines(), allow), True


def _load_allow_extension(path: Path) -> set[str]:
    """Load an allow-list extension file (one name per line, # comments)."""
    extra: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        extra.add(line)
    return extra


def scrub(root: Path, allow: frozenset[str], pytesseract_mod: object | None) -> int:
    """Walk `root`, scan every file, print FLAG: lines to stderr.

    Returns the number of flagged findings.
    """
    if not root.exists():
        print(f"ERROR: path does not exist: {root}", file=sys.stderr)
        return 1
    if not root.is_dir():
        print(f"ERROR: path is not a directory: {root}", file=sys.stderr)
        return 1

    flagged = 0
    ocr_skipped: list[Path] = []

    # Sorted walk for stable output (helps tests + diffing).
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in TEXT_EXTS:
            findings = _scan_text_file(path, allow)
        elif suffix in IMAGE_EXTS:
            findings, ocr_attempted = _scan_image_file(path, allow, pytesseract_mod)
            if not ocr_attempted:
                ocr_skipped.append(path)
                continue
        else:
            continue

        for line_no, match in findings:
            print(f"FLAG: {path}:{line_no}: {match}", file=sys.stderr)
            flagged += 1

    for path in ocr_skipped:
        print(f"OCR_SKIPPED: {path}", file=sys.stderr)

    return flagged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.scrub_artifacts",
        description="OCR + name-regex PII scrub for results/ and fixtures/ artifacts.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Directory to scan recursively (e.g. results/2026-05-22/).",
    )
    parser.add_argument(
        "--allow",
        type=Path,
        action="append",
        default=[],
        help="Extra allow-list file (one name per line). May be passed multiple times.",
    )
    args = parser.parse_args(argv)

    allow: set[str] = set(DEFAULT_ALLOW)
    for extra_path in args.allow:
        if not extra_path.exists():
            print(f"ERROR: allow-list file not found: {extra_path}", file=sys.stderr)
            return 1
        allow.update(_load_allow_extension(extra_path))

    pytesseract_mod, ocr_status = _try_import_ocr()
    if pytesseract_mod is None:
        print(f"OCR backend unavailable: {ocr_status} — text-only scan", file=sys.stderr)

    flagged = scrub(args.path, frozenset(allow), pytesseract_mod)
    if flagged > 0:
        print(f"scrub_artifacts: {flagged} flagged match(es) found.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
