# S5 — Fill application form

**MCP surface used:** `cloak_type(ref, text)` — one call per field. CloakBrowser does not expose a `fill_form` batch primitive; the comparable Playwright `browser_fill_form` would land all six fields in one tool call. Treat that as a cost dimension when comparing.

## Mock identity (from fixtures/mock_data.json)

```json
{
  "first_name": "Jane",
  "last_name": "Testworth",
  "email": "jane.testworth@example.com",
  "phone": "+1 555 867 5309",
  "linkedin": "https://linkedin.com/in/janetestworth",
  "github": "https://github.com/janetestworth"
}
```

## Fields filled

| Field        | Ref  | Tool call                                    | Verified in DOM |
|--------------|------|----------------------------------------------|-----------------|
| first_name   | @e1  | `cloak_type(page, '@e1', 'Jane')`            | yes (`Jane`) |
| last_name    | @e2  | `cloak_type(page, '@e2', 'Testworth')`       | yes (`Testworth`) |
| email        | @e3  | `cloak_type(page, '@e3', 'jane.testworth@example.com')` | yes |
| phone        | @e6  | `cloak_type(page, '@e6', '+1 555 867 5309')` | yes |

## Fields requested but unavailable in this fixture

| Field    | Reason                                                                 |
|----------|------------------------------------------------------------------------|
| linkedin | No `#linkedin` input or labeled equivalent in the Greenhouse fixture's form. Greenhouse postings configure custom fields per role; this Anthropic Fellows role does not collect LinkedIn. |
| github   | Same — no `#github` input. |

All input IDs in the fixture form: `first_name`, `last_name`, `email`, `country`, `phone`, `resume`, `question_14364081008`. There is no LinkedIn or GitHub field to fill.

## Tool-call cost

- 4 `cloak_type` calls for 4 available fields.
- No batch primitive; each field is a separate round-trip with its own returned snapshot.
- Compare: Playwright MCP's `browser_fill_form` would fold these into a single call. CloakBrowser's design prioritizes humanized per-field typing (it's a stealth-first MCP) over batch efficiency.
