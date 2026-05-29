# S8 — Screenshot

- **Tool:** `mcp__browsermcp__browser_screenshot` (no arguments)
- **Returned:** PNG, inline base64 in the tool result (no `path` parameter
  exists on this MCP — unlike Playwright's `browser_take_screenshot` which
  writes to disk). The harness's `raw_stream.jsonl` preserves the actual
  image bytes for the scorer.
- **Page captured:** the Greenhouse "Page not found" view at
  `http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html`
  — NOT a filled form, because S4–S7 all failed (Chrome's JS hydration
  replaced the SSR application form with the not-found view).
- **Visual content:** `greenhouse Recruiting` logo top-left, centered
  "Page not found" heading and "The job board you were viewing is no
  longer active." paragraph. Roughly viewport-sized capture, not full
  page (BrowserMCP exposes no `fullPage` flag).

## Limitation noted

This MCP has no surface for either:
1. Writing the screenshot to a file path directly (only inline return).
2. Capturing full-page screenshots (only the viewport).

For comparison the Playwright MCP's `browser_take_screenshot` supports
both; the BrowserMCP gap costs against Playwright on
`results-fidelity` (rubric dim. 4) and `harness-ergonomics`
(rubric dim. 6).
