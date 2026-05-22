---
phase: 1
plan: 06
type: execute
wave: 3
depends_on:
  - 01-04   # extends scripts/run_mcp_session.sh to emit all evidence files
  - 01-05   # uses the aggregator output shape
files_modified:
  - scripts/run_mcp_session.sh   # MODIFIED: wire stub-writer invocations + tools_inventory + tokens.json passthrough
  - bench/stub_writers.py
  - bench/capture_versions.py
  - bench/tools_inventory.py
  - tests/test_stub_writers.py
  - tests/test_capture_versions.py
  - results/.gitkeep
requirements:
  - HARNESS-02
  - SAFETY-03
success_criteria_advanced: [2]
status: planned
autonomous: true
estimate_hours: 2

must_haves:
  truths:
    - "After `make bench-playwright`, the evidence directory `results/<date>/playwright/` contains ALL of: transcript.md, raw_stream.jsonl, stage_s{1..8}.{yml,md,png,txt,NA,FAILED}, cold_start.json, tokens.json, tls.json, stability.log, orphan_audit.log, tools_inventory.json — even when the underlying measurement is deferred (stub files explicitly tagged `{\"deferred\": \"G-710\"}`)."
    - "`bench/capture_versions.py` writes `results/<date>/versions.json` from the LIVE environment (npm versions, uv versions, binary SHA256s, OS info, Claude Code version, Node version, Python version)."
    - "A human-readable `results/<date>/versions.lock.md` companion is produced from versions.json."
    - "`tools_inventory.json` per MCP contains the tool count + 6-category breakdown (extracted by spawning the MCP via `mcp.client.stdio` and calling `tools/list` — this is real work, not a stub)."
    - "SAFETY-03 stub `tls.json` is emitted as `{\"deferred\": \"G-710\", \"reason\": \"TLS fingerprint capture cut from v1 per 2026-05-22 scope cut\"}` so the evidence shape is locked."
  artifacts:
    - path: "bench/stub_writers.py"
      provides: "write_cold_start_stub(out_dir), write_tls_stub(out_dir), write_stability_stub(out_dir) — emit deferred-marker JSON / logs in the canonical shape"
    - path: "bench/capture_versions.py"
      provides: "CLI: write versions.json + versions.lock.md from live env; SHA256 each MCP binary; capture Claude Code, Node, Python, uv versions"
    - path: "bench/tools_inventory.py"
      provides: "Real work — spawns each MCP via mcp.client.stdio, calls tools/list, categorizes tools into 6 categories per chrome-devtools-mcp's scheme; writes tools_inventory.json"
  key_links:
    - from: "scripts/run_mcp_session.sh"
      to: "bench/stub_writers.py + bench/tools_inventory.py + bench/capture_versions.py"
      via: "post-session invocations that populate the missing evidence files"
      pattern: "(stub_writers|tools_inventory|capture_versions)"
    - from: "bench/capture_versions.py"
      to: "results/<date>/versions.json"
      via: "shasum -a 256 + npm view + uv tool list + claude --version"
      pattern: "(shasum|npm view|uv tool list|claude --version)"
---

## Goal

Lock the evidence-directory shape — every Phase 1 Playwright run produces a complete `results/<date>/playwright/` matching HARNESS-02's exact file list. Most files are real (transcript, raw_stream, stage artifacts, orphan_audit, tools_inventory, versions); the explicitly-deferred ones (tls, cold_start beyond a trivial first-call number, stability) are STUB FILES with a `{"deferred": "G-710"}` marker so Phase 2's add-the-other-6-MCPs work can rely on the directory contract.

Per CONTEXT.md: "Phase 1 still emits `tls.json` as a stub" + same for cold_start / stability (full versions land in Phase 3).

`bench/tools_inventory.py` is **real work**, not a stub — it spawns each MCP via the Python `mcp.client.stdio` SDK and captures the tool list. This is the cheapest cross-cutting measurement and is useful immediately.

## Files Modified

