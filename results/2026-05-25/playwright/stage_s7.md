# S7 — React Select source dropdown

## Outcome: partial — input accepts text, React state cannot be driven

| Probe | Result |
|---|---|
| Tool used | `mcp__playwright__browser_type` with `submit: true` (single call: fill + Enter) |
| Target | `#question_14364081008` (the only React Select on the form) |
| Value attempted | `Job board` (from `fixtures/mock_data.json` `source` field) |
| Post-action `input.value` | `"Job board"` ✅ |
| Post-action `aria-expanded` | `false` ✗ (popup never opened) |
| Visible selection in wrapper | empty ✗ (no "Job board" option rendered as selected) |

## Note on what this dropdown actually is

This is **not** the canonical Greenhouse "How did you hear about us?" source
dropdown. It is a custom-question React Select labelled *"Please note that
you will not be considered unless you complete the Constellation
application form."* — the only `react-select`-powered combobox on this
particular posting. It is the closest analog to the brief's S7 target on
this fixture; I drove it with the brief's mock `source` value (`"Job
board"`) for consistency with the rest of the run.

## Why type+Enter did not produce a real selection

The combobox is a standard `react-select` widget:

```
<input class="select__input" id="question_14364081008"
       role="combobox" aria-haspopup="true" aria-autocomplete="list"
       aria-expanded="false" type="text">
```

In a normally-loaded page, `type+Enter` works because react-select's JS
listens on `keydown` to:

1. open the popup (`aria-expanded → true`)
2. filter options as you type
3. promote the highlighted option to selected on Enter
4. write the option's `value` into a hidden form field, not the visible input

In this run, the React handlers are **not bound** — earlier (S4) the
posting was reconstructed by replacing `document.documentElement.innerHTML`
with the static SSR HTML, which is inert (script tags injected via
innerHTML don't execute). The visible `<input>` accepts the keystrokes and
exposes them via `.value`, but the surrounding react-select state never
mutates, so no option is "selected."

## Why the second fallback (drive React state directly) also doesn't work here

The brief suggests `browser_evaluate`-ing into the react-select state. That
strategy requires either:
- access to the `react-select` instance ref (only available if React mounted), or
- a properly bound `onChange` handler to fire (also only available post-hydration).

Both require the bundle to have executed, which it cannot in this
offline-snapshot run. **In a live Greenhouse page hit normally, either the
type+Enter path or a direct evaluate of the react-select `onChange` would
work** — this is a property of the offline fixture, not a Playwright
limitation.

## Bottom line for scoring

- **Playwright's tool surface is sufficient** for both paths the brief
  described (type+Enter via `browser_type`, direct state drive via
  `browser_evaluate`).
- **In this offline-snapshot run** the dropdown is uncontrollable for the
  same reason the resume Attach button was unclickable: no JS handlers
  bound. The input visibly carries the typed string, which would be
  enough to demonstrate the *form submission payload* would include it,
  but not enough to claim the *React state* accepts the value.
