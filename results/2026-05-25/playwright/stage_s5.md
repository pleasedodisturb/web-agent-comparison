# S5 — Fill application form

**Tool used:** `mcp__playwright__browser_fill_form` (single batched tool call, 4 fields)

## Mock data filled

| Field | Selector | Value |
|---|---|---|
| First name | `#first_name` | `Jane` |
| Last name | `#last_name` | `Testworth` |
| Email | `#email` | `jane.testworth@example.com` |
| Phone | `#phone` | `+1 555 867 5309` |

## Missing-from-fixture fields

The brief asked for 6 fields including LinkedIn and GitHub. **This Greenhouse
fixture's form does not contain LinkedIn or GitHub inputs** — the scrubbed
posting has only the four basic identity fields plus a Country combobox, a
Resume upload, and a single custom question ("Constellation application
form" source dropdown). I enumerated all form inputs in S4 to confirm there
were no hidden `linkedin_url` / `github_url` fields under different ids.

Greenhouse postings *can* have LinkedIn/GitHub fields as custom questions
configured per-job, but they are not part of the default schema and this
particular posting does not include them. Filling 4 of the 4 available
identity fields is the honest maximum.

## Verification

Post-fill, `document.getElementById(id).value` returns the entered string
for all four fields. The React form components accept the
`page.locator(...).fill()` writes that Playwright generates from
`browser_fill_form`.

## Tool surface notes

- `browser_fill_form` accepts a single array of `{ target, name, type, value }`
  and emits one `page.locator(...).fill()` per field — Playwright's
  efficient form-fill primitive. The MCP did NOT prompt for permission per
  field; all four went through in one round-trip.
- The form survived because earlier in S4 we replaced
  `document.documentElement.innerHTML` with the static SSR HTML (script
  tags inside innerHTML are inert per HTML5), preventing Greenhouse's
  Next.js bundle from re-running its offline-error redirect.
