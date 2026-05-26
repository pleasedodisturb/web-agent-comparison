# S5 — Fill application form

**MCP:** cloakbrowser
**Form state:** post-S4 (form re-injected via `cloak_evaluate`, React scripts stripped, 15 refs live)

## Fields filled via `cloak_type` (4 of 6)

| field         | mock_data.json value         | ref  | result                                |
|---------------|------------------------------|------|----------------------------------------|
| first_name    | Jane                         | @e1  | filled (`#first_name` value = "Jane") |
| last_name     | Testworth                    | @e2  | filled (`#last_name` value = "Testworth") |
| email         | jane.testworth@example.com   | @e3  | filled (`#email` value = "jane.testworth@example.com") |
| phone         | +1 555 867 5309              | @e6  | filled (`#phone` value = "+1 555 867 5309") |

DOM verification (`cloak_evaluate` → `document.getElementById(id).value`):

```json
{
  "first_name": "Jane",
  "last_name": "Testworth",
  "email": "jane.testworth@example.com",
  "phone": "+1 555 867 5309"
}
```

## Fields NOT filled (2 of 6) — absent in fixture

| field    | reason                                                                                          |
|----------|-------------------------------------------------------------------------------------------------|
| linkedin | No input or label matching `linkedin` in this Greenhouse fixture. Verified by selector probe in `cloak_evaluate`. |
| github   | No input or label matching `github` in this Greenhouse fixture. Verified by selector probe.    |

These omissions are honest — the Greenhouse Anthropic-Fellows posting only collects first_name, last_name, email, phone, country (combobox), resume (file), and one custom free-text combobox question. LinkedIn and GitHub are not part of this form schema.

## Tool primitive notes

- CloakBrowser does not currently expose a `browser_fill_form` batch primitive (cf. Playwright). Each field is one `cloak_type` call.
- `cloak_type` defaults to `clear=True` so refilling a field is safe without an explicit clear step.
- The auto-returned snapshot after each `cloak_type` shows the entered text inline (e.g. `[@e3] input[text] "Email": jane.testworth@example.com`), which means snapshot diffs are usable for assertion in CI.
- Total tool calls for S5: 4 × `cloak_type` + 1 × `cloak_evaluate` (DOM verification). No retries, no failed actions.

## Trade-off observed

Per-field typing means 4 tool round-trips vs. Playwright's 1-call `browser_fill_form`. For a 6-field form, this is +5 round-trips of latency. For CloakBrowser the trade-off is intentional: each `cloak_type` runs through the humanizer (key-by-key cadence) which is the entire reason CloakBrowser exists. Batching would defeat its stealth design.
