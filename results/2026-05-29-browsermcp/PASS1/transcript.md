# BrowserMCP — Stage Walk Transcript (2026-05-29)

**MCP under test:** `browsermcp` (`@browsermcp/mcp` via npx, per `.mcp.json`).
**Connection model:** WebSocket bridge to a real Chrome tab via the
BrowserMCP browser extension. NOT a spawned browser — inherits the host's
TLS fingerprint, cookies, and profile.
**Snapshot server:** `http://127.0.0.1:8765` (loopback).
**Output dir:** `results/2026-05-29/browsermcp/`.

## Connection setup (pre-S1)

- First `browser_navigate` call returned: *"No connection to browser
  extension. ... click 'Connect' button."*
- Bash-launched `~/.claude/scripts/chrome-agent.sh` to bring up the Chrome
  Agent profile (Profile Agent, PID 82814) where the BrowserMCP extension
  is installed and pre-authorised. Extension auto-reconnected to the
  freshly-opened tab.
- Retry succeeded — `browser_navigate` then returned a normal accessibility
  snapshot.
- **Implication for unattended scoring:** BrowserMCP is non-headless and
  requires a desktop session with the extension installed + a tab
  pre-bound. The Chrome Agent profile script is a workaround that makes
  it auto-reconnect, but it does not work on a remote/CI runner. Counts
  against the `harness-ergonomics` and `cross-machine reproducibility`
  rubric dimensions.

## Per-stage summary

| Stage | Tools called                                                                   | Outcome         | Artifact                       |
|-------|--------------------------------------------------------------------------------|-----------------|--------------------------------|
| S1    | `browser_navigate`, `browser_click`, `browser_wait`, `browser_snapshot`        | PARTIAL_VIA_MCP | `stage_s1.yml`                 |
| S2    | `browser_navigate`, `browser_wait`, `browser_snapshot`                         | EMPTY_BY_DESIGN | `stage_s2.yml`                 |
| S3    | (analysis — no MCP calls)                                                      | OK              | `stage_s3.md`                  |
| S4    | `browser_navigate`, `browser_snapshot`                                         | FAILED          | `stage_s4.FAILED`              |
| S5    | (cascaded — no calls)                                                          | FAILED          | `stage_s5.FAILED`              |
| S6    | (cascaded — no calls)                                                          | FAILED          | `stage_s6.FAILED`              |
| S7    | (cascaded — no calls)                                                          | FAILED          | `stage_s7.FAILED`              |
| S8    | `browser_screenshot`                                                           | CAPTURED        | `stage_s8.md` (PNG inline)     |

## Root cause — why S4–S7 cascaded

The Greenhouse snapshot at
`fixtures/snapshots/greenhouse_2026-05-22/anthropic/jobs/5023394008.html`
is server-rendered HTML that **includes** the job posting AND the
`<form id="application-form">` apply form embedded in the SSR shell. It
also includes the Greenhouse React bundle. When BrowserMCP routes Chrome
to this page:

1. SSR HTML paints briefly.
2. The React app hydrates, re-fetches the job from a backend URL that
   does not exist on the local snapshot server.
3. On the fetch error, Greenhouse's app routes to its built-in "Page not
   found" view, which **replaces the entire DOM** — wiping the job
   description AND the apply form.
4. BrowserMCP's accessibility snapshot, taken after hydration, sees only
   the 404.

BrowserMCP exposes **no tool to:** disable JavaScript, fetch raw HTML,
intercept network requests, evaluate JS in the page, or override
fetch responses. So the SSR form is unrecoverable from inside this MCP.
The same fixture would yield a different result for:
- Lightpanda (no JS → would see the SSR form, but can't fill it
  read-only).
- Firecrawl (server-side scrape of SSR shell).
- Playwright / chrome-devtools / browser-use (have `evaluate` /
  request-interception / `--disable-javascript` paths — *should* be able
  to recover the SSR form).

## What worked well

- `browser_navigate` returns a clean YAML accessibility snapshot
  immediately — concise, no DOM-dump bloat.
- `browser_click` correctly clicks by `ref` from the snapshot — no
  need for CSS selectors or coordinate math.
- `browser_screenshot` succeeded (returned PNG inline).
- Cold-start latency was sub-second on retry (extension already
  attached).

## What did not work (capability gaps vs. Playwright)

| Gap                              | Playwright equivalent             | Impact on rubric    |
|----------------------------------|-----------------------------------|---------------------|
| No raw-HTML / "get source"       | `page.content()` / `browser_evaluate` | dim. 4 (results-fidelity), dim. 8 (resilience) |
| No JS evaluation surface         | `browser_evaluate`                | dim. 7 (workarounds for React Select) |
| No request interception / mock   | Playwright route handler          | dim. 8 (resilience to broken backends) |
| No file-path screenshot          | `browser_take_screenshot --path`  | dim. 6 (harness-ergonomics) |
| No `browser_file_upload`         | `browser_file_upload`             | dim. 5 (form-fill completeness) |
| Requires desktop Chrome + ext.   | Headless Chromium spawned by MCP  | dim. 6, cross-machine reproducibility |

## Caveats for the scorer

- The S8 PNG bytes live in `raw_stream.jsonl` (inline base64 in the
  `browser_screenshot` tool result), not as a standalone `.png` on
  disk. The harness should grep the stream for the screenshot
  message-id and decode if a viewable artifact is required.
- S1's "salvaged SSR shell contents" block in `stage_s1.yml` was read
  via Bash from the snapshot file, NOT via BrowserMCP — included
  for the auditor's reference only; it must NOT count toward
  BrowserMCP's extraction score.
- Chrome instance used: real Chrome 148.0.7778.179, Profile Agent (per
  `~/.claude/scripts/chrome-agent.sh`).

## Tools allow-list compliance

Used only: `mcp__browsermcp__browser_navigate`, `browser_click`,
`browser_wait`, `browser_snapshot`, `browser_screenshot`; `Read`,
`Write`, `Bash`. No `WebFetch`, no other MCP, no shell-out to a
different browser. Allow-list contract maintained.
