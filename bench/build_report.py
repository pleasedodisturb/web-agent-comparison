"""build_report — Phase 4 public scored-comparison report builder.

Reads `results/<date>/scores.json` + `cross_cut_data.json` +
`CAPABILITY_MATRIX.md` + per-MCP `DEEP_ANALYSIS.md` files (or
`SKIPPED.md` for SKIPPED rows) and assembles the public scored
comparison report at `results/<run-date>-mcp-comparison.md`.

Stdlib-only. The module is split into:

  - aggregate_*    : load JSON inputs
  - load_*         : load per-MCP narrative artifacts
  - render_*       : Markdown emission for each report section
  - inject_*       : final-pass transformations (sandbox callout)
  - build_report   : top-level orchestrator + CLI entry point

CLI:
    python3 -m bench.build_report \\
        --scores results/2026-05-26/scores.json \\
        --cross-cut results/2026-05-26/cross_cut_data.json \\
        --capability results/2026-05-26/CAPABILITY_MATRIX.md \\
        --deep-dir results/2026-05-26 \\
        --run-date 2026-05-27 \\
        --out results/2026-05-27-mcp-comparison.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from bench._linear import (
    G703_URL,
    G710_URL,
    LINEAR_SUBTICKETS_DOC,
    SUBTICKETS,
    render_subtickets_inline,
)
from bench._sandbox import (
    SANDBOX_CALLOUT as SANDBOX_CALLOUT_CANONICAL,
    SANDBOX_RECOGNITION_RE as SANDBOX_CALLOUT_REGEX,
    inject_sandbox_callouts,
)

# ─── Constants ──────────────────────────────────────────────────────────

RUBRIC_WEIGHTS = {
    "data_quality": 3,
    "reliability": 3,
    "speed": 2,
    "token_efficiency": 2,
    "interaction_depth": 2,
    "js_rendering": 1,
    "setup_complexity": 1,
    "error_handling": 1,
}

DIMENSION_ORDER = (
    "data_quality",
    "reliability",
    "speed",
    "token_efficiency",
    "interaction_depth",
    "js_rendering",
    "setup_complexity",
    "error_handling",
)

DIMENSION_LABELS = {
    "data_quality": "Data Quality",
    "reliability": "Reliability",
    "speed": "Speed",
    "token_efficiency": "Token Efficiency",
    "interaction_depth": "Interaction Depth",
    "js_rendering": "JS Rendering",
    "setup_complexity": "Setup Complexity",
    "error_handling": "Error Handling",
}

# Ranking order for tables — leads with the headline composite.
# Note: browser-use-direct + browser-use-agent both surface (dual-row contract);
# the per-MCP "browser-use" Deep Analysis stanza folds them.
SCORE_TABLE_ORDER = (
    "cloakbrowser",
    "playwright",
    "lightpanda",
    "browser-use-direct",
    "chrome-devtools",
    "firecrawl",
    "obscura",
    "browser-use-agent",
)

# The 7 candidate MCPs as the public matrix calls them out (browser-use rolled
# up into ONE name; browser-use-direct + browser-use-agent surface as two
# table rows but as ONE Deep Analysis stanza per FAIRNESS-05).
SEVEN_MCPS = (
    "playwright",
    "browser-use",
    "chrome-devtools",
    "lightpanda",
    "obscura",
    "firecrawl",
    "cloakbrowser",
)

STAGES = tuple(f"S{i}" for i in range(1, 9))

# SANDBOX_CALLOUT_CANONICAL + SANDBOX_CALLOUT_REGEX + inject_sandbox_callouts
# are re-exported from bench._sandbox (single source of truth — WR-04, IN-03).
# The aliases above preserve the original module's public surface so any
# external import of `bench.build_report.SANDBOX_CALLOUT_CANONICAL` still
# resolves; the underlying value now matches build_recommendations.py exactly.

# Hard-coded list of rows whose Phase-3 stability column was COMPLETED at the
# transport level while Phase-2 semantic-output FAILed — per Phase 3 P05
# limitation 2 (build_cross_cut_summary.py precedent: _stability_transport_caveat_finding).
TRANSPORT_ONLY_ROWS = ("obscura", "browser-use-direct")

# Stage cell semantics. The 6 expected strings:
#   PASS    — stage attempted and passed
#   FAIL    — stage attempted and failed
#   PARTIAL — partial/degraded outcome
#   N/A     — stage not applicable (read-only MCP × interactive stage)
#   UNTESTED — stage exists in schema but no measurement was taken
#   SKIPPED — entire row SKIPPED (e.g. LLM_KEY_ABSENT)
STAGE_CELLS = ("PASS", "FAIL", "PARTIAL", "N/A", "UNTESTED", "SKIPPED")


# ─── Helpers ────────────────────────────────────────────────────────────


def _safe_load_json(path: Path) -> dict | None:
    """Read a JSON file; return None on missing or parse error."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _fmt_cell(value: Any) -> str:
    """Format a single cell value for a Markdown table; handle None / 'N/A'."""
    if value is None:
        return "—"
    if value == "N/A":
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _md_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _composite_for_row(row: dict, weights: dict[str, int]) -> float | None:
    """Compute weighted composite for a row, dropping 'N/A' cells from denom.

    Returns None if the row is SKIPPED or all cells are 'N/A'.
    """
    if row.get("status") == "SKIPPED":
        return None
    scores = row.get("scores", {}) or {}
    num = 0.0
    den = 0
    for k, w in weights.items():
        v = scores.get(k)
        if v is None or v == "N/A":
            continue
        try:
            num += float(v) * w
            den += w
        except (TypeError, ValueError):
            continue
    if den == 0:
        return None
    return num / den


# ─── Aggregators ────────────────────────────────────────────────────────


def aggregate_scores(scores_path: Path) -> dict:
    """Load scores.json. Returns dict keyed by MCP name."""
    data = _safe_load_json(scores_path)
    if data is None:
        return {}
    return data


