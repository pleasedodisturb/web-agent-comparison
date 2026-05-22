# G-703 Sub-Tickets (created 2026-05-22)

**Parent epic:** [G-703](https://linear.app/vitalik/issue/G-703) — Web-agent MCP comparison
**Filed by:** plan 01-02 (`G-703/phase-01-harness-foundation`) via `linearis` CLI
**Comment on parent:** posted, ID `3d084853-ae87-4811-b53c-8f48b674ce63`

This file is the in-repo source of truth for the OUTREACH-03 break-before-cycle split.
G-703 had estimate=16 (deliberate "break before cycle" signal). The 8 sub-tickets below
are the unit-of-work-sized children that Phase 2 picks up from.

## Per-MCP scoring sub-tickets (G-714..G-720)

One per candidate MCP. Each picks up its evidence-directory contract from
`.planning/phases/01-harness-foundation/01-CONTEXT.md` and the locked S1-S8 prompt
that lands in plan 01-04.

| Sub-Ticket | MCP | Title | Status |
|---|---|---|---|
| G-714 | playwright | G-703 sub: score playwright MCP end-to-end | Triage |
| G-715 | browser-use | G-703 sub: score browser-use MCP end-to-end | Triage |
| G-716 | chrome-devtools | G-703 sub: score chrome-devtools MCP end-to-end | Triage |
| G-717 | lightpanda | G-703 sub: score lightpanda MCP end-to-end | Triage |
| G-718 | obscura | G-703 sub: score obscura MCP end-to-end | Triage |
| G-719 | firecrawl | G-703 sub: score firecrawl MCP end-to-end | Triage |
| G-720 | cloakbrowser | G-703 sub: score cloakbrowser MCP end-to-end | Triage |

## Synthesis sub-ticket (G-721)

Blocked on all 7 per-MCP tickets above. Aggregates scores into
`results/<date>/scores.json`, runs `scoring/score.py`, writes
`results/recommendations.md`, updates README + HANDOFF.

| Sub-Ticket | Title | Status |
|---|---|---|
| G-721 | G-703 sub: synthesis — aggregate scores + write recommendations.md | Triage |

## Provenance

- All 8 tickets created via `linearis issues create --team G --project "Mac Setup & Environment" --parent-ticket G-703 --labels agent --priority 3 ...` (2026-05-22).
- `linearis` version: 2025.12.3. Linear has no `--estimate` flag — estimates are documented inline in each ticket's description body.
- Sub-issue list confirmed via `linearis issues read G-703` JSON output (`.subIssues[]`).
- Parent G-703 received a comment listing all 8 IDs at the same time as this file was written.

## STATUS: COMPLETE

All 8 sub-tickets exist in Linear and are reachable as children of G-703. Phase 2 may
begin once Phase 1 emits its calibration verdict (`make bench-playwright && make score`
within ±0.5 of 9.07).
