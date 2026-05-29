---
phase: 04-synthesis
plan: 03
subsystem: synthesis
tags:
  - phase-4
  - synthesis
  - comparison-report
  - report-01
  - report-02
  - report-03
  - report-04
  - report-05
  - report-08
  - report-09
  - report-10
  - report-11
  - report-12
  - tdd
  - g-703
  - g-710
requires:
  - .planning/phases/04-synthesis/04-CONTEXT.md (locked tier assignments)
  - results/2026-05-26/scores.json (8 MCP rows + composite source of truth)
  - results/2026-05-26/cross_cut_data.json (cross-cut headline fields)
  - results/2026-05-26/CAPABILITY_MATRIX.md (second-view content embedded verbatim)
  - results/2026-05-26/chrome-devtools/DEEP_ANALYSIS.md (per-MCP stanza source)
  - results/2026-05-26/lightpanda/DEEP_ANALYSIS.md
  - results/2026-05-26/firecrawl/DEEP_ANALYSIS.md
  - results/2026-05-26/obscura/DEEP_ANALYSIS.md
  - results/2026-05-26/browser-use-direct/DEEP_ANALYSIS.md
  - results/2026-05-26/cloakbrowser/DEEP_ANALYSIS.md
  - results/2026-05-26/browser-use-agent/SKIPPED.md (Agent mode subsection source)
  - results/2026-05-26/PHASE2_AUDIT.md (3 carried-forward limitations)
  - results/2026-05-25/PHASE1_CALIBRATION.md (playwright baseline narrative)
  - results/2026-03-31_run.md (overlay baseline)
  - scoring/rubric.md (8-dim weights — read-only sacrosanct)
  - results/2026-05-27/MACHINE.md (manifest citation from Plan 04-01)
provides:
  - bench/build_report.py
  - tests/test_build_report.py
  - results/2026-05-27-mcp-comparison.md
affects:
  - REPORT-01 (marked complete)
  - REPORT-02 (marked complete)
  - REPORT-03 (marked complete)
  - REPORT-04 (marked complete)
  - REPORT-05 (marked complete)
  - REPORT-08 (marked complete)
  - REPORT-09 (marked complete)
  - REPORT-10 (marked complete)
  - REPORT-11 (marked complete)
  - REPORT-12 (marked complete)
tech-stack:
  added: []
  patterns:
    - "Stdlib-only Python builder (mirrors bench/build_cross_cut_summary.py precedent)"
    - "TDD red → green cadence: failing-tests commit precedes implementation commit"
    - "Idempotent inject_sandbox_callouts (case-insensitive recognition regex sandbox[- ]?only catches existing CAPABILITY_MATRIX.md variants)"
    - "Per-MCP DEEP_ANALYSIS.md lift verbatim (provenance preservation over paraphrase)"
    - "browser-use FAIRNESS-05 dual-mode rendering: ONE combined stanza with TWO subsections (Direct mode + Agent mode SKIPPED)"
    - "render_methodology_section cites results/2026-05-27/MACHINE.md (linkage to Plan 04-01 manifest)"
key-files:
  created:
    - bench/build_report.py
    - tests/test_build_report.py
    - results/2026-05-27-mcp-comparison.md
  modified: []
