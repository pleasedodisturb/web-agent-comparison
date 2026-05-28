---
phase: 04-synthesis
verified: 2026-05-28T00:00:00Z
status: passed
score: 5/5 success criteria + 16/16 requirements verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 4: Synthesis Verification Report

**Phase Goal:** The public-facing artifacts (`2026-05-27-mcp-comparison.md`, `recommendations.md`, README headline verdict) ship with the methodology disclaimer, dual-view matrix, per-MCP deep analysis, and explicit Stage 2 graduation tiers — unblocking Stage 2 and pointing to G-710 for the deferred detection-resilience follow-up.

**Verified:** 2026-05-28
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Success-Criteria Truths (from ROADMAP.md Phase 4)

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| SC1 | `results/2026-05-27-mcp-comparison.md` has 8-dim weighted score table (7 MCPs × 8 dims + composite), S1-S8 × 7 MCPs stage matrix with distinct `N/A` and `UNTESTED` cells, per-MCP "Deep Analysis" stanzas, methodology section + disclaimer header, 2026-03 → 2026-05 overlay, "Negative Results" section, partial-run disclosure, sandbox callouts on every cloakbrowser mention, Linear traceability footer | ✓ VERIFIED | Report 1714 lines. Headings: `## Weighted Composite Score Table (REPORT-01)` (L59), `## Stage Matrix (REPORT-02)` (L74), `## Methodology disclaimer` (L30), `## Methodology` (L35), `## Per-MCP Deep Analysis (REPORT-03)` (L227) with all 7 MCP stanzas (playwright L231, browser-use L256 — split direct/agent, chrome-devtools L670, lightpanda L836, obscura L955, firecrawl L1164, cloakbrowser L1304), `## 2026-03 → 2026-05 overlay (REPORT-11)` (L1669), `## Negative Results` (L1681), `## Linear traceability` (L1707). Cell legend at L90 distinguishes `N/A`, `UNTESTED`, `SKIPPED`. 31 sandbox-only callouts surround cloakbrowser mentions; idempotency verified (running inject_sandbox_callouts twice yields identical output). Partial-run disclosure at L27 (browser-use-agent SKIPPED). |
| SC2 | `results/recommendations.md` publishes the explicit Stage 2 graduation tiers (PRIMARY / SECONDARY / SANDBOX-ONLY / SKIP) for each of the 7 MCPs; the repo README is updated with the headline verdict + methodology summary + link to recommendations | ✓ VERIFIED | recommendations.md L9 `## PRIMARY` (playwright 7.93, lightpanda 6.31), L30 `## SECONDARY` (browser-use-direct 5.87, chrome-devtools 5.60, firecrawl 4.23), L59 `## SANDBOX-ONLY` (cloakbrowser 8.33), L79 `## SKIP` (obscura 3.27, browser-use-agent SKIPPED). README L7 `## Headline verdict`, L11-16 tier table identical to recommendations, L20 `## Methodology summary`, L48 link to `results/recommendations.md`. Tier assignments match CONTEXT.md locked decisions exactly. |
| SC3 | Reproducibility manifest (versions.lock.md + versions.json + per-MCP binary SHA256s + uv.lock + package-lock.json + per-run MACHINE.md) is committed; `bench/capture_versions.py` produced versions.json from the live environment | ✓ VERIFIED | `results/2026-05-27/versions.json` (66 lines, captured_at 2026-05-27T22:00:43Z, all 7 MCP SHA256s present), `results/2026-05-27/versions.lock.md` (35 lines, Node v26.0.0 / Python 3.14.5 / uv 0.11.16 / per-MCP SHA256 table), `results/2026-05-27/MACHINE.md` (58 lines, PII-clean per public-repo hygiene). `uv.lock` (65033 bytes) + `package-lock.json` (178812 bytes) both git-tracked (`git ls-files uv.lock package-lock.json` returns both). |
| SC4 | `results/recommendations.md` has a "Future Waves" section pointing to G-710 (bot-detection + TLS-fingerprint follow-up) as the explicit next-wave anchor | ✓ VERIFIED | recommendations.md L102 `## Future Waves` heading; L104 says "the explicit next-wave anchor is [**G-710**](https://linear.app/abandoned-yachts/issue/G-710) — bot-detection + TLS-fingerprint follow-up that REUSES this wave's harness". G-710 also linked in README L76. |
| SC5 | A wave-close ritual confirms no scope-creep snuck in (candidate count unchanged, rubric column count unchanged, no Stage 2 commits in terminal-craft) | ✓ VERIFIED | `WAVE_CLOSE_AUDIT.md` (57 lines, ALL CHECKS PASS): candidate_count=7, rubric_columns=8, terminal_craft_commits=0, no_new_mcps=True. Auditor re-runs cleanly (`python3 -m bench.wave_close_check` returns `all_pass=True`). `git diff main -- scoring/score.py scoring/rubric.md .mcp.json` returns 0 lines (sacrosanct invariants preserved). |

