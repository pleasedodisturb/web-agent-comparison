# Phase 3: Cross-Cutting Measurements - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning
**Mode:** Smart discuss (infrastructure phase — partially pre-baked from Phase 2; the load-bearing decisions are about wall-clock budget for stability + cold-start)

<domain>
## Phase Boundary

Capture the 5 cross-cutting measurement artifacts per MCP that the rubric needs but Phase 2's S1-S8 walk doesn't naturally produce: cold-start latency (3-segment), token efficiency (3-scope), 1hr stability, per-stage tool-call counts, tool-surface inventory.

The work is **mostly aggregation of existing Phase-2 raw_stream.jsonl + tools_inventory.json** plus two genuinely new measurements (cold-start timing and stability runs). Where Phase 2 evidence already supports a measurement, recover it; don't re-run the harness for data we already have.

</domain>

<decisions>
## Implementation Decisions

### Reuse vs Re-Measure
Three of five MEAS- requirements can be satisfied from existing Phase 2 evidence:
- **MEAS-02 (tokens, payload scope)** — parse existing `results/2026-05-26/<mcp>/PASS{1,2,3}/raw_stream.jsonl`; sum JSON-RPC payload bytes per stage.
- **MEAS-08 (per-stage tool-call counts)** — count tool-use events in the same raw_stream.jsonl.
- **MEAS-09 (tools_inventory)** — already captured by `bench/tools_inventory.py` in Phase 2; aggregate into the per-MCP `tools_inventory.json` (or copy if already there) + emit a roll-up summary.

Two require fresh runs:
- **MEAS-01 (cold-start, 3-segment, ≥5 runs cold + ≥5 warm)** — needs new Python `mcp.client.stdio` invocations with timing instrumentation. ~10-15s per spawn × 5 cold + 5 warm × 7 MCPs ≈ **~15-25 minutes wall-clock** total. Cheap; do strictly.
- **MEAS-07 (1hr stability per MCP)** — 60 min × 7 = 7 hours sequential. **This is the load-bearing wall-clock decision.**

### Stability Wall-Clock Decision
The rubric says "60min S1+S5 loop". Strict reading: each MCP runs for 60 minutes against the snapshot fixture server, looping S1+S5, with per-tool-call 30s timeout and `ulimit -v` ceiling, post-run orphan_audit showing 0 survivors.

Pragmatic options:
- **(a) Strict 60min × 7 sequentially** — 7 hours wall-clock. Defensible but expensive.
- **(b) Strict 60min × 7 with overnight parallelism** — risk of port-8765 conflicts, orphan-process clashes, shared-resource contention. The Phase 2 sequential-execution decision was made specifically to avoid this.
- **(c) Reduced 30min × 7** — 3.5 hours; published with caveat in `recommendations.md`. Strict-vs-published gap small enough that an attentive reader can adjust.
- **(d) Reduced 15min × 7 (smoke stability)** — 1.75 hours; meaningfully weaker. The "MCP didn't crash in 15 minutes" signal is much weaker than "didn't crash in 60."
- **(e) Selective: 60min for the top-3 + 30min for the rest** — pragmatic compromise; the published recommendations turn on the top-3 anyway.

**Phase 3 default: option (a) strict 60min × 7 sequentially**, with a fallback to (e) if any single MCP exceeds 2× expected duration (indicating a hang). The autonomous executor should surface a checkpoint if it estimates >8 hours wall-clock total, asking the user whether to fall back to (c) or (e).

### Cold-Start 3-Segment Split
- `t_resolve` = process spawn → first byte of stdout
- `t_spawn` = first byte of stdout → MCP server ready to accept `initialize`
- `t_first_useful` = `initialize` sent → first `tools/list` response received

Implement via `bench/measure_cold_start.py` (new). Use `mcp.client.stdio` (Python SDK 1.16) for the JSON-RPC handshake; use `time.perf_counter_ns()` between segments. Cold = first run after `pkill -f <mcp>` + filesystem cache eviction (where applicable); warm = immediately-following second run.

Cache-eviction strategy on macOS: `sudo purge` evicts page cache but requires sudo. Skip if not available; document the limitation. Most MCPs are Node/Python binaries already in OS file cache after first run; the "cold" timing approximates "first-spawn-of-shell-session" rather than "uncached-filesystem."

Median of ≥5 published; record all individual samples in `cold_start.json` for transparency.

### Token Efficiency 3-Scope Split
- `schema` — token count of the MCP's `tools/list` response, computed via Anthropic SDK `count_tokens` (free). Static per MCP.
- `payload` — sum of JSON-RPC request/response bytes, parsed from raw_stream.jsonl. Per-stage, per-pass.
- `turn` — `usage` blocks in stream-json; per-stage Claude billing cost. Per-stage, per-pass.

