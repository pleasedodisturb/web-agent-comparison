#!/usr/bin/env bash
#
# test_provenance_complete.sh — grep-based audit asserting that every
# v1.1 fixture under fixtures/snapshots/ has a PROVENANCE.md with the
# 5 required v1.1 fields:
#
#   1. Source URL (or "Source:" for synthetic fixtures)
#   2. License
#   3. Agent-task tag    (DESIGN-03)
#   4. Rendering archetype  (FAIRNESS-08)
#   5. Scrub log            (either "Scrubbing applied:" or "Scrub log:")
#
# v1.0 fixtures (greenhouse_2026-05-22, ashby_2026-05-22) pre-date the
# v1.1 schema and are skipped — they keep their original 2-field
# (Source URL + capture date) provenance shape.
#
# Exit codes:
#   0 — every v1.1 fixture PROVENANCE.md has all 5 fields, OR no v1.1
#       fixtures exist yet (Wave 0 / pre-Wave-1 state)
#   1 — at least one v1.1 fixture PROVENANCE.md is missing a field, or
#       a v1.1 fixture dir has no PROVENANCE.md at all

set -euo pipefail
IFS=$'\n\t'

repo_root=$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)
snapshots_root="$repo_root/fixtures/snapshots"

if [ ! -d "$snapshots_root" ]; then
    echo "FAIL: $snapshots_root does not exist" >&2
    exit 1
fi

# v1.0 fixtures that predate the v1.1 PROVENANCE.md schema. These keep
# their original 2-field shape and are exempt from the audit.
v10_skip=(
    "greenhouse_2026-05-22"
    "ashby_2026-05-22"
)

is_v10_skip() {
    local name="$1"
    for skip in "${v10_skip[@]}"; do
        if [ "$name" = "$skip" ]; then
            return 0
        fi
    done
    return 1
}

failures=0
v11_fixtures_checked=0

# Iterate every direct child of fixtures/snapshots/ that has the v1.1
# slug shape (starts with "s" followed by a digit). The v1.0 dirs
# (greenhouse_*, ashby_*) are skipped by the prefix filter even before
# the explicit skip-list check.
shopt -s nullglob
for dir in "$snapshots_root"/*/; do
    name=$(basename "$dir")

    if is_v10_skip "$name"; then
        continue
    fi

    # Only audit v1.1-shaped slugs (sNN_*). Anything else is unexpected
    # and a planning bug — flag it so untracked fixtures don't sneak in.
    if ! [[ "$name" =~ ^s[0-9] ]]; then
        echo "WARN: unrecognised fixture dir (not v1.0, not v1.1-shaped): $name" >&2
        continue
    fi

    prov="$dir/PROVENANCE.md"
    if [ ! -f "$prov" ]; then
        echo "FAIL: $name: missing PROVENANCE.md" >&2
        failures=$((failures + 1))
        continue
    fi

    # Field 1: Source URL or Source: line
    if ! grep -qE "^\*?\*?(Source URL|Source):" "$prov"; then
        echo "FAIL: $prov: missing 'Source URL' or 'Source:' field" >&2
        failures=$((failures + 1))
    fi

    # Field 2: License (case-sensitive on the keyword, flexible on bullet
    # formatting).
    if ! grep -qE "^\*?\*?License:" "$prov"; then
        echo "FAIL: $prov: missing 'License:' field" >&2
        failures=$((failures + 1))
    fi

    # Field 3: Agent-task tag (DESIGN-03). Accept either 'Agent-task tag'
    # or 'Agent task tag' since PATTERNS.md uses both spellings.
    if ! grep -qE "Agent[- ]task tag" "$prov"; then
        echo "FAIL: $prov: missing 'Agent-task tag' field (DESIGN-03)" >&2
        failures=$((failures + 1))
    fi

    # Field 4: Rendering archetype (FAIRNESS-08).
    if ! grep -qE "Rendering archetype" "$prov"; then
        echo "FAIL: $prov: missing 'Rendering archetype' field (FAIRNESS-08)" >&2
        failures=$((failures + 1))
    fi

    # Field 5: Scrub log indicator — either 'Scrubbing applied:' (v1.0
    # template) or 'Scrub log:' (v1.1 shorthand).
    if ! grep -qE "(Scrubbing applied:|Scrub log:)" "$prov"; then
        echo "FAIL: $prov: missing 'Scrubbing applied:' or 'Scrub log:' field" >&2
        failures=$((failures + 1))
    fi

    v11_fixtures_checked=$((v11_fixtures_checked + 1))
done
shopt -u nullglob

if [ "$failures" -gt 0 ]; then
    echo "test_provenance_complete.sh: $failures field-miss(es) across v1.1 fixtures." >&2
    exit 1
fi

if [ "$v11_fixtures_checked" -eq 0 ]; then
    echo "test_provenance_complete.sh: no v1.1 fixtures present yet (Wave 0 state). OK."
else
    echo "test_provenance_complete.sh: $v11_fixtures_checked v1.1 fixture(s) checked, all 5-field complete."
fi
exit 0
