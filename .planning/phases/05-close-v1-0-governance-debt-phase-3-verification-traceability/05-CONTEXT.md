# Phase 5: Close v1.0 governance debt — Phase 3 verification + traceability sync - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

This is a **governance-debt-closer phase**, not a feature phase. Wave 2 closed 2026-05-27 with milestone DoD achieved (per `.planning/v1.0-MILESTONE-AUDIT.md`, status=`tech_debt`); this phase remediates the 5 non-blocking debt items the audit enumerated, so the milestone can be archived as `complete` instead of `tech_debt`.

**Deliverables (all documentation-only — no scoring artifacts, no scores.json mutation, no rubric change):**

1. `03-VERIFICATION.md` — retroactive goal-backward verification of Phase 3 (Cross-Cutting Measurements), authored by `gsd-verifier` against the existing `03-CONTEXT.md` + 5 `03-XX-SUMMARY.md` files.
2. `.planning/REQUIREMENTS.md` traceability table — 31 of 45 rows currently `Pending` are synced to `Complete`, sourced from each owning phase's VERIFICATION.md.
3. `.planning/phases/04-synthesis/04-01-SUMMARY.md`, `04-02-SUMMARY.md`, `04-03-SUMMARY.md` — author the 3 missing Phase 4 plan-level summaries from commit history + 04-VERIFICATION.md evidence.
4. `results/recommendations.md` — fix the cosmetic `2026-05-28` → `2026-05-27` date drift on L3 + L7 (one-line edit in `bench/build_recommendations.py`, then regenerate).
5. `05-VERIFICATION.md` — Phase 5 itself gets goal-backward verification (avoids creating new debt while closing old debt).

**Out of scope (locked):**
- No re-scoring, no `scores.json` edits, no `scoring/score.py` change, no `scoring/rubric.md` change (the sacrosanct invariants stay sacrosanct).
- No new MCP candidates, no rubric column changes (the `bench/wave_close_check.py` invariants must still pass at end-of-phase).
- No Linear closure (G-703, G-714..G-720, G-721) — that's the audit's 5th debt item, but it's an external manual step that this autonomous executor cannot perform (no Linear API access in this session). Documented as "external follow-up" and explicitly left for `/gsd-complete-milestone v1.0`.
- No fixes to the known `score_with_na.py` SKIPPED-row composite=0.0 sentinel (carried forward to a future wave; not v1.0 debt).
- No retroactive backfill of Phase 3 token `schema` scope from Anthropic SDK `count_tokens` (deferred — ANTHROPIC_API_KEY absent at measurement time; G-710 territory).

</domain>

<decisions>
## Implementation Decisions

### Scope inclusion (which audit items are in Phase 5)
- **D-01:** **Include all 5 audit items except external Linear closure.** Items 1–4 (Phase 3 VERIFICATION.md, traceability sync, missing Phase 4 SUMMARY.md trio, recommendations.md date fix) are all internal-codebase edits with zero risk to the published artifacts. Closing 4-of-5 inline beats Option A (archive with debt + clean up later) per the audit's recommendation, and the phase title's "Phase 3 verification + traceability sync" names the two LOAD-BEARING items — the other two are cheap kill-while-here adds.
- **D-02:** **External Linear closure (G-703 + G-714..G-720 + G-721) stays deferred to `/gsd-complete-milestone v1.0`.** Phase 5 documents the closure expectation in a follow-up note in `05-VERIFICATION.md`; it does not attempt API calls.

### Phase 3 verification approach
- **D-03:** **Use the `gsd-verifier` subagent retroactively against Phase 3.** Same tool that produced 01-, 02-, and 04-VERIFICATION.md — preserves goal-backward symmetry across all 4 closed phases. Inputs: ROADMAP.md Phase 3 Goal + SCs, 03-CONTEXT.md, 03-01..03-05-PLAN.md, 03-01..03-05-SUMMARY.md, and live artifacts (`results/2026-05-26/*/cold_start.json`, `tokens.json`, `stability.log`, `tools_inventory.json`, `bench/cross_cut_data.json`, `CROSS_CUT_SUMMARY.md`).
- **D-04:** **Verifier must walk the same 5 SCs verbatim from ROADMAP.md L54-59** (cold_start 3-segment medians, tokens 3-scope split, stability 60min loop with 0 orphans, per-stage tool-call counts, tools_inventory.json). Not a re-discovery of what was important — the SCs are LOCKED.
- **D-05:** **Tolerate the known carry-forward gaps as `partial` not `fail`:** firecrawl payload=0 (cloud cannot reach loopback), playwright cross-cut NO_EVIDENCE (PASS dirs at 2026-05-25 not 2026-05-26), token schema scope null (ANTHROPIC_API_KEY absent). All three are documented in `03-05-SUMMARY.md` and propagated into `04-VERIFICATION.md` — Phase 3 verification re-states them as known partials, doesn't re-litigate them.

