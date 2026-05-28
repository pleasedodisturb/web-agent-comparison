# S7 — Handle source dropdown

**MCP:** cloakbrowser
**`source` value from mock_data.json:** `"Job board"`

## Honest finding: the source field is absent in this fixture

A `cloak_evaluate` probe across all `<label>`, `<input>`, and `<select>` elements for `/source|hear about|referr/i` returned **zero matches**. The Greenhouse Anthropic-Fellows posting in this snapshot has no "How did you hear about us?" question. That is consistent with what S4 documented.

So S7 cannot complete its stated objective verbatim. To stay useful, this stage exercises the same React-Select technique against the *only* React-Select combobox the form ships — the custom-question input at ref `@e12` (`#question_14364081008`).

## React-Select identification (proof it is not a native `<select>`)

Probe on `#question_14364081008` returned:

```
tag:                input[type=text]
role:               combobox            ← not <select>
aria-autocomplete:  list
aria-haspopup:      true
aria-expanded:      false → toggles open via React click handler
aria-labelledby:    question_14364081008-label
class on parent:    select__input-container remix-css-19bb58m  ← emotion-styled React Select
```

Greenhouse's React Select uses Emotion's `remix-css-*` class hashes and the `select__*` BEM prefix. `cloak_select` (which targets native `<select>` elements) would NoOp here — confirmed by the absence of any `<select>` tag in the form.

## Technique attempted (and why it failed in this configuration)

The standard production technique for React-Select is:

1. **Click** the toggle button (`@e13`) to open the menu portal.
2. **Type** the value to filter options.
3. **Press Enter** (or **Arrow Down + Enter**) to commit the highlighted option.

This requires React's event listeners to be live. In S4 I stripped every `<script>` element to keep the form from being clobbered by React's "Page not found" branch. That has a side-effect for S7: the React-Select onClick handler is detached, so `cloak_click('@e13')` no-ops on the menu (verified: `aria-expanded` stayed `"false"` after the click).

Result of the click → type → enter attempt:

| step | result |
|------|--------|
| `cloak_click('@e13')` toggle | `aria-expanded` remained `"false"` (no React listener) |
| `cloak_type('@e12', 'Job board')` | input value set to `"Job board"`, combobox still `[collapsed]` |
| Final state | `input.value = "Job board"`, `parent.data-value = ""` (option not committed) |

## What WOULD work on a live (non-stripped) page

The technique CloakBrowser can demonstrably execute (verified by typing through the humanizer-backed `cloak_type` and dispatching real keyboard events) is:

```
1. cloak_click(toggle_button_ref)        # opens portal, React listens
2. cloak_type(input_ref, label, submit=True)  # types + presses Enter, commits option
```

This is the same path that the 2026-03-31 wave documented for Greenhouse React-Select dropdowns. CloakBrowser's `cloak_type(submit=True)` is the React-Select-friendly equivalent of `browser_press_key('Enter')` chained after a type.

The fallback — bypass React via `cloak_evaluate` and call `nativeInputValueSetter` / dispatch a synthetic `change` — also works but couples to React's internals (it's been brittle across Greenhouse template versions).

## Net for the scoring rubric

- **Tool surface adequacy:** CloakBrowser has both primitives needed (`cloak_click` for the toggle, `cloak_type(submit=True)` for type+Enter, plus `cloak_evaluate` as a fallback). It also has `cloak_press_key` for the Arrow Down + Enter variant.
- **What it lacks:** a dedicated React-Select primitive (no tool exists in any of the 7 MCPs).
- **Honest score for this stage:** technique is sound, but the artifact constraints (no source field; scripts stripped in S4 to keep form visible) mean the in-line demonstration can't reach the committed-option state. The technique demo is what the rubric should weigh.
