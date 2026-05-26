# Stage S3 — Platform Detection

**MCP:** cloakbrowser
**Inputs:** the two static HTML payloads captured in S1 and S2 — re-read via the existing browser context (`cloak_evaluate(fetch + DOMParser)`), no re-navigation.

## Verdict

| Snapshot | ATS | Confidence |
|---|---|---|
| `http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html` | **Greenhouse** | High |
| `http://127.0.0.1:8765/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html` | **Ashby** | High |

## Distinguishing signals

### Greenhouse signals (S1 payload, 84.6 KB)
1. **URL path shape** — `/{tenant}/jobs/{numeric_id}.html` mirrors `job-boards.greenhouse.io/{tenant}/jobs/{id}`, and the canonical URL recovered from the static HTML (`https://job-boards.greenhouse.io/anthropic/jobs/5023394008`) is the smoking gun.
2. **Static body carries the full posting** — 84,577 bytes of rendered HTML before any JS runs. Greenhouse server-side renders the description, location, salary band, workstreams list, and apply CTA. Classic SSR + hydration model.
3. **Apply primitive** — a literal `<button type="button" class="btn btn--rounded" aria-label="Apply">Apply</button>` with no `href`. Greenhouse opens the apply modal/form via in-page React rather than an anchor. The "real" apply URL appears as an in-body anchor (`https://bit.ly/afpsafety`), separate from the button.
4. **Numeric job ID** (`5023394008`) — Greenhouse uses 10-digit numeric job IDs as the canonical key; Ashby uses UUIDs.
5. **Tenant directory layout** — `/greenhouse_2026-05-22/anthropic/jobs/` mirrors Greenhouse's company-scoped board URLs.
6. **DOM markers** — `.app-title`, `.location` block, and the `Back to jobs` lead are classic Greenhouse-board class names.

### Ashby signals (S2 payload, 6.3 KB)
1. **URL path shape** — `/{tenant}/{uuid}.html` mirrors `jobs.ashbyhq.com/{tenant}/{uuid}`. The UUID `1e1a651f-693d-4f9d-bfd9-280a50d28d13` is RFC 4122 v4-shaped — Ashby's canonical posting identifier.
2. **Static body is a 6.3 KB bootstrap shell** — there is no job content in the served HTML. The page renders entirely client-side.
3. **`window.__appData`** — the bootstrap script defines a global with Datadog RUM IDs (`ddRumApplicationId`, `ddRumClientToken`), a `recaptchaPublicSiteKey` (`6LeFb_YUAAAAALUD5h-BiQEp8JaFChe0e0A6r49Y`), `organization: null`, `posting: null`, `jobBoard: null`, and `routerPrefix: "/"`. This shape is Ashby-specific — Datadog RUM + the `__appData` envelope is their fingerprint.
4. **Bundle origin** — the shell requests its JS from `cdn.ashbyprd.com` (visible during hydration).
5. **API contract** — the bundle calls `api.ashbyhq.com` with the URL-path UUID to fetch the posting JSON; absence of that API in the fixture explains the "Page not found" render.

## How CloakBrowser confirmed this without re-navigating

Both static HTMLs were already fetched in S1 and S2 via `cloak_evaluate(fetch + DOMParser)`. Detection is a function of the bytes alone:

- Greenhouse: presence of an `<h1>` job title, `.location` block, and the canonical anchor pattern `job-boards.greenhouse.io`.
- Ashby: absence of body content, presence of `window.__appData = {…ddRum…}`, presence of a `cdn.ashbyprd.com` script tag.

Either signal set alone is enough; together the classification is unambiguous.

## Why this matters for MCP capability scoring

The same MCP — CloakBrowser — handled both ATSs without configuration. The differentiator across MCPs in S2 is whether the JS bundle can run at all. CloakBrowser ran it (it is real Chromium), got an authoritative 404 from the live Ashby API path, and surfaced an `__appData` payload that is itself ATS-fingerprinting evidence. A non-JS MCP (e.g. lightpanda) would surface only the 6 KB shell and the same `__appData` JSON — which is still enough to classify Ashby, but not to extract a posting.
