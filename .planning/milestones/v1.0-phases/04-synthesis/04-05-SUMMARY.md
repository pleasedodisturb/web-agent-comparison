---
phase: 04-synthesis
plan: 05
subsystem: synthesis
tags:
  - phase-4
  - synthesis
  - readme
  - public-entry-point
  - report-07
  - g-703
  - g-710
requires:
  - .planning/phases/04-synthesis/04-CONTEXT.md (locked tier assignments)
  - results/recommendations.md (Stage 2 graduation gate — Plan 04-04)
  - results/2026-05-27-mcp-comparison.md (full scored report — Plan 04-03)
  - results/2026-03-31_run.md (historical context — preserve link)
  - .mcp.json (candidate-count = 7 invariant)
provides:
  - README.md (repo front door with 2026-05-27 headline verdict)
affects:
  - REPORT-07 (marked complete)
tech-stack:
  added: []
  patterns:
    - "Footnote-based 8-row-vs-7-candidate reconciliation (browser-use single SECONDARY row + FAIRNESS-05 footnote pointing to recommendations.md for the dual-row narrative)"
    - "Inline sandbox callout co-located with every cloakbrowser literal (REPORT-08 hygiene; both mentions carry the callout on the same line)"
    - "Demotion-not-deletion of the prior 2026-03 wave (link preserved as historical context; no longer primary headline; addendum callout replaced by Wave 2 callout)"
key-files:
  created: []
  modified:
    - README.md
decisions:
  - "Browser-use rendered as ONE SECONDARY row (not split into direct + agent) in the headline table to preserve the SAFETY-05 candidate-count = 7 invariant. The 8-row scoring split is surfaced via a parenthetical (`direct mode only — agent mode SKIPPED, see recommendations.md`) plus a footnote citing FAIRNESS-05. Readers count 7 candidates in the table; readers who follow the footnote see the full dual-row treatment in recommendations.md."
  - "SANDBOX-ONLY uses the exact uppercase-hyphenated form everywhere it appears in rendered content (matches Plan 04-04 recommendations.md heading per WARNING 3). No SANDBOX_ONLY identifier appears in the rendered README."
  - "Every cloakbrowser literal in the README is followed within the same line by `sandbox only — do not point at authenticated sessions` (REPORT-08 ≤5-line proximity rule satisfied with distance 0). Two cloakbrowser mentions, two sandbox callouts."
  - "Prior `📌 2026-05 update` callout pointing to `results/2026-05_addendum.md` REPLACED by the new `2026-05-27 update` callout. The addendum is superseded by the full Wave 2 report; the addendum file remains on disk for git-blame traceability but is no longer surfaced from README."
  - "Methodology summary paragraph compressed to one paragraph (6 sentences) citing all required hooks: 8-dim rubric, S1-S8 fixtures, REPRO-04 loopback snapshots, 7 candidates per .mcp.json, FAIRNESS-01 median-of-3, FAIRNESS-03 N/A-vs-UNTESTED, FAIRNESS-04 capability dual-view. Front-door reading time stays under 30 seconds."
  - "G-710 anchor + 5 explicit deferred-scope items listed in the Future waves section (TLS fingerprint, bot-detection adversary set, cross-machine reproducibility, Obscura Linux A/B, SANDBOX-ONLY stealth claim validation) — mirrors the recommendations.md Future Waves section so a reader landing on either file sees the same follow-up scope."
metrics:
  duration: "~2 minutes"
  completed: "2026-05-28"
  tasks_completed: 1
  files_modified: 1
  files_added: 0
  tests_added: 0
---

# Phase 4 Plan 05: README.md 2026-05-27 Headline Verdict Summary

Replace the README's 2026-03 app-level 5-agent headline table with the 2026-05-27 MCP-layer Stage 2 graduation tier table, add a one-paragraph methodology summary, and wire the primary CTA to `results/recommendations.md` (the Stage 2 graduation gate).

## Headline

REPORT-07 closed. A stranger landing on the repo's GitHub page now sees the 2026-05-27 MCP-layer comparison as the primary headline within 30 seconds: 4 tier rows (PRIMARY / SECONDARY / SANDBOX-ONLY / SKIP) covering exactly **7 candidates** (matches `.mcp.json` and SAFETY-05), with a footnote tying the 8-row scoring split to FAIRNESS-05 for readers who follow it. Primary CTAs point at `results/recommendations.md` (the Stage 2 unblock gate) and `results/2026-05-27-mcp-comparison.md` (full scored evidence). The 2026-03-31 wave is preserved as historical context — link intact, framing demoted.

## What shipped

One artifact, one commit:

1. **`README.md`** (84 lines, fits the 30-200 plan window) — rewritten with the 2026-05-27 headline verdict, methodology summary, key findings, results links, structure map, scoring explanation, and future waves section. H1 preserved (`# Web Agent Comparison Suite`). Commit `9c2a808`.

## Acceptance criteria pass status

All Task 1 acceptance criteria PASS:

