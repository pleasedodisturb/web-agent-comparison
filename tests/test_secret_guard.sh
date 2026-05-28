#!/usr/bin/env bash
# test_secret_guard.sh — exercise scripts/hooks/pre-commit against fixture
# .mcp.json files. Confirms (a) inline secret is rejected, (b) ${VAR}
# reference passes.
#
# Builds a throwaway scratch git repo, copies in the hook + a fixture
# .mcp.json, attempts a real commit, asserts on the exit code and stderr.
#
# Exit codes:
#   0 — both cases passed
#   1 — at least one case failed

set -euo pipefail

repo_root=$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)
hook_src="$repo_root/scripts/hooks/pre-commit"

if [ ! -x "$hook_src" ]; then
    echo "FAIL: $hook_src missing or not executable" >&2
    exit 1
fi

# Sanity: fixture files for both cases. Use heredocs into the scratch repos —
# we never commit the inline-secret fixture in the real repo (the hook would
# block it!). Note: $$ is intentional to suppress shell-substitution in the
# fixture's ${FIRECRAWL_API_KEY} string.
INLINE_SECRET_FIXTURE='{
  "mcpServers": {
    "firecrawl": {
      "command": "firecrawl-mcp",
      "env": { "FIRECRAWL_API_KEY": "fc-1234567890abcdefghij1234567890" }
    }
  }
}'

ENV_REF_FIXTURE='{
  "mcpServers": {
    "firecrawl": {
      "command": "firecrawl-mcp",
      "env": { "FIRECRAWL_API_KEY": "${FIRECRAWL_API_KEY}" }
    }
  }
}'

# Helper: set up a scratch git repo with the hook installed.
setup_scratch_repo() {
    local dir="$1"
    git init -q "$dir"
    # Use main as default branch; older git versions default to master.
    git -C "$dir" symbolic-ref HEAD refs/heads/main 2>/dev/null || true
    # Configure a committer identity so `git commit` doesn't refuse.
    git -C "$dir" config user.email "test@example.com"
    git -C "$dir" config user.name "Test User"
    # Disable signing for the scratch repo (the real repo signs commits, but
    # the test only cares about the hook's behavior).
    git -C "$dir" config commit.gpgsign false
    mkdir -p "$dir/.git/hooks"
    cp "$hook_src" "$dir/.git/hooks/pre-commit"
    chmod +x "$dir/.git/hooks/pre-commit"
}

scratch=$(mktemp -d -t secret-guard-test-XXXXXX)
trap 'rm -rf "$scratch"' EXIT

failures=0

# ─── Case A: inline secret → must be rejected ───────────────────────────────
case_a="$scratch/case_a"
setup_scratch_repo "$case_a"
printf '%s\n' "$INLINE_SECRET_FIXTURE" > "$case_a/.mcp.json"
git -C "$case_a" add .mcp.json

set +e
commit_out=$(git -C "$case_a" commit -m "test: inline-secret should be rejected" 2>&1)
commit_rc=$?
set -e

if [ "$commit_rc" -eq 0 ]; then
    echo "FAIL [case A: inline secret]: commit succeeded (rc=0); expected rejection." >&2
    echo "----- commit output -----" >&2
    echo "$commit_out" >&2
    echo "-------------------------" >&2
    failures=$((failures + 1))
elif ! echo "$commit_out" | grep -q "Inline secret detected"; then
    echo "FAIL [case A: inline secret]: rejected (rc=$commit_rc) but expected message missing." >&2
    echo "----- commit output -----" >&2
    echo "$commit_out" >&2
    echo "-------------------------" >&2
    failures=$((failures + 1))
else
    echo "PASS [case A: inline secret] — rejected with expected message (rc=$commit_rc)."
fi

# ─── Case B: ${VAR} reference → must be accepted ────────────────────────────
case_b="$scratch/case_b"
setup_scratch_repo "$case_b"
printf '%s\n' "$ENV_REF_FIXTURE" > "$case_b/.mcp.json"
git -C "$case_b" add .mcp.json

set +e
commit_out_b=$(git -C "$case_b" commit -m "test: env-ref should pass" 2>&1)
commit_rc_b=$?
set -e

if [ "$commit_rc_b" -ne 0 ]; then
    echo "FAIL [case B: env-ref]: commit rejected (rc=$commit_rc_b); expected pass." >&2
    echo "----- commit output -----" >&2
    echo "$commit_out_b" >&2
    echo "-------------------------" >&2
    failures=$((failures + 1))
else
    echo "PASS [case B: env-ref] — commit accepted (rc=$commit_rc_b)."
fi

if [ "$failures" -gt 0 ]; then
    echo "test_secret_guard.sh: $failures case(s) failed." >&2
    exit 1
fi

echo "test_secret_guard.sh: all cases passed."
exit 0
