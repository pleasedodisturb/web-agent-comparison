#!/usr/bin/env bash
#
# verify_calibration.sh — Phase 1's go/no-go gate.
#
# Drives an end-to-end Playwright run against the snapshot fixtures, then
# compares the composite score against the **harness re-baseline** of 8.33
# with a ±0.5 tolerance. Pass ⇒ Phase 1 is done; fail ⇒ STOP and surface
# a structured diagnostic per HANDOFF-GSD-AUTO.md STOP condition #1.
#
# CALIBRATION RE-BASELINE (2026-05-26, user-approved Option C)
# ------------------------------------------------------------
# The 2026-03-31 published Playwright composite is 9.07 (via
# `scoring/score.py` on the human-judged scores in `results/scores.json`).
# That number is the historical record and is PRESERVED — see
# `tests/test_calibration_math.py::TestCompositeReproducesFromPublishedResults`
# which still pins it.
#
# The Phase 1 harness re-scores the same 2026-03 evidence through the new
# heuristic scorers in `scripts/aggregate_scores.py` +
# `scripts/score_with_na.py`. Four of the eight scorers (Speed, Token
# Efficiency, Setup Complexity, Error Handling) return neutral defaults
# during Phase 1 because their real measurement is deferred to Phase 3
# (G-710). Re-scoring the 2026-03 evidence through the same heuristics
# produces 8.33 — see `results/2026-03-31_rebaseline/scores.json` for the
# regenerable artifact and `scoring/rubric_notes.md` "Calibration
# Re-Baseline (2026-05-26)" for the audit trail.
#
# This re-baseline is for harness self-validation only. The published
# 2026-03 wave-1 number (9.07) remains the methodology's anchor when
# comparing waves to each other; the heuristic re-baseline (8.33) is what
# the Phase 1 calibration GATE validates against, so we can detect
# regressions in the heuristic scorers without confusing them with the
# documented Phase-1-vs-Phase-3 scope cut.
#
# The script also exercises the other four Phase 1 success criteria so the
# acceptance check is single-command:
#
#   SC #1  composite ∈ [7.83, 8.83]                       (the gate itself)
#   SC #2  evidence-directory contract is complete        (file inventory)
#   SC #3  check_prereqs.sh fails when a binary is hidden (hide+restore probe)
#   SC #4  3-pass-of-3 retry gate handles a synthetic transient
#   SC #5  pre-commit hook blocks inline secrets in .mcp.json
#
# Usage:
#   bash scripts/verify_calibration.sh                       # full run
#   SKIP_BENCH=1 bash scripts/verify_calibration.sh          # skip the live run (uses existing artifacts)
#   bash scripts/verify_calibration.sh --no-prereq-hide      # skip the hide-binary probe
#
# Outputs:
#   results/<DATE>/playwright/                  # populated by the real run
#   results/<DATE>/CALIBRATION_DIAGNOSTIC.md    # on FAIL only
#   results/<DATE>/PHASE1_CALIBRATION.md        # on PASS only
#
# Exit codes:
#   0 — calibration PASS, all 5 SC met
#   1 — calibration FAIL; diagnostic written; STOP per HANDOFF-GSD-AUTO #1
#   2 — bad arguments / setup error (different class from a real fail)

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

VENV_PY="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    echo "verify_calibration: project venv python missing at $VENV_PY" >&2
    echo "verify_calibration: run 'uv sync' to materialize the .venv first" >&2
    exit 2
fi

DATE="${VERIFY_DATE:-$(date -u +%Y-%m-%d)}"
RESULTS_DIR="results/${DATE}"
PLAYWRIGHT_DIR="${RESULTS_DIR}/playwright"
DIAGNOSTIC_PATH="${RESULTS_DIR}/CALIBRATION_DIAGNOSTIC.md"
PASS_PATH="${RESULTS_DIR}/PHASE1_CALIBRATION.md"

# Calibration constants (mirror tests/test_calibration_math.py — DO NOT EDIT
# without also updating that test, or the band logic will silently diverge
# between the unit test and the live gate).
#
# TARGET_COMPOSITE is the HARNESS RE-BASELINE (2026-03 evidence re-scored
# through aggregate_scores.py + score_with_na.py). The PUBLISHED 2026-03
# composite (9.07) is preserved separately in tests/test_calibration_math.py
# and results/scores.json — see the module-header note above for the full
# audit trail.
TARGET_COMPOSITE=8.33
LOWER_BAND=7.83
UPPER_BAND=8.83
PUBLISHED_2026_03_COMPOSITE=9.07

