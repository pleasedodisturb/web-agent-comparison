#!/usr/bin/env bash
#
# run_stability.sh — Bash wrapper for the per-MCP stability soak.
#
# Usage:
#   scripts/run_stability.sh <MCP> [DURATION_MINUTES] [MODE]
#
#     MCP                — one of: playwright, chrome-devtools, lightpanda,
#                          cloakbrowser, obscura, browser-use-direct,
#                          firecrawl, browser-use-agent
#     DURATION_MINUTES   — wall-clock budget per MCP (default 60).
#                          Ignored for MODE=skip.
#     MODE               — full | read-only | skip   (default: full)
#                          'read-only' is the lightpanda mode (S1 only,
#                          S5 marked N/A_READONLY).
#                          'skip' writes a SKIPPED metadata file without
#                          spawning anything (firecrawl, browser-use-agent).
#
# Env:
#   DATE                  — YYYY-MM-DD bucket for results/. Defaults to UTC today.
#   SNAPSHOT_BASE_URL     — http://127.0.0.1:8765 unless overridden.
#   STABILITY_SKIP_REASON — for MODE=skip, the metadata.skip_reason field.
#   STABILITY_WALLCLOCK   — wallclock-decision identifier (strict_60min,
#                            selective_top3_60min_rest_30min, reduced_30min_all).
#                            Default: selective_top3_60min_rest_30min.
#
# Outputs (under results/$DATE/<MCP>/):
#   stability.log               — per-iteration rows (or SKIPPED marker line)
#   stability_metadata.json     — rolled-up summary consumed by Phase 4
#   stability_orphan_audit.log  — orphan_audit diff log (only when not SKIPPED)
#   .stability_ps_before.tsv    — pre-run ps snapshot (kept for debugging)
#   .stability_ps_after.tsv     — post-run ps snapshot
#   stability.err               — stderr from the python driver
#
# Pre-run guard: idempotently boots the fixture server (scripts/serve_fixtures.sh
# start). The fixture server lifecycle is owned by the caller in batch mode —
# this wrapper does NOT stop it on exit, so subsequent MCP runs reuse the
# same server (avoids tearing down and respawning between MCPs in a sweep).
#
# Memory ceiling: ulimit -v 4 GB inherited by the python child. This caps
# virtual memory and lets an OOM kill the MCP without taking the whole host
# down — important when running a 60-min loop against a leaky MCP.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

MCP="${1:-}"
DURATION="${2:-60}"
MODE="${3:-full}"

if [[ -z "$MCP" ]]; then
    echo "usage: $0 <MCP> [DURATION_MINUTES=60] [MODE=full|read-only|skip]" >&2
    exit 1
fi

DATE="${DATE:-$(date -u +%Y-%m-%d)}"
OUT_DIR="results/${DATE}/${MCP}"
mkdir -p "$OUT_DIR"

# ── Fixture server (idempotent boot) ─────────────────────────────────────
# `serve_fixtures.sh start` exits 0 on fresh boot, 2 if already running, 1
# on actual failure. We treat 0 and 2 as "server is up"; only 1 is fatal.
# Skip the boot entirely for MODE=skip — the skipped MCPs (firecrawl,
# browser-use-agent) don't need a fixture server.
if [[ "$MODE" != "skip" ]]; then
    if scripts/serve_fixtures.sh status | grep -q '^stopped'; then
        rc=0
        scripts/serve_fixtures.sh start || rc=$?
        if [[ "$rc" -ne 0 && "$rc" -ne 2 ]]; then
            echo "run_stability: fixture server failed to boot (rc=$rc)" >&2
            exit 1
        fi
    fi
fi

# ── ulimit (4 GB virtual memory) ─────────────────────────────────────────
# Best-effort; macOS sometimes ignores -v silently. The `|| true` keeps the
# script alive if ulimit refuses the limit (which is benign).
ulimit -v 4194304 2>/dev/null || true

# ── Pre-run ps snapshot ──────────────────────────────────────────────────
# The python driver also snapshots internally; this sidecar copy at the
# outer process boundary captures any orchestrator-level processes the
# inner snapshot would miss.
if [[ "$MODE" != "skip" ]]; then
    .venv/bin/python -m bench.orphan_audit --snapshot-only "$OUT_DIR/.stability_ps_outer_before.tsv" 2>/dev/null || true
fi

# ── Resolve skip reason for MODE=skip ────────────────────────────────────
if [[ "$MODE" == "skip" ]]; then
    SKIP_REASON="${STABILITY_SKIP_REASON:-}"
    if [[ -z "$SKIP_REASON" ]]; then
        # Sensible per-MCP defaults so callers don't always need to set
        # the env var.
        case "$MCP" in
            firecrawl)         SKIP_REASON="LOOPBACK_UNREACHABLE" ;;
            browser-use-agent) SKIP_REASON="LLM_KEY_ABSENT" ;;
            *)                 SKIP_REASON="UNSPECIFIED" ;;
        esac
    fi
    SKIP_ARGS=( --skip-reason "$SKIP_REASON" )
else
    SKIP_ARGS=()
fi

WALLCLOCK="${STABILITY_WALLCLOCK:-selective_top3_60min_rest_30min}"
FIXTURE_BASE_URL="${SNAPSHOT_BASE_URL:-http://127.0.0.1:8765}"

# ── Run the driver ───────────────────────────────────────────────────────
# setsid puts the python driver (and every child MCP it spawns) in a fresh
# process group, so the post-run orphan_audit + kill_group can clean up
# anything that survives. macOS lacks `setsid` by default; if absent, fall
# back to a plain subshell — orphan_audit's regex-based survivor detection
# will still catch leaks via the cmdline patterns.
if command -v setsid >/dev/null 2>&1; then
    PYTHON_CMD=(setsid .venv/bin/python -m bench.stability_loop)
else
    PYTHON_CMD=(.venv/bin/python -m bench.stability_loop)
fi

"${PYTHON_CMD[@]}" "$MCP" \
    --duration-minutes "$DURATION" \
    --sleep-s 30 \
    --fixture-base-url "$FIXTURE_BASE_URL" \
    --out-dir "$OUT_DIR" \
    --mode "$MODE" \
    --wallclock-decision "$WALLCLOCK" \
    "${SKIP_ARGS[@]}" \
    > "$OUT_DIR/stability.stdout.log" \
    2> "$OUT_DIR/stability.err"

# ── Post-run outer snapshot + audit ──────────────────────────────────────
# Only meaningful for non-skipped runs; for SKIPPED rows there's nothing
# to audit (no spawn happened).
if [[ "$MODE" != "skip" ]]; then
    .venv/bin/python -m bench.orphan_audit --snapshot-only "$OUT_DIR/.stability_ps_outer_after.tsv" 2>/dev/null || true
    rc=0
    .venv/bin/python -m bench.orphan_audit \
        --before-snapshot "$OUT_DIR/.stability_ps_outer_before.tsv" \
        --after-snapshot "$OUT_DIR/.stability_ps_outer_after.tsv" \
        --log "$OUT_DIR/stability_orphan_audit_outer.log" \
        || rc=$?
    if [[ "$rc" -ne 0 ]]; then
        echo "run_stability: outer orphan_audit found survivors (see $OUT_DIR/stability_orphan_audit_outer.log)" >&2
    fi
fi

echo "run_stability: $MCP DURATION=${DURATION}min MODE=$MODE → $OUT_DIR"
exit 0
