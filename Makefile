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
        versions \
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
	@echo "Reproducibility manifest (plan 01-06):"
	@echo "  make versions        # write/refresh results/$(DATE)/versions.{json,lock.md}"
	@echo ""
	@echo "Cross-cutting measurements (Phase 3):"
	@echo "  make cold-start         # 3-segment cold + warm sweep across all 8 MCP rows"
	@echo "  make cold-start-<mcp>   # one MCP only (e.g. cold-start-playwright)"
	@echo "                          # override N_RUNS=10 for more samples"
	@echo ""
	@echo "Stubs (deferred to G-710):"
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

# ─── Reproducibility manifest (plan 01-06) ───────────────────────────────────
# Regenerable on demand — the manifest captures live tool versions and
# binary SHA256s, which drift independently of the benchmark runs. Useful
# for "did anything change since yesterday?" diffs.

versions:
	@uv run python -m bench.capture_versions --date $(DATE) --results-root results/

# ─── Stability soak (Phase 3 plan 03-04, MEAS-07) ────────────────────────────
# Per-MCP target: drive the MCP through S1+S5 (or S1 only for read-only
# lightpanda) against the 127.0.0.1:8765 snapshot fixture server for
# STABILITY_MINUTES wall-clock, 30s sleep between iterations, per-tool-call
# 30s timeout, post-run orphan_audit.
#
# Three wall-clock decision recipes are exposed:
#   make stability-strict-60min      — 60min × 6 SCORED MCPs (~6.5 hours)
#   make stability-selective-top3    — 60min top-3 + 30min rest (~4.5 hours)
#   make stability-reduced-30min     — 30min × 6 (~3.5 hours)
#
# Each recipe also writes the two SKIPPED rows (firecrawl, browser-use-agent)
# so the matrix has all 7+1 rows accounted for.
#
# Per-MCP override:
#   make stability-playwright STABILITY_MINUTES=10  (10-minute smoke run)
#
# DATE override (default UTC today):
#   make stability-strict-60min DATE=2026-05-26
#
# Mode override is exposed by scripts/run_stability.sh directly — the
# Makefile only routes lightpanda → read-only and firecrawl/agent → skip,
# matching the rubric's MCP-by-MCP mode assignment.

STABILITY_MINUTES ?= 60
STABILITY_MCPS_FULL    := playwright chrome-devtools cloakbrowser obscura browser-use-direct
STABILITY_MCPS_RO      := lightpanda
STABILITY_MCPS_SKIPPED := firecrawl browser-use-agent
STABILITY_MCPS_ALL     := $(STABILITY_MCPS_FULL) $(STABILITY_MCPS_RO) $(STABILITY_MCPS_SKIPPED)

.PHONY: stability stability-strict-60min stability-selective-top3 \
        stability-reduced-30min stability-skipped-rows \
        $(addprefix stability-,$(STABILITY_MCPS_ALL))

# Default `make stability` runs the selective top-3 sweep — the wallclock
# decision the orchestrator pre-decided per 03-04 PLAN context.
stability: stability-selective-top3

# Per-MCP (full-mode) target — used by every recipe below for the
# interactive MCPs.
$(addprefix stability-,$(STABILITY_MCPS_FULL)): stability-%:
	@bash scripts/run_stability.sh $* $(STABILITY_MINUTES) full

# Read-only lightpanda: S1 only, S5 marked N/A_READONLY each iteration.
stability-lightpanda:
	@bash scripts/run_stability.sh lightpanda $(STABILITY_MINUTES) read-only

# Skipped rows: firecrawl (loopback-unreachable) + browser-use-agent (LLM-gated).
# Duration arg is ignored when MODE=skip — pass 0 for clarity.
stability-firecrawl:
	@STABILITY_SKIP_REASON=LOOPBACK_UNREACHABLE \
	    bash scripts/run_stability.sh firecrawl 0 skip

stability-browser-use-agent:
	@STABILITY_SKIP_REASON=LLM_KEY_ABSENT \
	    bash scripts/run_stability.sh browser-use-agent 0 skip

stability-skipped-rows: stability-firecrawl stability-browser-use-agent

# ── Strict 60-min × 6 SCORED runs (~6.5 hours wall-clock) ──
# All SCORED MCPs run at 60 minutes; SKIPPED rows still get a metadata file.
stability-strict-60min:
	@echo "stability-strict-60min: starting 60min × 6 SCORED runs (~6.5 hours)"
	@STABILITY_WALLCLOCK=strict_60min STABILITY_MINUTES=60 $(MAKE) stability-playwright STABILITY_MINUTES=60
	@STABILITY_WALLCLOCK=strict_60min $(MAKE) stability-cloakbrowser STABILITY_MINUTES=60
	@STABILITY_WALLCLOCK=strict_60min $(MAKE) stability-lightpanda STABILITY_MINUTES=60
	@STABILITY_WALLCLOCK=strict_60min $(MAKE) stability-chrome-devtools STABILITY_MINUTES=60
	@STABILITY_WALLCLOCK=strict_60min $(MAKE) stability-obscura STABILITY_MINUTES=60
	@STABILITY_WALLCLOCK=strict_60min $(MAKE) stability-browser-use-direct STABILITY_MINUTES=60
	@STABILITY_WALLCLOCK=strict_60min $(MAKE) stability-skipped-rows

