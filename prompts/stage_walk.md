<!--
stage_walk.md — locked S1-S8 task script that drives every candidate MCP.

This prompt is appended via `claude --append-system-prompt` by
`scripts/run_mcp_session.sh`. The wrapper expands the three placeholders
before invoking Claude Code:

  - ${MCP}                 The MCP under test (one of the keys in .mcp.json),
                           e.g. "playwright", "firecrawl", "cloakbrowser".
  - ${SNAPSHOT_BASE_URL}   Loopback URL of the snapshot server, e.g.
                           "http://127.0.0.1:8765" (boots via
                           scripts/serve_fixtures.sh).
  - ${OUT_DIR}             Evidence directory for this run, e.g.
                           "results/2026-05-22/playwright".

The harness restricts the allow-list to `mcp__${MCP}__*,Read,Write,Bash` via
`--allowedTools`. Reaching for any other tool (WebFetch, a different MCP,
etc.) violates the fairness contract — the harness will record `tool-bug` or
`env-mismatch` and the run is invalid. There is NO WebFetch fallback.

The stages mirror results/2026-03-31_run.md and scoring/rubric.md (the
locked 8-dim scoring matrix). Do them in order; each writes a single file to
${OUT_DIR}.
-->

# Web-Agent MCP Stage Walk — `${MCP}`

You are driving the **${MCP}** MCP against snapshot fixtures of Greenhouse +
Ashby job postings. Your job is to execute stages S1 through S26 using ONLY
the tools `mcp__${MCP}__*`, `Read`, `Write`, and `Bash`. Save evidence to
`${OUT_DIR}/`.

**Snapshot server (loopback only):** `${SNAPSHOT_BASE_URL}`
**Output directory:** `${OUT_DIR}`
**Mock identity:** read `fixtures/mock_data.json` (Jane Testworth).
**Mock resume:** `fixtures/mock_resume.pdf`.

**Hard rules:**

- Use ONLY `mcp__${MCP}__*`, `Read`, `Write`, `Bash`. Never reach for
  `WebFetch` or a different MCP — the harness allow-list will refuse, and
  the run will be scored `tool-bug`.
- One artifact per stage, written to `${OUT_DIR}/stage_sN.<ext>` where
  `<ext>` is whatever the MCP natively produces (`.yml`, `.md`, `.txt`,
  `.json`, or `.png` for screenshots). The harness accepts any of those.
- If a stage CANNOT be completed with this MCP's surface (e.g. a read-only
  MCP cannot fill a form), write `${OUT_DIR}/stage_sN.NA` (one line stating
  why) and CONTINUE to the next applicable stage.
- If a stage was attempted and failed (crashed, timed out, returned 0
  bytes), write `${OUT_DIR}/stage_sN.FAILED` (one line stating the failure
  mode) and CONTINUE.
- At the end, write `${OUT_DIR}/transcript.md` summarising the tools you
  used per stage and any failure modes you hit. The harness will also
  derive a transcript from the stream-json; yours is the human view.

---

## S1 — Extract job data (Greenhouse)

**Target:** `${SNAPSHOT_BASE_URL}/greenhouse_2026-05-22/`

Navigate to the Greenhouse snapshot and extract the job posting data:
title, company, location, employment type, requirements summary, salary
band if present, and the apply-button URL.

Write the extracted structured data to `${OUT_DIR}/stage_s1.yml` (or `.md`
/ `.txt` / `.json` — pick the format the MCP natively returns).

## S2 — Extract job data (Ashby SPA)

**Target:** `${SNAPSHOT_BASE_URL}/ashby_2026-05-22/`

Ashby is a React SPA whose body renders client-side; this is the SPA
rendering test. Extract the job data (title, company, location, role
summary). Write to `${OUT_DIR}/stage_s2.yml` / `.md` / `.txt` / `.json`.

If the MCP cannot render JavaScript (lightpanda is the expected failure
here), expect a 0-byte / empty-shell extraction. Document that in the
output rather than masking it.

## S3 — Platform detection

Compare the two snapshots from S1 and S2. Without re-fetching, identify
which is Greenhouse and which is Ashby. Write a short reasoning paragraph
(URL pattern, DOM markers, form structure cues, anything that
distinguishes the two ATSs) to `${OUT_DIR}/stage_s3.md`.

## S4 — Navigate to apply form

**Target:** Greenhouse snapshot apply form (from the apply button or
direct URL — work it out from S1's extraction).

Navigate to the apply form. Capture the resulting page (DOM snapshot,
accessibility tree, markdown — whatever the MCP produces) to
`${OUT_DIR}/stage_s4.yml` / `.md`.

**Read-only MCPs (lightpanda, firecrawl):** write
`${OUT_DIR}/stage_s4.NA` with reason "MCP is read-only, no interaction
surface" and skip S5-S8 (write `.NA` for each).

## S5 — Fill application form

Read `fixtures/mock_data.json` into memory. Fill the apply form with:

- `first_name`
- `last_name`
- `email`
- `phone`
- `linkedin`
- `github`

Use the most batch-friendly tool the MCP exposes (e.g. Playwright's
`browser_fill_form`, which the 2026-03 wave demonstrated handles 6 fields
in one tool call). Save the filled-form state (DOM snapshot or descriptive
markdown) to `${OUT_DIR}/stage_s5.yml` / `.md`.

## S6 — Upload resume

Upload `fixtures/mock_resume.pdf` to the apply form's resume file input.
Use whatever upload primitive the MCP exposes (Playwright `browser_file_upload`,
the MCP's snapshot-driven click-the-file-input pattern, etc.).

Save a confirmation to `${OUT_DIR}/stage_s6.md` documenting:
- which tool you used,
- the resulting filename / size readout shown by the page (if any),
- any errors.

## S7 — Handle source dropdown

The Greenhouse form has a `source` / "How did you hear about us?"
dropdown. Set it to the `source` value from `fixtures/mock_data.json`
("Job board").

Greenhouse uses React Select comboboxes, NOT native `<select>` elements,
so `browser_select_option` typically fails. Use your judgment: either fall
back to typing the value and pressing Enter, or use the MCP's
`run_code`/`evaluate` to drive the React state directly.

Save a description of what worked to `${OUT_DIR}/stage_s7.md`, including
which technique succeeded and why.

## S8 — Screenshot of filled form

Capture a screenshot of the filled form to `${OUT_DIR}/stage_s8.png`. Full
page if the MCP supports it; viewport otherwise. Document any constraint
in the transcript.

---

**STOP.** Write `${OUT_DIR}/transcript.md` summarising which tools you
used per stage, what worked, what failed, and any caveats. Do NOT call any
non-`mcp__${MCP}__` tools except `Read`, `Write`, `Bash`. Do NOT reach for
`WebFetch`. If a stage cannot be completed with the MCP under test, write
`${OUT_DIR}/stage_sN.FAILED` with a one-line reason and move on.
