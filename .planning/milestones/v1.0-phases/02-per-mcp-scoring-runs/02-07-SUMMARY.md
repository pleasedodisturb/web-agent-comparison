---
phase: 02-per-mcp-scoring-runs
plan: 07
mcp: audit
subsystem: benchmark
tags: [attribution-audit, FAIRNESS-04, FAIRNESS-05, FAIRNESS-06, capability-matrix, phase-closure, cross-row, score-py-sacrosanct, audit-injection, two-view-publication]

requires:
  - phase: 02-per-mcp-scoring-runs
    plans: [01, 02, 03, 04, 05, 06]
    provides: 7 SCORED + 1 SKIPPED rows in scores.json with per-MCP DEEP_ANALYSIS.md, SANDBOX_PROOF.md (cloakbrowser), SKIPPED.md (browser-use-agent + firecrawl partial-run pattern), per-row capability tags + attribution tags from {tool-bug, env-mismatch, target-flag, transient}
  - phase: 01-harness-foundation
    provides: scoring/score.py (SACROSANCT — byte-for-byte locked), scripts/score_with_na.py (N/A-aware composite wrapper), bench/failure_taxonomy.py (4-tag aggregator), 176-test suite

provides:
  - "PHASE2_AUDIT.md at both .planning/phases/02-per-mcp-scoring-runs/PHASE2_AUDIT.md and results/2026-05-26/PHASE2_AUDIT.md — per-SC PASS/FAIL summary across all 5 Phase 2 success criteria; tag-injection inventory; 3 known limitations carried forward for Phase 4"
  - "results/2026-05-26/CAPABILITY_MATRIX.md — the FAIRNESS-04 second-view artifact: MCPs grouped by capability category (tool-only / LLM-augmented / stealth-specialist / cloud / js-light) with sandbox-only callout for cloakbrowser per SAFETY-04 + REPORT-08; Phase 4 will lift this verbatim"
  - "results/2026-05-26/INJECTIONS.md — full audit-trail for the single injection set (playwright.capability=tool-only, playwright.mode=default); scoring values byte-for-byte preserved across all 8 rows"
  - "validated scores.json — all 8 expected rows present, all valid capability tags, all 11 sub-5 cells carry valid attribution tags, lightpanda+firecrawl carry N/A semantics, browser-use dual-row schema preserved"
  - "Phase 2 verdict: PASS. Phase 3 + Phase 4 are unblocked and can run in parallel"

affects: [phase-03-cross-cutting, phase-04-synthesis, G-703, G-715, G-716, G-717, G-718, G-719, G-720, G-710]

tech-stack:
  added: []
  patterns:
    - "Audit-injection pattern: when an audit finds a missing-tag gap that the originating-plan precedent makes UNAMBIGUOUS (e.g., playwright must be tool-only per CONTEXT.md `## Decisions § Capability Tags`), inject it AS PART OF the audit AND document in INJECTIONS.md. The audit's sacrosanct invariant is that scoring VALUES are byte-for-byte preserved; tag injections that add metadata are PERMITTED and DOCUMENTED. Reusable pattern for any future cross-row audit."
    - "Two-document audit-output pattern: per-SC verdict (PHASE2_AUDIT.md) goes in BOTH .planning/ (planning-state continuity) AND results/ (user-facing audit trail). The CAPABILITY_MATRIX.md (second-view artifact) goes ONLY in results/ because Phase 4 lifts it verbatim into the public report."
    - "Sub-5-cell attribution-completeness check via Python iteration (not bash): iterate `for dim, score in row['scores'].items() if isinstance(score, (int, float)) and score < 5`. The `isinstance` guard excludes 'N/A' string sentinels (FAIRNESS-03 semantics) — they are NOT failures and must NOT be tagged as such. Codified in the plan's verify clause."
    - "FAIRNESS-04 two-view publication contract: every benchmark with mixed-tier candidates must publish (a) the same-rubric composite ranking AND (b) the capability-grouped matrix that prevents apples-to-oranges category mixing. The two are NOT alternatives; they are complements — readers must consult both. Reusable for any future multi-tier benchmark."

