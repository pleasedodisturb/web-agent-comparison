# S6 — Upload resume

## Tool used

`mcp__chrome-devtools__upload_file` — one call.

## Target

- File: `/Users/pleasedodisturb/Projects/web-agent-comparison/fixtures/mock_resume.pdf`
- Input: `<input id="resume" type="file" accept=".pdf,.doc,.docx,.txt,.rtf" class="visually-hidden">`
  (the actual file input is `visually-hidden`; the visible "Attach" button is its
  Greenhouse wrapper)
- Target uid passed: `5_300` (the upload tool resolves visible click-targets that open
  the OS file chooser — no need to address the hidden input directly).

## Result

Upload **succeeded** on first try.

Post-upload verification via `evaluate_script`:

```json
{ "name": "mock_resume.pdf", "size": 742, "type": "application/pdf" }
```

- The DOM file input received the correct `File` object (`document.getElementById('resume').files`).
- Name, size, and MIME type all match the source file on disk.
- The Greenhouse UI's "value" attribute on the button wrapper did not visibly update in the
  rendered tree to show the filename (this is a Greenhouse SSR quirk — in the live site
  the React component updates a label; without React running, the label stays "No file
  chosen"). Functionally the file IS attached to the form — only the cosmetic label
  doesn't refresh.

## Errors

None.

## MCP capability finding

- chrome-devtools `upload_file` handles the standard Greenhouse pattern of
  `visually-hidden` file input + "Attach" button wrapper without special handling — the
  MCP resolves the visible click target to the underlying file chooser.
- Total tool calls for upload: 1 (upload_file) + 1 (evaluate_script verify).

## Tools used

- `mcp__chrome-devtools__upload_file`
- `mcp__chrome-devtools__evaluate_script`
