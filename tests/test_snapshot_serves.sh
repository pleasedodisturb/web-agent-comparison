#!/usr/bin/env bash
#
# test_snapshot_serves.sh — end-to-end check that the local fixture HTTP
# server boots cleanly and returns non-trivial content for both
# committed snapshots.
#
# Exit codes:
#   0 — both snapshots serve a non-empty response with HTTP 200
#   1 — start failed, curl failed, body too small, or stop failed
#
# Trap-exit always tears the server down so a failed run never leaves
# a server orphaned on port 8765.

set -euo pipefail
IFS=$'\n\t'

repo_root=$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)
serve_script="$repo_root/scripts/serve_fixtures.sh"
date_tag="2026-05-22"

if [ ! -x "$serve_script" ]; then
    echo "FAIL: $serve_script missing or not executable" >&2
    exit 1
fi

# Snapshot dirs the harness expects to exist before this test runs.
expected_dirs=(
    "$repo_root/fixtures/snapshots/greenhouse_${date_tag}"
    "$repo_root/fixtures/snapshots/ashby_${date_tag}"
)
for d in "${expected_dirs[@]}"; do
    if [ ! -d "$d" ]; then
        echo "FAIL: missing snapshot dir $d — run scripts/snapshot_fixtures.sh first" >&2
        exit 1
    fi
done

# Make sure the test starts from a known-stopped state. `stop` is
# idempotent so this is always safe.
"$serve_script" stop >/dev/null 2>&1 || true

trap '"$serve_script" stop >/dev/null 2>&1 || true' EXIT

if ! "$serve_script" start; then
    echo "FAIL: serve_fixtures.sh start did not succeed" >&2
    exit 1
fi

failures=0

check_url() {
    local label="$1"
    local url="$2"
    local min_bytes="$3"

    local body_file
    body_file=$(mktemp -t snapshot-serve-XXXXXX)
    local http_code
    http_code=$(curl -fsS -o "$body_file" -w "%{http_code}" --connect-timeout 2 --max-time 5 "$url" 2>/dev/null || echo "000")
    local body_size
    body_size=$(wc -c < "$body_file" | tr -d ' ')
    rm -f "$body_file"

    if [ "$http_code" != "200" ]; then
        echo "FAIL [$label]: HTTP $http_code from $url" >&2
        failures=$((failures + 1))
        return
    fi
    if [ "$body_size" -lt "$min_bytes" ]; then
        echo "FAIL [$label]: body size $body_size < expected min $min_bytes" >&2
        failures=$((failures + 1))
        return
    fi
    echo "PASS [$label] — HTTP 200, $body_size bytes"
}

# Index pages return Python's auto-generated directory listing (~300-500
# bytes — small but non-zero). Threshold 200 confirms we got a real
# listing back, not an empty body. The primary HTML files below are the
# substantive content check (Greenhouse ~84KB, Ashby ~6KB).
check_url "greenhouse index" \
    "http://127.0.0.1:8765/greenhouse_${date_tag}/" \
    200
check_url "ashby index" \
    "http://127.0.0.1:8765/ashby_${date_tag}/" \
    200

# Confirm the primary HTML files are reachable at their captured paths
# (i.e. the SHA256-anchored served-content tree is intact). Greenhouse
# is server-rendered HTML (~80KB+); Ashby is the SPA shell (~5KB+ given
# the loading-spinner CSS); a 4KB floor catches genuine truncation.
check_url "greenhouse primary" \
    "http://127.0.0.1:8765/greenhouse_${date_tag}/anthropic/jobs/5023394008.html" \
    4096
check_url "ashby primary" \
    "http://127.0.0.1:8765/ashby_${date_tag}/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html" \
    4096

# Stop the server (the trap will also try, but doing it here lets us
# verify the stop subcommand exits 0 on a running server).
if ! "$serve_script" stop; then
    echo "FAIL: serve_fixtures.sh stop did not succeed on a running server" >&2
    failures=$((failures + 1))
fi

# Idempotent second stop must be a no-op (rc=0).
if ! "$serve_script" stop; then
    echo "FAIL: serve_fixtures.sh stop is not idempotent (second call non-zero)" >&2
    failures=$((failures + 1))
fi

if [ "$failures" -gt 0 ]; then
    echo "test_snapshot_serves.sh: $failures case(s) failed." >&2
    exit 1
fi

echo "test_snapshot_serves.sh: all cases passed."
exit 0
