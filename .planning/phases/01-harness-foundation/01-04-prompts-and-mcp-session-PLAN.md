---
phase: 1
plan: 04
type: execute
wave: 2
depends_on:
  - 01-01   # uses Makefile + uv/npm envs + check_prereqs
  - 01-03   # boots serve_fixtures.sh start before driving the MCP
files_modified:
  - prompts/stage_walk.md
  - scripts/run_mcp_session.sh
  - bench/process_group.py
  - bench/orphan_audit.py
  - bench/timeout_watchdog.py   # NEW — per-tool-call 30s timeout enforcement (Claude Code does not enforce; upstream #35287)
  - tests/test_orphan_audit.py
  - tests/test_timeout_watchdog.py
  - tests/test_run_mcp_session_smoke.sh
  - Makefile   # MODIFIED (wires bench-<mcp> to scripts/run_mcp_session.sh + fixtures-serve dep)
requirements:
  - HARNESS-01
  - HARNESS-03
  - HARNESS-04
  - HARNESS-07
  - HARNESS-08
  - HARNESS-09
  - FAIRNESS-07
success_criteria_advanced: [1, 2]
status: planned
autonomous: true
estimate_hours: 4

must_haves:
  truths:
    - "Running `make bench-playwright` spawns a Claude Code session restricted to mcp__playwright__* + Read/Write/Bash via --allowedTools (no WebFetch fallback)."
    - "The session is driven by `prompts/stage_walk.md` walking S1-S8 against the loopback snapshot server."
    - "All MCP child processes are spawned under setsid (process-group leader); pre/post-run `ps` audit kills any orphan in the group; `orphan_audit.log` records 0 survivors on a clean run."
    - "Each tool call has a 30s harness-enforced timeout; exceeding it tags the call TIMEOUT in raw_stream.jsonl and the stage falls through to retry."
    - "`ulimit -v 4194304` (4 GB) is set before the Claude Code spawn; an OOM in the MCP child kills the MCP, not the Mac Mini."
    - "If Claude tries to reach for a non-allow-listed tool (WebFetch, a different MCP, etc.), the session fails fast and the harness records `tool-bug` or `env-mismatch` per FAIRNESS-07."
  artifacts:
    - path: "prompts/stage_walk.md"
      provides: "Locked S1-S8 task script; same prompt drives every MCP; parameterized by ${MCP} + ${SNAPSHOT_BASE_URL}"
    - path: "scripts/run_mcp_session.sh"
      provides: "Per-MCP driver: setsid + ulimit + timeout + claude --print --output-format stream-json + orphan_audit"
    - path: "bench/process_group.py"
      provides: "Python helper: spawn under setsid, return PGID, send SIGTERM+SIGKILL on cleanup, return ps diff"
    - path: "bench/orphan_audit.py"
      provides: "CLI: pre/post ps snapshot diff filtered by PGID + MCP-related cmdline patterns; writes orphan_audit.log; exits 1 if survivors found"
  key_links:
    - from: "scripts/run_mcp_session.sh"
      to: ".mcp.json"
      via: "jq -r .mcpServers"
      pattern: "jq.*mcpServers"
    - from: "scripts/run_mcp_session.sh"
      to: "claude --print"
      via: "--allowedTools mcp__${MCP}__*,Read,Write,Bash + --append-system-prompt prompts/stage_walk.md"
      pattern: "claude.*--allowedTools.*mcp__"
    - from: "scripts/run_mcp_session.sh"
      to: "bench/orphan_audit.py"
      via: "pre-run + post-run audit; failure → exit 1"
      pattern: "orphan_audit"
---

## Goal

Build the per-MCP driver. This is the load-bearing artifact for everything else: it owns process lifecycle (setsid + orphan_audit + ulimit + timeout), it owns prompt delivery (the locked S1-S8 stage_walk), and it owns the no-WebFetch-fallback contract via `--allowedTools`. Successfully driving Playwright end-to-end on the snapshot fixtures is the precondition for the Phase 1 calibration gate (plan 01-07).

