# Phase 2: Per-MCP Scoring Runs - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Mode:** Smart discuss (infrastructure phase — mechanical execution of the Phase-1 harness across 6 more MCPs, with explicit decisions on per-MCP exception handling)

<domain>
## Phase Boundary

Drive the locked Phase-1 harness against the 6 non-Playwright MCPs (browser-use, chrome-devtools, lightpanda, obscura, firecrawl, cloakbrowser), producing a complete evidence directory + populated `scores.json` row for each. Playwright's row already exists from plan 01-07's calibration (composite 7.93, in re-baseline band [7.83, 8.83]). Phase 2 closes the matrix from 1/7 to 7/7.

Each MCP's run consists of: harness spawn → median-of-3 attempts of S1-S8 → aggregation → capability tag + failure-attribution tags. SKIPPED.md per partial-run pattern for any MCP that cannot complete (Firecrawl-without-key, Obscura install gap, browser-use init timeout, etc.).

</domain>

<decisions>
## Implementation Decisions

### Execution Order
- **Sequential**, not parallel, for the first pass — each MCP is a load-bearing real run, and parallel runs risk per-MCP setup interference (browser binary downloads, shared port 8765, orphan-process clashes).
- Order: `chrome-devtools` → `lightpanda` → `firecrawl` → `obscura` → `browser-use` → `cloakbrowser`. Rationale: low-risk MCPs first (chrome-devtools is a Google-shipped reference implementation; lightpanda is read-only so failure mode is well-bounded; firecrawl is cloud so no local-binary risk), trickier MCPs after the harness shows it generalizes (obscura install gap, browser-use init timeout, cloakbrowser sandbox-only).
- One Linear sub-ticket per MCP (G-715..G-720; G-721 is synthesis). Update each as work progresses via `linearis comments create G-XXX --body "..."`.

### browser-use Dual Mode
- Two rows: `browser-use-direct` (no LLM key — `--mcp` mode without OPENAI/ANTHROPIC keys set) and `browser-use-agent` (LLM key enabled). Each is its own evidence directory: `results/<DATE>/browser-use-direct/` and `results/<DATE>/browser-use-agent/`.
- If the 2026-05-21 testbench's `initialize` timeout is still present in v0.12.7: file a Linear bug ticket against vendor, score the row as `0/15 — tool-bug` with footnote, do NOT retry indefinitely. Per HANDOFF-GSD-AUTO STOP #2.

### N/A Semantics (read-only MCPs)
- `lightpanda` and `firecrawl` are read-only — they cannot interact with forms. S4-S8 (form discovery, fill, upload, submit, screenshot) score **N/A**, not 0. `scripts/score_with_na.py` drops N/A cells from the weighted denominator; composite reflects only attempted dimensions (S1-S3 typically).
- The matrix row carries the capability tag `js-light` (lightpanda) or `cloud` (firecrawl) to make the asymmetry explicit.

### Capability Tags
- `tool-only` — playwright, chrome-devtools (raw browser-automation tooling, no built-in LLM)
- `LLM-augmented` — browser-use-agent (uses LLM in-tool for action planning)
- `stealth-specialist` — cloakbrowser, obscura (anti-detection focus)
- `cloud` — firecrawl (remote service, no local browser)
- `js-light` — lightpanda (JS-light or JS-blind, depending on what 2026-05 nightly does on Ashby)

Tags are written into `scores.json` per row; visible in the matrix.

### Failure-Attribution Tags
- Any sub-rubric cell < 5 gets a tag from the taxonomy in `bench/failure_taxonomy.py`: `tool-bug` / `env-mismatch` / `target-flag` / `transient`.
- Enforcement: `scripts/aggregate_scores.py` validates every row at emit time. Missing tag on a sub-5 cell = aggregation error, not silently shipped.

