# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** Pick the right browser MCP(s) for production agent use, backed by reproducible scores on the same fixtures every candidate is measured against.
**Current focus:** Phase 1 — Harness Foundation

## Current Position

Phase: 1 of 4 (Harness Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-05-22 — Roadmap created, 52 v1 requirements mapped across 4 phases

Progress: [░░░░░░░░░░] 0%

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

Last session: 2026-05-22
Stopped at: Roadmap + STATE created; ready for `/gsd:plan-phase 1`
Resume file: None
