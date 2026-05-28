# browser-use MCP — S1-S8 transcript (2026-05-26)

**MCP under test:** `browser-use` (Python `browser-use` 0.12.7, `--mcp` stdio
transport, real Playwright Chromium).
**Snapshot server:** `http://127.0.0.1:8765` (loopback, serving
`fixtures/snapshots/`).
**Allow-list:** `mcp__browser-use__*`, `Read`, `Write`, `Bash`. No WebFetch,
no other MCPs touched.

## Per-stage outcome

| Stage | Verdict | Artifact | Tools used |
|---|---|---|---|
| S1 — extract Greenhouse | partial (post-render DOM destroyed) | `stage_s1.yml` | `browser_navigate`, `browser_get_state`, `browser_extract_content`, `browser_get_html` |
| S2 — extract Ashby SPA | empty (expected; no backend API) | `stage_s2.yml` | same as S1 |
| S3 — platform detection | done from S1/S2 observations | `stage_s3.md` | (no MCP calls — reasoning over prior state) |
| S4 — navigate to apply form | **FAILED** — form destroyed on render | `stage_s4.FAILED` | `browser_navigate`, `browser_get_state` |
| S5 — fill form | **FAILED** — downstream of S4 | `stage_s5.FAILED` | n/a (no form fields reachable) |
| S6 — upload resume | **FAILED** — downstream of S4 | `stage_s6.FAILED` | n/a |
| S7 — source dropdown | **FAILED** — downstream of S4 | `stage_s7.FAILED` | n/a |
| S8 — screenshot + transcript | done | `stage_s8.png` (48 KB), this file | `browser_screenshot(full_page=true)` |

## Root cause of the S4-S7 cascade

The Greenhouse snapshot
(`fixtures/snapshots/greenhouse_2026-05-22/anthropic/jobs/5023394008.html`)
is a wget capture of a Greenhouse posting that retains absolute references
to `job-boards.cdn.greenhouse.io/assets/entry-*.css` and the React/vendor
JS bundles. The wget snapshot does NOT freeze the JS — Greenhouse's React
app runs on load, evaluates its router, decides the current URL is not a
valid posting route, and replaces `<body>` with:

```html
<main class="main">
  <svg class="recruiting-logo">…</svg>
  <div class="error-message font-secondary">
    <h3 class="section-header font-primary">Page not found</h3>
    <div class="job-board-inactive">
      <p class="body">The job board you were viewing is no longer active.</p>
    </div>
  </div>
</main>
```

The original `<form id="application-form" class="application--form">`, all
its inputs, and the React-Select source combobox vanish before the first
tool call lands. `browser-use`'s `browser_get_state` reports just 2
elements (a span and an SVG) post-render, vs. 100+ in the source. The
screenshot in `stage_s8.png` captures the final visual state — a near-
empty page with the Greenhouse Recruiting logo and the "Page not found"
text — and is the definitive evidence.

Implication: any JS-executing MCP (browser-use, playwright,
chrome-devtools, cloakbrowser, obscura) will hit the same wall on this
fixture. Only no-JS fetchers (lightpanda, firecrawl scrape mode) get the
form because they never run the bundle. This is a real benchmark axis,
not an MCP bug — it's the cost of having a "real" browser when the
fixture's own JS turns hostile.

## browser-use surface quirks observed

- **`browser_extract_content` returned "No content extracted" four times
  out of four** across both fixtures, with several different prompt
  framings. Whether this is because the underlying browser-use
  page-content extractor refuses to score a near-empty post-render DOM, or
  whether it requires an LLM key to be set on the MCP server itself, is
  unclear from the surface. Either way, the tool wasn't useful on these
  fixtures — `browser_get_html` (no selector) was a more honest read.
- **`browser_get_html` with a CSS selector returned "No element found"**
  even for selectors present in the source HTML (`h1`,
  `.job-post-container`). This is consistent with the post-render
  DOM-destruction story — the selectors really aren't there at query
  time. Not a bug, but worth noting for the scoring rubric: selector-based
  retrieval on this MCP is only as good as the page state after all JS
  settles.
- **`browser_get_html` with no selector** is the most reliable read; it
  returned the full post-render HTML for both fixtures.
- **`browser_get_state`** lists indices reliably, but its `text` fields
  were almost all empty strings here because the visible labels
  ("Powered by", "Privacy Policy" etc.) only attached after Ashby's
  partial hydration.
- **`browser_screenshot`** worked first try, full-page, ~48 KB PNG.
  Returned the image inline as a message attachment rather than writing
  to disk; persisted via `Bash` + a small Python decode of the harness's
  `raw_stream.jsonl`.

## Caveats / what was NOT exercised

- `retry_with_browser_use_agent` (the LLM-agent fallback) was not invoked.
  It would not have changed the outcome — the form node truly is missing
  post-render, no amount of agent reasoning conjures it back — and it
  would have added an out-of-band LLM call that the harness allow-list
  was not provisioned for.
- The Ashby fixture's missing backend means S2 was never going to extract
  job data on any MCP; that's the negative-control axis (graceful
  empty-handling).
- No interaction-level scoring was possible on S5/S6/S7 with this MCP on
  these fixtures.

## Tool-call summary

```
mcp__browser-use__browser_navigate          5  (3 unique URLs + 2 reloads)
mcp__browser-use__browser_get_state         4
mcp__browser-use__browser_extract_content   4  (all returned "No content extracted")
mcp__browser-use__browser_get_html          4  (1 full-page, 3 selector-based; 2 of 3 selectors "not found")
mcp__browser-use__browser_click             1  (directory-index drill-down)
mcp__browser-use__browser_screenshot        1  (full_page=true, 48 KB)
mcp__browser-use__retry_with_browser_use_agent  0
```

No tools outside the allow-list (`mcp__browser-use__*`, `Read`, `Write`,
`Bash`) were called.
