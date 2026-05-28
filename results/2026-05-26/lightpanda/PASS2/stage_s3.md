# S3 — Platform Detection

**MCP:** lightpanda
**Inputs:** S1 (Greenhouse snapshot) and S2 (Ashby snapshot diagnostic), no re-fetch.

## Verdict

| Snapshot | URL path | ATS |
|---|---|---|
| S1 | `/greenhouse_2026-05-22/anthropic/jobs/5023394008.html` | **Greenhouse** |
| S2 | `/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html` | **Ashby** |

## Distinguishing signals

### Greenhouse (S1)
- **URL pattern**: numeric job ID (`5023394008.html`) under `/<company>/jobs/`. Public Greenhouse boards live at `job-boards.greenhouse.io/<company>/jobs/<id>`.
- **Server-rendered**: full job body present in initial HTML — markdown extraction returns ~10 KB of structured content (title, locations, compensation, requirements, workstreams, apply form) on a JS-less browser. This is the canonical Greenhouse signature.
- **OpenGraph metadata**: `og:url` canonical is `https://job-boards.greenhouse.io/anthropic/jobs/5023394008` — explicit platform branding in the URL.
- **Apply form rendered inline**: the page itself contains First Name / Last Name / Email / Phone / Resume / "How did you hear about us?" fields under `## Apply for this job`. Greenhouse always inlines its form on the job page.
- **Footer**: literal "Powered by [Greenhouse](https://www.greenhouse.com)" branding visible in the rendered markdown.
- **Logo**: `s8-recruiting.cdn.greenhouse.io` CDN host on the company logo image.

### Ashby (S2)
- **URL pattern**: UUID job ID (`1e1a651f-693d-4f9d-bfd9-280a50d28d13.html`) under `/<company>/`. Public Ashby boards live at `jobs.ashbyhq.com/<company>/<uuid>`. UUID vs numeric is the cleanest tell.
- **Client-rendered SPA**: lightpanda gets `<title>Jobs</title>` and a 4.5 KB static React shell — `<div id="root">` with 2 placeholder children, 2 `<script>` tags, 55 bytes of body text. No job content extractable without a JS runtime.
- **Asset CDN**: favicon served from `cdn.ashbyprd.com` (Ashby's production CDN). The `prd` subdomain is an Ashby fingerprint.
- **Theme color**: `#483fad` (Ashby's brand purple) in the `<meta name="theme-color">` of the shell.
- **Generic title**: `<title>Jobs</title>` — Ashby's SPA defers per-job titles to client-side `document.title` mutation. Server-rendered ATSs (Greenhouse, Lever) put the job title in the static `<title>` tag.

## Reasoning summary

Even without seeing the rendered Ashby content, the **failure shape itself** is diagnostic. Lightpanda has no JS engine, so any ATS that pre-renders its job description on the server (Greenhouse, Lever, Workable) returns rich content; any ATS that hydrates client-side (Ashby, modern Workday) returns the bare shell. Crossing that signal with URL shape (numeric vs UUID) and CDN host (`*.greenhouse.io` vs `*.ashbyprd.com`) gives high confidence without re-fetching either page.
