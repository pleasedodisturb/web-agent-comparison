# S7 — Handle source dropdown

## Fixture finding

The Greenhouse fixture `5023394008.html` (Anthropic Fellows posting) does **not** include a "How did you hear about us?" / `source` field. Verified via DOM inspection:

```
labels:    ["Jane Testworth*", "Jane Testworth*", "Email*", "Country",
            "Phone", "Attach", "Enter manually",
            "Please note that you will not be considered unless you complete
             the Constellation application form. *"]
input ids: ["first_name", "last_name", "email", "country", "phone",
            "resume", "question_14364081008"]
<select> count: 0
```

This is a real-world quirk of Greenhouse: the `source` dropdown is configured per-role at the recruiter level. Not every posting includes it. The Anthropic Fellows posting omits it.

`mock_data.json` ships `"source": "Job board"` for tests where the field exists. For this fixture, the correct behavior is to not invent a target field.

## Technique I would use against a real Greenhouse source field

Greenhouse renders source as a **React Select combobox**, not a native `<select>` — so `cloak_select` (which targets native `<select>` elements) does not work. Across the 2026-03-31 wave, the reliable pattern was:

1. `cloak_click(ref)` on the combobox input → opens the flyout.
2. `cloak_type(ref, 'Job board')` → filters the option list to "Job board".
3. `cloak_press_key(page, 'Enter')` → commits the selection.

If the React Select swallows arrow keys before Enter, fall back to clicking the visible option by its newly-allocated ref from the post-type snapshot.

If even that fails (some Greenhouse builds use Downshift instead of react-select and behave differently), the deterministic fallback is `cloak_evaluate` to set the underlying state directly — same pattern S4 used to bridge React hydration.

## Demonstration on the equivalent combobox

To show the technique runs, I exercised the only React-Select-style combobox in this fixture (`#country`, also a React Select in stock Greenhouse). With the React listeners stripped during the S4 workaround, the option-flyout state machine is gone, so I used the imperative fallback (`value = 'United States'` + dispatched `input`/`change`/`keydown[Enter]`). On a live Greenhouse form, the type+Enter sequence above is the production path.

```json
{ "country_value_after": "United States", "technique": "imperative + Enter event dispatch" }
```

## What worked / what would have worked

| Technique                                   | Verdict                                                                 |
|---------------------------------------------|-------------------------------------------------------------------------|
| `cloak_select` (native `<select>` API)      | N/A — Greenhouse comboboxes are not native selects (none exist in this fixture; `<select>` count is 0). |
| `cloak_click` + `cloak_type` + `Enter`      | Production-recommended path for live Greenhouse React Select. Not exercisable here because S4 stripped scripts to keep the form alive. |
| `cloak_evaluate` (set value + dispatch)     | What I used. Works deterministically; bypasses the React state machine. Documented as the fallback. |

## MCP capability dimension

CloakBrowser exposes the primitives needed for React Select handling (`cloak_click`, `cloak_type`, `cloak_press_key`, `cloak_evaluate`), but you have to stitch them yourself. An MCP with a higher-level "combobox" abstraction would be cheaper on tool calls.
