# obscura — 2026-05-26 stage walk transcript

**Verdict:** S1 DEGRADED (returned post-React-hydration "Page not found" instead of SSR job content), S2–S8 FAILED (MCP wedged after S1).

## Per-stage summary

| Stage | Status | Tool(s) used | Outcome |
|---|---|---|---|
| S1 | DEGRADED | `mcp__obscura__browse_page` (markdown, html) | Navigated; React bundle clobbered SSR content with 404 component. No job fields extracted. |
| S2 | FAILED | `mcp__obscura__browse_page` (text) | `CDP request timed out: Target.createTarget` |
| S3 | FAILED | n/a | No second snapshot to compare against. |
| S4 | FAILED | n/a | MCP wedged; not a read-only-NA, see stage_s4.FAILED. |
| S5 | FAILED | n/a | MCP wedged; no batch-fill primitive in obscura anyway. |
| S6 | FAILED | n/a | MCP wedged; no file-upload primitive exists in obscura. |
| S7 | FAILED | n/a | MCP wedged; React Select interaction not reached. |
| S8 | FAILED | n/a | MCP wedged; no screenshot primitive in obscura (formats are text/markdown/html/links/cookies/axtree/layout). |

## Key findings (the things worth flagging to scoring)

### 1. SSRF guard blocks the standard loopback URL forms

Obscura's `browse_page` refused every standard loopback URL:

- `http://127.0.0.1:8765/...` → `Access to private/internal IP address 127.0.0.1 is not allowed`
- `http://localhost:8765/...` → `Access to localhost domain 'localhost' is not allowed`
- `http://[::1]:8765/...` → `Access to private/internal IPv6 address ::1 is not allowed`
- `http://0.0.0.0:8765/...` → **accepted** (macOS routes 0.0.0.0:port to local listeners; obscura's check apparently doesn't normalise this)

The 2026-05-26 harness boots the snapshot server bound to 127.0.0.1 only. Without the 0.0.0.0 fall-through, obscura would have scored 0/8 outright at the navigation step. This is a hardcoded behavior of obscura, not a tunable. Recommend the harness either (a) document the 0.0.0.0 substitution as an obscura-specific concession or (b) bind the snapshot server to a private LAN IP (e.g. 192.168.x.x) that obscura's filter does or doesn't accept consistently.

### 2. React hydration clobbers SSR snapshots

Obscura is a full Chromium-driven MCP. On the Greenhouse fixture, it executes the live `job-boards.cdn.greenhouse.io` React bundle, which then fetches dynamic job data, fails (the snapshotted job ID isn't in the live API), and **renders a "Page not found" component over the 84 KB of perfectly good SSR content**. Obscura returns the post-hydration DOM regardless of `format` (text, markdown, html — all returned the 404 state).

This is not an obscura defect per se — any browser-based MCP that executes JS will hit this on static-React-SPA fixtures. It IS a finding for the rubric: obscura cannot extract content from a snapshot whose JS layer makes outbound calls that won't resolve.

The dedicated way to bypass this would be to disable JS execution before navigation. Obscura's `browse_page` exposes no such option (no `javascript: false`, no `wait_until: 'domcontentloaded'` to bail before scripts run). Best workaround on the obscura surface would be to fetch the raw bytes via `eval` — see finding #3.

### 3. eval has no async path and sync XHR bricks the MCP

Attempted to extract the raw SSR HTML via `eval` two ways:

1. **Async fetch:**
   ```
   eval: (async () => { const r = await fetch(location.href); return await r.text(); })()
   ```
   Returned the literal string `Promise`. Obscura's eval pipeline serializes the immediate value of the expression; it does not await thenables.

2. **Sync XHR:**
   ```
   eval: (() => { const x = new XMLHttpRequest(); x.open('GET', location.href, false); x.send(); return x.responseText; })()
   ```
   The synchronous network call blocked the renderer thread. Obscura's CDP coordinator timed out. From that call onward, every `browse_page` / `browse_session.create` call returned `CDP request timed out: Target.createTarget`. The MCP did **not recover within the remaining session lifetime (~6 minutes)**. The `obscura serve` Node process stayed alive (PID 57077, no child Chromium visible in `ps`), implying the issue is at the Chromium-spawn or target-attach layer, not a serve crash.

Net effect: a single bad eval payload **permanently disabled obscura for the rest of the session**. The harness should consider this a stability defect — there's no client-side reset (no `browser_close`-style primitive in obscura's surface).

### 4. Surface gaps independent of the wedge

Even if obscura had not wedged, several stages were already going to fail or be very hard:

- **S6 file upload:** obscura's tool list has no upload primitive. Closest analogue would be `eval` to set `input.files`, but that requires a `DataTransfer` constructor + a real File object, which can't be constructed from a host-side path inside `eval`.
- **S8 screenshot:** obscura's `format` enum does not include `png` or `screenshot`. There is no screenshot primitive. The harness should mark this NA structurally, even on a healthy obscura.
- **S7 React Select:** obscura's `browse_interact` action=`type` would have to be paired with a `press_key` for Enter; the surface has no `press` action. Would have required `browse_session` with a typed-character-by-character approach, or eval-injection into the React props.

## Tools the run touched

- `mcp__obscura__browse_page` (only obscura tool to produce output before wedge)
- `mcp__obscura__browse_session` (action=list returned "No active sessions", action=create timed out)
- `Read`, `Bash`, `Write` (standard scoring/evidence handling)

## Tools NOT used (deliberately)

- `mcp__obscura__browse_scrape` (parallel-worker bulk-extract; not the right shape for any S1-S8 stage and would have hit the same React-hydration issue)
- `mcp__obscura__browse_interact` (planned for S5, never reached because of wedge)
- No `WebFetch`, no other MCP — harness allow-list respected.

## Reproducibility note

The wedge is reproducible: the failure-inducing eval payload is recorded above. A clean run starting from a freshly-spawned `obscura serve` would presumably get past S1 with the same degraded result, and again wedge if the sync-XHR eval is repeated. A run that avoids the sync XHR entirely would not wedge, but also would not extract more than the post-hydration 404 page from the Greenhouse fixture without an alternate strategy (e.g. blocking JS or fetching raw HTML out-of-band, neither of which obscura's surface supports).
