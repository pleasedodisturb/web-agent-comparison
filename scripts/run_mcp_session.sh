#!/usr/bin/env bash
#
# run_mcp_session.sh — drive ONE Claude Code session against ONE MCP.
#
# This is the per-MCP harness driver. The orchestration model is
# documented in .planning/phases/01-harness-foundation/01-CONTEXT.md
# ("Orchestration Model"): one Claude Code session per MCP, driven by
# `claude --print --output-format stream-json` with `--allowedTools`
# restricting the tool surface to `mcp__${MCP}__*,Read,Write,Bash`. No
# WebFetch fallback — each MCP lives or dies on its own surface, which is
# the fairness contract this whole comparison rests on.
#
# Usage:
#   scripts/run_mcp_session.sh <MCP_NAME>
#
# Where <MCP_NAME> is one of the keys in .mcp.json (playwright,
# browser-use, chrome-devtools, lightpanda, obscura, firecrawl,
# cloakbrowser).
#
# Pipeline:
#   1. make check        prereq gate
#   2. fixtures-serve    boot the snapshot http server (idempotent)
#   3. pre-run ps snapshot
#   4. cloakbrowser safety guard (loopback URL only)
#   5. envsubst the stage_walk prompt with ${MCP}/${SNAPSHOT_BASE_URL}/${OUT_DIR}
#   6. ulimit -v 4194304   (4 GB virtual-memory ceiling)
#   7. setsid claude --print --output-format stream-json ...
#   8. spawn the timeout watchdog as a sidecar
#   9. wait for Claude to exit (capture rc)
#   10. SIGTERM the watchdog (its purpose is done)
#   11. kill_group on the Claude PGID to reap any descendants
#   12. post-run ps snapshot
#   13. orphan_audit diff (writes orphan_audit.log; nonzero rc => leaked)
#   14. derive transcript.md from the JSONL stream
#
# Exit codes:
#   0 — Claude exited 0; orphan audit logged (may have flagged survivors,
#       see orphan_audit.log; Phase 1 logs-and-continues per plan 01-04)
#   1 — Claude exited non-zero, OR a step before Claude spawn failed
#   2 — bad arguments

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ─── Arg parsing ─────────────────────────────────────────────────────────

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <MCP_NAME>" >&2
    echo "  MCP_NAME must be a key in .mcp.json" >&2
    exit 2
fi
MCP_NAME="$1"

# Validate MCP_NAME exists in .mcp.json — fail fast with a clear message
# rather than letting Claude spawn and silently no-op when the MCP server
# doesn't exist.
if ! jq -e --arg m "$MCP_NAME" '.mcpServers[$m]' .mcp.json >/dev/null; then
    echo "run_mcp_session: '$MCP_NAME' is not a key in .mcp.json" >&2
    jq -r '.mcpServers | keys[]' .mcp.json | sed 's/^/  - /' >&2
    exit 2
fi

# ─── Paths + env ─────────────────────────────────────────────────────────

DATE="$(date -u +%Y-%m-%d)"
export OUT_DIR="results/${DATE}/${MCP_NAME}"
export MCP="$MCP_NAME"
export SNAPSHOT_BASE_URL="${SNAPSHOT_BASE_URL:-http://127.0.0.1:8765}"
mkdir -p "$OUT_DIR"

# The stage_walk prompt can be overridden for smoke testing. The smoke
# test (tests/test_run_mcp_session_smoke.sh) points this at a tiny "say
# hello" prompt so the driver can be exercised without running the full
# S1-S8 walk.
STAGE_WALK_PATH="${STAGE_WALK_PATH:-prompts/stage_walk.md}"
if [[ ! -f "$STAGE_WALK_PATH" ]]; then
    echo "run_mcp_session: prompt file missing at $STAGE_WALK_PATH" >&2
    exit 1
fi

