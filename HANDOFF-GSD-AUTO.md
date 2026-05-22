# HANDOFF — GSD Autonomous Execution

**Created:** 2026-05-22 (after PR #4 merge — GSD init complete).
**For:** the next Claude session that runs `/gsd:autonomous` on this repo.
**Predecessor handoff:** [HANDOFF.md](./HANDOFF.md) (still load-bearing for context on the 3-stage pipeline).

---

## TL;DR — start command

Open a new Claude Code session in `~/Projects/web-agent-comparison/` with a fat call budget, then paste:

```
/gsd:autonomous
```

That command walks through `discuss → plan → execute → verify` for every phase in `.planning/ROADMAP.md` (4 phases, 45 v1 reqs). Nothing else to type; everything you need is in `.planning/`.

---

## What's already been done (before you arrive)

- ✅ `.planning/` fully populated and committed to `main` (PR #4 merged at 2026-05-22T14:33:58Z, commit `3929f9c`).
- ✅ All 7 candidate MCPs registered in `./.mcp.json` at project scope. They auto-spawn when Claude Code opens this directory. Check via `/mcp` panel — expect all 7 connected.
- ✅ `FIRECRAWL_API_KEY` provisioned. `~/.zshrc` line 207-211 auto-populates `/tmp/firecrawl_api_token` from rbw (`firecrawl.dev` → `Firecrawl_API` field) on every interactive shell, then exports `FIRECRAWL_API_KEY` from it. Verify with `echo "${FIRECRAWL_API_KEY:0:4}…"`. If empty: `rbw get firecrawl.dev --field Firecrawl_API > /tmp/firecrawl_api_token && export FIRECRAWL_API_KEY=$(cat /tmp/firecrawl_api_token)`.
- ✅ Linear tickets in order: **G-703** = umbrella for this wave, **G-710** = deferred Wave 3 (detection + fingerprint). Cross-linked via comments on both sides.
- ✅ MCP master registry (`~/.claude/MCP_REGISTRY.md`) updated to reflect project-scope locations.
- ✅ Scope cuts applied (commit `579f539`): TLS fingerprint, bot detection, MacBook cross-machine reproduction, vendor courtesy disclosure all DEFERRED to G-710. Net v1 reqs: 52 → 45.

---

## Phase plan (4 phases, parallelisable 2↔3)

| # | Phase | Reqs | Stop condition |
|---|---|---|---|
| 1 | **Harness Foundation** (BLOCKER for everything else) | 22 | `make bench-playwright && make score` reproduces 2026-03 Playwright composite within ±0.5 of 9.07. If it doesn't, **STOP and ask** — the rubric or harness is broken. |
| 2 | **Per-MCP Scoring Runs** (parallel with Phase 3) | 2 | All 7 MCPs have evidence directories (or explicit `SKIPPED.md` per partial-run pattern). |
| 3 | **Cross-Cutting Measurements** (parallel with Phase 2) | 5 | All 7 MCPs have `cold_start.json` + `tokens.json` + `stability.log` + per-stage tool-call counts + `tools_inventory.json`. |
| 4 | **Synthesis** | 16 | `results/2026-05-XX-mcp-comparison.md` + `results/recommendations.md` + README updated + reproducibility manifest committed. |

Full details: `.planning/ROADMAP.md`.

---

## When to STOP and ask the user (only these)

These are the genuine "the world doesn't match the plan" cases. Everything else: handle and push.

1. **Phase 1 cannot reproduce 2026-03 Playwright score** (~9.07 ±0.5). This is the harness's go/no-go gate. If it fails, either the rubric is wrong, the harness is wrong, the fixtures drifted, or Playwright MCP regressed. **STOP and surface.**
2. **`browser-use` v0.12.7 `initialize` timeout still present** (2026-05 testbench bug). If the bug is fixed, just continue. If not, file a Linear bug ticket against browser-use, score the row as `0/15 — tool-bug` with footnote, and continue.
3. **Obscura engine install fails on macOS arm64**. Run `obscura-mcp install` early in Phase 1. If it fails: document in `SKIPPED.md` per partial-run pattern (6/7 acceptable per PROJECT.md), continue.
4. **A genuine "the world has changed" surprise** — Greenhouse / Ashby URL 404 (fixtures need re-snapshotting), Claude Code MCP lifecycle behaviour changed since plan was written, a candidate MCP yanked from npm, etc.

If you hit any of these, surface via a Linear comment on G-703 + paused state in `.planning/STATE.md`, then ask the user.

---

## What to handle without asking (push forward)

- Snapshot fixture creation (`wget --mirror` Greenhouse + Ashby into `fixtures/snapshots/<platform>_<date>/`, then `bench/scrub_artifacts.py`)
- `Makefile` + `bench/` scaffolding (per `.planning/research/ARCHITECTURE.md`)
- Pre-commit hook for inline-secret blocking in `.mcp.json` (per SAFETY-01)
- Process-group setsid wrapper + orphan audit (per HARNESS-07)
- Per-tool-call 30s timeout (per HARNESS-08)
- 3-pass-of-3 retry gate + transient taxonomy (per FAIRNESS-01/02)
- N/A vs 0 semantics in `scoring/score.py` (per FAIRNESS-03 — modify `score.py` cautiously, it's sacrosanct per ARCHITECTURE notes; if the change is non-trivial, prefer a thin adapter)
- Firecrawl-without-key partial-run pattern (per REPORT-09)
- Linear sub-ticket split: G-703 needs to break into 7 per-MCP scoring tickets + 1 synthesis ticket before Phase 2 starts (per OUTREACH-03). Use `linearis issues create` with `--team G --project "Mac Setup & Environment" --parent-ticket G-703 --labels agent`.

---

## Linear automation cheat sheet

```bash
# Create sub-ticket of G-703
linearis issues create "G-703 sub: score playwright MCP end-to-end" \
  --team G \
  --project "Mac Setup & Environment" \
  --parent-ticket G-703 \
  --labels "agent" \
  --priority 3

# Comment on parent
linearis comments create G-703 --body "Phase 2 sub-tickets filed: G-XXX..G-XXY"

# Update status
linearis issues update G-703 --status "In Progress"

# Note: linearis has no --estimate flag. Document estimates in the description body.
```

---

## Key references inside `.planning/`

- **PROJECT.md** — Core Value, Validated reqs, Out of Scope, Key Decisions
- **REQUIREMENTS.md** — 45 v1 reqs across HARNESS / FAIRNESS / MEAS / REPRO / REPORT / SAFETY / OUTREACH; Traceability table maps each to a phase
- **ROADMAP.md** — 4 phases with goals, requirements, success criteria, dependencies
- **STATE.md** — current blockers (3: browser-use init timeout, obscura arm64, cloakbrowser Linux); scope cuts; session continuity
- **research/SUMMARY.md** — synthesized recommendations from the 4 research agents (this is the quickest read; the four source files are deeper context)
- **research/PITFALLS.md** — 15 critical pitfalls with phase-mapped prevention work
- **research/ARCHITECTURE.md** — concrete 4-phase build order, component breakdown, single-command `make bench` reproducibility surface
- **config.json** — `model_profile=balanced`, `parallelization=true`, `mode=yolo`, all workflow toggles on, `code_review=true` (so `/gsd:ship` runs review before PR)

---

## Original 3-stage pipeline (do NOT start Stages 2-3)

```
   web-agent-comparison              terminal-craft                  Kestrel + Eyas
   ─────────────────────             ─────────────────               ──────────────
   THIS WAVE — public          →     private toolkit          →      production agents
   research + scoring                packaging                       (blocked on Stage 2)
```

Stage 2 (terminal-craft toolkit packaging) is BLOCKED on this wave's `results/recommendations.md`. Doing it concurrently violates the pipeline gate and would taint the scores by retrofitting them into a toolkit shape. SAFETY-05 + the Phase 4 wave-close ritual both audit for scope creep into Stage 2.

---

## Final notes

- The repo is **public** on GitHub (`pleasedodisturb/web-agent-comparison`). All commits land in the open. Public-grade hygiene: no inline secrets in `.mcp.json`, no real PII in fixtures (only `Jane Testworth` mock), no leaked machine identifiers in screenshots beyond what's already public on the prior 2026-03-31 report.
- If you encounter a GSD-tooling bug along the way (the previous GSD-init session found one: incremental rebase silently drops concurrent-merge content), file it as a Linear ticket against the GSD project, don't try to fix it in this repo.
- The previous session's failure mode worth knowing: GSD committed directly to `main` because of a workflow integration gap; was caught before push. The fix-pattern is `git update-ref refs/heads/main origin/main` + branch + PR. Don't repeat it: GSD should commit on a feature branch from the start.