key-files:
  created:
    - .planning/phases/02-per-mcp-scoring-runs/PHASE2_AUDIT.md — per-SC PASS/FAIL summary across all 5 Phase 2 SCs + tag-injection inventory + attribution interpretation caveats + known limitations for Phase 4 + Linear coordination + Phase 3+4 readiness checklist
    - results/2026-05-26/PHASE2_AUDIT.md — same content as the planning copy; lives in results/ for Phase 4 lift
    - results/2026-05-26/CAPABILITY_MATRIX.md — FAIRNESS-04 second-view: per-MCP capability matrix with composites + category groupings + cross-category note + sandbox-only callout for cloakbrowser
    - results/2026-05-26/INJECTIONS.md — full audit-trail for the playwright capability+mode injection set; documents the byte-for-byte-preservation contract that was upheld
  modified:
    - results/2026-05-26/scores.json — 2-line additive diff on the playwright row (capability + mode added; ALL other fields byte-for-byte preserved across all 8 rows)
    - .planning/STATE.md — Phase 2 closed; progress updated 75%; new decision entries for plan 02-07
    - .planning/ROADMAP.md — Phase 1 + Phase 2 marked complete; Phase 3 + 4 next

key-decisions:
  - "Audit-injection scope: ONLY the missing playwright.capability + .mode fields were injected. The Phase 1 calibration row pre-dates the FAIRNESS-04 capability-tag contract; the gap is unambiguous (CONTEXT.md `## Decisions § Capability Tags` explicitly maps playwright → tool-only, and chrome-devtools + lightpanda set the mode='default' precedent for non-mode-switching MCPs). No alternative interpretation exists. Injected as part of the audit, not surfaced as a STOP."
  - "browser-use-direct attribution NOT re-attributed: the executor prompt's gotchas section flagged S4-S7 cells as potentially `target-flag` rather than `tool-bug`, but the actual existing DEEP_ANALYSIS.md (written in plan 02-05) considered the same question and chose `tool-bug` with full documentation ('the 4-element taxonomy doesn't offer target-flag for MCP-cannot-reach-the-form'). The tag was NOT missing; it was intentionally set with documented interpretive nuance. Re-attributing would CHANGE scored data (the tag IS data) and violate the audit's byte-for-byte preservation contract. Preserved as-is; PHASE2_AUDIT.md `## Attribution interpretation caveats` lifts the nuance for Phase 4 to honour."
  - "Audit-output two-document pattern: PHASE2_AUDIT.md authored in BOTH .planning/ (planning-state continuity per executor protocol) AND results/ (verify-clause expectation + Phase 4 lift). CAPABILITY_MATRIX.md authored ONLY in results/ because Phase 4 REPORT-01 lifts it verbatim into the public report."
  - "scoring/score.py SACROSANCT contract upheld: `git diff main -- scoring/score.py | wc -l` returned 0 throughout the audit. The contract carries forward to G-710 (scoring-engine PR territory) — score.py is byte-for-byte locked until then. score_with_na.py also NOT modified (adjacent-to-sacrosanct; the SKIPPED-row composite=0.0 degenerate-case fallback is a known limitation documented in PHASE2_AUDIT.md for Phase 4 to address)."
  - "Three known limitations carried forward to Phase 4 in PHASE2_AUDIT.md: (1) score_with_na.py renders SKIPPED rows as composite=0.0 — Phase 4 matrix builder must consult status field, not just composite. (2) The 4-tag taxonomy's `tool-bug` aggregator default loses MCP-fault vs. agent-fault distinction — DEEP_ANALYSIS.md per row has the interpretive nuance; Phase 4 must lift those paragraphs into recommendations.md. (3) playwright lacks per-MCP DEEP_ANALYSIS.md (Phase 1 calibration baseline) — Phase 4 should either generate one from 2026-03-31_run.md lineage or explicitly call out the asymmetry."
  - "Phase 2 verdict published as PASS with the single injection documented. Phase 3 + Phase 4 unblocked. Per ROADMAP.md execution-order note, Phase 2 + Phase 3 are designed to run in parallel — Phase 3 can begin immediately on top of the validated scores.json matrix."

requirements-completed: [FAIRNESS-04, FAIRNESS-05]

duration: 20min
completed: 2026-05-27
---

# Phase 2 Plan 07: Cross-Row Attribution Audit Summary