# Pre-flight: pick the project venv python (3.12). System python3 on this
# host is 3.14.5 and is known broken — every other script in the harness
# already takes this route.
VENV_PY="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    echo "run_mcp_session: project venv python missing at $VENV_PY" >&2
    echo "run_mcp_session: run 'uv sync' to materialize the venv first" >&2
    exit 1
fi

# ─── 1. Prereq gate ──────────────────────────────────────────────────────

echo "==> run_mcp_session: $MCP_NAME" >&2
echo "==> make check (prereq gate)" >&2
make check

# ─── 2. fixtures-serve (idempotent) ──────────────────────────────────────
# We track whether we started the fixture server so we can stop it on
# exit (only if we started it — leave it running if a human had it up).

FIXTURES_STARTED_BY_US=0
if scripts/serve_fixtures.sh status | grep -q '^stopped'; then
    echo "==> booting fixture server (was stopped)" >&2
    scripts/serve_fixtures.sh start
    FIXTURES_STARTED_BY_US=1
else
    echo "==> fixture server already running — using existing instance" >&2
fi

cleanup_fixtures() {
    if (( FIXTURES_STARTED_BY_US == 1 )); then
        echo "==> stopping fixture server (we started it)" >&2
        scripts/serve_fixtures.sh stop || true
    fi
}

# ─── 3. cloakbrowser safety guard ────────────────────────────────────────
# CONSTRAINTS in CLAUDE.md: cloakbrowser is closed-source binary touching
# cookies; never point at authenticated host pages. Enforce loopback-only
# via the guard module. The check is cheap; running it for every MCP
# would be wasted work — only run it for cloakbrowser itself.

if [[ "$MCP_NAME" == "cloakbrowser" ]]; then
    echo "==> cloakbrowser guard: asserting loopback-only target URL" >&2
    "$VENV_PY" -c "from bench.cloakbrowser_guard import assert_local_only; assert_local_only('${SNAPSHOT_BASE_URL}')"
fi

# ─── 4. Pre-run ps snapshot ──────────────────────────────────────────────

PS_BEFORE="$OUT_DIR/.ps_before.tsv"
PS_AFTER="$OUT_DIR/.ps_after.tsv"
ORPHAN_LOG="$OUT_DIR/orphan_audit.log"

echo "==> ps snapshot (before)" >&2
"$VENV_PY" -m bench.orphan_audit --snapshot-only "$PS_BEFORE"

# ─── 5. Substitute the stage_walk prompt ─────────────────────────────────
# envsubst expands ${MCP}, ${SNAPSHOT_BASE_URL}, ${OUT_DIR} from the
# environment we exported above.

PROMPT_PATH="$OUT_DIR/.prompt.md"
echo "==> rendering prompt: $STAGE_WALK_PATH → $PROMPT_PATH" >&2
envsubst < "$STAGE_WALK_PATH" > "$PROMPT_PATH"

# ─── 6. ulimit + Claude spawn ────────────────────────────────────────────
# ulimit -v 4194304 = 4 GB virtual-memory ceiling, inherited by Claude
# Code and every child it spawns. An OOM in the MCP child kills the MCP,
# not the Mac Mini.

ulimit -v 4194304 2>/dev/null || \
    echo "run_mcp_session: ulimit -v unsupported on this platform (skipping)" >&2

RAW_STREAM="$OUT_DIR/raw_stream.jsonl"
TRANSCRIPT="$OUT_DIR/transcript.md"

# Build the user-message string. The system prompt is the rendered
# stage_walk; the user message tells Claude what to do at session-open.
USER_MSG="Walk stages S1-S8 against the ${MCP_NAME} MCP. Snapshot fixtures are served at ${SNAPSHOT_BASE_URL}. Save artifacts under ${OUT_DIR}/. STOP if you cannot complete a stage with this MCP."