- [x] File `README.md` exists, 84 lines (within 30-200 window)
- [x] H1 preserved: `# Web Agent Comparison Suite`
- [x] Latest wave callout block mentions `2026-05-27` and links to BOTH `results/recommendations.md` and `results/2026-05-27-mcp-comparison.md`
- [x] **BLOCKER 5 — Headline verdict table contains exactly 7 candidate names** (playwright, lightpanda, browser-use, chrome-devtools, firecrawl, cloakbrowser, obscura) — one per MCP in `.mcp.json`. browser-use appears as a single SECONDARY entry with parenthetical noting agent mode SKIPPED. No separate `browser-use-agent` row in the headline table. FAIRNESS-05 footnote ties the 8-row scoring split to the 7-candidate framing.
- [x] Table has 4 tier rows (PRIMARY, SECONDARY, `SANDBOX-ONLY`, SKIP). EXACT uppercase-hyphenated form for `SANDBOX-ONLY`; `SANDBOX_ONLY` literal absent from the rendered README.
- [x] Methodology summary paragraph present (cites 8-dim rubric, S1-S8 fixtures, REPRO-04 loopback snapshots, 7 candidates, FAIRNESS-01 median-of-3, FAIRNESS-03 N/A-vs-UNTESTED, FAIRNESS-04 capability dual-view)
- [x] Test stages S1-S8 list preserved
- [x] Key findings list updated for 2026-05 (lightpanda 51× cold-start, playwright 9.07 → 7.93, cloakbrowser 8.33 SANDBOX-ONLY, firecrawl loopback env-mismatch, browser-use direct vs agent)
- [x] Results section links to all four required targets: `results/2026-05-27-mcp-comparison.md` (full scored evidence — primary), `results/recommendations.md` (Stage 2 graduation gate — primary), `docs/REPRODUCIBILITY.md` (recipe), `results/2026-03-31_run.md` (historical)
- [x] Future waves section references G-710 with 5 explicit deferred-scope items
- [x] FAIRNESS-05 footnote present explaining the 8-row scoring split vs 7-candidate framing
- [x] Every cloakbrowser mention has a sandbox-only callout on the same line (`grep -c cloakbrowser README.md` = 2; `grep -ci 'sandbox only' README.md` = 2; co-located → distance 0 ≤ 5)
- [x] `scoring/score.py` and `scoring/rubric.md` unchanged (`git diff scoring/score.py scoring/rubric.md | wc -l` = 0)
- [x] No claims of intrinsic tool quality — framing throughout is "as of 2026-05-27, on the locked rubric + loopback fixtures"

Plan automated verify gate output: `OK: 7 candidate names in headline table` + `OK`.

## Self-check

- `README.md` — FOUND (84 lines)
- Commit `9c2a808` — FOUND in git log on `G-703/phase-01-harness-foundation`
- `scoring/score.py` unchanged — VERIFIED (`git diff scoring/score.py | wc -l` = 0)
- `scoring/rubric.md` unchanged — VERIFIED (`git diff scoring/rubric.md | wc -l` = 0)
- Link targets exist on disk:
  - `results/recommendations.md` — FOUND
  - `results/2026-05-27-mcp-comparison.md` — FOUND
  - `results/2026-03-31_run.md` — FOUND
  - `docs/REPRODUCIBILITY.md` — FOUND
  - `.mcp.json` — FOUND

## Self-Check: PASSED

## Deviations from Plan

None. The plan's content schedule + the 7-vs-8 reconciliation pattern + the sandbox-callout co-location pattern + the SANDBOX-ONLY display-name convention all came pre-specified from Plan 04-04. The README rewrite applied them verbatim. No Rule 1/2/3 fixes were needed; no Rule 4 architectural decisions surfaced.

## Threat Surface Scan

No new network endpoints, no new auth paths, no new file-access patterns, no schema changes. README is a Markdown document; no executable code introduced. No threat flags raised.

## Known Stubs

None. Every claim in the README is backed by an evidence link to one of:
- `results/recommendations.md` (tier rationale + per-MCP citations)
- `results/2026-05-27-mcp-comparison.md` (full scored matrix + deep-analysis stanzas)
- `results/2026-03-31_run.md` (historical wave + score baseline)
- `docs/REPRODUCIBILITY.md` (full reproducibility recipe)

Key-findings numbers (51× cold-start, 9.07 → 7.93 composite, 8.33 cloakbrowser composite, 9× SSR byte-count lift, 203-byte SPA refutation) are all cited by the linked reports.

## Reader path

A stranger landing on the GitHub repo page can:

1. Read the 1-paragraph framing → understand this is Stage 1 of a 3-stage pipeline scoring 7 browser-automation MCPs (~5 seconds).
2. Read the 2026-05-27 callout → see the new headline + click through to `results/recommendations.md` or `results/2026-05-27-mcp-comparison.md` (~10 seconds).
3. Scan the headline tier table → count 7 candidates, see SANDBOX-ONLY tier with the sandbox-only callout on cloakbrowser (~15 seconds).
4. Read the methodology summary paragraph → understand 8-dim rubric, S1-S8 fixtures, loopback snapshots, FAIRNESS hooks (~30 seconds).
5. Optionally scan key findings + future waves → see the 5 standout findings + G-710 anchor (~60 seconds).

Total time-to-understanding: under 60 seconds for the headline; under 30 seconds for the tier verdict. The repo front door now reflects Wave 2's primary headline; Wave 1's 2026-03-31 wave is preserved as historical context, not the primary framing. REPORT-07 closed.
