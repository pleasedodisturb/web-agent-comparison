#!/usr/bin/env bash
#
# test_run_mcp_session_evidence_dir.sh — directly verify the plan 01-06
# evidence-directory wiring in scripts/run_mcp_session.sh.
#
# Plan 01-06 added five post-Claude steps to run_mcp_session.sh:
#   13. tokens.json   (jq-derived from raw_stream.jsonl)
#   14. tools_inventory.json   (real probe via bench.tools_inventory)
#   15. tls.json / cold_start.json / stability.log   (stubs)
#   16. results/$DATE/versions.json + versions.lock.md
#   17. results/$DATE/MACHINE.md
#   18. final missing-file audit (log-only)
#
# This test DOES NOT invoke the run_mcp_session.sh wrapper end-to-end
# (which would spawn Claude Code and cost an API call). Instead, it
# directly invokes each Python module against a tempdir to confirm:
#
#   (a) every module the wrapper calls is importable and exits 0
#   (b) every file the wrapper expects to write actually gets written
#       with the documented shape
#
# The integration smoke test in test_run_mcp_session_smoke.sh covers the
# end-to-end path when WAC_SMOKE_RUN=1 is set; this script is the no-cost
# always-runnable companion.
#
# Run:
#   bash tests/test_run_mcp_session_evidence_dir.sh
#
# Exit codes:
#   0 — all assertions passed
#   1 — one or more assertions failed
#   2 — preconditions not met

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ─── Preconditions ──────────────────────────────────────────────────────

VENV_PY="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    echo "preconditions: $VENV_PY missing — run uv sync first" >&2
    exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "preconditions: jq required for the tokens.json pipeline" >&2
    exit 2
fi

if [[ ! -f templates/MACHINE.md ]]; then
    echo "preconditions: templates/MACHINE.md missing" >&2
    exit 2
fi

# ─── Setup ──────────────────────────────────────────────────────────────

TMPROOT=$(mktemp -d)
trap 'rm -rf "$TMPROOT"' EXIT

DATE="2099-12-31"   # synthetic future date so we don't collide with real runs
OUT_DIR="$TMPROOT/$DATE/playwright"
mkdir -p "$OUT_DIR"

# ─── Assertion helper ───────────────────────────────────────────────────

FAIL=0
ok() { echo "  OK: $1"; }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }

assert_file_exists() {
    [[ -f "$1" ]] && ok "exists: $1" || fail "missing: $1"
}

assert_json_has_key() {
    local path="$1" key="$2"
    if ! jq -e ".$key" "$path" >/dev/null 2>&1; then
        fail "$path: missing key .$key"
    else
        ok "$path: has key .$key"
    fi
}

# ─── 1. tokens.json pipeline (the jq one-liner from step 13) ────────────

echo "==> tokens.json pipeline"
# Synthesize a raw_stream.jsonl with a single result.usage block.
cat > "$OUT_DIR/raw_stream.jsonl" <<'EOF'
{"type":"system","subtype":"init","session_id":"abc"}
{"type":"assistant","message":{"content":[{"type":"text","text":"hi"}]}}
{"type":"result","subtype":"end","usage":{"input_tokens":10,"output_tokens":20}}
EOF

USAGE_BLOCK=$(jq -c '[inputs | select(.type=="result") | .usage] | last // {}' \
    < "$OUT_DIR/raw_stream.jsonl")
cat > "$OUT_DIR/tokens.json" <<TOKENS_EOF
{
  "mcp": "playwright",
  "scope": "turn",
  "deferred": "phase-3",
  "reason": "test",
  "turn": ${USAGE_BLOCK},
  "schema_bytes": null,
  "payload_bytes": null
}
TOKENS_EOF

assert_file_exists "$OUT_DIR/tokens.json"
assert_json_has_key "$OUT_DIR/tokens.json" "turn"
assert_json_has_key "$OUT_DIR/tokens.json" "turn.input_tokens"
assert_json_has_key "$OUT_DIR/tokens.json" "deferred"

# ─── 2. stub_writers (step 15) ──────────────────────────────────────────

echo "==> stub_writers"
"$VENV_PY" -m bench.stub_writers "$OUT_DIR" --mcp-name playwright >/dev/null 2>&1
assert_file_exists "$OUT_DIR/tls.json"
assert_file_exists "$OUT_DIR/cold_start.json"
assert_file_exists "$OUT_DIR/stability.log"
assert_json_has_key "$OUT_DIR/tls.json" "deferred"
assert_json_has_key "$OUT_DIR/cold_start.json" "deferred"
grep -q "STUB" "$OUT_DIR/stability.log" && ok "stability.log mentions STUB" \
    || fail "stability.log missing STUB marker"

# ─── 3. tools_inventory (step 14) ───────────────────────────────────────
# We can't actually spawn playwright-mcp without committing to a real
# 30 s budget here. The bench.tools_inventory unit tests cover the
# spawn path. For THIS test we point at an unspawnable binary so the
# wrapper records a non-zero exit and a status field; we just verify
# the file gets written.