| File | New / Modified | Purpose |
|---|---|---|
| `bench/stub_writers.py` | NEW | Stub emitters for tls.json, cold_start.json (stub variant), stability.log. Each writes the canonical JSON/log shape with `deferred: "G-710"` and the reason. |
| `bench/capture_versions.py` | NEW | Real work. Captures the full version manifest. |
| `bench/tools_inventory.py` | NEW | Real work. Spawns the MCP, calls `tools/list`, categorizes. |
| `tests/test_stub_writers.py` | NEW | Asserts each stub writer produces the canonical shape. |
| `tests/test_capture_versions.py` | NEW | Asserts capture_versions.py produces a versions.json with the required fields. |
| `scripts/run_mcp_session.sh` | MODIFIED | After the Claude session ends, invoke: `bench.tools_inventory` (if not already done), then `bench.stub_writers` to fill the deferred slots, then `bench.capture_versions` (once per run, not per-MCP — top-level invocation). |
| `results/.gitkeep` | NEW | Ensure the dir exists. |

## Tasks

1. **Write `bench/stub_writers.py`.**
   - Define `def write_tls_stub(out_dir: Path) -> None`:
     ```python
     (out_dir / "tls.json").write_text(json.dumps({
         "deferred": "G-710",
         "reason": "TLS fingerprint capture (JA3/JA4) cut from v1 per 2026-05-22 scope cut.",
         "see": "https://linear.app/abandoned-yachts/issue/G-710"
     }, indent=2))
     ```
   - Define `def write_cold_start_stub(out_dir: Path, mcp_name: str) -> None` — emits a stub matching the eventual shape (`{"t_resolve_ms": null, "t_spawn_ms": null, "t_first_useful_ms": null, "runs": 0, "deferred": "G-710 (full 3-segment cold/warm split)"}`). Even in Phase 1 we can populate a single coarse number from the run_mcp_session.sh start time, but per CONTEXT.md the full 3-segment work is Phase 3 / deferred to G-710 — so stub.
   - Define `def write_stability_stub(out_dir: Path) -> None` — emits `stability.log` containing a single line: `STUB — 60-min loop deferred to G-710 (full run lands Phase 3)`.
   - **verify:** `tests/test_stub_writers.py` (next task).

2. **Write `tests/test_stub_writers.py`.**
   - For each stub writer: invoke with a `tmp_path`, read back the produced file, assert it contains the `deferred: "G-710"` marker AND that it parses as valid JSON / readable text.
   - **verify:** `uv run python -m unittest tests.test_stub_writers` passes.

3. **Write `bench/tools_inventory.py`.**
   - CLI: `python -m bench.tools_inventory <mcp_name> --out <path>`.
   - Implementation:
     - Read `.mcp.json` to find the `command` + `args` for `<mcp_name>`.
     - Use `mcp.client.stdio.stdio_client` (Python SDK 1.16) to spawn the MCP, run `initialize`, then `tools/list`. Capture timeout = 30 s.
     - For each tool, categorize into one of 6 buckets following chrome-devtools-mcp's scheme:
       1. **navigation** — `navigate`, `goto`, `back`, `forward`, `reload`
       2. **inspection** — `snapshot`, `read`, `extract`, `tools/list`
       3. **interaction** — `click`, `type`, `fill`, `select`, `drag`, `hover`
       4. **capture** — `screenshot`, `record`, `pdf`
       5. **diagnostics** — `console`, `network`, `trace`, `performance`, `evaluate`
       6. **other** — anything that doesn't match the above
     - Output `tools_inventory.json`:
       ```json
       {
         "mcp": "playwright",
         "captured_at": "2026-05-22T14:33:58Z",
         "tool_count": 28,
         "categories": {"navigation": 4, "inspection": 6, "interaction": 8, "capture": 3, "diagnostics": 5, "other": 2},
         "tools": [{"name": "browser_navigate", "category": "navigation", "description_excerpt": "..."}, ...]
       }
       ```
   - **Handles failure:** if the MCP doesn't initialize within 30 s, emit `{"mcp": "<name>", "error": "initialize_timeout", "deferred": false}` and exit non-zero. The aggregator can read this to attribute the row as `tool-bug` per FAIRNESS-06.
   - **verify:** `uv run python -m bench.tools_inventory playwright --out /tmp/test_tools.json` produces a JSON with `tool_count >= 20` (RESEARCH §1 cites ~28 tools for Playwright MCP).

