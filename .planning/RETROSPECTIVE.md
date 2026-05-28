# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MCP-layer browser-server benchmark

**Shipped:** 2026-05-28
**Phases:** 5 | **Plans:** 30 | **Tasks:** ~50+

### What Was Built

- **Reproducible 7-MCP benchmark** scored on the locked 8-dimension rubric (composite 0-10), with both per-MCP composite ranking (playwright 7.93 leads tool-only; cloakbrowser 8.33 leads overall but SANDBOX-ONLY; lightpanda 6.31 read-only specialist) and per-stage S1-S8 matrix.
- **Stage 2 graduation gate** at `results/recommendations.md` — explicit 4-tier matrix (PRIMARY / SECONDARY / SANDBOX-ONLY / SKIP) that unblocks the private `terminal-craft` toolkit.
- **Cross-cutting measurements** for all 7 MCPs: cold-start 3-segment (resolve/spawn/first_useful; lightpanda 13ms vs browser-use 668ms = 51× spread), token efficiency 3-scope (schema/payload/turn; 7.3× spread among scored rows), 1hr stability with 0-orphan audit, per-stage tool-call counts, tool-surface inventory with 6-category breakdown.
- **Reproducibility manifest** — `versions.lock.md`, `versions.json`, per-MCP binary SHA256s, `uv.lock`, `package-lock.json`, per-run `MACHINE.md`, plus `docs/REPRODUCIBILITY.md` third-party recipe.
- **Sacrosanct-invariants framework** — `bench/wave_close_check.py` proved `scoring/score.py`, `scoring/rubric.md`, `.mcp.json` byte-for-byte unchanged from main throughout the entire wave; SAFETY-05 audit confirmed candidate_count=7, rubric_columns=8, 0 terminal-craft commits.
- **Phase 5 governance-debt closer** — retroactive 03-VERIFICATION.md, REQUIREMENTS.md 45/45 Complete sweep, Phase 4 plan SUMMARY.md backfill, recommendations.md date drift fix — milestone archived as `complete` rather than `tech_debt`.

### What Worked

