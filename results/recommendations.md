# Stage 2 Graduation Recommendations

> Evaluated as of 2026-05-28 with the locked 8-dimension rubric and the 7-MCP candidate list from `.mcp.json`. **Not intrinsic tool quality** — this is a snapshot of how each MCP performed on the S1-S8 fixture walk and the cross-cutting measurement suite (MEAS-01/02/07/08/09). Re-run any time the harness ships or the candidate list changes; the recommendation is a function of the rubric + fixtures, not the MCPs alone.

## Executive Summary

Of 7 MCP candidates evaluated 2026-05-28, **2 graduate to PRIMARY**, **3 to SECONDARY**, **1 SANDBOX-ONLY**, and **2 are excluded (SKIP)** from the Stage-2 terminal-craft toolkit this wave. The 8 tier-row total reflects browser-use's FAIRNESS-05 dual-mode contract (one candidate, two rows: direct + agent). Detailed scoring + per-MCP deep analysis + methodology + negative-results + 2026-03 → 2026-05 overlay live at [results/2026-05-27-mcp-comparison.md](2026-05-27-mcp-comparison.md). Tier assignments below are LOCKED per [`.planning/phases/04-synthesis/04-CONTEXT.md`](../.planning/phases/04-synthesis/04-CONTEXT.md) — this file does not re-litigate them, it publishes them with citations.

## PRIMARY

Graduates to the Stage-2 terminal-craft default toolkit. The candidates a production agent reaches for first.

### `playwright` — composite **7.93** (`tool-only` / `default`)

**Use for:** Interactive default for the production agent toolkit. Full S1-S8 surface with the Phase-1 calibration baseline; the `browser_fill_form` batch-fill primitive (re-grounded by Phase 2 P02..P05 evidence) is a real token-efficiency win on multi-field forms. Pair with a read-only specialist when SSR extraction throughput matters more than interaction depth.

**Evidence:**
- Phase 1 calibration baseline — `results/2026-05-25/playwright/transcript.md`
- Capability matrix row — `results/2026-05-26/CAPABILITY_MATRIX.md`

### `lightpanda` — composite **6.31** (`js-light` / `default`)

**Use for:** Read-only specialist for SSR-only paths. 13 ms cold-start (>50x faster than the next-fastest MCP measured this wave), 1.7 s extraction. Categorically N/A for S4-S8 per FAIRNESS-03 — and that's the point: use it for static HTML / server-rendered targets where sub-second cold-start matters; reach for an interactive PRIMARY peer for any form-handling workload.

**Evidence:**
- Per-MCP deep analysis — `results/2026-05-26/lightpanda/DEEP_ANALYSIS.md`
- Cross-cut cold-start finding — `results/2026-05-26/CROSS_CUT_SUMMARY.md` § 2


## SECONDARY

Situational / fallback. Graduates with caveats — recommended for specific use-cases, not as the agent's first reach.

### `browser-use-direct` — composite **5.87** (`LLM-augmented` / `direct`)

**Use for:** LLM-agnostic deterministic fallback for when the PRIMARY-tier interactive default is unavailable or `--mcp` constraints apply. Smallest pass-to-pass spread of any agent-driven MCP this wave (delta = 0.33). The deterministic tool surface (navigate / get_state / extract / screenshot) works without any LLM key; the agent-mode escape hatch is a separate row evaluated in the SKIP tier.

**Evidence:**
- Per-MCP deep analysis — `results/2026-05-26/browser-use-direct/DEEP_ANALYSIS.md`
- Dual-mode FAIRNESS-05 contract — `results/2026-05-26/CAPABILITY_MATRIX.md`

### `chrome-devtools` — composite **5.60** (`tool-only` / `default`)

