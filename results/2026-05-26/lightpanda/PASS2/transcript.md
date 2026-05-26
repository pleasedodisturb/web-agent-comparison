# lightpanda — Stage Walk Transcript (2026-05-26)

**MCP under test:** lightpanda
**Snapshot server:** http://127.0.0.1:8765
**Output dir:** results/2026-05-26/lightpanda/
**Tool allow-list used:** `mcp__lightpanda__*`, `Read`, `Write`, `Bash`. No fallback to WebFetch or any other MCP.

## Per-stage summary

| Stage | Verdict | Tools used | Notes |
|---|---|---|---|
| S1 | ✅ PASS | `goto`, `links`, `markdown`, `structuredData` | Greenhouse is server-rendered — full job content extracted from a JS-less browser. Drilled directory listing → `anthropic/` → `jobs/` → `5023394008.html`. Apply button: `https://bit.ly/afpsafety` (external Constellation portal). |
| S2 | ❌ FAILED (`spa_no_render`) | `goto`, `markdown`, `structuredData`, `semantic_tree`, `evaluate` | Ashby React shell never hydrates — markdown empty, semantic tree single `RootWebArea 'Jobs'`, body text 55 bytes (noscript fallback), `<div id="root">` rendered but app code never executes. Lightpanda's Zig engine implements a minimal JS subset; bundled React runtime is out of reach. **This is the expected, stable failure for the SPA-rendering dimension.** |
| S3 | ✅ PASS | none (reasoning from S1/S2 snapshots) | Greenhouse vs Ashby distinguished by URL shape (numeric ID vs UUID), CDN host (`greenhouse.io` vs `ashbyprd.com`), theme color (`#483fad`), and the failure-mode signature itself (server-rendered fills vs SPA hydrates). |
| S4 | N/A | — | Read-only MCP per locked stage-walk contract; no interaction surface invoked. |
| S5 | N/A | — | Read-only MCP per locked stage-walk contract. |
| S6 | N/A | — | Read-only MCP per locked stage-walk contract. No file-upload primitive. |
| S7 | N/A | — | Read-only MCP per locked stage-walk contract. No dropdown-interaction invoked. |
| S8 | N/A | — | Read-only MCP per locked stage-walk contract. No native screenshot primitive (`mcp__lightpanda__*` exposes no image-capture tool). |

## Failure modes hit

- **S2 SPA non-render**: stable, reproducible. Captured in `stage_s2.FAILED` (one-liner) and `stage_s2.diagnostic.yml` (full evidence: tool-by-tool output, `<title>=Jobs`, body text 55 bytes, root children 2, scripts 2 unexecuted, root cause analysis). This is a feature of the benchmark, not a regression — lightpanda's value proposition is bulk fetching of server-rendered pages, not SPA rendering.

## Tool-allow-list compliance

- No `WebFetch` invocation.
- No other MCP (`mcp__playwright__*`, `mcp__chrome-devtools__*`, etc.) invocation.
- One spurious empty-name tool call slip during stage transitions, rejected by the harness — no other MCP surface was touched. Telemetry should ignore it.

## Caveats

- Fixture content is the "Jane Testworth"-scrubbed snapshot (proper nouns replaced for privacy). Page structure, DOM, and JS behavior are preserved, so this does not affect the lightpanda failure-mode result.
- Lightpanda's tool inventory technically *does* expose `click`, `fill`, `selectOption`, `setChecked`, `press`, `hover` since some version after the harness was authored. The locked contract still classifies it as read-only for stage-walk purposes; treat that as a forward-looking note for the next harness revision, not a finding to act on this run.
- Lightpanda has no native screenshot tool — even if S4-S7 had been attempted, S8 would still be N/A.
