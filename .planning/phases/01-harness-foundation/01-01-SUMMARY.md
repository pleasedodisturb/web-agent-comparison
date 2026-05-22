---
phase: 1
plan: 01
subsystem: harness-foundation
tags: [makefile, prereqs, uv, npm, bootstrap]
title: "Makefile + check_prereqs.sh + uv/npm bootstraps"
requires: []
provides:
  - "single-command reproducibility surface (`make bench`)"
  - "prereq gate (`scripts/check_prereqs.sh`) usable by every downstream Phase 1 plan"
  - "uv.lock + package-lock.json — bit-for-bit dep reproducibility (REPRO-02)"
affects:
  - .planning/REQUIREMENTS.md  # HARNESS-06, REPRO-02 satisfied
tech-stack:
  added:
    - "uv 0.11 + Python 3.12 (managed by uv)"
    - "Node 22 LTS + npm 11"
    - "mcp 1.16, anthropic 0.49, httpx 0.28, tiktoken 0.13 (Python)"
    - "@playwright/mcp 0.0.75, chrome-devtools-mcp 1.0.1, obscura-mcp 0.1.4-3, firecrawl-mcp 3.17.0, @modelcontextprotocol/inspector 0.21.2 (npm)"
  patterns:
    - "Single-command Makefile surface — `make bench` → check → all 7 bench-<mcp> → score"
    - "Static-pattern rules over `bench-%:` to work around macOS GNU Make 3.81 phony-prereq bug"
    - "Per-MCP remediation strings live in `remediation_for()` case statement in check_prereqs.sh"
key-files:
  created:
    - Makefile
    - scripts/check_prereqs.sh
    - .gitignore
    - pyproject.toml
    - uv.lock
    - package.json
    - package-lock.json
    - .python-version
    - .nvmrc
  modified: []
decisions:
  - "Static-pattern rule (`$(addprefix bench-,$(MCPS)): bench-%: check`) chosen over plain pattern rule (`bench-%:`) — macOS ships GNU Make 3.81 which has a known phony-prereq bug that silently no-ops plain pattern rules."
  - "FIRECRAWL_API_KEY treated as WARNING not ERROR in check_prereqs.sh — 6/7 partial run is acceptable per PROJECT.md."
  - "`make score` uses `uv run python` not raw `.venv/bin/python` so reproducibility flows through the lockfile contract end-to-end."
  - "Used modern `[dependency-groups]` table in pyproject.toml rather than deprecated `[tool.uv].dev-dependencies` (which emits a future-removal warning under uv 0.11)."
  - "Did NOT commit `package-audit.log` — `npm audit signatures` returned clean (341 verified, 33 attestations) on the first run, so there's nothing to document."
metrics:
  duration_minutes: 35
  completed_date: 2026-05-22
  tasks_completed: 5
  files_created: 9
  files_modified: 0
  commits: 3
---

# Phase 1 Plan 01: Makefile + check_prereqs.sh Summary

## Goal achieved

Stood up the single-command reproducibility surface (`make bench`) and the prerequisite gate that runs before any MCP is touched. The toolchain foundation every other Phase 1 plan depends on is now in place: a clean clone can reach `make check` and `make bench-playwright` deterministically; only the real driver script (plan 01-04) is missing.

## What was built

### `pyproject.toml` + `uv.lock` + `.python-version`

uv-managed Python 3.12 project. Dependencies pinned per CONTEXT.md decisions:
- `mcp>=1.16,<1.17` — stdio client for cold-start measurement and per-MCP `initialize` probes
- `anthropic>=0.40,<0.50` — `count_tokens()` for the schema-scope token column
- `httpx>=0.28` — for the future TLS-fingerprint capture endpoints (G-710)
- `tiktoken>=0.7` — tokenizer for the payload-scope column

37 transitive packages, resolved by uv into `uv.lock` (committed verbatim).

Notable: switched to modern `[dependency-groups]` syntax — uv 0.11 emits a future-removal warning for `[tool.uv].dev-dependencies`.

### `package.json` + `package-lock.json` + `.nvmrc`

Node-side dep closure for the 4 npm-based MCPs + the MCP Inspector. All pinned to RESEARCH §1 verified-latest versions:
- `@playwright/mcp@0.0.75`
- `chrome-devtools-mcp@1.0.1`
- `obscura-mcp@0.1.4-3`
- `firecrawl-mcp@3.17.0`
- `@modelcontextprotocol/inspector@0.21.2`

