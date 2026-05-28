# S2 — Ashby JD extraction (browser-use)

**Target:** `http://127.0.0.1:8765/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html`

## Extraction result

`mcp__browser-use__browser_extract_content` → **No content extracted**.

`browser_get_html("h1")` returned `<h1 class="_title_ud4nd_34  ">Page not found</h1>`.

## Why

Ashby is a React SPA whose body renders client-side from an Ashby-hosted API. The captured static HTML is the React mount shell; when browser-use renders the JS without a live `ashbyhq.com` backend, hydration produces the in-app 404 fallback ("Page not found"). All visible interactive elements after hydration are footer links (Privacy Policy, Security, Vulnerability Disclosure, "Powered by Ashby").

## Comparison to S1

Both SPA platforms (Greenhouse + Ashby) collapse to the same in-app 404 under browser-use's JS-rendering profile against an offline static snapshot. This is the canonical "JS renderer vs. static SPA snapshot without backing API" failure mode.

If browser-use exposed a raw-HTML / pre-hydration tool it could still pull metadata; it does not. Its surface is render-then-read.

## Capability finding

For the rubric's "Ashby / SPA" dimension, browser-use is a structural fail on this fixture. Same as it would be for any JS-rendering MCP. Tools that read raw HTML (lightpanda raw fetch, firecrawl, obscura without JS) would do better here; tools that render JS (playwright, chrome-devtools, cloakbrowser, browser-use) would all hit the same 404.
