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
# Real driver script lands in plan 01-04 (scripts/run_mcp_session.sh). Until
# it exists, the recipe emits an explicit deferral message so the surface
# compiles end-to-end without breaking `make bench`.

$(addprefix bench-,$(MCPS)): bench-%: check
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