def aggregate_cross_cut(cross_cut_path: Path) -> dict:
    """Load cross_cut_data.json. Returns dict keyed by MCP name (lifted)."""
    data = _safe_load_json(cross_cut_path)
    if data is None:
        return {"mcps": []}
    # Lift the list-of-MCPs into a name->row dict for convenience
    mcps = data.get("mcps", []) or []
    by_name = {row.get("mcp"): row for row in mcps if isinstance(row, dict)}
    return {"raw": data, "mcps": mcps, "by_name": by_name}


# ─── Per-MCP narrative loaders ──────────────────────────────────────────


def load_deep_analysis(deep_dir: Path, mcp: str) -> str | None:
    """Load `<deep_dir>/<mcp>/DEEP_ANALYSIS.md`.

    Returns the file contents (string) or None if missing. playwright is
    expected to return None and is handled explicitly by render_deep_analysis.
    """
    path = deep_dir / mcp / "DEEP_ANALYSIS.md"
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def load_skipped_narrative(deep_dir: Path, mcp: str) -> str | None:
    """Load `<deep_dir>/<mcp>/SKIPPED.md` for rows like browser-use-agent."""
    path = deep_dir / mcp / "SKIPPED.md"
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


# ─── Demote helpers (lift H2/H3 down so they nest under report H1) ──────


def _demote_headings(md: str, levels: int = 1) -> str:
    """Demote every Markdown heading by `levels` (clamped at H6)."""
    out_lines: list[str] = []
    for line in md.splitlines():
        m = re.match(r"^(#{1,6})(\s)", line)
        if m:
            hashes = m.group(1)
            new_count = min(len(hashes) + levels, 6)
            line = "#" * new_count + line[len(hashes):]
        out_lines.append(line)
    return "\n".join(out_lines)


# ─── Sandbox callout injection (idempotent) ─────────────────────────────
#
# inject_sandbox_callouts is imported from bench._sandbox above (WR-04).
# Re-exported via the import statement so existing callers continue to
# work; the underlying implementation is now shared with
# bench.build_recommendations.


# ─── Render: Executive summary ──────────────────────────────────────────


def render_executive_summary(scores: dict, partial_run_flag: bool = False) -> str:
    """REPORT — headline verdict + Stage 2 tier preview + partial-run disclosure.

    If `partial_run_flag=True`, name the actual SKIPPED MCP(s) — in this wave,
    that's `browser-use-agent` (NOT firecrawl, which scored 4.23).
    """
    skipped = [
        name for name, row in scores.items()
        if row.get("status") == "SKIPPED"
    ]
    parts: list[str] = []
    parts.append("## Executive Summary")
    parts.append("")
    parts.append(
        "Seven browser-automation MCP servers measured against an identical "
        "8-stage job-application pipeline (Greenhouse SSR + Ashby React SPA, "
        "loopback snapshot fixtures). Same 8-dimension weighted rubric for all "
        "seven; N/A-aware composite drops categorically-inapplicable cells from "
        "the weighted denominator so read-only and cloud-only MCPs are compared "
        "honestly on the dimensions they can attempt."
    )
    parts.append("")
    parts.append("**Headline ranking (N/A-aware composite, 0-10):**")
    parts.append("")
    # Compute & render a short verdict bullet list
    ranked: list[tuple[str, float | None, dict]] = []
    for name in SCORE_TABLE_ORDER:
        if name not in scores:
            continue
        row = scores[name]
        comp = _composite_for_row(row, RUBRIC_WEIGHTS)
        ranked.append((name, comp, row))
    # Sort by composite descending; SKIPPED rows (None) sink to the bottom
    ranked.sort(
        key=lambda t: (t[1] is None, -(t[1] if t[1] is not None else 0.0))
    )
    for name, comp, row in ranked:
        annotations = []
        if row.get("sandbox_only"):
            annotations.append("SANDBOX-ONLY")
        if row.get("status") == "SKIPPED":
            annotations.append(f"SKIPPED ({row.get('skip_reason', 'no-reason')})")
        ann = f" — {' / '.join(annotations)}" if annotations else ""
        comp_str = "SKIPPED" if comp is None else f"{comp:.2f}"
        parts.append(f"- `{name}` — **{comp_str}**{ann}")
    parts.append("")
    parts.append("**Stage 2 graduation tier preview** (see `recommendations.md` for full rationale):")
    parts.append("")
    parts.append("- **PRIMARY** (default toolkit): `playwright`, `lightpanda`")
    parts.append("- **SECONDARY** (situational / fallback): `browser-use-direct`, `chrome-devtools`, `firecrawl`")
    parts.append("- **SANDBOX-ONLY**: `cloakbrowser` (closed-binary trust model is the binding constraint, not the score)")
    parts.append("- **SKIP** (do not graduate this wave): `obscura`, `browser-use-agent`")
    parts.append("")
    if partial_run_flag and skipped:
        # WARNING 1 fix: the disclosure MUST name the actual SKIPPED row(s).
        # browser-use-agent is the canonical case in this wave.
        named = ", ".join(skipped)
        parts.append(
            f"**Partial-run disclosure (REPORT-09):** {named} SKIPPED — "
            f"the report does NOT silently emit an N/M score in the composite. "
            f"For `browser-use-agent` the skip reason is `LLM_KEY_ABSENT`; the "
            f"re-run procedure is documented in "
            f"`results/2026-05-26/browser-use-agent/SKIPPED.md`. See "
            f"§ Negative Results for full disclosure of all partial / "
            f"environment-conditioned outcomes."
        )
        parts.append("")
    return "\n".join(parts)


# ─── Render: Methodology disclaimer (REPORT-05) ─────────────────────────


