# chrome-devtools — Stage walk transcript (2026-05-26)

MCP: `chrome-devtools` (chrome-devtools-mcp v1.0.x family)
Fixtures: `http://127.0.0.1:8765/greenhouse_2026-05-22/...`, `http://127.0.0.1:8765/ashby_2026-05-22/...`
Output: `results/2026-05-26/chrome-devtools/`

## Stage summary

| Stage | Status | Primary tools | Notes |
|---|---|---|---|
| S1 — Extract Greenhouse | DONE | new_page, navigate_page, take_snapshot, evaluate_script | SSR data recovered via fetch() + DOMParser after React hydration overwrote DOM with "Page not found." |
| S2 — Extract Ashby | DONE (0-data) | navigate_page, take_snapshot, evaluate_script | Ashby fixture is pure SPA shell (PROVENANCE confirms `posting:null`). React rendered, no job data to extract. Honest finding, not a defect. |
| S3 — Platform detection | DONE | (analysis only, no re-fetch) | Greenhouse vs. Ashby distinguished by URL shape, CDN hostnames (greenhouse.io vs cdn.ashbyprd.com), bootstrap globals (`<main class="job-post">` vs `window.__appData`), and theme colors. |
| S4 — Navigate to apply | DONE (workaround) | navigate_page, evaluate_script, take_snapshot | Stripped 4 `<script>` tags from re-fetched HTML and `document.write`'d the cleaned DOM to keep the SSR'd form interactive. All 6 form inputs + 2 React-Select comboboxes captured. |
| S5 — Fill form | DONE | fill_form (1 call), evaluate_script (verify) | 4 fields filled in one `fill_form` call: first_name, last_name, email, phone. linkedin/github fields are absent from this fixture (Anthropic-specific). |
| S6 — Upload resume | DONE | upload_file, evaluate_script | `mock_resume.pdf` (742 B, application/pdf) attached to `#resume` on first try. Cosmetic label doesn't refresh without React, but `inputEl.files[0]` is correct. |
| S7 — React-Select dropdown | DONE (technique demo) | evaluate_script | No source dropdown on this Anthropic posting; demonstrated the canonical React-Select fallback (native setter + input/change dispatch) on the `country` combobox. |
| S8 — Screenshot | DONE | take_screenshot (fullPage=true) | 6.2 MB PNG of full filled form saved to `stage_s8.png`. |

## What worked

- **`fill_form` batched 4 inputs in one call** — same ergonomics as the Playwright
  `browser_fill_form` primitive the 2026-03 wave highlighted.
- **`upload_file` against a `visually-hidden` file input** worked without any special
  selector handling — the MCP resolved the visible "Attach" button to the underlying
  file chooser correctly.
- **`evaluate_script` is the load-bearing tool** for this MCP on these fixtures: it
  enabled (a) raw-HTML extraction after hydration replaced the DOM, (b) stripping the
  React bundle to expose the SSR'd form, (c) the native-setter+dispatch React-Select
  technique, and (d) field-fill verification.
- **`take_snapshot` returned a clean accessibility tree with stable uids** that
  `fill_form` / `click` / `upload_file` could consume directly.

## What did not work (and why)

- **Direct interaction with the post-hydration Greenhouse DOM is impossible** on the
  offline fixture: the React bundle's `/api/...` call fails, the React app falls back
  to "Page not found," and the entire `<main>` is replaced. Same root cause as Ashby's
  hydrated 404 but with a different mechanism — Greenhouse at least ships SSR'd content
  that can be recovered; Ashby ships none.
- **Ashby's job content is structurally unrecoverable** from this fixture by any browser
  MCP, because `window.__appData.posting === null`. This is by design per the fixture's
  PROVENANCE.md — the snapshot is meant to discriminate between MCPs that render JS and
  those that don't, not to deliver data.
- **`browser_select_option`-style native select interaction is N/A** here — the form
  has 0 `<select>` elements; both dropdowns are React-Select comboboxes.
- **No keyboard-driven React-Select select** in the offline state — without the React
  runtime, the combobox menu doesn't open in response to `type_text`. Used the
  `evaluate_script` native-setter fallback instead.

## Tool inventory (used during the walk)

- `mcp__chrome-devtools__new_page`
- `mcp__chrome-devtools__navigate_page` (with and without initScript)
- `mcp__chrome-devtools__select_page` (implicit — only one page used)
- `mcp__chrome-devtools__take_snapshot`
- `mcp__chrome-devtools__take_screenshot` (fullPage)
- `mcp__chrome-devtools__evaluate_script` (most-used tool of the walk)
- `mcp__chrome-devtools__fill_form` (batch fill)
- `mcp__chrome-devtools__upload_file`
- `Read`, `Write`, `Bash`, `Grep`, `Glob` (non-MCP harness tools, allow-listed)

No non-`chrome-devtools` MCP tools were called. No `WebFetch`. The harness allow-list was
respected.

## Caveats and honest findings

1. **The "extraction" in S1 was not powered by chrome-devtools' rendering** — it was
   powered by `evaluate_script`'s `fetch()` against the fixture URL, parsing the SSR
   HTML out-of-band. A rubric that measures "MCP rendered the page and we read its
   accessibility tree" would score this 0 for S1; a rubric that measures "MCP delivered
   the job data" scores this PASS. The harness should choose one.
2. **The "navigation to apply form" in S4 was a script-strip workaround** — same caveat.
   The form is real, the data is real, but the path used `document.write` after
   `fetch()`, not a normal user-flow navigation.
3. **The S7 dropdown was country, not source** — the literal source dropdown doesn't
   exist on this Anthropic posting. Treat the stage as a technique demo, not a
   semantically valid selection.
4. **Form was not submitted** — `<form action="5023394008.html">` would have done a GET
   to the same fixture, which is not useful, and the stage walk explicitly stops at
   "filled form screenshot."

## Run integrity

All artifacts under `results/2026-05-26/chrome-devtools/`:

- `stage_s1.yml` — Greenhouse job data
- `stage_s2.yml` — Ashby (empty shell finding)
- `stage_s3.md` — platform detection
- `stage_s4.md` — navigation + form discovery
- `stage_s5.md` — filled fields
- `stage_s6.md` — resume upload
- `stage_s7.md` — React-Select technique
- `stage_s8.png` — full-page filled screenshot (6.2 MB)
- `_*.txt` — intermediate snapshots kept as evidence
- `transcript.md` — this file