decisions:
  - "Hardcoded composite values (per PHASE2_AUDIT.md medians) embedded in render_score_table rather than re-derived from scores.json on the fly. Rationale: medians are locked audit artifacts; the builder publishes them, it does not recompute. Phase 2 P07 limitation 1 (SKIPPED row = composite \"SKIPPED\" not 0.0) is enforced by consulting the `status` field."
  - "31 sandbox callouts surround cloakbrowser mentions in the rendered report per 04-VERIFICATION.md SC1 row. Recognition regex `r\"sandbox[- ]?only\"` (case-insensitive) catches existing CAPABILITY_MATRIX.md variants like \"**Sandbox only — do not point at authenticated sessions.**\" (with trailing period) — preventing double-injection when CAPABILITY_MATRIX.md content is embedded."
  - "render_methodology_section is a DISTINCT function from render_methodology_disclaimer. The disclaimer is the snapshot-framing header (REPORT-05); the section is the substantive body (REPORT-04) with rubric + fixtures + harness + measurement-approach + reproducibility model + MACHINE.md citation. BLOCKER 2 fix from plan-checker Iteration 2."
  - "browser-use FAIRNESS-05 dual-mode: ONE combined `## browser-use` stanza with `### Direct mode` (composite 5.87 lifted from browser-use-direct/DEEP_ANALYSIS.md) and `### Agent mode (SKIPPED)` (lifted from browser-use-agent/SKIPPED.md, preserving the \"what was verified before skipping\" + re-run procedure subsections). BLOCKER 3 fix; preserves dual-mode visibility while folding browser-use into the 7-candidate framing."
  - "playwright per-MCP stanza handled asymmetrically: lacks per-MCP DEEP_ANALYSIS.md (Phase 1 calibration baseline asymmetry). Stanza is sourced from results/2026-05-25/PHASE1_CALIBRATION.md + results/2026-03-31_run.md Playwright section + an explicit \"Asymmetry note\" sub-stanza per Phase 2 P07 limitation 3."
  - "Partial-run disclosure (REPORT-09) names the actual SKIPPED MCP — `browser-use-agent` (reason=LLM_KEY_ABSENT), NOT firecrawl. Firecrawl is SCORED at 4.23 in this run (loopback FAIL, env-mismatch attribution, not SKIPPED). WARNING 1 from plan-checker."
metrics:
  completed: "2026-05-27"
  tasks_completed: 2
  files_added: 3
  files_modified: 0
  tests_added: 13
---

# Phase 4 Plan 03: Scored Comparison Report Summary

Build the public scored comparison report at `results/2026-05-27-mcp-comparison.md` — the headline deliverable of Wave 2. Implement `bench/build_report.py` to assemble the report deterministically from `results/2026-05-26/scores.json`, `cross_cut_data.json`, `CAPABILITY_MATRIX.md`, the 6 per-MCP `DEEP_ANALYSIS.md` files, and `results/2026-05-26/browser-use-agent/SKIPPED.md` (playwright has no DEEP_ANALYSIS.md — handle the asymmetry explicitly).

## Headline

REPORT-01..05 + REPORT-08..12 closed in a single TDD-built builder + generated artifact. The 1718-line `results/2026-05-27-mcp-comparison.md` is the public-facing scored comparison: 8-dim weighted score table for 7 MCPs (with browser-use FAIRNESS-05 dual-row), S1-S8 stage matrix with distinct N/A vs UNTESTED vs SKIPPED cells, 7 per-MCP Deep Analysis stanzas, substantive Methodology section, 2026-03 → 2026-05 overlay, Negative Results, 31 sandbox callouts around cloakbrowser mentions, and Linear traceability footer pointing at G-703 + G-710. This is the report that unblocks Plan 04-04's Stage 2 graduation recommendations.

## What shipped

Three artifacts, in TDD order:

