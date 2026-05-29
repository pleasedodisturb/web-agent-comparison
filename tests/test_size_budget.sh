#!/usr/bin/env bash
#
# test_size_budget.sh — enforces the v1.1 size budget on
# fixtures/snapshots/ per REPRO-11:
#
#   - Total tree:    du -ks fixtures/snapshots/  must be <= 51200 KB (50 MB)
#   - Each child:    du -ks fixtures/snapshots/*/ must be <= 5120 KB (5 MB)
#
# Per Phase 6 CONTEXT.md stop condition #4: "du -sh fixtures/snapshots/
# <= 50 MB". The 5-MB-per-fixture sub-cap comes from VALIDATION.md Wave 0
# Requirements bullet 3. Both caps must pass for the suite to be green.
#
# Exit codes:
#   0 — both caps respected
#   1 — total tree > 50 MB, OR any direct child > 5 MB
#
# Uses `du -ks` (kilobytes, summary) so the math is portable across
# macOS and Linux without parsing human-readable suffixes.

set -euo pipefail
IFS=$'\n\t'

repo_root=$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)
snapshots_root="$repo_root/fixtures/snapshots"

# 50 MB cap (total) and 5 MB cap (per-fixture) expressed in KB.
TOTAL_CAP_KB=51200
PER_FIXTURE_CAP_KB=5120

if [ ! -d "$snapshots_root" ]; then
    echo "FAIL: $snapshots_root does not exist" >&2
    exit 1
fi

failures=0

# Step 1: total tree.
total_kb=$(du -ks "$snapshots_root" | awk '{print $1}')
if [ "$total_kb" -gt "$TOTAL_CAP_KB" ]; then
    echo "FAIL: total size $total_kb KB exceeds 50 MB cap (${TOTAL_CAP_KB} KB)" >&2
    failures=$((failures + 1))
else
    echo "PASS: total size $total_kb KB <= ${TOTAL_CAP_KB} KB (50 MB)"
fi

# Step 2: per-direct-child.
shopt -s nullglob
for dir in "$snapshots_root"/*/; do
    name=$(basename "$dir")
    child_kb=$(du -ks "$dir" | awk '{print $1}')
    if [ "$child_kb" -gt "$PER_FIXTURE_CAP_KB" ]; then
        echo "FAIL: $name: $child_kb KB exceeds 5 MB per-fixture cap (${PER_FIXTURE_CAP_KB} KB)" >&2
        failures=$((failures + 1))
    else
        echo "PASS: $name: $child_kb KB <= ${PER_FIXTURE_CAP_KB} KB (5 MB)"
    fi
done
shopt -u nullglob

if [ "$failures" -gt 0 ]; then
    echo "test_size_budget.sh: $failures cap violation(s)." >&2
    exit 1
fi

echo "test_size_budget.sh: all size caps respected."
exit 0