- **Median-of-3 with single-shot exceptions for architecturally-bounded candidates.** 3-pass surfaced agent-discovery variance (chrome-devtools 5.6/5.6/8.33 — PASS3 alone found the SSR-rescue trick); single-pass would have masked that finding. For lightpanda/firecrawl (hard architectural ceilings), single-pass would have sufficed. Worth keeping as a rubric default for the next wave.
- **Scope cut 2026-05-22.** Cutting TLS-fingerprint + bot-detection + cross-machine + vendor disclosure (52 → 45 requirements) kept v1.0 shippable without inventing fake completion criteria. Moved cleanly to G-710 follow-up wave anchor.
- **Sacrosanct-invariant enforcement at every plan boundary.** `bench/wave_close_check.py` re-run after every plan caught zero violations across 30 plans — proves the rubric/scoring code stayed locked even under high-velocity edit pressure.
- **Two-layer verification in Phase 5.** In-plan self-verifier (05-VERIFICATION.md from gsd-verifier methodology applied inline) + independent orchestrator-level audit (VERIFICATION-AUDIT.md, 11/11 spot-checks PASS) caught what a single check couldn't — surfaced (not buried) the SAFETY-03 DEFERRED-TO-G-710 judgment call from Plan 05-04's sweep.
- **N/A-aware composite scoring.** `score_with_na.py` correctly dropped N/A cells from weighted denominator for read-only candidates (lightpanda 6.31 with denominator=13 vs zero-fill's artificial 5.47); honest representation of partial-rubric coverage.

### What Was Inefficient

- **3 of 6 Phase 4 plans shipped without SUMMARY.md initially.** Plans 04-01, 04-02, 04-03 had commits but no plan-level summaries — caught only at v1.0 audit. Phase 5 backfilled, but the pattern should have been enforced as a plan-completion gate, not a post-hoc audit fix.
- **REQUIREMENTS.md §Traceability mass-staleness.** 31 of 45 rows said `Pending` despite phase VERIFICATION.md files satisfying them — pure index drift. The phase VERIFICATION.md files were the source of truth, but the traceability table never got synced as VERIFICATIONs landed. Phase 5 swept it; future waves should sync the table during phase close, not at milestone close.
- **Phase 3 lacked a formal VERIFICATION.md** until Phase 5 backfilled. The work was observably done (every MEAS-* requirement had live artifacts that Phase 4 ingested) but the goal-backward verification artifact was missing. Other phases (1, 2, 4) all had one — 3 was the odd one out.
- **Date drift in `bench/build_recommendations.py`.** Two string literals hardcoded "2026-05-28" instead of a single source-of-truth constant — drift slipped into the published `results/recommendations.md` L3+L7. Caught by v1.0 audit. The root-cause fix in Phase 5 set the literals correctly; a constant would have been better.
- **Linear API unreachable in autonomous executor session.** External Linear closure (G-703 + G-714..G-720 + G-721) had to be deferred to a manual follow-up because `linearis` CLI wasn't accessible to the autonomous executor and the global rule forbids `mcp__plugin_linear_linear__*` in local sessions. Forced a 4-of-5 debt closure rather than 5-of-5.
- **`browser-use-agent` SKIPPED.** OPENAI_API_KEY / ANTHROPIC_API_KEY / OPENROUTER_API_KEY all empty at measurement time + rbw locked + autonomous executor couldn't prompt for unlock. Documented as re-runnable but a real measurement gap.

### Patterns Established

- **Sacrosanct-invariants auditor as a plan-boundary gate.** `bench/wave_close_check.py` should be the template for future waves — name the things that must NOT change (rubric, scoring code, candidate count) and audit them at every plan boundary, not just at wave close.
- **Decimal-phase insertion for governance-debt closure.** Phase 5 demonstrated that v1.0 could be archived as `complete` (not `tech_debt`) by inserting a closer phase rather than punting items to v1.1. The pattern: milestone audit identifies debt → insert a phase with a tightly-scoped goal → close 4-of-5 inline, defer the rest with explicit deferral notes.
- **`gsd-verifier` retroactively for missing VERIFICATION.md.** The same subagent (or methodology) that produces forward-looking verifications can be applied retroactively to closed phases that shipped without one. Phase 5 Plan 05-01 proved the pattern works without re-executing the original plans.
- **Plan-level SUMMARY.md as a non-negotiable per-plan deliverable.** Going forward, no plan should ship without a SUMMARY.md — it should be a plan-completion gate, not a post-hoc backfill artifact.
- **Two-layer verification (in-plan + independent).** Phase 5's self-verification followed by an independent orchestrator-level audit caught nuance (the SAFETY-03 caveat) that a single layer would have buried.
- **Empirical N/A semantics with documented `env-mismatch` tags.** firecrawl's cloud-vs-loopback architectural mismatch was tagged `env-mismatch` (not `tool-bug`) — preserves the distinction between "the tool is broken" and "the tool's model doesn't fit this rubric's harness contract."

### Key Lessons

1. **Define plan-completion gates upfront** — SUMMARY.md, VERIFICATION.md (per phase), and REQUIREMENTS.md traceability sync should be hard gates, not post-hoc audit findings. v1.0 ate 3 of these.
2. **Use a single source-of-truth constant for wave-locked values** (dates, candidate counts, rubric column count). Two hardcoded string literals in `bench/build_recommendations.py` caused the L3+L7 date drift.
3. **Score architecturally-bounded candidates differently than agent-driven ones.** 3-pass median is most valuable when there's an unused capability a smart agent might discover (chrome-devtools); single-pass suffices for hard ceilings (lightpanda, firecrawl). The wave's 3-pass default was right but worth codifying.
4. **Scope cuts mid-wave are healthy when they're documented.** 52 → 45 requirements at 2026-05-22 with G-710 anchor was a clean cut. Don't be afraid to defer; do be afraid of silent scope drift.
5. **Autonomous executor sessions can't do everything.** Linear API closure (and any external system that requires session credentials the autonomous flow can't reach) must be flagged as deferred-to-manual at the start, not discovered at milestone close.
6. **Insert a debt-closer phase before milestone archive** if a milestone audit finds non-blocking debt. v1.0 demonstrated this gets the milestone to `complete` rather than `tech_debt` without changing scope.
7. **The honest answer for cloud-only MCPs against a loopback harness is `env-mismatch`, not `tool-bug`.** firecrawl's URL validator correctly rejected 127.0.0.1 — that's not a bug, it's a contract mismatch. Preserve this distinction in attribution tags.
8. **Closed-binary trust + cookie access = SANDBOX-ONLY tier even if the scoring is high.** cloakbrowser at composite 8.33 leads the matrix but is pre-tiered SANDBOX-ONLY. Composite alone cannot drive graduation tier — the trust model is a separate axis.

### Cost Observations

- **Model mix:** ~50% opus (planning, verification, orchestration) / ~50% sonnet (execution). No haiku used this wave; future waves may benefit from haiku for simple classification (e.g., capability-tag assignment from per-MCP run output).
- **Sessions:** Multiple; precise count not tracked in artifacts. Phase 5 alone ran the full plan→execute→verify chain in a single autonomous session with 5 gsd-executor dispatches + 1 plan-checker iter 2 + 1 phase-verifier audit.
- **Notable efficiency:** Phase 5 closed 4 audit debt items in ~2 hours total across 5 plans. The two-layer verification (in-plan + independent) added marginal cost but caught the SAFETY-03 caveat surfacing — worth the extra dispatch.
- **Sacrosanct-invariants auditor as a near-free guardrail:** `bench/wave_close_check.py` ran at every plan boundary across 30 plans (5 phases × 6 plans avg) with zero violations and negligible overhead. The cost-per-check is dominated by the editor confirming `all_pass=True`, not by the auditor itself.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 30 | First milestone — established sacrosanct-invariants auditor pattern; introduced decimal-phase debt-closer (Phase 5) before milestone archive |

### Cumulative Quality

| Milestone | Tests | Coverage | Sacrosanct Invariants Held |
|-----------|-------|----------|---------------------------|
| v1.0 | 309/309 baseline | wave_close_check `all_pass=True` | scoring/score.py, scoring/rubric.md, .mcp.json byte-for-byte unchanged from main throughout |

### Top Lessons (Verified Across Milestones)

1. **Sacrosanct-invariants enforcement at every plan boundary works** — v1.0 ran the auditor 30+ times across the wave with zero false positives and zero missed violations. Carry into v1.1.
2. **Documentation symmetry must be a plan-completion gate, not a milestone-close audit finding.** v1.0 had to backfill 3 SUMMARY.md files + 1 VERIFICATION.md + sweep 31 REQUIREMENTS.md rows at milestone close. Future milestones should fail plan close (not just milestone close) if these are missing.
