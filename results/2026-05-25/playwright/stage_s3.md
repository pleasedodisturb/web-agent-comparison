# S3 — Platform Detection

**Task:** Without re-fetching, identify which of the two snapshots is Greenhouse and which is Ashby, using only the evidence captured in S1 and S2.

## Verdict

| Snapshot path | ATS platform | Confidence |
|---|---|---|
| `greenhouse_2026-05-22/anthropic/jobs/5023394008.html` | **Greenhouse** | 1.00 |
| `ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html` | **Ashby** | 1.00 |

Both detections are trivially correct from the path itself, but more importantly they are independently verifiable from the snapshot contents — which is the point of the exercise.

## Greenhouse markers (snapshot 1)

1. **`og:url`** is `https://job-boards.greenhouse.io/anthropic/jobs/5023394008` — the public Greenhouse job-board domain. Greenhouse renders postings at `job-boards.greenhouse.io/<org>/jobs/<numeric_id>`; the numeric job id pattern (10 digits) is a Greenhouse hallmark.
2. **`og:image`** points to `https://s8-recruiting.cdn.greenhouse.io/...` — Greenhouse's shard-numbered recruiting CDN.
3. **Font preload** comes from `s8-recruiting.cdn.greenhouse.io/job_board_renderer/custom_fonts/` — `job_board_renderer` is the literal Greenhouse service name for the new job board UI (the Next.js rewrite that replaced the legacy `boards.greenhouse.io`).
4. The static HTML contains the **full job text** server-side (84 KB, 22 H2 sections, body copy hydratable). Greenhouse SSRs the posting content even though the page is a Next.js app — useful as a benchmark feature, not a coincidence.
5. The standard `Apply for this job` and `Submit application` button labels are present — Greenhouse's stock form copy.

## Ashby markers (snapshot 2)

1. The inline `window.__appData = {...}` blob is **Ashby's exact bootstrap shape** — keys `ddRumApplicationId`, `recaptchaPublicSiteKey`, `routerPrefix`, `jobBoard`, `posting`, `organization`. No other ATS uses this combination.
2. The bundle manifest is loaded from **`cdn.ashbyprd.com/frontend_non_user/`** — Ashby's production CDN hostname (`ashbyprd` = Ashby + prd/production). `frontend_non_user` is Ashby's anonymous-job-board bundle namespace, distinct from `frontend_user` for authenticated recruiter pages.
3. Page title is the generic `"Jobs"` and body is the loading shell (`"You need to enable JavaScript to run this app."`) — Ashby is a hard SPA that does **not SSR** posting content. This itself is a behavioral fingerprint: a 6 KB HTML body where Greenhouse delivers 84 KB is diagnostic.
4. The posting URL slug is a **UUID v4** (`1e1a651f-693d-4f9d-bfd9-280a50d28d13`) rather than Greenhouse's numeric id — Ashby uses UUIDs for posting ids.
5. The `recaptchaPublicSiteKey` `6LeFb_YUAA...` is Ashby's shared reCAPTCHA v2 site key — same value across all Ashby boards (confirmable by checking any public Ashby posting).

## Why this matters for the benchmark

The two snapshots are diagnostically different even **before** trying to interact with them:
- Greenhouse: heavy SSR + light React hydration. A non-JS scraper (lightpanda, raw HTTP) can extract everything from the static HTML.
- Ashby: full SPA, content arrives via runtime API call to `cdn.ashbyprd.com`. Only a JS-rendering tool with live network access can extract anything; an offline snapshot is unrecoverable regardless of MCP capability.

For Playwright specifically, S1 succeeded (via `fetch` + `DOMParser`, sidestepping the broken hydration) and S2 returned an honest "rendered, empty" — both correct behaviors.