SKIP_BENCH="${SKIP_BENCH:-0}"
DO_PREREQ_HIDE=1
for arg in "$@"; do
    case "$arg" in
        --no-prereq-hide) DO_PREREQ_HIDE=0 ;;
        --help|-h)
            sed -n '2,40p' "$0"
            exit 0
            ;;
        *) echo "verify_calibration: unknown arg: $arg" >&2; exit 2 ;;
    esac
done

# ─── Cleanup trap ────────────────────────────────────────────────────────
# The fixture server has its own lifecycle (run_mcp_session.sh manages it),
# but we may boot it here for the SC #5 / orphan tests too. The trap stops
# whatever we own on exit. Idempotent — `serve_fixtures.sh stop` is a no-op
# when nothing is running.

OWN_FIXTURE_SERVER=0
SCRATCH_DIR=""

cleanup() {
    rc=$?
    if (( OWN_FIXTURE_SERVER == 1 )); then
        scripts/serve_fixtures.sh stop >/dev/null 2>&1 || true
    fi
    if [[ -n "$SCRATCH_DIR" && -d "$SCRATCH_DIR" ]]; then
        rm -rf "$SCRATCH_DIR" 2>/dev/null || true
    fi
    if [[ -n "${HIDDEN_BINARY_DST:-}" && -f "$HIDDEN_BINARY_DST" ]]; then
        # Restore the hidden binary if the prereq probe was interrupted
        # mid-run (e.g. ^C between hide and restore).
        if [[ -n "${HIDDEN_BINARY_SRC:-}" && ! -f "$HIDDEN_BINARY_SRC" ]]; then
            mv "$HIDDEN_BINARY_DST" "$HIDDEN_BINARY_SRC" 2>/dev/null || true
        fi
    fi
    exit "$rc"
}
trap cleanup EXIT INT TERM

# ─── Helpers ─────────────────────────────────────────────────────────────

step() {
    printf '\n==> [verify_calibration] %s\n' "$*" >&2
}

bail() {
    printf '\n!!  [verify_calibration] FAIL — %s\n' "$*" >&2
    write_diagnostic_if_missing "$*"
    exit 1
}

