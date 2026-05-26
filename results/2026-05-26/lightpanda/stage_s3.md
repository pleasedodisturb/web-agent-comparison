# S3 — Platform Detection (lightpanda)

## Verdict
- `http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html` → **Greenhouse**
- `http://127.0.0.1:8765/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html` → **Ashby**

## Distinguishing signals (collected without re-fetch, from S1/S2 evidence)

### URL pattern
- Greenhouse path tree: `/anthropic/jobs/{numeric_id}.html`. Job IDs are 10-digit decimal (`5023394008`). The "anthropic" segment is the company slug, which matches the canonical Greenhouse hosted URL shape `job-boards.greenhouse.io/{company}/jobs/{id}`.
- Ashby path tree: `/replit/{uuid_v4}.html`. ID is a UUID v4 (`1e1a651f-693d-4f9d-bfd9-280a50d28d13`), which matches Ashby's canonical `jobs.ashbyhq.com/{company}/{job_uuid}` shape.

### DOM / SSR markers
- Greenhouse: full server-rendered HTML — every heading, paragraph, mentor list, form schema, and meta tag is in the static document. OpenGraph populated (`og:title`, `og:description`, `og:url`, `og:image` pointing at `s8-recruiting.cdn.greenhouse.io`). Apply button visible in markdown. `[Powered by](https://www.greenhouse.com)` footer tag present.
- Ashby: SPA shell only. `<title>Jobs</title>` is the entire reachable content under lightpanda. Theme-color `#483fad` (Ashby's purple), favicons hosted on `cdn.ashbyprd.com`. No JSON-LD, no OpenGraph, no body text — content is injected by the React bundle that lightpanda's JS engine does not execute.

### Form schema cue
- Greenhouse exposes the apply form INLINE on the job page (same document, `<form>` rendered in SSR HTML). Fields surfaced through lightpanda's markdown extraction: First Name, Last Name, Email, Phone, Country, Resume/CV, plus a "Please note..." source-dropdown above the submit button. The "Powered by Greenhouse" footer is the canonical confirmation.
- Ashby renders no form into the SSR shell. The apply UI is mounted client-side under the same React app. Lightpanda sees nothing.

### ATS asset CDNs
- Greenhouse meta `og:image` → `s8-recruiting.cdn.greenhouse.io` (definitive Greenhouse fingerprint).
- Ashby favicon → `cdn.ashbyprd.com` (definitive Ashby fingerprint; "ashbyprd" = ashby production).

## Reasoning
Even with lightpanda's read-only surface and zero JS rendering on the Ashby side, identification is unambiguous: the URL path shape (numeric id vs. UUID), the asset-CDN domain in the SSR head (`*.greenhouse.io` vs. `cdn.ashbyprd.com`), and the SSR-vs-CSR rendering posture (full content vs. `<title>Jobs</title>` shell) each independently nail the platform. Three converging signals from a single navigation each.
