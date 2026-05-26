# S3 — Platform detection (no re-fetch)

Comparing the artifacts gathered in S1 and S2.

## Snapshot 1 → Greenhouse (Anthropic posting `5023394008`)

URL pattern, DOM markers, and form-related cues:

- **URL shape:** `/greenhouse_2026-05-22/anthropic/jobs/5023394008.html` — flat numeric
  job ID, parent path is the company slug, top path segment names the ATS. Greenhouse's
  live URLs follow `https://job-boards.greenhouse.io/{org}/jobs/{numeric_id}` — the
  fixture preserves that shape.
- **`og:url` in HTML:** `https://job-boards.greenhouse.io/anthropic/jobs/5023394008` —
  conclusive ATS identifier.
- **CDN bundles:** stylesheet href starts with `https://job-boards.cdn.greenhouse.io/`.
  CSS asset filenames (`entry-rL0h39AS.css`, `vendor-da5IcPkB.css`) are Greenhouse's Vite
  build outputs.
- **Greenhouse-isms in DOM:** custom CSS variables prefixed `--custom-link-color`,
  `--custom-active-field-color`, `--custom-primary-typography-color` etc. — Greenhouse's
  per-tenant theming hook.
- **Footer logo:** `external_greenhouse_job_boards/logos/.../original/2025-04-07-greenhouse.png`.
- **SSR content present:** the HTML ships the full job description inline inside
  `<main class="main font-secondary job-post">…</main>` (recoverable even though the
  React app overrides it at hydration time).
- **Form structure cue (from S5 prep):** Greenhouse apply forms typically use a
  React Select combobox for "How did you hear about us?" — NOT a native `<select>`
  (see S7).

## Snapshot 2 → Ashby (replit posting `1e1a651f-693d-4f9d-bfd9-280a50d28d13`)

- **URL shape:** `/ashby_2026-05-22/replit/{uuid}.html` — UUID-style job ID, parent
  path is company slug, top path segment names the ATS. Ashby's live URLs follow
  `https://jobs.ashbyhq.com/{org}/{uuid}` — matches.
- **CDN bundles:** dynamic bundle loader points at
  `https://cdn.ashbyprd.com/frontend_non_user/{commit-sha}/.vite/manifest.json` — Ashby's
  production CDN. Conclusive.
- **Embedded boot payload:** `window.__appData = {ddRumApplicationId, ddRumClientToken,
  recaptchaPublicSiteKey, organization, posting, jobBoard, customDomainData}` — Ashby's
  signature SPA-bootstrap object.
- **Ashby-isms in DOM:** `meta[name="theme-color"]` set to `#483fad`, footer "Powered by
  Ashby" link to `https://www.ashbyhq.com/`, Privacy/Security/Vulnerability Disclosure
  links to `ashbyhq.com/{path}`.
- **SSR content absent:** primary HTML is a 6.3 KB shell with a `noscript` "You need to
  enable JavaScript" banner and an empty `<div id="root">` — listing content is fetched
  at runtime via the React bundle (per PROVENANCE.md).
- **Form structure cue:** Ashby apply forms are colocated under the same SPA route
  prefix (`routerPrefix: "/"` in __appData) — not visited in this stage walk because
  the SPA never hydrated past "Page not found" without a live API.

## Distinguishing markers — summary table

| Signal | Greenhouse (S1) | Ashby (S2) |
|---|---|---|
| Top URL segment | `/greenhouse_2026-05-22/...` | `/ashby_2026-05-22/...` |
| Job ID shape | numeric (10 digits) | UUID v4 |
| `og:url` | `job-boards.greenhouse.io/...` | absent (no OG tags shipped) |
| CDN | `*.greenhouse.io` | `cdn.ashbyprd.com` |
| Rendering | SSR + React hydration | pure SPA shell |
| Bootstrap global | (none — uses `<main>` SSR) | `window.__appData` |
| Theme color | Anthropic peach `#D97757` | Ashby purple `#483fad` |
| Footer | `Powered by Greenhouse` (in real listings) | `Powered by Ashby` |

## Confidence

- Snapshot 1 is Greenhouse: **certain** — `og:url`, CDN, theming vars, SSR layout, and URL
  shape all agree.
- Snapshot 2 is Ashby: **certain** — `cdn.ashbyprd.com`, `window.__appData`, footer
  links, theme color, and URL shape all agree.

No re-fetch was performed for this stage — all evidence was already captured in S1
(`_gh_snapshot.txt`, `stage_s1.yml`) and S2 (`_ashby_snapshot.txt`, `stage_s2.yml`).
