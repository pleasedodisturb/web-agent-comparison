# S4 — Navigate to apply form

**Fixture:** `http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html` — the Greenhouse snapshot embeds the apply form *inline* in the same page as the job description (Greenhouse SSRs the form below the role copy). There is no separate apply URL in this fixture.

## React-hydration workaround

`cloak_navigate` triggers a React bundle that overwrites the entire `<body>` with a "Page not found" stub. The form exists in the *served HTML* but vanishes the moment the bundle runs.

Workaround (all via the cloakbrowser MCP, no external tool):

1. `cloak_navigate` to the posting URL (loads the page; React clobbers the form).
2. `cloak_evaluate`:
   - `fetch(url)` from page context → static HTML (84,577 bytes).
   - `DOMParser` → extract the `<form>` element.
   - Replace `document.body.innerHTML` with the form's `outerHTML`.
   - Remove every remaining `<script>` so React cannot re-mount and re-clobber.
3. `cloak_snapshot` produces 15 `[@eN]` refs — every downstream stage (S5, S6, S7, S8) works through these refs without CSS-selector hacks.

## Live snapshot after workaround (15 interactive refs)

| ref  | element          | id / aria-label / text                                         | notes |
|------|------------------|----------------------------------------------------------------|-------|
| @e1  | input[text]      | id=`first_name`, aria-label "Jane Testworth"                  | label rewritten in fixture; id is canonical |
| @e2  | input[text]      | id=`last_name`, aria-label "Jane Testworth"                   | |
| @e3  | input[text]      | id=`email`, aria-label "Email"                                | |
| @e4  | input[text]      | id=`country` (combobox, collapsed)                            | React Select |
| @e5  | button           | aria-label "Toggle flyout"                                    | opens country combobox |
| @e6  | input[tel]       | id=`phone`, aria-label "Phone"                                | |
| @e7  | button           | text "Attach"                                                 | resume upload affordance |
| @e8  | input[file]      | id=`resume`, accept=".pdf,.doc,.docx,.txt,.rtf"               | actual file input |
| @e9  | button           | text "Dropbox"                                                | alternate upload source |
| @e10 | button           | text "Jane Testworth"                                         | (Google Drive — anonymized) |
| @e11 | button           | text "Enter manually"                                         | paste-resume affordance |
| @e12 | input[text]      | id=`question_14364081008` (combobox, collapsed)               | custom required question |
| @e13 | button           | aria-label "Toggle flyout"                                    | opens custom-question combobox |
| @e14 | link             | "application form" → https://bit.ly/afpsafety                 | external apply link |
| @e15 | button[submit]   | text "Submit application"                                     | |

Form action: `http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html`
Form method: `GET` (fixture-rewritten; the real Greenhouse form posts to their API).

## Caveats for downstream stages

- **No `linkedin` field, no `github` field** in this Greenhouse fixture. S5 will document the missing fields rather than fabricate refs.
- **No `source` / "How did you hear about us?" dropdown** in this fixture. The custom-question combobox at @e12 is the closest analogue (a React Select), so S7 uses it to demonstrate the React-Select fill technique.
- **Labels are anonymized to "Jane Testworth"**; field selection uses the id-stable refs from the snapshot, not the visible label text.
- The form does not actually POST anywhere meaningful — the success criterion for S5–S7 is "values present in DOM after fill," not "form submitted."