# Spawn Claude under setsid (new session = new process group). We pipe
# stdout+stderr both to the JSONL so any error messages are captured.
#
# --allowedTools is the fairness contract: ONLY mcp__${MCP_NAME}__* plus
# Read/Write/Bash. No WebFetch, no other MCPs.
#
# --append-system-prompt takes the rendered stage_walk content via
# command substitution.
#
# --include-partial-messages is on so the watchdog sees streaming tokens
# and the mtime-stall fallback has signal to work with.

echo "==> spawning Claude Code with --allowedTools mcp__${MCP_NAME}__*,Read,Write,Bash" >&2

# We use `setsid` indirectly by relying on `start_new_session=True` from
# the Python launcher pattern would require shelling into Python; in
# bash, the closest portable equivalent is to rely on the fact that
# bash's `&` puts the child in its own process group when job control is
# enabled. We enable job control explicitly with `set -m` to make this
# guaranteed. `set +m` restores afterwards.
set -m
claude --print \
    --output-format stream-json \
    --include-partial-messages \
    --verbose \
    --allowedTools "mcp__${MCP_NAME}__*,Read,Write,Bash" \
    --append-system-prompt "$(cat "$PROMPT_PATH")" \
    "$USER_MSG" \
    > "$RAW_STREAM" 2>&1 &
CLAUDE_PID=$!
set +m

# Capture the PGID. With `set -m` the child is its own group leader, so
# PGID == PID for the child.
CLAUDE_PGID=$(ps -o pgid= -p "$CLAUDE_PID" | tr -d ' ' || echo "$CLAUDE_PID")
echo "==> Claude PID=$CLAUDE_PID PGID=$CLAUDE_PGID" >&2

# ─── 7. Watchdog sidecar ─────────────────────────────────────────────────
# Per-tool-call 30s timeout + 30min overall guardrail.

echo "==> spawning timeout watchdog (per-tool-call=30s, overall=1800s)" >&2
"$VENV_PY" -m bench.timeout_watchdog \
    --jsonl "$RAW_STREAM" \
    --parent-pid "$CLAUDE_PID" \
    --timeout-seconds 30 \
    --overall-timeout-seconds 1800 \
    > "$OUT_DIR/.watchdog.log" 2>&1 &
WATCHDOG_PID=$!

# ─── 8. Wait for Claude to exit ──────────────────────────────────────────

CLAUDE_RC=0
if wait "$CLAUDE_PID"; then
    CLAUDE_RC=0
else
    CLAUDE_RC=$?
fi
echo "==> Claude exited rc=$CLAUDE_RC" >&2

# ─── 9. Reap the watchdog ────────────────────────────────────────────────

if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
    kill "$WATCHDOG_PID" 2>/dev/null || true
    wait "$WATCHDOG_PID" 2>/dev/null || true
fi

# ─── 10. Kill any Claude descendants still hanging around ────────────────
# kill_group via Python so the SIGTERM+grace+SIGKILL pattern is the same
# one tests/test_orphan_audit.py exercises.

echo "==> kill_group on PGID=$CLAUDE_PGID" >&2
"$VENV_PY" -c "
import sys
from bench.process_group import kill_group
try:
    kill_group(int(sys.argv[1]), grace_s=3.0)
except ProcessLookupError:
    pass
" "$CLAUDE_PGID" || true

# ─── 11. Post-run ps snapshot + orphan audit ─────────────────────────────

echo "==> ps snapshot (after)" >&2
"$VENV_PY" -m bench.orphan_audit --snapshot-only "$PS_AFTER"

echo "==> orphan audit diff" >&2
AUDIT_RC=0
"$VENV_PY" -m bench.orphan_audit \
    --before-snapshot "$PS_BEFORE" \
    --after-snapshot "$PS_AFTER" \
    --pgid "$CLAUDE_PGID" \
    --log "$ORPHAN_LOG" || AUDIT_RC=$?

