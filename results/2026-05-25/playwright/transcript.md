# Playwright MCP — Stage Walk Transcript (2026-05-25)

**MCP under test:** `@playwright/mcp` (version per harness)
**Snapshot server:** `http://127.0.0.1:8765`
**Output dir:** `results/2026-05-25/playwright/`
**Allow-listed tools:** `mcp__playwright__*`, `Read`, `Write`, `Bash`
(no fall-through to `WebFetch` or other MCPs)

## Per-stage summary

| Stage | Outcome | Tools used | Artifact |
|---|---|---|---|
| S1 | ✅ success (full extraction) | `browser_navigate`, `browser_evaluate` (with `fetch` + `DOMParser`) | `stage_s1.yml` |
| S2 | ⚠️ rendered, payload empty (snapshot is loader shell only) | `browser_navigate`, `browser_evaluate` | `stage_s2.yml` |
| S3 | ✅ confident classification of both ATSs | (analysis only — no MCP call) | `stage_s3.md` |
| S4 | ✅ form reconstructed and snapshotted with stable refs | `browser_navigate`, `browser_evaluate` (HTML restore), `browser_snapshot` | `stage_s4.yml` |
| S5 | ✅ 4-field fill via single batched call (LinkedIn/GitHub absent from fixture) | `browser_fill_form` | `stage_s5.md` |
| S6 | ✅ resume uploaded, verified on `#resume.files[0]` | `browser_evaluate` (chooser trigger), `browser_file_upload` | `stage_s6.md` |
| S7 | ⚠️ partial — input accepts text, React-Select state not driveable offline | `browser_type` (fill + Enter) | `stage_s7.md` |
| S8 | ✅ full-page PNG, 1.92 MB | `browser_evaluate` (scroll), `browser_take_screenshot` | `stage_s8.png` |

## Key findings

### 1. Both fixtures are SPAs that wipe the DOM offline

When Playwright navigates to either snapshot, the React/Next.js bundle
attempts a runtime fetch against the live backend, fails, and replaces the
DOM with an error page (`Greenhouse: "Page not found"`, `Ashby: "The page
you requested was not found"`). Naively snapshotting after navigation
yields ~120 chars of error text.

**Workaround for Greenhouse (used in S4-S8):** fetch the raw HTML inside
`browser_evaluate`, parse with `DOMParser`, and replace
`document.documentElement.innerHTML` with the inner markup. Per HTML5,
script tags injected via `innerHTML` are inert, so the SSR DOM survives
and is interactable.

**Workaround for Ashby (S2):** none possible. The Ashby fixture is a
6.3 KB SPA loader shell with `window.__appData = { posting: null }` — no
content is serialized; everything is fetched from `cdn.ashbyprd.com` at
runtime. This is a snapshot-fidelity gap, not a Playwright capability gap.

### 2. SSR-restored Greenhouse loses JS event handlers (cascading effects on S6, S7)

The innerHTML trick recovers the form *markup* but not its bound React
handlers:
- S6: the "Attach" button can't be clicked to trigger the file chooser
  (a sibling overlay intercepts pointer events because its hover-state JS
  never registered). Workaround: trigger `#resume.click()` directly via
  `browser_evaluate`, then `browser_file_upload`.
- S7: react-select's keydown handler is unbound, so type+Enter writes
  text into the visible `<input>` but never updates the react-select
  selection state. No selectable option list exists to drive.

In a **live** Greenhouse page (online, normal hydration) both of these
work straight-through — they're collateral damage from the SSR-rescue
strategy.

### 3. Tool choices that paid off

- `browser_fill_form` with 4 field descriptors batched cleanly into one
  Playwright `page.locator(...).fill()` per field, no permission prompt,
  no per-field round-trip. This is the right primitive for multi-field
  forms.
- `browser_snapshot` with `target: '#application-form'` and `filename:`
  produced a compact 57-line accessibility tree of just the form
  subtree — fast for the LLM to reason over, cheap on context.
- `browser_evaluate` is the load-bearing tool: it handled raw-HTML
  reconstruction (S4), file-chooser triggering (S6), and React-state
  inspection (S7).

### 4. Form fixture has fewer fields than the brief assumed

The scrubbed Greenhouse posting (Anthropic Fellows Program, anonymized)
includes only the four identity fields (first/last/email/phone), a
Country combobox, a Resume upload, and one custom React-Select question.
There are no `linkedin` or `github` inputs. S5 filled the 4 available
fields; "6 fields" is not achievable on this fixture regardless of MCP.

## Failures and caveats

- **No stage marked `.FAILED`** — all 8 stages produced an artifact.
- **S2 and S7 are partial:** S2 was a payload-empty render (honest
  representation of the fixture's content); S7 wrote text to the
  combobox input but the React-Select state remained unselected.
- **No `WebFetch` or non-`mcp__playwright__` MCP was invoked** — only
  `Read`, `Write`, `Bash` (for `curl` / `ls` / `grep` on fixture files)
  and Playwright tools. Fairness contract preserved.

## Tool-call count (approximate, from this session)

| Tool | Count |
|---|---|
| `mcp__playwright__browser_navigate` | 4 |
| `mcp__playwright__browser_evaluate` | ~10 |
| `mcp__playwright__browser_snapshot` | 1 (with `filename:` for S4) |
| `mcp__playwright__browser_fill_form` | 1 |
| `mcp__playwright__browser_click` | 2 (1 timeout, 1 success via snapshot ref) |
| `mcp__playwright__browser_file_upload` | 1 (success) + 1 (errored before chooser opened) |
| `mcp__playwright__browser_type` | 1 |
| `mcp__playwright__browser_take_screenshot` | 1 |
| `Read` / `Write` / `Bash` | ~10 (fixture inspection, output writes) |