echo "==> tools_inventory (failure-path coverage)"
SYNTH_CFG="$TMPROOT/.mcp.synth.json"
cat > "$SYNTH_CFG" <<EOF
{
  "mcpServers": {
    "broken": {"command": "/bin/false", "args": []}
  }
}
EOF
"$VENV_PY" -m bench.tools_inventory broken \
    --mcp-json "$SYNTH_CFG" \
    --out "$OUT_DIR/tools_inventory.json" \
    --timeout-s 3 >/dev/null 2>&1 || true
assert_file_exists "$OUT_DIR/tools_inventory.json"
assert_json_has_key "$OUT_DIR/tools_inventory.json" "status"

# ─── 4. capture_versions (step 16) ──────────────────────────────────────

echo "==> capture_versions"
"$VENV_PY" -m bench.capture_versions \
    --date "$DATE" \
    --results-root "$TMPROOT" >/dev/null 2>&1
assert_file_exists "$TMPROOT/$DATE/versions.json"
assert_file_exists "$TMPROOT/$DATE/versions.lock.md"
assert_json_has_key "$TMPROOT/$DATE/versions.json" "host"
assert_json_has_key "$TMPROOT/$DATE/versions.json" "tooling"
assert_json_has_key "$TMPROOT/$DATE/versions.json" "mcps"
grep -q "Reproducibility Manifest" "$TMPROOT/$DATE/versions.lock.md" \
    && ok "versions.lock.md has header" \
    || fail "versions.lock.md missing header"

# ─── 5. MACHINE.md rendering (step 17) ──────────────────────────────────

echo "==> MACHINE.md"
export DATE
export CAPTURED_AT_UTC="$(jq -r '.captured_at // ""' "$TMPROOT/$DATE/versions.json")"
export HOST_OS="$(jq -r '.host.os // ""' "$TMPROOT/$DATE/versions.json")"
export HOST_KERNEL="$(jq -r '.host.kernel_version // ""' "$TMPROOT/$DATE/versions.json")"
export HOST_ARCH="$(jq -r '.host.arch // ""' "$TMPROOT/$DATE/versions.json")"
export MACOS_VERSION="$(jq -r '.host.macos_version // ""' "$TMPROOT/$DATE/versions.json")"
export CLAUDE_VERSION="$(jq -r '.tooling.claude_code // ""' "$TMPROOT/$DATE/versions.json")"
export NODE_VERSION="$(jq -r '.tooling.node // ""' "$TMPROOT/$DATE/versions.json")"
export NPM_VERSION="$(jq -r '.tooling.npm // ""' "$TMPROOT/$DATE/versions.json")"
export PYTHON_VERSION="$(jq -r '.tooling.python // ""' "$TMPROOT/$DATE/versions.json")"
export UV_VERSION="$(jq -r '.tooling.uv // ""' "$TMPROOT/$DATE/versions.json")"
envsubst < templates/MACHINE.md > "$TMPROOT/$DATE/MACHINE.md"
assert_file_exists "$TMPROOT/$DATE/MACHINE.md"
# After envsubst, ${VAR} placeholders should be gone (replaced or empty).
if grep -E '\$\{[A-Z_]+\}' "$TMPROOT/$DATE/MACHINE.md" >/dev/null; then
    fail "MACHINE.md contains unresolved \${VAR} placeholders"
else
    ok "MACHINE.md placeholders all resolved"
fi
# Specifically: the date placeholder MUST have been resolved.
grep -q "$DATE" "$TMPROOT/$DATE/MACHINE.md" \
    && ok "MACHINE.md contains date $DATE" \
    || fail "MACHINE.md missing date"

# ─── 6. Public-repo hygiene check ───────────────────────────────────────
# CLAUDE.md mandates no PII in evidence artifacts. Spot-check for the
# common slips.

echo "==> public-repo hygiene"
for f in "$TMPROOT/$DATE/versions.json" "$TMPROOT/$DATE/MACHINE.md"; do
    # macOS host names commonly look like "<First>'s MacBook".
    if grep -Eq "MacBook|iMac|Mini" "$f" 2>/dev/null; then
        fail "$f contains a macOS device-name pattern"
    fi
    # User-level absolute paths should be ~-collapsed.
    if grep -q "/Users/" "$f" 2>/dev/null; then
        fail "$f contains an uncollapsed /Users/ path"
    fi
done
ok "no macOS device-name or /Users/ paths found"

# ─── Summary ────────────────────────────────────────────────────────────

if (( FAIL > 0 )); then
    echo "test_run_mcp_session_evidence_dir: $FAIL assertion(s) failed" >&2
    exit 1
fi
echo "test_run_mcp_session_evidence_dir: PASSED" >&2
exit 0