**Use for:** DevTools-exclusive value (`list_console_messages`, `list_network_requests`, `performance_start_trace`) — recommended for performance/debugging probes, not bulk extraction. PASS3 outlier shows agent-discovery uplift potential (composite jumps to 8.33 when the SSR-rescue workaround is discovered); the 7 DevTools-exclusive tools are structurally inventoried but not exercised by the current S1-S8 walk.

**Evidence:**
- Per-MCP deep analysis — `results/2026-05-26/chrome-devtools/DEEP_ANALYSIS.md`
- DevTools-exclusive tools (7 inventoried) — `results/2026-05-26/TOOLS_INVENTORY_SUMMARY.md`

### `firecrawl` — composite **4.23** (`cloud` / `markdown`)

**Use for:** Cloud SSR specialist — 9x byte-count lift on Greenhouse SSR (24,237 vs ~2.6 KB structured-YAML from a local interactive peer in live-probe comparison). Refuted on Ashby React SPA (203 bytes of footer chrome only). Use for SSR-heavy targets where LLM-cleaned markdown is more valuable than structured DOM extraction; not a JS-SPA fallback. Loopback-incompat tagged `env-mismatch` per FAIRNESS-06.

**Evidence:**
- Per-MCP deep analysis — `results/2026-05-26/firecrawl/DEEP_ANALYSIS.md`
- Loopback-incompat attribution — `results/2026-05-26/scores.json` (`env-mismatch` tag)


## SANDBOX-ONLY

Sandbox-only graduation per SAFETY-04 + REPORT-08. The closed-binary + cookie-touch trust model is the binding constraint — useful for sandboxed scraping of public fixtures, NEVER for authenticated host pages.

### `cloakbrowser` — composite **8.33** (`stealth-specialist` / `sandbox-loopback`)

**Sandbox only — do not point at authenticated sessions.**

**Use for:** Sandboxed stealth probes against the public Greenhouse + Ashby snapshot fixtures only. Leads the S1-S8 surface at 8.33 composite, but the closed-binary + cookie-touch + sandbox-loopback trust model is the binding constraint, not the stealth claim itself. The stealth claim is DEFERRED to G-710 — the loopback snapshot fixtures don't fingerprint-check.

**Sandbox only — do not point at authenticated sessions.**

**Evidence:**
- Per-MCP deep analysis — `results/2026-05-26/cloakbrowser/DEEP_ANALYSIS.md`
- SANDBOX_PROOF — `results/2026-05-26/cloakbrowser/SANDBOX_PROOF.md`
- Sandbox-only policy origin — `CLAUDE.md` § Constraints

**Sandbox only — do not point at authenticated sessions.**


## SKIP

Does not graduate this wave. Documented reasons below; follow-up tickets noted in the Future Waves section.

### `obscura` — composite **3.27** (`stealth-specialist` / `no-stealth-flag`)

**Use for:** Do NOT graduate this wave. macOS `Sec-CH-UA-Platform-*` leak per SAFETY-03 means `--stealth` is disabled by default; missing screenshot/file-upload primitives (S6 + S8 uncompletable on surface); SSRF guard rejects 127.0.0.1 → harness-incompat cascade. Re-evaluate after the G-710 Linux A/B.

**Evidence:**
- Per-MCP deep analysis — `results/2026-05-26/obscura/DEEP_ANALYSIS.md`
- SAFETY-03 macOS stealth leak — [`docs/external-findings/browser-tools-2026-05-21.md`](../docs/external-findings/browser-tools-2026-05-21.md) § SAFETY-03

### `browser-use-agent` — composite **SKIPPED** (`LLM-augmented` / `agent`)