def render_methodology_disclaimer(run_date: Any) -> str:
    """REPORT-05 — snapshot-framing disclaimer that the report measures
    "configuration on date X" not intrinsic tool quality.

    Raises ValueError if `run_date` is None, empty, or otherwise yields an
    empty date string. The CLI's `--run-date` argument is required so
    this only fires for programmatic callers that omit the date (WR-07);
    failing loudly is preferable to rendering "evaluated on ****" in the
    artifact.
    """
    if isinstance(run_date, dict):
        date_str = run_date.get("run_date") or run_date.get("date") or ""
    else:
        date_str = str(run_date or "")
    date_str = date_str.strip()
    if not date_str:
        raise ValueError(
            "render_methodology_disclaimer requires a non-empty run_date "
            "(got None / empty); refusing to emit a malformed disclaimer "
            "header with no date."
        )
    return (
        f"## Methodology disclaimer\n"
        f"\n"
        f"This report scores 7 browser-automation MCP servers as evaluated on "
        f"**{date_str}** against a frozen 8-stage job-application pipeline. Every "
        f"number is a snapshot of how each MCP performed in that configuration on "
        f"that date — **not intrinsic tool quality**, not a statement about which "
        f"MCP is \"best\" in the abstract. Vendor patch "
        f"cadence is high (Playwright MCP 0.0.74 → 0.0.75 in 24 hours during the run "
        f"window; chrome-devtools-mcp went 0.26.0 → 1.0.0 → 1.0.1 in 4 days), so the "
        f"score-card has a half-life measured in weeks, not years. Treat it as a "
        f"baseline for the methodology, re-run when the rubric or candidate set "
        f"changes meaningfully."
        f"\n"
    )


# ─── Render: Methodology body section (REPORT-04) ───────────────────────


def render_methodology_section(ctx: dict | None = None) -> str:
    """REPORT-04 — substantive Methodology section body.

    Distinct from `render_methodology_disclaimer`. Emits a "## Methodology"
    heading followed by rubric / fixtures / harness / measurement-approach /
    reproducibility model — cites `results/2026-05-27/MACHINE.md`.
    """
    return (
        "## Methodology\n"
        "\n"
        "### Scoring rubric\n"
        "Eight weighted dimensions (total weight = 15): Data Quality (3×), "
        "Reliability (3×), Speed (2×), Token Efficiency (2×), Interaction Depth "
        "(2×), JS Rendering (1×), Setup Complexity (1×), Error Handling (1×). "
        "Composite is N/A-aware: cells marked `N/A` (categorically inapplicable, "
        "e.g. read-only MCP × interactive stage) drop from the weighted "
        "denominator rather than score 0. The locked rubric lives at "
        "[`scoring/rubric.md`](../scoring/rubric.md) and was NOT modified during "
        "the run.\n"
        "\n"
        "### Test fixtures (S1-S8 pipeline)\n"
        "Eight stages mapped to a job-application flow: S1 Greenhouse JD extract, "
        "S2 Ashby SPA extract, S3 platform detection, S4 apply-form snapshot, "
        "S5 fill form, S6 upload resume, S7 React-Select dropdown, S8 screenshot. "
        "All fixtures are loopback snapshots (REPRO-04 model) served from "
        "`http://127.0.0.1:8765` — frozen byte-for-byte from the 2026-05-22 "
        "Greenhouse + Ashby live pages so the scores are reproducible by any "
        "third party with the public repo. **No live URLs are used in the scoring "
        "harness.** Per-fixture provenance is captured in "
        "`fixtures/snapshots/*/PROVENANCE.md`.\n"
        "\n"
        "### Harness lineage\n"
        "Phase 1 calibration (`results/2026-05-25/PHASE1_CALIBRATION.md`) anchors "
        "the scoring engine against the 2026-03-31 Playwright baseline (9.07 published "
        "composite → 7.93 observed under loopback fixtures, within the ±0.5 accept band). "
        "Phase 2 measured each MCP individually (`results/2026-05-26/<mcp>/DEEP_ANALYSIS.md`); "
        "Phase 3 added cross-cutting measurements (cold-start, tokens, stability, "
        "tool-call counts, tools inventory — see `results/2026-05-26/CROSS_CUT_SUMMARY.md`). "
        "Phase 4 (this report) synthesises the three.\n"
        "\n"
        "### Measurement approach\n"
        "- **Cold-start (MEAS-01):** three-segment timing — `t_resolve` (binary/script "
        "located on PATH) + `t_spawn` (process launches) + `t_first_useful` "
        "(`tools/list` handshake completes). 5 cold + 5 warm runs per MCP, median "
        "reported. Per HARNESS-03, cache eviction is process-only (`pkill` + "
        "respawn); OS-file-cache eviction is deferred to G-710.\n"
        "- **Token accounting (MEAS-02):** three scopes — schema tokens "
        "(Anthropic `count_tokens` on the tools/list response, SKIPPED this wave "
        "because rbw is locked), payload bytes (JSON-RPC stream byte-count), and "
        "turn tokens (Claude billing units). Per HARNESS-04, do NOT conflate.\n"
        "- **Stability (MEAS-07):** 60-min S1+S5 loop against the loopback "
        "fixture server. Transport-PASS only — a tool call counts as PASS iff "
        "`call_tool` returned without raising. Stability does **not** verify "
        "semantic output correctness; Phase 2's semantic-output FAILs on "
        "`obscura` and `browser-use-direct` stand independently of their "
        "stability column (Phase 3 P05 limitation 2).\n"
        "- **Tool-call counts (MEAS-08) + tools inventory (MEAS-09):** "
        "per-stage median across PASS{1,2,3}; structural inventory probe via "
        "`mcp.client.stdio` handshake.\n"
        "\n"
        "### Reproducibility model\n"
        "Loopback snapshot fixtures (REPRO-04) — no live URL dependency, no API "
        "credentials required by the harness itself (`firecrawl` is the one cloud "
        "MCP; its `FIRECRAWL_API_KEY` is needed only to spawn its MCP server, not "
        "to reach the loopback fixtures, which Firecrawl's URL validator rejects "
        "by design — see § Negative Results). The full reproducibility recipe "
        "(install matrix, env vars, Make targets, expected output) lives in "
        "[`docs/REPRODUCIBILITY.md`](../docs/REPRODUCIBILITY.md).\n"
        "\n"
        "### Run-environment specifics\n"
        "Machine, NTP-disciplined timestamps, OS, kernel, Node / Python / uv versions, "
        "and per-MCP binary SHA256s are pinned in "
        "[`results/2026-05-27/MACHINE.md`](2026-05-27/MACHINE.md) and "
        "`results/2026-05-27/versions.lock.md`. The repo is a public artifact; the "
        "MACHINE.md file deliberately omits hostname / username / MAC addresses / "
        "hardware UUIDs per the project's public-repo PII hygiene rule.\n"
    )


