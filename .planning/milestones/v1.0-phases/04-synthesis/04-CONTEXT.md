# Phase 4: Synthesis - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning
**Mode:** Smart discuss (no AskUserQuestion per autonomous-no-pause directive). Reasonable judgments captured below; user can override during planning or execution.

<domain>
## Phase Boundary

Synthesize the existing Phase 2 (per-MCP scoring) + Phase 3 (cross-cutting measurements) evidence into the public-facing artifacts that close Wave 2 and unblock Stage 2 (terminal-craft toolkit):

1. **`results/2026-05-27-mcp-comparison.md`** — scored 8-dim matrix + S1-S8 stage matrix + per-MCP "Deep Analysis" + methodology + disclaimer + 2026-03 → 2026-05 overlay + Negative Results + partial-run disclosures + sandbox callouts + Linear footer (REPORT-01..05, REPORT-08..12).
2. **`results/recommendations.md`** — explicit Stage 2 graduation tiers (PRIMARY / SECONDARY / SANDBOX-ONLY / SKIP) per MCP + Future Waves section pointing to G-710 (REPORT-06).
3. **`README.md`** — headline verdict + methodology summary + link to recommendations (REPORT-07).
4. **Reproducibility manifest** — `results/2026-05-27/versions.lock.md` + `versions.json` + `MACHINE.md` + `docs/REPRODUCIBILITY.md` (REPRO-01, REPRO-03, REPRO-06).
5. **Wave-close ritual** — SAFETY-05 audit: candidate count = 7 (unchanged), rubric column count = 8 (unchanged), no Stage 2 commits.

The phase is **mostly synthesis + report writing**, not new code. The genuinely new code lives in `bench/capture_versions.py` (already exists from Phase 1) and a small `bench/build_recommendations.py` / matrix-table builder that reads `results/2026-05-26/scores.json`, `cross_cut_data.json`, and per-MCP `DEEP_ANALYSIS.md` files.

</domain>

<decisions>
## Implementation Decisions

### Stage 2 Graduation Tiering (THE headline verdict)

Driven by the evidence in `results/2026-05-26/scores.json` (8 rows: 7 MCPs + browser-use-direct/agent split), `CROSS_CUT_SUMMARY.md`, `CAPABILITY_MATRIX.md`, and per-MCP `DEEP_ANALYSIS.md`.

**PRIMARY tier (graduates to terminal-craft default toolkit):**
- **`playwright`** (composite 7.93, full S1-S8 surface, calibration baseline). The interactive default. Caveats: per Phase 1 calibration FAIL outside [8.57, 9.57] window — loopback fixtures + 2026-05 vendor patches account for the delta. `browser_fill_form` batch-fill claim re-grounded by Phase 2 P02..P05 evidence.
- **`lightpanda`** (composite 6.31 N/A-aware, denominator=13). The read-only specialist for SSR-only paths. 13ms cold start (51× faster than browser-use-direct), 1.7s extraction. Categorically N/A for S4-S8 per FAIRNESS-03 — and that's the point: pair lightpanda for read with playwright for write.

**SECONDARY tier (situational / fallback):**
- **`browser-use-direct`** (composite 5.87, smallest pass-to-pass spread of any agent-driven MCP at Δ=0.33). LLM-agnostic deterministic fallback when playwright is unavailable or `--mcp` constraints apply.
- **`chrome-devtools`** (composite 5.6 median, 8.33 PASS3). DevTools-exclusive value (`list_console_messages`, `list_network_requests`, `performance_start_trace`) — recommended for performance/debugging probes, not bulk extraction. PASS3 outlier shows agent-discovery uplift potential; structurally inventoried tools not exercised by current S1-S8 walk.
- **`firecrawl`** (composite 4.23, cloud-only). Cloud SSR specialist — 9× byte-count lift on Greenhouse SSR vs playwright structured YAML (24,237 vs 2,663). Refuted on Ashby React SPA (203 bytes of footer chrome only). Use for SSR-heavy targets only; not a JS-SPA fallback. Loopback-incompat tagged `env-mismatch` per FAIRNESS-06.

