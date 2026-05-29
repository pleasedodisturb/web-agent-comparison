# browser-use MCP — 2026-05-28 stage walk transcript

**Verdict: 0/8 stages completed. MCP non-functional in this environment.**

## Root cause

The `browser-use` MCP exposes two surfaces and both are dead:

1. **Stdio tool surface** (`browser_navigate`, `browser_get_state`, `browser_get_html`, `browser_screenshot`, `browser_click`, `browser_type`, `browser_scroll`, `browser_extract_content`, etc.) — `browser_navigate` returns a misleading success string ("Navigated to: …") but the underlying browser session never actually launches. Every follow-up call fails:
   - `browser_get_state` → `Expected at least one handler to return a non-None result`
   - `browser_get_html` → `Root CDP client not initialized`
   - `browser_screenshot` → `Root CDP client not initialized`
   - `browser_list_sessions` → `No active browser sessions`
   - `browser_extract_content` → `LLM not initialized (set OPENAI_API_KEY)`
   - First `browser_navigate` call also hit a 30s `BrowserStartEvent` timeout.

2. **Agent fallback** (`retry_with_browser_use_agent`) — fails with HTTP 401 because the MCP is shipped with a placeholder OpenAI API key (`your-ope...here`). The agent loops through 5 steps producing only 401s, never extracts anything.

## Per-stage results

| Stage | File | Tool attempted | Outcome |
|-------|------|----------------|---------|
| S1 | stage_s1.FAILED | `browser_navigate`, `browser_extract_content`, `browser_get_state`, `browser_get_html`, `retry_with_browser_use_agent` | CDP never initializes; LLM key invalid |
| S2 | stage_s2.FAILED | n/a — same MCP, same failure |
| S3 | stage_s3.FAILED | n/a — no S1/S2 artifacts to compare |
| S4 | stage_s4.FAILED | n/a |
| S5 | stage_s5.FAILED | n/a — `browser_type` requires `index` from `browser_get_state`, which is dead |
| S6 | stage_s6.FAILED | n/a — no file_upload primitive reachable without a live page |
| S7 | stage_s7.FAILED | n/a |
| S8 | stage_s8.FAILED | `browser_screenshot` returns "Root CDP client not initialized" |

## Caveats / scoring notes

- The `browser_navigate` tool returns a false-positive success message even when no browser has been launched. This is a tool-bug worth flagging in the cross-cutting stability dimension — the MCP lies about success.
- `retry_with_browser_use_agent` (the headline browser-use agent loop) is gated on an LLM key that the MCP packaging does not source from any standard env var on this host. The 2026-05-21 testbench note ("transport mismatch on `initialize`") may have been resolved in 0.12.7, but the LLM-key precondition was not in scope of that bug — it remains a blocker.
- Honored the fairness contract: only `mcp__browser-use__*`, `Read`, `Write`, `Bash` were called. No WebFetch, no other MCP, no manual file-fetching to fake stage artifacts.
- One bash command (`curl -sI`) was used pre-stage to confirm the snapshot server was up; no fixture content was scraped via curl.