# ─── Render: 8-dim weighted score table (REPORT-01) ─────────────────────


def render_score_table(scores: dict, rubric_weights: dict[str, int]) -> str:
    """REPORT-01: 7 MCPs × 8 dims + composite. SKIPPED rows show "SKIPPED",
    NOT "0.0". Cloakbrowser carries SANDBOX-ONLY annotation. Obscura and
    browser-use-direct stability rows are annotated transport-only.
    """
    headers = ["MCP", "Capability"] + [DIMENSION_LABELS[d] for d in DIMENSION_ORDER] + ["Composite", "Notes"]
    lines: list[str] = [_md_row(headers), _md_row(["---"] * len(headers))]
    for name in SCORE_TABLE_ORDER:
        if name not in scores:
            continue
        row = scores[name]
        cells = [f"`{name}`", row.get("capability", "—")]
        is_skipped = row.get("status") == "SKIPPED"
        for d in DIMENSION_ORDER:
            v = row.get("scores", {}).get(d)
            if is_skipped:
                cells.append("—")
                continue
            cells.append(_fmt_cell(v))
        # Composite
        if is_skipped:
            cells.append("**SKIPPED**")
        else:
            comp = _composite_for_row(row, rubric_weights)
            cells.append(f"**{comp:.2f}**" if comp is not None else "—")
        # Notes (annotations)
        notes_bits: list[str] = []
        if row.get("sandbox_only"):
            notes_bits.append("SANDBOX-ONLY")
        if is_skipped:
            notes_bits.append(f"SKIPPED ({row.get('skip_reason', 'no-reason')})")
        if name in TRANSPORT_ONLY_ROWS:
            notes_bits.append("stability: COMPLETED ⚠ transport-only (Phase 2 semantic-output FAIL stands)")
        cells.append("; ".join(notes_bits) if notes_bits else "—")
        lines.append(_md_row(cells))
    return "\n".join(lines)


# ─── Render: stage matrix (REPORT-02) ───────────────────────────────────


def render_stage_matrix(scores: dict) -> str:
    """REPORT-02: S1-S8 × N MCPs. Cells distinct across PASS / FAIL / PARTIAL /
    N/A / UNTESTED / SKIPPED.
    """
    headers = ["MCP"] + list(STAGES) + ["Row status"]
    lines: list[str] = [_md_row(headers), _md_row(["---"] * len(headers))]
    for name in SCORE_TABLE_ORDER:
        if name not in scores:
            continue
        row = scores[name]
        stages_map = row.get("stages", {}) or {}
        is_skipped = row.get("status") == "SKIPPED"
        cells = [f"`{name}`"]
        for st in STAGES:
            v = stages_map.get(st)
            if is_skipped:
                # Distinguish row-level SKIPPED from cell-level N/A
                cells.append("SKIPPED")
            elif v is None:
                cells.append("UNTESTED")
            else:
                # PASS / FAIL / PARTIAL / N/A flow through
                cells.append(str(v))
        cells.append("SKIPPED" if is_skipped else "SCORED")
        lines.append(_md_row(cells))
    # Make sure UNTESTED is at least mentioned in the legend so the public reader
    # sees it even if no row currently maps to it.
    legend = (
        "\n\n"
        "**Cell legend:** `PASS` = stage attempted and met success criteria; "
        "`FAIL` = stage attempted but criteria unmet; `PARTIAL` = partial / degraded; "
        "`N/A` = categorically inapplicable (e.g. read-only MCP × interactive stage); "
        "`UNTESTED` = stage exists in schema but no measurement taken; "
        "`SKIPPED` = entire row skipped at the harness level (see row-status column)."
    )
    return "\n".join(lines) + legend


# ─── Render: capability view (FAIRNESS-04) ──────────────────────────────


def render_capability_view(capability_path: Path) -> str:
    """Embed `CAPABILITY_MATRIX.md` verbatim (provenance preservation).

    The caller is expected to run `inject_sandbox_callouts` on the full document
    as a final pass — the embedded content already carries the callout, and the
    regex-based recogniser ensures no double-injection.
    """
    if not capability_path.is_file():
        return "## Capability View\n\n_CAPABILITY_MATRIX.md not found._\n"
    try:
        body = capability_path.read_text(encoding="utf-8")
    except OSError:
        return "## Capability View\n\n_CAPABILITY_MATRIX.md read failed._\n"
    demoted = _demote_headings(body, levels=1)
    return (
        "## Capability View — second-view matrix (FAIRNESS-04)\n"
        "\n"
        "Per FAIRNESS-04, this second view groups MCPs by architectural category "
        "so readers cannot accidentally compare a cloud service to a local browser "
        "on a single composite number. The content below is lifted verbatim from "
        "`results/2026-05-26/CAPABILITY_MATRIX.md` (Phase 2 P07 artifact).\n"
        "\n"
        f"{demoted}\n"
    )