### Traceability sync method
- **D-06:** **Single sweep after Phase 3 VERIFICATION.md exists.** Order matters: produce 03-VERIFICATION.md FIRST (so the MEAS-01/02/07/08/09 rows have a documented source), then do the traceability sweep.
- **D-07:** **Source of truth per requirement:** each row reads from its owning phase's VERIFICATION.md (01-VERIFICATION.md for HARNESS/FAIRNESS/REPRO/SAFETY/OUTREACH rows on Phase 1, 02-VERIFICATION.md for FAIRNESS-04/05, the new 03-VERIFICATION.md for MEAS-*, 04-VERIFICATION.md for REPRO-01/03/06 + REPORT-01..12 + SAFETY-05).
- **D-08:** **Manual mechanical edit, not a script.** 45 rows × ~10 seconds per row = ~7 minutes. Writing a script + validating its output costs more than the edit. The audit's `~10 min` estimate stands. Apply directly via `Edit` tool with `replace_all` where safe.
- **D-09:** **Status taxonomy stays binary (`Complete` / `Pending`).** No new `Deferred` state needed — the 7 scope-cut requirements (MEAS-03/04, MEAS-05/06, REPRO-07, OUTREACH-01/02) were already removed from the 45-row table when v1 scope dropped 52→45. All 45 rows must end as `Complete` after the sweep. Any row that cannot be marked `Complete` after the sweep is a real gap that blocks milestone close.

### Phase 4 SUMMARY.md backfill
- **D-10:** **Author 04-01, 04-02, 04-03 SUMMARY.md** from commit-message + 04-VERIFICATION.md evidence. Match the format of the existing 04-04/04-05/04-06 SUMMARY.md files for consistency. No new evidence; the artifacts (versions manifest, REPRODUCIBILITY.md, build_report.py + comparison.md) already exist and pass goal-backward verification per the milestone audit.
- **D-11:** **Do NOT re-execute the plans.** Just write the summaries. This is governance symmetry, not re-work.

### recommendations.md date fix
- **D-12:** **Fix the root cause in `bench/build_recommendations.py`, then regenerate `results/recommendations.md` via the existing builder.** Hand-editing the generated artifact would re-introduce the drift on next regenerate. The fix is the locked wave-date constant (`2026-05-27`) in the builder.
- **D-13:** **Diff must be exactly 2 lines changed in `results/recommendations.md`** (L3 + L7 "2026-05-28" → "2026-05-27"). Anything else means the regenerate touched something it shouldn't — investigate before committing.

### Phase 5 self-verification
- **D-14:** **Phase 5 produces its own `05-VERIFICATION.md`.** Goal-backward analysis on the 5 deliverables listed in the Phase Boundary section. Same `gsd-verifier` subagent. Closes the debt-closer recursively; no new debt created.

### Test-suite + sacrosanct invariants gate (mandatory exit check)
- **D-15:** **End-of-phase: `pytest` runs green (309/309 baseline holds) AND `bench/wave_close_check.py` still reports `all_pass=True` on candidate_count=7 + rubric_columns=8 + terminal_craft_commits=0 + no_new_mcps=True.** If either breaks, Phase 5 fails — none of its edits should touch test surface or wave-close invariants.
- **D-16:** **`scoring/score.py` + `scoring/rubric.md` + `.mcp.json` byte-for-byte unchanged from main.** Verify via `git diff main -- scoring/score.py scoring/rubric.md .mcp.json` returning empty.

