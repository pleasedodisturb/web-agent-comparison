# BrowserMCP — Exploratory Probe (v1.0.x patch evidence)

**Run date:** 2026-05-29
**Host:** macOS arm64 (operator's Mac Mini), Node 26, real Chrome via Chrome Agent profile
**MCP under test:** `@browsermcp/mcp@0.1.3` (npm), binary `mcp-server-browsermcp`
**Methodology:** Direct JSON-RPC walker (no Claude Code orchestration, no LLM cost) — see `probe.py`
**Status:** **Exploratory only — NOT scored on the v1.0 rubric.** This is an out-of-scope follow-up to v1.0's deliberate exclusion of BrowserMCP from the 7-MCP framing.

## Why BrowserMCP was excluded from v1.0

Per `PROJECT.md`: *"different operational model (Chrome extension + Agent profile); kept out for apples-to-apples comparison."*

Concretely, the 7 v1.0 candidates share a key architectural property — **they spawn their own browser** (or, for Firecrawl, a cloud browser). BrowserMCP is categorically different: it **attaches to a pre-existing Chrome session** via a browser extension installed in a specific Chrome profile. The MCP server does not own a browser; it talks to yours over a local WebSocket on port 9009.

This breaks v1.0's framing in three ways:
1. **Headless vs headed.** All 7 v1.0 MCPs ran headless Chromium. BrowserMCP requires Chrome to be open in the foreground.
2. **Profile state.** v1.0's `.mcp.json` is environment-agnostic. BrowserMCP requires a specific Chrome profile with a specific extension installed.
3. **Reproducibility model.** v1.0 fixtures are byte-frozen loopback snapshots. BrowserMCP needs the operator's local Chrome state.

So this is an **exploratory probe**, not a v1.0 row. It captures empirical data without contaminating the v1.0 7-MCP composite framing.

## Headline findings

| Finding | Detail |
|--------|--------|
| **BrowserMCP works end-to-end on real Chrome** | S1+S2 navigate + accessibility-tree snapshot succeeded against loopback fixtures with ~50ms/navigate and ~10ms/snapshot. |
| **Connection-fragility claim from 2026-04 NOT reproduced** | The previous app-level wave noted "disconnected mid-test." During this probe's ~6-second walk, zero disconnects observed. Sample size is small — fragility may surface on longer runs. |
| **Operational model: WebSocket on port 9009** | The MCP server binds `127.0.0.1:9009`; the Chrome extension's "Connect" button initiates the WebSocket handshake. The server kills any prior process on 9009 on startup — re-running `mcp-server-browsermcp` requires the extension to Disconnect → Connect to re-pair. |
| **Output model: YAML accessibility tree, not raw HTML** | BrowserMCP's `browser_snapshot` returns an a11y tree formatted as YAML (e.g., `link "anthropic/" [ref=s1e10]`). Tools use `element + ref` interaction (similar to Playwright's accessibility API), not CSS selectors. **This is a real methodology divergence from v1.0 MCPs** — direct comparison against `data_quality` would require either normalizing outputs or expanding the rubric. |
| **Node-side stack-overflow bug discovered** | When `mcp-server-browsermcp` shuts down without a Chrome connection, `server.close` recurses infinitely → `RangeError: Maximum call stack size exceeded`. Reproducible deterministically. Affects clean exit but not steady-state operation. Worth flagging upstream. |
| **Operator's REAL Chrome TLS fingerprint captured (gold for #11/G-739)** | Because BrowserMCP drives the operator's actual Chrome, navigating to `tools.scrapfly.io/api/fp/ja3?extended=1` and reading the response captures the production-baseline TLS handshake. See `tls_fingerprint.json`. |

## Tool surface

12 tools registered (vs Obscura's 4, Playwright's 21+):

```
browser_navigate, browser_go_back, browser_go_forward,
browser_snapshot, browser_screenshot,
browser_click, browser_hover, browser_type, browser_press_key,
browser_select_option, browser_wait,
browser_get_console_logs
```

Notable surface gaps vs Playwright:
- **No file_upload primitive.** BrowserMCP does not expose `browser_file_upload` — uploads would require keyboard interaction with the file picker dialog, which is OS-modal and unreliable.
- **No batch-fill primitive.** No equivalent of Playwright's `browser_fill_form`. Multi-field forms require N round-trips through `browser_type`.
- **No network/perf surface.** No equivalent of chrome-devtools-mcp's `list_network_requests`, `performance_start_trace`, etc.

Implications for the v1.0 stage walk: **S6 (resume upload) is categorically N/A on BrowserMCP** (no upload primitive), similar to Obscura's S6+S8 gap. S8 (screenshot) is supported via `browser_screenshot`.

## Real Chrome TLS fingerprint

