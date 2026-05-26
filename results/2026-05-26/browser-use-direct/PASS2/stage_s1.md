# S1 — Greenhouse JD extraction (browser-use)

**Target:** `http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html`

## Extraction result (via browser-use primitives)

`mcp__browser-use__browser_extract_content` → **No content extracted** (returned twice, with and without `extract_links`).

## Why

browser-use renders JavaScript. The Greenhouse fixture is the captured React SPA shell; on hydration without a live `job-boards.greenhouse.io` backend it falls back to the in-app 404 ("Page not found / The job board you were viewing is no longer active"). The body that browser-use sees post-hydration contains only the Greenhouse logo SVG + the `<h3>Page not found</h3>` error block. The static JD content (title, location, Apply button, role description) is in the source HTML but is wiped by React mount.

Evidence: `browser_get_html("body")` returned only the recruiting-logo SVG + the `error-message` block with "Page not found".

## What IS reachable (from `<head>` metadata, persisted past hydration)

| Field | Value | Source |
|---|---|---|
| Title (page) | `Jane Testworth for Jane Testworth Program at Anthropic` | `<title>` via `browser_get_state.title` |
| Title (role) | `Jane Testworth Program` | static `<meta property="og:title">` (NOT extractable via browser-use's surface — only via inspecting the raw HTML file out-of-band) |
| Location | `London, UK; Ontario, CAN; Remote-Friendly, Jane Testworth; Jane Testworth, CA` | static `<meta property="og:description">` (same caveat) |
| Canonical URL | `https://job-boards.greenhouse.io/anthropic/jobs/5023394008` | static `<meta property="og:url">` (same caveat) |
| Company | Anthropic | inferred from URL path |
| Apply URL | not reachable post-hydration (the live JD would have `?gh_jid=...` or `/jobs/<id>/applications` link) | n/a |
| Employment type | not present in metadata | n/a |
| Salary band | not present in metadata | n/a |
| Requirements | only `<h1>/<h2>` skeletons in source (the body text is mocked with "Jane Testworth" tokens) | n/a |

## Capability finding for the rubric

browser-use **fails Greenhouse SPA extraction against this fixture** for the same structural reason a headless JS browser fails any SPA without its backing API. This is shared with playwright/chrome-devtools/cloakbrowser — anything that runs the React mount will see the 404 fallback. The non-JS path (raw HTML scrape / firecrawl / lightpanda raw) would see more, but browser-use does not expose that surface.

This is not a tool bug; it is a JS-renderer-vs-static-SPA-snapshot mismatch, and is the expected behavior to document for this MCP class.
