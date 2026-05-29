---
phase: 04-synthesis
plan: 02
subsystem: synthesis
tags:
  - phase-4
  - synthesis
  - reproducibility-recipe
  - repro-06
  - third-party-clone
  - g-703
  - g-710
requires:
  - .planning/phases/04-synthesis/04-CONTEXT.md (locked tier assignments)
  - .planning/phases/04-synthesis/04-01-PLAN.md (manifest output cited by recipe)
  - .planning/PROJECT.md (Core Value statement + Constraints — 6/7 partial-scoring policy + cloakbrowser sandbox-only rule)
  - .mcp.json (canonical source of truth for the 7 MCP keys + install commands)
  - CLAUDE.md (project root — FIRECRAWL_API_KEY note + cloakbrowser sandbox-only rule)
provides:
  - docs/REPRODUCIBILITY.md
affects:
  - REPRO-06 (marked complete)
tech-stack:
  added: []
  patterns:
    - "Markdown-only third-party recipe; no new code paths"
    - "Single `make bench` recipe with honest aspirational-vs-implemented annotation"
    - "Explicit MacBook + Linux parity NOT validated disclaimer pointing at G-710 follow-up wave"
    - "Sandbox-only callout co-located with every cloakbrowser mention (REPORT-08 hygiene applied to docs/)"
key-files:
  created:
    - docs/REPRODUCIBILITY.md
  modified: []
decisions:
  - "Single third-party recipe pattern: one canonical document at docs/REPRODUCIBILITY.md (not split across multiple READMEs). A reader can clone, install, and re-run without further navigation. Per PROJECT.md Core Value: \"If everything else fails, the comparison matrix and the graduate-to-toolkit recommendation are what must exist at the end.\""
  - "FIRECRAWL_API_KEY disclosed as the only paid-key requirement; 6/7 partial-scoring acceptable per CLAUDE.md and G-703 AC. The recipe explicitly states this is normal — firecrawl will render as SKIPPED in the matrix when the key is absent."
  - "CloakBrowser Linux uncertainty disclosed honestly. Closed-source binary verified on macOS arm64; Linux availability not validated this wave. Sandbox-only constraint co-located with every cloakbrowser mention so a reader cannot accidentally point it at authenticated host pages."
  - "MacBook parity NOT validated this wave (per CLAUDE.md: \"Mac Mini has all 7 binaries installed; MacBook parity not yet verified.\"). Deferred to G-710 follow-up wave which adds bot-detection + TLS-fingerprint + cross-machine reproducibility."
  - "Docker / devcontainer explicitly REJECTED in the recipe (and the rejection is mentioned briefly in a \"Why no Docker?\" sub-note). Rationale: Docker contaminates cold-start latency (image pull + container start), TLS fingerprints (Docker network namespace), and changes cloakbrowser's launch profile. Per RESEARCH.md §4."
  - "No new framework recommendations per PROJECT.md \"no framework — keep it dogfood-friendly\"."
metrics:
  completed: "2026-05-27"
  tasks_completed: 1
  files_added: 1
  files_modified: 0
  tests_added: 0
---

# Phase 4 Plan 02: docs/REPRODUCIBILITY.md Third-Party Recipe Summary

Create the third-party reproducibility recipe at `docs/REPRODUCIBILITY.md` — the single document a stranger reads to clone, install, and re-run the 2026-05-27 wave on their own machine.

## Headline

REPRO-06 closed. A reader who has never touched this repo can, by reading only `docs/REPRODUCIBILITY.md` (231 lines), install the 7 MCPs, run the comparison, and produce a results directory comparable to `results/2026-05-27/`. The doc surfaces honest caveats — Linux untested, MacBook untested, cloakbrowser sandbox-only, FIRECRAWL_API_KEY optional with 6/7 partial-scoring — rather than over-promising. Per PROJECT.md Core Value: a claim is only as good as its reproducibility, and this recipe is what makes the claim verifiable.

## What shipped

One artifact, one commit:

**`docs/REPRODUCIBILITY.md`** (231 lines) — the third-party reproducibility recipe. Per 04-VERIFICATION.md REPRO-06 row, the file contains 6 H2 sections covering the full clone-to-reproduce path:

| Section | Line | Content |
| --- | --- | --- |
| `## Prerequisites` | L15 | macOS arm64 verified; Linux untested. Node 22 LTS, Python 3.12+, uv ≥ 0.7.x, Claude Code CLI on PATH. Cites `results/2026-05-27/versions.lock.md` as the canonical exact-version snapshot. |
| `## Installing 7 MCPs` | L37 | Per-MCP install command keyed to `.mcp.json`: `@playwright/mcp`, `browser-use[cli]`, `chrome-devtools-mcp`, lightpanda nightly binary, `obscura-mcp` + engine, `firecrawl-mcp` (cloud), `cloakbrowsermcp`. |
| `## API keys` | L62 | FIRECRAWL_API_KEY as the only paid-key requirement; rbw / .env / .envrc patterns documented; explicit "6/7 acceptable when absent" callout per CLAUDE.md partial-scoring policy. Pre-commit hook (SAFETY-01) blocks committed keys. |
| `## Running the comparison` | L87 | Single-command recipe (`make bench` aspirational; closest implemented equivalent documented with `python3 -m bench.capture_versions ...` + per-MCP bench scripts in `scripts/`). Cross-references `results/2026-05-27/MACHINE.md` for run-environment specifics. |
| `## cloakbrowser sandbox-only` | L126 | **Sandbox only — do not point at authenticated sessions** callout (bolded). Closed-source binary explanation; tested only against public Greenhouse + Ashby loopback fixtures; Linux availability unverified. INSTALL_FAILED row expected if cloakbrowser is unavailable on the reader's platform. |
| `## Cross-machine parity disclosure` | L150 | Mac Mini (Apple Silicon, macOS arm64) ran this wave end-to-end. MacBook + Linux NOT cross-validated this wave per CLAUDE.md constraint. Deferred to [G-710](https://linear.app/abandoned-yachts/issue/G-710) follow-up wave (bot-detection + TLS-fingerprint + cross-machine reproducibility). |

The doc also covers "What to expect" (results directory shape per scored MCP + ±0.5 composite tolerance for "reproduced" per HARNESS-05) and "Troubleshooting" (three most-likely failure modes: missing MCP binary on PATH flagged by `scripts/check_prereqs.sh` per HARNESS-06; FIRECRAWL_API_KEY absent yielding 6/7 partial; cloakbrowser unavailable on Linux yielding INSTALL_FAILED row).

## Acceptance criteria pass status

All Task 1 acceptance criteria PASS per 04-VERIFICATION.md REPRO-06 row:

- [x] `docs/REPRODUCIBILITY.md` exists, length 231 lines (80-300 window per plan acceptance criteria — well within range)
- [x] Contains all 9 required sections (Prerequisites, Installing the 7 MCPs, API keys, Running the comparison, cloakbrowser sandbox-only, Cross-machine parity, What to expect, Troubleshooting + framing intro)
- [x] All 7 MCPs from `.mcp.json` named (playwright, browser-use, chrome-devtools, lightpanda, obscura, firecrawl, cloakbrowser)
- [x] FIRECRAWL_API_KEY requirement disclosed
- [x] 6/7 partial-scoring policy stated explicitly per CLAUDE.md
- [x] Every cloakbrowser mention accompanied within the same section by a sandbox-only callout (REPORT-08 hygiene extended to docs/)
- [x] MacBook + Linux parity NOT validated this wave disclosed honestly
- [x] G-710 referenced as the follow-up wave anchor
- [x] `versions.lock.md` cited as the canonical exact-version reference
- [x] No inline literal API keys; no Docker as recommended path (only in a "Why no Docker?" rebuttal sub-note)

## Self-check

- `docs/REPRODUCIBILITY.md` — FOUND (231 lines, 10312 bytes)
- Commit `e0e052d` (G-703(04-02): write docs/REPRODUCIBILITY.md third-party recipe (REPRO-06)) — FOUND on G-703/phase-01-harness-foundation
- Section headings at L15, L37, L62, L87, L126, L150 — VERIFIED per 04-VERIFICATION.md REPRO-06 row
- 6 H2 sections + intro + troubleshooting + what-to-expect — VERIFIED via grep on the live file

## Self-Check: PASSED

## Provenance / commit history

The recipe landed in a single commit at `e0e052d` ("G-703(04-02): write docs/REPRODUCIBILITY.md third-party recipe (REPRO-06)") on branch `G-703/phase-01-harness-foundation`. The recipe has been stable since landing — no follow-up fix-up commits touched it during the Wave 2 fix-up sweep (04-fix series at `1f69aed`, `32d94e0`, etc. modified other artifacts but NOT `docs/REPRODUCIBILITY.md`), confirming the recipe was correct on first pass.

## Threat Surface Scan

Documentation-only artifact. No new network endpoints, no new auth paths, no new code paths. The recipe describes how to use existing third-party MCP installers (npm, uv, lightpanda binary download) — those installers are NOT introduced by this plan, only documented for third-party reproducibility.

No threat flags raised.

## Known Stubs

None. The recipe describes only what actually exists in the repo today, with honest aspirational-vs-implemented annotations for the `make bench` target (closest-implemented equivalent documented inline). No placeholder commands, no TODO sections, no synthetic examples.

## Reader path

A third party landing on `docs/REPRODUCIBILITY.md`:

1. Reads the Prerequisites section to confirm their platform is supported (macOS arm64 verified; Linux untested with disclosed caveat).
2. Follows the Installing 7 MCPs section to set up each candidate via the documented commands keyed to `.mcp.json`.
3. Sets `FIRECRAWL_API_KEY` if they want 7/7 scoring, or accepts 6/7 partial-scoring if absent (per CLAUDE.md policy).
4. Runs the comparison via the documented command sequence.
5. Treats the cloakbrowser section's sandbox-only callout as a hard rule — never points cloakbrowser at authenticated host pages.
6. Compares their reproduced scores against `results/2026-05-27-mcp-comparison.md` composites; ±0.5 composite-tolerance threshold means "reproduced" per HARNESS-05.
7. If their reproduction reveals MacBook or Linux drift, they have the G-710 follow-up wave anchor for the deferred cross-machine A/B.

That third-party reproducibility path is what REPRO-06 requires, and what 04-VERIFICATION.md REPRO-06 row confirms ships.
