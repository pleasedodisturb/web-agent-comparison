#!/usr/bin/env bash
#
# serve_fixtures.sh — boot/teardown of the local fixture HTTP server.
#
# Subcommands:
#   start   spawn `python3 -m http.server 8765 --bind 127.0.0.1
#           --directory fixtures/snapshots/` under nohup. Wait up to 5s
#           for the loopback port to answer before returning success.
#   stop    kill the recorded PID (if any), remove the pidfile.
#           No-op (rc=0) if the pidfile is absent.
#   status  print "running PID=<n>" or "stopped".
#
# Pidfile:      /tmp/wac_fixture_server.pid
# Log:         /tmp/wac_fixture_server.log
# Bind:        127.0.0.1:8765 (loopback only — never expose externally)
#
# Per CONTEXT.md "Local server: `python3 -m http.server` bound to
# `127.0.0.1`" — the loopback bind is the safety boundary that keeps
# the snapshot fixture off the LAN.
#
# Exit codes:
#   0 — subcommand succeeded
#   1 — start failed (server didn't answer), or stop hit an unexpected error,
#       or bad arguments.
#   2 — start refused because the server is already running.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PIDFILE="/tmp/wac_fixture_server.pid"
LOGFILE="/tmp/wac_fixture_server.log"
PORT="${WAC_FIXTURE_PORT:-8765}"
BIND="127.0.0.1"
ROOT="$REPO_ROOT/fixtures/snapshots"

usage() {
    cat >&2 <<EOF
usage: $0 {start|stop|status}

  start    boot python3 -m http.server on ${BIND}:${PORT}, serving:
           ${ROOT}
  stop     kill the recorded server PID (if any).
  status   print running|stopped.
EOF
    exit 1
}

is_alive() {
    # $1 = pid; returns 0 if the pid is alive, non-zero otherwise.
    kill -0 "$1" 2>/dev/null
}

ping_loopback() {
    # Returns 0 if the loopback server responds, non-zero otherwise.
    # We accept any 2xx/3xx (the root index is an auto-generated dir
    # listing). Tight timeouts: --connect-timeout 1 + --max-time 2 keep
    # each poll cheap so the 5s startup deadline isn't eaten by curl's
    # own connect retry behaviour. Pure loopback should respond in <10ms
    # when alive; the wide-open window is just paranoia.
    #
    # `-s` (silent) suppresses curl's progress and error spam during
    # startup polling — we already inspect the rc and log on failure.
    curl -fs -o /dev/null --connect-timeout 1 --max-time 2 "http://${BIND}:${PORT}/" 2>/dev/null
}

cmd_start() {
    if [[ -f "$PIDFILE" ]]; then
        existing=$(cat "$PIDFILE" 2>/dev/null || true)
        if [[ -n "$existing" ]] && is_alive "$existing"; then
            echo "serve_fixtures: already running at PID $existing" >&2
            return 2
        fi
        # Stale pidfile — remove it before re-spawning.
        rm -f "$PIDFILE"
    fi

    if [[ ! -d "$ROOT" ]]; then
        echo "serve_fixtures: snapshots root missing at $ROOT" >&2
        echo "serve_fixtures: run scripts/snapshot_fixtures.sh first" >&2
        return 1
    fi

    # Resolve the Python interpreter through the project venv (uv-managed).
    # Reason: the system `python3` on this host is 3.14.5, whose
    # `http.server` immediately closes the listen socket on macOS
    # (per CLAUDE.md "avoid Python 3.14 — too new for downstream deps").
    # The .venv/bin/python is the 3.12.x interpreter `uv sync` installed
    # and is the same one the rest of the harness uses, so we get
    # consistent behaviour and no surprise PATH version pickup.
    venv_python="$REPO_ROOT/.venv/bin/python"
    if [[ ! -x "$venv_python" ]]; then
        echo "serve_fixtures: project venv python missing at $venv_python" >&2
        echo "serve_fixtures: run 'uv sync' to materialize the .venv first" >&2
        return 1
    fi

    # Spawn under nohup so the server survives the parent shell. setsid
    # would be nice for clean process-group teardown, but macOS doesn't
    # ship it; nohup + a single-PID pidfile is enough for our pattern
    # (one server, killed by the same script that started it).
    nohup "$venv_python" -m http.server "$PORT" \
        --bind "$BIND" \
        --directory "$ROOT" \
        > "$LOGFILE" 2>&1 &
    server_pid=$!
    echo "$server_pid" > "$PIDFILE"

    # Wait up to 5s wall-clock for the loopback port to answer. We poll
    # with a deadline (not a fixed iteration count) so the wait is
    # actual-elapsed-seconds rather than "n probes that each took 2s
    # because curl had a generous --max-time".
    deadline=$(( $(date +%s) + 5 ))
    while [[ "$(date +%s)" -lt "$deadline" ]]; do
        if ping_loopback; then
            echo "serve_fixtures: started PID=$server_pid bind=${BIND}:${PORT} root=${ROOT}"
            return 0
        fi
        # Bail early if the child died before the port opened.
        if ! is_alive "$server_pid"; then
            echo "serve_fixtures: server PID=$server_pid died during startup" >&2
            echo "----- last 20 log lines -----" >&2
            tail -20 "$LOGFILE" >&2 || true
            echo "-----------------------------" >&2
            rm -f "$PIDFILE"
            return 1
        fi
        sleep 0.1
    done

    echo "serve_fixtures: server did not answer on http://${BIND}:${PORT}/ within 5s" >&2
    echo "----- last 20 log lines -----" >&2
    tail -20 "$LOGFILE" >&2 || true
    echo "-----------------------------" >&2
    # Best-effort kill so we don't leak a process.
    kill "$server_pid" 2>/dev/null || true
    rm -f "$PIDFILE"
    return 1
}

cmd_stop() {
    if [[ ! -f "$PIDFILE" ]]; then
        # Idempotent: stop with no running server is a clean no-op.
        return 0
    fi
    pid=$(cat "$PIDFILE" 2>/dev/null || true)
    if [[ -z "$pid" ]]; then
        rm -f "$PIDFILE"
        return 0
    fi
    if is_alive "$pid"; then
        kill "$pid" 2>/dev/null || true
        # Give it a moment to exit cleanly; fall back to KILL.
        for _ in 1 2 3 4 5; do
            if ! is_alive "$pid"; then
                break
            fi
            sleep 0.2
        done
        if is_alive "$pid"; then
            kill -KILL "$pid" 2>/dev/null || true
        fi
    fi
    rm -f "$PIDFILE"
    echo "serve_fixtures: stopped PID=$pid"
    return 0
}

cmd_status() {
    if [[ -f "$PIDFILE" ]]; then
        pid=$(cat "$PIDFILE" 2>/dev/null || true)
        if [[ -n "$pid" ]] && is_alive "$pid"; then
            if ping_loopback; then
                echo "running PID=$pid (port ${PORT} responding)"
                return 0
            fi
            echo "running PID=$pid (port ${PORT} NOT responding — likely starting or wedged)"
            return 0
        fi
        echo "stopped (stale pidfile at $PIDFILE)"
        return 0
    fi
    echo "stopped"
    return 0
}

case "${1:-}" in
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    *)      usage ;;
esac