**Score:** 5/5 success criteria verified.

### Required Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| REPRO-01 | versions.lock.md + versions.json + per-MCP SHA256s + Node/uv/Python/OS/arch from bench/capture_versions.py | ✓ SATISFIED | `results/2026-05-27/versions.json` lines 4-9 (host), 11-56 (per-MCP SHA256s), 59-63 (tooling) |
| REPRO-03 | MACHINE.md per `results/<date>/` records machine specs / NTP-synced timestamp; methodology section cites it | ✓ SATISFIED | `results/2026-05-27/MACHINE.md` exists; report L56 cites it: "pinned in `results/2026-05-27/MACHINE.md`" |
| REPRO-06 | `docs/REPRODUCIBILITY.md` documents `make bench` command, FIRECRAWL_API_KEY note, CloakBrowser Linux uncertainty | ✓ SATISFIED | `docs/REPRODUCIBILITY.md` (231 lines): § Prerequisites (L15), § Installing 7 MCPs (L37), § API keys (L62), § Running the comparison (L87), § cloakbrowser sandbox-only (L126), § Cross-machine parity disclosure (L150) |
| REPORT-01 | 8-dim weighted score table (7 MCPs × 8 dims + composite) | ✓ SATISFIED | Report L59-72: 8 score rows × 8 dimensions + composite column |
| REPORT-02 | Stage matrix (S1-S8 × 7 MCPs); N/A and UNTESTED distinct | ✓ SATISFIED | Report L74-90: 8 rows × 8 stages + cell legend at L90 distinguishing PASS/FAIL/PARTIAL/N/A/UNTESTED/SKIPPED |
| REPORT-03 | Per-MCP "Deep Analysis" stanza (3-6 strengths + weaknesses + verdict + interesting angle) for each of 7 MCPs | ✓ SATISFIED | 7 Deep Analysis sections present (playwright L231, browser-use L256, chrome-devtools L670, lightpanda L836, obscura L955, firecrawl L1164, cloakbrowser L1304). Browser-use covers both direct + agent (SKIPPED) modes |
| REPORT-04 | Methodology section explains rubric/fixtures/harness/measurement/reproducibility; cites MACHINE.md | ✓ SATISFIED | `render_methodology_section` (build_report.py L392-468) emits the heading + 6 subsections + MACHINE.md citation. Rendered output at report L35-56 |
| REPORT-05 | Methodology disclaimer header stating "evaluated as of <date> with configuration <X>; not intrinsic tool quality" | ✓ SATISFIED | Report L30-32: "evaluated on **2026-05-27**...**not intrinsic tool quality**...Treat it as a baseline for the methodology" |
| REPORT-06 | recommendations.md contains Stage 2 graduation recommendation with 4 tiers; IS the Stage 2 unblock gate | ✓ SATISFIED | recommendations.md L9/30/59/79 (4 tiers); L114 "this recommendations file IS the Stage-2 unblock gate" |
| REPORT-07 | README.md updated with headline verdict, methodology summary, link to recommendations.md | ✓ SATISFIED | README L7 (Headline verdict + tier table), L20 (Methodology summary), L48 (link to recommendations.md) |
| REPORT-08 | Every cloakbrowser mention carries `**Sandbox only — do not point at authenticated sessions**` callout | ✓ SATISFIED | 31 sandbox-only callouts saturate the cloakbrowser section in the report; inject_sandbox_callouts pass is idempotent (verified by running twice) |
| REPORT-09 | Partial-run disclosure if SKIPPED; report does NOT silently emit 6/7 | ✓ SATISFIED | Report L27 disclosure for browser-use-agent SKIPPED. Firecrawl was NOT skipped (scored 4.23) so the conditional doesn't fire for that row — SKIPPED row composite renders as `SKIPPED` not `0.0` (L72) |
| REPORT-10 | "Negative Results" section explicitly documents what didn't work | ✓ SATISFIED | Report L1681-1693: 5 numbered findings (firecrawl loopback-incompat, obscura macOS leak, browser-use-agent SKIPPED, chrome-devtools DevTools-exclusive unexercised, playwright cross-cut date gap) |
| REPORT-11 | 2026-03 → 2026-05 overlay on overlapping technologies | ✓ SATISFIED | Report L1669-1678 (Playwright overlay 9.07 → 7.93 with fixture-sourcing delta interpretation) |
| REPORT-12 | Linear traceability footer cites G-703 + per-MCP sub-tickets | ✓ SATISFIED | Report L1707-1713: G-703 umbrella + G-715..G-720 per-MCP sub-tickets + G-710 future-wave anchor |
| SAFETY-05 | Wave-close ritual audits scope-creep | ✓ SATISFIED | `WAVE_CLOSE_AUDIT.md` ALL PASS; `bench/wave_close_check.py` + 27 tests passing |

