# Phase 1: Harness Foundation - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning
**Mode:** Smart discuss (infrastructure phase — grey areas already resolved in `.planning/research/`; CONTEXT.md captures the resolved decisions for plan-phase)

<domain>
## Phase Boundary

Build the runner, snapshot fixtures, retry gate, scrub pipeline, and version-lock infrastructure so a user can drive one Claude Code session per MCP through the locked S1-S8 prompt and capture self-contained evidence directories. Stop condition: `make bench-playwright && make score` reproduces the 2026-03 Playwright composite within ±0.5 of 9.07 against the self-hosted snapshot fixtures. The harness must demonstrably measure what the wave needs to measure before any other MCP is added in Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Orchestration Model
- One Claude Code session per MCP, driven by `claude --print --output-format stream-json` with `--allowedTools "mcp__${MCP}__*,Read,Write,Bash"` so each MCP lives or dies on its own surface (no silent WebFetch fallback).
- The session's `stream-json` IS the transcript; per-MCP evidence directories are self-contained and re-runnable in isolation.
- File-mediated stage handoff — any single S1-S8 step can be re-run without re-driving the whole session.

### Toolchain — resolved from cross-document tensions in SUMMARY.md
- **Makefile** at repo root (not Justfile) — single-command reproducibility surface: `make bench`, `make bench-<mcp>`, `make tls`, `make coldstart`, `make stability`, `make score`. Matches dogfood-friendly idiom from PROJECT.md.
- **Python 3.12 + uv 0.7.x with committed `uv.lock`** — extends existing `scoring/score.py`; `uv sync --locked` for bit-for-bit reproducibility.
- **Node 22 LTS + `package-lock.json`** — for the 4 npm MCPs (playwright, chrome-devtools, obscura, firecrawl).
- **Bash 5+** for orchestration (matches 2026-03 wave style).
- **NO Docker / NO devcontainer** — they contaminate cold-start and TLS-fingerprint measurements, which are this wave's main differentiators. Reproducibility surface is the host environment + lockfiles, not a container.
- **`mcp` Python SDK 1.16.x (`mcp.client.stdio`)** for direct stdio cold-start probing (~30-50ms overhead vs MCP Inspector's ~300-500ms).
- **Anthropic SDK `count_tokens`** for clean per-MCP token accounting (free, separate rate limit).

### Cold-start measurement
- 3-segment split: `t_resolve` / `t_spawn` / `t_first_useful`. Both cold AND warm cache runs. Median of ≥5.
- Implemented via Python `mcp.client.stdio` (resolves STACK vs ARCHITECTURE tension in favour of STACK).

### TLS fingerprint capture
- **Deferred to G-710** per 2026-05-22 scope cut. Phase 1 still emits `tls.json` as a **stub** (empty object with `{"deferred": "G-710"}` provenance) so the evidence-directory shape is locked for the follow-up wave.

### Bot-detection adversaries
- **Deferred to G-710** per 2026-05-22 scope cut. No probe-set decision needed in this wave.

### Token measurement
- 3-scope split: `schema` (from `count_tokens`), `payload` (parsed JSON-RPC, headline column), `turn` (from `stream-json` `usage` blocks). All three captured per stage per MCP.

### Stability test
- 60-min S1+S5 loop against the **self-hosted snapshot fixture server** (NOT live URLs — they rate-limit mid-test). Per-tool-call 30s timeout. `ulimit -v` ceiling. Post-run `orphan_audit.log` shows 0 surviving processes.

### Fixtures — self-hosted snapshots
- `fixtures/snapshots/greenhouse_<date>/` + `fixtures/snapshots/ashby_<date>/` via `wget --mirror`.
- `bench/scrub_artifacts.py` runs OCR + name-regex to strip any PII (only `Jane Testworth` mock survives).
- Each snapshot directory carries `PROVENANCE.md` (source URL, capture date, scrubbed-fields list).
- Local server: `python3 -m http.server` bound to `127.0.0.1`.
- ONE live-URL smoke test per platform as drift detector (NOT scored — drift signal only).

### Retry gate + transient taxonomy
- `bench/transient.py` implements 3-pass-of-3 with explicit transient classifier (WebSocket 1001/1006, ECONNRESET, MCP `initialize` timeout, HTTP 429/503, Chromium SIGKILL).
- Score the **median** of 3 attempts. Publish `n/3 passes` in the matrix so readers see variance.

### N/A vs 0 semantics
- `scoring/score.py` is SACROSANCT — preserve 2026-03 comparability. If N/A handling needs a change, write a thin adapter in `scripts/aggregate_scores.py`. Read-only MCPs (lightpanda, firecrawl) get `N/A` on S4-S8, NOT `0`. `aggregate_scores.py` drops N/A cells from the weighted denominator.

### Failure-attribution taxonomy
- Any sub-rubric score < 5 carries a tag: `tool-bug` / `env-mismatch` / `target-flag` / `transient`. Per-row, per-stage. Enforced at `scores.json` emit time.

### Safety: inline-secret blocking
- Pre-commit hook regex-blocks any literal `fc-`, `sk-`, or `Bearer ` in `.mcp.json`. `${VAR}` references pass cleanly. Message: "Inline secret detected in .mcp.json — use ${ENV_VAR} reference instead."
- `.mcp.json` already uses `${VAR}` form for `FIRECRAWL_API_KEY`. Pre-commit hook enforces it stays that way.

### Process hygiene
- All MCP children spawned under `setsid` (process-group leader).
- Pre-run + post-run `ps` snapshot diff; any survivor in the process group gets `kill -KILL -<pgid>`.
- Per-tool-call 30s timeout enforced by harness (Claude Code enforces none).
- `orphan_audit.log` captures the diff result; must show 0 survivors for the run to be considered clean.

### Version lock + reproducibility manifest
- `bench/capture_versions.py` writes `versions.json` from live environment (npm + uv tool versions, per-MCP binary SHA256s, OS, Claude Code version, Node version, Python version).
- `versions.lock.md` is the human-readable companion.
- `uv.lock` + `package-lock.json` committed.
- Per-run `MACHINE.md` (`results/<date>/MACHINE.md`) capturing host spec + Claude Code session details + NTP-disciplined timestamp.

### Evidence-directory contract
Each MCP run produces `results/<date>/<mcp>/` with:
- `transcript.md` — human-readable
- `raw_stream.jsonl` — original stream-json
- `stage_s{1..8}.{yml,md,png,txt}` — per-stage outputs in whatever native format the MCP produces
- `cold_start.json` — populated by `scripts/measure_cold_start.sh`
- `tokens.json` — 3-scope token counts
- `tls.json` — stub (`{"deferred": "G-710"}`) in this wave
- `stability.log` — populated by `scripts/stability_loop.sh`
- `orphan_audit.log` — process-group diff
- `tools_inventory.json` — count + 6-category breakdown (populated at harness start)
- For skipped MCPs: `SKIPPED.md` with `reason`, `attempted_command`, `error_excerpt` per partial-run pattern.

### Linear sub-ticket split (OUTREACH-03)
- G-703 splits into 7 per-MCP scoring sub-tickets (`G-703 sub: score <mcp> end-to-end`) + 1 synthesis sub-ticket BEFORE Phase 2 starts.
- Use `linearis issues create --team G --project "Mac Setup & Environment" --parent-ticket G-703 --labels agent`.
- Linear has no `--estimate` flag — document estimates in description body.

### Claude's Discretion
- Pre-commit hook implementation: shell script vs Python — Claude picks whichever is more idiomatic for this repo (currently shell-heavy → shell).
- Snapshot capture script: shell wrapper around `wget --mirror` vs Python `requests`+`BeautifulSoup` — pick `wget --mirror` for fidelity to the original DOM (Greenhouse + Ashby React state matters).
- Echo-server fixture (for Sec-CH-UA-Platform leak detection) — **deferred to G-710** since TLS fingerprinting is deferred.
- Test harness language: pytest vs ad-hoc shell — start with shell (current style); add pytest only when a 9th MCP or third fixture site lands.
- Whether to commit `versions.lock.md` for Phase 1 (only Playwright tested) or wait until Phase 2 has all 7: commit a Phase 1 version covering Playwright + harness deps so the reproducibility shape is exercised end-to-end.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scoring/score.py` — 8-dim weighted scorer, sacrosanct, unchanged since 2026-03-31 wave.
- `scoring/rubric.md` — locked 8-dimension scoring rubric.
- `results/2026-03-31_run.md` — prior wave's published report; shape to mirror.
- `results/2026-05_addendum.md` — prior addendum.
- `results/scores.json` — existing schema `scoring/score.py` consumes.
- `results/playwright_s*.{yml,md,png}` + `results/lightpanda_s*.md` + `results/agent_browser_s*.txt` — prior-wave evidence artifacts; shape and naming convention to preserve.
- `fixtures/mock_data.json` + `fixtures/mock_resume.pdf` — Jane Testworth mock identity, reused.
- `.mcp.json` — committed at project scope, 7 MCPs registered with `${VAR}` env references.

### Established Patterns
- Python 3 + shell, no framework (per PROJECT.md constraint).
- Existing evidence-file naming: `<mcp>_s<N>_<descriptor>.<ext>` — preserve for direct visual diff with 2026-03.
- Project-scope `.mcp.json` (not user-scope) per G-688 lesson.
- Reproducibility via lockfiles + version manifest, not containers (per ARCHITECTURE.md).
- Public-repo hygiene: no PII in fixtures, no inline secrets, no machine identifiers in screenshots.

### Integration Points
- `scoring/score.py` consumes `scores.json` — `scripts/aggregate_scores.py` must emit this exact shape.
- `.mcp.json` is read by Claude Code on session spawn and by harness wrapper scripts via `jq`.
- Pre-commit hook integrates via `.git/hooks/pre-commit` or `.pre-commit-config.yaml` (project hasn't picked yet — start with raw `.git/hooks/pre-commit` for zero-install simplicity).
- Linear `linearis` CLI for sub-ticket creation.
- `FIRECRAWL_API_KEY` from `~/.zshrc` (rbw-backed); harness reads from env, never from disk.

</code_context>

<specifics>
## Specific Ideas

- The 2026-03 Playwright composite of **9.07** is the calibration target. Within ±0.5 = pass. Outside = STOP and surface to user (per HANDOFF-GSD-AUTO.md stop condition #1).
- Snapshot date in directory names: use `2026-05-22` (capture date) rather than `_latest_` symlink — explicit dates for reproducibility audit trail.
- `obscura-mcp install` should be attempted EARLY in Phase 1 so Phase 2 isn't surprised (per HANDOFF-GSD-AUTO.md). If it fails: document in `SKIPPED.md`, continue.
- `browser-use --mcp` initialize-timeout from 2026-05-21 testbench needs re-testing on v0.12.7 in Phase 2; Phase 1 just exercises Playwright end-to-end.

</specifics>

<deferred>
## Deferred Ideas

Items captured but explicitly NOT in this phase:
- TLS-fingerprint capture across all 7 MCPs → G-710 (this phase emits stub `tls.json` only).
- Bot-detection adversary harness → G-710.
- Cross-machine MacBook reproduction → G-710.
- Vendor courtesy-disclosure window → G-710.
- Echo-server header diff test (Sec-CH-UA-Platform leak detection) → G-710 (depends on TLS work).
- Stage 2 terminal-craft packaging → blocked on Phase 4 `recommendations.md`.
- Authenticated-session testing → out of scope for the entire wave (global safety policy).

</deferred>