# ─── Render: per-MCP Deep Analysis (REPORT-03) ──────────────────────────


def _playwright_stanza(scores: dict) -> str:
    """Playwright lacks per-MCP DEEP_ANALYSIS.md — lift calibration narrative
    + emit explicit asymmetry note per Phase 2 P07 limitation 3.
    """
    row = scores.get("playwright", {})
    comp = _composite_for_row(row, RUBRIC_WEIGHTS)
    comp_str = f"{comp:.2f}" if comp is not None else "—"
    return (
        "## playwright\n"
        "\n"
        "**Capability:** tool-only · **Mode:** default · "
        f"**Median composite (N/A-aware):** **{comp_str} / 10**\n"
        "\n"
        "### Asymmetry note\n"
        "Playwright lacks a per-MCP `DEEP_ANALYSIS.md` at "
        "`results/2026-05-26/playwright/` — this is a documented Phase 1 "
        "calibration baseline asymmetry (Phase 2 P07 limitation 3). The row is "
        "still scored against the same 8-dimension rubric as every other "
        "candidate; the interpretive narrative below lifts from the calibration "
        "PASS in `results/2026-05-25/PHASE1_CALIBRATION.md` and the prior-wave "
        "context in `results/2026-03-31_run.md`. Phase 4 should either generate "
        "an in-tree DEEP_ANALYSIS.md from the calibration evidence in a future "
        "wave, or accept the asymmetry; this report does the latter and flags it.\n"
        "\n"
        "### Calibration baseline\n"
        "Phase 1 calibration (`scripts/verify_calibration.sh`) PASSed at 7.93 — "
        "within the [7.83, 8.83] accept band (±0.5 of the harness re-baseline "
        "8.33; published 2026-03 composite was 9.07 on live URLs). The composite "
        "delta is fixture-sourcing, not regression: loopback snapshots are "
        "harsher than live URLs on JS-rendering dimensions because the React "
        "bundle's `fetch` calls fail against the snapshot's missing backend, "
        "and the SPA's not-found route replaces the form DOM. Playwright's "
        "tool surface (~30 tools, `browser_fill_form` batch-fill, "
        "`browser_take_screenshot` full-page) was sufficient to PASS all 8 "
        "stages under the loopback contract.\n"
        "\n"
        "### Strengths\n"
        "- Full S1-S8 PASS — the only candidate to achieve this without sandbox "
        "constraints (cloakbrowser is sandbox-only).\n"
        "- Richest tool surface in the matrix (~30 tools including "
        "`browser_fill_form`, `browser_take_screenshot`, multi-tab management).\n"
        "- Vendor-backed (Microsoft); patch cadence is fast (0.0.74 → 0.0.75 in 24 hours).\n"
        "- Calibration baseline — the methodology's wave-to-wave anchor.\n"
        "\n"
        "### Weaknesses\n"
        "- Highest steady-state RSS in the matrix (~160 MB max during stability) — "
        "trade-off for full Chromium under the hood.\n"
        "- Cross-cut date gap (Phase 3 P05): PASS{1,2,3} dirs live at "
        "2026-05-25 (the calibration date), not 2026-05-26; per-stage tool-call "
        "counts are NO_EVIDENCE for this wave — see § Negative Results.\n"
        "- No DEEP_ANALYSIS.md (asymmetry above).\n"
        "\n"
        "### Verdict\n"
        "Calibration baseline confirmed; PRIMARY-tier graduation to the Stage 2 "
        "toolkit. The default interactive MCP unless a specific reason "
        "(stealth, cloud markdown, JS-light speed) suggests an alternative.\n"
    )


def _browser_use_stanza(deep_dir: Path) -> str:
    """browser-use SPECIAL CASE per FAIRNESS-05: ONE stanza with TWO subsections."""
    direct_body = load_deep_analysis(deep_dir, "browser-use-direct")
    skipped_body = load_skipped_narrative(deep_dir, "browser-use-agent")
    parts: list[str] = []
    parts.append("## browser-use")
    parts.append("")
    parts.append(
        "Dual-mode MCP per FAIRNESS-05. Direct mode is scored (5.87 composite); "
        "Agent mode is SKIPPED this wave because the autonomous executor's env "
        "had no `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` with non-empty value. "
        "Both rows surface in the score table to preserve the dual-mode visibility."
    )
    parts.append("")
    parts.append("### Direct mode")
    parts.append("")
    if direct_body:
        parts.append(_demote_headings(direct_body, levels=2))
    else:
        parts.append("_Direct-mode DEEP_ANALYSIS.md not found at "
                     "`results/2026-05-26/browser-use-direct/DEEP_ANALYSIS.md`._")
    parts.append("")
    parts.append("### Agent mode (SKIPPED)")
    parts.append("")
    parts.append(
        "**Status:** SKIPPED (reason: `LLM_KEY_ABSENT`). The harness can spawn "
        "the browser-use `--mcp` server in agent mode (the initialize handshake "
        "does not consume LLM keys) but cannot exercise the agent-driven planning "
        "path without an OpenAI or Anthropic key. Below is the SKIPPED narrative "
        "lifted verbatim from `results/2026-05-26/browser-use-agent/SKIPPED.md`."
    )
    parts.append("")
    if skipped_body:
        parts.append(_demote_headings(skipped_body, levels=2))
    else:
        parts.append("_SKIPPED.md not found at "
                     "`results/2026-05-26/browser-use-agent/SKIPPED.md`._")
    parts.append("")
    return "\n".join(parts)


