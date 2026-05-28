"""_linear — Single source of truth for G-703 Linear ticket mappings.

The canonical MCP -> sub-ticket mapping lives in
`docs/LINEAR_SUBTICKETS.md`. This module duplicates the mapping as a
Python constant so the two Phase 4 builders (`build_report.py` +
`build_recommendations.py`) cannot drift on which MCP belongs to which
sub-ticket — fixing CR-01.

If `docs/LINEAR_SUBTICKETS.md` is updated, update `SUBTICKETS` below to
match. The constants are imported by both builders; renaming a key
without updating the docs file is a code-review red flag.

Stdlib-only.
"""

from __future__ import annotations

# Source of truth: docs/LINEAR_SUBTICKETS.md (2026-05-22)
# Parent epic: G-703 (estimate=16, break-before-cycle signal).
# 8 sub-tickets total: 7 per-MCP scoring + 1 synthesis.
G703_URL = "https://linear.app/abandoned-yachts/issue/G-703"
G710_URL = "https://linear.app/abandoned-yachts/issue/G-710"

# Per-MCP sub-ticket mapping. Keys MUST match the 7 candidate MCP names
# exactly as they appear in `.mcp.json` mcpServers and in the bench
# constants (SEVEN_MCPS / WAVE2_BASELINE / TIER_ASSIGNMENTS).
SUBTICKETS: dict[str, str] = {
    "playwright":      "G-714",
    "browser-use":     "G-715",
    "chrome-devtools": "G-716",
    "lightpanda":      "G-717",
    "obscura":         "G-718",
    "firecrawl":       "G-719",
    "cloakbrowser":    "G-720",
}

# Synthesis sub-ticket (Phase 4 — this work).
SYNTHESIS_SUBTICKET = "G-721"

# Source-of-truth doc path (relative to repo root). Builder footers cite
# this so readers can verify the mapping independently.
LINEAR_SUBTICKETS_DOC = "docs/LINEAR_SUBTICKETS.md"


def render_subtickets_inline(separator: str = ", ") -> str:
    """Render the per-MCP sub-ticket list as a single inline string.

    Used by the builder footers so both files emit identical text.
    Example output (separator=", "):
        "G-714 (playwright), G-715 (browser-use), G-716 (chrome-devtools), ..."
    """
    return separator.join(
        f"{ticket} ({mcp})" for mcp, ticket in SUBTICKETS.items()
    )
