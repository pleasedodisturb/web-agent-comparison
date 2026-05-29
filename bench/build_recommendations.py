"""build_recommendations — Phase-4 Stage-2 graduation recommendations builder.

Reads `results/<date>/scores.json` and emits a Markdown file at
`results/recommendations.md` with explicit Stage-2 graduation tiers
(PRIMARY / SECONDARY / SANDBOX-ONLY / SKIP) for each of the seven MCP
candidates plus the dual-row browser-use-agent SKIPPED entry.

The tier assignments are LOCKED in
`.planning/phases/04-synthesis/04-CONTEXT.md` per user decision and
encoded here as the module-level `TIER_ASSIGNMENTS` constant. This
builder DOES NOT re-litigate tier assignments; it just renders them
faithfully with citations to per-MCP evidence.

WARNING 3 — heading form
------------------------
The Python identifier for the sandbox tier is `SANDBOX_ONLY` (Python
syntax requires underscores), but the rendered Markdown heading MUST
use the hyphenated form `SANDBOX-ONLY`. `TIER_DISPLAY_NAMES` maps the
identifier to the display string; every render path goes through it.

CLI
---
    python -m bench.build_recommendations \\
        --scores results/2026-05-26/scores.json \\
        --out results/recommendations.md

The module is stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from bench._linear import (
    G703_URL as _LINEAR_G703_URL,
    G710_URL as _LINEAR_G710_URL,
    LINEAR_SUBTICKETS_DOC,
    SUBTICKETS,
    render_subtickets_inline,
)
from bench._sandbox import (
    SANDBOX_CALLOUT,
    SANDBOX_RECOGNITION_RE,
    inject_sandbox_callouts,
)

# ─── LOCKED tier assignments (per 04-CONTEXT.md) ─────────────────────────


TIER_ASSIGNMENTS: dict[str, list[str]] = {
    "PRIMARY": ["playwright", "lightpanda"],
    "SECONDARY": ["browser-use-direct", "chrome-devtools", "firecrawl"],
    "SANDBOX_ONLY": ["cloakbrowser"],
    "SKIP": ["obscura", "browser-use-agent"],
}


# Python identifier `SANDBOX_ONLY` (underscore) → Markdown heading
# `SANDBOX-ONLY` (hyphen). WARNING 3 — the rendered output uses the
# hyphenated form exclusively.
TIER_DISPLAY_NAMES: dict[str, str] = {
    "PRIMARY": "PRIMARY",
    "SECONDARY": "SECONDARY",
    "SANDBOX_ONLY": "SANDBOX-ONLY",
    "SKIP": "SKIP",
}


# Per-MCP rationale paragraphs (lifted from 04-CONTEXT.md). Centralised
# here so the renderer can pick the right paragraph by MCP name.
#
# Style rule: each rationale describes ONLY the MCP under discussion;
# it does NOT name other MCPs by literal name. Comparisons to other
# tiers happen elsewhere (executive summary, cross-cut tables). This
# keeps each tier section self-contained, prevents accidental cross-tier
# leakage at the prose level, and makes tier-membership tests trivially
# enforceable.
USE_FOR_RATIONALES: dict[str, str] = {
    "playwright": (
        "Interactive default for the production agent toolkit. Full "
        "S1-S8 surface with the Phase-1 calibration baseline; the "
        "`browser_fill_form` batch-fill primitive (re-grounded by Phase "
        "2 P02..P05 evidence) is a real token-efficiency win on "
        "multi-field forms. Pair with a read-only specialist when SSR "
        "extraction throughput matters more than interaction depth."
    ),
    "lightpanda": (
        "Read-only specialist for SSR-only paths. 13 ms cold-start "
        "(>50x faster than the next-fastest MCP measured this wave), "
        "1.7 s extraction. Categorically N/A for S4-S8 per FAIRNESS-03 "
        "— and that's the point: use it for static HTML / server-"
        "rendered targets where sub-second cold-start matters; reach for "
        "an interactive PRIMARY peer for any form-handling workload."
    ),
    "browser-use-direct": (
        "LLM-agnostic deterministic fallback for when the PRIMARY-tier "
        "interactive default is unavailable or `--mcp` constraints "
        "apply. Smallest pass-to-pass spread of any agent-driven MCP "
        "this wave (delta = 0.33). The deterministic tool surface "
        "(navigate / get_state / extract / screenshot) works without "
        "any LLM key; the agent-mode escape hatch is a separate row "
        "evaluated in the SKIP tier."
    ),
    "chrome-devtools": (
        "DevTools-exclusive value (`list_console_messages`, "
        "`list_network_requests`, `performance_start_trace`) — "
        "recommended for performance/debugging probes, not bulk "
        "extraction. PASS3 outlier shows agent-discovery uplift "
        "potential (composite jumps to 8.33 when the SSR-rescue "
        "workaround is discovered); the 7 DevTools-exclusive tools are "
        "structurally inventoried but not exercised by the current S1-"
        "S8 walk."
    ),
    "firecrawl": (
        "Cloud SSR specialist — 9x byte-count lift on Greenhouse SSR "
        "(24,237 vs ~2.6 KB structured-YAML from a local interactive "
        "peer in live-probe comparison). Refuted on Ashby React SPA "
        "(203 bytes of footer chrome only). Use for SSR-heavy targets "
        "where LLM-cleaned markdown is more valuable than structured "
        "DOM extraction; not a JS-SPA fallback. Loopback-incompat "
        "tagged `env-mismatch` per FAIRNESS-06."
    ),
    "cloakbrowser": (
        "Sandboxed stealth probes against the public Greenhouse + "
        "Ashby snapshot fixtures only. Leads the S1-S8 surface at 8.33 "
        "composite, but the closed-binary + cookie-touch + sandbox-"
        "loopback trust model is the binding constraint, not the "
        "stealth claim itself. The stealth claim is DEFERRED to G-710 "
        "— the loopback snapshot fixtures don't fingerprint-check."
    ),
    "obscura": (
        "Do NOT graduate this wave. macOS `Sec-CH-UA-Platform-*` leak "
        "per SAFETY-03 means `--stealth` is disabled by default; "
        "missing screenshot/file-upload primitives (S6 + S8 "
        "uncompletable on surface); SSRF guard rejects 127.0.0.1 → "
        "harness-incompat cascade. Re-evaluate after the G-710 Linux "
        "A/B."
    ),
    "browser-use-agent": (
        "Do NOT graduate this wave. Composite **0.00** with `tool-bug` "
        "attribution per FAIRNESS-06 — browser-use 0.12.7's MCP-agent "
        "path is deterministically broken when an LLM key is in env. "
        "Same binary in **direct mode** scores 5.87. Detail below."
    ),
}


# Per-MCP evidence citations: at least one DEEP_ANALYSIS.md or specific
# Phase 2/3 finding per row. The citations are stable file paths that
# do not change between runs.
EVIDENCE_LINKS: dict[str, list[str]] = {
    "playwright": [
        "Phase 1 calibration baseline — `results/2026-05-25/playwright/transcript.md`",
        "Capability matrix row — `results/2026-05-26/CAPABILITY_MATRIX.md`",
    ],
    "lightpanda": [
        "Per-MCP deep analysis — `results/2026-05-26/lightpanda/DEEP_ANALYSIS.md`",
        "Cross-cut cold-start finding — `results/2026-05-26/CROSS_CUT_SUMMARY.md` § 2",
    ],
    "browser-use-direct": [
        "Per-MCP deep analysis — `results/2026-05-26/browser-use-direct/DEEP_ANALYSIS.md`",
        "Dual-mode FAIRNESS-05 contract — `results/2026-05-26/CAPABILITY_MATRIX.md`",
    ],
    "chrome-devtools": [
        "Per-MCP deep analysis — `results/2026-05-26/chrome-devtools/DEEP_ANALYSIS.md`",
        "DevTools-exclusive tools (7 inventoried) — `results/2026-05-26/TOOLS_INVENTORY_SUMMARY.md`",
    ],
    "firecrawl": [
        "Per-MCP deep analysis — `results/2026-05-26/firecrawl/DEEP_ANALYSIS.md`",
        "Loopback-incompat attribution — `results/2026-05-26/scores.json` (`env-mismatch` tag)",
    ],
    "cloakbrowser": [
        "Per-MCP deep analysis — `results/2026-05-26/cloakbrowser/DEEP_ANALYSIS.md`",
        "SANDBOX_PROOF — `results/2026-05-26/cloakbrowser/SANDBOX_PROOF.md`",
        "Sandbox-only policy origin — `CLAUDE.md` § Constraints",
    ],
    "obscura": [
        "Per-MCP deep analysis — `results/2026-05-26/obscura/DEEP_ANALYSIS.md`",
        "SAFETY-03 macOS stealth leak — "
        "[`docs/external-findings/browser-tools-2026-05-21.md`]"
        "(../docs/external-findings/browser-tools-2026-05-21.md) § SAFETY-03",
    ],
    "browser-use-agent": [
        "Per-MCP deep analysis — `results/2026-05-26/browser-use-agent/DEEP_ANALYSIS.md`",
        "Raw stdio reproducer (no harness) — `results/2026-05-26/browser-use-agent/stdio_probe_evidence.log`",
        "v1.0.1 harness pass — `results/2026-05-26/browser-use-agent/PASS1/transcript.md`",
        "v1.0 SKIPPED baseline (sequestered) — `results/2026-05-26/browser-use-agent/_SKIPPED_20260528T180853Z/SKIPPED.md`",
        "Phase 2 audit — `results/2026-05-26/PHASE2_AUDIT.md`",
    ],
}


# SANDBOX_CALLOUT + SANDBOX_RECOGNITION_RE + inject_sandbox_callouts are
# imported from bench._sandbox above — single source of truth (WR-04 + IN-03).
# The original module-level definitions are removed so the two builders
# cannot drift on callout phrasing or injection algorithm.


# Linear ticket anchors — re-exported from bench._linear (single source of
# truth) so the URLs cannot drift between build_report.py and build_recommendations.py.
G710_URL = _LINEAR_G710_URL
G703_URL = _LINEAR_G703_URL


# ─── Pure helpers ────────────────────────────────────────────────────────


def aggregate_scores(scores_path: Path) -> dict[str, Any]:
    """Read scores.json from disk. Stdlib JSON; no schema validation."""
    if not scores_path.is_file():
        raise FileNotFoundError(f"scores.json not found at {scores_path}")
    return json.loads(scores_path.read_text(encoding="utf-8"))


_RUBRIC_WEIGHTS_LOCAL: dict[str, int] = {
    "data_quality": 3,
    "reliability": 3,
    "speed": 2,
    "token_efficiency": 2,
    "interaction_depth": 2,
    "js_rendering": 1,
    "setup_complexity": 1,
    "error_handling": 1,
}

# Published medians per the 2026-05-26 audit (PHASE2_AUDIT.md). Used as a
# fallback when scores.json does not carry a usable scores dict for a given
# MCP — keeps the historical numbers visible if a future wave's scores.json
# drops a row entirely. When scores.json provides data, that data wins
# (IN-02: don't ignore the function's own parameter).
_HARDCODED_COMPOSITES: dict[str, str] = {
    "playwright": "7.93",
    "lightpanda": "6.31",
    "browser-use-direct": "5.87",
    "chrome-devtools": "5.60",
    "firecrawl": "4.23",
    "cloakbrowser": "8.33",
    "obscura": "3.27",
    "browser-use-agent": "0.00",
}


def _composite_for(mcp: str, scores: dict[str, Any]) -> str:
    """Return the published composite string for a given MCP.

    Computes the N/A-aware weighted composite from `scores[mcp]["scores"]`
    when available; falls back to the 2026-05-26 hardcoded medians only
    when no usable scores dict exists for the row. SKIPPED rows return
    'SKIPPED'.

    IN-02 fix: the function previously ignored its `scores` parameter
    entirely and always returned from the hardcoded dict, which silently
    cited stale composites if scores.json was updated.
    """
    row = scores.get(mcp) if isinstance(scores, dict) else None
    if isinstance(row, dict):
        if row.get("status") == "SKIPPED":
            return "SKIPPED"
        row_scores = row.get("scores") or {}
        num = 0.0
        den = 0
        for k, w in _RUBRIC_WEIGHTS_LOCAL.items():
            v = row_scores.get(k)
            if v is None or v == "N/A":
                continue
            try:
                num += float(v) * w
                den += w
            except (TypeError, ValueError):
                continue
        if den > 0:
            return f"{num / den:.2f}"
    # Fall back to the historical median.
    return _HARDCODED_COMPOSITES.get(mcp, "—")


def _capability_for(mcp: str, scores: dict[str, Any]) -> str:
    """Pull capability tag from scores.json; fall back to '—'."""
    row = scores.get(mcp, {})
    return row.get("capability", "—")


def _mode_for(mcp: str, scores: dict[str, Any]) -> str:
    """Pull mode tag from scores.json; fall back to '—'."""
    row = scores.get(mcp, {})
    return row.get("mode", "—")


def _status_for(mcp: str, scores: dict[str, Any]) -> str:
    """Pull status from scores.json."""
    row = scores.get(mcp, {})
    return row.get("status", "—")


# ─── Section renderers ───────────────────────────────────────────────────


def render_executive_summary() -> str:
    """One-paragraph framing: 7 candidates → 4 tiers, link to scored report.

    Tier counts: PRIMARY=2, SECONDARY=3, SANDBOX-ONLY=1, SKIP=2 → 8 rows
    (browser-use dual-row contract per FAIRNESS-05). Candidate count is
    7 (browser-use counts as one candidate, produces two rows).
    """
    primary_n = len(TIER_ASSIGNMENTS["PRIMARY"])
    secondary_n = len(TIER_ASSIGNMENTS["SECONDARY"])
    sandbox_n = len(TIER_ASSIGNMENTS["SANDBOX_ONLY"])
    skip_n = len(TIER_ASSIGNMENTS["SKIP"])
    return (
        f"Of 7 MCP candidates evaluated 2026-05-27, **{primary_n} graduate to "
        f"PRIMARY**, **{secondary_n} to SECONDARY**, **{sandbox_n} SANDBOX-ONLY**, "
        f"and **{skip_n} are excluded (SKIP)** from the Stage-2 terminal-craft "
        "toolkit this wave. The 8 tier-row total reflects browser-use's "
        "FAIRNESS-05 dual-mode contract (one candidate, two rows: direct + "
        "agent). Detailed scoring + per-MCP deep analysis + methodology + "
        "negative-results + 2026-03 → 2026-05 overlay live at "
        "[results/2026-05-27-mcp-comparison.md](2026-05-27-mcp-comparison.md). "
        "Tier assignments below are LOCKED per "
        "[`.planning/phases/04-synthesis/04-CONTEXT.md`](../.planning/phases/"
        "04-synthesis/04-CONTEXT.md) — this file does not re-litigate them, "
        "it publishes them with citations."
    )


def _render_mcp_entry(
    mcp: str,
    scores: dict[str, Any],
    tier_key: str,
) -> str:
    """Render a single per-MCP entry inside a tier section.

    Each entry includes:
      - **Bolded MCP name** + composite + capability tag
      - **Use for:** rationale paragraph
      - **Evidence:** cite line(s)
      - For browser-use-agent SKIPPED: SKIPPED.md re-run procedure note
      - For cloakbrowser: inline sandbox callout INSIDE the entry
    """
    composite = _composite_for(mcp, scores)
    capability = _capability_for(mcp, scores)
    mode = _mode_for(mcp, scores)
    status = _status_for(mcp, scores)
    rationale = USE_FOR_RATIONALES.get(mcp, "(no rationale recorded)")
    citations = EVIDENCE_LINKS.get(mcp, [])

    lines: list[str] = []

    # Header line
    if status == "SKIPPED":
        header = (
            f"### `{mcp}` — composite **SKIPPED** "
            f"(`{capability}` / `{mode}`)"
        )
    else:
        header = (
            f"### `{mcp}` — composite **{composite}** "
            f"(`{capability}` / `{mode}`)"
        )
    lines.append(header)
    lines.append("")

    # Sandbox callout INSIDE the entry for cloakbrowser (right after header).
    if tier_key == "SANDBOX_ONLY" or mcp == "cloakbrowser":
        lines.append(SANDBOX_CALLOUT)
        lines.append("")

    # Use-for rationale
    lines.append(f"**Use for:** {rationale}")
    lines.append("")

    # browser-use-agent: bug callout for v1.0.1 tool-bug, OR (legacy) re-run
    # procedure if a future wave finds the row reverted to SKIPPED.
    if mcp == "browser-use-agent":
        if status == "SKIPPED":
            lines.append(
                "**Re-run procedure:** SKIPPED reason `LLM_KEY_ABSENT`. To "
                "re-run: (1) `rbw unlock`, (2) `export ANTHROPIC_API_KEY=$(rbw "
                "get \"Anthropic Claude\" --field Anthropic_API)`, (3) re-invoke "
                "plan 02-05 Task 2. Full procedure in `results/2026-05-26/"
                "browser-use-agent/_SKIPPED_*/SKIPPED.md`."
            )
        else:
            lines.append(
                "**Headline finding (v1.0.1):** 30s `BrowserStartEvent` timeout "
                "on the first `browser_navigate` call when `OPENAI_API_KEY` (or "
                "`ANTHROPIC_API_KEY`) is set in env. Every CDP-dependent tool "
                "then errors with `Root CDP client not initialized`. Reproducible "
                "without the harness via direct JSON-RPC to `browser-use --mcp` "
                "— see `stdio_probe_evidence.log`. Same binary in **direct mode** "
                "scores 5.87 with S1/S2/S3/S8 passing; the failure is gated on "
                "env-LLM-key presence. Tool-bug attribution per FAIRNESS-06. "
                "Tracked upstream at "
                "[browser-use/browser-use#4846](https://github.com/browser-use/"
                "browser-use/issues/4846) — re-score if a fix ships."
            )
        lines.append("")

    # For cloakbrowser, repeat the sandbox callout right before Evidence
    # so the citation lines (which themselves contain "cloakbrowser" in
    # paths like `results/2026-05-26/cloakbrowser/DEEP_ANALYSIS.md`) are
    # within ±3 lines of a sandbox callout.
    if mcp == "cloakbrowser":
        lines.append(SANDBOX_CALLOUT)
        lines.append("")

    # Evidence citations
    lines.append("**Evidence:**")
    for cite in citations:
        lines.append(f"- {cite}")
    lines.append("")

    # For cloakbrowser, append a trailing sandbox callout so the
    # citation lines (which themselves contain "cloakbrowser" in
    # paths) are within ±3 lines of a callout on BOTH sides
    # (the leading callout sits ≤3 lines before the first citation;
    # this trailing callout sits ≤3 lines after the last citation).
    if mcp == "cloakbrowser":
        lines.append(SANDBOX_CALLOUT)
        lines.append("")

    return "\n".join(lines)


def render_tier_section(
    tier_name: str,
    mcps: list[str],
    scores: dict[str, Any],
    sandbox_only: bool = False,
) -> str:
    """Render a single tier section: H2 heading + per-MCP entries.

    `tier_name` is the Python identifier (`PRIMARY` / `SECONDARY` /
    `SANDBOX_ONLY` / `SKIP`). The heading text uses
    `TIER_DISPLAY_NAMES[tier_name]` so the SANDBOX_ONLY identifier
    renders as `SANDBOX-ONLY` per WARNING 3.
    """
    display = TIER_DISPLAY_NAMES.get(tier_name, tier_name)

    # Heading + tier-level intro
    lines: list[str] = []
    lines.append(f"## {display}")
    lines.append("")

    # Tier-level descriptor
    descriptors = {
        "PRIMARY": (
            "Graduates to the Stage-2 terminal-craft default toolkit. The "
            "candidates a production agent reaches for first."
        ),
        "SECONDARY": (
            "Situational / fallback. Graduates with caveats — recommended "
            "for specific use-cases, not as the agent's first reach."
        ),
        "SANDBOX_ONLY": (
            "Sandbox-only graduation per SAFETY-04 + REPORT-08. The "
            "closed-binary + cookie-touch trust model is the binding "
            "constraint — useful for sandboxed scraping of public "
            "fixtures, NEVER for authenticated host pages."
        ),
        "SKIP": (
            "Does not graduate this wave. Documented reasons below; "
            "follow-up tickets noted in the Future Waves section."
        ),
    }
    lines.append(descriptors.get(tier_name, ""))
    lines.append("")

    # Per-MCP entries
    for mcp in mcps:
        lines.append(_render_mcp_entry(mcp, scores, tier_name))

    return "\n".join(lines)


def render_future_waves() -> str:
    """H2 'Future Waves' section anchored to G-710 + G-710 follow-ups."""
    return (
        "## Future Waves\n"
        "\n"
        f"This wave's harness ships [G-703]({G703_URL}); the explicit "
        "next-wave anchor is "
        f"[**G-710**]({G710_URL}) — bot-detection + TLS-fingerprint "
        "follow-up that REUSES this wave's harness (no re-build required).\n"
        "\n"
        "G-710's scope (the work that lives _outside_ this wave's "
        "Stage-2 unblock gate):\n"
        "\n"
        "- **TLS fingerprint capture per MCP** (JA3/JA4 via Scrapfly "
        "endpoint or local pcap) — verifies stealth claims that the "
        "snapshot-fixture S1-S8 walk cannot exercise.\n"
        "- **Bot-detection adversary set** — Cloudflare nowsecure.nl, "
        "reCAPTCHA demo, BrowserScan, FingerprintJS. Run each "
        "Chromium-class MCP with identical user-agent intent; compare "
        "pass-fail outcomes.\n"
        "- **Cross-machine reproducibility** — MacBook parity vs the Mac "
        "Mini that ran this wave (REPRO-07 punt).\n"
        "- **Obscura Linux A/B** — re-test obscura `--stealth` from a "
        "Linux host where `Sec-CH-UA-Platform-*` is honest, to validate "
        "the macOS leak finding (SAFETY-03 conditional).\n"
        "- **SANDBOX-ONLY tier's stealth claim** — the closed-binary "
        "stealth claim is DEFERRED here, validated in the G-710 "
        "adversary set.\n"
        "\n"
        "Per the PROJECT.md \"Core Value\" — this recommendations file "
        "IS the Stage-2 unblock gate. With it published, the private "
        "`terminal-craft` repo (Stage 2) can pull the PRIMARY tier into "
        "its default toolkit. G-710 picks up the cross-cutting "
        "validations that PROJECT.md's constraints intentionally "
        "deferred from this wave."
    )


def render_wave_close_compliance() -> str:
    """Footer noting SAFETY-05 audit numbers + Stage-2-leak gate."""
    return (
        "## Wave-Close Compliance (SAFETY-05 preview)\n"
        "\n"
        "Audit summary for this wave (full audit in Plan 04-06):\n"
        "\n"
        "- **Candidate count = 7** (unchanged from `.mcp.json`). 7 MCP "
        "candidates evaluated; browser-use produces two scored rows "
        "(direct + agent) per FAIRNESS-05 dual-mode contract — the row "
        "count is 8, the candidate count is 7.\n"
        "- **Rubric column count = 8** (unchanged from "
        "`scoring/rubric.md`). The 8-dimension weighted composite is "
        "the same axis Phase 1 calibration ran against; no rubric drift.\n"
        "- **No Stage-2 commits in this repo.** Stage 2 (the "
        "terminal-craft toolkit) lives in a private repo per PROJECT.md "
        "pipeline. `git log --grep=\"terminal-craft\"` returns empty in "
        "this repo, by design.\n"
        "- **`scoring/score.py` unchanged** (SACROSANCT per Phase 2 P07 "
        "audit). `git diff main -- scoring/score.py | wc -l` returns 0.\n"
        "- **No new MCPs added to `.mcp.json`** since the 2026-05-22 "
        "wave start.\n"
    )


# ─── Sandbox callout enforcement (idempotent) ────────────────────────────
#
# inject_sandbox_callouts is imported from bench._sandbox at the top of
# the module (WR-04). The shared implementation produces fewer callouts
# than the original per-line algorithm in this file — one callout per
# cloakbrowser cluster instead of one per mention — and is byte-identical
# to the one bench.build_report uses.


# ─── Top-level orchestrator ──────────────────────────────────────────────


def build_recommendations(scores_path: Path, out_path: Path) -> str:
    """Assemble the full recommendations.md from scores.json.

    Returns the rendered Markdown string; also writes it to `out_path`.
    """
    scores = aggregate_scores(scores_path)

    parts: list[str] = []

    # Title + executive summary
    parts.append("# Stage 2 Graduation Recommendations")
    parts.append("")
    parts.append(
        "> Evaluated as of 2026-05-27 with the locked 8-dimension rubric "
        "and the 7-MCP candidate list from `.mcp.json`. **Not intrinsic "
        "tool quality** — this is a snapshot of how each MCP performed on "
        "the S1-S8 fixture walk and the cross-cutting measurement suite "
        "(MEAS-01/02/07/08/09). Re-run any time the harness ships or the "
        "candidate list changes; the recommendation is a function of the "
        "rubric + fixtures, not the MCPs alone."
    )
    parts.append("")
    parts.append("## Executive Summary")
    parts.append("")
    parts.append(render_executive_summary())
    parts.append("")

    # 4 tier sections in locked order
    for tier_key in ("PRIMARY", "SECONDARY", "SANDBOX_ONLY", "SKIP"):
        parts.append(render_tier_section(
            tier_key,
            TIER_ASSIGNMENTS[tier_key],
            scores,
            sandbox_only=(tier_key == "SANDBOX_ONLY"),
        ))
        parts.append("")

    # Future Waves
    parts.append(render_future_waves())
    parts.append("")

    # Wave-close compliance footer
    parts.append(render_wave_close_compliance())
    parts.append("")

    # Linear traceability footer — mapping pulled from bench._linear so it
    # cannot drift from build_report.py (CR-01 fix).
    subtickets_inline = render_subtickets_inline()
    parts.append("## Linear Traceability")
    parts.append("")
    parts.append(
        f"- Umbrella: [G-703]({G703_URL}) — Phase 4 synthesis under "
        "this wave's break-before-cycle estimate=16 split.\n"
        f"- Per-MCP sub-tickets (canonical mapping per "
        f"[`{LINEAR_SUBTICKETS_DOC}`](../{LINEAR_SUBTICKETS_DOC})): "
        f"{subtickets_inline}.\n"
        f"- Future-wave anchor: [G-710]({G710_URL}) — bot-detection + "
        "TLS-fingerprint + cross-machine reproducibility follow-up. "
        "Reuses this wave's harness; ships in a follow-up wave."
    )
    parts.append("")

    md = "\n".join(parts)

    # Final pass: inject sandbox callouts where missing. Idempotent.
    md = inject_sandbox_callouts(md)

    # Write to disk. WR-05: parent must exist; match wave_close_check.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return md


# ─── CLI ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.build_recommendations",
        description=(
            "Build the Phase-4 Stage-2 graduation recommendations file "
            "(results/recommendations.md) from a scores.json. The four "
            "tier assignments are LOCKED per "
            ".planning/phases/04-synthesis/04-CONTEXT.md; this script "
            "renders them with citations, it does not re-litigate them."
        ),
    )
    parser.add_argument(
        "--scores",
        type=Path,
        required=True,
        help="Path to scores.json (e.g. results/2026-05-26/scores.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Path to write the recommendations.md (e.g. results/recommendations.md)",
    )
    args = parser.parse_args(argv)

    if not args.scores.is_file():
        print(
            f"build_recommendations: ERROR scores.json not found at {args.scores}",
            file=sys.stderr,
        )
        return 2

    md = build_recommendations(args.scores, args.out)
    print(
        f"build_recommendations: wrote {args.out} "
        f"({len(md.splitlines())} lines)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