def render_deep_analysis(scores: dict, deep_dir: Path, mcp: str) -> str:
    """REPORT-03 — per-MCP Deep Analysis stanza.

    Handles four cases:
      (a) browser-use: ONE combined stanza with Direct mode + Agent mode subsections
      (b) playwright: synthetic stanza + asymmetry note (no DEEP_ANALYSIS.md exists)
      (c) cloakbrowser / chrome-devtools / lightpanda / obscura / firecrawl:
          lift `DEEP_ANALYSIS.md` verbatim with H2 → H3 demotion
      (d) anything else: best-effort fallback
    """
    if mcp == "browser-use":
        return _browser_use_stanza(deep_dir)
    if mcp == "playwright":
        return _playwright_stanza(scores)
    body = load_deep_analysis(deep_dir, mcp)
    if body is None:
        return f"## {mcp}\n\n_DEEP_ANALYSIS.md not found at `{deep_dir}/{mcp}/DEEP_ANALYSIS.md`._\n"
    return _demote_headings(body, levels=1)


# ─── Render: 2026-03 → 2026-05 overlay (REPORT-11) ──────────────────────


def render_overlay_2026_03_2026_05(scores: dict) -> str:
    """Minimum viable overlay — single Playwright row showing 9.07 → 7.93,
    annotated with fixture-sourcing explanation.
    """
    pw = scores.get("playwright", {})
    current = _composite_for_row(pw, RUBRIC_WEIGHTS)
    current_str = f"{current:.2f}" if current is not None else "7.93"
    return (
        "## 2026-03 → 2026-05 overlay (REPORT-11)\n"
        "\n"
        "Only Playwright participated in both the 2026-03-31 wave (live URLs) "
        "and the 2026-05-26 wave (loopback snapshots). The score is comparable in "
        "shape — same 8-dimension rubric, same 8-stage pipeline — but the "
        "fixture-sourcing difference is the entire reason for the delta.\n"
        "\n"
        "| Wave | Composite | Fixture sourcing | Notes |\n"
        "|---|---|---|---|\n"
        f"| 2026-03-31 | **9.07** | Live URLs (`job-boards.greenhouse.io`, `jobs.ashbyhq.com`) | Original published score; methodology's wave-to-wave anchor (per `scoring/rubric_notes.md`). |\n"
        f"| 2026-05-26 | **{current_str}** | Loopback snapshots (`http://127.0.0.1:8765/...`) | Same rubric. Loopback fixture's missing backend causes the React bundle to clobber the SSR form with a not-found shell — Playwright's tool surface still PASSes via timing + structured extract, but JS-rendering scores reflect the hostile fixture environment. |\n"
        "\n"
        "**Delta interpretation:** the 1.14-point drop is fixture-sourcing, not "
        "Playwright regression. Phase 1 calibration validated this via the "
        "[7.83, 8.83] accept band (±0.5 of the harness re-baseline 8.33 — see "
        "[`results/2026-05-25/PHASE1_CALIBRATION.md`](2026-05-25/PHASE1_CALIBRATION.md)). "
        "Out of scope for this overlay: re-mapping app-level WebFetch / Agent Browser CLI / BrowserMCP / "
        "Lightpanda CLI rows from the 2026-03 wave into this matrix — those candidates were tested "
        "differently (CLI tool, not MCP server) and apples-to-apples carry-over would require a fresh run.\n"
    )


# ─── Render: Negative Results (REPORT-10) ───────────────────────────────


def render_negative_results(scores: dict, cross_cut: dict) -> str:
    """REPORT-10 — explicit negative findings."""
    parts: list[str] = []
    parts.append("## Negative Results")
    parts.append("")
    parts.append(
        "The findings below are publishable failures — limitations the rubric "
        "surfaced cleanly, useful precisely because they demonstrate what the "
        "harness can and cannot measure."
    )
    parts.append("")
    parts.append(
        "1. **`firecrawl` loopback-incompatibility (env-mismatch by design).** "
        "Firecrawl's cloud-API URL validator refuses `http://127.0.0.1:8765/...` "
        "before any scrape attempt, returning HTTP 400 BAD_REQUEST with "
        "`\"URL must have a valid top-level domain or be a valid path\"`. This is "
        "not a Firecrawl bug — the cloud validator is correctly preventing SSRF — "
        "but it makes Firecrawl architecturally incompatible with the loopback "
        "fixture contract (REPRO-04). Tagged `env-mismatch` per FAIRNESS-06 on "
        "`data_quality` + `js_rendering`. Single-shot live-URL probes confirm "
        "Firecrawl is genuinely strong on SSR targets (24,237-byte Anthropic JD "
        "vs Playwright's 2,663-byte YAML) and weak on React SPAs (203 bytes of "
        "Ashby footer chrome only). See "
        "`results/2026-05-26/firecrawl/DEEP_ANALYSIS.md` for the full probe data."
    )
    parts.append("")
    parts.append(
        "2. **`obscura` macOS-only stealth leak (SAFETY-03).** Obscura's "
        "`--stealth` flag (and per-call `stealth` parameter) was DISABLED on "
        "macOS for this benchmark: enabling stealth on macOS leaks "
        "`Sec-CH-UA-Platform-*` client hints from the network stack regardless of "
        "any JS-level User-Agent shim — Cloudflare cross-checks this signal "
        "(per [`docs/external-findings/browser-tools-2026-05-21.md`]"
        "(../docs/external-findings/browser-tools-2026-05-21.md) § SAFETY-03). "
        "Running Obscura on Linux (where Sec-CH-UA-Platform-* is honest) is the "
        "right comparison; deferred to G-710. Phase 4 must NOT promote Obscura "
        "to SECONDARY-tier on the basis of \"stealth-specialist\" without that "
        "Linux A/B."
    )
    parts.append("")
    parts.append(
        "3. **`browser-use-agent` SKIPPED — `LLM_KEY_ABSENT`.** The autonomous "
        "executor's env had `OPENAI_API_KEY=<empty>` and `ANTHROPIC_API_KEY=<unset>` "
        "(intentional zero-length sentinels), so the agent-mode code path "
        "(`retry_with_browser_use_agent`) could not be exercised. The initialize "
        "handshake works (tool_count=16 in both modes), confirming the 2026-05-21 "
        "testbench's `initialize` timeout regression is fixed in v0.12.7. Full "
        "re-run procedure in `results/2026-05-26/browser-use-agent/SKIPPED.md`. "
        "SKIPPED is not the same as scored-0: the row contributes no composite to "
        "the matrix, only a documented gap."
    )
    parts.append("")
    parts.append(
        "4. **`chrome-devtools` 7 DevTools-exclusive tools structurally inventoried "
        "but not exercised.** chrome-devtools-mcp exposes 10 diagnostic + 10 "
        "interaction tools (29-tool total surface, richest in matrix). The "
        "DevTools-only primitives — `list_console_messages`, `list_network_requests`, "
        "`performance_start_trace`, `emulate_cpu`, `emulate_network` — are "
        "structurally present (tools_inventory.json confirms) but the natural S1-S8 "
        "walk doesn't ask for network waterfalls or trace recordings, so the "
        "agent never reached for them. Zero invocations across all 3 passes. "
        "This is a CLEAN negative result: the DevTools surface exists and is "
        "ready to use, but is NOT what made or unmade chrome-devtools' 5.60 row. "
        "A future \"9th DevTools-Probe stage\" (deferred per CONTEXT.md) would "
        "convert structural inventory into scored differentiation."
    )
    parts.append("")
    parts.append(
        "5. **`playwright` cross-cut date gap.** Playwright's PASS{1,2,3} "
        "directories exist at `results/2026-05-25/playwright/` (the Phase 1 "
        "calibration run) but NOT at `results/2026-05-26/playwright/`. Phase 3 "
        "tokens.json and tool_call_counts.json are therefore NO_EVIDENCE for "
        "playwright in this wave (cold-start, stability, and tools_inventory ARE "
        "valid — they don't depend on PASS dirs). Do NOT cite the Playwright "
        "`browser_fill_form` batch-fill claim (\"N fields per call\") as "
        "CONFIRMED until a re-run produces PASS dirs at the current date. "
        "Deferred to G-710; the rest of the matrix uses 2026-05-26 PASS dirs."
    )
    parts.append("")
    return "\n".join(parts)


