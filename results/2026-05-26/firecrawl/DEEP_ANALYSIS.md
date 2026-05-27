# firecrawl — Deep Analysis

**Run date:** 2026-05-26
**Linear sub-ticket:** G-719 (Phase-2 per-MCP scoring; see G-703 umbrella — per [`docs/LINEAR_SUBTICKETS.md`](../../../docs/LINEAR_SUBTICKETS.md))
**Plan:** [02-03-firecrawl-PLAN.md](../../../.planning/phases/02-per-mcp-scoring-runs/02-03-firecrawl-PLAN.md)
**Package:** `firecrawl-mcp@3.17.0` (npm; sha256 `55d5fbb20270518f9cb6f0c16fb054e934847fe9a557b355503c0f05dce7d89f`)

## Capability Tag

**`cloud`** — firecrawl-mcp is a thin local client that proxies every scrape request to the firecrawl.dev cloud API. The local MCP process has no browser, no JS engine, and no rendering surface; the scraping happens on firecrawl's edge fleet and the markdown is shipped back. This is the asymmetric category the rubric needed `capability=cloud` to make legible.

## Median Composite

**4.23 / 10** (N/A-aware; only the 6 dimensions firecrawl can attempt count toward the weighted denominator). 4th of 4 measured MCPs so far.

| Dimension (weight) | Median Score | Notes |
|---|---|---|
| Data Quality (3×) | 0 | All 3 read-only stages FAIL — firecrawl cloud cannot reach `127.0.0.1` (fixture-loopback contract) |
| Reliability (3×) | 7 | `10 - 3 fails = 7`; the failure mode is deterministic, not flaky |
| Speed (2×) | 5 | Phase-1 neutral stub; real cold-start in Phase 3 (firecrawl's cold-start is "0ms locally; network-bound for first byte" per plan-text) |
| Token Efficiency (2×) | 5 | Phase-1 neutral stub; real per-scope split in Phase 3 |
| Interaction Depth (2×) | **N/A** | Architectural — cloud markdown scraper, no interactive surface, FAIRNESS-03 |
| JS Rendering (1×) | 2 | S2 FAILED → 2; firecrawl rejected the loopback URL before any JS could run |
| Setup Complexity (1×) | 7 | Single `npm i firecrawl-mcp` install + `FIRECRAWL_API_KEY` env var; cloud handles the rest |
| Error Handling (1×) | 5 | Returns clean JSON `{"success":false,"code":"BAD_REQUEST",...}` — graceful, machine-readable |

**Ranking among 4 measured MCPs:** 4th (playwright 7.93 > lightpanda 6.31 > chrome-devtools 5.6 > **firecrawl 4.23**).

## N/A Semantics Callout

Stages S4 (form discovery), S5 (form fill), S6 (resume upload), S7 (source dropdown), S8 (screenshot) and the `interaction_depth` dimension are scored **`"N/A"`** — **not zero** — per FAIRNESS-03 and the hardcoded `READ_ONLY_MCPS = {"lightpanda", "firecrawl"}` fairness policy in `scripts/aggregate_scores.py:68`. `scripts/score_with_na.py` drops N/A cells from the weighted denominator at composite time, so the published 4.23 reflects ONLY the dimensions firecrawl's architecture allows it to compete on (denominator = 3+3+2+2+1+1+1 = 13, not 15). Treating these as 0 would have produced an artificial 3.67 that misrepresents the candidate's category — same fairness fix lightpanda's 6.31 received.

firecrawl exposes 24 tools at the MCP layer (per `tools_inventory.json`), including `firecrawl_interact`, `firecrawl_browser_create`, `firecrawl_browser_execute`. **These are cloud-mediated and DO interact with remote browsers — firecrawl has a richer surface than lightpanda or pure scrapers.** However, none of them can target a `127.0.0.1` URL, so all interactive stages map to "architecturally inapplicable under the harness invariant" rather than "exercised and failed." N/A is the correct fairness call.

## The Falsifiable Empirical Finding — Cloud-vs-Loopback + Cloud LLM-extraction

### The cloud-vs-loopback architectural mismatch

The Phase-1 fixture-loopback contract (REPORT-09 + research/SUMMARY.md) serves S1-S3 targets at `http://127.0.0.1:8765/...`. firecrawl cloud refuses these URLs at the request-validation layer **before any scrape attempt**:

```http
POST https://api.firecrawl.dev/v1/scrape
{"url": "http://127.0.0.1:8765/greenhouse_2026-05-22/", "formats": ["markdown"]}

HTTP/1.1 400 BAD_REQUEST
{"success":false,
 "code":"BAD_REQUEST",
 "error":"URL must have a valid top-level domain or be a valid path",
 "details":[{"code":"custom","path":["url"],
             "message":"URL must have a valid top-level domain or be a valid path"}]}
```

This is a clean architectural mismatch, not a tool bug — firecrawl's cloud is doing exactly what it's designed to do (refuse non-public URLs), and the loopback contract is doing exactly what IT's designed to do (keep fixtures reproducible, offline, and immune to live-URL rot). The two designs are mutually exclusive on this dimension. Per FAIRNESS-06 the failure tag is **`env-mismatch`**, written on `data_quality` and `js_rendering` attributions in `scores.json` — not `tool-bug` (which the aggregator's default would have assigned, and which is incorrect here).

