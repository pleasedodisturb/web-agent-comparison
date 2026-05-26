# Capability Matrix — 2026-05-26

Per **FAIRNESS-04**: this view groups MCPs by category so readers cannot
accidentally compare a cloud service to a local browser on a single
composite number. The same-rubric composite IS published (Phase 4
REPORT-01), but readers MUST consult this capability matrix first to
understand what each tier of MCP is even attempting.

## Two-view contract

| View | Where | What it shows |
|---|---|---|
| **Same-rubric composite** | `scores.json` + Phase 4 REPORT-01 | All 8 rows on a single weighted-composite axis — answers "what gets the job done on Greenhouse + Ashby today?" |
| **Capability matrix** *(this file)* | `CAPABILITY_MATRIX.md` | Group MCPs by architectural category before comparing — answers "what are we comparing, apples-to-apples?" |

Cross-reference both before drawing conclusions. The composite penalises
read-only/cloud MCPs on interactive stages even when those stages are
N/A by category; the matrix below puts category context back in.

## Per-MCP capability matrix

| MCP | Capability | Mode | Status | Composite (N/A-aware) | Notes |
|-----|-----------|------|--------|----------------------|-------|
| `playwright` | tool-only | default | SCORED | 7.93 | Calibration baseline — full S1-S8 PASS |
| `chrome-devtools` | tool-only | default | SCORED | 5.60 | S4-S8 FAIL on Greenhouse React-clobber (interaction_depth=0) — 1-of-3 passes found the SSR-rescue workaround |
| `browser-use-direct` | LLM-augmented | direct (no user LLM key) | SCORED | 5.87 | Vitalik's headline-claim CONFIRMED for S1+S2+S3+S8 (no LLM needed); REFUTED for S4-S7 (React-clobber, not missing LLM) |
| `browser-use-agent` | LLM-augmented | agent (LLM key required) | SKIPPED | 0.0\* | reason=`LLM_KEY_ABSENT`; SKIPPED.md has re-run procedure (Phase 4 must consult `status`, not composite) |
| `cloakbrowser` | stealth-specialist | sandbox-loopback | SCORED | 8.33 | **Sandbox only — do not point at authenticated sessions.** SANDBOX_PROOF.md attests zero non-loopback hostnames across all 3 passes. |
| `obscura` | stealth-specialist | no-stealth-flag (macOS) | SCORED | 3.27 | `--stealth` flag disabled per SAFETY-03 (Sec-CH-UA-Platform-* leak on macOS); SSRF guard rejects 127.0.0.1 → harness-incompatibility cascade |
| `firecrawl` | cloud | markdown | SCORED | 4.23 | S1-S3 FAIL on loopback fixtures — cloud service cannot reach localhost; data_quality + js_rendering tagged `env-mismatch`. S4-S8 N/A by category. |
| `lightpanda` | js-light | nightly@2026-05-22 | SCORED | 6.31 | S4-S8 N/A by category (no interaction surface); js_rendering=2 by architectural design (Zig engine has no JS runtime — React never hydrates) |

\* `browser-use-agent` composite=0.0 is a degenerate-case fallback in
   `score_with_na.py` (all-N/A rows divide by zero in the denominator,
   the wrapper returns 0.0). The `status: "SKIPPED"` field is the
   source of truth. Documented as a known limitation for Phase 4 to
   address — `score_with_na.py` is adjacent-to-sacrosanct this wave.

## Category groupings

### tool-only (raw browser-automation, no built-in LLM)

- `playwright` — calibration baseline, full S1-S8 PASS
- `chrome-devtools` — same architectural tier; differs on agent's
  ability to discover SSR-rescue workaround for Greenhouse's
  React-hydration clobber

Both run a real Chromium under host control. Direct comparability —
this is the apples-to-apples within-tier benchmark.

### LLM-augmented (uses LLM in-tool for action planning)

