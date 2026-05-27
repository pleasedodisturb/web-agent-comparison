---
phase: 03-cross-cutting-measurements
plan: 05
subsystem: synthesis
tags: [synthesis, aggregation, cross-cut, phase-4-handoff, empirical-findings, markdown-rendering]

requires:
  - phase: 03-cross-cutting-measurements/01
    provides: "tool_call_counts.json + tools_inventory.json per MCP"
  - phase: 03-cross-cutting-measurements/02
    provides: "tokens.json per MCP (3-scope)"
  - phase: 03-cross-cutting-measurements/03
    provides: "cold_start.json per MCP (3-segment, cold+warm)"
  - phase: 03-cross-cutting-measurements/04
    provides: "stability_metadata.json per MCP (COMPLETED/SKIPPED)"
provides:
  - "bench/build_cross_cut_summary.py module + 7-test pytest suite"
  - "results/2026-05-26/CROSS_CUT_SUMMARY.md — Phase-4-consumable 9-section synthesis (171 lines)"
  - "results/2026-05-26/cross_cut_data.json — programmatic companion (headline values per dimension, no raw)"
  - "Six empirical findings with CONFIRMED/REFUTED/NO_EVIDENCE/INCONCLUSIVE verdicts grounded in loaded data"
affects: [phase-4-synthesis, recommendations-md, matrix-builder]

tech-stack:
  added:
    - "Stdlib-only pure-Python markdown table rendering (no tabulate / no jinja2)"
    - "Per-dimension status routing — stability uses completion_status, others use status"
  patterns:
    - "Aggregator-renderer split: aggregate_results returns JSON-ready dict, render_* functions consume it"
    - "Empirical findings as functions returning bullet strings (one per claim); _verdict helper for CONFIRMED/REFUTED logic"
    - "Strip-raw companion JSON pattern: drop nested raw payloads, lift only headline values for programmatic consumers"

key-files:
  created:
    - "bench/build_cross_cut_summary.py"
    - "tests/test_build_cross_cut_summary.py"
    - "results/2026-05-26/CROSS_CUT_SUMMARY.md"
    - "results/2026-05-26/cross_cut_data.json"
  modified: []

key-decisions:
  - "stability uses `completion_status` field (COMPLETED/SKIPPED/CRASHED); all four other dimensions use the `status` field. _dimension_status routes by dim name."
  - "Empirical findings emit grounded verdicts — the data IS the finding. No verdict was hand-edited to match the prior research hypothesis even when the numbers said NO_EVIDENCE."
  - "Maximal cold-start spread is the headline (51.4×, lightpanda 13ms vs browser-use 668ms); the lightpanda-vs-playwright finding (15.2×) is the secondary published number. Both surfaced in §7."
  - "Stability transport-vs-semantic caveat is hardcoded — obscura + browser-use-direct PASSed stability but Phase 2 semantic-output FAILs stand. Phase 4 matrix MUST annotate."
  - "JSON companion strips raw payloads but lifts headline values per dimension so Phase 4 can ingest without re-walking per-MCP dirs."

patterns-established:
  - "Aggregate-then-render: aggregate_results returns a structured dict; renderers consume it; tests target both layers"
  - "Verdict templates as functions: _playwright_batch_fill_finding, _lightpanda_cold_start_finding, etc — each returns a bullet string with a CONFIRMED/REFUTED/NO_EVIDENCE/INCONCLUSIVE marker"
  - "Status normalization through a thin _dimension_status helper that knows per-dim canonical field names"

requirements-completed: [MEAS-01, MEAS-02, MEAS-07, MEAS-08, MEAS-09]
success_criteria_advanced: [SC1, SC2, SC3, SC4, SC5]

duration: 30min
completed: 2026-05-27
---

# Phase 3 Plan 05: Cross-Cut Synthesis Summary

**Phase-4-consumable `CROSS_CUT_SUMMARY.md` (171 lines, 9 sections, 60 table rows) joining the 5 cross-cutting measurements from plans 03-01..03-04 into a single document — with 6 grounded empirical-finding verdicts and a programmatic JSON companion.**

## Performance

- **Duration:** ~30 min (TDD test ~10min, aggregator implementation ~10min, run + spot-check ~5min, SUMMARY ~5min)
- **Started:** 2026-05-27T (post-03-04 close)
- **Completed:** 2026-05-27
- **Tasks:** 2 (Task 1 TDD aggregator + tests, Task 2 generate live CROSS_CUT_SUMMARY.md)

## Accomplishments

- All 5 Phase 3 success criteria supported via the consolidated `CROSS_CUT_SUMMARY.md` (SC1=cold_start, SC2=tokens, SC3=stability, SC4=tool-call counts, SC5=tools_inventory) — each MEAS- dimension gets its own §-numbered section + appears in the §1 master table.
- All 5 MEAS- requirements satisfied at the synthesis layer: every dimension surfaces an empirical value per MCP (or a documented gap — playwright `NO_EVIDENCE` for tokens/tool-calls, browser-use-agent `SKIPPED` for tokens/tool-calls/stability, firecrawl `SKIPPED` for stability).
- Phase 4 has a single ingestion point — no need to walk per-MCP directories. `cross_cut_data.json` provides headline values programmatically; `CROSS_CUT_SUMMARY.md` is the human-readable narrative ingest.
- 7 new tests pass (master-table, missing-file handling, SKIPPED row rendering, batch-fill finding, NO_EVIDENCE finding, source manifest, browser-use dual rows). Full suite green: 234/234 (was 227 pre-Phase-3-05).
- scoring/score.py byte-unchanged (sacrosanct contract upheld).

