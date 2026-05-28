# S4 — Navigate to apply form

**Fixture:** `http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html` — the Greenhouse snapshot's apply form is embedded *inline* in the same page as the job description (Greenhouse SSRs the form below the role copy). There is no separate apply URL.

## Workaround for React hydration

`cloak_navigate` triggers React hydration that replaces the entire `<body>` with a "Page not found" stub, destroying the form before any ref can be assigned. PASS1 documented the same behavior.

Fix (legitimate use of `cloak_evaluate`):
1. `fetch('/greenhouse_2026-05-22/anthropic/jobs/5023394008.html')` from the same origin.
2. Parse the response via `DOMParser`.
3. Extract the `<form>` element's `outerHTML`.
4. Replace `document.body.innerHTML` with that form.
5. Remove every `<script>` in the document so React cannot re-mount and clobber.

The result is a live, interactive form that `cloak_snapshot` ref-tags normally. No CSS-selector hacks — every downstream stage works through `[@eN]` refs.

## Live snapshot after workaround (15 interactive refs)

| ref  | element            | id / aria-label / text                              | notes |
|------|--------------------|-----------------------------------------------------|-------|
| @e1  | input[text]        | id=`first_name`, aria-label "Jane Testworth"        | label rewritten to "Jane Testworth" in fixture |
| @e2  | input[text]        | id=`last_name`, aria-label "Jane Testworth"         | |
| @e3  | input[text]        | id=`email`, aria-label "Email"                      | |
| @e4  | input[text]        | id=`country` (combobox, collapsed)                  | React Select |
| @e5  | button             | aria-label "Toggle flyout"                          | opens country combobox |
| @e6  | input[tel]         | id=`phone`, aria-label "Phone"                      | |
| @e7  | button             | text "Attach"                                       | resume upload affordance |
| @e8  | input[file]        | id=`resume`, accept=".pdf,.doc,.docx,.txt,.rtf"     | actual file input |
| @e9  | button             | text "Dropbox"                                      | alternate upload source |
| @e10 | button             | text "Jane Testworth"                               | (Google Drive — anonymized) |
| @e11 | button             | text "Enter manually"                               | paste-resume affordance |
| @e12 | input[text]        | id=`question_14364081008` (combobox, collapsed)     | custom required question |
| @e13 | button             | aria-label "Toggle flyout"                          | opens custom-question combobox |
| @e14 | link               | "application form" → https://bit.ly/afpsafety      | external apply link |
| @e15 | button[submit]     | text "Submit application"                            | |

## Caveats for downstream stages

- **No `linkedin` field, no `github` field** in this Greenhouse fixture. `mock_data.json` includes both but the form only accepts first_name, last_name, email, phone, country, resume, and a custom free-text question. S5 will document the missing fields.
- **No `source` / "How did you hear about us?" dropdown** in this fixture. S7 will gracefully document the absence rather than fake a fill.
- **Labels are anonymized to "Jane Testworth"** for the first/last name fields. IDs remain semantic; field selection uses snapshot refs (not visible label text).
- **Form action** points to `5023394008.html` (the fixture rewrote it); the success criterion for S5–S7 is "field values present in DOM," not "form actually submits."