**Cross-cutting Phase 2 audit complete. All 5 Phase 2 success criteria
PASS. scores.json contains all 8 expected rows (7 SCORED + 1 SKIPPED)
with valid capability tags from `{tool-only, LLM-augmented,
stealth-specialist, cloud, js-light}` and all 11 sub-5 cells across
the 7 SCORED rows carry valid attribution tags from `{tool-bug,
env-mismatch, target-flag, transient}`. The audit injected exactly
ONE field set (`playwright.capability="tool-only"` +
`playwright.mode="default"` — the Phase 1 calibration row pre-dated
the FAIRNESS-04 capability-tag contract); scoring values are
byte-for-byte preserved across all 8 rows. CAPABILITY_MATRIX.md emits
the FAIRNESS-04 second-view artifact (capability-grouped, with
sandbox-only callout for cloakbrowser per SAFETY-04+REPORT-08).
PHASE2_AUDIT.md emits the per-SC PASS/FAIL summary +
tag-injection inventory + 3 known limitations carried forward for
Phase 4. `scoring/score.py` SACROSANCT contract upheld (git diff
main = 0). 176/176 Phase-1 tests still pass. **Phase 2 CLOSED.
Phase 3 + Phase 4 are unblocked and can run in parallel.**

## Per-SC verdict

| SC | Verdict | Evidence |
|----|---------|----------|
| **SC #1** — 7 evidence dirs or SKIPPED.md | **PASS** | 8 rows in scores.json: 7 SCORED (chrome-devtools, lightpanda, firecrawl, obscura, browser-use-direct, cloakbrowser, playwright Phase-1 baseline) + 1 SKIPPED (browser-use-agent) |
| **SC #2** — Read-only MCPs N/A not 0 | **PASS** | lightpanda + firecrawl both carry `interaction_depth="N/A"` (string) and `stages.S4-S8="N/A"`; score_with_na.py drops N/A from weighted denominator (verified: lightpanda composite 6.31 with denominator=13, not 5.65 with denominator=15) |
| **SC #3** — browser-use dual-mode | **PASS** | Both `browser-use-direct` (SCORED, mode="direct") AND `browser-use-agent` (SKIPPED, mode="agent") present with distinct mode field values; FAIRNESS-05 contract upheld |
| **SC #4** — Capability + attribution complete | **PASS (1 injection)** | 8/8 rows have valid capability tags after audit injection of playwright.capability="tool-only"; 11/11 sub-5 cells across 7 SCORED rows carry valid attribution tags (9 tool-bug, 2 env-mismatch, 0 target-flag, 0 transient) — no attribution injections required |
| **SC #5** — cloakbrowser loopback-only | **PASS** | results/2026-05-26/cloakbrowser/SANDBOX_PROOF.md exists; no SANDBOX_VIOLATION.md; 3-tier audit (Phase 1 active-egress: all `cloak_navigate` URLs are 127.0.0.1:8765; Phase 2 transcript hostname sweep: 10 non-loopback hostnames are CONTENT strings from snapshots, not tool-call targets; Phase 3 passive background loading documented as architectural same-as-every-Chromium-MCP) |

## Injection inventory

**One injection set. Two field additions. Zero scoring-value mutations.**

| Row | Field | Before | After | Source |
|-----|-------|--------|-------|--------|
| `playwright` | `capability` | (absent) | `"tool-only"` | CONTEXT.md `## Decisions § Capability Tags` |
| `playwright` | `mode` | (absent) | `"default"` | Precedent: chrome-devtools, lightpanda also use `mode: "default"` |

Diff scope (the entirety of audit-caused changes to scores.json):

```diff
@@ -532,6 +532,8 @@
       }
     },
     "attribution": {},
+    "capability": "tool-only",
+    "mode": "default",
     "scores": {
       "data_quality": 10,
       "error_handling": 5,
```

No attribution injections were required. The 11 pre-existing sub-5
cells across the 7 SCORED rows all already carried valid attribution
tags from their originating plans (02-01..02-05). Full inventory in
PHASE2_AUDIT.md `## Tag injections` and `## Attribution interpretation
caveats`.

## Performance

- **Duration:** ~20 min (plan start to final commit)
- **Started:** 2026-05-27T00:00Z (approx)
- **Completed:** 2026-05-27T00:05Z (approx)
- **Tasks:** 2 (cross-row validation + audit-doc emission)
- **Files modified/created:** 5 (PHASE2_AUDIT.md × 2 + CAPABILITY_MATRIX.md + INJECTIONS.md + scores.json 2-line additive diff)

## Accomplishments

1. **All 5 Phase 2 success criteria validated PASS** with per-SC evidence and PASS/FAIL summary.
2. **Single injection set executed** to repair the Phase 1 calibration row's missing capability+mode tags; scoring values byte-for-byte preserved across all 8 rows.
3. **CAPABILITY_MATRIX.md emitted** — the FAIRNESS-04 second-view artifact, ready for Phase 4 to lift verbatim.
4. **3 known limitations documented for Phase 4** — score_with_na.py SKIPPED rendering, tool-bug aggregator default's interpretive collapse, playwright DEEP_ANALYSIS.md asymmetry.
5. **SACROSANCT contract upheld** — scoring/score.py byte-for-byte unchanged; score_with_na.py also not modified (adjacent-to-sacrosanct).
6. **Phase 2 CLOSED** — orchestrator unblocked for Phase 3 + Phase 4 parallel execution.

