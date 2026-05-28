## S3 — Platform Detection

Comparing the two snapshots extracted in S1 and S2 without re-fetching.

### Snapshot A → Greenhouse

URL pattern: `job-boards.greenhouse.io/<company>/jobs/<numeric_id>` — the
canonical post-2024 Greenhouse-hosted board layout. Snapshot fixture path
preserved this: `greenhouse_2026-05-22/anthropic/jobs/5023394008.html`.

DOM markers (from S1):

- `<script>window.__remixContext = { … }</script>` — Greenhouse migrated
  their job-board renderer to Remix in 2024-2025. The `loaderData` shape
  with `routes/$url_token_.jobs_.$job_post_id` is a Remix route-id naming
  convention.
- `window.ENV` block lists Greenhouse-specific service hosts:
  `email-address-validator.us.greenhouse.io`, `boards.greenhouse.io`,
  `api-geocode-earth-proxy.greenhouse.io`, `c.spl.greenhouse.io`
  (Snowplow), and a Rollbar `job-board-renderer` token.
- Assets load from `job-boards.cdn.greenhouse.io/assets/*` with
  Vite-style fingerprinted filenames (`manifest-3629d205.js`).
- Loader payload includes `boardConfiguration.job_board_id`, `urlToken`,
  `quickApply.url = "https://my.greenhouse.io"` — `my.greenhouse.io` is
  Greenhouse's candidate portal.
- Application schema is rendered server-side as `questions[]` with field
  objects (`{ name: "first_name", type: "input_text" }`) — the canonical
  Greenhouse application-form schema.

### Snapshot B → Ashby

URL pattern: `jobs.ashbyhq.com/<company>/<UUID-v4>`. Fixture path:
`ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html`. The
job-id-as-UUID is an Ashby tell — Greenhouse uses numeric ids,
Workday uses opaque slugs, Lever uses base32 UUIDs.

DOM markers (from S2):

- `<script>window.__appData = { … }</script>` is Ashby's app-bootstrap
  global. Specifically the `ddRumApplicationId` / `ddRumClientToken`
  pair (DataDog RUM) and `recaptchaPublicSiteKey` are bundled here in a
  fixed schema — Ashby's app-init contract.
- Empty SSR — `posting: null`, `organization: null`, `jobBoard: null`,
  `customDomainData: null`. Ashby fetches posting data via an
  authenticated GraphQL call AFTER hydration. Greenhouse, by contrast,
  ships the post inline in `__remixContext`.
- Title tag is the generic literal `"Jobs"` — Ashby uses a single
  `document.title` for the whole SPA and updates it client-side after
  fetch resolves.
- No form element in the static HTML (`document.forms.length === 0`) —
  again, Ashby renders the application form client-side; Greenhouse's
  Remix loader had a structured `questions[]` block.

### Distinguishing features

| Signal                          | Greenhouse                        | Ashby                                   |
| ------------------------------- | --------------------------------- | --------------------------------------- |
| Job-id format                   | numeric (`5023394008`)            | UUID v4 (`1e1a651f-…`)                  |
| SSR data global                 | `window.__remixContext`           | `window.__appData`                      |
| SSR completeness                | full post inline                  | empty shell — post arrives via GraphQL  |
| CDN host                        | `job-boards.cdn.greenhouse.io`    | inline assets / Ashby CDN               |
| Telemetry vendor                | Snowplow + Rollbar                | DataDog RUM                             |
| Form schema in HTML             | `questions[]` array               | absent (rendered post-hydration)        |
| Apply-action surface            | `submitPath` URL + `quickApply`   | typically a single `<button>` SPA route |
| Confirmation message location   | `confirmation_message` field      | client-side toast after POST            |

### Conclusion

Snapshot A is Greenhouse, Snapshot B is Ashby. The cleanest single
signal: presence of `window.__remixContext` vs. `window.__appData`. Even
if the page rendered identically (both happen to show "Page not found"
in these snapshots because of CDN/GraphQL unreachability), the
bootstrapping globals make the platform unambiguous.

Tools used: only the S1 + S2 extracts written to disk. No additional
chrome-devtools calls were issued for this stage.
