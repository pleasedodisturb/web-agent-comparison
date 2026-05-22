#!/usr/bin/env bash
#
# check_prereqs.sh — prerequisite gate for the web-agent-comparison harness.
#
# Reads the 7 MCP entries from .mcp.json (via jq), verifies that each MCP's
# command is on PATH, plus a short list of host tools the harness itself
# needs (jq, node, npm, python3, uv, envsubst, wget).
#
# Exits non-zero on any miss with a one-line remediation per gap so the
# `make bench` pipeline fails loud with actionable output (per HARNESS-06).
#
# Portability: stick to bash 5 + POSIX-ish flags. NO gdate / gawk / GNU-only
# extensions — third-party reproducibility matters here (PROJECT.md).
#
# FIRECRAWL_API_KEY is a WARNING (not an error) since partial-run 6/7 is
# acceptable per PROJECT.md.

set -euo pipefail
IFS=$'\n\t'

# Resolve repo root from this script's location so the gate works regardless
# of the caller's cwd. (Make invokes it from repo root, but humans don't.)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MCP_JSON="$REPO_ROOT/.mcp.json"

MISSING=0
WARNINGS=0

say_missing() {
    # $1 = binary name, $2 = remediation string
    printf '%s: missing — install with: %s\n' "$1" "$2" >&2
    MISSING=$((MISSING + 1))
}

say_warning() {
    # $1 = subject, $2 = remediation/note
    printf '%s: WARNING — %s\n' "$1" "$2" >&2
    WARNINGS=$((WARNINGS + 1))
}

# Per-MCP remediation strings (RESEARCH §1 pinned versions).
remediation_for() {
    case "$1" in
        playwright)        echo 'npm install -g @playwright/mcp@0.0.75' ;;
        browser-use)       echo 'uv tool install browser-use==0.12.7' ;;
        chrome-devtools)   echo 'npm install -g chrome-devtools-mcp@1.0.1' ;;
        lightpanda)        echo 'download from github.com/lightpanda-io/browser/releases (nightly@2026-05-22 or v0.2.6)' ;;
        obscura)           echo 'npm install -g obscura-mcp@0.1.4-3 && obscura-mcp install' ;;
        firecrawl)         echo 'npm install -g firecrawl-mcp@3.17.0  (also needs FIRECRAWL_API_KEY)' ;;
        cloakbrowser)      echo 'uv tool install cloakbrowsermcp==2.0.4' ;;
        *)                 echo "unknown MCP '$1' — check .mcp.json and add a remediation entry" ;;
    esac
}

# Host-tool remediation strings (Homebrew defaults; documented for the README).
host_remediation_for() {
    case "$1" in
        jq)         echo 'brew install jq' ;;
        node)       echo 'brew install node@22  (then: brew link --overwrite --force node@22)' ;;
        npm)        echo 'comes with node@22 — install node first' ;;
        python3)    echo 'brew install python@3.12  (or rely on uv to manage 3.12)' ;;
        uv)         echo 'brew install uv  (or: curl -LsSf https://astral.sh/uv/install.sh | sh)' ;;
        envsubst)   echo 'brew install gettext && brew link --force gettext  (Apple base ships no envsubst)' ;;
        wget)       echo 'brew install wget  (needed by snapshot capture in plan 01-03)' ;;
        *)          echo "host tool '$1' — see README.md or .planning/research/STACK.md for install pointers" ;;
    esac
}

# 1. Host tools — checked before the MCPs because they're cheaper to remediate
#    and a missing jq would prevent the .mcp.json read below.
echo "==> Checking host tools" >&2
for tool in jq node npm python3 uv envsubst wget; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        say_missing "$tool" "$(host_remediation_for "$tool")"
    fi
done

# Bail early if jq is missing — the rest of the script needs it.
if ! command -v jq >/dev/null 2>&1; then
    echo "check_prereqs: $MISSING missing (cannot continue without jq)" >&2
    exit 1
fi

# 2. .mcp.json must exist and parse cleanly.
if [[ ! -f "$MCP_JSON" ]]; then
    echo ".mcp.json: missing at $MCP_JSON" >&2
    MISSING=$((MISSING + 1))
    echo "check_prereqs: $MISSING missing" >&2
    exit 1
fi
if ! jq -e . "$MCP_JSON" >/dev/null 2>&1; then
    echo ".mcp.json: invalid JSON at $MCP_JSON" >&2
    MISSING=$((MISSING + 1))
    echo "check_prereqs: $MISSING missing" >&2
    exit 1
fi

# 3. Each MCP's .command field must be on PATH.
echo "==> Checking MCP binaries from .mcp.json" >&2
while IFS= read -r mcp; do
    cmd=$(jq -r --arg m "$mcp" '.mcpServers[$m].command' "$MCP_JSON")
    if [[ -z "$cmd" || "$cmd" == "null" ]]; then
        say_missing "$mcp" "missing .command field in .mcp.json"
        continue
    fi
    if ! command -v "$cmd" >/dev/null 2>&1; then
        say_missing "$cmd" "$(remediation_for "$mcp")"
    fi
done < <(jq -r '.mcpServers | keys[]' "$MCP_JSON")

# 4. FIRECRAWL_API_KEY is a soft requirement — partial 6/7 acceptable per PROJECT.md.
if [[ -z "${FIRECRAWL_API_KEY:-}" ]]; then
    say_warning "FIRECRAWL_API_KEY" "unset — firecrawl will be scored as SKIPPED (6/7 partial run is acceptable per PROJECT.md)"
fi

# 5. Summary.
if (( MISSING > 0 )); then
    echo "check_prereqs: $MISSING missing, $WARNINGS warning(s)" >&2
    exit 1
fi
echo "check_prereqs: ok ($WARNINGS warning(s))"
exit 0
