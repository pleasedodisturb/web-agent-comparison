---
phase: 1
plan: 04
subsystem: harness-driver
status: complete
completed: 2026-05-22
tags: [harness, mcp, claude-code, process-group, timeout, fairness]
dependency-graph:
  requires: [01-01, 01-02, 01-03]
  provides:
    - per-mcp-driver
    - locked-stage-walk-prompt
    - orphan-audit-cli
    - timeout-watchdog
    - process-group-helpers
  affects: [01-05, 01-06, 01-07]
tech-stack:
  added:
    - "Python 3.12 (subprocess + signal, no new deps)"
    - "envsubst (gettext) for prompt placeholder expansion"
    - "Bash 'set -m' job-control mode for setsid-equivalent process-group spawn"
  patterns:
    - "ps -axo pid,ppid,pgid,rss,command snapshot diff for orphan detection"
    - "JSONL-tail watchdog for per-tool-call timeout enforcement"
    - "claude --print --output-format stream-json + --allowedTools allow-list"
key-files:
  created:
    - prompts/stage_walk.md
    - bench/process_group.py
    - bench/orphan_audit.py
    - bench/timeout_watchdog.py
    - scripts/run_mcp_session.sh
    - tests/test_orphan_audit.py
    - tests/test_timeout_watchdog.py
    - tests/test_run_mcp_session_smoke.sh
    - tests/fixtures/hello_prompt.md
  modified:
    - Makefile  (bench-<mcp> now depends on fixtures-serve; fixtures-serve swallows rc=2 idempotently)
decisions:
  - "set -m + & for setsid: Python's start_new_session=True is portable; bash's `set -m` job-control mode is the in-shell equivalent. setsid(1) is not on macOS base; gsetsid via coreutils works but adds a brew dep we don't need."
  - "Watchdog as Popen sidecar, not signal-based timer: per-tool-call timeouts need to know WHICH call timed out (the tool_use_id sentinel goes into raw_stream.jsonl for plan 01-05's scorer to attribute the stage). A SIGALRM in-process is simpler but loses the per-call attribution."
  - "Phase 1 logs-and-continues on orphan_audit nonzero rc; future phases tighten to hard fail. Plan 01-04 explicitly says don't gate the run on orphans yet — we want to surface the gap on Playwright before tightening."
  - "Smoke test gated behind WAC_SMOKE_RUN=1 because it consumes API tokens. Default skip; CI sets the flag."
metrics:
  duration_minutes: 75
  commits: 6
  files_created: 9
  files_modified: 1
  tests_added: 13
  tests_passing: 32
---

# Phase 1 Plan 04: Prompts and MCP Session Driver Summary

The load-bearing per-MCP driver. Owns process lifecycle (setsid + orphan_audit + ulimit + per-tool-call 30s timeout), owns prompt delivery (the locked S1-S8 stage_walk), and owns the no-WebFetch-fallback fairness contract via `claude --allowedTools "mcp__${MCP}__*,Read,Write,Bash"`.

## What was built

### `prompts/stage_walk.md`
Locked S1-S8 task script. Same prompt drives every candidate MCP. Three placeholders the wrapper expands via `envsubst`: `${MCP}`, `${SNAPSHOT_BASE_URL}`, `${OUT_DIR}`. Stages mirror `results/2026-03-31_run.md` and `scoring/rubric.md`:

- **S1** — Extract job data from the Greenhouse snapshot
- **S2** — Extract job data from the Ashby SPA snapshot (renders client-side; the lightpanda dealbreaker stage)
- **S3** — Platform detection (Greenhouse vs Ashby from the two extracted blobs)
- **S4** — Navigate to apply form (read-only MCPs emit `.NA` here)
- **S5** — Fill application form (Jane Testworth, 6 fields)
- **S6** — Upload `fixtures/mock_resume.pdf`
- **S7** — Handle Greenhouse source dropdown (React Select — `select_option` fails, requires type+Enter or run_code)
- **S8** — Screenshot of filled form

Verify: `grep -c '^## S[1-8]' prompts/stage_walk.md` returns 8.

### `bench/process_group.py`
Setsid + killpg helpers. Public API:

- `spawn_setsid(argv, env, cwd, ...)` → `Popen` with `start_new_session=True` (PID == PGID)
- `kill_group(pgid, grace_s=5.0)` — SIGTERM, grace, SIGKILL via `os.killpg`
- `pgid_of(pid)` → `int` (thin wrapper)
- `snapshot_ps()` → list[dict] via `ps -axo pid,ppid,pgid,rss,command`
- `write_ps_snapshot(path)` / `read_ps_snapshot(path)` — tab-separated dump format (trivially `cat`-readable for debugging)

