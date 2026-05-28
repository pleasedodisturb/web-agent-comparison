# Stage S3 — Platform detection

**MCP:** cloakbrowser
**Inputs:** the two static-HTML extractions captured in S1 and S2 (no re-fetches).

## Verdict

| Snapshot path | Platform |
|---|---|
| `/greenhouse_2026-05-22/anthropic/jobs/5023394008.html` | **Greenhouse** |
| `/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html` | **Ashby** |

## Reasoning

### URL-path markers
- `/anthropic/jobs/<numeric-id>.html` mirrors Greenhouse's public job-board URL shape `job-boards.greenhouse.io/<org>/jobs/<numeric-id>` (S1 also surfaced the canonical `https://job-boards.greenhouse.io/anthropic/jobs/5023394008`).
- `/replit/<uuid>.html` mirrors Ashby's `jobs.ashbyhq.com/<org>/<uuid>` shape — Ashby uses UUIDs for posting IDs, Greenhouse uses 10-digit numeric IDs.

### Static-HTML payload size
- Greenhouse snapshot: **84,577 bytes** — full server-rendered job content. Job title, location, salary, description, workstreams, and the apply button all live in the HTML body before any JS runs.
- Ashby snapshot: **6,294 bytes** — bootstrap shell only. The body contains a `<noscript>`-style fallback, an inline spinner CSS, and a `<script>` block that loads `https://cdn.ashbyprd.com/frontend_non_user/<sha>/<bundle>.js`. The job content does not exist in the HTML; it arrives via a runtime API call.

### DOM markers
- **Greenhouse:** the static HTML carries a fully populated `<h1>Jane Testworth Program</h1>` and the canonical `<button class="btn btn--rounded" aria-label="Apply">Apply</button>` paired with two `<a href="https://bit.ly/afpsafety">` anchors ("Apply using this link", "Apply here"). These are Greenhouse's standard job-board templates.
- **Ashby:** the static HTML has no `<h1>`, no `<meta name="description">`, no JSON-LD. Instead it carries a `window.__appData` object with telemetry keys `ddRumApplicationId` / `ddRumClientToken` (DataDog RUM identifiers Ashby ships in its bootstrap), a `recaptchaPublicSiteKey` (Ashby's anti-bot layer on apply forms), and `posting: null` / `jobBoard: null` placeholders that the bundle later fills.

### Form / interaction cues
- Greenhouse posts use a JS-rendered apply modal but expose a stable `aria-label="Apply"` `<button>` and bit.ly redirect anchors at the static level. The actual apply form lives at a separate URL (the `bit.ly/afpsafety` redirect or an embedded iframe) and uses React Select for "How did you hear about us?" dropdowns — a well-documented Greenhouse quirk relevant to S7.
- Ashby posts mount a single React tree under `#root` whose application form is part of the same SPA. The bundle source path (`cdn.ashbyprd.com/frontend_non_user/...`) is a textbook Ashby tell.

### Telemetry / branding
- Ashby's bundle ships DataDog RUM client tokens inline (`ddRumApplicationId`, `ddRumClientToken`) and the rendered footer in S2 reads "Powered by [Ashby]" — that line came from the post-hydration body even though the posting itself 404'd.
- Greenhouse uses Segment / Datadog server-side and does not leak RUM keys into the static HTML.

## Confidence

High. Both snapshots match canonical templates for their respective ATSs across at least four independent signals (URL path, payload size, DOM scaffolding, bootstrap-script origin). No re-fetch was needed — S1's extracted body and S2's `window.__appData` object are sufficient.
