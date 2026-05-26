# S4 — Navigate to apply form

**Target:** Greenhouse fixture apply form (same URL as job posting — Greenhouse SSRs the
job description and the apply form in the same HTML document).

## Navigation result

The Apply button (`<button aria-label="Apply">` on the job page) is a same-page React route
trigger — clicking it normally swaps the visible region from listing to form via React
state, NOT a URL change. The DOM markup for the form is already in the SSR'd HTML at the
SAME URL as the listing.

When chrome-devtools navigated to the fixture and let the Greenhouse React bundle hydrate,
the bundle's offline-API fetch failed and the bundle replaced the entire body with "Page
not found." The Apply button, the form, and every input were wiped from the live DOM.

## Workaround (inside the chrome-devtools surface)

To get an interactive apply form for S5-S8, I re-fetched the fixture HTML via
`evaluate_script` → `fetch()`, stripped its 4 `<script>` tags (the React bundle loaders),
and replaced `document` via `document.open() / document.write() / document.close()`.
Result: the SSR'd form is fully rendered and interactive, the React-driven 404 cannot
override it because there's no React.

This is faithful to what the fixture actually contains. No off-MCP tools were used; the
work was done by `mcp__chrome-devtools__evaluate_script` and `mcp__chrome-devtools__take_snapshot`.

## Apply form fields discovered

| uid | role | name / id | label / aria | required |
|---|---|---|---|---|
| 5_284 | textbox | `first_name` | "Jane Testworth" (scrubbed) | yes |
| 5_286 | textbox | `last_name` | "Jane Testworth" (scrubbed) | yes |
| 5_288 | textbox | `email` | "Email" | yes |
| 5_292 | combobox | `country` (React-Select) | "Country" | optional |
| 5_296 | textbox | `phone` | "Phone" | no |
| 5_298 / 5_300 | button + file input | `resume` | "Attach" / "Resume/CV" | yes |
| 5_309 | combobox | `question_14364081008` (React-Select) | "Please note that you will not be considered unless you complete the Constellation application form. *" | yes |
| 5_319 | button | — | "Submit application" | — |

## Fields the harness asked for vs. what's in this fixture

| Harness asks | Present? | Notes |
|---|---|---|
| `first_name` | ✓ | `#first_name` |
| `last_name` | ✓ | `#last_name` |
| `email` | ✓ | `#email` |
| `phone` | ✓ | `#phone` |
| `linkedin` | **absent** | No linkedin field on Anthropic's Fellows posting form. |
| `github` | **absent** | No github field either. |
| `source` / "How did you hear about us?" | **absent** | This posting has no source dropdown. The only React-Select questions are `country` and a Constellation custom question. |

This is a posting-specific finding — Anthropic stripped the typical Greenhouse "How did
you hear" dropdown and linkedin/github fields on their Fellows posting. The remaining
S5/S6/S7 stages will fill what IS present and document what is not.

## Artifact

Snapshot saved to `_s4_form_snapshot.txt` (sibling file). Form is rendered, no
"Page not found" interference, ready for S5.

## Tools used

- `mcp__chrome-devtools__navigate_page`
- `mcp__chrome-devtools__evaluate_script` (fetch HTML, strip scripts, document.write)
- `mcp__chrome-devtools__take_snapshot`