## Task Commits

Each task committed atomically per the per-task commit protocol (`G-703:` prefix):

1. **Task 1: Cross-row validation + audit injection** — `6aef9c6`
   - `results/2026-05-26/scores.json` — 2-line additive diff on playwright row
   - `results/2026-05-26/INJECTIONS.md` — full injection inventory + audit trail
   - 2 files changed, 94 insertions

2. **Task 2: CAPABILITY_MATRIX.md + PHASE2_AUDIT.md** — `7a365ac`
   - `.planning/phases/02-per-mcp-scoring-runs/PHASE2_AUDIT.md` — per-SC PASS/FAIL summary
   - `results/2026-05-26/PHASE2_AUDIT.md` — same content for Phase 4 lift
   - `results/2026-05-26/CAPABILITY_MATRIX.md` — FAIRNESS-04 second-view artifact
   - 3 files changed, 623 insertions

**Plan metadata commit:** (next commit — this SUMMARY + STATE + ROADMAP, follows immediately)

## Files Created/Modified

### Created (5 files):
- `.planning/phases/02-per-mcp-scoring-runs/PHASE2_AUDIT.md` — per-SC verdict + tag injections + interpretive caveats + Phase-4 limitations + Linear coordination + readiness checklist
- `results/2026-05-26/PHASE2_AUDIT.md` — identical to the planning copy; lives in results/ for the plan's verify clause + Phase 4 lift
- `results/2026-05-26/CAPABILITY_MATRIX.md` — FAIRNESS-04 second-view artifact: per-MCP capability matrix + category groupings + cross-category note + sandbox-only callout
- `results/2026-05-26/INJECTIONS.md` — single-injection audit-trail: documents the byte-for-byte preservation contract that was upheld and the non-injections that were considered and rejected
- `02-07-SUMMARY.md` — this file

### Modified:
- `results/2026-05-26/scores.json` — 2-line additive diff on playwright row (capability="tool-only" + mode="default"); ALL OTHER rows byte-for-byte preserved
- `.planning/STATE.md` — Phase 2 closed; progress 75%; new decision entries; session continuity updated
- `.planning/ROADMAP.md` — Phase 1 + Phase 2 checkboxes marked; phase progress table updated

## Acceptance Criteria Status (from plan 02-07 §Acceptance)

All 10 acceptance criteria PASS:

- [x] All 8 expected rows (`playwright`, `chrome-devtools`, `lightpanda`, `firecrawl`, `obscura`, `browser-use-direct`, `browser-use-agent`, `cloakbrowser`) present in `scores.json` (scored or SKIPPED).
- [x] Every row has a valid capability tag from `{tool-only, LLM-augmented, stealth-specialist, cloud, js-light}`.
- [x] Every sub-rubric cell < 5 across all rows has an attribution tag from `{tool-bug, env-mismatch, target-flag, transient}`.
- [x] `lightpanda` + `firecrawl` show `"N/A"` (string) for S4-S8 + `interaction_depth`, not 0 or `null`.
- [x] `browser-use-direct` AND `browser-use-agent` both exist with distinct `mode` fields.
- [x] `cloakbrowser` evidence has SANDBOX_PROOF.md; no SANDBOX_VIOLATION.md.
- [x] `CAPABILITY_MATRIX.md` exists with all 5 capability categories + sandbox-only callout.
- [x] `PHASE2_AUDIT.md` exists covering all 5 Phase 2 SCs explicitly (PASS/FAIL per SC).
- [x] `scoring/score.py` byte-for-byte unchanged (`git diff main` = 0 lines).
- [x] All previously-existing rows in `scores.json` byte-for-byte unchanged (only `attribution` map injections + capability field fixes are allowed; here only the playwright row received capability+mode additions, nothing else touched).

No `PHASE2_AUDIT_FAILURES.md` was created — audit passed cleanly.

## Deviations from Plan

### Rule 2 — Auto-added (none)
No critical functionality was missing; the plan was complete.

### Rule 3 — Auto-fixed blocking issues (none)
No blocking issues encountered.

