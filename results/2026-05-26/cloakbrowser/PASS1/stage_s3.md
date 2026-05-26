# S3 — Platform Detection

**Method:** Static-HTML inspection of the two fixtures already loaded for S1/S2,
no re-fetch. Distinguishing markers below were captured via `cloak_evaluate(fetch
+ DOMParser)` in stages S1 and S2.

## Fixture A — `greenhouse_2026-05-22/anthropic/jobs/5023394008.html` → **Greenhouse**

Distinguishing markers:

1. **URL path shape:** `/{company}/jobs/{numeric_id}.html`. The numeric `5023394008`
   is Greenhouse's canonical 10-digit job ID. Ashby uses UUIDv4 (see Fixture B).
2. **Asset CDN:** Stylesheets pulled from `https://job-boards.cdn.greenhouse.io/`
   and a Greenhouse-branded logo from `s8-recruiting.cdn.greenhouse.io`. The
   `og:image` URL also lives on `s8-recruiting.cdn.greenhouse.io`.
3. **Canonical URL meta:** `<meta property="og:url" content="https://job-boards.greenhouse.io/anthropic/jobs/5023394008">`.
4. **Server-side rendered job body:** 84,577 bytes of static HTML containing
   `<main class="main font-secondary job-post">`, an explicit `<h1
   class="section-header section-header--large font-primary">`, location block,
   description, and an Apply `<button>` — i.e. Greenhouse SSRs the job and uses
   React only for the interactive layer.
5. **React mount portal:** `<div id="react-portal-mount-point"></div>` —
   Greenhouse's distinctive named mount node.
6. **Custom CSS variables in the body style attribute** matching Anthropic's
   brand palette (`--custom-link-color:#141413`, `--custom-active-field-color:#D97757`,
   etc.) — Greenhouse exposes employer-branding tokens as inline CSS vars on
   `<body>`, which Ashby does not.

## Fixture B — `ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html` → **Ashby**

Distinguishing markers:

1. **URL path shape:** `/{workspace}/{uuid_v4}`. `1e1a651f-693d-4f9d-bfd9-280a50d28d13`
   is a canonical UUIDv4 — Ashby's job-posting identifier scheme.
2. **Static HTML payload size:** 6,294 bytes total — a pure SPA shell with no
   inline job content, no `og:title`, no `og:description`, no JSON-LD island.
   Contrast with Greenhouse's 84KB SSR'd body.
3. **CSP nonce meta:** `<meta name="csp-nonce" content="zBraEcTzMv5IiEcOFmDNdvEfBIFzIbtUHTE6bzG2GQI">`
   — Ashby ships a per-request CSP nonce for inline scripts, which Greenhouse
   does not.
4. **Theme color:** `<meta name="theme-color" content="#483fad">` — Ashby's
   signature purple.
5. **Empty hydration target:** `#root` initially contains only loading-state CSS
   and a spinner; all content is fetched client-side from the Ashby JSON API
   (`api.ashbyhq.com/job-posting/<workspace>/<uuid>`) after JS boot.
6. **No SSR job content at all:** in the captured snapshot the job title,
   description, location, and apply form ALL come from a runtime XHR. That is
   the textbook Ashby architecture.

## Form-structure cues (hypothesized, since neither apply form was reachable
this run)

- **Greenhouse** apply forms are SSR'd HTML `<form action="/anthropic/jobs/5023394008">`
  with `<input name="first_name">` style fields and **React Select**
  comboboxes for source/location (which is exactly the wrinkle stage S7 calls
  out — `browser_select_option` against them fails because they aren't native
  `<select>`).
- **Ashby** apply forms are fully client-rendered from the JSON schema returned
  by `applicationFormDefinition`. Every input is a controlled React component
  with no semantic `name=` attribute matching the field key — selectors must
  go through `aria-label` or test IDs.

These cues alone — URL path shape (`{numeric}.html` vs `{uuid}`), CDN host,
SSR payload size, and presence vs absence of the `react-portal-mount-point`
node — are enough to classify either fixture without re-fetching.