- `browser-use-direct` — claims to work without user's own LLM key;
  16-tool surface; 5.87 composite — tied for 3rd
- `browser-use-agent` — LLM key required; SKIPPED this run because
  `OPENAI_API_KEY` was zero-length sentinel (intentional, prevents
  inadvertent benchmark LLM spend)

The two modes are a single product with distinct measurement contracts
per FAIRNESS-05 — both rows must remain in the matrix even when one is
SKIPPED, so the comparison is honest about what was measured.

### stealth-specialist (anti-detection focus)

- `cloakbrowser` — closed-source binary patched for stealth; passes
  Cloudflare, reCAPTCHA, FingerprintJS (per vendor claims); **sandbox
  only — do not point at authenticated sessions.** Composite 8.33 in
  the loopback harness; stealth claims DEFERRED to G-710 per CONTEXT.md
- `obscura` — Rust+V8 stealth engine with `--stealth` flag DISABLED on
  macOS per SAFETY-03 (Sec-CH-UA-Platform-* client-hints leak the real
  OS regardless of JS UA spoof); SSRF guard refuses 127.0.0.1 →
  harness-incompatibility cascade tagged `tool-bug` per FAIRNESS-06
  aggregator default

Both make stealth their differentiator; this benchmark measures their
basic browser-automation surface, not their anti-detection efficacy
(that's a separate cross-cutting measurement, deferred to G-710 + Phase 3).

### cloud (remote service, no local browser)

- `firecrawl` — markdown-extraction cloud service; cannot reach
  loopback fixtures by architecture (cloud egress sees public-internet,
  not the harness's localhost). `data_quality` and `js_rendering`
  tagged `env-mismatch` per FAIRNESS-06 because the failure is a
  loopback-vs-cloud architectural caveat, not a Firecrawl bug

Comparing `firecrawl` to `playwright` on a single composite is the
apples-to-oranges trap (Pitfall 2). The composite IS published — but
`env-mismatch` tags + this matrix tell the reader what they're
actually comparing.

### js-light (JS-light or JS-blind)

- `lightpanda` — Zig-based browser engine with no JS runtime; sub-second
  cold-start; designed for server-rendered targets and JSON-API
  consumption. `js_rendering=2` is by architectural design, not a
  regression. S4-S8 N/A by category (no interaction surface)

The headline negative result: lightpanda is correctly the wrong tool
for SPA-targeting browser-automation workloads. Use it when you know
the target is server-rendered and you want sub-second cold-start; do
not reach for it as a general browser drop-in (per lightpanda
DEEP_ANALYSIS.md).

## Cross-category note

Comparing `firecrawl` (cloud) to `playwright` (local) on a single
composite is the apples-to-oranges trap (Pitfall 2). The same-rubric
composite IS published (Phase 4 REPORT-01), but readers MUST consult
this capability matrix first to understand what each tier of MCP is
even attempting. The `env-mismatch` attribution on `firecrawl` and the
`N/A` cells on `firecrawl` + `lightpanda` are the in-rubric devices
that preserve a single-axis ranking while signalling the caveat.

## Sources

- `results/2026-05-26/scores.json` — the audited matrix
- `results/2026-05-26/{mcp}/DEEP_ANALYSIS.md` — per-MCP capability
  rationale (chrome-devtools, lightpanda, firecrawl, obscura,
  browser-use-direct, cloakbrowser)
- `results/2026-05-26/cloakbrowser/SANDBOX_PROOF.md` — SC #5 evidence
- `results/2026-05-26/browser-use-agent/SKIPPED.md` — LLM_KEY_ABSENT
  re-run procedure
- `results/2026-05-26/firecrawl/DEEP_ANALYSIS.md` — cloud-vs-loopback
  architectural caveat
- `.planning/phases/02-per-mcp-scoring-runs/02-CONTEXT.md` — FAIRNESS-04,
  FAIRNESS-05, FAIRNESS-06 contracts
