# S3 — Platform detection

Comparing the two fixtures observed in S1 and S2 (no re-fetching).

## Greenhouse — `http://127.0.0.1:8765/greenhouse_2026-05-22/...`

**Verdict: Greenhouse.** Distinguishing markers I saw via the browser-use MCP:

- **URL pattern** — `/greenhouse_2026-05-22/anthropic/jobs/5023394008.html`.
  Greenhouse public boards canonically route as
  `job-boards.greenhouse.io/<company>/jobs/<numeric-id>` and the wget capture
  preserved that path layout. The numeric job ID alone is a Greenhouse fingerprint;
  Ashby uses UUIDs.
- **DOM markers in the source HTML** (before React killed them): class names
  `job-post-container`, `job__title`, `job__location`, `job__tags`,
  `job__description`, `section-header section-header--large font-primary` — all
  standard Greenhouse public board styles. Stylesheet hrefs point to
  `job-boards.cdn.greenhouse.io/assets/entry-*.css` and `vendor-*.css`.
- **Form structure** — `<form method="get" action="5023394008.html"
  id="application-form" class="application--form" data-discover="true">` — the
  `application--form` class + `data-discover` attribute are Greenhouse Remix
  app conventions, and the form is colocated on the same page as the job
  posting (a Greenhouse design).
- **Apply form cue** — `<h2 class="section-header font-primary">Apply for this
  job</h2>` sits inside the same document as the job description, which is
  Greenhouse's single-page posting-plus-apply layout (Ashby splits these).
- **Page title pattern** — `"<First> <Last> for <Role> at <Company>"` is the
  Greenhouse stitched format that prepends a candidate's name when the route
  carries one. Ashby titles are plain (just `"Jobs"`).

## Ashby — `http://127.0.0.1:8765/ashby_2026-05-22/...`

**Verdict: Ashby.** Distinguishing markers:

- **URL pattern** — `/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html`.
  A 36-char UUID, not a numeric ID. Canonical Ashby is
  `jobs.ashbyhq.com/<org>/<uuid>`.
- **Hydrated footer links** (the only post-render evidence I had access to,
  since the page is empty pre-hydration): `Powered by` → `https://www.ashbyhq.com`,
  `Privacy Policy` → `https://www.ashbyhq.com/privacy`, `Security` →
  `https://www.ashbyhq.com/security`, `Vulnerability Disclosure` →
  `https://www.ashbyhq.com/disclosure`. All four point to
  `ashbyhq.com` — a definitive ATS fingerprint.
- **Rendering shape** — the source HTML is a 139-line hydration shell with
  almost no scrapable body content (title `"Jobs"`). Ashby is a true CSR SPA
  that fetches data from its own API after mount; Greenhouse SSRs the
  posting markup. browser-use confirmed this asymmetry: Greenhouse arrived
  with the form already in the DOM before React deleted it, Ashby arrived
  empty and stayed empty because its API was unreachable.
- **No form on page** — consistent with Ashby's design of having a separate
  `/application` sub-route for the apply step (not present in this fixture).

## Summary table

| Signal | Greenhouse | Ashby |
|---|---|---|
| URL ID format | numeric (`5023394008`) | UUID v4 (`1e1a651f-...`) |
| Vendor URL in DOM | `job-boards.cdn.greenhouse.io` | `ashbyhq.com` |
| Job DOM in source | yes (`job-post-container`, `job__*`) | no (CSR shell only) |
| Apply form layout | inline same-page | separate route |
| Page title pattern | `"<name> for <role> at <co>"` | `"Jobs"` |
| Render behavior under JS | React replaces body with "Page not found" | partial hydrate, no data |

Both detections are unambiguous from a single observation of each page; no
second fetch needed.
