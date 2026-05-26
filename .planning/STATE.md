---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: "Plan 02-03 (firecrawl) complete; 3/7 MCPs scored beyond Playwright calibration. Ready for Plan 02-04 (obscura)."
last_updated: "2026-05-26T22:10:00Z"
last_activity: 2026-05-26
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 13
  completed_plans: 10
  percent: 42
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Pick the right browser MCP(s) for production agent use, backed by reproducible scores on the same fixtures every candidate is measured against.
**Current focus:** Phase 2 — Per-MCP Scoring Runs (3/7 MCPs scored beyond Playwright)

## Current Position

Phase: 2 of 4 (Per-MCP Scoring Runs)
Plan: 3 of 7 complete in Phase 2 (chrome-devtools, lightpanda, firecrawl); 4 remaining (obscura, browser-use, cloakbrowser, attribution-audit)
Status: Ready to execute Plan 02-04 (obscura)
Last activity: 2026-05-26

Phase-1 progress: [██████████] 100%
Phase-2 progress: [███░░░░] 3/7

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

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- **Browser-use `initialize` timeout** — 2026-05 testbench showed transport mismatch on v0.12.7; Phase 2 must determine whether the bug is fixed and, if not, score 0 with a Linear bug ticket against the vendor (no courtesy-disclosure window in this wave per 2026-05-22 scope cut).
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

Last session: 2026-05-26T22:10:00Z
Stopped at: Plan 02-03 (firecrawl) complete. Median row 4.23 published in results/2026-05-26/scores.json. Ranking now: playwright 7.93 > lightpanda 6.31 > chrome-devtools 5.6 > firecrawl 4.23. Ready for Plan 02-04 (obscura).
Resume file: None