`npm audit signatures` returned clean: 341 packages verified, 33 with attestations. No `package-audit.log` needed.

The `obscura-mcp@0.1.4-3` deprecation notice ("upstream ships native MCP via `obscura mcp`") is expected — that IS the version locked by the plan; the deprecation surfaces a future upgrade signal for Phase 2 to act on.

### `scripts/check_prereqs.sh`

Reads `.mcp.json` via `jq`, validates each MCP's `.command` field is on PATH, plus host tools (`jq`, `node`, `npm`, `python3`, `uv`, `envsubst`, `wget`). Per-binary remediation strings hard-code the pinned install commands from RESEARCH §1. `FIRECRAWL_API_KEY` is treated as a WARNING (partial 6/7 run is acceptable per PROJECT.md).

Bash 5+ with `set -euo pipefail`, no GNU-only flags — portable to a clean clone on any macOS or Linux host.

### `Makefile`

Targets: `bench`, `bench-<mcp>`, `score`, `check`, `clean`, `coldstart`, `stability`, `tls`, `help`.

- `bench` depends on `check` FIRST, then all `bench-<mcp>`, then `score`. `make -n bench` confirms `scripts/check_prereqs.sh` is the first line of the target plan (HARNESS-06 satisfied).
- `bench-<mcp>` uses a **static-pattern rule** rather than a plain `bench-%:` pattern rule because macOS ships GNU Make 3.81, which has a known phony-prereq bug. The static-pattern form (`$(addprefix bench-,$(MCPS)): bench-%: check`) works under both 3.81 and 4.x.
- Until `scripts/run_mcp_session.sh` lands in plan 01-04, each `bench-<mcp>` recipe emits `"scripts/run_mcp_session.sh not yet installed (driver lands in plan 01-04)"` and exits 0.
- Stub targets `coldstart`, `stability`, `tls` emit `"<target>: deferred to G-710 (scope cut 2026-05-22)"` and exit 0. The surface area is locked from day 1.

### `.gitignore`

Excludes `.venv/`, `node_modules/`, `__pycache__/`, `.env*`, `.envrc`, `/tmp/firecrawl_api_token`, `results/*/.scratch/`, OS cruft, and editor temp files. Explicitly documents the files that MUST stay tracked (`.mcp.json`, `uv.lock`, `package-lock.json`, etc.) in a trailing comment block.

## Verification

All acceptance bullets met:

| Check | Result |
|---|---|
| `make check` exits 0 on Mac Mini | PASS — all 7 binaries detected, 0 warnings |
| `make -n bench` shows `check` as the FIRST step | PASS — first line is `scripts/check_prereqs.sh` |
| `uv sync --locked` exits 0 | PASS — 37 packages resolved deterministically |
| `npm ci` exits 0 | PASS — 341 packages installed from lockfile |
| `.venv/bin/python -c "import mcp, anthropic, httpx, tiktoken"` | PASS — all four import cleanly |
| `npx -y -p @playwright/mcp@0.0.75 playwright-mcp --version` | PASS — prints `Version 0.0.75` |
| `make bench-playwright` emits plan-01-04 deferral message | PASS |
| `make coldstart/stability/tls` emit G-710 deferral and exit 0 | PASS for all three |
| `make score` (no scores.json) emits remediation and exits 1 | PASS |
| `git check-ignore -v .venv` → ignored | PASS |
| `git check-ignore -v .mcp.json` → NOT ignored | PASS (exit 1) |
| `npm audit signatures` clean | PASS — 341/341 verified, 33 attestations |
| Failure-mode check_prereqs (PATH stripped) → exit 1 with remediation | PASS — 3 missing binaries reported with install commands |

## Files modified

| File | Status | Purpose |
|---|---|---|
| `Makefile` | NEW | Single-command reproducibility surface |
| `scripts/check_prereqs.sh` | NEW | Prereq gate; reads `.mcp.json` + host tools |
| `.gitignore` | NEW | Repo hygiene |
| `pyproject.toml` | NEW | uv-managed Python 3.12 project root |
| `uv.lock` | NEW | Committed Python dep lockfile |
| `package.json` | NEW | npm root with the 4 npm-based MCPs + Inspector |
| `package-lock.json` | NEW | Committed Node dep lockfile |
| `.python-version` | NEW | `3.12` |
| `.nvmrc` | NEW | `22` |

