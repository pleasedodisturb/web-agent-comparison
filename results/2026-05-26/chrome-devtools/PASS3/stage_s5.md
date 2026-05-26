# S5 — Fill application form

## Tool used

`mcp__chrome-devtools__fill_form` — the batch-friendly tool. Filled 4 fields in **one
call** (chrome-devtools' equivalent of Playwright's `browser_fill_form`).

## Values filled (from `fixtures/mock_data.json`)

| Field id | uid | Value | Verified post-fill |
|---|---|---|---|
| `first_name` | `5_284` | `Jane` | ✓ |
| `last_name` | `5_286` | `Testworth` | ✓ |
| `email` | `5_288` | `jane.testworth@example.com` | ✓ |
| `phone` | `5_296` | `+1 555 867 5309` | ✓ |

Verification was done by `evaluate_script` reading `document.getElementById(...).value`
for each id — confirmed all four reflect the typed values.

## Fields NOT filled (and why)

| Harness-requested field | Reason skipped |
|---|---|
| `linkedin` | No linkedin field on the Anthropic Fellows fixture form (confirmed in S4). |
| `github` | No github field on the Anthropic Fellows fixture form (confirmed in S4). |

This is a fixture-specific finding (Anthropic's Fellows posting only collects
first/last/email/country/phone/resume + 1 custom question), not a chrome-devtools
limitation. The MCP would happily fill linkedin/github if they were in the DOM.

## MCP capability finding

- `fill_form` batched 4 inputs in a single MCP tool call — same ergonomics as the
  Playwright `browser_fill_form` primitive that the 2026-03 wave highlighted.
- Inputs were targeted by `uid` from the prior `take_snapshot`. The uids were stable
  across the fill, so no re-snapshot was required between steps.
- Total tool calls for the fill: 1 (fill_form) + 1 (evaluate_script verify) +
  1 (take_snapshot of filled state).

## Filled-form snapshot

Saved to `_s5_filled_snapshot.txt` (accessibility tree of the form after fills).

## Tools used

- `mcp__chrome-devtools__fill_form`
- `mcp__chrome-devtools__evaluate_script` (verification)
- `mcp__chrome-devtools__take_snapshot`
