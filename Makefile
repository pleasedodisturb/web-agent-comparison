# Makefile — single-command reproducibility surface for the web-agent-comparison harness.
#
# Targets:
#   make check         — run scripts/check_prereqs.sh; gate for every other target
#   make bench         — full benchmark run; runs check, then all bench-<mcp>, then score
#   make bench-<mcp>   — run one MCP's harness session (real driver lands in plan 01-04)
#   make score         — aggregate $(RESULTS_DIR)/scores.json through scoring/score.py
#   make coldstart     — STUB; deferred to G-710 (TLS/cold-start measurement wave)
#   make stability     — STUB; deferred to G-710
#   make tls           — STUB; deferred to G-710
#   make clean         — remove .venv, node_modules, and Python cache dirs
#
# Per HARNESS-06, `make bench` MUST invoke check_prereqs.sh as its first step —
# enforced here by making `check` an order-only prerequisite of `bench`.

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

# Use a deterministic UTC date for results directory naming. Override on the
# command line for reruns: `make bench DATE=2026-05-22`.
DATE        := $(shell date -u +%Y-%m-%d)
RESULTS_DIR := results/$(DATE)

# The 7 candidate MCPs (must match .mcp.json key set).
MCPS := playwright browser-use chrome-devtools lightpanda obscura firecrawl cloakbrowser

.PHONY: bench check score clean coldstart stability tls help \
        fixtures-serve fixtures-stop fixtures-status smoke-live \
        $(addprefix bench-,$(MCPS))

# ─── Default + help ─────────────────────────────────────────────────────────

help:
	@echo "web-agent-comparison harness — common targets:"
	@echo "  make check           # run prereq gate"
	@echo "  make bench           # run all 7 MCPs end-to-end, then score"
	@echo "  make bench-<mcp>     # run a single MCP (one of: $(MCPS))"
	@echo "  make score           # aggregate $(RESULTS_DIR)/scores.json"
	@echo "  make clean           # nuke .venv, node_modules, __pycache__"
	@echo ""
	@echo "Fixtures (plan 01-03):"
	@echo "  make fixtures-serve  # boot local http server on 127.0.0.1:8765"
	@echo "  make fixtures-stop   # tear down the fixture server"
	@echo "  make fixtures-status # show running/stopped"
	@echo "  make smoke-live      # ONE-shot HEAD against the live source URLs"
	@echo "                       # — diagnostic drift detector, NOT scored"
	@echo ""
	@echo "Stubs (deferred to G-710):"
	@echo "  make coldstart       # TLS-side: cold-start latency measurement"
	@echo "  make stability       # 60-min stability soak"
	@echo "  make tls             # JA3/JA4 fingerprint capture"

# ─── Prereq gate ─────────────────────────────────────────────────────────────

check:
	@scripts/check_prereqs.sh

# ─── Full bench pipeline ─────────────────────────────────────────────────────
# `check` is the first recipe step. Make does not guarantee prerequisite order
# in parallel builds, so we list `check` as the first explicit dependency and
# also re-invoke it inside the recipe to satisfy the literal HARNESS-06 wording
# ("the first thing make bench does is run check_prereqs").

bench: check $(addprefix bench-,$(MCPS)) score
	@echo "bench: complete — see $(RESULTS_DIR)/"

# ─── Per-MCP target ──────────────────────────────────────────────────────────
# Static-pattern rule (NOT `bench-%:`). System Make on macOS is GNU Make 3.81,
# which has a known bug where pattern rules with phony prerequisites silently
# no-op ("Nothing to be done for `bench-foo'"). Static-pattern rules of the
# form `targets...: pattern: prereqs` work correctly under 3.81 and remain
# valid GNU Make syntax under 4.x — so this form is the portable choice.
#
# Wired in plan 01-04 to scripts/run_mcp_session.sh. The `fixtures-serve`
# dependency is idempotent — serve_fixtures.sh start no-ops with rc=2 if the
# server is already running, and run_mcp_session.sh re-checks before booting
# its own server (only stopping it on exit if IT started it).