## Task Commits

1. **Task 1 RED — failing tests for build_cross_cut_summary** — `be3c1cd` (test)
2. **Task 1 GREEN — bench/build_cross_cut_summary.py module** — `fee4736` (feat)
3. **Task 2 — generate live CROSS_CUT_SUMMARY.md + JSON companion** — `96f5e70` (feat)

## CROSS_CUT_SUMMARY.md Structure

| Section | Topic | Rows | Headline number |
|---|---|---|---|
| §1 | Master Cross-Cut Table | 8 (7 MCPs + browser-use-agent SKIPPED) | one row per MCP, 11 cols (cold/warm/payload/in/out tokens/stability/iters/tool-calls/S5/tool-count) |
| §2 | Cold-Start (MEAS-01) | 8 | 3-segment cold + warm medians per MCP |
| §3 | Token Efficiency (MEAS-02) | 8 | payload bytes (median), turn input/output tokens |
| §4 | Stability (MEAS-07) | 8 | configured/actual minutes, iters, RSS first/max/growth, orphan survivors |
| §5 | Tool-Call Counts (MEAS-08) | 8 | median total + per-stage S1-S8 |
| §6 | Tools Inventory (MEAS-09) | 8 | tool_count + 6-category breakdown |
| §7 | Empirical Findings | 6 bulleted findings | verdicts grounded in data |
| §8 | Methodology Notes | 5 sub-sections | disclaimers Phase 4 needs to honor |
| §9 | Source Manifest | 40 file paths | every per-MCP file with status |

## Headline Empirical Findings (the most-interesting three)

### 1. Cold-start spread is 51.4× (the headline cold-start delta)

`lightpanda` cold median = **13ms** vs `browser-use` (both direct + agent variants, shared MCP binary) at **668ms**. Maximal cold-start spread across all 8 OK rows. The Zig binary with no Chromium download path explains the gap — lightpanda spawns and answers `tools/list` faster than the OS's process-spawn syscall typically takes for Node-based MCPs.

The narrower lightpanda-vs-playwright comparison (15.2×) is the published secondary number. Both surfaced in §7 so Phase 4 has both framings.

### 2. Token-payload spread is 7.3×

Smallest payload: `obscura` at **16,394 bytes** median (across 8 stages × 3 passes). Largest: `browser-use-direct` at **120,059 bytes** median. The spread is significant because payload bytes are the proxy for context cost — every byte of MCP response that lands in Claude's context window is a token billed at the conversation's rate. A 7.3× spread on a per-stage measurement compounds across an 8-stage workflow.

Caveat (per methodology §8): payload bytes diverge from `turn` tokens (actual billing) by 2-10× because of cache-creation / cache-read deltas. The payload column is a proxy for **incremental context cost**, not absolute billing.

### 3. Playwright batch-fill claim is **NO_EVIDENCE** in this wave

Hypothesis (from research/SUMMARY.md): `browser_fill_form` fills N fields in 1-2 tool-calls vs ~6 per-field-fill calls for other MCPs. This would be a load-bearing differentiator for the Stage-2 toolkit graduation decision.

**The data does not support a verdict in this wave.** Playwright's `PASS{1,2,3}` directories exist at `results/2026-05-25/` (the calibration / Phase-1 run) but NOT at `results/2026-05-26/`. The `tool_call_counts.json` is therefore `status: NO_EVIDENCE` and `tokens.json` is `scope: no-evidence` for playwright in this wave.