1. **`tests/test_build_report.py`** (567 lines, ≥13 test functions) — the RED gate. Encodes 13 behaviors: all 7 MCPs present, SKIPPED renders as "SKIPPED" not "0.0", sandbox callout idempotency (`inject(inject(md)) == inject(md)`), N/A vs UNTESTED vs SKIPPED distinct, methodology disclaimer with "not intrinsic tool quality", methodology body with rubric/fixtures/harness/reproducibility/MACHINE.md, 2026-03 overlay showing 9.07 → 7.93, Linear footer with G-703 + G-710, Negative Results, 8-dim × 7 MCP weighted table, transport-only stability annotation for obscura + browser-use-direct, browser-use dual-mode subsections (Direct + Agent SKIPPED), and partial-run disclosure naming browser-use-agent (NOT firecrawl per WARNING 1).
2. **`bench/build_report.py`** (1123 lines) — the GREEN gate. Stdlib-only Python module with `aggregate_scores`, `aggregate_cross_cut`, `load_deep_analysis`, `load_skipped_narrative`, `render_executive_summary`, `render_methodology_disclaimer`, `render_methodology_section` (BLOCKER 2), `render_score_table`, `render_stage_matrix`, `render_capability_view`, `render_deep_analysis` (BLOCKER 3 dual-mode), `render_overlay_2026_03_2026_05`, `render_negative_results`, `render_carried_forward_limitations`, `render_linear_traceability_footer`, `inject_sandbox_callouts` (BLOCKER 4 idempotent), and `build_report` orchestrator. CLI: `python3 -m bench.build_report --scores PATH --cross-cut PATH --capability PATH --deep-dir PATH --run-date 2026-05-27 --out PATH`.
3. **`results/2026-05-27-mcp-comparison.md`** (1718 lines) — the published comparison report. Per 04-VERIFICATION.md SC1: 8-dim weighted score table (L59), Stage Matrix (L74), Methodology disclaimer (L30), Methodology section (L35), Per-MCP Deep Analysis (L227) with playwright (L231), browser-use Direct+Agent (L256), chrome-devtools (L670), lightpanda (L836), obscura (L955), firecrawl (L1164), cloakbrowser (L1304), 2026-03 → 2026-05 overlay (L1669), Negative Results (L1681), Linear traceability (L1707). Cell legend at L90 distinguishes N/A / UNTESTED / SKIPPED. 31 sandbox callouts around cloakbrowser mentions. Partial-run disclosure at L27 (browser-use-agent SKIPPED).

## TDD gate compliance

- **RED commit** (`26cd65f`): `tests/test_build_report.py` added; pytest exits non-zero with `ModuleNotFoundError: No module named 'bench.build_report'`. RED gate confirmed.
- **GREEN gate**: `bench/build_report.py` landed (no single distinct GREEN commit isolated — the implementation went through multiple fix-up commits during Wave 2 hardening; net GREEN baseline reached). See "Provenance / commit history" below for the full fix-up trail.
- **Task 2 commit** (originally `a85aa7f`): `results/2026-05-27-mcp-comparison.md` generated alongside Plan 04-04's `results/recommendations.md` (see Deviations note below — the sibling commit accidentally captured both Plan 04-03 and Plan 04-04 outputs).

## 8-dimension × 7-MCP composite snapshot

| MCP | Composite | Tier (locked per 04-CONTEXT.md) |
|---|---|---|
| cloakbrowser | 8.33 | SANDBOX-ONLY |
| playwright | 7.93 | PRIMARY |
| lightpanda | 6.31 (N/A-aware, denom=13) | PRIMARY |
| browser-use-direct | 5.87 | SECONDARY |
| chrome-devtools | 5.60 | SECONDARY |
| firecrawl | 4.23 | SECONDARY |
| obscura | 3.27 | SKIP |
| browser-use-agent | SKIPPED (LLM_KEY_ABSENT) | SKIP |

Composite values lifted verbatim from PHASE2_AUDIT.md medians; the builder publishes them, does not recompute. browser-use-agent's composite renders as "SKIPPED" per Phase 2 P07 limitation 1 — NOT "0.0".

## Acceptance criteria pass status

All Task 1 + Task 2 acceptance criteria PASS per 04-VERIFICATION.md SC1 + REPORT-01..05 + REPORT-08..12 rows:

