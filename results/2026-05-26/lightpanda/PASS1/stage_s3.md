# S3 — Platform Detection (Lightpanda)

## Verdict

- **Greenhouse:** `greenhouse_2026-05-22/anthropic/jobs/5023394008.html`
- **Ashby:**     `ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html`

Reached without re-fetching, purely by comparing the S1 and S2 extractions.

## Reasoning

### URL pattern

- `…/greenhouse_2026-05-22/anthropic/jobs/<numeric-id>.html` — numeric job IDs
  (5023394008) are the long-standing Greenhouse `gh_jid` convention. Path
  fragment `/anthropic/jobs/` mirrors `job-boards.greenhouse.io/anthropic/jobs/…`
  that S1 also captured in the OpenGraph `url` field
  (`https://job-boards.greenhouse.io/anthropic/jobs/5023394008`).
- `…/ashby_2026-05-22/replit/<uuid>.html` — UUID job IDs
  (`1e1a651f-693d-4f9d-bfd9-280a50d28d13`) are Ashby's standard public-board
  identifier; their hosted boards live at `jobs.ashbyhq.com/<company>/<uuid>`.
  Path fragment `/replit/` reflects the upstream `jobs.ashbyhq.com/replit/...` host.

### DOM markers

- Greenhouse markdown ends with `Powered by [](https://www.greenhouse.com)` —
  the canonical Greenhouse footer attribution.
- Ashby snapshot's `<head>` declares `theme-color="#483fad"` (Ashby's brand
  purple) and pulls its favicon from `cdn.ashbyprd.com` — both Ashby
  fingerprints in the SSR shell that Lightpanda CAN see even when the body
  never hydrates.
- Greenhouse OG metadata is fully populated (title, description, image, url).
  Ashby OG metadata is empty — SPAs that defer head population to the JS
  bundle commonly leak this way.

### Form structure cues

- Greenhouse renders a server-side form on the same page: explicit
  `first_name`, `last_name`, `email`, `phone`, `Resume/CV (Attach / Dropbox /
  Enter manually)`, plus a Greenhouse-typical `Select... required` "source"
  combobox. Footer is plain "Submit application". This matches the classic
  Greenhouse job-boards apply pattern.
- Ashby body never renders in Lightpanda. We can't compare form structure
  directly, but the absence of any body content combined with a 2-child
  `#root` div, two `<script>` tags, and SSR shell sized at 6,805 bytes is the
  classic signature of an Ashby React-rendered apply flow that hydrates
  client-side.

### Hydration / engine cue

- Greenhouse rendered fully under Lightpanda (`bodyTextLen` ≈ thousands of
  characters; the full job description came through).
- Ashby rendered as 55 chars of body text — exactly the "SSR shell only"
  signature. Whenever Lightpanda yields a vast head + tiny body + non-empty
  `#root` with no descendants the agent can read, the page is a SPA. Ashby
  is that.

## Confidence

High. URL pattern + footer + theme-color + form layout vs. shell are four
independent signals all pointing the same direction.
