# chrome-devtools — Deep Analysis (2026-05-26)

**MCP:** `chrome-devtools-mcp` v1.0.1 (GA'd 2026-05-18, npm `latest`)
**Capability tag:** `tool-only`
**Mode:** `default` (no special invocation flags)
**Median composite (3-pass, N/A-aware):** **5.6 / 10**
**Run dates:** 2026-05-26 (all 3 passes within a 26-minute window)
**Linear ticket:** G-715 (chrome-devtools sub-ticket of G-703)

## Capability tag

`tool-only` — chrome-devtools-mcp is raw browser-automation tooling backed by the Chrome
DevTools Protocol. There is no built-in LLM; planning and orchestration are driven by the
caller (Claude Code in this run). Same category as `playwright`, distinct from
`browser-use-agent` (LLM-augmented) and `firecrawl` (cloud).

## Median composite & sub-rubric

| Dimension (weight) | Median | PASS1 | PASS2 | PASS3 |
|---|---|---|---|---|
| Data Quality (3×) | **10** | 10 | 10 | 10 |
| Reliability (3×) | **5** | 5 | 5 | 10 |
| Speed (2×) | **5** | 5 | 5 | 5 |
| Token Efficiency (2×) | **5** | 5 | 5 | 5 |
| Interaction Depth (2×) | **0** | 0 | 0 | 10 |
| JS Rendering (1×) | **10** | 10 | 10 | 10 |
| Setup Complexity (1×) | **7** | 7 | 7 | 7 |
| Error Handling (1×) | **2** | 2 | 2 | 8 |
| **Weighted Composite** | **5.6** | 5.6 | 5.6 | 8.33 |

Speed, Token Efficiency, and Setup Complexity are neutral mid-band values per the Phase-1
stub policy (cold_start.json + tokens.json are `{deferred: phase-3}`; Setup Complexity
will get real signal in plan 01-07's successor measurement task). They are the same
constants every MCP carries this wave — Playwright also scores 5/5/7 on those three.

## Per-stage verdicts (3-pass majority)

| Stage | Median verdict | PASS1 | PASS2 | PASS3 | Tool calls (median) |
|---|---|---|---|---|---|
| S1 — Greenhouse extract | **PASS** | PASS | PASS | PASS | navigate + evaluate_script (SSR rescue) |
| S2 — Ashby SPA extract | **PASS** (empty payload) | PASS | PASS | PASS | navigate + take_snapshot |
| S3 — Platform detection | **PASS** | PASS | PASS | PASS | analysis only, no MCP calls |
| S4 — Apply-form snapshot | **FAIL** | FAIL | FAIL | PASS | required SSR-rescue trick to expose form |
| S5 — Fill form | **FAIL** | FAIL | FAIL | PASS | `fill_form` (1 batched call when reached) |
| S6 — Upload resume | **FAIL** | FAIL | FAIL | PASS | `upload_file` against `#resume` |
| S7 — React-Select dropdown | **FAIL** | FAIL | FAIL | PASS | `evaluate_script` native-setter fallback |
| S8 — Screenshot | **FAIL** | FAIL | FAIL | PASS | `take_screenshot` (fullPage=true) |

**Tool calls per pass:** PASS1=10, PASS2=14, PASS3=35 (chrome-devtools-scoped).
**Wall-clock:** PASS1=5m51s, PASS2=5m38s, PASS3=10m08s. Median = 5m51s. None exceeded the
60-minute budget; single-pass fallback was **not** invoked.

## Pass-to-pass variance — the load-bearing finding

The dramatic spread (PASS1/PASS2 composite=5.6 vs PASS3=8.33) is **not** chrome-devtools
flapping. The MCP, fixture, harness, and host environment were identical across the three
passes. The variance lives in the **driving agent**'s discovery of a workaround:

- The Greenhouse fixture's React bundle attempts a live-CDN fetch on hydration. The
  fetch fails offline, and the SPA replaces the entire `<body>` with a "Page not found"
  fallback before any agent can interact with the SSR'd form.
- **PASS1 and PASS2:** the agent observed the post-hydration "Page not found" state, ran
  `take_snapshot` to confirm no form was in the DOM, wrote `stage_s4.FAILED`, and
  cascaded `.FAILED` sentinels through S5-S8. Honest reporting, but the form was
  in fact reachable.
- **PASS3:** the agent ran `evaluate_script` to `fetch()` the raw HTML, parsed it with
  `DOMParser`, stripped the `<script>` tags, and used `document.open()/write()/close()`
  to replace the live DOM with the inert SSR markup. The SSR form became interactive,
  `fill_form` filled 4 fields in one call, `upload_file` attached the resume, and
  `take_screenshot` captured a 6.2 MB full-page PNG. S4-S8 all passed.

Playwright's 2026-05-25 calibration row used the same SSR-rescue trick (per
`results/2026-05-25/playwright/transcript.md`). That run was scored against a single
session and so reads as "Playwright works." chrome-devtools' 3-pass median exposes that
the workaround is **agent-discovery-dependent**, not deterministic. **This is the
fairness-critical finding the 3-pass FAIRNESS-01 protocol exists to surface.** A
single-pass result for chrome-devtools could plausibly have landed at either 5.6 or 8.33
depending on which session was sampled.

## Failure-attribution table

Sub-rubric cells scoring < 5 in the median row, each tagged per `bench/failure_taxonomy.py`:

| Dimension | Score | Tag | Justification |
|---|---|---|---|
| `interaction_depth` | 0 | `tool-bug` | 2-of-3 passes failed S4-S8 (the interactive stages). Reading "tool-bug" loosely: the failure was in the agent's interaction with the MCP, not in the MCP binary itself — but the failure_taxonomy module's 4 tags don't separate "MCP fault" from "agent fault." `tool-bug` is the conservative aggregator default per FAIRNESS-06 when no per-attempt tag is recorded. The correct read is documented in this section, not in the tag alone. |
| `error_handling` | 2 | `tool-bug` | The transcript heuristic counts `error|retry|fail` lexemes; PASS1/PASS2's `stage_sN.FAILED` sentinels and their cascade descriptions push the count past the >10 threshold. PASS3 (full success) scored 8 on the same heuristic. Same root cause as `interaction_depth`: agent-side, not MCP-side. |

Both attributions trace to a single root cause (the SSR-rescue discovery gap), not two
independent MCP bugs. The taxonomy doesn't distinguish "MCP capability gap" from "agent
strategy gap" — that distinction is in this paragraph.

## Interesting-angle finding (DevTools-exclusive signals)

Per `.planning/research/SUMMARY.md`, chrome-devtools' candidate-distinguishing claim is
the **DevTools-only tool surface**: network waterfall, performance trace, source-mapped
console. This run captured `tools_inventory.json` to document the available surface, then
let the natural S1-S8 walk run.

**Tools observed in `tools_inventory.json` (29 total across 6 categories):**

| Category | Count | Headliners |
|---|---|---|
| interaction | 10 | `click`, `fill`, `fill_form`, `upload_file`, `press_key`, `type_text`, `drag`, `wait_for`, `handle_dialog`, `hover` |
| diagnostics | **10** | `list_console_messages`, `get_console_message`, `list_network_requests`, `get_network_request`, `performance_start_trace`, `performance_stop_trace`, `performance_analyze_insight`, `emulate_cpu`, `emulate_network` |
| inspection | 3 | `take_snapshot`, `evaluate_script`, `list_pages` |
| navigation | 1 | `navigate_page` |
| capture | 1 | `take_screenshot` |
| other | 4 | `new_page`, `close_page`, `select_page`, `resize_page` |

**DevTools-exclusive (no other comparison MCP exposes these):**

- `list_console_messages` / `get_console_message`
- `list_network_requests` / `get_network_request`
- `performance_start_trace` / `performance_stop_trace` / `performance_analyze_insight`
- `emulate_cpu` / `emulate_network`

**Were any of these called naturally during S1-S8?** No — across all 3 passes, the
chrome-devtools tool-call breakdown was: `evaluate_script`, `navigate_page`, `new_page`,
`take_snapshot`, `take_screenshot`, `fill_form`, `upload_file`. **Zero invocations of any
diagnostic or performance tool in any pass.** The S1-S8 walk's prompts don't ask for
network waterfalls or trace recordings, and the agent had no reason to reach for them.

**Implication for Phase 4 synthesis:** the DevTools-exclusive surface is **structurally
present and inventoried** (the score for "candidate exposes DevTools tools" is
unambiguously 10/10 against any other MCP in the matrix), but the **natural S1-S8 walk
does not surface a behavioral advantage** because the rubric doesn't grade on
network/performance/console probing. The CONTEXT.md "9th DevTools-Probe stage" idea
(deferred) is the path to turning the structural advantage into a scored one.

This is a clean negative result: chrome-devtools' unique tool surface exists and is
ready to use, but is NOT what made (or unmade) its S1-S8 row. The S4-S8 spread was
agent-strategy-driven, not chrome-devtools-capability-driven.

## Wall-clock budget posture

| | Time |
|---|---|
| PASS1 wall-clock | 5m51s |
| PASS2 wall-clock | 5m38s |
| PASS3 wall-clock | 10m08s |
| Total (3 passes) | 21m37s |
| Budget per pass | 60m |
| Single-pass fallback invoked? | **No** |

Pace for the remaining 5 MCPs (assuming similar wall-clocks): ~110 minutes if all run
sequentially with 3-pass median. Within plan budget; no time-budget escalation needed.

## Linear ticket

Per CONTEXT.md `## Decisions § Execution Order`, this row belongs under sub-ticket
**G-715** (chrome-devtools split of G-703). A summary comment will be posted via
`linearis comments create G-715` referencing this DEEP_ANALYSIS.md and the median row in
`scores.json`.

## Sources

- `results/2026-05-26/chrome-devtools/PASS{1,2,3}/` — per-pass evidence
- `results/2026-05-26/chrome-devtools/PASS{1,2,3}.json` — per-pass aggregated rows
- `results/2026-05-26/chrome-devtools/tools_inventory.json` — 29-tool inventory probe
- `results/2026-05-26/scores.json` — median row alongside playwright row
- `results/2026-05-26/chrome-devtools/.composite_check.txt` — `score_with_na.py` output

**Sacrosanct check:** `scoring/score.py` byte-for-byte unchanged
(`git diff main -- scoring/score.py | wc -l` returns 0).