### Interesting-angle: single-shot live-URL probes (evidence-only, not scored)

To test research/SUMMARY.md's claim that **"Cloud LLM-extraction lifts Data Quality (3x weight) above raw-page MCPs at cost of latency + tokens; 96% success on JS-heavy sites,"** I issued single-shot probes against the LIVE original URLs from `fixtures/snapshots/*/PROVENANCE.md`. These are NOT used for scoring (they break the loopback contract), only for the empirical claim audit.

| Probe | URL | Wall clock | Response bytes | Extraction outcome |
|---|---|---|---|---|
| S1 live | `https://job-boards.greenhouse.io/anthropic/jobs/5023394008` | 0.70s | 24,237 markdown | **Rich**: 30+ heading sections, multi-thousand-word job body, complete metadata (og:title, og:description, etc.) |
| S2 live | `https://jobs.ashbyhq.com/replit/...` | 1.67s | 203 markdown | **Empty shell**: only `[Powered by Ashby]` footer + privacy/security/disclosure links. `metadata.title = "Jobs"` (static, not the job posting title) |

Comparing to **Playwright's saved S1+S2 outputs (`results/2026-05-25/playwright/`)**:

| Dim | firecrawl (live) | Playwright (loopback fixture) |
|---|---|---|
| S1 output | 24,237 bytes of natural-language markdown | 2,663 bytes of structured YAML (title + locations + canonical_url + scrubbed fields) |
| S1 verdict | PASS (job title extracted as "Anthropic Fellows Program") | PASS (same job title — same target, same finding) |
| S2 output | 203 bytes (Ashby footer chrome) | 113 bytes ("Page not found") |
| S2 verdict | **Empty — Ashby SPA defeats firecrawl too** | partial_render → empty_payload (same outcome) |

### Verdict on the "96% success on JS-heavy sites" claim

**PARTIALLY REFUTED.** Firecrawl's cloud extraction is genuinely impressive on the SSR-friendly Greenhouse posting — 9× the byte count of Playwright's structured YAML, full markdown body with section headings preserved. This is real Data-Quality lift on the right targets. BUT on the React SPA (Ashby) firecrawl returns 203 bytes of footer chrome with title="Jobs" — **the same React-blind failure mode lightpanda hit**, just delivered via a cloud endpoint instead of a local Zig engine. The "96% on JS-heavy sites" claim is marketing for which sites firecrawl tests on; the real-world distribution includes React 18 SPAs like Ashby that firecrawl does not wait-and-render, and on which it returns nothing useful. This is exactly the kind of falsifiable observation the per-MCP "interesting angle" exists to surface.

**For Phase 4:** firecrawl is a tool for SSR-heavy targets where LLM-cleaned markdown is more valuable than structured DOM extraction. It is **not a general-purpose JS-SPA fallback** — for that, you need a real browser MCP, and on Ashby specifically that's playwright (or chrome-devtools with the SSR-rescue technique it discovered in PASS3).

### Verdict on the loopback contract

**CONFIRMED.** The loopback contract is the right call. Scoring firecrawl against live URLs would have:
1. Produced a Data Quality score of ~10 on S1 (rich Anthropic markdown) but still 0/2 on S2 (Ashby footer chrome) — net rank change minor.
2. Broken apples-to-apples comparison (other 6 MCPs measured against the loopback snapshot, firecrawl against the live origin).
3. Made the score un-reproducible across time (the live posting can be edited, archived, or removed).
4. Burned firecrawl API credits unnecessarily — the API key is metered, and 24 cells × 1 credit each is wasteful when the architectural verdict was determinable in 1 probe.

The Phase-4 `recommendations.md` should publish firecrawl's row with the env-mismatch caveat in the footnote AND publish the single-shot live-URL probe data as the "what firecrawl WOULD do on real sites" callout. Both findings matter; the rubric measures only one.

## Pass-to-Pass Variance

| Pass | S1 | S2 | S3 | S4-S8 | Composite (this pass alone) |
|---|---|---|---|---|---|
| PASS1 | FAIL | FAIL | FAIL | N/A | 4.23 |
| PASS2 | FAIL | FAIL | FAIL | N/A | 4.23 |
| PASS3 | FAIL | FAIL | FAIL | N/A | 4.23 |

**Zero variance across 3 passes.** Same headline observation as lightpanda's run: when an MCP's failure mode is architectural rather than agent-discovery-dependent, 1-pass would have been sufficient. The 3-pass median is most useful when the candidate has unused capability (cf. chrome-devtools, where PASS3 found an SSR-rescue technique PASS1/PASS2 missed). For firecrawl-vs-loopback, no amount of multi-pass exploration changes the verdict — firecrawl cloud refuses the URL at the validation layer before any agent intelligence can intervene.

