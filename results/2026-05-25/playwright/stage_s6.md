# S6 — Upload resume

## Outcome: success

| Property | Value |
|---|---|
| File | `fixtures/mock_resume.pdf` |
| Filename on input | `mock_resume.pdf` |
| Size | 742 bytes |
| MIME type | `application/pdf` |
| Input | `#resume` (`<input type="file">`) |
| Tool used | `mcp__playwright__browser_file_upload` |

## What I did

1. **Triggered the file chooser via `browser_evaluate`** — `document.getElementById('resume').click()`. The MCP reported a new modal state: `File chooser: can be handled by browser_file_upload`.
2. **Called `browser_file_upload` with the absolute path** — Playwright wired it to the captured chooser via `fileChooser.setFiles([...])`.
3. **Verified** with another `browser_evaluate` that `input.files[0]` resolves to `mock_resume.pdf` (742 bytes, `application/pdf`).

## Why not just click the "Attach" button?

The Greenhouse posting's "Attach" button normally calls `#resume.click()`
in its JS click handler. Because S4 restored the SSR HTML by replacing
`document.documentElement.innerHTML` (script tags are inert when injected
via innerHTML), the React handlers were never bound to the Attach button —
clicking it timed out with "div.file-upload__wrapper intercepts pointer
events" (a sibling overlay was waiting for a hover state the script would
have toggled).

Triggering the underlying file input directly bypasses the missing
handler. In a normally-loaded Greenhouse page (with working JS) the
straightforward path would be: snapshot ref the Attach button → click →
`browser_file_upload`. Either path produces the same end state on the
`#resume` input.

## MCP-surface note

`browser_file_upload` is designed around the file-chooser modal contract:
it errors with "can only be used when there is related modal state
present" if you call it before triggering a chooser. The MCP cleanly
surfaces the modal in its post-action page state (`### Modal state
- [File chooser]: can be handled by browser_file_upload`), which makes the
choreography explicit and debuggable.