**SANDBOX-ONLY tier (per SAFETY-04 + REPORT-08):**
- **`cloakbrowser`** (composite 8.33, leads S1-S8 surface but pre-tiered SANDBOX-ONLY by Phase 2 P06). Closed-binary + cookie-touch + sandbox-loopback constraint. Useful for sandbox stealth probes against public Greenhouse/Ashby; **NEVER** for authenticated host pages.

**SKIP tier (do not graduate to Stage 2 toolkit this wave):**
- **`obscura`** (composite 3.27). macOS Sec-CH-UA-Platform-* leak (per `~/.claude/docs/browser-tools.md` + SAFETY-03), missing screenshot/file-upload primitives (S6 + S8 uncompletable on surface). Re-evaluate after G-710 Linux A/B.
- **`browser-use-agent`** (SKIPPED — LLM_KEY_ABSENT in autonomous executor env). Re-run procedure documented in `results/2026-05-26/browser-use-agent/SKIPPED.md`; revisit when an OPENROUTER_API_KEY (or equivalent) is available.

### Report Authoring

- **Filename**: `results/2026-05-27-mcp-comparison.md` (today's date stamp; matches REQUIREMENTS.md `results/2026-05-XX-mcp-comparison.md` pattern).
- **Recommendations**: `results/recommendations.md` at results/ root for direct README link.
- **README strategy**: Replace 2026-03 prior-wave table with 2026-05 MCP comparison headline. Preserve the link to 2026-03-31_run.md as historical for traceability. Mention the 2026-05_addendum.md → graduates into the new report.
- **Methodology disclaimer header** (per REPORT-05): "evaluated as of 2026-05-27 with configuration <X>; not intrinsic tool quality. Snapshot framing."
- **Playwright cross-cut data gap**: Methodology section adds disclaimer: "playwright cross-cut data captured 2026-05-25 (Phase 1 calibration date), not 2026-05-26; PASS dirs at `results/2026-05-25/playwright/`. Per-stage tool-call counts NO_EVIDENCE for this reason — re-running with PASS dirs at 2026-05-26 is a follow-up if the matrix sees external scrutiny."

### Carried-Forward Limitation Handling

Three known limitations from Phase 2 P07 + Phase 3 P05 must surface in the public artifacts:

1. **SKIPPED composite=0.0 sentinel** (`scoring/score.py` adjacent, NOT fixed): matrix builder reads `status` field — SKIPPED rows render as `SKIPPED` (not `0.0`) in the composite column. browser-use-agent + firecrawl-as-SKIPPED handled this way.
2. **Transport vs semantic stability** (Phase 3 P04 caveat): stability column annotated "COMPLETED (transport)" with a footnote: "60min loop without process crash; does not verify semantic output correctness per iteration." obscura and browser-use-direct ran the reduced 7-min config (selective_top3 schedule).
3. **Playwright cross-cut date gap**: documented in methodology as noted above.

### Negative Results Section (REPORT-10)

Explicitly document:
- firecrawl loopback-incompat (env-mismatch by design; cloud-API URL validator rejects 127.0.0.1)
- obscura macOS-only stealth leak (Sec-CH-UA-Platform-* on Apple)
- browser-use agent-mode SKIPPED (LLM_KEY_ABSENT; re-runnable)
- chrome-devtools 7 DevTools-exclusive tools structurally inventoried but not exercised by S1-S8 walk
- playwright cross-cut date gap (PASS dirs at 2026-05-25)

### 2026-03 → 2026-05 Overlay (REPORT-11)

Minimum viable overlay: a single row for Playwright (only candidate in both waves) showing 9.07 → 7.93. Annotated: same rubric, different fixture sourcing (loopback snapshot vs live URL), explains delta. Out of scope: re-mapping app-level WebFetch / Agent Browser / BrowserMCP / Lightpanda CLI rows into the MCP-layer comparison — those were tested differently.

### Reproducibility Manifest

- **`results/2026-05-27/versions.lock.md`** + `versions.json` — generated by `bench/capture_versions.py` (already exists from Phase 1). Records exact pinned versions of all 7 MCP servers + their binary SHA256s + Node + uv + Python + OS + arch + Chromium versions.
- **`results/2026-05-27/MACHINE.md`** — model, CPU, RAM, OS, NTP timestamp, network info. Pattern established in 2026-05-25 + 2026-05-26 dirs.
- **`docs/REPRODUCIBILITY.md`** — `make bench` recipe, FIRECRAWL_API_KEY note (6/7 acceptable absent), CloakBrowser Linux uncertainty + macOS-only verified, MacBook parity disclosure (Mac Mini ran the wave; MacBook NOT cross-validated this wave; G-710 follow-up).

### Wave-Close Ritual (SAFETY-05)

Final commit includes evidence:
- Candidate count = 7 (unchanged from `.mcp.json`)
- Rubric column count = 8 (unchanged from `scoring/rubric.md`)
- `git log --grep="terminal-craft"` returns empty (no Stage 2 leak)
- No new MCPs added to `.mcp.json` since wave start
- Final ROADMAP.md shows all 4 phases complete

### Linear Traceability Footer (REPORT-12)

Cite G-703 (umbrella, estimate=16) + per-MCP sub-tickets (linked from `LINEAR_SUBTICKETS.md`). G-710 referenced in Future Waves section as the detection/fingerprint follow-up anchor.

### Claude's Discretion

- **Implementation language**: Python (matches Phase 1-3 utilities; reuses existing `bench/` modules).
- **Number of plans**: ~5-6 plans (a) report builder + matrix tables, (b) recommendations.md + tiering, (c) README update, (d) reproducibility manifest, (e) docs/REPRODUCIBILITY.md, (f) wave-close ritual + final commit.
- **Whether to add tests**: Yes per global CLAUDE.md "EVERY piece of code MUST have unit tests". Matrix-table builder and recommendations builder both get unit tests against fixed JSON fixtures.
- **Build script vs hand-written report**: Hybrid — `bench/build_report.py` emits the tables and structured sections from `scores.json` + `cross_cut_data.json`; the per-MCP "Deep Analysis" prose lifts verbatim from existing per-MCP `DEEP_ANALYSIS.md` (already authored by Phase 2 per-MCP plans). No hand-rewriting; preserve provenance.
- **Whether to file new Linear tickets**: Optionally one for the playwright cross-cut date gap if user wants traceable follow-up. Defer to planning.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (already shipped)
- **`results/2026-05-26/scores.json`** — 8 scored rows with composite/status/mode/capability/sandbox_only fields. Source of truth for the matrix.
- **`results/2026-05-26/CROSS_CUT_SUMMARY.md`** + `cross_cut_data.json` — Phase 3 synthesis, ready to lift into the matrix.
- **`results/2026-05-26/CAPABILITY_MATRIX.md`** — Phase 2 P07's FAIRNESS-04 dual-view artifact. Lifts verbatim as the "second-view" matrix in the report.
- **`results/2026-05-26/<mcp>/DEEP_ANALYSIS.md`** (6 of 7) — per-MCP strengths/weaknesses/verdict + "interesting angle" findings. **playwright lacks one** (Phase 1 calibration baseline asymmetry per Phase 2 P07 limitation 3) — either generate from `results/2026-03-31_run.md` lineage or call out explicitly.
- **`bench/capture_versions.py`** — already runs; just invoke against today's env to populate `results/2026-05-27/versions.lock.md` + `versions.json`.
- **`results/2026-05-25/MACHINE.md`** + `2026-05-26/MACHINE.md` — template patterns for `2026-05-27/MACHINE.md`.
- **`scoring/score.py`** — SACROSANCT (per Phase 2 P07 audit). DO NOT MODIFY.
- **`scoring/score_with_na.py`** — N/A-aware composite computer. Reuse for any score recomputation; documented composite=0.0 sentinel for SKIPPED rows is handled in the matrix-builder, not here.

### Established Patterns
- **Markdown table generation**: Phase 3 P05's `bench/build_cross_cut_summary.py` is the precedent — reads JSON, writes Markdown table rows. Pattern reusable for report tables.
- **Cite-source discipline**: Every number in CROSS_CUT_SUMMARY.md cites the per-MCP file it came from. Continue the pattern in the new report.
- **Sandbox callout** (REPORT-08): every cloakbrowser mention gets `**Sandbox only — do not point at authenticated sessions**` callout. Phase 2 P06 + P07 established the convention; reuse.

### Integration Points
- README.md root — REPORT-07 says update with headline verdict + methodology summary + link to recommendations
- `results/2026-05-27-mcp-comparison.md` (new at results/ root)
- `results/recommendations.md` (new at results/ root)
- `results/2026-05-27/` (new directory for versions.lock + versions.json + MACHINE.md)
- `docs/REPRODUCIBILITY.md` (new — `docs/` dir does not yet exist; create it)

### Constraints
- **No new MCPs** in `.mcp.json` (SAFETY-05 wave-close).
- **No Stage 2 terminal-craft commits** in this repo (pipeline gate).
- **No live URLs** in the report's evidence cells — all fixtures are loopback snapshots per REPRO-04.
- **No PII in screenshots** — `bench/scrub_artifacts.py` already enforced in Phase 1-3; new artifacts (if any) must pass the scrub.

</code_context>

<specifics>
## Specific Ideas

- **Two-view matrix per FAIRNESS-04**: composite scores table AND capability-tagged category matrix (already exists in `CAPABILITY_MATRIX.md`) so readers cannot accidentally compare cloud-to-local on a single number.
- **Per-MCP "interesting angle" finding** (REPORT-03 + Phase 2 P07 DEEP_ANALYSIS.md): lift verbatim from each `DEEP_ANALYSIS.md`. Examples in evidence dirs:
  - chrome-devtools: SSR-rescue trick (fetch+DOMParser+document.write); 7 DevTools-exclusive tools inventoried but unexercised
  - lightpanda: 0 bytes vs ~5KB dead shell framing for Ashby
  - firecrawl: 24KB SSR lift confirmed, 203-byte SPA refutation
  - obscura: 0.0.0.0 SSRF-guard workaround; ~30MB CDP-direct vs ~300MB Playwright partial-support
  - browser-use: dual-mode contract; interpretation-variance vs execution-variance distinction
  - cloakbrowser: pre-tiered SANDBOX-ONLY by construction
  - playwright: calibration FAIL 7.93 outside [8.57, 9.57] window — Phase 1 lineage + fixture-sourcing delta
- **Future Waves section**: G-710 explicit anchor for bot-detection + TLS-fingerprint follow-up. Mention re-baseline if Wave 2 fixtures need refresh after a year.

</specifics>

<deferred>
## Deferred Ideas

- **v2: chrome-devtools "DevTools probe" 9th stage** producing `network.json` + `trace.json` + `console.json` — defer because it changes the stage matrix and breaks 2026-03 comparability.
- **v2: LLM-extraction split scoring for Firecrawl + browser-use** — defer because dual-mode complicates the matrix.
- **v2: Residential-IP rotation pool** — defer pending bot-detection cut (now lives in G-710).
- **v2: Memory-footprint snapshot per MCP during S1** — surfaces Obscura's ~30MB-per-tab vs Playwright's ~300MB-per-tab differentiator; FEATURES "should have" rather than must.
- **Playwright cross-cut data re-run** — if external scrutiny demands tool-call counts for playwright, re-run the cross-cut suite with PASS dirs at 2026-05-26. Document gap in the published report; not blocking for this wave's close.
- **MacBook cross-machine parity** (REPRO-07 cut to G-710) — Mac Mini ran this wave; MacBook parity NOT validated this wave.

</deferred>
