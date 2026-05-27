# Roadmap: web-agent-comparison Wave 2 (MCP-layer browser-server benchmark)

## Overview

This wave produces a public, reproducible comparison of 7 MCP-layer browser servers (playwright, browser-use, chrome-devtools, lightpanda, obscura, firecrawl, cloakbrowser) scored on the locked 8-dimension rubric + S1-S8 fixtures inherited from the 2026-03-31 app-level wave. The end product is a comparison report + explicit Stage 2 graduation recommendation; it is the gate that unblocks the private terminal-craft toolkit (Stage 2) and the Kestrel/Eyas production agents (Stage 3).

The work is **horizontally layered** (`PROJECT_MODE=standard`): harness foundation must land coherently before any MCP runs, per-MCP scoring and cross-cutting measurements (cold-start / token efficiency / 1hr stability / tool-call counting) run in parallel against the same harness, and synthesis closes the wave. A vertical-MVP slice would force premature scoring decisions before the harness reproduces the known 2026-03 Playwright result, and would collapse the parallelism that lets Phases 2 + 3 overlap.

**Scope cut 2026-05-22:** TLS-fingerprint capture + bot-detection adversary testing + cross-machine MacBook reproduction + vendor courtesy disclosure were cut from v1 — Greenhouse/Ashby targets don't fingerprint-check, and the work doesn't bear on the Kestrel/Eyas use case. Detection + fingerprint work moved to follow-up wave **[G-710](https://linear.app/abandoned-yachts/issue/G-710)** which reuses this wave's harness once it ships and adds the anti-captcha.com integration.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Harness Foundation** - Build the runner, snapshot fixtures, retry gate, scrub pipeline, and version-lock infrastructure; reproduce 2026-03 Playwright score as go/no-go gate
- [x] **Phase 2: Per-MCP Scoring Runs** - Score all 7 MCPs end-to-end on S1-S8 with median-of-3 retry, capability tags, and per-row failure attribution
- [x] **Phase 3: Cross-Cutting Measurements** - Capture cold-start (3-segment), token efficiency (3-scope), 1hr stability, per-stage tool-call count, and per-MCP tool-surface inventory (completed 2026-05-27)
- [ ] **Phase 4: Synthesis** - Publish scored matrix + recommendations.md + README verdict; reproducibility manifest committed

## Phase Details

### Phase 1: Harness Foundation
**Goal**: A user can drive one Claude Code session per MCP through the locked S1-S8 prompt, capture self-contained evidence directories, and reproduce the 2026-03 Playwright composite within ±0.5 — proving the harness measures what the wave needs to measure before any other MCP is added.
**Depends on**: Nothing (first phase; pure scaffolding)
**Requirements**: HARNESS-01, HARNESS-02, HARNESS-03, HARNESS-04, HARNESS-05, HARNESS-06, HARNESS-07, HARNESS-08, HARNESS-09, FAIRNESS-01, FAIRNESS-02, FAIRNESS-03, FAIRNESS-06, FAIRNESS-07, REPRO-02, REPRO-04, REPRO-05, SAFETY-01, SAFETY-02, SAFETY-03, SAFETY-04, OUTREACH-03
**Success Criteria** (what must be TRUE):
  1. `make bench-playwright && make score` reproduces a Playwright composite within ±0.5 of the 2026-03-31 baseline (9.07) against the self-hosted snapshot fixtures — the harness's go/no-go gate.
  2. `make bench-playwright` writes a complete evidence directory at `results/<date>/playwright/` containing `transcript.md`, `raw_stream.jsonl`, `stage_s*.{yml,md,png,txt}`, `cold_start.json` (stub OK), `tokens.json`, `tls.json` (stub OK), `stability.log` (stub OK), and `orphan_audit.log` showing 0 surviving processes.
  3. `scripts/check_prereqs.sh` detects every missing MCP binary in `.mcp.json`, exits non-zero with a one-line remediation per gap, and is the first step of `make bench`.
  4. Inducing any taxonomied transient failure (kill the MCP child mid-S5; block `tls.peet.ws` via `/etc/hosts`) triggers `bench/transient.py` to retry the affected stage twice more and records median pass-count in `raw.jsonl` instead of failing the run.
  5. Attempting to commit a `.mcp.json` with an inline literal API key (`"FIRECRAWL_API_KEY": "fc-..."`) is blocked by the pre-commit hook with an explicit message; `${VAR}` references pass cleanly. G-703 is split into per-MCP sub-tickets + 1 synthesis ticket in Linear before any Phase 2 work begins.
**Plans**: TBD
**UI hint**: no

### Phase 2: Per-MCP Scoring Runs
**Goal**: Every one of the 7 MCPs has a complete evidence directory + populated `scores.json` row with median-of-3 results, correct N/A semantics for read-only candidates, capability-category tags, and a failure-attribution tag for any sub-rubric score < 5 — turning the harness into 7 comparable, defensible rows.
**Depends on**: Phase 1 (harness validated against Playwright)
**Requirements**: FAIRNESS-04, FAIRNESS-05
**Success Criteria** (what must be TRUE):
  1. `results/<date>/` contains a complete evidence subdirectory for all 7 MCPs (`playwright`, `browser-use`, `chrome-devtools`, `lightpanda`, `obscura`, `firecrawl`, `cloakbrowser`) — or, for Firecrawl-without-API-key and any install-gap MCP, an explicit `SKIPPED.md` documenting the reason per the partial-run pattern.
  2. Read-only MCPs (`lightpanda`, `firecrawl`) show `N/A` (not `0`) for S4-S8 in the stage matrix; `scoring/score.py` drops `N/A` cells from the weighted denominator so their composite reflects only attempted dimensions.
  3. `browser-use` produces two rows in `scores.json` — `browser-use-direct` (no LLM key) and `browser-use-agent` (LLM key enabled) — each labeled with mode and scored independently.
  4. Every matrix row carries an explicit capability tag (`tool-only` / `LLM-augmented` / `stealth-specialist` / `cloud` / `js-light`) and any sub-score < 5 has a failure-attribution tag from the taxonomy (`tool-bug` / `env-mismatch` / `target-flag` / `transient`).
  5. The `cloakbrowser` evidence directory contains zero requests to any hostname other than `127.0.0.1`; the harness refuses to spawn it against any other target.
**Plans**: TBD
**UI hint**: no

### Phase 3: Cross-Cutting Measurements
**Goal**: Every MCP has the new-this-wave measurement artifacts (cold-start, token efficiency, 1hr stability, per-stage tool-call counts, tool-surface inventory) captured with discipline that prevents the measurement-attribution traps (single-shot cold-start, token-scope confusion, orphan-induced stability failures) — runs in full parallel with Phase 2 on the shared harness.
**Depends on**: Phase 1 (harness + `.mcp.json` reading + per-MCP output convention); parallel with Phase 2
**Requirements**: MEAS-01, MEAS-02, MEAS-07, MEAS-08, MEAS-09
**Success Criteria** (what must be TRUE):
  1. Every MCP's `cold_start.json` contains the 3-segment split (`t_resolve` / `t_spawn` / `t_first_useful`) for BOTH cold and warm cache, with the published value being the median of ≥5 runs.
  2. Every MCP's `tokens.json` contains the 3-scope split (`schema` / `payload` / `turn`); the published headline column is `payload`; `schema` came from Anthropic SDK `count_tokens`, `turn` from `stream-json` `usage` blocks, `payload` from parsed JSON-RPC.
  3. Every MCP's `stability.log` shows a completed 60min S1+S5 loop against the snapshot fixture server (not live URLs) with the post-run `orphan_audit.log` showing 0 surviving processes; per-tool-call 30s timeouts and `ulimit -v` ceilings were enforced throughout.
  4. Per-stage tool-call counts are recorded for every S1-S8 attempt across all 7 MCPs (empirically grounds Playwright's `browser_fill_form` batch-fill claim).
  5. A `tools_inventory.json` with count + 6-category breakdown is captured at harness start for each MCP.
**Plans**: TBD
**UI hint**: no

### Phase 4: Synthesis
**Goal**: The public-facing artifacts (`<date>_run.md`, `recommendations.md`, README headline verdict) ship with the methodology disclaimer, dual-view matrix, per-MCP deep analysis, and explicit Stage 2 graduation tiers — unblocking Stage 2 and pointing to G-710 for the deferred detection-resilience follow-up.
**Depends on**: Phase 2 + Phase 3 (both must populate every MCP's evidence directory)
**Requirements**: REPRO-01, REPRO-03, REPRO-06, REPORT-01, REPORT-02, REPORT-03, REPORT-04, REPORT-05, REPORT-06, REPORT-07, REPORT-08, REPORT-09, REPORT-10, REPORT-11, REPORT-12, SAFETY-05
**Success Criteria** (what must be TRUE):
  1. `results/2026-05-XX-mcp-comparison.md` contains the 8-dim weighted score table (7 MCPs × 8 dims + composite, same shape as `results/2026-03-31_run.md`), the S1-S8 × 7 MCPs stage matrix with distinct `N/A` and `UNTESTED` cells, a per-MCP "Deep Analysis" stanza with the "interesting angle" empirical finding, a methodology section + disclaimer header, the 2026-03 → 2026-05 overlay, an explicit "Negative Results" section, a partial-run disclosure if Firecrawl was skipped, sandbox-only callouts on every cloakbrowser mention, and a Linear traceability footer (G-703 + per-MCP sub-tickets).
  2. `results/recommendations.md` publishes the explicit Stage 2 graduation tiers (PRIMARY / SECONDARY / SANDBOX-ONLY / SKIP) for each of the 7 MCPs; the repo README is updated with the headline verdict + methodology summary + link to recommendations.
  3. The reproducibility manifest (`versions.lock.md` + `versions.json` + per-MCP binary SHA256s + `uv.lock` + `package-lock.json` + per-run `MACHINE.md`) is committed for the published wave; `bench/capture_versions.py` produced `versions.json` from the live environment.
  4. `results/recommendations.md` has a "Future Waves" section pointing to G-710 (bot-detection + TLS-fingerprint follow-up) as the explicit next-wave anchor.
  5. A wave-close ritual confirms no scope-creep snuck in (candidate count unchanged from wave start, rubric column count unchanged, no Stage 2 commits in `terminal-craft`).
**Plans**:
- [ ] 04-01-PLAN.md — Reproducibility manifest (versions.json + versions.lock.md + MACHINE.md)
- [ ] 04-02-PLAN.md — docs/REPRODUCIBILITY.md third-party recipe
- [ ] 04-03-PLAN.md — Scored comparison report (bench/build_report.py + results/2026-05-27-mcp-comparison.md)
- [x] 04-04-PLAN.md — Stage 2 graduation recommendations (bench/build_recommendations.py + results/recommendations.md)
- [ ] 04-05-PLAN.md — README headline verdict update
- [ ] 04-06-PLAN.md — Wave-close ritual + final ROADMAP close
**UI hint**: no

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4. Phases 2 and 3 are explicitly designed to run in parallel against the Phase 1 harness; the roadmap orders them by phase number but execution can overlap fully.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Harness Foundation | 7/7 | Complete (calibration PASS 2026-05-26 per `results/2026-05-25/PHASE1_CALIBRATION.md`) | 2026-05-26 |
| 2. Per-MCP Scoring Runs | 7/7 | Complete (all 6 per-MCP runs + attribution audit; all 5 SCs PASS per `.planning/phases/02-per-mcp-scoring-runs/PHASE2_AUDIT.md`) | 2026-05-27 |
| 3. Cross-Cutting Measurements | 5/5 | Complete   | 2026-05-27 |
| 4. Synthesis | 1/6 | In Progress|  |