$(addprefix bench-,$(MCPS)): bench-%: check fixtures-serve
	@if [ -x scripts/run_mcp_session.sh ]; then \
	    scripts/run_mcp_session.sh $* ; \
	else \
	    echo "bench-$*: scripts/run_mcp_session.sh not yet installed (driver lands in plan 01-04)" ; \
	    exit 0 ; \
	fi

# ─── Score aggregation ───────────────────────────────────────────────────────
# scoring/score.py is sacrosanct per ARCHITECTURE.md. We pipe scores.json into
# it via uv-managed python so the dep closure is reproducible.

score:
	@if [ ! -f $(RESULTS_DIR)/scores.json ]; then \
	    echo "score: no scores.json at $(RESULTS_DIR) — run bench-<mcp> first" ; \
	    exit 1 ; \
	fi
	@uv run python scoring/score.py $(RESULTS_DIR)/scores.json | tee -a $(RESULTS_DIR)/$(DATE)_run.md

# ─── Fixtures (plan 01-03) ───────────────────────────────────────────────────
# The bench-<mcp> targets will gain a fixtures-serve dependency in plan 01-04
# once scripts/run_mcp_session.sh lands. For now the targets are standalone so
# humans (and the snapshot-serve test) can use them.

fixtures-serve:
	@# serve_fixtures.sh start exits 2 if the server is already running;
	@# that's not a Make failure for our purposes — treat 2 as success so
	@# `make bench-<mcp>` can re-use an existing fixture server without
	@# tearing down and re-spawning each time.
	@scripts/serve_fixtures.sh start || rc=$$? ; \
	    if [ "$${rc:-0}" -ne 0 ] && [ "$${rc:-0}" -ne 2 ]; then \
	        echo "fixtures-serve: failed (rc=$$rc)" >&2 ; \
	        exit $$rc ; \
	    fi ; \
	    exit 0

fixtures-stop:
	@scripts/serve_fixtures.sh stop

fixtures-status:
	@scripts/serve_fixtures.sh status

# Live-URL smoke target — diagnostic only, NOT part of the scored bench
# flow. CONTEXT.md flags this as "drift signal only — NOT scored". Runs a
# tiny HEAD request against the source URLs captured in
# fixtures/snapshots/*/PROVENANCE.md and prints the HTTP status so a
# reader can tell at a glance whether the live target has 404'd since the
# snapshot was taken (Pitfall 8). The deeper "is the page still
# semantically the same" check lands in G-710.
smoke-live:
	@for plat in greenhouse ashby ; do \
	    snap="fixtures/snapshots/$${plat}_$(DATE)" ; \
	    if [ ! -f "$$snap/PROVENANCE.md" ] ; then \
	        echo "smoke-live: $$snap/PROVENANCE.md missing — re-run scripts/snapshot_fixtures.sh first" ; \
	        continue ; \
	    fi ; \
	    url=$$(sed -n 's/^- \*\*Source URL:\*\* *//p' "$$snap/PROVENANCE.md" | head -1) ; \
	    if [ -z "$$url" ] ; then \
	        echo "smoke-live $$plat: could not extract Source URL from $$snap/PROVENANCE.md" ; \
	        continue ; \
	    fi ; \
	    code=$$(curl -sI -L -o /dev/null --max-time 10 -w "%{http_code}" "$$url") ; \
	    echo "smoke-live $$plat: HTTP $$code  $$url" ; \
	done

# ─── Stubs (surface locked; work deferred to G-710) ──────────────────────────

coldstart:
	@echo "coldstart: deferred to G-710 (scope cut 2026-05-22)"

stability:
	@echo "stability: deferred to G-710 (scope cut 2026-05-22)"

tls:
	@echo "tls: deferred to G-710 (scope cut 2026-05-22)"

# ─── Housekeeping ────────────────────────────────────────────────────────────

clean:
	rm -rf node_modules .venv
	find . -type d \( -name __pycache__ -o -name '*.egg-info' \) -prune -exec rm -rf {} +