# ── Selective: top-3 (cloakbrowser/playwright/lightpanda) at 60min,
# rest (browser-use-direct/chrome-devtools/obscura) at 30min (~4.5 hours) ──
# This is the orchestrator's pre-decided wallclock budget for Plan 03-04.
stability-selective-top3:
	@echo "stability-selective-top3: starting 3×60min + 3×30min runs (~4.5 hours)"
	@STABILITY_WALLCLOCK=selective_top3_60min_rest_30min $(MAKE) stability-cloakbrowser STABILITY_MINUTES=60
	@STABILITY_WALLCLOCK=selective_top3_60min_rest_30min $(MAKE) stability-playwright STABILITY_MINUTES=60
	@STABILITY_WALLCLOCK=selective_top3_60min_rest_30min $(MAKE) stability-lightpanda STABILITY_MINUTES=60
	@STABILITY_WALLCLOCK=selective_top3_60min_rest_30min $(MAKE) stability-browser-use-direct STABILITY_MINUTES=30
	@STABILITY_WALLCLOCK=selective_top3_60min_rest_30min $(MAKE) stability-chrome-devtools STABILITY_MINUTES=30
	@STABILITY_WALLCLOCK=selective_top3_60min_rest_30min $(MAKE) stability-obscura STABILITY_MINUTES=30
	@STABILITY_WALLCLOCK=selective_top3_60min_rest_30min $(MAKE) stability-skipped-rows

# ── Reduced 30-min × 6 (~3.5 hours wall-clock) ──
stability-reduced-30min:
	@echo "stability-reduced-30min: starting 30min × 6 SCORED runs (~3.5 hours)"
	@STABILITY_WALLCLOCK=reduced_30min_all $(MAKE) stability-playwright STABILITY_MINUTES=30
	@STABILITY_WALLCLOCK=reduced_30min_all $(MAKE) stability-cloakbrowser STABILITY_MINUTES=30
	@STABILITY_WALLCLOCK=reduced_30min_all $(MAKE) stability-lightpanda STABILITY_MINUTES=30
	@STABILITY_WALLCLOCK=reduced_30min_all $(MAKE) stability-chrome-devtools STABILITY_MINUTES=30
	@STABILITY_WALLCLOCK=reduced_30min_all $(MAKE) stability-obscura STABILITY_MINUTES=30
	@STABILITY_WALLCLOCK=reduced_30min_all $(MAKE) stability-browser-use-direct STABILITY_MINUTES=30
	@STABILITY_WALLCLOCK=reduced_30min_all $(MAKE) stability-skipped-rows

tls:
	@echo "tls: deferred to G-710 (scope cut 2026-05-22)"

# ─── Cold-start measurement (Phase 3 plan 03-03, MEAS-01) ────────────────────
# Per-MCP target: spawn the MCP via mcp.client.stdio, time the 3 segments
# (t_resolve / t_spawn / t_first_useful) across N_RUNS cold + N_RUNS warm
# samples, write results/$(DATE)/<mcp>/cold_start.json.
#
# Cold means: pkill -f <pattern> + 200ms sleep before each sample.
# Warm means: no pkill (binary in OS page cache from the prior cold run).
# N_RUNS defaults to 5 per the plan's "median of >=5" requirement.
#
# The per-MCP rule fans through the static-pattern list to keep GNU Make 3.81
# (macOS system Make) happy, same convention as bench-<mcp>.

N_RUNS ?= 5
COLD_START_MCPS := playwright chrome-devtools lightpanda obscura firecrawl cloakbrowser browser-use-direct browser-use-agent

.PHONY: cold-start $(addprefix cold-start-,$(COLD_START_MCPS))

$(addprefix cold-start-,$(COLD_START_MCPS)): cold-start-%:
	@mkdir -p $(RESULTS_DIR)/$*
	@.venv/bin/python -m bench.measure_cold_start $* \
	    --out $(RESULTS_DIR)/$*/cold_start.json \
	    --n-runs $(N_RUNS)

# Aggregate: run sequentially per Phase 2 sequential-runs contract
# (orphan-process clashes if parallel).
cold-start: $(addprefix cold-start-,$(COLD_START_MCPS))
	@echo "cold-start: complete — see $(RESULTS_DIR)/*/cold_start.json"

# Legacy alias the help target advertised; now points at the real sweep.
coldstart: cold-start

# ─── Housekeeping ────────────────────────────────────────────────────────────

clean:
	rm -rf node_modules .venv
	find . -type d \( -name __pycache__ -o -name '*.egg-info' \) -prune -exec rm -rf {} +
