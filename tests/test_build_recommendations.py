"""test_build_recommendations — unit tests for Phase-4 Stage-2 graduation recs.

The builder (`bench/build_recommendations.py`) reads `results/<date>/scores.json`
and emits a Markdown file at `results/recommendations.md` containing four
locked tier sections (PRIMARY / SECONDARY / SANDBOX-ONLY / SKIP) covering
exactly the seven MCP candidates plus the dual-row browser-use-agent
SKIPPED entry. Tier assignments are LOCKED in
`.planning/phases/04-synthesis/04-CONTEXT.md`.

These tests are the RED gate of Phase 4 Plan 04-04 TDD:
  - TIER_ASSIGNMENTS exact membership for all 4 tiers (Tests 2-5)
  - SANDBOX-ONLY heading uses exact hyphenated form (Test 11 — WARNING 3)
  - Each tiered MCP has evidence citation (Test 7)
  - Future Waves section anchors to G-710 (Test 6)
  - browser-use-agent cites SKIPPED.md re-run procedure (Test 8)
  - Link back to 2026-05-27-mcp-comparison.md (Test 9)
  - Wave-close compliance footer notes candidate count = 7 (Test 10)
  - Every cloakbrowser mention has sandbox callout ≤3 lines (Test 4)
  - All 4 tier headings present (Test 1)

Run with:
    .venv/bin/python -m pytest tests/test_build_recommendations.py -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from bench.build_recommendations import (
    TIER_ASSIGNMENTS,
    TIER_DISPLAY_NAMES,
    build_recommendations,
    inject_sandbox_callouts,
    render_executive_summary,
    render_future_waves,
    render_tier_section,
    render_wave_close_compliance,
)


# ─── Fixtures ────────────────────────────────────────────────────────────


MINIMAL_SCORES_FIXTURE = {
    "playwright": {
        "capability": "tool-only",
        "mode": "default",
        "status": "SCORED",
        "scores": {
            "data_quality": 10, "error_handling": 5, "interaction_depth": 10,
            "js_rendering": 10, "reliability": 9, "setup_complexity": 7,
            "speed": 5, "token_efficiency": 5,
        },
    },
    "lightpanda": {
        "capability": "js-light",
        "mode": "default",
        "status": "SCORED",
        "scores": {
            "data_quality": 7, "error_handling": 5, "interaction_depth": "N/A",
            "js_rendering": 2, "reliability": 9, "setup_complexity": 7,
            "speed": 5, "token_efficiency": 5,
        },
    },
    "browser-use-direct": {
        "capability": "LLM-augmented",
        "mode": "direct",
        "status": "SCORED",
        "scores": {
            "data_quality": 10, "error_handling": 2, "interaction_depth": 2,
            "js_rendering": 10, "reliability": 5, "setup_complexity": 7,
            "speed": 5, "token_efficiency": 5,
        },
    },
    "chrome-devtools": {
        "capability": "tool-only",
        "mode": "default",
        "status": "SCORED",
        "scores": {
            "data_quality": 10, "error_handling": 2, "interaction_depth": 0,
            "js_rendering": 10, "reliability": 5, "setup_complexity": 7,
            "speed": 5, "token_efficiency": 5,
        },
    },
    "firecrawl": {
        "capability": "cloud",
        "mode": "markdown",
        "status": "SCORED",
        "scores": {
            "data_quality": 0, "error_handling": 5, "interaction_depth": "N/A",
            "js_rendering": 2, "reliability": 7, "setup_complexity": 7,
            "speed": 5, "token_efficiency": 5,
        },
    },
    "cloakbrowser": {
        "capability": "stealth-specialist",
        "mode": "sandbox-loopback",
        "status": "SCORED",
        "sandbox_only": True,
        "scores": {
            "data_quality": 10, "error_handling": 8, "interaction_depth": 10,
            "js_rendering": 10, "reliability": 10, "setup_complexity": 7,
            "speed": 5, "token_efficiency": 5,
        },
    },
    "obscura": {
        "capability": "stealth-specialist",
        "mode": "no-stealth-flag",
        "status": "SCORED",
        "scores": {
            "data_quality": 0, "error_handling": 2, "interaction_depth": 0,
            "js_rendering": 2, "reliability": 6, "setup_complexity": 7,
            "speed": 5, "token_efficiency": 5,
        },
    },
    "browser-use-agent": {
        "capability": "LLM-augmented",
        "mode": "agent",
        "status": "SKIPPED",
        "skip_reason": "LLM_KEY_ABSENT",
        "skip_evidence": "results/2026-05-26/browser-use-agent/SKIPPED.md",
        "scores": {k: "N/A" for k in (
            "data_quality", "error_handling", "interaction_depth",
            "js_rendering", "reliability", "setup_complexity",
            "speed", "token_efficiency",
        )},
    },
}


@pytest.fixture
def scores_path(tmp_path: Path) -> Path:
    p = tmp_path / "scores.json"
    p.write_text(json.dumps(MINIMAL_SCORES_FIXTURE), encoding="utf-8")
    return p


@pytest.fixture
def rendered_output(scores_path: Path, tmp_path: Path) -> str:
    """Run the full builder against the fixture; return the rendered string."""
    out_path = tmp_path / "recommendations.md"
    md = build_recommendations(scores_path, out_path)
    return md


# ─── TIER_ASSIGNMENTS membership (locked) ────────────────────────────────


def test_tier_assignments_constant_exact_membership():
    """TIER_ASSIGNMENTS dict must match the user-locked 04-CONTEXT.md tiers."""
    assert set(TIER_ASSIGNMENTS.keys()) == {
        "PRIMARY", "SECONDARY", "SANDBOX_ONLY", "SKIP"
    }
    assert TIER_ASSIGNMENTS["PRIMARY"] == ["playwright", "lightpanda"]
    assert TIER_ASSIGNMENTS["SECONDARY"] == [
        "browser-use-direct", "chrome-devtools", "firecrawl",
    ]
    assert TIER_ASSIGNMENTS["SANDBOX_ONLY"] == ["cloakbrowser"]
    assert TIER_ASSIGNMENTS["SKIP"] == ["obscura", "browser-use-agent"]


def test_tier_display_names_sandbox_only_hyphenated():
    """TIER_DISPLAY_NAMES['SANDBOX_ONLY'] must be 'SANDBOX-ONLY' (WARNING 3)."""
    assert TIER_DISPLAY_NAMES["SANDBOX_ONLY"] == "SANDBOX-ONLY"


# ─── Test 1 — all 4 tier headings present ────────────────────────────────


def test_rendered_contains_all_four_tier_headings(rendered_output):
    """All 4 tier headings (PRIMARY/SECONDARY/SANDBOX-ONLY/SKIP) appear."""
    for heading in ("PRIMARY", "SECONDARY", "SANDBOX-ONLY", "SKIP"):
        assert heading in rendered_output, f"missing tier heading: {heading}"


# ─── Test 2 — PRIMARY tier exact membership ──────────────────────────────


def test_primary_section_exact_membership(rendered_output):
    """PRIMARY section names playwright AND lightpanda; no other tier MCPs."""
    # Slice the PRIMARY section between its heading and the next H2.
    lines = rendered_output.splitlines()
    primary_lines: list[str] = []
    in_primary = False
    for line in lines:
        if line.startswith("## PRIMARY"):
            in_primary = True
            continue
        if in_primary and line.startswith("## ") and not line.startswith("## PRIMARY"):
            break
        if in_primary:
            primary_lines.append(line)
    primary_text = "\n".join(primary_lines)
    assert "playwright" in primary_text
    assert "lightpanda" in primary_text
    # MCPs that belong to OTHER tiers must NOT be named in the PRIMARY section.
    for other in (
        "browser-use-direct",
        "browser-use-agent",
        "chrome-devtools",
        "firecrawl",
        "obscura",
        "cloakbrowser",
    ):
        assert other not in primary_text, (
            f"{other} (not a PRIMARY MCP) appears in PRIMARY section"
        )


# ─── Test 3 — SECONDARY tier exact membership ────────────────────────────


def test_secondary_section_exact_membership(rendered_output):
    """SECONDARY section names browser-use-direct, chrome-devtools, firecrawl."""
    lines = rendered_output.splitlines()
    sec_lines: list[str] = []
    in_sec = False
    for line in lines:
        if line.startswith("## SECONDARY"):
            in_sec = True
            continue
        if in_sec and line.startswith("## ") and not line.startswith("## SECONDARY"):
            break
        if in_sec:
            sec_lines.append(line)
    sec_text = "\n".join(sec_lines)
    assert "browser-use-direct" in sec_text
    assert "chrome-devtools" in sec_text
    assert "firecrawl" in sec_text
    for other in (
        "playwright",
        "lightpanda",
        "obscura",
        "cloakbrowser",
        "browser-use-agent",
    ):
        # Be careful: 'browser-use-direct' substring contains nothing else.
        # Use word-boundary-ish check via surrounding non-alpha chars.
        assert other not in sec_text, (
            f"{other} (not a SECONDARY MCP) appears in SECONDARY section"
        )


# ─── Test 4 — SANDBOX-ONLY exact membership + callout proximity ──────────


def test_sandbox_only_section_exact_membership_and_callout(rendered_output):
    """SANDBOX-ONLY tier names cloakbrowser only; sandbox callout ≤3 lines.

    The cloakbrowser mention inside the SANDBOX-ONLY section must be
    accompanied by a "Sandbox only — do not point at authenticated sessions"
    callout within ≤3 lines.
    """
    lines = rendered_output.splitlines()
    sb_lines: list[str] = []
    sb_start_idx: int | None = None
    for idx, line in enumerate(lines):
        if line.startswith("## SANDBOX-ONLY"):
            sb_start_idx = idx
            break
    assert sb_start_idx is not None, "SANDBOX-ONLY heading not found"

    # Slice until next ## heading
    for line in lines[sb_start_idx + 1:]:
        if line.startswith("## "):
            break
        sb_lines.append(line)
    sb_text = "\n".join(sb_lines)
    assert "cloakbrowser" in sb_text
    # No other tier members in this section
    for other in (
        "playwright",
        "lightpanda",
        "browser-use-direct",
        "browser-use-agent",
        "chrome-devtools",
        "firecrawl",
        "obscura",
    ):
        assert other not in sb_text, (
            f"{other} (not a SANDBOX-ONLY MCP) appears in SANDBOX-ONLY section"
        )

    # Find every cloakbrowser mention in sb_lines; for each, scan ±3 lines
    # for a "sandbox only" callout (case-insensitive).
    for i, line in enumerate(sb_lines):
        if "cloakbrowser" in line.lower():
            window_lo = max(0, i - 3)
            window_hi = min(len(sb_lines), i + 4)
            window = "\n".join(sb_lines[window_lo:window_hi]).lower()
            assert "sandbox only" in window, (
                f"cloakbrowser mention at line {i} lacks sandbox callout "
                f"within ±3 lines"
            )


# ─── Test 5 — SKIP tier exact membership ─────────────────────────────────


def test_skip_section_exact_membership(rendered_output):
    """SKIP section names obscura AND browser-use-agent; no others."""
    lines = rendered_output.splitlines()
    skip_lines: list[str] = []
    in_skip = False
    for line in lines:
        if line.startswith("## SKIP"):
            in_skip = True
            continue
        if in_skip and line.startswith("## ") and not line.startswith("## SKIP"):
            break
        if in_skip:
            skip_lines.append(line)
    skip_text = "\n".join(skip_lines)
    assert "obscura" in skip_text
    assert "browser-use-agent" in skip_text
    for other in (
        "playwright",
        "lightpanda",
        "browser-use-direct",
        "chrome-devtools",
        "firecrawl",
        "cloakbrowser",
    ):
        assert other not in skip_text, (
            f"{other} (not a SKIP MCP) appears in SKIP section"
        )


# ─── Test 6 — Future Waves anchors G-710 ─────────────────────────────────


def test_future_waves_section_references_g710(rendered_output):
    """Future Waves section is present and contains G-710 anchor."""
    assert "Future Waves" in rendered_output
    assert "G-710" in rendered_output


# ─── Test 7 — every tiered MCP cites evidence ────────────────────────────


def test_each_tiered_mcp_has_evidence_citation(rendered_output):
    """Each tiered MCP has at least one cited evidence string.

    Evidence = composite score (e.g. "7.93", "6.31", "5.87", "5.60", "4.23",
    "8.33", "3.27"), a capability tag (e.g. "tool-only", "js-light",
    "LLM-augmented", "stealth-specialist", "cloud"), or a DEEP_ANALYSIS.md
    reference. We assert composite-score presence (the strictest of the three).
    """
    expected_evidence: dict[str, list[str]] = {
        "playwright": ["7.93"],
        "lightpanda": ["6.31"],
        "browser-use-direct": ["5.87"],
        "chrome-devtools": ["5.60", "5.6"],
        "firecrawl": ["4.23"],
        "cloakbrowser": ["8.33"],
        "obscura": ["3.27"],
        "browser-use-agent": ["SKIPPED", "LLM_KEY_ABSENT"],
    }
    for mcp, candidates in expected_evidence.items():
        found = any(c in rendered_output for c in candidates)
        assert found, (
            f"{mcp} lacks any of the expected evidence strings {candidates}"
        )


# ─── Test 8 — browser-use-agent SKIP entry cites SKIPPED.md ──────────────


def test_browser_use_agent_cites_skipped_md_re_run_procedure(rendered_output):
    """browser-use-agent SKIP entry cites SKIPPED.md as re-run procedure."""
    assert "SKIPPED.md" in rendered_output
    # Re-run procedure summary phrase
    lowered = rendered_output.lower()
    assert "re-run" in lowered or "rerun" in lowered or "re run" in lowered


# ─── Test 9 — link back to scored report ─────────────────────────────────


def test_links_back_to_scored_report(rendered_output):
    """File links to results/2026-05-27-mcp-comparison.md as evidence source."""
    assert "2026-05-27-mcp-comparison.md" in rendered_output


# ─── Test 10 — wave-close compliance footer ──────────────────────────────


def test_wave_close_compliance_footer_notes_candidate_count(rendered_output):
    """Footer notes candidate count = 7 (preview of SAFETY-05 audit)."""
    # The compliance footer should explicitly cite "7" as the candidate count.
    # Accept either "= 7" or "count: 7" or "7 candidates" idioms.
    assert (
        "= 7" in rendered_output
        or "count: 7" in rendered_output
        or "7 candidates" in rendered_output
        or "candidate count = 7" in rendered_output.lower()
        or "candidate count: 7" in rendered_output.lower()
    ), "wave-close compliance footer must reference candidate count = 7"


# ─── Test 11 — WARNING 3: SANDBOX-ONLY exact heading form ────────────────


def test_sandbox_only_heading_exact_hyphenated_form(rendered_output):
    """Rendered output uses 'SANDBOX-ONLY' exactly; never 'SANDBOX_ONLY'.

    The Python identifier `SANDBOX_ONLY` is fine inside the source code,
    but the rendered Markdown must NOT contain that underscored form.
    Other variants (`Sandbox-Only`, `Sandbox Only` as a heading) are also
    rejected. The inline callout phrase
    "Sandbox only — do not point at authenticated sessions" is a separate
    string that contains "Sandbox only" with mixed case — this is allowed
    (it's a phrase, not the heading).
    """
    assert "SANDBOX-ONLY" in rendered_output
    assert "SANDBOX_ONLY" not in rendered_output, (
        "rendered output contains the underscored Python-identifier form "
        "'SANDBOX_ONLY' — heading must use the hyphenated 'SANDBOX-ONLY'"
    )
    # The heading lines should be the canonical form; check the H2 line itself.
    h2_lines = [ln for ln in rendered_output.splitlines() if ln.startswith("## ")]
    sb_h2 = [ln for ln in h2_lines if "sandbox" in ln.lower()]
    assert any("SANDBOX-ONLY" in ln for ln in sb_h2), (
        f"no H2 heading uses 'SANDBOX-ONLY' (found {sb_h2})"
    )


# ─── Helper-function unit tests (separately from integration) ────────────


def test_render_executive_summary_mentions_seven_candidates():
    """Executive summary mentions 7 candidates and tier counts."""
    out = render_executive_summary()
    assert "7" in out
    # Must reference the scored report for evidence
    assert "2026-05-27-mcp-comparison.md" in out


def test_render_future_waves_includes_g710_link():
    """render_future_waves emits an H2 + G-710 reference."""
    out = render_future_waves()
    assert out.startswith("## ")
    assert "Future Waves" in out
    assert "G-710" in out


def test_render_wave_close_compliance_says_seven_and_eight():
    """Compliance footer states candidate count = 7, rubric col count = 8."""
    out = render_wave_close_compliance()
    assert "7" in out
    assert "8" in out


def test_inject_sandbox_callouts_idempotent():
    """inject_sandbox_callouts must not double-inject when already present."""
    md = (
        "cloakbrowser is great.\n"
        "**Sandbox only — do not point at authenticated sessions.**\n"
    )
    once = inject_sandbox_callouts(md)
    twice = inject_sandbox_callouts(once)
    # Count callouts; should not grow on the second pass.
    assert once.lower().count("sandbox only") == twice.lower().count("sandbox only")


def test_render_tier_section_uses_display_heading_for_sandbox_only(
    scores_path: Path,
):
    """render_tier_section for SANDBOX_ONLY key emits SANDBOX-ONLY heading."""
    scores = json.loads(scores_path.read_text())
    out = render_tier_section(
        "SANDBOX_ONLY", TIER_ASSIGNMENTS["SANDBOX_ONLY"], scores, sandbox_only=True,
    )
    assert "## SANDBOX-ONLY" in out
    assert "## SANDBOX_ONLY" not in out


# ─── WR-05: build_recommendations creates parent directory ───────────────


def test_wr05_build_recommendations_creates_parent_directory(
    scores_path: Path, tmp_path: Path
):
    """WR-05: nested output paths should be created on demand."""
    nested_out = tmp_path / "nested" / "dirs" / "recommendations.md"
    assert not nested_out.parent.is_dir()
    build_recommendations(scores_path, nested_out)
    assert nested_out.is_file()
