# Obscura MCP — Stage Walk Transcript (2026-05-26)

**MCP under test:** `obscura` (obscura-mcp npm wrapper, cloud-routed engine)
**Fixture server:** `http://127.0.0.1:8765` (loopback only — host `curl` returns 200 on both targets)
**Outcome:** STOP at S1. Structural cloud-vs-loopback incompatibility.

## Tools attempted

| Stage | Tool(s) called                                                                                                | Result |
|-------|---------------------------------------------------------------------------------------------------------------|--------|
| pre   | `Bash` curl probe of `/greenhouse_2026-05-22/` and `/ashby_2026-05-22/`                                       | 200 / 200 — fixture server confirmed up |
| S1    | `mcp__obscura__browse_page` (format=markdown + eval, url=greenhouse fixture)                                 | Hard error: `Network error: Access to private/internal IP address 127.0.0.1 is not allowed` |
| S1    | `mcp__obscura__browse_page` (format=markdown, url=ashby fixture) — cross-check                                | Same hard error |
| S1    | `mcp__obscura__browse_session` create → extract `{url, title, h1, bodyLen}`                                   | Session created successfully; extract returns `{"url":"http://127.0.0.1:8765/greenhouse_2026-05-22/","title":"","bodyLen":0}` — silent 0-byte page |
| S1    | `mcp__obscura__browse_session` close                                                                          | OK |
| S2–S8 | Not attempted — user instruction was to STOP if a stage cannot be completed |  |

## Why stopped

Obscura's two surfaces fail differently on the same input but with the same root cause:

- **`browse_page`** throws an explicit SSRF-policy error referencing the private/loopback address.
- **`browse_session`** silently navigates and returns a zero-byte page (URL reflected, body empty). This is the more dangerous failure mode — looks like a successful empty fetch unless the caller checks `bodyLen`.

Both behaviors are consistent with a server-side SSRF filter on the cloud worker rejecting RFC1918 and loopback ranges. There is no client-side knob in the MCP surface to bypass it (no proxy override, no "use my own browser" mode, no per-request egress IP selection).

This is the same architectural finding the firecrawl wave already captured for this milestone (see prior commits `0003430`, `981c6a9`, `872dd73`, `2640061` — "cloud-vs-loopback empirical proof"). Cloud-routed MCPs are structurally incompatible with local-fixture benchmarks. Stages S2 through S8 would all have failed by the same mechanism (every target URL is on `127.0.0.1:8765`) and re-running them would not add information.

## Caveats / additional notes

- The two failure modes (hard error vs silent 0-byte) are themselves a robustness finding worth carrying into the scoring rubric: a session-level silent zero-byte is harder to detect downstream than a thrown error.
- Obscura's tool surface also lacks two primitives that S6 and S8 require regardless of reachability: no `file_upload` primitive and no `screenshot` primitive. Even if a public-target version of this benchmark were run, S6 and S8 would be `.NA` for capability reasons.
- For Stage 2 (terminal-craft graduation): Obscura's value is on public, server-rendered bulk scraping where its cloud egress is desirable. It is the wrong choice for any flow that touches local services, internal hosts, or VPN-only endpoints.

## Files written

- `stage_s1.FAILED` — one-line failure reason
- `transcript.md` — this file