# ─── Render: carried-forward limitations ────────────────────────────────


def render_carried_forward_limitations() -> str:
    return (
        "## Carried-forward limitations (Phase 2 P07 + Phase 3 P05)\n"
        "\n"
        "Three known limitations are surfaced explicitly here so external readers "
        "see them rather than discover them in evidence:\n"
        "\n"
        "1. **SKIPPED composite=0.0 sentinel** — `score_with_na.py` returns "
        "composite=0.0 when a row has all-N/A scores (denominator=0 fallback). "
        "The score table in this report consults the row's `status` field and "
        "renders `SKIPPED` rather than `0.0` for those rows (`browser-use-agent` "
        "is the canonical case). `score_with_na.py` is adjacent to the "
        "sacrosanct `scoring/score.py` and was NOT modified this wave; the "
        "rendering layer is the right fix until G-710's scoring-engine PR.\n"
        "\n"
        "2. **Transport vs semantic stability (Phase 3 P05).** Phase 3's "
        "stability harness counts a tool call as PASS iff `call_tool` returned "
        "without raising — it does NOT verify the response body. Phase 2's "
        "semantic-output FAILs on `obscura` (SSRF-guard tool-bug cascade) and "
        "`browser-use-direct` (S5 React-clobber) stand independently of their "
        "Phase 3 COMPLETED stability. Their stability cells in this report "
        "carry the `COMPLETED ⚠ transport-only (Phase 2 semantic-output FAIL stands)` "
        "annotation.\n"
        "\n"
        "3. **playwright DEEP_ANALYSIS.md asymmetry** — playwright was scored "
        "during Phase 1 calibration before the Phase 2 DEEP_ANALYSIS.md format "
        "crystallised; the in-tree interpretive document for playwright does "
        "not exist. The Playwright stanza in this report synthesises from "
        "`PHASE1_CALIBRATION.md` + `2026-03-31_run.md` + an explicit asymmetry "
        "note. Phase 4 either generates a real DEEP_ANALYSIS.md in a future "
        "wave or accepts the asymmetry; this report does the latter and flags it.\n"
    )


# ─── Render: Linear traceability footer (REPORT-12) ─────────────────────


def render_linear_traceability_footer() -> str:
    subtickets_inline = render_subtickets_inline()
    return (
        "## Linear traceability\n"
        "\n"
        "This report closes Phase 4 Wave 2 of the G-703 umbrella ticket. "
        "Per-MCP sub-tickets G-714..G-720 carry the per-row evidence comments; "
        "G-710 is the deferred-follow-up anchor for the bot-detection + "
        "TLS-fingerprint adversary set (Cloudflare nowsecure.nl, reCAPTCHA "
        "demo, BrowserScan, FingerprintJS) and the Linux A/B for Obscura.\n"
        "\n"
        f"- **[G-703]({G703_URL})** — umbrella "
        "ticket (estimate=16, broken into 7 per-MCP sub-tickets + 1 synthesis ticket).\n"
        f"- **[G-710]({G710_URL})** — deferred "
        "follow-up: bot-detection adversary set, TLS-fingerprint capture, MacBook "
        "cross-machine parity, OS-file-cache cold-start, scoring-engine SKIPPED "
        "composite fix, Obscura Linux A/B.\n"
        f"- Per-MCP sub-tickets (canonical mapping per [`{LINEAR_SUBTICKETS_DOC}`]"
        f"(../{LINEAR_SUBTICKETS_DOC})): {subtickets_inline}. Evidence comments "
        "lifted verbatim from each row's `DEEP_ANALYSIS.md`.\n"
        "\n"
        "_Note: some embedded Phase 2 `DEEP_ANALYSIS.md` content was authored "
        "before the canonical sub-ticket mapping was filed and may cite stale "
        f"ticket IDs inline; the authoritative mapping is [`{LINEAR_SUBTICKETS_DOC}`]"
        f"(../{LINEAR_SUBTICKETS_DOC}) — this footer above._\n"
    )


