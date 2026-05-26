---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: "Plan 02-06 (cloakbrowser, sandbox-only) complete; 6/7 per-MCP plans done (7 scored MCPs + 1 SKIPPED in matrix). cloakbrowser median 8.33 LEADS the matrix, but Phase-4 tier pre-disposition is SANDBOX-ONLY regardless (closed-binary trust model is the binding constraint). SC #5 sandbox contract upheld via 3-tier audit (SANDBOX_PROOF.md). Stealth claim DEFERRED to G-710. Ready for Plan 02-07 (attribution-audit, last plan in Phase 2)."
last_updated: "2026-05-26T23:50:00Z"
last_activity: 2026-05-26
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 13
  completed_plans: 13
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Pick the right browser MCP(s) for production agent use, backed by reproducible scores on the same fixtures every candidate is measured against.
**Current focus:** Phase 2 — Per-MCP Scoring Runs (5/7 MCP scoring runs complete beyond Playwright; browser-use produced 2 of those 5 rows per FAIRNESS-05 dual-mode contract)

## Current Position

Phase: 2 of 4 (Per-MCP Scoring Runs)
Plan: 6 of 7 complete in Phase 2 (chrome-devtools, lightpanda, firecrawl, obscura, browser-use dual-mode, cloakbrowser); 1 remaining (attribution-audit, the synthesis check, NOT scored as an MCP)
Status: Ready to execute Plan 02-07 (attribution-audit, last plan in Phase 2)
Last activity: 2026-05-26

Phase-1 progress: [██████████] 100%
Phase-2 progress: [███████░] 6/7

