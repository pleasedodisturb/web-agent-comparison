# S7 — Source / "Constellation form completed" dropdown (Lightpanda)

## Outcome: FAILED — no technique successfully set the React Select state

This Greenhouse fixture's source-style dropdown is a react-select v5 combobox
(`#question_14364081008`, accessible name "Please note that you will not be
considered unless you complete the Constellation application form. *").
Lightpanda's Zig-based JS runtime cannot execute the react-select React
handlers, so none of the documented setting techniques worked.

## Techniques attempted (in order)

### 1. `mcp__lightpanda__selectOption` — REJECTED at MCP layer
```
selectOption(backendNodeId=13, value="Job board")
→ MCP error -32602: Node is not a <select> element
```
Confirms react-select is not a native `<select>` — same outcome we'd see in
any MCP. Tool refused, which is the correct behavior.

### 2. `fill` + `press Enter` — visually wrote text, did NOT update React state
```
fill(13, "Job board")         → input.value = "Job board"
press(13, "Enter")            → no menu open, no option selected
```
Post-conditions read back via `evaluate`:
- `input.value` = "Job board"   (just sits there as a literal string)
- `aria-expanded` = "false"     (menu never opened)
- placeholder ".select__placeholder" still visible reading "Select..."
- `data-value` on input-container = ""   (react-select internal state unchanged)
- `.select__menu` / `.select__option` nodes never created
- Body HTML contains 0 occurrences of "Job board" outside the input itself

### 3. DOM probe for any selectable option list — empty
```
querySelector('.select__menu')         → null
querySelector('.select__option')       → null
querySelectorAll('input[name*=question]')  → []
```
The static snapshot was frozen BEFORE the dropdown was ever opened, so the
options array (which react-select fetches/renders only on interaction) is
literally absent from the DOM. Even a "real" browser would need a click +
async render to materialize the options here.

### 4. JS `.value =` assignment (workaround, not equivalent to selecting)
Could have set the visible input's `value`, but that would NOT trigger the
react-select `onChange` and would NOT register a real selection. Skipped —
would produce a fake green check.

## Why this is a Lightpanda limit, not a fixture limit

Other engines (chrome-devtools, Playwright) can drive react-select v5 by:
- clicking the `.select__control`, waiting for `.select__menu` to mount,
  then clicking the matching `.select__option`, or
- driving react-select's keyboard model: focus input, ArrowDown to open
  menu, type filter, ArrowDown to highlight, Enter to commit.

Both depend on the React event loop running. Lightpanda's browsercore engine
implements just enough of the DOM/JS surface to render static HTML; the
react-select runtime never executes, so the menu never mounts, so there is
nothing to click or commit to.

## Verdict

This dimension is the predicted Lightpanda weakness, mirroring the S2 SPA
failure: Lightpanda is for static/SSR content, not interactive React widgets.
The "source" question stays blank — document as FAILED on the rubric's
interactive-widget axis.