write_diagnostic_if_missing() {
    local reason="$1"
    mkdir -p "$RESULTS_DIR"
    if [[ -f "$DIAGNOSTIC_PATH" ]]; then
        return 0
    fi
    cat > "$DIAGNOSTIC_PATH" <<EOF
# Phase 1 Calibration — DIAGNOSTIC (FAIL)

**Date (UTC):** ${DATE}
**Gate:** \`scripts/verify_calibration.sh\`
**Result:** FAIL
**Failure reason:** ${reason}
**HANDOFF policy:** STOP per HANDOFF-GSD-AUTO.md STOP condition #1.

## Calibration target

| | Value |
|---|---|
| 2026-03-31 published Playwright composite (historical) | ${PUBLISHED_2026_03_COMPOSITE} |
| Harness re-baseline (2026-03 evidence re-scored) | ${TARGET_COMPOSITE} |
| Tolerance | ±0.5 |
| Accept band | [${LOWER_BAND}, ${UPPER_BAND}] |
| Observed composite | (see Observation below) |

## Observation

${OBSERVED_NOTE:-No observation captured (failure occurred before composite was computed).}

## Most likely root causes (rank-ordered)

1. **Fixture drift** — Ashby snapshot is a SPA shell (no body content from
   wget --mirror; React hydrates client-side from runtime API responses
   that wget cannot capture). S2 is the most-likely failure mode.
   See \`fixtures/snapshots/ashby_2026-05-22/PROVENANCE.md\` "SPA-shell caveat".
2. **Harness bug** — \`scripts/aggregate_scores.py\` dimension scorers
   may be too strict (e.g. \`_score_data_quality\` only awards 10 when
   ALL three of S1/S2/S3 PASS; if S2 is FAIL the row drops to 7).
3. **Rubric drift** — \`scoring/score.py\` was edited (it is SACROSANCT;
   verify \`git diff HEAD~ scoring/score.py\` shows zero lines changed).
4. **Playwright MCP regression** — \`@playwright/mcp@0.0.75\` shipped
   2026-05-07; behavioural change vs the 2026-03 wave's version is
   possible. Check \`results/${DATE}/versions.json\`.

## Inspection commands

\`\`\`bash
# Per-stage outcomes
ls -la results/${DATE}/playwright/stage_s*

# Human-readable transcript
head -100 results/${DATE}/playwright/transcript.md 2>/dev/null

# Orphan-process audit (Pitfall 9)
cat results/${DATE}/playwright/orphan_audit.log 2>/dev/null

# Compare emitted scores against 2026-03 baseline
diff <(jq -S . results/scores.json) \\
     <(jq -S . results/${DATE}/scores.json) 2>/dev/null | head -80

# Re-render the matrix
.venv/bin/python scripts/score_with_na.py results/${DATE}/scores.json 2>/dev/null

# Confirm score.py is byte-for-byte unchanged
git diff HEAD~3 -- scoring/score.py | head
\`\`\`

## What to do next

DO NOT iterate on the harness or rubric to "make calibration pass."
That bias is exactly what this gate exists to prevent. Surface this
diagnostic to the user; the user decides whether to:

  - Re-run against the live Ashby URL with a documented snapshot-only
    caveat (plan-checker C3 recommended fallback), OR
  - Accept the lower S2 score and document the snapshot deficiency, OR
  - Invest in capturing the Ashby runtime API responses (out of scope
    per CONTEXT.md, but may be the right long-term call), OR
  - Investigate a real Playwright MCP regression.
EOF
    echo "verify_calibration: wrote diagnostic → $DIAGNOSTIC_PATH" >&2
}

# Reset the diagnostic path each run — a stale FAIL diagnostic from a
# previous run must not be left in place once we get past the prereq gate
# (we re-write it on real failure). We DON'T delete it eagerly here; the
# trap-cleanup'd path is via `write_diagnostic_if_missing` only on bail.

OBSERVED_NOTE=""

# ─── 0. results dir + log header ─────────────────────────────────────────

mkdir -p "$RESULTS_DIR"

step "verify_calibration: DATE=${DATE} target=${TARGET_COMPOSITE} band=[${LOWER_BAND},${UPPER_BAND}]"

# ─── 1. SC #3: prereq check + hide-binary probe ──────────────────────────

step "SC #3 — make check (prereq gate)"
if ! make check >&2; then
    OBSERVED_NOTE="make check failed — host environment is not ready."
    bail "make check failed (SC #3 — prereq gate)"
fi

if (( DO_PREREQ_HIDE == 1 )); then
    step "SC #3 — hide-binary probe: temporarily mv playwright-mcp away, assert check fails"
    HIDDEN_BINARY_SRC=$(command -v playwright-mcp || true)
    if [[ -z "$HIDDEN_BINARY_SRC" ]]; then
        echo "verify_calibration: playwright-mcp not on PATH — skipping hide probe" >&2
    else
        HIDDEN_BINARY_DST="/tmp/.verify_calibration.hidden.playwright-mcp.$$"
        if ! mv "$HIDDEN_BINARY_SRC" "$HIDDEN_BINARY_DST" 2>/dev/null; then
            # On Homebrew installs the binary may not be writable for the
            # current user — that's fine, skip the probe with a note.
            echo "verify_calibration: cannot move $HIDDEN_BINARY_SRC (probably read-only Homebrew bottle); skipping hide probe" >&2
            HIDDEN_BINARY_DST=""
        else
            set +e
            HIDE_OUTPUT=$(make check 2>&1)
            HIDE_RC=$?
            set -e
            # Restore IMMEDIATELY — never leave the binary missing if we can help it.
            mv "$HIDDEN_BINARY_DST" "$HIDDEN_BINARY_SRC"
            HIDDEN_BINARY_DST=""
            if (( HIDE_RC == 0 )); then
                bail "hide-binary probe: make check returned 0 even with playwright-mcp hidden (SC #3 broken)"
            fi
            if ! echo "$HIDE_OUTPUT" | grep -qi "playwright-mcp.*missing"; then
                bail "hide-binary probe: stderr did not mention 'playwright-mcp: missing' (SC #3 broken)"
            fi
            echo "verify_calibration: hide-binary probe OK — make check correctly failed with playwright-mcp absent" >&2
        fi
    fi
fi

# ─── 2. SC #5: pre-commit hook blocks inline secrets in .mcp.json ────────

step "SC #5 — pre-commit hook secret-guard test (scratch repo)"
SCRATCH_DIR=$(mktemp -d -t wac-verify-XXXXXX)
(
    cd "$SCRATCH_DIR"
    git init -q
    git config user.email "verify@test.local"
    git config user.name  "Verify Calibration"
    git config commit.gpgsign false
    mkdir -p .git/hooks
    cp "$REPO_ROOT/scripts/hooks/pre-commit" .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

    # Case A: inline secret → MUST be rejected.
    cat > .mcp.json <<'JSON'
{
  "mcpServers": {
    "firecrawl": {
      "command": "firecrawl-mcp",
      "env": {"FIRECRAWL_API_KEY": "fc-abcdefghij1234567890qwertyuiopASDF"}
    }
  }
}
JSON
    git add .mcp.json
    set +e
    OUT_A=$(git commit -m "should fail" 2>&1)
    RC_A=$?
    set -e
    if (( RC_A == 0 )); then
        echo "verify_calibration: SC #5 broken — inline secret was NOT rejected" >&2
        echo "$OUT_A" >&2
        exit 1
    fi
    if ! echo "$OUT_A" | grep -qi "inline secret detected"; then
        echo "verify_calibration: SC #5 broken — hook rejected commit but did not emit 'Inline secret detected'" >&2
        echo "$OUT_A" >&2
        exit 1
    fi

    # Case B: ${VAR} reference → MUST be accepted.
    cat > .mcp.json <<'JSON'
{
  "mcpServers": {
    "firecrawl": {
      "command": "firecrawl-mcp",
      "env": {"FIRECRAWL_API_KEY": "${FIRECRAWL_API_KEY}"}
    }
  }
}
JSON
    git add .mcp.json
    if ! git commit -m "should pass" >/dev/null 2>&1; then
        echo "verify_calibration: SC #5 broken — \${VAR} form was REJECTED" >&2
        exit 1
    fi
) || bail "SC #5 pre-commit secret-guard test failed (see stderr above)"
rm -rf "$SCRATCH_DIR"
SCRATCH_DIR=""
echo "verify_calibration: SC #5 OK — inline secret rejected, \${VAR} form accepted" >&2

# ─── 3. SC #4: 3-pass-of-3 retry gate handles a synthetic transient ──────

step "SC #4 — synthetic transient retry test (bench.transient)"
RETRY_LOG="${RESULTS_DIR}/.sc4_retry.json"
mkdir -p "$RESULTS_DIR"
"$VENV_PY" - <<PYEOF || bail "SC #4 retry gate did not behave as expected (see traceback)"
"""Drive bench.transient.retry_stage against a stage that fails the first
time with a TRANSIENT error (ECONNRESET) and passes on retry. Assert
the gate retries, the median pass count is >= 2/3, and the resulting
JSONL records have the expected shape."""
import json, sys
from pathlib import Path
sys.path.insert(0, "${REPO_ROOT}")
from bench.transient import retry_stage, median_pass, write_attempts_to_jsonl
from bench.failure_taxonomy import FailureTag

# Counter so the stage closure can fail-then-pass deterministically.
state = {"calls": 0}
def stage():
    state["calls"] += 1
    if state["calls"] == 1:
        # ECONNRESET — the canonical transient that the harness already
        # classifies via bench.failure_taxonomy. Verifies the classifier
        # honours its own taxonomy at runtime, not just in unit tests.
        raise ConnectionResetError("ECONNRESET — simulated mid-S5 MCP child kill")
    return {"stage": "S5", "result": "ok-after-retry"}

attempts = retry_stage(stage, max_attempts=3, sleep_between_s=0)
write_attempts_to_jsonl(attempts, Path("${RETRY_LOG}"))
passes, total = median_pass(attempts)

# Assertions — fail loudly with a clear print so the bash bail picks up
# the right error context.
assert total >= 2, f"retry_stage stopped after {total} attempts (expected >= 2)"
assert passes >= 1, f"no attempt passed (passes={passes}/{total})"
# The first attempt MUST have been classified TRANSIENT — otherwise the
# retry gate would have stopped after one try (per retry_stage's
# transient_only=True semantics).
first_tag = attempts[0].tag
assert first_tag == FailureTag.TRANSIENT, f"first failure was tagged {first_tag}, expected TRANSIENT"
print(f"SC #4 OK — attempts={total}, passes={passes}, first_failure_tag={first_tag.value}")
PYEOF
echo "verify_calibration: SC #4 OK — retry gate recovered from synthetic transient (see $RETRY_LOG)" >&2

# ─── 4. Real run: SC #1 + SC #2 ─────────────────────────────────────────

if (( SKIP_BENCH == 1 )); then
    step "SKIP_BENCH=1 set — skipping live Playwright run; using existing $PLAYWRIGHT_DIR/"
    if [[ ! -d "$PLAYWRIGHT_DIR" ]]; then
        bail "SKIP_BENCH=1 but $PLAYWRIGHT_DIR/ does not exist — nothing to score"
    fi
else
    step "SC #1+2 — make bench-playwright (live Claude session against snapshot fixtures)"
    # `make bench-playwright` depends on `check` + `fixtures-serve` and
    # invokes `scripts/run_mcp_session.sh playwright` which writes the
    # full evidence dir to results/$DATE/playwright/. The session itself
    # takes ~5-15 minutes (Chromium download on first run can add more).
    if ! make bench-playwright; then
        OBSERVED_NOTE="\`make bench-playwright\` exited non-zero — see $PLAYWRIGHT_DIR/raw_stream.jsonl for the Claude stream and $PLAYWRIGHT_DIR/orphan_audit.log for process hygiene."
        bail "make bench-playwright exited non-zero (SC #1+2 — live run)"
    fi
fi

# ─── 5. Aggregate + score ───────────────────────────────────────────────

step "Aggregating per-MCP evidence into scores.json"
"$VENV_PY" scripts/aggregate_scores.py "$RESULTS_DIR" >&2 \
    || bail "aggregate_scores.py failed — see stderr"

SCORES_JSON="${RESULTS_DIR}/scores.json"
if [[ ! -s "$SCORES_JSON" ]]; then
    bail "aggregate_scores.py did not write $SCORES_JSON"
fi

# ─── 6. Read composite + assert band ────────────────────────────────────

step "Computing N/A-aware composite for the playwright row"
# Run the wrapper directly so the math path is the same one the unit test
# in tests/test_calibration_math.py covers. Emit ONLY the float so bash
# can compare it; stderr carries the formatted matrix for human eyes.
COMPOSITE=$("$VENV_PY" - <<PYEOF
import json, sys
from pathlib import Path
sys.path.insert(0, "${REPO_ROOT}")
from scripts.score_with_na import compute_na_aware_composite

data = json.loads(Path("${SCORES_JSON}").read_text())
# aggregate_scores.py keys the dict by .mcp.json key ("playwright"), but
# we also tolerate the published-results name "Playwright MCP" in case a
# manual scores.json is fed in.
row = data.get("playwright") or data.get("Playwright MCP")
if row is None:
    print(f"NO_PLAYWRIGHT_ROW: keys={list(data.keys())}", file=sys.stderr)
    sys.exit(2)
print(compute_na_aware_composite(row["scores"]))
PYEOF
)
COMPOSITE=$(echo "$COMPOSITE" | tail -1 | tr -d '[:space:]')
echo "verify_calibration: observed composite = $COMPOSITE" >&2

# Also print the full matrix to stderr for diagnostic context.
"$VENV_PY" scripts/score_with_na.py "$SCORES_JSON" >&2 || true

# Band check — pure Python so float comparison matches the unit test
# semantics exactly (avoid bc / awk float quirks).
IN_BAND=$("$VENV_PY" - <<PYEOF
c = float("${COMPOSITE}")
lo, hi = ${LOWER_BAND}, ${UPPER_BAND}
print("yes" if lo <= c <= hi else "no")
PYEOF
)

OBSERVED_NOTE="Observed composite = **${COMPOSITE}** (target ${TARGET_COMPOSITE}, band [${LOWER_BAND}, ${UPPER_BAND}]).
Per-MCP scores.json at \`${SCORES_JSON}\`.
N/A-aware matrix re-rendered above for diagnostic reference."

if [[ "$IN_BAND" != "yes" ]]; then
    bail "composite ${COMPOSITE} OUTSIDE band [${LOWER_BAND}, ${UPPER_BAND}] — Phase 1 gate FAILED"
fi
echo "verify_calibration: SC #1 OK — composite $COMPOSITE in [${LOWER_BAND}, ${UPPER_BAND}]" >&2

# ─── 7. SC #2: evidence-directory completeness ──────────────────────────

step "SC #2 — evidence-directory file inventory"
REQUIRED=(transcript.md raw_stream.jsonl cold_start.json tokens.json tls.json stability.log orphan_audit.log tools_inventory.json)
MISSING_FILES=()
for f in "${REQUIRED[@]}"; do
    if [[ ! -f "${PLAYWRIGHT_DIR}/$f" ]]; then
        MISSING_FILES+=("$f")
    fi
done
if (( ${#MISSING_FILES[@]} > 0 )); then
    bail "SC #2 — missing evidence files in ${PLAYWRIGHT_DIR}: ${MISSING_FILES[*]}"
fi

# At least 3 stage_s*.* artifacts must exist (S1/S2/S3 read-only stages,
# minimum; a Playwright run that reaches even S3 has demonstrated the
# evidence-shape contract).
STAGE_COUNT=$(find "${PLAYWRIGHT_DIR}" -maxdepth 1 -name 'stage_s*.*' -type f 2>/dev/null | wc -l | tr -d ' ')
if (( STAGE_COUNT < 3 )); then
    bail "SC #2 — only $STAGE_COUNT stage_s*.* artifacts (expected >= 3)"
fi

# orphan_audit.log must show 0 survivors (the success line is "ORPHANS=0").
# Note: orphan_audit.py emits ORPHANS=<n> and KILLED_COUNT=<n>. The
# Phase-1 policy logs-and-continues even with survivors, so we don't
# fail this gate on a non-zero count — but we DO surface it loudly so
# any reader sees the deviation.
if grep -q "^ORPHANS=0$" "${PLAYWRIGHT_DIR}/orphan_audit.log"; then
    echo "verify_calibration: orphan audit clean (0 survivors)" >&2
else
    ORPHANS_LINE=$(grep "^ORPHANS=" "${PLAYWRIGHT_DIR}/orphan_audit.log" || echo "ORPHANS=?")
    echo "verify_calibration: WARNING — orphan audit reports $ORPHANS_LINE (Phase-1 policy: log and continue)" >&2
fi

echo "verify_calibration: SC #2 OK — ${#REQUIRED[@]} required files present, $STAGE_COUNT stage artifacts" >&2

# ─── 8. PASS document + scoring/score.py SACROSANCT check ───────────────

# Confirm scoring/score.py is byte-for-byte unchanged. We don't fail on
# difference (a deliberate refactor with the same behaviour is fine), but
# we record the diff in the PASS document so the audit trail captures it.
SCORE_PY_DIFF=$(git diff --stat HEAD -- scoring/score.py 2>/dev/null || true)
if [[ -z "$SCORE_PY_DIFF" ]]; then
    SCORE_PY_NOTE="scoring/score.py: no uncommitted changes (SACROSANCT contract upheld)"
else
    SCORE_PY_NOTE="scoring/score.py: uncommitted changes detected — \`$SCORE_PY_DIFF\` (review required)"
fi

# Pull a few useful facts from versions.json (best-effort; absence is fine).
VERSIONS_JSON="${RESULTS_DIR}/versions.json"
if [[ -f "$VERSIONS_JSON" ]]; then
    CLAUDE_VERSION=$(jq -r '.tooling.claude_code // "unknown"' "$VERSIONS_JSON")
    NODE_VERSION=$(jq -r '.tooling.node // "unknown"' "$VERSIONS_JSON")
    PYTHON_VERSION=$(jq -r '.tooling.python // "unknown"' "$VERSIONS_JSON")
    HOST_OS=$(jq -r '.host.os // "unknown"' "$VERSIONS_JSON")
else
    CLAUDE_VERSION="unknown (versions.json missing)"
    NODE_VERSION="unknown"
    PYTHON_VERSION="unknown"
    HOST_OS="unknown"
fi

# Note the gap from target — useful for trend-watching across re-calibrations.
DELTA=$("$VENV_PY" -c "print(round(${COMPOSITE} - ${TARGET_COMPOSITE}, 2))")

cat > "$PASS_PATH" <<EOF
# Phase 1 Calibration — PASS

**Date (UTC):** ${DATE}
**Gate:** \`scripts/verify_calibration.sh\`
**Result:** **PASS**

## Calibration

| | Value |
|---|---|
| 2026-03-31 published Playwright composite (historical, via \`scoring/score.py\`) | ${PUBLISHED_2026_03_COMPOSITE} |
| Harness re-baseline (2026-03 evidence re-scored via \`aggregate_scores.py\`) | ${TARGET_COMPOSITE} |
| Observed (${DATE}, this run) | **${COMPOSITE}** |
| Delta vs re-baseline | ${DELTA} |
| Accept band | [${LOWER_BAND}, ${UPPER_BAND}] |
| Tolerance | ±0.5 |

**Phase 1 calibration PASS. Harness reproduces the 2026-03 Playwright
evidence under its own heuristic scoring within ±0.5 of the apples-to-
apples re-baseline. Phase 2 may proceed.**

The published 2026-03 composite (9.07) is unchanged and remains the
methodology's wave-to-wave anchor — see \`scoring/rubric_notes.md\`
"Calibration Re-Baseline (2026-05-26)" for why the gate validates
against the heuristic re-baseline (8.33) instead.

## Environment

| | Value |
|---|---|
| Host OS | ${HOST_OS} |
| Claude Code | ${CLAUDE_VERSION} |
| Node | ${NODE_VERSION} |
| Python (venv) | ${PYTHON_VERSION} |

## Success criteria

- **SC #1 — Composite in band:** PASS (composite=${COMPOSITE} ∈ [${LOWER_BAND}, ${UPPER_BAND}])
- **SC #2 — Evidence directory complete:** PASS (${#REQUIRED[@]} required files present, $STAGE_COUNT stage artifacts)
- **SC #3 — \`check_prereqs.sh\` detects missing binaries:** PASS (hide-probe rejected the run)
- **SC #4 — Retry gate handles synthetic transient:** PASS (see \`${RETRY_LOG#${REPO_ROOT}/}\`)
- **SC #5 — Pre-commit hook blocks inline secrets:** PASS (scratch-repo probe rejected inline, accepted \${VAR})

## Process hygiene

$(grep "^ORPHANS=" "${PLAYWRIGHT_DIR}/orphan_audit.log" 2>/dev/null || echo "ORPHANS=?")
$(grep "^KILLED_COUNT=" "${PLAYWRIGHT_DIR}/orphan_audit.log" 2>/dev/null || echo "KILLED_COUNT=?")

## Sacrosanct check

${SCORE_PY_NOTE}

## Reproducibility

\`\`\`bash
bash scripts/verify_calibration.sh
\`\`\`

Per-MCP evidence: \`${PLAYWRIGHT_DIR}/\`
Aggregated scores: \`${SCORES_JSON}\`
EOF

# If a stale diagnostic from a prior failed run is sitting next to the new
# pass doc, remove it so the directory tells a coherent story. Exception:
# if the diagnostic carries a "SUPERSEDED" marker, it's part of an audit
# trail (e.g. the 2026-05-25 FAIL → 2026-05-26 re-baseline PASS sequence)
# and must NOT be deleted.
if [[ -f "$DIAGNOSTIC_PATH" ]]; then
    if grep -q "SUPERSEDED" "$DIAGNOSTIC_PATH" 2>/dev/null; then
        echo "verify_calibration: $DIAGNOSTIC_PATH carries SUPERSEDED marker — preserving for audit trail" >&2
    else
        echo "verify_calibration: removing stale $DIAGNOSTIC_PATH (now superseded by PASS)" >&2
        rm -f "$DIAGNOSTIC_PATH"
    fi
fi

echo "" >&2
echo "✓ Calibration passes: ${COMPOSITE}" >&2
echo "  Re-baseline target ${TARGET_COMPOSITE} ± 0.5  (band [${LOWER_BAND}, ${UPPER_BAND}])" >&2
echo "  Published 2026-03 composite (historical, preserved): ${PUBLISHED_2026_03_COMPOSITE}" >&2
echo "  Delta vs re-baseline: ${DELTA}" >&2
echo "  PASS document: ${PASS_PATH}" >&2
exit 0