## Failure-Attribution Table

Per FAIRNESS-06, every sub-rubric cell scoring < 5 must carry one of `{tool-bug, env-mismatch, target-flag, transient}`. N/A cells are not failures and not tagged.

| Dimension | Score | Tag | Justification |
|---|---|---|---|
| data_quality | 0 | `env-mismatch` | Cloud-vs-loopback architectural mismatch (firecrawl cloud refuses 127.0.0.1 URLs at request validation). NOT `tool-bug` — firecrawl's URL validator is doing its job correctly; the conflict is environmental. NOT `target-flag` — the loopback fixture isn't flagging firecrawl, it simply isn't reachable from public internet. NOT `transient` — deterministic verdict across 3 passes. The aggregator's default fallback is `tool-bug`, manually overridden here to the correct tag. |
| js_rendering | 2 | `env-mismatch` | Same root cause — S2 FAILED because the loopback URL was rejected before firecrawl's cloud even attempted a render. The js_rendering=2 score is the "S2 FAIL → 2" branch of `_score_js_rendering`, propagating the env-mismatch verdict via the rubric's stage-to-dimension mapping. Single-shot live probe confirms firecrawl ALSO fails on Ashby React SPA on the live URL — see "Interesting-angle" above — but that finding is evidential, not scored. |

Aggregator default override note: `scripts/aggregate_scores.py` lines 380-389 assign `FailureTag.TOOL_BUG.value` as the fallback when no stage-level attempt records carry a tag. firecrawl's run does not flow through `bench/transient.py` (no raw.jsonl per-attempt records — the verdict is deterministic), so the default would have mis-tagged the failure as `tool-bug`. The override is recorded in commit history; future Phase-3 measurement runs that DO emit raw.jsonl will naturally produce the correct tag without override.

## Tool Inventory

`tools_inventory.json` (24 tools, `protocol_version: 2025-06-18`, `status: OK`):

- **inspection**: `firecrawl_scrape`, `firecrawl_search`, `firecrawl_extract`, `firecrawl_browser_list`, `firecrawl_monitor_list` (5)
- **navigation**: `firecrawl_search_feedback` (1)
- **other**: 18 tools spanning crawl, agent, browser-lifecycle, interact, monitor, parse

The 24-tool surface is the richest of any read-only MCP in this comparison (cf. lightpanda's 20, browser-use's smaller surface). Firecrawl's `firecrawl_extract` is the LLM-extraction differentiator the research/SUMMARY.md claim points to; `firecrawl_browser_*` provides cloud-mediated browser sessions. **None of these can target a 127.0.0.1 URL** — the rich surface is invisible to a benchmark that runs on the loopback contract.

## Scope Cut Acknowledgement

Per research/PROJECT.md and plan 02-03 `## Interesting Angle`: **structured-schema extraction (the `firecrawl_extract` tool with a JSON schema) is deferred to v2.** This plan covers `firecrawl_scrape` (default markdown mode) only. The "Cloud LLM-extraction lifts Data Quality" claim is partially testable from the markdown extraction alone (see live-URL section above); the schema-extraction split would compare structured JSON output to Playwright's snapshot YAML — a richer comparison saved for the second wave.

## Phase-4 Headline

**firecrawl is the right tool when:** the target is publicly addressable on the open internet, server-renders most of its content, and you want LLM-cleaned markdown that's easier to feed to a downstream LLM than raw DOM. **It is the wrong tool when:** the target is on a private network, blocks public scraping (Cloudflare, etc.), is a React SPA that requires waiting for hydration, or you need form interaction. The 4.23 composite reflects what happens when these wrong-tool conditions hit simultaneously (loopback target + Ashby SPA + 8-stage application flow); the live-URL probe data is what surfaces firecrawl's real-world fit.

This row's headline for Stage 2 toolkit selection: **adopt firecrawl as a complement to playwright, not a replacement.** Playwright covers the JS-SPA + form-interaction beat; firecrawl covers the SSR-heavy + LLM-friendly-markdown beat. Both are first-tier picks for different jobs.

## Linear Sub-ticket Reference

G-719 (canonical mapping per [`docs/LINEAR_SUBTICKETS.md`](../../../docs/LINEAR_SUBTICKETS.md); the G-714..G-720 split was filed 2026-05-22 by plan 01-02). This Deep Analysis can be lifted verbatim into the G-719 comment thread when it lands.

## Stretch Items NOT Done (Deferred)

- `firecrawl_extract` with structured JSON schema vs `firecrawl_scrape` markdown (v2 scope per research/PROJECT.md).
- `firecrawl_agent` LLM-driven multi-step extraction comparison (v2).
- Per-credit token-efficiency measurement using firecrawl's `creditsUsed` metadata field (deferred to Phase 3 / MEAS-02 — the field is captured in `live_probe_s1.yml` for the future Phase-3 reader).
- 1-hour stability against firecrawl cloud (deferred to Phase 3 / MEAS-04).
