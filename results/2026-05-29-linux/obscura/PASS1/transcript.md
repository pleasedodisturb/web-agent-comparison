# Obscura MCP — Stage Walk Transcript (2026-05-29)

**MCP under test:** `obscura` (`obscura-mcp@0.1.4-3`, wrapper around the
`Obscura — Headless Browser v0.1.0` Rust/V8 engine), launched by the harness
as `node /usr/local/bin/obscura-mcp --stealth`.
**Snapshot server:** `http://127.0.0.1:8765` (loopback).
**Allowed tools:** `mcp__obscura__*`, `Read`, `Write`, `Bash`.

## Verdict: TOTAL FAILURE — no obscura tool can reach the fixtures

Every stage is `.FAILED`. There is no working code path from any obscura tool
to the loopback fixtures, so **no stage artifact could be produced**, and S3
(platform detection) has no S1/S2 snapshots to compare. I did **not** hand-drive
the engine via Bash/curl to fabricate artifacts — that would bypass the MCP
under test and violate the fairness contract. The blanket failure is the finding.

## Tool surface exposed by this MCP

| Tool | Purpose | Result against fixtures |
|------|---------|--------------------------|
| `browse_page` | one-shot fetch (text/markdown/html/links/cookies/axtree/layout) | ❌ `Obscura CDP client is not connected` |
| `browse_interact` | click / type (one-shot) | ❌ same (no connected browser) |
| `browse_session` | create/goto/wait/extract/click/type | ❌ `CDP connection is not open` (`list` works — server alive) |
| `browse_scrape` | parallel **cloud** workers | ❌ `Network error: Access to private/internal IP address 127.0.0.1 is not allowed` |

Note: obscura exposes **no screenshot/PNG primitive** of any kind, so S8 could
not be satisfied even with a healthy engine.

## Two independent, fatal failure modes

### 1. CDP browser path — engine never binds port 9222
The wrapper spawns `obscura serve` and waits (`OBSCURA_STARTUP_TIMEOUT_MS`, 15s
default) for the CDP server, parsing stderr for the ws URL, then connects as a
CDP client. The engine **prints the success banner/log**
(`Obscura CDP server listening on ws://127.0.0.1:9222`, both `serve` and
`--verbose` modes) **but never actually opens the TCP socket** in this Linux
x86_64 container. Verified directly:

```
$ obscura serve        # banner claims ws://127.0.0.1:9222, process stays alive
$ ss -ltn | grep 9222  # → port 9222 never bound after 15s
$ obscura --verbose     # logs "INFO ... listening on ws://127.0.0.1:9222"
$ ss -ltn | grep 9222  # → port 9222 never bound after 8s
```

The binary itself is fine for this host (`ELF 64-bit ... x86-64`, runs, parses
args) — this is **not** the documented arm64/x86_64 packaging mismatch. The
engine simply logs a phantom listener and never serves. Consequently the
wrapper's CDP client times out / never connects, and every browser tool returns
`Obscura CDP client is not connected`.

### 2. Cloud scrape path — SSRF guard blocks loopback
`browse_scrape` routes through Obscura's cloud worker processes, which enforce
an SSRF guard rejecting private/internal IPs:
`Access to private/internal IP address 127.0.0.1 is not allowed`. The fixtures
are loopback-only, so this path is structurally unusable for this benchmark
regardless of the CDP engine state.

## Per-stage outcome

| Stage | Outcome | Reason |
|-------|---------|--------|
| S1 Extract (Greenhouse) | `stage_s1.FAILED` | CDP not connected; scrape blocks loopback |
| S2 Extract (Ashby SPA)  | `stage_s2.FAILED` | same |
| S3 Platform detection   | `stage_s3.FAILED` | no S1/S2 snapshots exist to compare |
| S4 Navigate to apply form | `stage_s4.FAILED` | CDP not connected |
| S5 Fill form            | `stage_s5.FAILED` | no connected browser to type into |
| S6 Upload resume        | `stage_s6.FAILED` | no connected browser; no upload primitive |
| S7 Source dropdown      | `stage_s7.FAILED` | no connected browser |
| S8 Screenshot           | `stage_s8.FAILED` | CDP not connected; no screenshot primitive exists |

## Tools actually invoked this session
- `mcp__obscura__browse_page` ×4 → all `CDP client is not connected`
- `mcp__obscura__browse_session` (`create` → CDP not open; `list` → "No active sessions", confirming the wrapper is alive)
- `mcp__obscura__browse_scrape` ×1 → loopback blocked
- `Bash` (read-only diagnosis: `ps`, `ss`, `file`, direct `obscura serve`/`--verbose` launch to confirm the port-never-binds root cause), `Read`, `Write`

## Caveats / fairness notes
- Gave the engine a >25s cold-start grace window across retries; behavior was
  stable, not transient.
- The standalone `obscura serve` launches I ran were **diagnostic only** and
  were `pkill`ed afterward; they were not used to produce any stage artifact,
  and they do not name-match the wrapper process so they could not perturb it.
- Classified every stage as `.FAILED` (runtime failure) rather than `.NA`
  (capability absent): obscura *has* the tool surface for navigate/extract/
  click/type — it just cannot connect to its own engine here. The lone genuine
  capability gap is the missing screenshot primitive (noted under S8).