### Claude's Discretion
- **Order of edits within plan:** Claude picks the dependency-correct ordering inside the planner (03-VERIFICATION.md before traceability sweep is mandatory; everything else is flexible).
- **Exact format of new SUMMARY.md files** (D-10): mirror the structure of 04-04-SUMMARY.md as the canonical template; minor structural variation allowed if matching evidence shape requires it.
- **Whether to commit the 4 deliverables as 4 atomic commits or 1 squashed commit:** Claude picks; atomic is preferred for traceability but not enforced.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit + milestone definition (load-bearing)
- `.planning/v1.0-MILESTONE-AUDIT.md` — defines the 5 debt items, the DoD per-clause verdict, and the Option A/B recommendation. This phase implements Option B for items 1–4.
- `.planning/REQUIREMENTS.md` §Traceability (L107-155) — the table being synced. Lines L111-155 are the 45-row table; 31 rows are `Pending` and must be flipped to `Complete` or flagged as real gaps.
- `.planning/REQUIREMENTS.md` §Definition of Done (L175+) — confirms the milestone-close gate.
- `.planning/ROADMAP.md` §Phase 3 (L50-61) — the 5 SCs that `gsd-verifier` walks for 03-VERIFICATION.md.

### Phase 3 inputs for `gsd-verifier` (read-only for verifier; do not re-author)
- `.planning/phases/03-cross-cutting-measurements/03-CONTEXT.md`
- `.planning/phases/03-cross-cutting-measurements/03-01-PLAN.md` through `03-05-PLAN.md`
- `.planning/phases/03-cross-cutting-measurements/03-01-SUMMARY.md` through `03-05-SUMMARY.md`
- `bench/cross_cut_data.json` — the load-bearing cross-cut aggregation
- `results/2026-05-26/<mcp>/cold_start.json`, `tokens.json`, `stability.log`, `tools_inventory.json` for all 7 MCPs (acknowledge playwright NO_EVIDENCE)
- `CROSS_CUT_SUMMARY.md` (location: per 03-05-SUMMARY.md provenance line)

### Phase 4 SUMMARY.md template + evidence (for backfill)
- `.planning/phases/04-synthesis/04-04-SUMMARY.md` — canonical template format for the 3 backfilled summaries
- `.planning/phases/04-synthesis/04-05-SUMMARY.md`, `04-06-SUMMARY.md` — additional format reference
- `.planning/phases/04-synthesis/04-VERIFICATION.md` — goal-backward evidence for what 04-01/02/03 each delivered
- Commit log for plans 04-01/02/03 — provenance for what each plan touched

### Date-fix targets
- `bench/build_recommendations.py` — the builder that emits `results/recommendations.md`. Locate the wave-date constant and pin to `2026-05-27`.
- `results/recommendations.md` L3, L7 — the two affected lines (both currently say "2026-05-28").

### Sacrosanct invariants gate
- `scoring/score.py`, `scoring/rubric.md`, `.mcp.json` — diff-against-main must remain empty.
- `bench/wave_close_check.py` — re-run at end-of-phase; must report `all_pass=True`.
- `.planning/phases/04-synthesis/WAVE_CLOSE_AUDIT.md` — current baseline (do not regenerate; just verify the live re-run matches).

### Project + state
- `.planning/PROJECT.md` — project core value + Stage 1/2/3 framing (untouched by this phase).
- `.planning/STATE.md` — currently shows milestone status=completed; updating to reflect Phase 5 work is part of normal STATE.md hygiene at phase close.

### Prior phase context (for `gsd-verifier` to mirror format/style)
- `.planning/phases/01-harness-foundation/01-VERIFICATION.md` — Phase 1's verifier output, structural reference for 03-VERIFICATION.md format
- `.planning/phases/02-per-mcp-scoring-runs/02-VERIFICATION.md` — Phase 2's verifier output, structural reference for 03-VERIFICATION.md format
- `.planning/phases/04-synthesis/04-VERIFICATION.md` — Phase 4's verifier output, the most recent format

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`gsd-verifier` subagent** (installed per init.phase-op → `agents_installed: true`): produces VERIFICATION.md from phase Goal + SCs + plan summaries. Used for Phase 1, 2, 4. Phase 5 reuses it for both Phase 3 retroactively AND Phase 5 itself.
- **`bench/build_recommendations.py`** (per 04-VERIFICATION.md): the existing builder for `results/recommendations.md` — `build_report.py`-style generator pattern. Edit the wave-date constant in this file, then re-execute the entry point. Do NOT hand-edit the output file.
- **`bench/wave_close_check.py`** (per 04-06 plan): the SAFETY-05 invariants auditor. Re-run at the end of Phase 5 as the milestone-close re-gate (proves nothing leaked).
- **Existing VERIFICATION.md format** (Phase 1, 2, 4): consistent structure — SC-by-SC verdict table + evidence citations + known limitations. `gsd-verifier` will follow this format for Phase 3 by default.