**16/16 phase requirements satisfied.**

### Locked Decisions Compliance (from 04-CONTEXT.md)

| Decision | Status | Evidence |
|----------|--------|----------|
| Stage 2 tiers exactly: PRIMARY={playwright, lightpanda}, SECONDARY={browser-use-direct, chrome-devtools, firecrawl}, SANDBOX-ONLY={cloakbrowser}, SKIP={obscura, browser-use-agent} | ✓ MATCHES | recommendations.md tiers match exactly; README L11-16 tier table matches exactly; report L22-25 tier preview matches exactly |
| Report filename = `results/2026-05-27-mcp-comparison.md` | ✓ MATCHES | File exists at correct path (1714 lines) |
| Recommendations at `results/recommendations.md` | ✓ MATCHES | File exists at correct path (130 lines) |
| 3 carried-forward limitations disclosed: SKIPPED composite=0.0 sentinel, transport-PASS stability, playwright cross-cut date gap | ✓ ALL 3 PRESENT | Report L1696-1704 numbered list of 3 limitations |

### BLOCKER Fixes from plan-checker Iteration 2

| Blocker | Status | Evidence |
|---------|--------|----------|
| BLOCKER 1: uv.lock + package-lock.json git-tracked | ✓ FIXED | `git ls-files uv.lock package-lock.json` returns both files; files exist (uv.lock 65033 bytes, package-lock.json 178812 bytes) |
| BLOCKER 2: render_methodology_section emitted with body + MACHINE.md citation | ✓ FIXED | `render_methodology_section` at build_report.py L392-468 emits 6 subsections + MACHINE.md citation. Rendered into report L35-56 |
| BLOCKER 3: browser-use Direct mode + Agent mode (SKIPPED) subsections | ✓ FIXED | Report L260 `### Direct mode`, L617 `### Agent mode (SKIPPED)`; full SKIPPED narrative lifted from `results/2026-05-26/browser-use-agent/SKIPPED.md` |
| BLOCKER 4: inject_sandbox_callouts idempotent | ✓ FIXED | `inject_sandbox_callouts(inject_sandbox_callouts(md)) == inject_sandbox_callouts(md)` verified live; docstring at build_report.py L241-248 explicitly states idempotency contract |
| BLOCKER 5: README headline = 7 candidates with FAIRNESS-05 footnote | ✓ FIXED | README L9 "7 MCP candidates"; L18 footnote `[^1]: browser-use produces TWO scored rows...per FAIRNESS-05` |

### Sacrosanct Invariants

| Invariant | Status | Evidence |
|-----------|--------|----------|
| `scoring/score.py` unchanged from main | ✓ HOLDS | `git diff main -- scoring/score.py` returns 0 lines |
| `scoring/rubric.md` unchanged from main | ✓ HOLDS | `git diff main -- scoring/rubric.md` returns 0 lines |
| `.mcp.json` unchanged from main | ✓ HOLDS | `git diff main -- .mcp.json` returns 0 lines |

### Test Suite Health

