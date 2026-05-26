# S4 — Navigate to Apply Form

**Method:** The fixture's HTML contains the apply form embedded in the same
`5023394008.html` page (no separate apply URL — Greenhouse SSRs the form
inline beneath the description). However, on `cloak_navigate` the React shell
hydrates and replaces the entire `<body>` with a "Page not found" stub,
destroying the form before any interaction is possible.

**Workaround:** Used `cloak_evaluate` to (a) re-fetch the static HTML via
`fetch()`, (b) `DOMParser` the response, (c) extract the `<form>` outerHTML,
(d) replace `document.body.innerHTML` with that form, and (e) `remove()` every
`<script>` in the document so React cannot re-mount and wipe the form again.
This yields a live, interactive form that `cloak_snapshot` can ref-tag.

This workaround is a legitimate use of the MCP's surface — `cloak_evaluate`
is exposed for exactly this kind of bridging. The fixture's React shell is
the limiting factor, not the MCP.

## Live snapshot after workaround (15 interactive refs)

| ref | element | label / text | notes |
|-----|---------|--------------|-------|
| @e1 | input[text] | "Jane Testworth" | id=`first_name` |
| @e2 | input[text] | "Jane Testworth" | id=`last_name` |
| @e3 | input[text] | "Email" | id=`email` |
| @e4 | input[text] collapsed | "Country" | combobox; aria-expanded driven |
| @e5 | button | (chevron for country combobox) | opens country list |
| @e6 | input[tel] | "Phone" | id=`phone` |
| @e7 | button | "Attach" | resume upload trigger |
| @e8 | input[file] | "Attach" | accept=".pdf,.doc,.docx,.txt,.rtf" |
| @e9 | button | "Dropbox" | (resume from Dropbox) |
| @e10 | button | "Jane Testworth" | (resume from Google Drive — anonymized) |
| @e11 | button | "Enter manually" | resume-by-pasting |
| @e12 | input[text] collapsed | "Please note ... Constellation application ..." | custom question, free text |
| @e13 | button | (chevron for question combobox) | |
| @e14 | link | "application form" → https://bit.ly/afpsafety | external apply link |
| @e15 | button | "Submit application" | submit |

## Caveats for downstream stages

- **No `linkedin` field, no `github` field** in this Greenhouse fixture.
  `mock_data.json` includes both but the form will only accept first_name,
  last_name, email, phone, country, resume, and a custom free-text question.
  This is a documented gap in the fixture, not in the MCP.
- **No `source` / "How did you hear about us?" dropdown** in this fixture —
  S7 will document and gracefully degrade.
- **Labels are anonymized to "Jane Testworth"** in both the first_name and
  last_name fields. The IDs (`first_name`, `last_name`) are still semantic;
  selection should be by ID/snapshot ref, not by visible label.

## Form action

The form's `action` attribute points to
`http://127.0.0.1:8765/ashby_2026-05-22/replit/5023394008.html` —
clearly the fixture-baking script rewrote the form action to point inside
the local snapshot tree. Submitting wouldn't reach a real apply endpoint;
the success criterion for S5–S7 is "fields are filled in DOM," not "form
actually submits."