Captured via the same probe (BrowserMCP-drives-real-Chrome navigation to Scrapfly's JA3/JA4 endpoint). Full structured data in [`tls_fingerprint.json`](tls_fingerprint.json). Key digests:

| Fingerprint | Value | Notes |
|-------------|-------|-------|
| `ja3_digest` | `16f5c1035ce7f60fdd6afe5224275811` | Scrapfly's reference set is ~125k samples — cross-checking this digest against the database confirms or denies real-Chrome match |
| `ja4_hash` | `3fc5444b6956` | Newer fingerprint, harder to spoof; this is the production-baseline number to beat |
| `scrapfly_fp_digest` | `2084695c9595178c76ba04d5d080dab8` | Scrapfly's proprietary fingerprint scheme |

Critically, **GREASE values are present** (`0x5A5A` in cipher list, `GREASE-4865-...` in scrapfly_fp). GREASE is Chrome's randomized extension prefix — its presence is a strong "real Chrome" signal, since most spoofing libraries forget it.

**This is the baseline for #11 / G-739** (TLS fingerprint capture per MCP). When other MCPs claim "real Chrome" stealth, their `ja4_hash` should match `3fc5444b6956` or very close. Anything substantially different is a different TLS stack regardless of marketing claims.

## How would BrowserMCP score on the rubric (if we ran it formally)?

This is not done in v1.0.x — it would require either including BrowserMCP in the candidate set (changes the 7-MCP framing) or running it as an explicit 8th row with an `extension-attached` capability tag. Both decisions belong to v1.1, not v1.0.x.

**Speculative rough scoring** based on the exploratory data, NOT to be cited as a real composite:

| Dim | Score | Reasoning |
|-----|------:|-----------|
| Data Quality | ~8 | Accessibility-tree output is structurally clean, lossless of semantic info, more LLM-friendly than raw HTML. |
| Reliability | ~6 | Connection-fragility risk noted in 2026-04 prior wave; not reproduced here but sample size is N=1 probe. Stack-overflow shutdown bug. |
| Speed | ~9 | Sub-100ms per tool call against loopback. Real Chrome native perf. |
| Token Efficiency | ~7 | YAML a11y tree is more verbose than Firecrawl's clean-markdown but tighter than raw HTML. |
| Interaction Depth | ~6 | 12 tools, no batch-fill, no file upload. S5 form fill via `browser_type` + `browser_press_key` should work; S6 categorically N/A. |
| JS Rendering | ~10 | It IS real Chrome; React/SPA rendering is trivially the user's Chrome's responsibility. |
| Setup Complexity | ~3 | Requires Chrome Agent profile launcher script + extension install + manual Connect click. NOT a self-contained `.mcp.json` setup. |
| Error Handling | ~5 | Clear error messages ("No connection to browser extension..."), but the recursive-close bug suggests internal error handling is fragile. |

**Estimated composite (NOT official):** ~ (8×3 + 6×3 + 9×2 + 7×2 + 6×2 + 10×1 + 3×1 + 5×1) / 15 = (24+18+18+14+12+10+3+5) / 15 = 104 / 15 = **6.93**

This would slot BrowserMCP in the **SECONDARY tier**, above browser-use-direct (5.87) but below Playwright (7.93) and Lightpanda (6.31 N/A-aware). The trust model (your Chrome, your tabs) makes it the **only correct choice for authenticated personal sessions** — but the operational model (must launch Chrome + click Connect) makes it impractical for any scenario where the operator isn't present.

## What we did NOT test in this probe

- **Full S1-S8 walk against real job-page fixtures** (probe targeted directory listings; drilling into `anthropic/jobs/5023394008.html` is a follow-up)
- **Multi-pass median per FAIRNESS-01** (single probe — no variance characterization)
- **Stability over a 1-hour soak** (the 2026-04 fragility claim deserves the v1.0 MEAS-07 stability harness)
- **Cold-start latency 3-segment split** (would need the v1.0 `measure_cold_start.py` adapted for BrowserMCP's WebSocket-handshake pattern)
- **Token efficiency 3-scope** (didn't run through Claude Code, so no `payload`/`turn` scope captured)

These are deferred to a v1.1 candidate-decision moment. If v1.1 includes BrowserMCP as the 8th MCP, those measurements become part of its row.

## Evidence files in this directory

- `probe.py` — direct JSON-RPC walker (S1+S2 navigate+snapshot + TLS capture)
- `probe2_output.log` — full tool-call event log from the successful probe run
- `tls_fingerprint.json` — clean structured TLS fingerprint capture (the gold artifact)
- `mcp.overlay.json` — `.mcp.json` overlay used to register BrowserMCP locally (not committed to the repo's sacrosanct `.mcp.json`)

## Tracking

- [GitHub issue]: to be filed as part of this PR — "Consider BrowserMCP as v1.1 candidate (exploratory data + operational model notes)"
- [Linear ticket]: to be filed as v1.1 candidate decision under future-milestone parent (no parent ticket yet — file when v1.1 scope is defined)

## Cost ledger

- Light probe (tool inventory + initial connection attempt): $0
- Full probe (handshake-wait + S1+S2 walk + TLS capture): $0
- **Total v1.0.x BrowserMCP exploration:** **$0** (direct JSON-RPC, no Claude Code session)

The zero-cost result is partly because BrowserMCP's deterministic tool surface doesn't need agent-discovery variance characterization in the way Obscura/browser-use's would. For a v1.1 formal benchmark we'd want LLM-driven passes for parity with v1.0 methodology.