4. **Write `bench/capture_versions.py`.**
   - CLI: `python -m bench.capture_versions --date <YYYY-MM-DD> --results-root results/`.
   - Steps:
     - Run `claude --version` → capture full version string.
     - Run `node --version` and `npm --version`.
     - Run `python3 --version` and `uv --version`.
     - For each MCP in `.mcp.json`: locate the binary (`command -v <cmd>`), compute its SHA256 (`shasum -a 256 <path>`), and if it's an npm package run `npm view <pkg>@latest version` to record the latest version (for drift visibility). If uv tool, `uv tool list | grep <name>`.
     - Capture OS info: `sw_vers` on macOS (or `uname -a` cross-platform).
     - Capture lightpanda's binary self-report inconsistency (per RESEARCH §1: "binary self-identifies as 0.3.0 in some builds and 0.1.0 in the MCP JSON-RPC handshake"). Record both: `lightpanda --version` output AND the `tools_inventory.json`'s captured `protocolVersion` (or `serverInfo.version`) from the initialize handshake.
   - Output `results/<date>/versions.json`:
     ```json
     {
       "captured_at": "2026-05-22T14:33:58Z",
       "host": {"os": "Darwin", "version": "25.5.0", "arch": "arm64", "machine_name": "<redacted>"},
       "tooling": {"claude_code": "v2.1.81", "node": "v22.0.0", "npm": "10.0.0", "python": "3.12.0", "uv": "0.7.0"},
       "mcps": {
         "playwright": {"binary_path": "/opt/homebrew/bin/playwright-mcp", "sha256": "abc...", "package_version": "0.0.75", "latest_on_npm": "0.0.75"},
         "lightpanda": {"binary_path": "...", "sha256": "...", "binary_self_report": "0.3.0", "handshake_protocol_version": "0.1.0"},
         ...
       }
     }
     ```
   - Also emit `results/<date>/versions.lock.md` — human-readable companion:
     ```markdown
     # Reproducibility Manifest — 2026-05-22

     ## Host
     - macOS Darwin 25.5.0 (arm64)
     ## Tooling
     - Claude Code v2.1.81 …

     ## MCPs (with binary SHA256)
     | MCP | Version | SHA256 |
     ...
     ```
   - **verify:** `tests/test_capture_versions.py` (next task).

5. **Write `tests/test_capture_versions.py`.**
   - Run `uv run python -m bench.capture_versions --date 2099-12-31 --results-root /tmp/version_test/`.
   - Assert: `/tmp/version_test/2099-12-31/versions.json` exists; parses as JSON; has `tooling`, `host`, `mcps` keys.
   - For at least one MCP we know is installed (Playwright per HANDOFF), assert `sha256` field is a 64-char lowercase hex string.
   - **verify:** `uv run python -m unittest tests.test_capture_versions` passes.

6. **Wire `scripts/run_mcp_session.sh` updates.**
   - After the Claude Code session ends (line in plan 01-04 where `wait $CLAUDE_PID` returns), insert:
     ```bash
     # Tools inventory (real)
     uv run python -m bench.tools_inventory "$MCP_NAME" --out "$OUT_DIR/tools_inventory.json" || \
       echo "tools_inventory: failed for $MCP_NAME — see error in file" >&2

     # Stubs (deferred to G-710)
     uv run python -c "from pathlib import Path; from bench.stub_writers import write_tls_stub, write_cold_start_stub, write_stability_stub; out=Path('$OUT_DIR'); write_tls_stub(out); write_cold_start_stub(out, '$MCP_NAME'); write_stability_stub(out)"

     # Version manifest (once per run; idempotent — runs only if versions.json absent for this DATE)
     test -f "results/$DATE/versions.json" || uv run python -m bench.capture_versions --date "$DATE" --results-root results/
     ```
   - Also ensure `tokens.json` is produced: `jq -s 'map(select(.type=="result").usage) | last // {}' "$OUT_DIR/raw_stream.jsonl" > "$OUT_DIR/tokens.json"`. (This is the `turn`-scope token count from the stream-json `usage` blocks. The 3-scope split [`schema`/`payload`/`turn`] is Phase 3; Phase 1 captures only `turn` and stubs the rest with `null`.)
   - Final cleanup: ensure all 11 required artifacts are present (per HARNESS-02 list). If any are missing, the script emits `MISSING: <file>` to stderr but continues — calibration plan 01-07 has an explicit gate that fails the run if any file is missing.
   - **verify:** Re-run `make bench-playwright`; `ls results/<date>/playwright/` shows ALL of: transcript.md, raw_stream.jsonl, stage_s*.{yml,md,png,txt,NA,FAILED}, cold_start.json, tokens.json, tls.json, stability.log, orphan_audit.log, tools_inventory.json.

