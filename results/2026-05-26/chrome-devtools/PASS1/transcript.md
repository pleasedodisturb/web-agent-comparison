# chrome-devtools — Stage Walk Transcript

Run date: 2026-05-26
MCP: `chrome-devtools-mcp` (npm `chrome-devtools-mcp@1.0.1`, just-GA'd 2026-05-18)
Allowed tools used: `mcp__chrome-devtools__*`, `Read`, `Write`, `Bash`, `Grep`.

## Stage-by-stage summary

| Stage | Outcome | Artifact | Tools used |
|-------|---------|----------|------------|
| S1    | PASS    | `stage_s1.yml` | `new_page`, `navigate_page`, `evaluate_script` |
| S2    | PASS (empty)   | `stage_s2.yml` | `navigate_page`, `evaluate_script` |
| S3    | PASS    | `stage_s3.md` | (analysis only — no MCP calls) |
| S4    | FAILED  | `stage_s4.FAILED` | `take_snapshot` (confirmed no form) |
| S5    | FAILED  | `stage_s5.FAILED` | n/a — no form |
| S6    | FAILED  | `stage_s6.FAILED` | n/a — no file input |
| S7    | FAILED  | `stage_s7.FAILED` | n/a — no source dropdown |
| S8    | FAILED  | `stage_s8.FAILED` | n/a — nothing to screenshot |

## What worked

**S1 (Greenhouse extract).** chrome-devtools drove a real Chromium against
the snapshot. The visible DOM resolved to "Page not found" because
`job-boards.cdn.greenhouse.io` is unreachable from loopback, so the Remix
client bundles failed to load. But chrome-devtools' raw CDP access let me
pull `window.__remixContext` via `evaluate_script`, which contained the
full SSR loader payload: job title (scrubbed to "Jane Testworth Program"),
company (Anthropic), location, employment field, published_at, the
application form schema (`questions[]` with first_name / last_name /
email / phone / resume / acknowledgement-checkbox), and the
external-partner apply link (Constellation `bit.ly/afpsafety`). This is
the kind of finding that distinguishes a CDP-native MCP from a
markdown-extraction one — the structured SSR data is still recoverable
even when hydration fails.

**S2 (Ashby SPA).** Navigation succeeded, JS executed, React mounted. The
SPA rendered "Page not found" for the same fixture-rot reason. Unlike
Greenhouse, Ashby's `window.__appData.posting` was `null` in source — Ashby
fetches the posting via an authenticated GraphQL call AFTER hydration, and
the wget snapshot froze the page before that resolved. Result: extraction
returned only the company slug ("replit") inferable from the URL path. Not
a chrome-devtools failure — the data was never in the bytes.

**S3 (platform detection).** Distinguishing globals are unmistakable:
`window.__remixContext` for Greenhouse, `window.__appData` for Ashby.
Greenhouse uses numeric job IDs, Ashby uses UUIDv4. Greenhouse ships full
SSR; Ashby ships an empty shell. See `stage_s3.md` for the detection
matrix.

## What failed and why

**S4-S8 all failed for the same structural reason:** neither fixture
contains an application form in the rendered DOM. The Greenhouse snapshot
is a JS-driven Remix app that needs CDN-hosted bundles to materialize the
form; the snapshot server can't host those bundles. The Ashby snapshot has
no form even in source HTML because Ashby renders forms client-side after
GraphQL resolution.

**This is fixture-shaped, not MCP-shaped.** chrome-devtools v1.0.1 ships
`click`, `fill`, `fill_form`, `upload_file`, `evaluate_script`,
`take_snapshot`, `take_screenshot`, `press_key`, `select_page`, and a
React-Select-compatible `type_text + press_key` fallback — all the
primitives needed for S5-S8 are present. The form was simply absent from
the target. The same failure would propagate to every other MCP
(playwright, browser-use, cloakbrowser, obscura) — none can fill a form
that doesn't exist in the DOM. firecrawl, lightpanda, and read-only MCPs
would degrade further: they'd not even reach the "form is missing"
diagnosis since they can't run client-side JS or inspect Remix context.

## Caveats and notes

- The Greenhouse snapshot's `PROVENANCE.md` flags this exact scenario
  under "Pitfall 8 (public-fixture rot) — live URLs 404 within 6 months."
  The capture date (2026-05-22) was apparently already on the wrong side
  of Greenhouse's post-expiry behavior, where the live page returns a
  200 with an empty Remix bundle that renders "Page not found." A
  re-capture against a known-active job posting would let S4-S8 actually
  exercise the form-driving primitives.
- The Remix-context extraction technique in S1 is platform-agnostic for
  any Greenhouse-hosted board — `window.__remixContext.state.loaderData`
  follows a fixed Remix route-id schema (`routes/$url_token_.jobs_.$job_post_id`).
  Worth bookmarking for the production toolkit.
- I never wrote a "filled form" screenshot for S8. The honest signal is
  `stage_s8.FAILED`; a screenshot of the "Page not found" page would
  mislead the scorer about what was captured.
- No use of `WebFetch` or any non-chrome-devtools MCP. Fairness contract
  honored.

## Tool inventory observed

Verified working against this fixture in this run:
`new_page`, `navigate_page`, `evaluate_script`, `take_snapshot`,
`list_pages` (via test). Schemas confirmed loaded for `click`, `fill`,
`fill_form`, `upload_file`, `take_screenshot`, `wait_for`, `select_page`,
`press_key`, `type_text` but not exercised due to missing form.
