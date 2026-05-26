# obscura — stage walk transcript (2026-05-26)

## Headline

**Run terminated at S1 due to architectural incompatibility with the loopback methodology.** Obscura's server enforces an SSRF block that rejects all requests to private/internal IPs (including `127.0.0.1`). The harness serves fixtures at `http://127.0.0.1:8765/`, so no Obscura tool that performs a fetch can reach them. This is the same failure shape recorded for `firecrawl` in the 2026-05 PASS runs — both MCPs route through a hosted backend rather than executing the browser on the local machine.

## Tools available on the obscura surface

| Tool | Purpose | Reached snapshot server? |
|---|---|---|
| `mcp__obscura__browse_page` | one-shot fetch + extract (text/markdown/html/links/axtree/layout) + eval | NO — SSRF block |
| `mcp__obscura__browse_scrape` | bulk parallel scrape with eval | NO — SSRF block (worker returned identical error) |
| `mcp__obscura__browse_session` | multi-step session (create/goto/wait/click/type/extract) | `create` succeeded; `goto` rejected with same SSRF error |
| `mcp__obscura__browse_interact` | one-shot click/type | Not exercised — depends on a URL fetch that would hit the same block |

No screenshot primitive. No file-upload primitive. Even if loopback worked, S6 (upload) and S8 (screenshot) would still be `NA`.

## Per-stage outcome

| Stage | Verdict | Evidence |
|---|---|---|
| S1 — extract Greenhouse | **FAILED** | `browse_page(...greenhouse...)` → `Access to private/internal IP address 127.0.0.1 is not allowed` |
| S2 — extract Ashby (SPA) | **FAILED** | `browse_page(...ashby...)` → same SSRF error |
| S3 — platform detection | **FAILED** | Cannot reason from empty S1/S2 output |
| S4 — navigate to apply form | **FAILED** | `browse_session.goto` rejected loopback (session create succeeded; the block applies at request dispatch, not session init) |
| S5 — fill form | **NA** | No form reached in S4; Obscura has no batch-fill primitive analogous to Playwright `browser_fill_form` |
| S6 — upload resume | **NA** | Obscura exposes no file-upload primitive |
| S7 — source dropdown | **NA** | No form reached; eval-driven React-Select pattern would have been viable on a reachable page |
| S8 — screenshot | **NA** | Obscura exposes no screenshot primitive |

## What worked

- `browse_scrape` verified that the SSRF block also applies to parallel workers, not just single-page fetches (per-URL `error` field returned identically).
- `browse_session.create` succeeded against a loopback URL, suggesting the SSRF check runs at request dispatch rather than at session bring-up. This is useful intel for future runs that need to test session-level features against public targets.
- Tool-allow-list discipline preserved: only `mcp__obscura__*`, `Read`, `Write`, `Bash` invoked. No `WebFetch` reach.

## What failed and why

- **Loopback rejection is the dominant signal.** Obscura is a hosted-engine MCP (similar to firecrawl); its workers run outside the loopback boundary and refuse to dial back into a private address space. The snapshot-server methodology — which is essential to fair, deterministic, offline benchmarking — is fundamentally incompatible with hosted-engine MCPs. The G-703 PASS runs for firecrawl already documented this; obscura repeats it.
- **No screenshot, no upload.** Two stages (S6, S8) are unreachable on capability grounds independent of the network block. Obscura is positioned as a server-rendered scraper, not a full browser-automation MCP, and the surface reflects that.

## Caveats and recommendations

- **Fair-scoring interpretation:** This is not an obscura bug; it is a methodology/surface mismatch. The rubric should record this as a category-level incompatibility ("hosted-engine MCP vs. loopback fixtures") and either (a) score obscura on the *public-URL* variant of the fixtures hosted at a public domain, or (b) accept the partial score and document the architectural reason in the synthesis ticket.
- **What obscura would likely score well on** if pointed at a public fixture mirror: S1 (server-rendered Greenhouse), S2 (would still likely 0-out on Ashby SPA — Obscura's `markdown` format relies on rendered DOM, but its JS execution depth is unclear in this surface), S3 (URL-pattern + DOM-marker reasoning), S5/S7 (eval hook gives React-Select access). S4 is doable via `browse_session`. S6 and S8 remain NA on capability grounds.
- **Sandbox/cookie note:** Obscura's `cookies` parameter on `browse_page` could in principle re-inject session state for authenticated targets, but the global rule "never point at authenticated host pages" still applies to closed-source/hosted browsers — and is moot here since the loopback target carries no auth surface.