### Established Patterns
- **VERIFICATION.md per closed phase** — symmetry pattern. Phase 3 is the only outlier; this phase fixes that.
- **`-SUMMARY.md` per plan** — symmetry pattern. Phase 4 plans 04-01/02/03 are the outliers; this phase fixes that.
- **`Complete` vs `Pending` binary status** in REQUIREMENTS.md traceability (per L109-155). No `Deferred` state — scope-cut items are removed entirely.
- **2-line additive diff discipline** — the Phase 2 attribution audit (`02-07`) and `recommendations.md` regenerate both target minimal-diff outputs to prove no scope leakage.
- **Sacrosanct invariants check** — `scoring/score.py`, `scoring/rubric.md`, `.mcp.json` are byte-for-byte locked. Verified across Phase 2, 3, 4. Phase 5 inherits the same lock.

### Integration Points
- **`gsd-verifier` consumes** Phase 3's CONTEXT.md + PLAN.md + SUMMARY.md files (read-only) and emits `03-VERIFICATION.md` — no upstream code change.
- **REQUIREMENTS.md traceability sweep** is a pure-edit operation against `.planning/REQUIREMENTS.md` — no code touches.
- **`bench/build_recommendations.py` regenerate** flows into `results/recommendations.md`. Verify exactly 2-line diff before committing.
- **End-of-phase `pytest` re-run** is the test-suite integration gate (309/309 baseline). No tests should be added; this is doc-only work.

</code_context>

<specifics>
## Specific Ideas

- **Wave-locked dates:** `2026-05-27` is the canonical wave-close date. Every artifact in Phase 5 that names a date must agree. `2026-05-28` (today) appears only in audit + Phase 5 work itself (CONTEXT.md gathered date, etc.) — that's correct context, not drift.
- **"Same format as Phase 4"** is the consistent answer to layout/structure questions in Phase 5. The Phase 4 VERIFICATION.md and SUMMARY.md files are the most recent and most aligned with current GSD conventions.
- **Audit-says-tech-debt → milestone-says-complete** is the success state. The `gsd-complete-milestone v1.0` invocation after Phase 5 should observe `status: complete` (or equivalently: no open debt items in `.planning/v1.0-MILESTONE-AUDIT.md`).

</specifics>

<deferred>
## Deferred Ideas

- **External Linear closure (G-703 + G-714..G-720 + G-721)** — out of scope for autonomous execution (no API access in this session). Will be done by the user (or a Linear-CLI-enabled session) as a manual follow-up after `/gsd-complete-milestone v1.0`. Phase 5 explicitly notes this expectation in `05-VERIFICATION.md`.
- **`score_with_na.py` SKIPPED-row composite=0.0 sentinel fix** — known limitation carried forward from Phase 2 P05 and Phase 2 P07. Not v1.0 debt; Phase 4 matrix builder already works around it by consulting the `status` field. Future-wave concern.
- **Token schema-scope backfill from Anthropic SDK `count_tokens`** — would require ANTHROPIC_API_KEY at re-measurement time. Per Phase 3 P02 SUMMARY: idempotent re-run will backfill four `schema_*` fields without disturbing payload/turn data. Defer to a future wave or G-710.
- **Playwright cross-cut data gap** (PASS dirs at 2026-05-25 not 2026-05-26) — Phase 4's `build_report.py` already surfaces this as NO_EVIDENCE. Not a Phase 5 deliverable; surface in Phase 3 VERIFICATION.md as a known partial.
- **Linux A/B for obscura + cloakbrowser** — G-710 territory, explicitly out of scope. Stage 2 graduation tiers in `results/recommendations.md` stay as-is (`SANDBOX-ONLY` for cloakbrowser, `SKIP` for obscura).

</deferred>

---

*Phase: 5-Close v1.0 governance debt: Phase 3 verification + traceability sync*
*Context gathered: 2026-05-28*