### cloakbrowser Sandbox-Only Enforcement
- `bench/cloakbrowser_guard.py` (built in plan 01-02) already raises `HostnameNotAllowedError` for any non-loopback target.
- The harness MUST refuse to spawn cloakbrowser against anything other than 127.0.0.1. Verified per-run: `grep -r "[^127.0.0.1]" results/<DATE>/cloakbrowser/transcript.md` must return no non-trivial matches.
- Document in `results/<DATE>/cloakbrowser/SANDBOX_PROOF.md`.

### Median-of-3 Retry Gate
- `bench/transient.py` (3-pass-of-3) runs per stage. Median pass-count = score. Published as `n/3 passes` per cell in the matrix.
- For per-MCP runs in Phase 2, each MCP gets 3 full harness runs (median over runs, not just per-stage). This is expensive but is the FAIRNESS-01 contract.
- **Pragmatic concession:** if 3 full runs is prohibitively slow (>2 hours per MCP), document and surface. The autonomous mode can fall back to 1-pass per MCP with a published caveat in `recommendations.md` — but only with user approval. Start with 3-pass and adjust if needed.

### SKIPPED.md Pattern
For any MCP that cannot complete its harness run, write `results/<DATE>/<mcp>/SKIPPED.md`:
- `reason`: short tag (`INIT_TIMEOUT`, `INSTALL_FAILED`, `API_KEY_ABSENT`, `BINARY_MISSING`)
- `attempted_command`: the exact command that was run
- `error_excerpt`: relevant stderr/stdout
- `linear_ticket`: the per-MCP sub-ticket where this is being tracked
- `partial_evidence_path`: pointer to whatever evidence was captured before the failure

The aggregator treats a SKIPPED row as N/A composite, not 0.

### Known Per-MCP Risks (from research/PITFALLS.md + HANDOFF-GSD-AUTO STOP conditions)
- `browser-use v0.12.7` may have lingering `initialize` timeout — STOP condition #2.
- `obscura` engine install may fail on macOS arm64 — run `obscura-mcp install` early; if it fails, SKIPPED.md per partial-run, continue. STOP condition #3.
- `cloakbrowser` is sandbox-only; closed-source binary that touches cookies — only against 127.0.0.1 loopback. Hard rule.
- `firecrawl` requires `FIRECRAWL_API_KEY` env var; if absent, SKIPPED.md with `reason: API_KEY_ABSENT`. (User confirmed key is set via rbw — should be available.)
- `lightpanda` is React-blind; expect 0-byte response on Ashby (this IS the empirical finding). Score S2 as PARTIAL or FAIL with attribution, NOT as a harness bug.

### Claude's Discretion
- File-naming for two browser-use rows: `browser-use-direct` vs `browser-use-agent` (underscore-separated; matches the rest of the per-MCP dir convention).
- Whether to capture browser-use-agent runs at all if no LLM key is locally available (the harness allows BYO key via env; if user's env doesn't have one, SKIPPED.md for the agent row, complete row for direct mode).
- Time-budget per MCP: target 15-30 minutes per MCP for the full 3-pass median harness; if any MCP exceeds 60 minutes per pass (slow installs, hung sessions), surface for user decision.
- Whether to use worktree isolation for parallel runs in a second pass (NOT first pass — keep sequential for now).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (all built in Phase 1)
- **`scripts/run_mcp_session.sh <mcp>`** — the per-MCP harness driver. Spawns Claude Code session, drives through S1-S8, writes complete evidence directory.
- **`scripts/aggregate_scores.py`** — walks `results/<DATE>/<mcp>/`, emits `scores.json` in score.py shape.
- **`scripts/score_with_na.py`** — N/A-aware composite wrapper.
- **`scripts/verify_calibration.sh`** — the calibration gate (Playwright-specific). Not reused per-MCP, but its structure is the model for per-MCP gates.
- **`bench/transient.py`** — 3-pass-of-3 retry gate.
- **`bench/failure_taxonomy.py`** — transient classifier + 4-tag failure attribution.
- **`bench/orphan_audit.py`** — pre/post-run process diff.
- **`bench/cloakbrowser_guard.py`** — assert_local_only() loopback guard.
- **`bench/tools_inventory.py`** — per-MCP tools/list probe with 6-category classification.
- **`bench/capture_versions.py`** — versions.json + versions.lock.md producer.
- **`bench/stub_writers.py`** — deferred-to-G-710 stubs (tls.json, cold_start.json, stability.log).
- **`prompts/stage_walk.md`** — locked S1-S8 task script.
- **`fixtures/snapshots/{greenhouse,ashby}_2026-05-22/`** — loopback-served snapshot fixtures.
- **`scripts/serve_fixtures.sh`** — fixture server start/stop/status.