## Files Modified

| File | New / Modified | Purpose |
|---|---|---|
| `prompts/stage_walk.md` | NEW | The S1-S8 task script. Templated with `${MCP}` and `${SNAPSHOT_BASE_URL}` placeholders the wrapper substitutes via `envsubst`. |
| `scripts/run_mcp_session.sh` | NEW | The per-MCP driver. ~150 lines of Bash. |
| `bench/process_group.py` | NEW | Python module: subprocess.Popen + `start_new_session=True`, pgid capture, term/kill helpers. |
| `bench/orphan_audit.py` | NEW | Python CLI: pre/post ps snapshot, diff, kill survivors. |
| `tests/test_orphan_audit.py` | NEW | unittest: spawn a sleep, audit, kill, verify clean. |
| `tests/test_run_mcp_session_smoke.sh` | NEW | Smoke test against Playwright only — runs against a tiny "say hello" prompt, asserts evidence dir exists with required files. |
| `Makefile` | MODIFIED | Replace the stub `bench-%` with a real recipe that calls `scripts/run_mcp_session.sh $*`. Add `fixtures-serve` as a dependency. |

## Tasks

1. **Write `prompts/stage_walk.md`.**
   - Header explains the variables: `${MCP}`, `${SNAPSHOT_BASE_URL}` (e.g. `http://127.0.0.1:8765`), `${OUT_DIR}` (the evidence directory).
   - Sections, one per stage, mirroring the 2026-03 rubric and stages (per `scoring/rubric.md` + `results/2026-03-31_run.md`):
     - **S1 — Extract job data (Greenhouse).** Target: `${SNAPSHOT_BASE_URL}/greenhouse_2026-05-22/`. Use ONLY `mcp__${MCP}__*` tools. Save the extracted data as `${OUT_DIR}/stage_s1.yml` (or `.md` / `.txt` depending on what the MCP natively produces — Claude picks the most natural extension; the harness accepts any of `.yml/.md/.txt/.json`).
     - **S2 — Extract job data (Ashby SPA).** Target: `${SNAPSHOT_BASE_URL}/ashby_2026-05-22/`. Save as `${OUT_DIR}/stage_s2.{yml,md,txt}`.
     - **S3 — Platform detection.** From the snapshots, identify whether each target is Greenhouse vs Ashby. Save reasoning as `${OUT_DIR}/stage_s3.md`.
     - **S4 — Navigate to apply form.** Greenhouse target. Save resulting page as `${OUT_DIR}/stage_s4.{yml,md}`. Read-only MCPs (lightpanda, firecrawl) should emit `${OUT_DIR}/stage_s4.NA` instead and stop here.
     - **S5 — Fill application form.** Use `fixtures/mock_data.json` (Jane Testworth). Fill: first_name, last_name, email, phone, linkedin, github. Save `${OUT_DIR}/stage_s5.{yml,md}` showing the filled state.
     - **S6 — Upload resume.** Use `fixtures/mock_resume.pdf`. Save `${OUT_DIR}/stage_s6.md` documenting how the upload was performed and confirming success.
     - **S7 — Handle source dropdown.** "Job board" value from mock_data. Use Claude's judgment for the technique (`browser_select_option` vs typing-and-Enter for React Select per the prior wave's lesson). Save `${OUT_DIR}/stage_s7.md`.
     - **S8 — Screenshot of filled form.** Save as `${OUT_DIR}/stage_s8.png`.
   - Footer block: "STOP. Write a brief `${OUT_DIR}/transcript.md` summarizing what tools you used per stage and any failure modes. Do NOT call any non-mcp__${MCP}__ tools except Read, Write, Bash. Do NOT reach for WebFetch. If a stage cannot be completed with the MCP under test, write `${OUT_DIR}/stage_sN.FAILED` with a one-line reason."
   - **verify:** File exists; `grep -c '^## S[1-8]' prompts/stage_walk.md` returns 8 (one heading per stage).