## Acceptance

- After `make bench-playwright`, `results/<date>/playwright/` contains all 11 expected files (transcript, raw_stream, stage_s1..s8.*, cold_start.json, tokens.json, tls.json, stability.log, orphan_audit.log, tools_inventory.json) — verified by a one-liner: `for f in transcript.md raw_stream.jsonl cold_start.json tokens.json tls.json stability.log orphan_audit.log tools_inventory.json; do test -f "results/<date>/playwright/$f" || echo MISSING $f; done` produces no MISSING output. (Stage_s* artifacts vary by MCP per the rubric — at least 3 of S1-S8 must exist.)
- `tls.json` content is `{"deferred": "G-710", ...}` — the stub shape locks the directory contract.
- `tools_inventory.json` for Playwright shows `tool_count >= 20` and a 6-category breakdown.
- `results/<date>/versions.json` exists and `versions.lock.md` is its human-readable twin.
- Lightpanda's binary-vs-handshake version mismatch is recorded if lightpanda is installed (the harness gracefully no-ops the field if not).

## Dependencies

- **Plan 01-04:** `scripts/run_mcp_session.sh` exists and is callable.
- **Plan 01-05:** the evidence-directory contract is what `aggregate_scores.py` walks; this plan completes the contract.

## Notes / Pitfalls

- **Pitfall 10 (version drift):** `bench/capture_versions.py` is the defense. Per the gate at the bottom of Pitfall 10: mismatches between `versions.lock.md` and `versions.json` should fail the run. Phase 1 implements the capture; the strict gate (`fail-on-mismatch`) is appropriate for Phase 2+ where multiple researchers might be running and lockfile drift is more likely. Phase 1 logs the discrepancy.
- **Pitfall 9 (orphan accumulation):** `bench/tools_inventory.py` spawns a real MCP process. It MUST use `bench.process_group.spawn_setsid` and clean up via `kill_group` after `tools/list` returns. Reference: same pattern as `scripts/run_mcp_session.sh`.
- **CONTEXT.md decision honored:** "Phase 1 still emits `tls.json` as a **stub** (empty object with `{\"deferred\": \"G-710\"}` provenance) so the evidence-directory shape is locked for the follow-up wave." Exactly this.
- **CONTEXT.md decision honored:** "`bench/capture_versions.py` writes `versions.json` from live environment (npm + uv tool versions, per-MCP binary SHA256s, OS, Claude Code version, Node version, Python version)." Exactly this.
- **SAFETY-03 stub:** The literal text of SAFETY-03 mentions "echo-server fixture + `tests/stealth_leak_test.py`" — those are deferred to G-710 per CONTEXT.md Deferred Ideas ("Echo-server header diff test ... → G-710"). What this plan delivers for SAFETY-03 is the stub mechanism + a TODO record in `tls.json`'s `reason` field pointing at G-710 so the requirement is acknowledged with a clear hand-off, not silently dropped.

## Out of Scope

- Real cold-start measurement (3-segment, cold+warm, median of 5) — Phase 3 (MEAS-01).
- Real 1hr stability loop against the snapshot fixtures — Phase 3 (MEAS-07).
- Real TLS-fingerprint capture — deferred to G-710.
- Real Sec-CH-UA-Platform leak echo-server test — deferred to G-710.
- The 3-scope token split (`schema` / `payload` / `turn`) — Phase 3 (MEAS-02); Phase 1 captures only `turn` from stream-json usage blocks.
- Per-stage tool-call counts — Phase 3 (MEAS-08).
- Strict `versions.lock.md`-vs-`versions.json` fail-on-mismatch gate — Phase 4 (REPRO-01); Phase 1 logs but does not fail.
- `MACHINE.md` per `results/<date>/` — Phase 4 (REPRO-03); Phase 1's `versions.lock.md` covers a subset of the same data.
