# Web-Agent MCP Comparison

## What This Is

A public benchmark of browser-automation MCP servers driven by Claude Code. Stage 1 of a 3-stage pipeline that ends in production agent tooling: this repo scores candidate MCPs on standardized job-application fixtures, the winners graduate into the private `terminal-craft` toolkit (Stage 2), which is then wired into the `Kestrel` and `Eyas` job-hunting agents (Stage 3). Reproducible methodology so external readers can clone, run, and confirm the scores.

## Core Value

**Pick the right browser MCP(s) for production agent use, backed by reproducible scores on the same fixtures every candidate is measured against.** If everything else fails, the comparison matrix and the graduate-to-toolkit recommendation are what must exist at the end.

## Requirements

### Validated

<!-- Inferred from existing code in fixtures/, scoring/, results/. These are locked. -->

- ✓ **Scoring rubric exists** — 8 weighted dimensions (Data Quality 3x, Reliability 3x, Speed 2x, Token Efficiency 2x, Interaction Depth 2x, JS Rendering 1x, Setup Complexity 1x, Error Handling 1x), composite on 0-10 scale — `scoring/rubric.md`, `scoring/score.py`
- ✓ **Test fixtures established** — mock applicant `Jane Testworth` + mock resume PDF — `fixtures/mock_data.json`, `fixtures/mock_resume.pdf`
- ✓ **Test stages defined** — S1-S8 covering read-only extraction (S1-S3) and interactive form flows (S4-S8) on Greenhouse + Ashby targets
- ✓ **Prior app-level wave complete** — 5 agents scored 2026-03-31 (Playwright MCP 9.07, WebFetch 7.87, Agent Browser 7.60, Lightpanda 5.87, BrowserMCP 5.53) — `results/2026-03-31_run.md`
- ✓ **Project-scope `.mcp.json`** — 7 candidate MCPs auto-spawn when Claude opens this repo — G-703 (2026-05-22)

### Active

<!-- Stage 1 scope. Each is a hypothesis until shipped. -->

- [ ] All 7 MCPs scored on the 8-dimension rubric using the existing fixtures
- [ ] Cold-start latency measured per MCP (spawn → first usable tool call)
- [ ] DOM coverage per MCP across S1-S8 (which pages each successfully navigates + extracts)
- [ ] Bot-detection resilience tested against Cloudflare, DataDome, Akamai, reCAPTCHA
- [ ] TLS fingerprint (JA3/JA4) characterized per MCP — confirm or refute the "only real Chrome passes 2025-2026 detection" claim
- [ ] Token efficiency measured per MCP per task (tokens consumed / task completed)
- [ ] Stability tested — each MCP survives 1hr continuous use without process crash
- [ ] `results/2026-05-XX-mcp-comparison.md` — scored matrix published
- [ ] `results/recommendations.md` — explicit "graduate to Stage 2 toolkit" verdict in order of preference
- [ ] README updated with methodology + headline verdict (public-facing summary)
- [ ] Reproducibility validated — methodology documented enough that a third party can clone, run, and get similar scores

### Out of Scope

- **Stage 2 (terminal-craft toolkit packaging)** — separate private repo, blocked on Stage 1 verdict
- **Stage 3 (Kestrel + Eyas agent wiring)** — production agent integration, blocked on Stage 2 toolkit
- **App-level agents (Skyvern, Manus, Comet, etc.)** — covered in the prior 2026-03-31 wave; this comparison is MCP-layer only
- **`browsermcp` server** — needs the Chrome Agent profile + browser extension; different operational model from the 7 candidates and out of scope for this wave (may revisit in a follow-up)
- **Authenticated session testing on real banking/credential pages** — global policy prohibits browser MCPs on those; cloakbrowser is sandbox-only
- **Building shared abstractions over the MCPs** — that's Stage 2's job

## Context

- **Stage 1 of a 3-stage pipeline.** `web-agent-comparison` (public, this repo) → `terminal-craft` (private toolkit) → `Kestrel` + `Eyas` (production job-hunting agents). Stages 2 and 3 must NOT begin until Stage 1 produces actionable comparison results.
- **Prior wave (March 2026)** scored 5 app-level agents on the same fixtures. The same rubric and fixtures are reused here for direct comparability, but the candidate set is different: this wave focuses on **MCP-layer browser servers** that Claude Code can drive directly.
- **MCP scope rescoping (G-703, 2026-05-22)** — the 7 candidate MCPs were previously registered at user scope, which caused them to spawn in every Claude session everywhere (rocket-icon dock pollution). They were moved to this repo's `.mcp.json` and removed from user scope. They now only spawn when Claude opens this directory — which is exactly what we want for comparison work.
- **Existing scaffolding to reuse:** `scoring/rubric.md`, `scoring/score.py`, `fixtures/mock_data.json`, `fixtures/mock_resume.pdf`, prior result format in `results/2026-03-31_run.md`. The prior wave's README ranking table will need updating once this wave completes.
- **TLS fingerprinting (JA3/JA4)** dominates 2025-2026 bot detection per Vitalik's global browser-tools doc. For hard targets only real Chrome via BrowserMCP or CloakBrowser passes; the comparison should confirm or refute this empirically per MCP.

## Constraints

- **Tech stack**: Python 3 (scoring), Markdown (results), shell (test orchestration). No framework — keep it dogfood-friendly.
- **Reproducibility**: Methodology must be runnable by a third party with only the public repo. No internal-only fixtures, no rbw-gated secrets in the core flow.
- **API keys**: `FIRECRAWL_API_KEY` required for firecrawl MCP (in rbw under `firecrawl.dev` → `Firecrawl_API`). If absent, partial scoring (6/7) is acceptable per G-703 AC. No other paid keys.
- **Sandbox-only MCPs**: `cloakbrowser` is closed-source binary touching cookies — never point at authenticated host pages. Tested only against the public Greenhouse + Ashby fixtures.
- **Public repo**: `.mcp.json` is committed and visible. Acceptable for a research repo; the candidate list IS the research artifact.
- **Linear traceability**: G-703 is the umbrella ticket (estimate=16 = break-before-cycle signal). Splits into ~7 per-MCP scoring tickets + 1 synthesis ticket before pulling into a cycle.
- **Cross-machine**: Mac Mini has all 7 binaries installed; MacBook parity not yet verified. The `.mcp.json` will silently fail to spawn missing binaries.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Reuse the 2026-03 rubric + fixtures rather than redesign | Direct comparability with prior wave; the dimensions are already battle-tested | — Pending |
| `.mcp.json` at project scope, not user scope | Prevents rocket-icon dock pollution in every other Claude session; only spawns when working on this comparison (G-703 lesson) | ✓ Good |
| `browsermcp` excluded from this wave | Different operational model (Chrome extension + Agent profile); would muddy the apples-to-apples comparison | — Pending |
| Stage gating (no Stage 2/3 work until Stage 1 ships) | Avoids premature toolkit decisions before the data exists | — Pending |
| `cloakbrowser` tested on public fixtures only | Closed-source binary + cookie access = sandbox-only per global browser-tools policy | ✓ Good |
| Partial scoring (6/7) acceptable if Firecrawl key absent | API-key dependency shouldn't block the comparison; Firecrawl is one row | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-22 after initialization*