2. **Write `bench/process_group.py`.**
   - Define `spawn_setsid(argv: list[str], env: dict, cwd: str | None = None) -> subprocess.Popen`: calls `subprocess.Popen(argv, start_new_session=True, env=env, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)`. `start_new_session=True` is the cross-platform `setsid` equivalent (sets the process as session leader, becomes the process-group leader).
   - Define `kill_group(pgid: int, grace_s: float = 5.0) -> None`: `os.killpg(pgid, signal.SIGTERM)`, sleep `grace_s`, `os.killpg(pgid, signal.SIGKILL)` (ignore ProcessLookupError on the second call).
   - Define `pgid_of(pid: int) -> int`: `os.getpgid(pid)`.
   - Define `snapshot_ps() -> list[dict]`: shells out to `ps -axo pid,ppid,pgid,rss,command` and returns parsed rows.
   - **verify:** Importable; `python -c "from bench.process_group import spawn_setsid, kill_group, snapshot_ps; print('ok')"` prints `ok`.

3. **Write `bench/orphan_audit.py`.**
   - CLI: `python -m bench.orphan_audit --before-snapshot <path> --after-snapshot <path> --pgid <int> --log <path>`.
   - Logic: load before + after `ps` snapshots, compute the set of PIDs in `after - before` filtered by `pgid == <given-pgid>` OR by cmdline matching MCP regex (`chromium|playwright|obscura|cloak|firecrawl|lightpanda|browser-use|chrome-devtools-mcp`).
   - For each survivor: `kill -9 <pid>` and log `KILLED pid=<pid> cmd=<cmdline>` to the log file. Exit code: 0 if survivors == 0; 1 otherwise (so the harness can flag the run as "harness leaked, not MCP unstable" per Pitfall 9).
   - Also support a `--snapshot-only <path>` mode that just dumps the current `ps` to a file for the pre-run capture.
   - **verify:** `tests/test_orphan_audit.py` (next task).

4. **Write `tests/test_orphan_audit.py`.**
   - Test: spawn `sleep 30` via `bench.process_group.spawn_setsid`; take a before-snapshot; then a separate `sleep 30` from the same shell (to simulate an "orphan-style" descendent); run the audit with the pgid of the first sleep; assert survivor list includes the second sleep; assert it gets killed.
   - **verify:** `uv run python -m unittest tests.test_orphan_audit` exits 0.

