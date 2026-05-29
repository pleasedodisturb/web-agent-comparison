# S3 — Platform detection

Without re-fetching, comparing the snapshots captured in S1 and S2.

## Snapshot A — Greenhouse

- **URL pattern:** `/greenhouse_2026-05-22/anthropic/jobs/5023394008.html`
  — `/<board>/jobs/<numeric-id>.html`. Numeric IDs and a single
  flat `jobs/` directory under the board slug are Greenhouse's
  canonical URL shape (`job-boards.greenhouse.io/<board>/jobs/<id>`).
- **`og:url` meta in source HTML:**
  `https://job-boards.greenhouse.io/anthropic/jobs/5023394008` —
  explicit `greenhouse.io` host. Definitive.
- **`og:image`:** `s8-recruiting.cdn.greenhouse.io/.../greenhouse.png`
  — Greenhouse CDN.
- **DOM markers in the SSR shell:** custom CSS variables
  `--custom-link-color`, `--custom-active-field-color`, etc., plus a
  `<div id="react-portal-mount-point">` and CSS bundle paths under
  `job-boards.cdn.greenhouse.io/assets/entry-rL0h39AS.css` — all
  Greenhouse hallmarks.
- **Form structure cue (carried over from the locked-fixture context):**
  Greenhouse boards render a `source` / "How did you hear about us?"
  combobox via **React Select** (not a native `<select>`) — the canonical
  Greenhouse signal that breaks `browser_select_option`.

## Snapshot B — Ashby

- **URL pattern:** `/ashby_2026-05-22/replit/<uuid>.html` — `/<org>/<uuid>`.
  UUID slugs (no numeric IDs, no `/jobs/` segment) are Ashby's canonical
  shape (`jobs.ashbyhq.com/<org>/<uuid>`).
- **`PROVENANCE.md` source URL:**
  `https://jobs.ashbyhq.com/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13`
  — explicit `ashbyhq.com` host.
- **Footer DOM markers (captured by BrowserMCP):** `Powered by` "Ashby"
  branding, "Learn more about Ashby" link to `ashbyhq.com`, and the
  `Privacy Policy` / `Security` / `Vulnerability Disclosure` triad all
  pointing at `ashbyhq.com` paths. Definitive.
- **Rendering profile:** pure SPA shell, `<div id="root">` mount point,
  `<noscript>You need to enable JavaScript</noscript>` banner. No SSR
  job content. This is the *Ashby signature* — Greenhouse's boards
  always SSR enough HTML for the `<title>` and `<h1>` to be present;
  Ashby never does.

## Verdict

| Field            | A                                            | B                                  |
|------------------|----------------------------------------------|------------------------------------|
| ATS              | **Greenhouse**                               | **Ashby**                          |
| URL signature    | `greenhouse.io/<board>/jobs/<numeric-id>`    | `ashbyhq.com/<org>/<uuid>`         |
| SSR posture      | SSR shell with job data (overwritten by JS)  | SPA shell only, no SSR job data    |
| Form combobox    | React Select (custom)                        | Ashby React form (custom)          |
| `og:` host       | `job-boards.greenhouse.io`                   | n/a (footer + provenance instead)  |

## How a BrowserMCP-driven agent would have detected this live

Greenhouse and Ashby are *both* React apps with a `<div>` mount point, so
"does this page run JS" doesn't discriminate. The discriminators that
BrowserMCP sees through Chrome are:

1. The URL host / path shape (numeric vs UUID, presence of `/jobs/`).
2. The footer attribution block — Ashby always prints `Powered by Ashby`
   with links to `ashbyhq.com`; Greenhouse renders its own branding via
   `Apply` button styling and CSS variables.
3. The `og:` meta tags, when present in the SSR shell.

For an agent doing this live (not against snapshots), the URL host alone
is sufficient — `job-boards.greenhouse.io` vs `jobs.ashbyhq.com`.