if (( AUDIT_RC != 0 )); then
    # Phase 1 logs-and-continues on orphans (per plan 01-04). Future
    # phases will tighten this to a hard fail. Surface the leak in a
    # sentinel file the scorer can key off.
    echo "harness_leaked=true" > "$OUT_DIR/.harness_leaked"
    echo "==> orphan audit flagged survivors; see $ORPHAN_LOG (continuing — Phase 1 policy)" >&2
fi

# ─── 12. Derive transcript.md from the JSONL stream ─────────────────────
# Pull assistant text-content blocks out of stream-json. This gives a
# human-readable view of what Claude said, separate from the raw event
# stream. If Claude wrote its own transcript.md per the stage_walk
# instructions, that's the canonical version; this fallback covers cases
# where Claude failed before reaching the end.

if [[ ! -s "$TRANSCRIPT" ]]; then
    jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="text") | .text' \
        "$RAW_STREAM" > "$TRANSCRIPT" 2>/dev/null || true
fi

# ─── 13. Extract turn-scope token usage (plan 01-06) ────────────────────
# Phase 1 only captures the `turn`-scope token count from the stream-json
# `usage` blocks. The 3-scope split (schema / payload / turn) lands in
# Phase 3 / MEAS-02. The aggregator's `_score_token_efficiency` already
# treats a {"deferred": ...} payload as neutral; the file we write here
# always carries the `turn` numbers we DO have, plus null placeholders for
# `schema` and `payload`, with a top-level "deferred" key pointing at the
# Phase 3 ticket.
#
# jq pipeline:
#   `select(.type=="result")` → keep only the terminal-result envelope
#   `.usage`                  → unwrap the usage block
#   `[ ... ] | last // {}`    → grab the last one (the cumulative total)
TOKENS_PATH="$OUT_DIR/tokens.json"
USAGE_BLOCK=$(jq -c '[inputs | select(.type=="result") | .usage] | last // {}' \
    < "$RAW_STREAM" 2>/dev/null || echo '{}')

cat > "$TOKENS_PATH" <<EOF
{
  "mcp": "${MCP_NAME}",
  "scope": "turn",
  "deferred": "phase-3",
  "reason": "3-scope token split (schema/payload/turn) deferred to Phase 3 (MEAS-02). Phase 1 captures only turn-scope from stream-json usage blocks.",
  "turn": ${USAGE_BLOCK},
  "schema_bytes": null,
  "payload_bytes": null
}
EOF

# ─── 14. tools_inventory (real measurement, plan 01-06) ─────────────────
# Spawn the MCP via mcp.client.stdio (Python SDK 1.16), call tools/list,
# write tools_inventory.json. Failure modes (INITIALIZE_TIMEOUT,
# SPAWN_OR_RPC_ERROR, MCP_CONFIG_ERROR) all produce a non-zero exit code
# from the module — we capture it and log, but DO NOT fail the whole
# session. The aggregator reads tools_inventory.json and attributes
# `tool-bug` per FAIRNESS-06 when status != "OK".
echo "==> tools_inventory: probing ${MCP_NAME} via mcp.client.stdio" >&2
INVENTORY_RC=0
"$VENV_PY" -m bench.tools_inventory "$MCP_NAME" \
    --out "$OUT_DIR/tools_inventory.json" \
    || INVENTORY_RC=$?
if (( INVENTORY_RC != 0 )); then
    echo "==> tools_inventory: ${MCP_NAME} exited rc=$INVENTORY_RC (see $OUT_DIR/tools_inventory.json for status field)" >&2
fi

# ─── 15. Deferred-marker stubs (plan 01-06) ─────────────────────────────
# Lock the evidence-directory shape by emitting tls.json, cold_start.json,
# and stability.log as deferred-marker stubs. The aggregator already
# recognizes {"deferred": ...} and assigns the neutral mid-band score.
echo "==> stub_writers: emitting tls.json + cold_start.json + stability.log" >&2
"$VENV_PY" -m bench.stub_writers "$OUT_DIR" --mcp-name "$MCP_NAME" || \
    echo "==> stub_writers: failed (continuing — Phase 1 policy)" >&2