Phase 4 reader: **do not cite the batch-fill claim as CONFIRMED** until a re-run produces PASS dirs at the current date. The cold-start, stability, and tools_inventory rows ARE valid (those measurements don't depend on PASS dirs).

## Limitations Carried Forward for Phase 4

These three should be surfaced explicitly in `recommendations.md`:

### Limitation 1: score_with_na.py SKIPPED-row composite=0.0 sentinel

`browser-use-agent` is `status: SKIPPED` in scores.json. The N/A-aware composite excludes it (correct behavior — SKIPPED means "not attempted," not "attempted and failed"). Phase 4 matrix-builder must use the row's `status` field, NOT just the composite, to distinguish this row from rows that attempted-and-failed. Otherwise browser-use-agent's composite of 0.0 will look indistinguishable from a 0/10 actual failure.

### Limitation 2: Transport-vs-semantic stability annotation needed

Two rows (`obscura`, `browser-use-direct`) PASSed stability at the transport level (call_tool returned without raising) but Phase 2 evidence shows SEMANTIC-output failures (obscura tool-bug cascade across all 8 stages; browser-use-direct S5 React-clobber). Phase 4 matrix MUST annotate these stability cells as `COMPLETED ⚠ (transport-only; Phase 2 semantic-output FAIL stands)`. The annotation is documented in §7 and §8 of CROSS_CUT_SUMMARY.md.

### Limitation 3: Playwright cross-cut data gap

PASS dirs at `results/2026-05-25/playwright/` not `results/2026-05-26/playwright/`. Cold-start, stability, and tools_inventory rows ARE valid (those don't depend on PASS dirs). Tokens (`scope: no-evidence`) and tool-call counts (`status: NO_EVIDENCE`) are the gap. Phase 4 has three options:

  - **(a)** Re-run playwright Phase-2 walk on 2026-05-26 to populate PASS dirs (~30min wall-clock).
  - **(b)** Cite the 2026-05-25 dir explicitly with a footnote acknowledging the date gap.
  - **(c)** Accept the NO_EVIDENCE marker in the published matrix and note "batch-fill claim unverified in this wave."

The CROSS_CUT_SUMMARY.md takes option (c) by default (the autonomous executor cannot extend wall-clock beyond the plan budget for a re-run). Phase 4 can override by re-running plans 03-01 + 03-02 with `--mcp playwright` if the recommendations.md author decides the batch-fill claim is load-bearing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Initial _dimension_status didn't route stability through completion_status**
- **Found during:** Task 1 GREEN — two tests (SkippedHandlingTests and BrowserUseDualRowsTests) failed with `AssertionError: 'OK' != 'SKIPPED'` because the function was reading `status` for every dimension, but stability_metadata.json uses `completion_status` (COMPLETED / SKIPPED / CRASHED) as its canonical field.
- **Fix:** Added a per-dim branch in `_dimension_status` — when dim=="stability", prefer the `completion_status` field; otherwise fall back to the `status` field.
- **Files modified:** `bench/build_cross_cut_summary.py` (`_dimension_status`).
- **Commit:** `fee4736`.

**2. [Rule 2 - Missing] Maximal cold-start spread was implicit, not explicit**
- **Found during:** Task 2 spot-check — the lightpanda finding compared lightpanda-vs-playwright (15.2×), but the headline executor-contract number was the maximal spread across all rows (51.4×, lightpanda vs browser-use). The implicit number was visible in the §1 master table but the §7 finding didn't surface it as a headline.
- **Fix:** Extended `_lightpanda_cold_start_finding` to also compute the global max spread across all OK rows and append it to the finding as the explicit headline number.
- **Files modified:** `bench/build_cross_cut_summary.py` (`_lightpanda_cold_start_finding`).
- **Commit:** `96f5e70`.

**3. [Rule 1 - Bug] Dangling `mcps.append_dim = None` placeholder**
- **Found during:** First TDD GREEN attempt — a leftover scaffolding line `mcps.append_dim = None  # placeholder to keep mypy quiet` was inside the aggregate_results loop. Harmless at runtime (just an attribute assignment on a list, which Python permits but mypy complains about). Removed cleanly.
- **Fix:** Deleted the placeholder line.
- **Files modified:** `bench/build_cross_cut_summary.py`.
- **Commit:** `fee4736` (same commit as the function implementation).

## Stop Conditions

None encountered. No file was unreadable; no findings rendered as all-INCOMPLETE; scores.json was present and parsed correctly.

## Phase 3 Closure

This is the **last plan of Phase 3**. With it complete:

- All 5 cross-cutting measurements per MCP are captured + synthesized.
- All 5 Phase 3 success criteria PASS (SC1-SC5).
- Phase 4 can begin with a single ingestion point: `results/2026-05-26/CROSS_CUT_SUMMARY.md` + `results/2026-05-26/cross_cut_data.json`.
- The three limitations above (SKIPPED composite, transport-vs-semantic, playwright PASS-dir gap) are explicit and ready for Phase 4 to address in `recommendations.md`.

scoring/score.py SACROSANCT contract upheld across all of Phase 3 (zero diff from main).

Full test suite: 234/234 green (was 216 pre-Phase-3, 227 after 03-04, 234 after 03-05).

## Self-Check

- [x] `bench/build_cross_cut_summary.py` exists and imports cleanly
- [x] `tests/test_build_cross_cut_summary.py` — 7/7 passing
- [x] `results/2026-05-26/CROSS_CUT_SUMMARY.md` exists; 171 lines, 60 table rows, 9 sections
- [x] `results/2026-05-26/cross_cut_data.json` exists with stripped-raw headline values per dimension
- [x] Master table has 8 rows (7 MCPs + browser-use-agent SKIPPED)
- [x] §7 Empirical Findings has 6 grounded findings (Playwright batch-fill, Lightpanda cold-start, Obscura memory, Token-payload spread, Cold-vs-warm delta, Stability transport-vs-semantic)
- [x] §9 Source Manifest lists 40 file paths (8 MCPs × 5 dimensions) with status
- [x] Full test suite: 234/234 green
- [x] scoring/score.py byte-unchanged (git diff main = 0 lines)

## Self-Check: PASSED
