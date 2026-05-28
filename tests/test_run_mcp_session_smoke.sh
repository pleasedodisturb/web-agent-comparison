#!/usr/bin/env bash
#
# test_run_mcp_session_smoke.sh — smoke test for scripts/run_mcp_session.sh.
#
# Exercises the driver against the playwright MCP using a tiny "say hello"
# prompt that the smoke fixture provides (tests/fixtures/hello_prompt.md).
# The smoke prompt instructs Claude Code to Write a one-word file and
# stop — no actual MCP tool calls are made, so the test costs ~1 API
# call's worth of tokens and finishes in ~30s.
#
# Default behaviour: SKIP the test unless WAC_SMOKE_RUN=1 is set in the
# environment. The test makes a real Claude Code API call, which (a)
# costs money and (b) requires a working Claude Code installation. CI
# pipelines that can pay for it set WAC_SMOKE_RUN=1; local dev runs
# default to skip.
#
# Run manually:
#   WAC_SMOKE_RUN=1 bash tests/test_run_mcp_session_smoke.sh
#
# Exit codes:
#   0 — test passed (or skipped via WAC_SMOKE_RUN!=1)
#   1 — test failed
#   2 — preconditions not met (e.g. .venv missing)

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ─── Gate ───────────────────────────────────────────────────────────────

if [[ "${WAC_SMOKE_RUN:-0}" != "1" ]]; then
    echo "test_run_mcp_session_smoke: SKIPPED (set WAC_SMOKE_RUN=1 to run)" >&2
    exit 0
fi

# ─── Preconditions ──────────────────────────────────────────────────────

if [[ ! -x scripts/run_mcp_session.sh ]]; then
    echo "test_run_mcp_session_smoke: scripts/run_mcp_session.sh missing or not executable" >&2
    exit 2
fi

if [[ ! -f tests/fixtures/hello_prompt.md ]]; then
    echo "test_run_mcp_session_smoke: hello_prompt.md fixture missing" >&2
    exit 2
fi

if ! command -v claude >/dev/null 2>&1; then
    echo "test_run_mcp_session_smoke: claude CLI not on PATH" >&2
    exit 2
fi

# ─── Setup ──────────────────────────────────────────────────────────────

DATE="$(date -u +%Y-%m-%d)"
EXPECTED_OUT="results/${DATE}/playwright"

# Wipe any prior smoke-run artifacts so the assertions below start clean.
# We don't `rm -rf results/` (that would nuke real benchmark runs); we
# only clear the playwright subdir for today's date.
if [[ -d "$EXPECTED_OUT" ]]; then
    rm -rf "$EXPECTED_OUT"
fi

# ─── Run ────────────────────────────────────────────────────────────────

echo "==> running scripts/run_mcp_session.sh playwright (smoke prompt)" >&2
STAGE_WALK_PATH=tests/fixtures/hello_prompt.md \
    scripts/run_mcp_session.sh playwright

# ─── Assertions ─────────────────────────────────────────────────────────

FAIL=0
check_file_nonempty() {
    if [[ ! -s "$1" ]]; then
        echo "FAIL: $1 is missing or empty" >&2
        FAIL=$((FAIL + 1))
    else
        echo "  OK: $1 exists and is non-empty" >&2
    fi
}

check_file_contains() {
    # $1 = path, $2 = substring
    if [[ ! -f "$1" ]]; then
        echo "FAIL: $1 missing" >&2
        FAIL=$((FAIL + 1))
        return
    fi
    if ! grep -qF "$2" "$1"; then
        echo "FAIL: $1 does not contain '$2'" >&2
        FAIL=$((FAIL + 1))
    else
        echo "  OK: $1 contains '$2'" >&2
    fi
}

check_file_contains "$EXPECTED_OUT/stage_s1.md" "hello"
check_file_nonempty "$EXPECTED_OUT/raw_stream.jsonl"
check_file_nonempty "$EXPECTED_OUT/orphan_audit.log"

# Fairness contract assertion: no WebFetch tool_use in the stream.
if grep -q '"name":"WebFetch"' "$EXPECTED_OUT/raw_stream.jsonl"; then
    echo "FAIL: raw_stream.jsonl contains a WebFetch tool_use (fairness contract violation)" >&2
    FAIL=$((FAIL + 1))
else
    echo "  OK: no WebFetch tool_use in raw_stream.jsonl" >&2
fi

if (( FAIL > 0 )); then
    echo "test_run_mcp_session_smoke: $FAIL assertion(s) failed" >&2
    exit 1
fi
echo "test_run_mcp_session_smoke: PASSED" >&2
exit 0