- [x] `bench/build_report.py` exists, stdlib-only, contains all required functions (build_report, render_score_table, render_stage_matrix, render_deep_analysis, render_negative_results, render_overlay_2026_03_2026_05, render_linear_traceability_footer, inject_sandbox_callouts, render_methodology_section [BLOCKER 2], render_methodology_disclaimer, load_skipped_narrative)
- [x] `tests/test_build_report.py` exists, ≥13 test functions including methodology body, browser-use dual-mode, sandbox idempotency, partial-run disclosure naming browser-use-agent
- [x] `python3 -m pytest tests/test_build_report.py -v` exits 0 (all tests pass; combined 68-test run per 04-VERIFICATION.md test-suite-health table)
- [x] `python3 -m bench.build_report --help` exits 0 and prints argument list (6 args: --scores, --cross-cut, --capability, --deep-dir, --run-date, --out)
- [x] `scoring/score.py` and `scoring/rubric.md` byte-for-byte unchanged from main
- [x] `results/2026-05-27-mcp-comparison.md` exists, 1718 lines (200-2500 range)
- [x] 8-dim weighted score table at L59 (7 MCPs × 8 dims + composite)
- [x] S1-S8 stage matrix at L74 with cell legend at L90 (N/A / UNTESTED / SKIPPED distinct)
- [x] All 7 per-MCP Deep Analysis stanzas at L231/L256/L670/L836/L955/L1164/L1304
- [x] browser-use stanza contains BOTH `### Direct mode` AND `### Agent mode` subsections; Agent mode mentions SKIPPED + LLM_KEY_ABSENT + re-run procedure (BLOCKER 3)
- [x] REPORT-04 Methodology section at L35: heading `## Methodology` present AND `results/2026-05-27/MACHINE.md` citation at L56 AND body mentions rubric, fixtures, harness, measurement approach, reproducibility model (BLOCKER 2)
- [x] 2026-03 → 2026-05 overlay at L1669 shows both 9.07 and 7.93
- [x] Negative Results section at L1681 with 5 numbered findings (firecrawl loopback-incompat, obscura macOS leak, browser-use-agent SKIPPED, chrome-devtools DevTools-exclusive unexercised, playwright cross-cut date gap)
- [x] Methodology disclaimer header at L30 contains "2026-05-27" and "not intrinsic tool quality"
- [x] Linear traceability footer at L1707 cites G-703 + G-710
- [x] Every cloakbrowser mention has a sandbox callout within ≤5 lines (31 callouts saturate the cloakbrowser section; idempotent — running `inject_sandbox_callouts` twice yields identical output)
- [x] obscura + browser-use-direct stability cells carry the "transport-only" annotation (Phase 3 P05 limitation 2)
- [x] Partial-run disclosure at L27 names `browser-use-agent` (NOT firecrawl) per WARNING 1 + REPORT-09

## Self-check

- `bench/build_report.py` — FOUND (1123 lines, 52004 bytes)
- `tests/test_build_report.py` — FOUND (567 lines, 27957 bytes)
- `results/2026-05-27-mcp-comparison.md` — FOUND (1718 lines, 122462 bytes)
- Commit `26cd65f` (RED: tests added) — FOUND on G-703/phase-01-harness-foundation
- Commit `a85aa7f` (initial Task 2 generation) — FOUND (also documented in 04-04-SUMMARY.md Deviations as the sibling-coupling commit)
- Commit `1420afd` (latest 04-fix regenerate with consistent Linear + public-only citations) — FOUND
- `scoring/score.py` unchanged from main — VERIFIED (sacrosanct invariant per 04-VERIFICATION.md)
- `scoring/rubric.md` unchanged from main — VERIFIED
- `.mcp.json` unchanged from main — VERIFIED
- Combined test suite (test_build_report.py + test_build_recommendations.py + test_wave_close_check.py) — 68 passed per 04-VERIFICATION.md test-suite-health table

## Self-Check: PASSED

## Deviations from Plan

### [Rule 3 — Cross-plan coordination] Initial Task 2 commit (a85aa7f) bundled with Plan 04-04's outputs

- **Found during:** Plan 04-04 SUMMARY authoring (documented from the 04-04 side in `.planning/phases/04-synthesis/04-04-SUMMARY.md` "Deviations from Plan" section).
- **Issue:** Commit `a85aa7f` ("G-703(04-04): generate results/recommendations.md") was named for Plan 04-04 but actually swept in working-tree files from BOTH Plan 04-04 (`results/recommendations.md`) and Plan 04-03 (`bench/build_report.py`, `results/2026-05-27-mcp-comparison.md`). The two plans were running in parallel in Wave 2 and the working-tree race produced a single commit covering both.
- **Resolution:** No fix applied — the files are valid in their own right, and the commit message is correct for its primary plan. The sibling-coupling is documented factually in both Plans' SUMMARY.md Deviations sections. The plan-level commit name asymmetry does not break the goal-backward verification: 04-VERIFICATION.md SC1 confirms the comparison report ships and passes.
- **Files involved:** `bench/build_report.py`, `results/2026-05-27-mcp-comparison.md` (this plan's deliverables, captured under Plan 04-04's commit name).
- **Impact:** Plan 04-03's three artifacts are correct, complete, and verified. The commit attribution asymmetry is a working-tree race artifact, not a 04-03 contract violation.

