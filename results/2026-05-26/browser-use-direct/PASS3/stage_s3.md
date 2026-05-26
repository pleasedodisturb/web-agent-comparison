# S3 — Platform detection

**Without re-fetching**, comparing the two snapshots from S1 and S2.

## Snapshot A → **Greenhouse**

URL path: `/greenhouse_2026-05-22/anthropic/jobs/5023394008.html`

Distinguishing markers (from S1's `browser_get_html` dump):

1. **Inline `recruiting-logo` SVG**: the captured `<main>` contains a hand-rolled
   SVG with `class="recruiting-logo"` rendering the literal word
   "greenhouse" via per-letter `<path>` glyphs in the Greenhouse brand
   green (`#15372c` for "greenhouse", `#24a47f` for "recruiting"). No
   reference to an external CDN font or sprite — Greenhouse inlines its
   wordmark into every page so headless-but-image-blocked clients still
   render the brand. This is a stable Greenhouse signature.
2. **`<div class="flash-contents flash-contents--extra-light-red">`**
   wrapping a circular "i" icon and the body "The job board you were
   viewing is no longer active." — that DOM structure and class naming
   (`flash-contents--extra-light-red`, `font-secondary`, `icon--red`) is
   characteristic Greenhouse markup. Ashby's design system uses
   data-attribute-driven CSS, not `flash-*` class modifiers.
3. **URL pattern**: `/<company-slug>/jobs/<numeric-id>` with a numeric
   job id (`5023394008`). Greenhouse job IDs are monotonic 10-digit
   integers. Ashby uses UUIDv4 ids in URLs (see Snapshot B).
4. **Page text**: "Page not found" + "The job board you were viewing is
   no longer active." rendered server-side. Greenhouse renders this
   interstitial from the server tier even when the job has expired —
   useful for our purposes because Snapshot A is reachable as static HTML
   despite the live posting being dead.
5. **`<react-portal-mount-point>` div**: Greenhouse uses a single
   portal-mount-point at the top of the body for flash banners; the rest
   of the page is server-rendered. Ashby's root is `<div id="root">`
   (a Vite/React default).

## Snapshot B → **Ashby**

URL path: `/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html`

Distinguishing markers (from S2):

1. **`<div id="root">`** as the sole hydration target, paired with
   `<noscript>You need to enable JavaScript to run this app.</noscript>`
   — the Vite/React SPA shell pattern. Greenhouse's posting pages are
   server-rendered HTML, so they have content even with JS disabled.
2. **`cdn.ashbyprd.com`** preload directives: the head preloads
   `https://cdn.ashbyprd.com/frontend_non_user/<commit-sha>/.vite/manifest.json`
   plus three WhitneySSm font weights from the same CDN. The
   `ashbyprd.com` domain (Ashby Production CDN) is a hard fingerprint.
3. **URL pattern**: `/<company-slug>/<uuid>` — `1e1a651f-693d-4f9d-bfd9-280a50d28d13`
   is a canonical UUIDv4 (8-4-4-4-12 hex layout). Greenhouse uses
   numeric ids.
4. **`<meta name="theme-color" content="#483fad">`**: the purple
   `#483fad` is Ashby's brand colour, embedded as the iOS Safari address
   bar tint. Greenhouse doesn't ship a theme-color meta tag.
5. **CSP nonce in `<meta name="csp-nonce">`**: Ashby ships per-page CSP
   nonces; Greenhouse's portal does not (its CSP is header-based).
6. **Footer chrome only**: the rendered page shows just "Powered by
   Ashby / Privacy Policy / Security / Vulnerability Disclosure" — those
   four links are the Ashby boilerplate footer rendered by the SPA boot
   shell while it waits for hydration.
7. **`.grecaptcha-badge { visibility: hidden; }`** inline style:
   Ashby's apply pages embed reCAPTCHA v3 (invisible-badge variant); the
   stylesheet hint is in the shell HTML even before the form renders.

## Summary

| Marker                  | Greenhouse                       | Ashby                                  |
|-------------------------|----------------------------------|----------------------------------------|
| URL id format           | numeric (`5023394008`)           | UUIDv4 (`1e1a651f-...`)                |
| Server-rendered body    | yes (even on expired job)        | no — SPA shell only                    |
| CDN signature           | none (self-hosted assets)        | `cdn.ashbyprd.com`                     |
| React mount             | `react-portal-mount-point`       | `<div id="root">`                      |
| Theme colour            | none                             | `#483fad` (purple)                     |
| CSP                     | header-based                     | per-page `<meta name="csp-nonce">`    |
| Captcha hint            | none in shell                    | `grecaptcha-badge` style stub          |
| Footer brand            | inline `recruiting-logo` SVG     | "Powered by Ashby" link to ashbyhq.com |

Conclusion: Snapshot A is unambiguously **Greenhouse**, Snapshot B is
unambiguously **Ashby**. The two could be distinguished even from a
1-byte content-prefix in practice (the doctype + `<meta>` ordering
differs), but the markers above are robust to incidental whitespace
changes.

## MCP note

This stage required only reasoning over already-captured snapshots — no
`mcp__browser-use__*` call was needed beyond what S1 and S2 already did.
The browser-use MCP's `browser_get_html` (used in S1) and the headless
hydration attempt (S2) were sufficient to surface the markers above.
