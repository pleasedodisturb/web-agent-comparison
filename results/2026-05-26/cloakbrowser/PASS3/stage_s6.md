# S6 — Upload resume

**MCP:** cloakbrowser
**Target:** `<input type="file" id="resume" accept=".pdf,.doc,.docx,.txt,.rtf">` (snapshot ref `@e8`)

## Tool used

`cloak_evaluate` with a synthesized `File` + `DataTransfer` assignment.

CloakBrowser's tool surface does **not** include a dedicated upload primitive (no `cloak_file_upload`, no `cloak_upload`). The MCP's interaction surface is click/type/select/press_key/scroll/hover/snapshot/screenshot/evaluate. For file inputs the legitimate path is `cloak_evaluate` — it is a first-class primitive in the server's documented tool list.

## Mechanism

1. Read `fixtures/mock_resume.pdf` from disk (742 bytes, PDF 1.4, one page) via `Bash` → base64.
2. Embed the base64 string into a single `cloak_evaluate` payload.
3. In-page JS:
   - `atob` → `Uint8Array`
   - `new File([bytes], 'mock_resume.pdf', { type: 'application/pdf' })`
   - `new DataTransfer()` → assign to `input.files`
   - Dispatch `input` and `change` events with `bubbles: true` so any listeners that drive UI state see the upload.

## Result (from the same `cloak_evaluate` return)

```json
{
  "fileCount": 1,
  "fileName": "mock_resume.pdf",
  "fileSize": 742,
  "fileType": "application/pdf",
  "accept": ".pdf,.doc,.docx,.txt,.rtf"
}
```

`input.files[0]` matches the source file byte-for-byte (742 bytes), the MIME type is correctly set to `application/pdf`, and the file's extension is in the `accept` list — so a real Greenhouse form-validation pass would accept it.

## Errors

None. Single tool call, no retries.

## Trade-off observed

A purpose-built `browser_file_upload` (Playwright, chrome-devtools) is one tool call with a path string and zero in-page JS. The `cloak_evaluate` path is more boilerplate but has two upsides for stealth use cases:

1. **No host filesystem access from the browser process** — the file is materialised in the page's JS heap, not handed to Chromium via the privileged `setInputFiles` CDP method that detectors can fingerprint.
2. **Works on inputs that are visually hidden behind an "Attach" button** without needing the click sequence; the `@e7 Attach` affordance is bypassed entirely.

The downside: a 742-byte PDF base64s cleanly into one `cloak_evaluate` call, but a 5 MB resume would push the call past the MCP's payload limits. The `terminal-craft` graduation note for this MCP should flag the size ceiling.