| Module | Tests | Status |
|--------|-------|--------|
| `tests/test_build_report.py` | covers render_executive_summary, render_methodology_section, render_methodology_disclaimer, inject_sandbox_callouts (idempotency), render_score_table, render_stage_matrix, render_overlay, render_negative_results, render_deep_analysis, etc. | ✓ PASSING |
| `tests/test_build_recommendations.py` | covers tier assignment, render per tier, future-waves section, G-710 anchor | ✓ PASSING |
| `tests/test_wave_close_check.py` | 27 tests covering candidate_count, rubric_columns, terminal_craft_commits (refined semantics), no_new_mcps, render_audit_md | ✓ PASSING |
| **Combined run** | `pytest tests/test_build_report.py tests/test_build_recommendations.py tests/test_wave_close_check.py -q` | ✓ **68 passed in 0.10s** |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| build_report CLI is invokable | `python3 -m bench.build_report --help` | Help output with all 6 args (--scores, --cross-cut, --capability, --deep-dir, --run-date, --out) | ✓ PASS |
| build_recommendations CLI is invokable | `python3 -m bench.build_recommendations --help` | Help output with --scores + --out | ✓ PASS |
| wave_close_check produces all-pass audit | `python3 -m bench.wave_close_check` | `wave_close_check: candidate_count=7 rubric_columns=8 terminal_craft_commits=0 no_new_mcps=True all_pass=True` | ✓ PASS |
| inject_sandbox_callouts is idempotent on real report | Apply twice, compare | True (no change on second pass; matches committed file byte-for-byte) | ✓ PASS |
| All 68 tests pass | `pytest tests/test_build_report.py tests/test_build_recommendations.py tests/test_wave_close_check.py -q` | `68 passed in 0.10s` | ✓ PASS |

### Anti-Patterns Found

None. Greps for `TBD|FIXME|XXX` and `TODO|HACK|PLACEHOLDER` against all modified files (`bench/build_report.py`, `bench/build_recommendations.py`, `bench/wave_close_check.py`, `results/2026-05-27-mcp-comparison.md`, `results/recommendations.md`, `README.md`, `docs/REPRODUCIBILITY.md`) return zero matches.

### Minor Observations (Non-Blocking)

- **Date inconsistency in recommendations.md** (cosmetic, not a gap): `results/recommendations.md` line 3 and 7 say "Evaluated as of 2026-05-28" but the comparison report file, CONTEXT.md, MACHINE.md, and versions.json all say 2026-05-27. The file was regenerated on 2026-05-28 (today). The 2026-05-27 date in the report and manifest is the locked wave date, so this is a minor inconsistency in the recommendations narrative but does not affect tier assignments, evidence citations, or the headline verdict. Not blocking SC2 because the tier assignments, candidate count, and recommendation content remain correct and traceable to the locked CONTEXT.md decisions.
- **SUMMARY.md asymmetry**: Plans 04-01, 04-02, 04-03 have commits in git log but no `-SUMMARY.md` files (only 04-04, 04-05, 04-06 do). This does not affect the phase goal since the artifacts they produced (versions manifest, docs/REPRODUCIBILITY.md, build_report.py + tests + the report itself) all exist and pass goal-backward verification. Plan-level summary documentation is informational governance, not a goal-achievement criterion.

### Gaps Summary

No gaps. All 5 phase success criteria, all 16 phase requirement IDs, all 4 locked CONTEXT.md decisions, all 5 plan-checker BLOCKER fixes, all 3 sacrosanct invariants, all 5 behavioral spot-checks, and the full test suite pass.

The phase goal is observably achieved in the codebase:

- **The three public-facing artifacts ship** (`results/2026-05-27-mcp-comparison.md`, `results/recommendations.md`, README headline verdict).
- **Methodology disclaimer, dual-view matrix (composite + capability), per-MCP deep analysis (all 7 MCPs), and explicit Stage 2 graduation tiers** are all present with locked tier assignments matching CONTEXT.md.
- **Stage 2 is unblocked** — recommendations.md is the gate; the wave-close audit confirms zero Stage 2 commits in this repo.
- **G-710 is the named follow-up anchor** in both the report (Negative Results + Linear traceability footer) and recommendations.md (Future Waves section) and README (Future waves section).

---

_Verified: 2026-05-28_
_Verifier: Claude (gsd-verifier)_