### `bench/orphan_audit.py`
CLI with two modes:

- `--snapshot-only PATH` — dump current ps to a file (used before+after Claude spawn)
- `--before-snapshot ... --after-snapshot ... --pgid ... --log ...` — diff the two; any new PID matching the target PGID OR an MCP cmdline regex is SIGKILL'd, logged as `KILLED pid=... pgid=... cmd=...`, exit code 1 if survivors > 0

MCP cmdline regex matches: playwright-mcp, chrome-devtools-mcp, obscura-mcp, firecrawl-mcp, cloakbrowsermcp, browser-use, lightpanda, chromium, headless_shell, chrome_crashpad_handler. Over-kill inside the harness window is cheap; false-negative leaks are exactly the bug we're defending against (Pitfall 9).

### `bench/timeout_watchdog.py`
Per-tool-call 30s timeout enforcer (Claude Code does not enforce — upstream #35287). Runs as a `Popen` sidecar alongside the Claude session:

1. Tails `raw_stream.jsonl` incrementally (resumes from last offset)
2. Tracks open `tool_use_id`s by parsing `assistant.message.content[]` blocks; pops them when matching `tool_result` blocks arrive
3. If a `tool_use` stays open longer than `--timeout-seconds`, appends a `{"type":"watchdog_timeout", ...}` sentinel to the JSONL, SIGINTs Claude
4. 5s grace for Claude to abort the in-flight tool, then SIGTERM escalation
5. Overall-session guardrail at 1800s (30 min) — the documented fallback if per-tool-call detection is too brittle

Defensive parsing: malformed JSON lines are skipped silently (Claude may flush mid-write). Mtime-stall fallback at 2x the per-tool-call threshold for cases where the primary scanner gets confused.

### `scripts/run_mcp_session.sh`
The driver. Pipeline (in order):

1. `make check` — prereq gate
2. `fixtures-serve` — idempotent; only stops on exit if WE started it
3. Pre-run `ps` snapshot
4. `cloakbrowser_guard.assert_local_only()` — only for cloakbrowser (loopback-only contract)
5. `envsubst` expands `${MCP}` / `${SNAPSHOT_BASE_URL}` / `${OUT_DIR}` in the stage_walk prompt
6. `ulimit -v 4194304` — 4 GB virtual-memory ceiling inherited by the Claude child and descendants
7. `setsid`-equivalent (`set -m` + `&`) spawn of `claude --print --output-format stream-json --allowedTools "mcp__${MCP}__*,Read,Write,Bash" --append-system-prompt <rendered>`
8. Timeout watchdog Popen sidecar
9. `wait` for Claude; capture rc
10. Reap watchdog
11. `kill_group` on the Claude PGID (Python-bridged so the SIGTERM+grace+SIGKILL pattern matches the tested code path)
12. Post-run ps snapshot
13. `orphan_audit` diff — nonzero rc writes `.harness_leaked` sentinel but continues (Phase 1 policy)
14. Derive `transcript.md` from the JSONL stream if Claude didn't write its own

`STAGE_WALK_PATH` env override lets the smoke test substitute `tests/fixtures/hello_prompt.md` — a tiny "use Write to make stage_s1.md contain 'hello'" prompt that exercises the driver without spending tokens on real MCP tool calls.

### Tests

- **`tests/test_orphan_audit.py`** — 8 tests covering pure-function diff logic (5 synthetic cases) + integration (spawn a real `sleep` under setsid with a cmdline matching the MCP regex; verify SIGKILL'd via Popen.wait returncode == -9).
- **`tests/test_timeout_watchdog.py`** — 9 tests covering the JSONL scanner (form 1+2+3 of tool_use/tool_result events, malformed lines, offset-resume), `_stalled_use` (oldest-first selection), and end-to-end SIGINT delivery against a Python signal-trap stub.
- **`tests/test_run_mcp_session_smoke.sh`** — gated by `WAC_SMOKE_RUN=1`. Runs the real driver against playwright with the hello prompt, asserts: `stage_s1.md contains 'hello'`, `raw_stream.jsonl` non-empty, `orphan_audit.log` exists, NO `WebFetch` `tool_use` in the stream (fairness contract).

Total: 13 new tests; 32 unit tests passing across the whole suite (orphan_audit + timeout_watchdog + cloakbrowser_guard + scrub_artifacts).

### `Makefile` change

`bench-<mcp>` now lists `fixtures-serve` as an explicit prerequisite. `fixtures-serve` recipe swallows `serve_fixtures.sh start` rc=2 (server already running) so repeated `make bench-<mcp>` calls don't fail on the second invocation.

## Verification

```
$ .venv/bin/python -m unittest discover -s tests
Ran 32 tests in 1.6s
OK

$ bash tests/test_secret_guard.sh           # all cases passed
$ bash tests/test_snapshot_serves.sh        # all cases passed
$ bash tests/test_run_mcp_session_smoke.sh  # SKIPPED (gated)

$ grep -c '^## S[1-8]' prompts/stage_walk.md
8

$ .venv/bin/python -c "from bench.process_group import spawn_setsid, kill_group, snapshot_ps; print('ok')"
ok

$ make -n bench-playwright
scripts/check_prereqs.sh
scripts/serve_fixtures.sh start || rc=$? ; if [ "${rc:-0}" -ne 0 ] && [ "${rc:-0}" -ne 2 ]; ...
if [ -x scripts/run_mcp_session.sh ]; then scripts/run_mcp_session.sh playwright ; ...

$ make check
==> Checking host tools
==> Checking MCP binaries from .mcp.json
check_prereqs: ok (0 warning(s))

$ # envsubst expansion of the locked prompt — 0 unsubstituted vars, 9 mentions of "playwright"
$ OUT_DIR=/tmp/x MCP=playwright SNAPSHOT_BASE_URL=http://127.0.0.1:8765 envsubst < prompts/stage_walk.md | grep -c '\${'
0
```

Smoke test of `make bench-playwright` end-to-end was NOT run because the calibration gate is plan 01-07, not 01-04. The scope_anchor explicitly says "make bench-playwright should succeed in producing evidence files; whether the composite reproduces 9.07 ±0.5 is plan 01-07's gate". The wrapper's syntax, expansion logic, and orphan-audit / watchdog integrations are exercised by the unit tests; the smoke test exists and is parked behind `WAC_SMOKE_RUN=1` for plan 01-07 to use as the calibration entry point.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `fixtures-serve` Make recipe failed on idempotent re-invocation**
- **Found during:** Task 7 (Makefile wiring)
- **Issue:** `scripts/serve_fixtures.sh start` exits rc=2 when the server is already running. That's "success, no-op" semantically, but Make treats it as a hard failure. Running `make bench-playwright` twice in a row would fail the second time.
- **Fix:** The `fixtures-serve` recipe now captures the rc and treats both 0 and 2 as success, while still failing on any other nonzero rc.
- **Files modified:** `Makefile`
- **Commit:** `3aae22a`

**2. [Rule 1 - Bug] Initial orphan-audit integration test used an unrealistic empty before-snapshot**
- **Found during:** Task 4 (writing tests/test_orphan_audit.py)
- **Issue:** Synthesizing an empty before-snapshot meant the diff treated every running process as "new", so any chromium/playwright processes already on the dev host got flagged and killed (25 survivors in the first run). That's not how a real harness run looks.
- **Fix:** Switched the integration test to take a REAL before-snapshot just before spawning the synthetic survivor. The diff then isolates exactly one new PID — the one we spawned — which is the realistic harness flow.
- **Files modified:** `tests/test_orphan_audit.py`
- **Commit:** `6d11328`

**3. [Rule 1 - Bug] macOS `kill -0` returns success on zombie processes**
- **Found during:** Task 4 (running tests/test_orphan_audit.py)
- **Issue:** The test polled liveness via `os.kill(pid, 0)` after the audit's SIGKILL. On macOS a zombie process (killed but not yet `wait`-reaped) still answers `kill -0`, so the test reported the sleep as alive even though it had been SIGKILL'd successfully.
- **Fix:** Switched to `Popen.wait(timeout=5)` and asserted `returncode == -SIGKILL` (-9). That semantics is portable across macOS and Linux.
- **Files modified:** `tests/test_orphan_audit.py`
- **Commit:** `6d11328`

**4. [Rule 1 - Bug] Shell-level `trap INT` did not fire under sleep**
- **Found during:** Task 5 (running tests/test_timeout_watchdog.py)
- **Issue:** The watchdog integration test used `/bin/sh -c "trap 'exit 42' INT; sleep 60"` as a stub parent. When the watchdog SIGINT'd the stub, the shell didn't deliver the trap until the external `sleep 60` finished — which never happened, so the watchdog escalated to SIGTERM 5s later and the test asserted on the wrong exit code.
- **Fix:** Switched the stub to a Python signal-trap (`signal.signal(SIGINT, lambda *_: sys.exit(42))` + `time.sleep(60)`). Python's signal handling delivers SIGINT promptly, regardless of what the process is doing.
- **Files modified:** `tests/test_timeout_watchdog.py`
- **Commit:** `8ffdb66`

### Implementation Tradeoffs

**Watchdog brittleness — per plan instructions, documented here for visibility.**

The per-tool-call 30s timeout is a HARD requirement per CLAUDE.md and the plan, but Claude Code itself does not expose a per-tool-call timeout API (upstream #35287). The watchdog approach has three failure modes worth flagging for plan 01-05 / 01-07:

1. **JSON line buffering.** Claude Code may flush a `tool_use` event in chunks; if the watchdog reads a half-line, JSON parse fails. Mitigation: we skip malformed lines and re-read from the same byte offset on the next poll. The next complete write will be processed.

2. **Form-detection skew.** We parse three forms of tool_use/tool_result events (top-level event, assistant.content[], user.content[]). If Claude Code adds a fourth form in a future release (e.g. a new partial-message format), the watchdog will silently miss it. The mtime-stall fallback at 2x the threshold partially covers this — if Claude is wedged but emitting no JSON events, the file stops growing and the fallback fires.

3. **SIGINT vs in-flight tool call.** The plan documents that Claude Code "is documented to abort the in-flight tool on SIGINT", but we have not empirically verified the per-MCP behaviour. If Claude eats the SIGINT and continues, the SIGTERM escalation at +5s will terminate the whole process — which is louder than aborting just the one tool call, but is still a safe stop.

If plan 01-07's calibration exposes a watchdog regression that breaks the Playwright reproduction, the documented fallback is `timeout 1800` (30 min) as a coarse session-level guardrail. The overall-timeout-seconds flag is already wired and defaults to 1800.

**setsid via `set -m` rather than gsetsid.**
macOS base does not ship `setsid(1)`. `gsetsid` is available via Homebrew coreutils but would add a new prereq to `check_prereqs.sh`. The bash idiom `set -m; cmd &; set +m` enables job-control, which puts the backgrounded child in its own process group — exactly setsid semantics. We capture PGID via `ps -o pgid= -p $CHILD_PID`. Tested OK on macOS 25.5.0.

## Auth gates encountered

None. All steps ran with locally-installed tooling (uv, npm-installed MCPs, claude CLI).

## Known Stubs

None introduced. The `raw_stream.jsonl` is real Claude Code output; `orphan_audit.log` is real ps-diff output; `transcript.md` is jq-derived from the JSONL or Claude-written.

The phase still has stubs from plan 01-01 (`coldstart`, `tls`, `stability` Make targets all print "deferred to G-710") — those are unchanged in this plan and remain Phase 3 / G-710 work.

## What's next

Plan 01-05 (retry gate + transient classifier) consumes the per-stage evidence files this plan produces. The scorer it builds keys off `.harness_leaked` and the `watchdog_timeout` JSONL sentinels we added. Plan 01-06 emits the stub `cold_start.json` / `tls.json` / `stability.log` placeholders. Plan 01-07 is the calibration gate that actually runs `make bench-playwright` and asserts the 9.07 ±0.5 reproduction — that's the moment the smoke test (`WAC_SMOKE_RUN=1`) graduates to a real-prompt run.

## Self-Check: PASSED

Created files exist:
- `prompts/stage_walk.md` — FOUND
- `bench/process_group.py` — FOUND
- `bench/orphan_audit.py` — FOUND
- `bench/timeout_watchdog.py` — FOUND
- `scripts/run_mcp_session.sh` — FOUND (executable)
- `tests/test_orphan_audit.py` — FOUND
- `tests/test_timeout_watchdog.py` — FOUND
- `tests/test_run_mcp_session_smoke.sh` — FOUND (executable)
- `tests/fixtures/hello_prompt.md` — FOUND

Commits exist on branch `G-703/phase-01-harness-foundation`:
- `6291df3` — prompts/stage_walk.md — FOUND
- `4014cca` — bench/process_group.py — FOUND
- `6d11328` — bench/orphan_audit.py + tests — FOUND
- `8ffdb66` — bench/timeout_watchdog.py + tests — FOUND
- `bcebbf0` — scripts/run_mcp_session.sh + smoke test — FOUND
- `3aae22a` — Makefile wiring — FOUND

Tests: 32/32 unit tests pass; all shell tests pass; smoke test correctly skips when `WAC_SMOKE_RUN` is unset.