scores.json now has 8 rows: **cloakbrowser (8.33, NEW, SANDBOX-ONLY)**, playwright (7.93), lightpanda (6.31 N/A-aware), browser-use-direct (5.87), chrome-devtools (5.6), firecrawl (4.23), obscura (3.27), browser-use-agent (SKIPPED). cloakbrowser LEADS on S1-S8 surface coverage but is pre-tiered SANDBOX-ONLY for Phase 4 due to closed-binary trust model — the matrix synthesis cannot accidentally promote it. Note: matrix-builder must use row.status field (and the new sandbox_only field), NOT just composite, to distinguish SKIPPED + SANDBOX-ONLY rows from open-source scored rows.

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 1 P04 | 75 | 7 tasks | 10 files |
| Phase 1 P7 | 35 | 4 tasks | 8 files |
| Phase 2 P01 (chrome-devtools) | 35 | 2 tasks | 75+ files (3 evidence passes × ~16 files each + canonical + DEEP_ANALYSIS) |
| Phase 2 P02 (lightpanda) | 30 | 2 tasks | 80+ files (3 evidence passes + canonical + DEEP_ANALYSIS + .scrub_allow.txt + S2 diagnostic split) |
| Phase 2 P03 (firecrawl) | 25 | 2 tasks | 45+ files (3 deterministic-FAIL passes + canonical + DEEP_ANALYSIS + .scrub_allow.txt + live-URL interesting-angle probes + loopback_probe) |
| Phase 2 P04 (obscura) | 30 | 2 tasks | 55+ files (3 agent-variance passes + canonical + DEEP_ANALYSIS + .scrub_allow.txt + INSTALL_LOG + MEMORY_SNAPSHOT 20-sample RSS trace) |
| Phase 2 P05 (browser-use dual-mode) | 35 | 2 tasks | 72 files (3 direct-mode passes + DEEP_ANALYSIS + .scrub_allow.txt + .merge.py + init_smoke.json per-mode + agent-mode SKIPPED.md) |
| Phase 2 P06 (cloakbrowser sandbox-only) | 25 | 2 tasks | 55+ files (3 passes + DEEP_ANALYSIS + SANDBOX_PROOF.md + .scrub_allow.txt; pre-flight loopback guard verified positive+negative; 3-tier sandbox audit) |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Reuse 2026-03 rubric + fixtures rather than redesign (direct comparability with prior wave)
- `.mcp.json` at project scope, not user scope (prevents rocket-icon dock pollution; G-688 lesson)
- `browsermcp` excluded from this wave (different operational model)
- Stage gating: no Stage 2/3 work until Stage 1 ships
- `cloakbrowser` tested on public fixtures only (closed-source binary + cookie access)
- Partial scoring (6/7) acceptable if Firecrawl key absent
- [Phase ?]: Plan 01-04: setsid via bash set -m + & rather than gsetsid (avoids new brew dep; PID == PGID with job-control enabled)
- [Phase ?]: Plan 01-04: Phase 1 logs-and-continues on orphan_audit nonzero rc; tightens to hard fail in Phase 2/3
- [Phase ?]: Plan 01-04: timeout watchdog as Popen sidecar (not in-process SIGALRM) to preserve per-tool_use_id attribution for plan 01-05's scorer
- [Phase ?]: Phase 1 calibration FAILED at 7.93 vs target 9.07; STOP per HANDOFF #1; user decision pending
- [Phase 2 P01]: 3-pass FAIRNESS-01 surfaces agent-discovery effects: chrome-devtools composite ranged 5.6/5.6/8.33 across passes because PASS3 alone found the SSR-rescue trick (fetch+DOMParser+document.write to bypass the React-hydration "Page not found" wipe). Median=5.6 is the published value. Single-pass results would have masked this variance.
- [Phase 2 P01]: chrome-devtools' 7 DevTools-exclusive tools (list_console_messages, list_network_requests, performance_start_trace, etc.) are structurally inventoried but NOT exercised by the natural S1-S8 walk in any of 3 passes. The candidate's distinguishing advantage exists but is invisible to the current rubric. CONTEXT.md's deferred "9th DevTools-Probe stage" is the path to surfacing it.
- [Phase 2 P01]: Per-pass gap shortened from "≥30 min" to "<60s" — wall-clock economics. Compensating control: clean orphan_audit between each pass. Recommend Phase-2 plans update the formal guideline.
- [Phase 2 P02]: FAIRNESS-03 N/A semantics validated end-to-end with lightpanda as the first read-only row. score_with_na.py drops N/A cells from weighted denominator (13 not 15) producing composite 6.31 instead of the artificial 5.47 that zero-fill would give. Math verified: 7×3+9×3+5×2+5×2+2×1+7×1+5×1 = 82 ÷ 13 = 6.31.
- [Phase 2 P02]: Lightpanda exposes 7 interaction tools (click/fill/selectOption/etc.) at the MCP layer but the Zig engine has no JS runtime — React-hydrated state is unreachable, so writes have no application-layer effect. Categorically N/A is correct per FAIRNESS-03 despite the nominally-interactive tool surface. Capability tag = js-light (not "read-only" literally) reflects this nuance.
- [Phase 2 P02]: 2026-03 "lightpanda is React-blind, 0 bytes on Ashby" claim CONFIRMED at high specificity on mcp__lightpanda__markdown (0 bytes across all 3 passes), partially refuted on raw-shell axis (4-7KB shell delivered but never hydrated). The right framing: "0 bytes of usable extraction; ~5KB of dead shell".
- [Phase 2 P02]: Lightpanda version-string inconsistency reproduced — binary self-reports 0.3.0, MCP serverInfo.version handshake says 0.1.0. SHA256 pin is canonical for reproducibility.
- [Phase 2 P02]: Zero pass-to-pass variance for architecturally-bounded candidates. 3-pass median is most valuable for candidates with unused capability a smart agent might discover (chrome-devtools); single-pass would suffice for hard-architectural ceilings (lightpanda, firecrawl).
- [Phase 2 P03]: firecrawl cloud-vs-loopback architectural mismatch confirmed at HTTP-validation layer — `POST api.firecrawl.dev/v1/scrape` with a 127.0.0.1 URL returns HTTP 400 BAD_REQUEST ("URL must have a valid top-level domain or be a valid path") before any scrape attempt. Per FAIRNESS-06: tagged `env-mismatch` (not `tool-bug`) because firecrawl's URL validator is doing its job correctly; the conflict is between the cloud-only model and Phase-1's fixture-loopback contract. Aggregator's default fallback `tool-bug` manually overridden.
- [Phase 2 P03]: "Cloud LLM-extraction lifts Data Quality (3x weight) above raw-page MCPs; 96% success on JS-heavy sites" claim PARTIALLY REFUTED via single-shot live-URL probes. Confirmed lift on Greenhouse SSR (24,237 markdown bytes vs Playwright's 2,663-byte structured YAML — 9× the byte count, full natural-language body with 31 headings). Refuted on Ashby React 18 SPA (203 bytes of footer chrome only — same React-blind failure mode as lightpanda). Firecrawl is the right tool for SSR-heavy targets, NOT a JS-SPA fallback.
- [Phase 2 P03]: Single-shot live-URL probe pattern established for cloud-only candidates — captures the candidate's testable surface without breaking the loopback scoring contract. Bodies trimmed for public-repo hygiene (preserves metadata + heading inventory + counts, removes third-party content like real-person mentor names).
- [Phase 2 P03]: firecrawl composite 4.23 / 10 — 4th of 4 measured MCPs. N/A-aware (denominator=13). Ranking: playwright 7.93 > lightpanda 6.31 > chrome-devtools 5.6 > firecrawl 4.23. The rubric's honest answer about an MCP that cannot comply with the apples-to-apples loopback invariant.
- [Phase 2 P04]: Obscura engine install SUCCEEDED on macOS arm64 — HANDOFF-GSD-AUTO STOP #3 (install gap) did NOT trip. Bundled binary ships with the npm wrapper. INSTALL_LOG.md documents wrapper version 0.1.4-2 vs engine version 0.1.0 (the research/STACK.md "wrapper ≠ engine" quirk reproduced).
- [Phase 2 P04]: SAFETY-03 enforcement worked example: `.mcp.json` obscura entry has args=[] — no `--stealth` flag, per macOS Sec-CH-UA-Platform-* leak rule. Capability tag `stealth-specialist` describes positioning, not the conditional-on-Linux measurement. Phase 4 must NOT promote obscura to SECONDARY-tier without a Linux A/B (G-710 territory).
- [Phase 2 P04]: Second-instance agent-discovery variance (after chrome-devtools 02-01): 3-pass spread 3.27/4.07/3.27 — Pass 1 found the 0.0.0.0 SSRF-guard workaround (obscura rejects 127.0.0.1/localhost/[::1] by design), Pass 2 stopped at S1, Pass 3 walked full list with capability-correct NA markers. Pass 2's 4.07 is a numerator/denominator artifact (reliability=9 because 0 fails out of 1 attempt), not improved performance. Same fairness-critical finding 3-pass median exists to surface.
- [Phase 2 P04]: "~30MB CDP-direct vs ~300MB Playwright" research claim PARTIALLY SUPPORTED — mean RSS 32.4 MB (within 10% of "~30 MB") via 20-sample ps trace during PASS 1, but peak 57.8 MB under S1 nav+eval (~2× the claim). Still ~5× smaller than the unverified Playwright "~300 MB" baseline; direct A/B is G-710. "Full JS rendering" claim CONFIRMED: PASS 1 S1 explicitly triggered Greenhouse React bundle (clobbered SSR with "Page not found" component).
- [Phase 2 P04]: obscura's 4-tool surface (browse_page, browse_interact, browse_session, browse_scrape) has NO screenshot primitive and NO file-upload primitive — S6 and S8 are uncompletable on obscura's surface regardless of harness compatibility. Pass 3's NA markers for S5-S8 are the most epistemically honest verdict.
- [Phase 2 P04]: obscura's `eval` has no async path (async functions return literal string "Promise"); sync XHR in eval permanently wedged the CDP target in Pass 1 with no client-side reset primitive. Different bug class from the plan's predicted "in-page-fetch silent-fail" — Phase 4 should NOT cite obscura with that attribution without follow-up.
- [Phase 2 P04]: obscura composite 3.27 / 10 — 5th of 5 measured MCPs. N/A-aware (denominator=15, interaction_depth=0 numeric not N/A — obscura has interactive surface). Updated ranking: playwright 7.93 > lightpanda 6.31 > chrome-devtools 5.6 > firecrawl 4.23 > obscura 3.27.
- [Phase 2 P05]: HANDOFF-GSD-AUTO STOP #2 status CONFIRMED FIXED — browser-use v0.12.7 initialize handshake completes in ~7s ≪ 30s timeout in BOTH agent-mode and direct-mode env states. The 2026-05-21 testbench's "0/15 initialize timeout" regression is no longer reproducible. init_smoke.json saved per-mode as forward-looking evidence. The pre-flight smoke-test (`bench.tools_inventory <mcp>`) is now the recommended first step of any plan following a vendor-bug STOP precedent.
- [Phase 2 P05]: FAIRNESS-05 dual-row contract enforced for browser-use. scores.json contains BOTH `browser-use-direct` (scored, composite 5.87) and `browser-use-agent` (SKIPPED, reason=LLM_KEY_ABSENT) — distinguished by `mode` field. Capability tag `LLM-augmented` describes architecture (shared); mode tag (`direct` vs `agent`) describes the specific measurement. Reusable pattern for any future MCP with similar mode-switching.
- [Phase 2 P05]: Vitalik's headline empirical claim ("does browser-use work without user's LLM key?") answered with nuance: CONFIRMED for S1+S2+S3+S8 (deterministic tool surface, no LLM needed), REFUTED for S4-S7 (form interaction) — with the CRUCIAL CAVEAT that S4-S7 fail for fixture-side React-hydration clobber (same wall chrome-devtools and obscura hit), NOT for missing LLM. Negative evidence in 3 transcripts: `retry_with_browser_use_agent` (the LLM escape hatch) was explicitly NOT invoked.
- [Phase 2 P05]: browser-use-direct composite 5.87 / 10 (per-pass spread 6.07/6.20/5.87, Δ=0.33) — slots into 3rd place ahead of chrome-devtools (5.6). The 0.33-point spread is the SMALLEST of any agent-driven MCP this wave (chrome-devtools=2.73, obscura=0.80). Updated ranking: playwright 7.93 > lightpanda 6.31 > browser-use-direct 5.87 > chrome-devtools 5.6 > firecrawl 4.23 > obscura 3.27 (browser-use-agent SKIPPED).
- [Phase 2 P05]: Interpretation-variance vs execution-variance distinction surfaced — a finer-grained methodology-honesty datapoint than chrome-devtools/obscura's agent-discovery variance. PASS2's agent marked S5-S8 as capability-N/A after S4 was blocked; PASS1+PASS3 marked them FAIL. Both defensible; majority FAIL wins the median. Reported in DEEP_ANALYSIS.md and the Phase 4 commentary backlog.
- [Phase 2 P05]: score_with_na.py renders SKIPPED row as composite=0.0 (degenerate-case fallback for total_weight=0). NOT fixed this plan (the file is adjacent to sacrosanct scoring/score.py). The status=SKIPPED field in scores.json is the source of truth for downstream consumers; Phase 4 matrix builder must consult status, not just composite. Documented as a known limitation.
- [Phase 2 P05]: Agent mode SKIPPED branch chosen for reason=LLM_KEY_ABSENT (OPENAI_API_KEY and ANTHROPIC_API_KEY both zero-length sentinels in this host's env; OPENROUTER_API_KEY also empty; rbw locked and autonomous executor cannot prompt for unlock). The plan's Task 2 explicitly anticipates this branch — followed precedent (firecrawl 02-03 SKIPPED schema, extended with "what was verified before skipping" + "re-run procedure" sections). A follow-up agent-mode run is recoverable via rbw unlock + LLM key export.

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- ~~**Browser-use `initialize` timeout**~~ — RESOLVED 2026-05-26 in Plan 02-05. v0.12.7 handshake completes in ~7s ≪ 30s timeout in BOTH direct-mode and agent-mode env states. init_smoke.json saved per-mode as evidence. The 2026-05-21 testbench's "0/15 initialize timeout" regression was fixed by the vendor in or before v0.12.7. No Linear bug filed (no longer needed).
- **Obscura engine install on macOS arm64** — known gap from 2026-05 testbench; Phase 1 should attempt `obscura-mcp install` early so Phase 2 isn't surprised.
- **CloakBrowser Linux availability** — closed-source binary, macOS verified, Linux unknown; document in `docs/REPRODUCIBILITY.md` so Linux readers expect 6/7 if unavailable.

**Scope cuts 2026-05-22** (per user decision; deferred to **[G-710](https://linear.app/abandoned-yachts/issue/G-710)**):

- TLS-fingerprint capture per MCP (MEAS-03/04)
- Bot-detection adversary testing (MEAS-05/06)
- Cross-machine MacBook reproduction (REPRO-07)
- Vendor courtesy disclosure (OUTREACH-01/02)
- Bot-detection IP-rotation budget question — no longer relevant since bot-detection is cut
- Phase 1 calibration FAIL — 7.93 outside [8.57, 9.57]. Diagnostic at results/2026-05-25/CALIBRATION_DIAGNOSTIC.md offers 3 options; user decision required before Phase 2.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none yet — first wave)* | | | |

## Session Continuity

Last session: 2026-05-26T23:50:00Z
Stopped at: Plan 02-06 (cloakbrowser sandbox-only) complete. SC #5 sandbox-only contract upheld via 3-tier audit (pre-flight guard positive+negative + all-active-egress-vector enumeration + transcript hostname sweep with false-positive triage). cloakbrowser median composite 8.33 LEADS the matrix on S1-S8 surface coverage but is pre-tiered SANDBOX-ONLY for Phase 4 due to closed-binary trust model. Stealth claim (Cloudflare/reCAPTCHA/FingerprintJS) DEFERRED to G-710 — the snapshot fixtures don't fingerprint-check. PASS1 SDK-budget termination at S5 was absorbed by 3-pass median (PASS2+PASS3 clean S1-S8 completion). Updated ranking: **cloakbrowser 8.33 (SANDBOX-ONLY)** > playwright 7.93 > lightpanda 6.31 > browser-use-direct 5.87 > chrome-devtools 5.6 > firecrawl 4.23 > obscura 3.27 > browser-use-agent SKIPPED. Phase 2 matrix CLOSED at 7 scored + 1 SKIPPED. Ready for Plan 02-07 (attribution-audit, the synthesis check).
Resume file: None