# ─── 16. Versions manifest (once per run, idempotent) ───────────────────
# capture_versions.py writes results/$DATE/versions.json +
# results/$DATE/versions.lock.md. Run only if absent for this date — the
# manifest covers the whole run, not per-MCP, so re-running for every MCP
# would just waste cycles on shasum/npm-view calls.
if [[ ! -f "results/$DATE/versions.json" ]]; then
    echo "==> capture_versions: writing results/$DATE/versions.{json,lock.md}" >&2
    "$VENV_PY" -m bench.capture_versions \
        --date "$DATE" \
        --results-root "results" \
        || echo "==> capture_versions: failed (continuing — Phase 1 policy)" >&2
else
    echo "==> capture_versions: results/$DATE/versions.json already exists; skipping" >&2
fi

# ─── 17. MACHINE.md (once per run, idempotent) ──────────────────────────
# Populate results/$DATE/MACHINE.md from templates/MACHINE.md via envsubst.
# Pulls every field from versions.json (single source of truth) so the
# two files cannot disagree about host or tooling versions.
MACHINE_TEMPLATE="$REPO_ROOT/templates/MACHINE.md"
MACHINE_OUT="results/$DATE/MACHINE.md"
if [[ -f "$MACHINE_TEMPLATE" && ! -f "$MACHINE_OUT" ]]; then
    if [[ -f "results/$DATE/versions.json" ]]; then
        echo "==> MACHINE.md: rendering from $MACHINE_TEMPLATE" >&2
        # Export envsubst variables from versions.json (jq -r emits "" for nulls).
        export CAPTURED_AT_UTC="$(jq -r '.captured_at // ""' "results/$DATE/versions.json")"
        export HOST_OS="$(jq -r '.host.os // ""' "results/$DATE/versions.json")"
        export HOST_KERNEL="$(jq -r '.host.kernel_version // ""' "results/$DATE/versions.json")"
        export HOST_ARCH="$(jq -r '.host.arch // ""' "results/$DATE/versions.json")"
        export MACOS_VERSION="$(jq -r '.host.macos_version // ""' "results/$DATE/versions.json")"
        export CLAUDE_VERSION="$(jq -r '.tooling.claude_code // ""' "results/$DATE/versions.json")"
        export NODE_VERSION="$(jq -r '.tooling.node // ""' "results/$DATE/versions.json")"
        export NPM_VERSION="$(jq -r '.tooling.npm // ""' "results/$DATE/versions.json")"
        export PYTHON_VERSION="$(jq -r '.tooling.python // ""' "results/$DATE/versions.json")"
        export UV_VERSION="$(jq -r '.tooling.uv // ""' "results/$DATE/versions.json")"
        envsubst < "$MACHINE_TEMPLATE" > "$MACHINE_OUT"
    else
        echo "==> MACHINE.md: skipping (versions.json absent)" >&2
    fi
fi

# ─── 18. Final missing-file audit ───────────────────────────────────────
# Per HARNESS-02 the evidence directory MUST contain a fixed file list.
# We do NOT fail the run on missing files (plan 01-07 owns the strict
# gate); we just log MISSING markers to stderr so a human sees them.
REQUIRED_FILES=(
    transcript.md
    raw_stream.jsonl
    cold_start.json
    tokens.json
    tls.json
    stability.log
    orphan_audit.log
    tools_inventory.json
)
echo "==> evidence-directory audit:" >&2
for f in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$OUT_DIR/$f" ]]; then
        echo "    OK      $f" >&2
    else
        echo "    MISSING $f" >&2
    fi
done

# ─── 19. Cleanup + exit ─────────────────────────────────────────────────

cleanup_fixtures

echo "==> done: $OUT_DIR" >&2
exit "$CLAUDE_RC"
