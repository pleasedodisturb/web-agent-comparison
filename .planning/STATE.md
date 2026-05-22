---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: "Roadmap + STATE created; ready for `/gsd:plan-phase 1`"
last_updated: "2026-05-22T16:10:39.865Z"
last_activity: 2026-05-22 — Plan 01-04 complete (per-MCP driver, stage_walk prompt, orphan_audit, timeout_watchdog)
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 7
  completed_plans: 4
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Pick the right browser MCP(s) for production agent use, backed by reproducible scores on the same fixtures every candidate is measured against.
**Current focus:** Phase 1 — Harness Foundation

## Current Position

Phase: 1 of 4 (Harness Foundation)
Plan: 4 of 7 in current phase
Status: In progress
Last activity: 2026-05-22 — Plan 01-04 complete (per-MCP driver, stage_walk prompt, orphan_audit, timeout_watchdog)

Progress: [██████░░░░] 57%

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

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none yet — first wave)* | | | |

## Session Continuity

Last session: 2026-05-22T16:10:26.812Z
Stopped at: Roadmap + STATE created; ready for `/gsd:plan-phase 1`
Resume file: None
