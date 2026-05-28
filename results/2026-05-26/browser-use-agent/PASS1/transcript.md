# browser-use MCP — Stage Walk Transcript (2026-05-28)

**Target:** snapshot fixtures at `http://127.0.0.1:8765` (Greenhouse + Ashby)
**MCP under test:** `browser-use` (PyPI `browser-use` 0.12.x, stdio transport)
**Allow-list honoured:** `mcp__browser-use__*`, `Read`, `Write`, `Bash`. No WebFetch, no other MCPs.

## Verdict: 0 / 8 stages completed

All eight stages produced `stage_sN.FAILED` markers. The root cause is a single
infrastructural failure that takes the entire tool surface offline.

## Failure mode

`browser_navigate` accepts the URL and returns the literal string
`"Navigated to: <url>"`, but `browser_list_sessions` immediately reports
**"No active browser sessions"** and every downstream tool errors:

| Tool | Error |
|---|---|
| `browser_get_state` | `Expected at least one handler to return a non-None result … BrowserStateRequestEvent` |
| `browser_get_html` | `Root CDP client not initialized` |
| `browser_screenshot` | `Root CDP client not initialized` |
| `browser_click`, `browser_type`, `browser_scroll` | (same — depend on CDP) |
| `browser_extract_content` | `LLM not initialized (set OPENAI_API_KEY)` |
| `retry_with_browser_use_agent` | Navigates 4× but every LLM step returns `401 Incorrect API key provided: ar7NRR6U********wxqU` — invalid key embedded in MCP config |

The very first `browser_navigate` call also took **>30s and timed out** on the
`BrowserStartEvent` watchdog before a retry succeeded — Chromium did launch
eventually, but the CDP wiring never attached to the MCP server, so the server's
own state shows zero sessions even while a browser is running.

## What I tried

1. Retry `browser_navigate` after the 30s timeout — second call returned
   "success" but produced no session.
2. `browser_list_sessions` — `"No active browser sessions"` (state is
   inconsistent: navigate "worked", session count = 0).
3. `browser_close_all` — `"No active sessions to close"`.
4. `browser_get_state`, `browser_get_html`, `browser_screenshot` — all errored
   on missing CDP client.
5. `browser_extract_content` — refused (`LLM not initialized`).
6. `retry_with_browser_use_agent` with `max_steps=3` and
   `allowed_domains=["127.0.0.1"]` — agent visited the URL four times but every
   LLM step returned HTTP 401 with a redacted-but-clearly-invalid OpenAI key.

## Tools used per stage

| Stage | Tools attempted | Outcome |
|---|---|---|
| S1 | `browser_navigate`, `browser_get_state`, `browser_get_html`, `browser_extract_content`, `retry_with_browser_use_agent` | FAILED — CDP + LLM both unusable |
| S2 | (covered by S1's failure; not re-attempted to avoid spinning a broken loop) | FAILED |
| S3 | (depends on S1 + S2 artifacts) | FAILED |
| S4 | (depends on `browser_click` / `browser_get_state`) | FAILED |
| S5 | (depends on `browser_type` + indices) | FAILED |
| S6 | (browser-use 0.12.x has no `file_upload` primitive) | FAILED |
| S7 | (no element indices; no `evaluate`/`run_code` primitive) | FAILED |
| S8 | (`browser_screenshot` → CDP error) | FAILED |

## Caveats and notes for scoring

- This is a **runtime / configuration failure**, not a missing-capability
  failure. browser-use's tool surface in principle covers S1–S8 (extract,
  click, type, screenshot) — except S6, where there is no file-upload tool
  exposed at all in 0.12.x, and S7's React-Select would have needed clever
  typing since no `evaluate` primitive exists either.
- The `01 Incorrect API key` error from `retry_with_browser_use_agent`
  suggests the `.mcp.json` is feeding a stale/wrong OPENAI key. Fixing the key
  would unblock the agent path but NOT the lower-level `browser_*` tools —
  those failed for a different reason (CDP not initialized), which is the
  browser-tools.md 2026-05-21 documented stdio-transport regression.
- No non-`mcp__browser-use__` tools were used for interaction. Only `Read`,
  `Write`, `Bash`, and `TaskCreate`/`TaskUpdate` (allow-list compliant).
- This reproduces the 2026-05-21 testbench result documented in
  `~/.claude/docs/browser-tools.md`: browser-use scored 0/15 with timeout on
  every `initialize`. Today's run upgrades the diagnostic — the server does
  initialize, but its CDP client never attaches.