5. **Write `scripts/run_mcp_session.sh`.**
   - Shebang `#!/usr/bin/env bash`, `set -euo pipefail`, `IFS=$'\n\t'`.
   - Args: `$1 = MCP_NAME` (one of the keys in `.mcp.json`).
   - Resolve `DATE=$(date -u +%Y-%m-%d)`, `OUT_DIR=results/${DATE}/${MCP_NAME}`, `mkdir -p "$OUT_DIR"`.
   - **Prereq + fixtures-serve:** Call `make check`. Call `scripts/serve_fixtures.sh start`. trap-exit `scripts/serve_fixtures.sh stop` (only if it wasn't running before — track this with a flag).
   - **Pre-run audit:** `uv run python -m bench.orphan_audit --snapshot-only "$OUT_DIR/.ps_before"`.
   - **MCP-specific guard:** if `MCP_NAME == cloakbrowser`, call `uv run python -c "from bench.cloakbrowser_guard import assert_local_only; assert_local_only('${SNAPSHOT_BASE_URL}')"` — must pass since `SNAPSHOT_BASE_URL == http://127.0.0.1:8765`.
   - **ulimit:** `ulimit -v 4194304` (4 GB) — applies to the Claude Code child and everything it spawns.
   - **Prompt substitution:** `SNAPSHOT_BASE_URL=http://127.0.0.1:8765 MCP=$MCP_NAME OUT_DIR=$OUT_DIR envsubst < prompts/stage_walk.md > "$OUT_DIR/.prompt.md"`.
   - **Spawn Claude under setsid:**
     ```bash
     setsid claude --print \
       --output-format stream-json \
       --include-partial-messages \
       --allowedTools "mcp__${MCP_NAME}__*,Read,Write,Bash" \
       --append-system-prompt "$(cat "$OUT_DIR/.prompt.md")" \
       "Walk stages S1-S8 against the ${MCP_NAME} MCP. Snapshot fixtures are served at http://127.0.0.1:8765/. Save artifacts under ${OUT_DIR}/. STOP if you cannot complete a stage with this MCP." \
       > "$OUT_DIR/raw_stream.jsonl" 2>&1 &
     CLAUDE_PID=$!
     CLAUDE_PGID=$(ps -o pgid= -p $CLAUDE_PID | tr -d ' ')
     ```
   - **Per-tool-call timeout enforcement:** Claude Code does not enforce a per-tool-call timeout (Pitfall 9, upstream #35287). Use this strategy: watch `raw_stream.jsonl` for tool-call start events (`{"type":"assistant","message":{"content":[{"type":"tool_use",...`); if no matching `tool_result` appears within 30s, set the tool_call_id in a "timed_out" sentinel and pipe a SIGINT to the Claude process (which is documented to abort the in-flight tool). This is the **simplest correct approach**: implement it as a Python sidecar (`bench/timeout_watchdog.py`) that tails `raw_stream.jsonl` and signals the harness; the harness then aborts and re-spawns Claude for the next stage (each stage being its own re-attemptable unit via the file-mediated handoff pattern from CONTEXT.md). Set the overall session timeout (`timeout 1800`, 30 min) as a guardrail too.

     **Implementation detail:** `bench/timeout_watchdog.py` runs as `subprocess.Popen` for the duration of the session, reads `raw_stream.jsonl` incrementally via `tail -F`, and on `tool_use` events starts a 30s timer; on `tool_result` cancels it; on timer expiry writes a `TIMEOUT` line to `raw_stream.jsonl` and sends SIGINT to the Claude PID. If Claude doesn't abort within 5s, SIGTERM. If still not gone within 5 more, escalate to the pgid.
   - **Wait + cleanup:** `wait $CLAUDE_PID` (capture exit code). Then `kill_group $CLAUDE_PGID` to clean up any survivors.
   - **Post-run audit:** `uv run python -m bench.orphan_audit --before-snapshot "$OUT_DIR/.ps_before" --after-snapshot <(uv run python -m bench.orphan_audit --snapshot-only /dev/stdout) --pgid $CLAUDE_PGID --log "$OUT_DIR/orphan_audit.log"`. (Or simpler: take an explicit post-snapshot then call the audit with both file paths.) Non-zero exit → flag the run as `harness_leaked=true` in a sentinel file but continue (per Pitfall 9 "fail the run if orphan count > 0" — but in Phase 1 we LOG and CONTINUE on Playwright to surface the gap; future phases enforce stricter).
   - **Tee a transcript.md view:** `jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="text") | .text' "$OUT_DIR/raw_stream.jsonl" > "$OUT_DIR/transcript.md"`.
   - **Exit code:** 0 if claude exited 0 AND orphan audit ran (regardless of orphan count for Phase 1 — log only). 1 if Claude exited non-zero.
   - **verify:** `bash -n scripts/run_mcp_session.sh` syntax-checks; integration tested via `tests/test_run_mcp_session_smoke.sh` (next task).

6. **Write `tests/test_run_mcp_session_smoke.sh`.**
   - Boot `serve_fixtures.sh start`.
   - Replace `prompts/stage_walk.md` (temporarily, via env override `STAGE_WALK_PATH=tests/fixtures/hello_prompt.md`) with a one-line "Save 'hello' to ${OUT_DIR}/stage_s1.md and stop." prompt — proves the driver works without exercising every stage.
   - Run `scripts/run_mcp_session.sh playwright`.
   - Assert: `results/$(date -u +%Y-%m-%d)/playwright/stage_s1.md` exists and contains `hello`; `results/.../raw_stream.jsonl` is non-empty; `results/.../orphan_audit.log` exists; `results/.../transcript.md` is non-empty.
   - **verify:** `bash tests/test_run_mcp_session_smoke.sh` exits 0.

7. **Wire the Makefile updates.**
   - Replace the stub `bench-%` recipe with:
     ```makefile
     bench-%: check fixtures-serve
     \tscripts/run_mcp_session.sh $*
     ```
   - Add a `fixtures-serve` target that calls `scripts/serve_fixtures.sh start` (idempotent — script handles "already running").
   - **verify:** `make bench-playwright` runs end-to-end (with the smoke prompt or the real one).

## Acceptance

- `make bench-playwright` against the real `prompts/stage_walk.md` produces `results/<date>/playwright/` with `raw_stream.jsonl`, `transcript.md`, `stage_s1..s8.*` (or `.NA` / `.FAILED` for stages not applicable), and `orphan_audit.log`.
- `--allowedTools` restriction prevents WebFetch fallback (verified by grepping `raw_stream.jsonl` for any `WebFetch` tool_use — none present).
- Per-tool-call timeouts fire on a synthetic stalled tool (the smoke test induces a timeout by pointing at a `http://127.0.0.1:8765/slow` endpoint — not implemented yet, can be added later if calibration reveals a regression).
- `orphan_audit.log` shows 0 survivors after a clean Playwright run on the snapshot fixtures.
- `ulimit -v` is set; can verify via `ps -o vsz= -p $(pgrep -f "claude --print" | head -1)` during a run.

## Dependencies

- **Plan 01-01:** Makefile + uv + check_prereqs.
- **Plan 01-03:** snapshot fixtures + `serve_fixtures.sh` (so `bench-playwright` has something to drive against).
- **Plan 01-02:** `bench/cloakbrowser_guard.py` (only required for cloakbrowser, not Playwright; but the import path must be valid).

## Notes / Pitfalls

- **Pitfall 9 (orphan accumulation):** This plan's primary defense — setsid + orphan_audit + ulimit + per-tool-call timeout. Without these four, the 1hr stability test (Phase 3) is a lie.
- **Pitfall 1 (transient failures):** Retry gate is plan 01-05's job; this plan just produces the per-stage evidence files the retry gate operates over.
- **Anti-Pattern 3 from ARCHITECTURE.md (Claude reaches for fallback tools):** Defended by `--allowedTools "mcp__${MCP}__*,Read,Write,Bash"`. No WebFetch in the allow-list.
- **FAIRNESS-07 ("do not bypass MCP-reported failures"):** Honored. If the MCP times out on `initialize` or crashes mid-stage, the harness records the failure rather than swapping the MCP for a different one. Tag goes in the failure-attribution taxonomy applied by plan 01-05.
- **CONTEXT.md decision honored:** "Orchestration Model — One Claude Code session per MCP, driven by `claude --print --output-format stream-json` with `--allowedTools` so each MCP lives or dies on its own surface (no silent WebFetch fallback)."
- **GNU vs BSD tooling on macOS:** `ps -axo pgid` works on macOS (BSD ps); `setsid` is available via `coreutils` (`brew install coreutils` provides `gsetsid`, but Python's `start_new_session=True` is the portable path — use it from `bench/process_group.py` rather than relying on a CLI tool).
- **Ashby snapshot caveat (from plan 01-03):** If the Ashby snapshot renders as an empty shell because the live API is unreachable from loopback, the harness will record S2 as FAIL or N/A. This is acceptable for calibration if Playwright's S2 score in 2026-03 was driven by the live API; plan 01-07 will compare carefully and surface a discrepancy if the snapshot diverges from the live behavior.

## Out of Scope

- Real-time TLS-fingerprint capture during the session — deferred to G-710.
- Cold-start measurement — Phase 3 (deferred reqs MEAS-01); Phase 1 emits `cold_start.json` as a stub via plan 01-06.
- Token efficiency 3-scope split — Phase 3 (MEAS-02); Phase 1 emits `tokens.json` as a partial stub (just the `turn` scope from stream-json usage blocks, which falls out for free).
- Per-stage tool-call counts — Phase 3 (MEAS-08).
- The bot-detection probe stages — deferred to G-710.