# ─── Build orchestrator ─────────────────────────────────────────────────


def build_report(
    scores_path: Path,
    cross_cut_path: Path,
    capability_path: Path,
    deep_dir: Path,
    run_date: str,
    out_path: Path | None,
) -> str:
    """Top-level: read inputs, assemble report, write to `out_path` if given.

    Returns the rendered Markdown string regardless of out_path.
    """
    scores = aggregate_scores(scores_path)
    cross_cut = aggregate_cross_cut(cross_cut_path)
    partial_run_flag = any(
        row.get("status") == "SKIPPED" for row in scores.values()
    )
    parts: list[str] = []
    parts.append(f"# Web-Agent MCP Comparison — {run_date}")
    parts.append("")
    parts.append(
        "_Public scored comparison of browser-automation MCP servers. Generated "
        "by `bench.build_report` from `results/2026-05-26/scores.json` + "
        "`cross_cut_data.json` + per-MCP `DEEP_ANALYSIS.md`. Provenance preserved "
        "verbatim; sandbox callouts re-applied idempotently as a final pass._"
    )
    parts.append("")
    parts.append(render_executive_summary(scores, partial_run_flag=partial_run_flag))
    parts.append("")
    parts.append(render_methodology_disclaimer(run_date))
    parts.append("")
    parts.append(render_methodology_section({"run_date": run_date}))
    parts.append("")
    parts.append("## Weighted Composite Score Table (REPORT-01)")
    parts.append("")
    parts.append(
        "Eight-dimension N/A-aware composite. Cell legend: `N/A` for "
        "categorically-inapplicable dimensions (drops from denominator); "
        "`SKIPPED` for whole-row skips (composite does NOT collapse to 0.0)."
    )
    parts.append("")
    parts.append(render_score_table(scores, RUBRIC_WEIGHTS))
    parts.append("")
    parts.append("## Stage Matrix (REPORT-02)")
    parts.append("")
    parts.append(
        "Per-stage outcomes across the 8-stage job-application pipeline. "
        "`N/A` (categorical) and `SKIPPED` (whole-row) are deliberately "
        "distinct cell types — the harness records both, the report renders both."
    )
    parts.append("")
    parts.append(render_stage_matrix(scores))
    parts.append("")
    parts.append(render_capability_view(capability_path))
    parts.append("")
    parts.append("## Per-MCP Deep Analysis (REPORT-03)")
    parts.append("")
    parts.append(
        "Each stanza below lifts verbatim from the corresponding "
        "`results/2026-05-26/<mcp>/DEEP_ANALYSIS.md` (with H2/H3 demoted by one "
        "level so the headings nest under this report's H1). `playwright` lacks "
        "a per-MCP DEEP_ANALYSIS.md and carries an explicit asymmetry note; "
        "`browser-use` renders as ONE combined stanza with Direct mode + Agent "
        "mode subsections per the FAIRNESS-05 dual-mode contract."
    )
    parts.append("")
    for mcp in SEVEN_MCPS:
        parts.append(render_deep_analysis(scores, deep_dir, mcp))
        parts.append("")
    parts.append(render_overlay_2026_03_2026_05(scores))
    parts.append("")
    parts.append(render_negative_results(scores, cross_cut))
    parts.append("")
    parts.append(render_carried_forward_limitations())
    parts.append("")
    parts.append(render_linear_traceability_footer())
    parts.append("")
    raw = "\n".join(parts)
    # Final pass: ensure every cloakbrowser mention is within 5 lines of a
    # sandbox callout. Idempotent against existing callouts in the embedded
    # CAPABILITY_MATRIX.md and per-MCP DEEP_ANALYSIS.md content.
    final = inject_sandbox_callouts(raw)
    if out_path is not None:
        # WR-05: parent must exist before write_text; match wave_close_check's
        # behavior so all three sibling builders share the same UX.
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(final, encoding="utf-8")
    return final


# ─── CLI ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m bench.build_report",
        description=(
            "Build the Phase 4 public scored comparison report from "
            "scores.json + cross_cut_data.json + per-MCP DEEP_ANALYSIS.md."
        ),
    )
    parser.add_argument("--scores", type=Path, required=True,
                        help="Path to scores.json (Phase 2 output)")
    parser.add_argument("--cross-cut", type=Path, required=True,
                        help="Path to cross_cut_data.json (Phase 3 output)")
    parser.add_argument("--capability", type=Path, required=True,
                        help="Path to CAPABILITY_MATRIX.md (Phase 2 P07 artifact)")
    parser.add_argument("--deep-dir", type=Path, required=True,
                        help="Directory containing per-MCP DEEP_ANALYSIS.md files "
                             "(typically `results/2026-05-26`)")
    parser.add_argument("--run-date", type=str, required=True,
                        help="Run date (e.g. 2026-05-27) for the report title")
    parser.add_argument("--out", type=Path, required=True,
                        help="Path to write the assembled Markdown report")
    args = parser.parse_args(argv)

    for path, label in [
        (args.scores, "scores"),
        (args.cross_cut, "cross-cut"),
        (args.capability, "capability"),
    ]:
        if not path.is_file():
            print(f"build_report: ERROR {label} input not found: {path}",
                  file=sys.stderr)
            return 2
    if not args.deep_dir.is_dir():
        print(f"build_report: ERROR deep-dir not found: {args.deep_dir}",
              file=sys.stderr)
        return 2

    md = build_report(
        args.scores, args.cross_cut, args.capability,
        args.deep_dir, args.run_date, args.out,
    )
    print(
        f"build_report: wrote {args.out} "
        f"({len(md.splitlines())} lines)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