Published headline column = `payload`. The other two captured for analysis. Schema is static (per MCP, doesn't vary by stage); the headline matrix can include it as a per-row "context cost" annotation.

`bench/measure_tokens.py` (new) reads raw_stream.jsonl + calls count_tokens on tools_inventory.json. Writes per-MCP `tokens.json` overwriting the Phase-1 stub (`{"deferred": "..."}`).

### Per-Stage Tool-Call Counts
- Count `tool_use` events per stage in raw_stream.jsonl
- Special interest: S5 fill-form — Playwright's `browser_fill_form` claim is "N fields in 1 call vs N calls." This grounds the claim empirically.
- Write to `tool_call_counts.json` per MCP; aggregate into Phase 4's matrix.

### Tools-Surface Inventory
Already captured per MCP in Phase 2 (via `bench/tools_inventory.py`). Phase 3 just confirms the file exists for all 7 and emits a roll-up `TOOLS_INVENTORY_SUMMARY.md` showing the 6-category breakdown side-by-side.

### Aggregation Output
- `results/2026-05-26/<mcp>/cold_start.json` — overwrites Phase 1 stub
- `results/2026-05-26/<mcp>/tokens.json` — overwrites Phase 1 stub
- `results/2026-05-26/<mcp>/stability.log` — overwrites Phase 1 stub (or .gz if very large)
- `results/2026-05-26/<mcp>/tool_call_counts.json` — new
- `results/2026-05-26/<mcp>/tools_inventory.json` — already exists
- `results/2026-05-26/CROSS_CUT_SUMMARY.md` — roll-up consumed by Phase 4

### Claude's Discretion
- Implementation language: Python (matches Phase 1 utilities; uses mcp.client.stdio).
- Whether to add stability runs as a new Make target (`make stability-<mcp>`) or just a script. Make target is cleaner; the user can re-run individually.
- Whether to commit the 60min×7 stability.log files (can be ~10MB total). Compress via `gzip` if needed; commit the compressed form.
- Whether to also re-compute tokens.json against PASS3 specifically (the highest-discovery pass for chrome-devtools/obscura) vs median across passes. Default to median.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (all built in Phase 1)
- **`bench/tools_inventory.py`** — already does `mcp.client.stdio` initialize + tools/list. Extend with timing instrumentation for cold_start measurement.
- **`scripts/run_mcp_session.sh`** — produces raw_stream.jsonl already.
- **`scripts/serve_fixtures.sh`** — loopback fixture server.
- **`bench/orphan_audit.py`** — pre/post-run process diff for stability runs.
- **`bench/stub_writers.py`** — currently writes `{"deferred": "G-710"}` stubs; Phase 3 overwrites with real values.
- **`prompts/stage_walk.md`** — for stability loop, just S1+S5 stages (subset).
- **`bench/cloakbrowser_guard.py`** — loopback enforcement (cloakbrowser stability run must be loopback-only).

### Phase 2 Evidence to Mine
- `results/2026-05-26/<mcp>/PASS{1,2,3}/raw_stream.jsonl` — token + tool-call source data for all 7 MCPs (8 if counting browser-use dual).
- `results/2026-05-26/<mcp>/tools_inventory.json` — per-MCP tool surface, already captured.
- `results/2026-05-26/<mcp>/SKIPPED.md` (for browser-use-agent) — handle by writing N/A cross-cuts for that row.

### Integration Points
- Phase 4 synthesis consumes cross_cut artifacts to populate the 8-dim matrix's Speed (cold-start) and Token Efficiency dimensions with real numbers instead of neutral 5.
- The 4 deferred dimensions from Phase 1 calibration (Speed, Token Efficiency, Setup Complexity, Error Handling) get real values here. Setup Complexity + Error Handling remain heuristic for this wave; only Speed + Token Efficiency get true measurements.

</code_context>

<specifics>
## Specific Ideas

- **Stability loop content:** S1 (Greenhouse markdown extraction) + S5 (form fill — using a fresh tab per iteration so prior state doesn't accumulate). 30-second sleep between iterations. Per-tool-call 30s timeout. Loop for 60 min wall-clock. Post-run: orphan_audit + final memory snapshot via `ps`.
- **Cold-start cache eviction:** Use `pkill -f <binary-name>` between cold runs; skip `sudo purge` (don't require sudo). Document the limitation in `cold_start.json` metadata: `"cache_eviction": "process_only"`.
- **Token measurement methodology disclosure:** the `count_tokens` schema scope uses Anthropic's tokenizer. Note in the Phase 4 synthesis that "schema" is Anthropic-tokenizer-counted while "payload" is byte-count (proxy for token cost). Don't conflate the two units.
- **Cloakbrowser stability:** loopback-only. Same SC #5 contract as Phase 2.
- **browser-use stability:** run only the direct mode (agent mode is SKIPPED). Note the asymmetry in CROSS_CUT_SUMMARY.md.
- **For firecrawl:** stability against loopback is meaningless (it can't reach loopback). Skip stability run with `SKIPPED.md` rationale; cold-start measurement IS still valid (process spawn timing doesn't require network reach).

</specifics>

<deferred>
## Deferred Ideas

- TLS fingerprint per MCP (JA3/JA4) → G-710.
- Bot-detection adversary testing → G-710.
- Cross-machine MacBook reproduction → G-710.
- chrome-devtools "9th DevTools-Probe stage" capturing network waterfall/perf trace/console — could land in Phase 3 as a stretch, but per Phase 2 02-01 SUMMARY, it's deferred. Skip.
- Memory-pressure benchmarking under N-tab load (obscura's 30MB/tab claim) → could be a Phase 3 stretch but only if stability runs leave wall-clock budget.
- True "uncached-filesystem" cold-start measurement → requires `sudo purge`; deferred.

</deferred>