### Rule 4 — Architectural (none)
No architectural changes needed. The single injection set was a metadata-only repair (capability+mode on a row that pre-dated the FAIRNESS-04 contract); it does NOT alter the rubric, the scoring engine, or the matrix interpretation.

### Documentation deviation — audit-output location

- **Plan said:** `results/<DATE>/PHASE2_AUDIT.md`
- **Execution contract said:** `.planning/phases/02-per-mcp-scoring-runs/PHASE2_AUDIT.md`
- **Decision:** Both. The planning copy upholds the executor's planning-state-continuity expectation; the results/ copy upholds the plan's verify clause AND Phase 4's lift contract. Identical content in both files.

### Interpretation deviation — browser-use-direct attribution

- **Gotcha said:** "S4-S7 should be tagged target-flag (the fixture itself, not the MCP) — verify per 02-05 SUMMARY."
- **Audit found:** The existing tag is `tool-bug` with documented intentional reasoning in browser-use-direct DEEP_ANALYSIS.md.
- **Decision:** PRESERVE the existing tag. Re-attributing would CHANGE scored data (the tag IS data) and violate the audit's byte-for-byte preservation contract. The interpretive nuance is lifted into PHASE2_AUDIT.md `## Attribution interpretation caveats` for Phase 4 synthesis to honour rather than overwriting the originating plan's intentional choice.
- **Documented in:** INJECTIONS.md `## Non-injections (preserved as-is)` and PHASE2_AUDIT.md `## Attribution interpretation caveats`

## Linear Coordination

- **G-703 (parent):** Phase 2 complete — ready for `linearis comments create G-703 --body "Phase 2 complete: 7 MCPs evaluated (6 SCORED + 1 SKIPPED dual-mode). All 5 SCs PASS per PHASE2_AUDIT.md. Capability tags + attribution validated. Ready for Phase 3 + Phase 4."`
- Per-MCP sub-tickets (G-715..G-720) referenced in each plan's SUMMARY.md but NOT created at run time (per OUTREACH-03 ownership — same pattern as 02-03/04/05/06). DEEP_ANALYSIS.md files + this PHASE2_AUDIT.md are ready to lift into ticket comments when the per-MCP ticket sweep lands.

## Known Stubs

None. This plan emits audit documentation; no stubs introduced.

## Phase 3 + 4 readiness

- [x] Phase 3 can begin (cross-cutting measurements — uses scores.json as baseline; all 8 rows validated)
- [x] Phase 4 can wait on Phase 3 completion before synthesis; CAPABILITY_MATRIX.md is ready to lift verbatim as the FAIRNESS-04 second-view artifact

## Phase 4 Headline Candidate

> "Phase 2 closed at 7 SCORED + 1 SKIPPED rows: cloakbrowser leads at
> 8.33 (SANDBOX-ONLY by closed-binary trust model), playwright follows
> at 7.93 (calibration baseline), then lightpanda 6.31 (N/A-aware,
> denominator 13), browser-use-direct 5.87 (Vitalik headline-claim
> CONFIRMED for S1+S2+S3+S8), chrome-devtools 5.60 (SSR-rescue
> 1-of-3 discovery), firecrawl 4.23 (cloud-vs-loopback env-mismatch),
> obscura 3.27 (SSRF-guard cascade), browser-use-agent SKIPPED
> (LLM_KEY_ABSENT, re-run procedure documented). The FAIRNESS-04
> second-view (CAPABILITY_MATRIX.md) puts category context back in:
> tool-only vs LLM-augmented vs stealth-specialist vs cloud vs js-light
> — readers must consult both views to avoid the apples-to-oranges
> trap that a single composite ranking would invite."

## Self-Check: PASSED

- [x] Files created exist: `.planning/phases/02-per-mcp-scoring-runs/PHASE2_AUDIT.md`, `results/2026-05-26/PHASE2_AUDIT.md`, `results/2026-05-26/CAPABILITY_MATRIX.md`, `results/2026-05-26/INJECTIONS.md`, `02-07-SUMMARY.md`
- [x] Commits exist: `6aef9c6` (audit injection), `7a365ac` (audit docs)
- [x] All 10 plan acceptance criteria PASS
- [x] 5/5 Phase 2 SCs PASS per PHASE2_AUDIT.md
- [x] scoring/score.py byte-for-byte unchanged
- [x] 176/176 Phase-1 tests still pass
- [x] No PHASE2_AUDIT_FAILURES.md created (audit passed)
- [x] No SANDBOX_VIOLATION.md exists in cloakbrowser dir
