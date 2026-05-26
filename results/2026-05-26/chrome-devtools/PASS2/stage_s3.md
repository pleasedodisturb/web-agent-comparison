# S3 — Platform Detection

**Method:** Visual + structural comparison of the two snapshots from S1 and S2.
No re-fetching; reasoning works only from artifacts already captured.

## Snapshot A → Greenhouse

URL: `http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html`

Discriminating evidence:

- **URL pattern:** `/anthropic/jobs/<numeric-id>` — Greenhouse uses an integer job
  ID (`5023394008`) and a flat `/<org>/jobs/<id>` layout. The og:url meta
  resolves to `job-boards.greenhouse.io/anthropic/jobs/5023394008`, which is
  the canonical Greenhouse hosted-board host.
- **Server-rendered HTML:** 84,577 bytes with full job content present pre-hydration
  — Greenhouse SSRs the posting body. The React app hydrates over it and, on a
  loopback snapshot without API access, falls back to an "expired board" UI.
- **CDN asset hosts:** `s8-recruiting.cdn.greenhouse.io`,
  `job-boards.cdn.greenhouse.io`, plus the canonical-Greenhouse `StyreneALC-Medium`
  custom font.
- **DOM markers:** `.job-post`, `.job-post-container`, `.job__header`,
  `.job__location`, `button[aria-label="Apply"]`, `.section-header--large` —
  Greenhouse's job-board renderer's stable class names.
- **Apply pattern:** A single `<button aria-label="Apply">` in the header
  (Greenhouse's apply button is JS-driven; clicking it routes to a hosted
  application form at the same hostname).

## Snapshot B → Ashby

URL: `http://127.0.0.1:8765/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html`

Discriminating evidence:

- **URL pattern:** `/replit/<uuid>` — Ashby uses a UUID for the posting ID and
  a `/<org-slug>/<uuid>` layout. UUIDs vs. integer IDs is the cleanest single
  signal between the two ATSs.
- **Empty shell:** 6,294 bytes total. Body has `<div id="root">` and a
  `<noscript>` banner. Zero job content in the static HTML — Ashby is a pure
  CSR React SPA whose content is fetched at runtime from
  `https://jobs.ashbyhq.com/...` API endpoints.
- **CDN asset hosts:** `cdn.ashbyprd.com` (Ashby production CDN).
- **Inline bootstrap:** `window.__appData = { ddRumApplicationId, ddRumClientToken,
  organization, posting, jobBoard, routerPrefix, recaptchaPublicSiteKey, ... }`
  — this `__appData` global is an Ashby-specific bootstrap shape. Greenhouse
  uses a different bootstrap mechanism (server-rendered `<main>` content, no
  `__appData` global).
- **Footer chrome (rendered after SPA mount):** "Powered by / Privacy Policy /
  Security / Vulnerability Disclosure" — Ashby's standard footer chrome that
  renders even on the not-found view.

## Single-glance discriminators

| Signal | Greenhouse | Ashby |
|---|---|---|
| Job-ID shape | integer (`5023394008`) | UUID (`1e1a651f-…`) |
| URL path | `/<org>/jobs/<id>` | `/<org>/<uuid>` |
| Static HTML size | ~85 KB (SSR) | ~6 KB (shell only) |
| Bootstrap global | none (SSR) | `window.__appData` |
| CDN host | `*.greenhouse.io` | `cdn.ashbyprd.com` |
| Apply pattern | `button[aria-label="Apply"]` in header | hosted form at same `/<org>/<uuid>` path under SPA route |

Either of the top two rows alone (job-ID shape OR static-HTML size) is sufficient
to identify the platform unambiguously without inspecting page content.