## Commits

| Hash | Subject |
|---|---|
| `eb82695` | G-703: bootstrap uv + npm dep closures for the harness |
| `cde1269` | G-703: add Makefile + check_prereqs.sh — single-command harness surface |
| `0504ecd` | G-703: add .gitignore — exclude .venv/node_modules/secrets/scratch dirs |

## Deviations from Plan

### [Rule 1 — Bug] Static-pattern rule replacing plain pattern rule

- **Found during:** Task 4 verification
- **Issue:** The plan specified `bench-%: check` as a plain pattern rule. Under macOS GNU Make 3.81 (the system make), this silently no-ops with `"Nothing to be done for `bench-playwright'"` even though the target is `.PHONY` and its prerequisite is satisfied. The recipe never runs.
- **Fix:** Switched to a static-pattern rule: `$(addprefix bench-,$(MCPS)): bench-%: check`. This is valid under both Make 3.81 and 4.x, enumerates the 7 targets explicitly, and runs the recipe correctly. The `$*` automatic variable still expands to the MCP name as the plan expects.
- **Files modified:** Makefile
- **Commit:** `cde1269`

### [Rule 3 — Blocking] pyproject.toml `[tool.uv].dev-dependencies` deprecated

- **Found during:** Task 1 `uv lock`
- **Issue:** uv 0.11 emits a deprecation warning: `The 'tool.uv.dev-dependencies' field is deprecated and will be removed in a future release; use 'dependency-groups.dev' instead`.
- **Fix:** Replaced `[tool.uv]\ndev-dependencies = []` with `[dependency-groups]\ndev = []` (the modern syntax). Re-ran `uv lock` clean — no warnings.
- **Files modified:** pyproject.toml
- **Commit:** `eb82695`

### [Decision] `package-audit.log` not committed

- **Found during:** Task 2
- **Issue:** Plan said to capture `npm audit signatures` output to `package-audit.log` "if it errors out." The audit returned clean (341/341 verified, 33 attestations) on the first run, so there's nothing to document.
- **Fix:** No log committed. Audit-clean state recorded in this SUMMARY instead.
- **Files modified:** None
- **Commit:** N/A

## Out of scope (per plan)

- Real MCP session driver (`scripts/run_mcp_session.sh`) — lands in plan 01-04.
- Pre-commit hook for `.mcp.json` inline-secret blocking — plan 01-02.
- Snapshot fixtures + `wget --mirror` of Greenhouse/Ashby — plan 01-03.
- `obscura-mcp install` engine-download — surfaced in the remediation string only; attempting it is Phase 2.
- TLS, cold-start, stability work — deferred to G-710.

## Notes for downstream plans

- **Plan 01-04 (run_mcp_session.sh):** The Makefile already routes `make bench-<mcp>` to `scripts/run_mcp_session.sh $*` with an executable-existence guard. Drop the script at that path with `chmod +x` and `make bench-playwright` will start invoking it without any Makefile edit.
- **Plan 01-02 (pre-commit hook):** The hook can `grep -E '(fc-|sk-|Bearer )' .mcp.json` and block on match; the existing `.mcp.json` already uses `${VAR}` references, so the hook won't fire on the current content.
- **Plan 01-03 (snapshot fixtures):** `wget` is now a checked prereq, so the fixture-capture script can assume it's available; otherwise `make check` would have failed loud.
- **Plan 01-06 (`bench/capture_versions.py`):** Reads `uv.lock` + `package-lock.json` for dep versions; both files are now committed with the canonical versions to capture.

## Self-Check: PASSED

- [x] `Makefile` exists at repo root
- [x] `scripts/check_prereqs.sh` exists and is executable
- [x] `.gitignore`, `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `.python-version`, `.nvmrc` all exist at repo root
- [x] Commit `eb82695` in `git log`
- [x] Commit `cde1269` in `git log`
- [x] Commit `0504ecd` in `git log`
- [x] `make check` exits 0
- [x] `make -n bench` first line is `scripts/check_prereqs.sh`
- [x] No `.venv/`, `node_modules/`, or secrets in `git status`
