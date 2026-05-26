# lightpanda — Deep Analysis

**Run date:** 2026-05-26
**Linear sub-ticket:** G-716 (Phase-2 per-MCP scoring; see G-703 umbrella)
**Plan:** [02-02-lightpanda-PLAN.md](../../../.planning/phases/02-per-mcp-scoring-runs/02-02-lightpanda-PLAN.md)
**Binary:** `~/.local/bin/lightpanda` (sha256 `4ca3897a1547c9b3b843a0a921c2b4d044afb3ad4914091a845ac608fe1cb047`)

## Capability Tag

**`js-light`** — Zig-based 'Browsercore' engine that ships with no full JS runtime (no V8 / no SpiderMonkey). The binary is suitable for static HTML and server-rendered content but cannot execute client-side JavaScript frameworks (React, Vue, etc.). Categorically read-only per the harness's `READ_ONLY_MCPS` constant in `scripts/aggregate_scores.py:68`.

## Median Composite

**6.31 / 10** (N/A-aware; only the 6 dimensions lightpanda can attempt count toward the weighted denominator).

| Dimension (weight) | Median Score | Notes |
|---|---|---|
| Data Quality (3×) | 7 | S1 PASS + S3 PASS; S2 FAIL ⇒ 2/3 read-only stages |
| Reliability (3×) | 9 | One stage fail (S2) docks 1 from 10 |
| Speed (2×) | 5 | Phase-1 neutral stub; real cold-start in Phase 3 |
| Token Efficiency (2×) | 5 | Phase-1 neutral stub; real 3-scope split in Phase 3 |
| Interaction Depth (2×) | **N/A** | Architectural — read-only MCP, FAIRNESS-03 |
| JS Rendering (1×) | 2 | S2 FAILED — Ashby React never hydrates |
| Setup Complexity (1×) | 7 | Single binary, no Chromium download required |
| Error Handling (1×) | 5 | Tool surface refuses gracefully (e.g. selectOption "Node is not a `<select>` element") |

**Ranking among 3 measured MCPs:** 2nd (playwright 7.93 > lightpanda 6.31 > chrome-devtools 5.6).

## N/A Semantics Callout

Stages S4 (form discovery), S5 (form fill), S6 (resume upload), S7 (source dropdown), S8 (screenshot) and the `interaction_depth` dimension are scored **`"N/A"`** — **not zero** — per FAIRNESS-03 and the hardcoded `READ_ONLY_MCPS = {"lightpanda", "firecrawl"}` fairness policy in `scripts/aggregate_scores.py`. `scripts/score_with_na.py` drops N/A cells from the weighted denominator at composite time, so the published 6.31 reflects ONLY the dimensions lightpanda's architecture allows it to compete on (denominator = 3+3+2+2+1+1+1 = 13, not 15). Treating these as 0 would have produced an artificial 5.47 that misrepresents the candidate's category — that's the deviation `score_with_na.py` exists to prevent.

