<!-- GSD:project-start source:PROJECT.md -->
## Project

**Web-Agent MCP Comparison**

A public benchmark of browser-automation MCP servers driven by Claude Code. Stage 1 of a 3-stage pipeline that ends in production agent tooling: this repo scores candidate MCPs on standardized job-application fixtures, the winners graduate into the private `terminal-craft` toolkit (Stage 2), which is then wired into the `Kestrel` and `Eyas` job-hunting agents (Stage 3). Reproducible methodology so external readers can clone, run, and confirm the scores.

**Core Value:** **Pick the right browser MCP(s) for production agent use, backed by reproducible scores on the same fixtures every candidate is measured against.** If everything else fails, the comparison matrix and the graduate-to-toolkit recommendation are what must exist at the end.

This file does not restate global rules — read `~/.claude/CLAUDE.md` first.

### Constraints

- **Tech stack**: Python 3 (scoring), Markdown (results), shell (test orchestration). No framework — keep it dogfood-friendly.
- **Reproducibility**: Methodology must be runnable by a third party with only the public repo. No internal-only fixtures, no rbw-gated secrets in the core flow.
- **API keys**: `FIRECRAWL_API_KEY` required for firecrawl MCP (in rbw under `firecrawl.dev` → `Firecrawl_API`). If absent, partial scoring (6/7) is acceptable per G-703 AC. No other paid keys. `check_prereqs.sh` reads the var straight from the environment — export it before `make bench` (e.g. `export FIRECRAWL_API_KEY=$(rbw get firecrawl.dev --field Firecrawl_API)`).
- **Sandbox-only MCPs**: `cloakbrowser` is closed-source binary touching cookies — never point at authenticated host pages. Tested only against the public Greenhouse + Ashby fixtures.
- **Public repo**: `.mcp.json` is committed and visible. Acceptable for a research repo; the candidate list IS the research artifact.
- **Linear traceability**: G-703 is the umbrella ticket (estimate=16 = break-before-cycle signal). Splits into ~7 per-MCP scoring tickets + 1 synthesis ticket before pulling into a cycle.
- **Cross-machine**: Mac Mini has all 7 binaries installed; MacBook parity not yet verified. The `.mcp.json` will silently fail to spawn missing binaries.
<!-- GSD:project-end -->

## Commands

The `Makefile` is the single-command reproducibility surface. `make help` lists everything; the load-bearing targets:

| Command | What it does |
|---|---|
| `make check` | Prereq gate (`scripts/check_prereqs.sh`); first step of every other target |
| `make bench` | Full run — `check`, then all 7 `bench-<mcp>`, then `score` |
| `make bench-<mcp>` | One MCP only (`playwright`, `browser-use`, `chrome-devtools`, `lightpanda`, `obscura`, `firecrawl`, `cloakbrowser`) via `scripts/run_mcp_session.sh` |
| `make score` | Aggregate `results/<DATE>/scores.json` through `scoring/score.py` (`uv run`) |
| `make versions` | Refresh `results/<DATE>/versions.{json,lock.md}` reproducibility manifest |
| `make cold-start` / `make cold-start-<mcp>` | Cold+warm latency sweep (override `N_RUNS=10` for more samples) |
| `make fixtures-serve` / `-stop` / `-status` | Local fixture HTTP server on `127.0.0.1:8765` (`scripts/serve_fixtures.sh`) |
| `make smoke-live` | One-shot HEAD against live source URLs — drift detector, NOT scored |
| `make stability` / `make tls` | Stubs, deferred to G-710 |
| `make clean` | Remove `.venv`, `node_modules`, `__pycache__` |

Override the results directory date for reruns: `make bench DATE=2026-05-22`.

Python is run through `uv` (`uv.lock` committed for bit-for-bit reproducibility). Tests: `uv run pytest`.

## Architecture

Flat, script-driven harness — no framework. Data flows MCP session → per-MCP scores → aggregated matrix.

- `scoring/score.py` — load-bearing scoring engine (sacrosanct per `.planning/research/ARCHITECTURE.md`); `scoring/rubric.md` is the locked 8-dimension rubric.
- `scripts/` — shell orchestration: `check_prereqs.sh` (gate), `run_mcp_session.sh` (per-MCP driver), `serve_fixtures.sh`, `run_stability.sh`, `snapshot_fixtures.sh`, plus `aggregate_scores.py` / `score_with_na.py`.
- `bench/` — Python helpers: version capture, tool-call/inventory aggregation, cross-cut summary, report + recommendation builders.
- `fixtures/` — pinned Greenhouse + Ashby snapshots (`snapshots/`, `framework-variants/`) the candidates are measured against.
- `prompts/` — `stage_walk.md`, the standardized task fed to each MCP.
- `results/<DATE>/` — per-run output: `scores.json`, `versions.*`, `<DATE>_run.md`.
- `docs/` — reader-facing `REPRODUCIBILITY.md`, `RUNNING_ON_LINUX.md`, external findings.
- `.mcp.json` — committed candidate-MCP list (the research artifact itself).

## Conventions

- New shell goes in `scripts/`, new Python helpers in `bench/`, wired through Makefile targets — match the existing static-pattern-rule style (the per-MCP target uses static-pattern rules, not `bench-%:`, because macOS system Make is GNU 3.81).
- Keep the candidate set in `Makefile` `MCPS`, `.mcp.json`, and `scripts/check_prereqs.sh` in sync — adding a 9th MCP touches all three.
- Per-MCP tickets use `linearis` CLI, never the Linear MCP tools (global rule).

## Reference: candidate versions & stack

The full pinned-version table, per-MCP compatibility notes, breaking changes, measurement tooling, and the "what NOT to use" supply-chain notes live in **`.planning/research/STACK.md`** (with `FEATURES.md`, `PITFALLS.md`, `ARCHITECTURE.md`, `SUMMARY.md` alongside it). That is the source of truth for version pins — do not duplicate it here. Quick reminders that bite during a run:

- Pin npm MCPs to the `latest` dist-tag, never `next` (e.g. `@playwright/mcp` `next` is a nightly that drifts every 24h).
- `firecrawl-mcp` GitHub releases are dead since `v3.2.1` (2025-09) — check `npm view firecrawl-mcp version` and run `npm audit signatures` before pinning.
- `lightpanda` self-reports its version inconsistently; don't trust the runtime version string.

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->