### Established Patterns
- One Claude Code session per MCP via `claude --print --output-format stream-json --allowedTools "mcp__${MCP}__*,Read,Write,Bash"`.
- Self-contained evidence directories at `results/<DATE>/<mcp>/`.
- `.venv/bin/python` (Python 3.12) for all Python invocations; system python3 is 3.14.5 (broken).
- `G-703:` commit prefix; pre-commit hook blocks inline secrets in .mcp.json.
- Sacrosanct `scoring/score.py` (extensions via `scripts/aggregate_scores.py` + `scripts/score_with_na.py`).

### Integration Points
- Each Phase-2 run produces `results/<DATE>/<mcp>/` — Phase 4 synthesis consumes these.
- Failure-attribution tags + capability tags written into per-row metadata in `scores.json` — consumed by Phase 4's matrix builder.
- Linear sub-tickets G-715..G-720 (one per MCP) + G-721 (synthesis) — comment-update as work progresses.

</code_context>

<specifics>
## Specific Ideas

- **browser-use direct mode** is the one Vitalik specifically wants validated (claim: "works without user's own LLM API key"). Capture explicit evidence — the harness should run with `unset OPENAI_API_KEY ANTHROPIC_API_KEY` before spawning for the direct-mode row.
- **chrome-devtools** is the most likely "interesting angle" win — it has tools (network waterfall, performance trace, console with source-mapped stacks) no other MCP can produce. The harness should add a 9th stage "DevTools Probe" producing `network.json`, `trace.json`, `console.json` for chrome-devtools only. This is OUT OF SCOPE for the base S1-S8 score but should be captured as bonus evidence.
- **lightpanda S2 (Ashby)** is the falsifiable test: 2026-03 said "React-blind, 0 bytes on Ashby." Re-run on 2026-05 nightly captures the truth. Whatever the answer, document it explicitly in the row's "Deep Analysis" note.
- **cloakbrowser** evidence in `results/<DATE>/cloakbrowser/SANDBOX_PROOF.md`: grep transcript + raw_stream for any non-127.0.0.1 hostname; if found, the run is invalid and the user MUST be surfaced (sandbox-only contract broken).
- **Use 3-pass median for the first MCP (chrome-devtools).** If wall-clock per MCP exceeds 60 minutes, surface and ask the user about dropping to 1-pass for the remaining 5 MCPs.

</specifics>

<deferred>
## Deferred Ideas

- Per-MCP cold-start (3-segment), 1hr stability, real token-efficiency measurements → Phase 3 (Cross-Cutting Measurements).
- TLS fingerprint capture per MCP → G-710.
- Bot-detection adversary testing per MCP → G-710.
- Cross-machine MacBook reproduction → G-710.
- Vendor courtesy disclosure window → G-710 (no longer in this wave per 2026-05-22 scope cut).
- Stage 2 terminal-craft packaging → blocked on Phase 4 recommendations.md.
- chrome-devtools' 9th "DevTools Probe" stage is a STRETCH — only do it if the base S1-S8 run completes cleanly and there's budget left. NOT a phase blocker.

</deferred>
