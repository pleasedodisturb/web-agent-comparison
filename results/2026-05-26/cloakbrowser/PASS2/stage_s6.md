# S6 — Upload resume

## MCP capability gap

CloakBrowser's tool surface (`cloak_launch`, `cloak_navigate`, `cloak_snapshot`, `cloak_click`, `cloak_type`, `cloak_select`, `cloak_check`, `cloak_evaluate`, `cloak_read_page`, `cloak_screenshot`, `cloak_back`, `cloak_forward`, `cloak_hover`, `cloak_press_key`, `cloak_scroll`, `cloak_wait`, `cloak_new_page`, `cloak_close_page`, `cloak_list_pages`, `cloak_close`) does **not** expose a native file-upload primitive.

Compare:
- Playwright MCP — `browser_file_upload(paths)`
- Chrome DevTools MCP — `upload_file`
- BrowserMCP — typically `upload`

The MCP-native idiom for cloakbrowser is therefore "use `cloak_evaluate` to construct a File and assign it to the input via the DataTransfer API." That's the same workaround you'd use with Playwright's `evaluate` if `browser_file_upload` didn't exist.

## What I did

1. Read `fixtures/mock_resume.pdf` from disk (742 bytes).
2. Base64-encoded the bytes outside the browser (the fixture server does not expose the PDF, and the Greenhouse fixture page is on a different origin from the file).
3. Called `cloak_evaluate` to:
   - decode the base64 into a `Uint8Array`,
   - wrap it in a `new File([bytes], 'mock_resume.pdf', {type: 'application/pdf'})`,
   - build a `DataTransfer` object and add the File,
   - assign `input.files = dt.files` on `#resume`,
   - dispatch `change` and `input` events so any listeners fire.

## Result (read back from the DOM)

```json
{
  "set_files_count": 1,
  "file_name": "mock_resume.pdf",
  "file_size": 742,
  "file_type": "application/pdf",
  "input_accept": ".pdf,.doc,.docx,.txt,.rtf"
}
```

`accept` matches `application/pdf` — the file would be accepted by the Greenhouse upload validator if this were a live form.

## Errors encountered

None. The DataTransfer approach succeeded on first attempt under the static-form workaround established in S4 (scripts already removed, so no React handler intercepted `files=`).

## Cost dimension

- 1 `cloak_evaluate` call to perform the upload (after one out-of-band base64 read).
- An MCP with a native `upload_file` primitive would do this in 1 tool call without needing the developer to know the DataTransfer dance.
- For automation that targets stealth-protected real-world forms, the lack of a native primitive is a non-trivial gap — the DataTransfer trick can be detected by aggressive form-fingerprinters that watch for `dispatchEvent` outside a real input flow. This is a real-world stealth concern even though it works fine on local fixtures.