**Use for:** Do NOT graduate this wave. SKIPPED with reason `LLM_KEY_ABSENT` (no OPENAI_API_KEY / ANTHROPIC_API_KEY in the autonomous executor's env, rbw locked). The agent-mode code path is measurable but was not exercised. Revisit when an LLM key is available.

**Re-run procedure:** SKIPPED reason `LLM_KEY_ABSENT`. To re-run: (1) `rbw unlock`, (2) `export ANTHROPIC_API_KEY=$(rbw get "Anthropic API")`, (3) re-invoke plan 02-05 Task 2 against `results/<new-date>/browser-use-agent/`. Full procedure in `results/2026-05-26/browser-use-agent/SKIPPED.md`.

**Evidence:**
- Skip evidence + re-run procedure — `results/2026-05-26/browser-use-agent/SKIPPED.md`
- Phase 2 audit — `results/2026-05-26/PHASE2_AUDIT.md`


## Future Waves

This wave's harness ships [G-703](https://linear.app/abandoned-yachts/issue/G-703); the explicit next-wave anchor is [**G-710**](https://linear.app/abandoned-yachts/issue/G-710) — bot-detection + TLS-fingerprint follow-up that REUSES this wave's harness (no re-build required).

G-710's scope (the work that lives _outside_ this wave's Stage-2 unblock gate):

- **TLS fingerprint capture per MCP** (JA3/JA4 via Scrapfly endpoint or local pcap) — verifies stealth claims that the snapshot-fixture S1-S8 walk cannot exercise.
- **Bot-detection adversary set** — Cloudflare nowsecure.nl, reCAPTCHA demo, BrowserScan, FingerprintJS. Run each Chromium-class MCP with identical user-agent intent; compare pass-fail outcomes.
- **Cross-machine reproducibility** — MacBook parity vs the Mac Mini that ran this wave (REPRO-07 punt).
- **Obscura Linux A/B** — re-test obscura `--stealth` from a Linux host where `Sec-CH-UA-Platform-*` is honest, to validate the macOS leak finding (SAFETY-03 conditional).
- **SANDBOX-ONLY tier's stealth claim** — the closed-binary stealth claim is DEFERRED here, validated in the G-710 adversary set.

Per the PROJECT.md "Core Value" — this recommendations file IS the Stage-2 unblock gate. With it published, the private `terminal-craft` repo (Stage 2) can pull the PRIMARY tier into its default toolkit. G-710 picks up the cross-cutting validations that PROJECT.md's constraints intentionally deferred from this wave.

## Wave-Close Compliance (SAFETY-05 preview)

Audit summary for this wave (full audit in Plan 04-06):

- **Candidate count = 7** (unchanged from `.mcp.json`). 7 MCP candidates evaluated; browser-use produces two scored rows (direct + agent) per FAIRNESS-05 dual-mode contract — the row count is 8, the candidate count is 7.
- **Rubric column count = 8** (unchanged from `scoring/rubric.md`). The 8-dimension weighted composite is the same axis Phase 1 calibration ran against; no rubric drift.
- **No Stage-2 commits in this repo.** Stage 2 (the terminal-craft toolkit) lives in a private repo per PROJECT.md pipeline. `git log --grep="terminal-craft"` returns empty in this repo, by design.
- **`scoring/score.py` unchanged** (SACROSANCT per Phase 2 P07 audit). `git diff main -- scoring/score.py | wc -l` returns 0.
- **No new MCPs added to `.mcp.json`** since the 2026-05-22 wave start.


## Linear Traceability

- Umbrella: [G-703](https://linear.app/abandoned-yachts/issue/G-703) — Phase 4 synthesis under this wave's break-before-cycle estimate=16 split.
- Per-MCP sub-tickets (canonical mapping per [`docs/LINEAR_SUBTICKETS.md`](../docs/LINEAR_SUBTICKETS.md)): G-714 (playwright), G-715 (browser-use), G-716 (chrome-devtools), G-717 (lightpanda), G-718 (obscura), G-719 (firecrawl), G-720 (cloakbrowser).
**Sandbox only — do not point at authenticated sessions.**
- Future-wave anchor: [G-710](https://linear.app/abandoned-yachts/issue/G-710) — bot-detection + TLS-fingerprint + cross-machine reproducibility follow-up. Reuses this wave's harness; ships in a follow-up wave.