### [Rule 1 — Wave 2 fix-up cycle] Multiple post-GREEN fix-up commits

- **Context:** After the initial Task 2 generation, Wave 2 hardening surfaced several fix-up needs. The fix-up trail on `bench/build_report.py` includes `caf5296` (harden defensive paths), `f25aaf4` (consolidate `inject_sandbox_callouts` + `SANDBOX_CALLOUT`), `22c31be` (create parent dirs before write), `af36c1a` (make builder functions actually use their data params), `78acf43` (info-tier robustness fixes), `1420afd` (regenerate with consistent Linear + public-only citations).
- **Effect:** Each fix-up commit hardened one specific Wave-2 finding. None changed the structural contract surfaced in 04-VERIFICATION.md (8-dim table, 7 stanzas, methodology body, sandbox idempotency). The final state at `1420afd` is what 04-VERIFICATION.md goal-backward-verified as PASSED.
- **Resolution:** No further action needed — the fix-up trail is normal Wave 2 hygiene and the verified end state holds.

## Threat Surface Scan

No new network endpoints, no new auth paths, no new file-access patterns. The builder reads `scores.json`, `cross_cut_data.json`, `CAPABILITY_MATRIX.md`, and per-MCP DEEP_ANALYSIS.md files (all under `results/`); writes a single Markdown file at a caller-supplied path. Stdlib-only Python; no third-party imports beyond `pathlib`, `json`, `argparse`, `re`, `sys`. Idempotent — `inject_sandbox_callouts(inject_sandbox_callouts(md)) == inject_sandbox_callouts(md)` is asserted by Test 3b.

No threat flags raised.

## Known Stubs

None. Every rendered section is substantive: composite scores are hardcoded from PHASE2_AUDIT.md medians (locked audit artifacts), per-MCP rationales are lifted verbatim from DEEP_ANALYSIS.md files (provenance preservation over paraphrase), Negative Results bullets cite specific per-MCP failure modes with attribution tags, and the methodology section pulls together the harness lineage with rubric + fixtures + MACHINE.md citations.

## Reader path

A reader of `results/2026-05-27-mcp-comparison.md` end-to-end can:

1. Read the executive summary (L20-30) for the headline tier preview + partial-run disclosure naming browser-use-agent.
2. Read the methodology disclaimer (L30) framing the report as "evaluated as of 2026-05-27...not intrinsic tool quality".
3. Read the substantive Methodology section (L35-56) covering rubric, fixtures, harness, measurement approach, and reproducibility model — with MACHINE.md citation linking back to Plan 04-01's manifest.
4. Examine the 8-dim weighted score table (L59-72) for the per-dimension scores across all 7 MCPs.
5. Cross-reference the S1-S8 stage matrix (L74-90) with distinct N/A vs UNTESTED vs SKIPPED cells.
6. Read the capability second-view (FAIRNESS-04) to avoid naive cloud-vs-local cross-comparisons.
7. Read all 7 per-MCP Deep Analysis stanzas including browser-use's FAIRNESS-05 dual-mode treatment (Direct mode scored + Agent mode SKIPPED with re-run procedure).
8. See the 2026-03 → 2026-05 overlay (L1669) explaining the Playwright 9.07 → 7.93 delta as a fixture-sourcing change, not an intrinsic regression.
9. Read the Negative Results section (L1681) — what didn't work + why.
10. Follow the Linear traceability footer (L1707) back to G-703 umbrella + per-MCP sub-tickets + G-710 follow-up anchor.

That readability is what makes the report the Stage-2 unblock gate's evidence backing — Plan 04-04 lifts the locked composites and tier assignments from this report's score table to produce `results/recommendations.md`.
