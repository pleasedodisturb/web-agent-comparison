# S3 — Platform detection (Greenhouse vs Ashby)

Without re-fetching the snapshots, the two pages from S1 and S2 are distinguishable by several signals — all of which survived even though both pages collapsed to in-app 404s under JS hydration.

## Greenhouse — `http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html`

- **URL path shape**: `/<company-slug>/jobs/<numeric-id>.html` — Greenhouse's canonical pattern is `job-boards.greenhouse.io/<slug>/jobs/<numeric_id>`. The numeric ID (`5023394008`) is the unmistakable Greenhouse job-ID format (10-digit).
- **`<title>` tag**: `Jane Testworth for Jane Testworth Program at Anthropic` — Greenhouse uses the verbose `<candidate name> for <role> at <company>` template.
- **Hydration fallback text**: `<h3 class="section-header font-primary">Page not found</h3>` inside `<div class="error-message font-secondary">` with `<div class="job-board-inactive"><p class="body">The job board you were viewing is no longer active.</p></div>` — Greenhouse-specific CSS class naming (`section-header`, `font-primary`, `job-board-inactive`).
- **Logo SVG**: 261×36 viewBox containing the recruiting-logo path data of Greenhouse's wordmark, with `fill="#15372c"` (Greenhouse dark green) and `#24a47f` (Greenhouse mid-green) — these colors are Greenhouse brand tokens.
- **CSS asset hosts**: `job-boards.cdn.greenhouse.io/assets/entry-rL0h39AS.css` and `vendor-da5IcPkB.css`.
- **Custom CSS vars**: `--custom-link-color`, `--custom-active-field-color`, `--custom-focus-color`, plus `StyreneALC-Medium`/`Lora` font-family hints — Greenhouse's customer-themed CSS-variable schema (Anthropic's brand palette is `#D97757` orange + `#FAF9F5` cream, set here).

## Ashby — `http://127.0.0.1:8765/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html`

- **URL path shape**: `/<company-slug>/<uuid>.html` — UUIDv4 in the path is Ashby's canonical job-posting ID (matches `[0-9a-f]{8}-[0-9a-f]{4}-...`).
- **Footer links** survive hydration and point to `ashbyhq.com/privacy`, `ashbyhq.com/security`, `ashbyhq.com/disclosure`, and `ashbyhq.com` ("Powered by"). Ashby brands its footer "Powered by Ashby" on every embed.
- **CSS class style**: `_title_ud4nd_34` — Ashby uses CSS Modules with hashed suffixes (`<readable-name>_<hash>_<line>`). This naming is distinctive: Greenhouse uses kebab-case BEM-ish (`section-header`, `font-primary`).
- **Company slug** `replit` is consistent with Ashby's customer roster (Replit publishes on Ashby).

## DOM markers summary

| Signal | Greenhouse | Ashby |
|---|---|---|
| URL job-ID format | 10-digit numeric | UUIDv4 |
| CSS class style | kebab-case BEM | CSS Modules `_name_hash_line` |
| 404 fallback text | "The job board you were viewing is no longer active" | bare `<h1>Page not found` |
| Footer attribution | none on this snapshot | `Powered by Ashby` + 3 ashbyhq.com policy links |
| Brand colors (logo SVG) | `#15372c`, `#24a47f` | n/a (logo not in hydrated DOM) |

Identification is robust even under the hydration-to-404 failure mode, because the surrounding chrome (header logo for Greenhouse, footer for Ashby) is part of the SPA shell itself and renders regardless of API availability.