Note: lightpanda DOES expose `click` / `fill` / `selectOption` / `setChecked` / `hover` / `press` / `scroll` / `waitForSelector` tools at the MCP layer (7 of its 20 tools are categorized as `interaction` per `tools_inventory.json`). However, these tools operate against a DOM that React never hydrates — the form fields they touch are SSR scaffolding without React handlers, so writes have no application-layer effect. Architectural inability to interact ⇒ N/A is the correct fairness call. (Claude's PASS1 attempted-stage diagnostic `PASS1/_attempted_stage_s4.yml` and `_attempted_stage_s5.yml` document the empirical limitation in detail.)

## The Falsifiable Empirical Finding — Ashby SPA Test (2026-03 → 2026-05)

### 2026-03 claim
From `.planning/research/SUMMARY.md § Empirical Claims to Falsify`: *"lightpanda — 'React-blind' — returned 0 bytes on Ashby in 2026-03; check whether 2026-05 nightly is better/same/worse."*

### 2026-05 nightly observation (3 passes, identical verdict)

| Measurement | PASS1 | PASS2 | PASS3 |
|---|---|---|---|
| `markdown` tool output bytes | 0 | 0 | **0** |
| `semantic_tree` node count | 1 (RootWebArea only) | 1 | 1 |
| `structuredData.jsonLd` items | 0 | 0 | 0 |
| `structuredData.openGraph` keys | 0 | 0 | 0 |
| `structuredData.meta.title` | "Jobs" (static `<title>`, not job-posting title) | "Jobs" | "Jobs" |
| Raw HTML shell present? | yes — 6805 chars `document.documentElement.outerHTML` | yes — 4555 chars `body.innerHTML` | yes — same shell |
| `<div id="root">` present? | yes, 2 SSR'd skeleton children | yes, 2 | yes |
| Scripts in DOM (referenced) | 2 | 2 | 2 |
| Job data fields extracted (title/company/location/role_summary) | 0 / 4 | 0 / 4 | 0 / 4 |

### Verdict (with attribution to the rubric)

The 2026-03 "0 bytes on Ashby" claim is **CONFIRMED at high measurement specificity** on lightpanda's primary content-extraction tool (`mcp__lightpanda__markdown`): all 3 passes returned exactly 0 bytes. The `semantic_tree` accessibility-style probe likewise returns 1 node with no children — no body content was extractable through any of the 5 tools Claude reached for (`markdown`, `structuredData`, `semantic_tree`, `evaluate`, `navigate`).

**The claim is partially REFUTED on raw-shell metric:** the static React shell HTML (4-7KB depending on which `document.*.outerHTML` slice you measure) IS delivered over the wire and parsed into a DOM. So "0 bytes" was imprecise as a single number — the right framing is "0 bytes of hydrated content" or "0 bytes from the markdown extraction tool."

**Attribution:** `js_rendering=2` with tag `tool-bug` (FAIRNESS-06). The "bug" is architectural — lightpanda's Zig engine intentionally omits a JS runtime — but the rubric's `tool-bug` taxonomy fits ("inherent MCP limitation, not transient and not target-side"). NOT classified as `target-flag` (the Ashby fixture is a vanilla React 18 SPA reproducible across all other browser MCPs) and NOT classified as `env-mismatch` (the harness is identical to what playwright and chrome-devtools ran under).

This is the headline negative result for Phase 4's `recommendations.md`: **lightpanda is correctly the wrong tool for SPA-targeting browser-automation workloads. Use it when you know the target is server-rendered and you want sub-second cold-start; do not reach for it as a general browser drop-in.**

## Version-String Inconsistency

The `bench/capture_versions.py` step and the live MCP handshake disagree about which version of lightpanda is running:

| Source | Reported version |
|---|---|
| `versions.json` → `mcps.lightpanda.binary_self_report` (parsed from the binary itself) | **`0.3.0`** |
| MCP JSON-RPC `initialize` response → `serverInfo.version` (sent by the running server) | **`0.1.0`** |
| `versions.json` → `mcps.lightpanda.sha256` (canonical pin) | `4ca3897a1547c9b3b843a0a921c2b4d044afb3ad4914091a845ac608fe1cb047` |

This was documented in `~/.claude/docs/browser-tools.md` (2026-05-21 verification) and reproduced byte-for-byte here. We **do not resolve the contradiction** — both numbers are recorded so a future Phase-4 reader can cite the actual artifact source. The canonical version reference for reproducibility is the SHA256 pin, not either human-facing version string. Phase 4's "Negative Results" section can use this as a documentation-hygiene callout against the vendor.

## Pass-to-Pass Variance

| Pass | Wall-clock | S1 | S2 | S3 | S4-S8 | Composite (this pass alone) |
|---|---|---|---|---|---|---|
| PASS1 | 5m44s | PASS | FAIL | PASS | N/A | 6.31 |
| PASS2 | 2m59s | PASS | FAIL | PASS | N/A | 6.31 |
| PASS3 | 3m29s | PASS | FAIL | PASS | N/A | 6.31 |

**Zero variance across 3 passes** — every dimension and every stage verdict was identical. This is the polar opposite of chrome-devtools, where PASS3 found an SSR-rescue technique that PASS1/PASS2 didn't (2-1 split on S4-S8 verdict). Lightpanda's architectural ceiling is not subject to agent-discovery effects: there's no reasoning path through lightpanda's tool surface that produces React-hydrated output, so no amount of multi-pass exploration changes the verdict.

This is itself a publishable observation: **a 3-pass median harness is most valuable when the candidate has unused capability that a smart agent might discover; for architecturally-bounded candidates, 1-pass would have been sufficient.** Useful nuance for Phase 4's methodology section, and a useful efficiency note for the remaining MCP runs.

## Failure-Attribution Table

Per FAIRNESS-06, every sub-rubric cell scoring < 5 must carry one of `{tool-bug, env-mismatch, target-flag, transient}`. N/A cells are not failures and not tagged.

| Dimension | Score | Tag | Justification |
|---|---|---|---|
| js_rendering | 2 | `tool-bug` | Architectural — Zig engine has no JS runtime; React never hydrates. The "bug" is by design (lightpanda's differentiator is speed via JS-light); the taxonomy still classifies it `tool-bug` because the limitation is in the MCP, not the target or environment. |

No other sub-5 cells in the row (data_quality=7, reliability=9, speed=5, token_efficiency=5, setup_complexity=7, error_handling=5; interaction_depth=N/A).

## What the Tool Inventory Confirmed

`tools_inventory.json` (20 tools, `protocol_version: 2024-11-05`):

- **2 navigation** tools: `goto`, `navigate` (alias)
- **2 inspection** tools: `markdown`, `findElement`
- **1 diagnostics** tool: `evaluate`
- **7 interaction** tools: `click`, `fill`, `scroll`, `waitForSelector`, `hover`, `press`, `selectOption`
- **8 other**: `eval` (alias), `semantic_tree`, `nodeDetails`, `interactiveElements`, `structuredData`, `detectForms`, `links`, `setChecked`

**The interaction surface exists but is functionally dead against hydrated apps.** This is the load-bearing structural finding: when a future reader asks "but the docs say lightpanda has `fill` — why is interaction_depth scored N/A?" the answer is here. The MCP's tool *count* and *signatures* match an interactive browser, but the underlying engine cannot complete the actions in any application-meaningful way. The capability tag `js-light` (not `read-only` literally) reflects that nuance.

## Linear Sub-ticket Reference

G-716 (proposed per CONTEXT.md § Implementation Decisions; the tickets G-715..G-720 split is owned by the OUTREACH-03 sweep and was not created at run time). This Deep Analysis can be lifted verbatim into the G-716 comment thread when it lands.

## Stretch Items NOT Done (Deferred)

- Per-tool latency profiling (deferred to Phase 3 / MEAS-02 — measures `t_first_useful` for each of the 20 tools).
- Comparison against the older `nightly@2025-09-XX` build to attribute which engine changes between 2026-03 and 2026-05 (none on the hydration axis, evidently).
- Probing the `evaluate` tool with a polyfilled mini-React to characterize exactly which JS APIs are missing (V8 absent → most of them; not interesting enough to justify the time).
