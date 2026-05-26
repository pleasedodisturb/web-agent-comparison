---
phase: 3
plan: 01
subsystem: cross-cutting-measurements/tool-call-counts + tools-inventory-rollup
tags: [meas-08, meas-09, aggregation, raw-stream, tools-inventory, fairness-06]
dependency_graph:
  requires:
    - 01-06   # bench/tools_inventory.py — used to gap-fill 4 missing inventories
    - 02-XX   # Phase 2 raw_stream.jsonl evidence per MCP × pass
  provides:
    - bench/aggregate_tool_calls.py             # MEAS-08 walker
    - bench/aggregate_tools_inventory.py        # MEAS-09 rollup
    - results/2026-05-26/<mcp>/tool_call_counts.json  (8 MCPs)
    - results/2026-05-26/<mcp>/tools_inventory.json   (8 MCPs total, +4 new)
    - results/2026-05-26/TOOLS_INVENTORY_SUMMARY.md   # side-by-side roll-up
  affects:
    - Phase 4 synthesis (will consume tool_call_counts.json + summary for the
      8-dim matrix's tool-efficiency annotation)
tech_stack:
  added: []  # stdlib-only aggregators; no new deps
  patterns:
    - "Write-marker stage attribution: a Write tool_use whose input.file_path matches stage_s<N>.<ext> is a stage boundary. Tool uses since the previous boundary (including the Write itself) attribute to S<N>. Leftover tail = 'unattributed'."
    - "assistant-only tool_use counting: the Claude session emits each tool_use twice (stream_event content_block_start + assistant message content). Counting the assistant block is canonical and deduped by construction."
    - "Median-of-three across PASS1-3 with missing-tool = 0: a tool that appears in 2 of 3 passes still produces a sensible integer median rather than being dropped."
    - "SKIPPED.md → status=SKIPPED row (no synthesized scores; the N/A-aware composite in scoring/score_with_na.py already excludes them)."
key_files:
  created:
    - bench/aggregate_tool_calls.py
    - bench/aggregate_tools_inventory.py
    - tests/test_aggregate_tool_calls.py
    - tests/test_aggregate_tools_inventory.py
    - results/2026-05-26/TOOLS_INVENTORY_SUMMARY.md
    - results/2026-05-26/playwright/tools_inventory.json
    - results/2026-05-26/playwright/tool_call_counts.json
    - results/2026-05-26/browser-use-direct/tools_inventory.json
    - results/2026-05-26/browser-use-agent/tools_inventory.json
    - results/2026-05-26/cloakbrowser/tools_inventory.json
    - results/2026-05-26/{chrome-devtools,cloakbrowser,obscura,browser-use-direct,browser-use-agent,firecrawl,lightpanda}/tool_call_counts.json
  modified: []
decisions:
  - "Counted tool_use blocks from `type==\"assistant\"` lines only. The stream_event line carries a duplicate content_block_start with the same tool_use id — counting both would inflate every number 2x and corrupt the Playwright batch-fill claim."
  - "Stage attribution uses Write-tool file_path against the regex `stage_s(\\d+)\\.[A-Za-z][A-Za-z0-9_.]*$`. This matches .yml/.md/.png/.txt PLUS .FAILED, .NA, and .diagnostic.yml suffixes used by Phase 2's failure-attribution taxonomy. Without `.FAILED`/`.NA` matching, firecrawl + obscura + lightpanda failure-row stages would all collapse to 'unattributed'."
  - "Median treats missing tools across passes as 0. Three passes: [click=2, click=0, click=4] median is 2, not 'undefined'. This matters when a deviant pass omits a tool that the median behavior of the MCP exhibits."
  - "browser-use-agent inventory is COPIED from browser-use-direct (Phase 2 audit confirmed both modes share the same tools/list surface; mode diverges at session runtime, not at MCP handshake). The mcp field is patched + a note recorded so downstream readers see provenance."
  - "playwright tool_call_counts.json records status=NO_EVIDENCE rather than a fabricated count. Playwright was not scored in Phase 2 (no PASS{1,2,3} dirs). The honest gap is more useful than a synthesized number."
metrics:
  duration_minutes: 35
  completed_date: 2026-05-27
---

# Phase 3 Plan 01: Tool-Call Counts + Tools-Inventory Rollup Summary

Two stdlib-only aggregators that recover MEAS-08 (per-stage tool-call counts)
and MEAS-09 (six-category tools-surface inventory) from existing Phase-2
evidence. Plus four fresh `tools_inventory.json` probes that close the
Phase-1-calibration gap (playwright, browser-use-direct, browser-use-agent,
cloakbrowser). No Phase-2 harness re-runs needed — pure aggregation. The
falsifiable Playwright batch-fill claim is intentionally surfaced as
`NO_EVIDENCE` rather than fabricated.

## What was built

### bench/aggregate_tool_calls.py (MEAS-08)

CLI: `python -m bench.aggregate_tool_calls <RESULTS_DATE_DIR> [--mcp NAME] [--stage-attribution {none,marker}]`

For each per-MCP subdirectory under the date dir, walks `PASS{1,2,3}/raw_stream.jsonl`,
counts `tool_use` events from `assistant`-typed lines (deduped from the
stream_event duplicates by construction), partitions them into S1–S8 stages
via `Write` tool_use events whose `input.file_path` matches
`stage_s<N>.{yml,md,png,txt,FAILED,NA,diagnostic.yml}`, computes the
integer median across passes (missing tools count as 0), and emits
`<mcp>/tool_call_counts.json` with the shape:

```json
{
  "mcp": "<name>",
  "status": "OK|SKIPPED|NO_EVIDENCE",
  "stage_attribution_mode": "marker",
  "passes": {"PASS1": {"S1": {...}, ...}, ...},
  "median_per_stage": {"S1": {"<tool>": <int>, ...}, ...},
  "median_total_per_stage": {"S1": <int>, ...},
  "total_calls_per_pass": {"PASS1": N, ...},
  "median_total_calls": <int>,
  "interesting": {"s5_calls_per_field_filled": null}
}
```

Special handling:
- **SKIPPED.md + no PASS dirs** (browser-use-agent) → `{status: SKIPPED, reason: <first line>}`.
- **PASS dirs but no raw_stream.jsonl** (firecrawl — only stage markers, no Claude session) → 0-count evidence row.
- **No PASS dirs and no SKIPPED.md** (playwright — not scored in Phase 2) → `{status: NO_EVIDENCE}`.

### bench/aggregate_tools_inventory.py (MEAS-09)

CLI: `python -m bench.aggregate_tools_inventory <RESULTS_DATE_DIR> [--out PATH]`

Reads every per-MCP `tools_inventory.json` under the date dir, normalizes
the 6 category buckets (zero-filling missing ones), and emits a Markdown
rollup with: side-by-side table (8 rows × 6 category columns + tool_count +
status), Gaps section (any non-OK rows; absent here — see below), and a
methodology footer citing the first-match-wins keyword table from
`bench/tools_inventory.py`.

Also flags row-internal inconsistency (sum-of-categories ≠ tool_count) which
none of the 8 rows trigger — confirms the per-MCP probes are healthy.

### Four fresh tools_inventory.json probes

Phase-2-audit-discovered gaps (per CONTEXT.md):
- **playwright** — OK, 23 tools, 2 nav / 11 inter / 1 cap / 5 diag / 1 insp / 3 other
- **browser-use** (`browser-use-direct/` + copy to `browser-use-agent/`) — OK, 16 tools, 2 nav / 3 inter / 1 cap / 0 diag / 5 insp / 5 other
- **cloakbrowser** — OK, 20 tools, 3 nav / 6 inter / 1 cap / 1 diag / 3 insp / 6 other

The browser-use v0.12.7 INITIALIZE_TIMEOUT documented in browser-tools.md
(2026-05-21) **no longer reproduces** — handshake completes in <8s with
status=OK regardless of LLM-key presence. This corroborates the SKIPPED.md
note that the timeout fix landed before this run; the SKIPPED.md row for
agent mode remains valid (the key absence shows up at session runtime,
not at MCP handshake).

## Headline empirical findings

### S5 tool-call counts (median across passes)

| MCP | S5 total | S5 non-Write tool calls | Note |
|---|---|---|---|
| `playwright`         | N/A | — | NO_EVIDENCE (not scored in Phase 2; the falsifiable batch-fill claim cannot be confirmed from existing evidence) |
| `chrome-devtools`    | 1 | (none) | S5 never reached — S4 React-Select FAILED upstream; only the stage_s5.FAILED Write counts |
| `cloakbrowser`       | **6** | `cloak_type×4 + cloak_evaluate×1` | **Empirically confirms "N fields = N type calls"** for the per-field type-tool pattern. Plus 1× Write to stage_s5.yml. |
| `obscura`            | 1 | (none) | S5 never reached — upstream FAILED |
| `browser-use-direct` | 1 | (none) | S5 never reached — upstream FAILED |
| `browser-use-agent`  | N/A | — | SKIPPED (LLM_KEY_ABSENT) |
| `firecrawl`          | 0 | (none) | Cloud-only; harness can't reach loopback fixtures (env-mismatch FAILED on every stage) |
| `lightpanda`         | 1 | (none) | S5 never reached — React-rendered form returned 0 interactive elements at S4 |

**The Playwright batch-fill claim ("N fields in 1 call") cannot be tested
from Phase 2 evidence.** Phase 4 synthesis must either:
1. Score Playwright in a follow-up (smallest delta — one harness run), OR
2. Mark the claim as `evidence: pending` in the matrix.

This is preferable to fabricating a number.

### Total tool-call medians (Phase-2 session totals)

| MCP | Median calls per pass | Notes |
|---|---|---|
| `cloakbrowser`       | 53 | Highest — `cloak_snapshot`/`cloak_evaluate`-heavy stages |
| `browser-use-direct` | 51 | Direct-mode tool calls; agent mode would likely be lower |
| `chrome-devtools`    | 39 | Many `evaluate_script` rounds + Bash diagnostics |
| `lightpanda`         | 34 | All but S1/S2 short-circuited to Write-only (React unsupported) |
| `obscura`            | 19 | Sparse tool surface; many failures Write-only |
| `firecrawl`          | 0  | Harness couldn't exercise the cloud API against loopback |
| `playwright`         | N/A | Not scored in Phase 2 |
| `browser-use-agent`  | N/A | SKIPPED |

### Tools-surface category distribution (MEAS-09)

| MCP | Total | nav | inter | cap | diag | insp | other |
|---|---|---|---|---|---|---|---|
| `chrome-devtools`   | 29 | 1 | 10 | 1 | 10 | 3 | 4 |
| `firecrawl`         | 24 | 1 |  0 | 0 |  0 | 5 | 18 |
| `playwright`        | 23 | 2 | 11 | 1 |  5 | 1 |  3 |
| `cloakbrowser`      | 20 | 3 |  6 | 1 |  1 | 3 |  6 |
| `lightpanda`        | 20 | 2 |  7 | 0 |  1 | 2 |  8 |
| `browser-use-*`     | 16 | 2 |  3 | 1 |  0 | 5 |  5 |
| `obscura`           |  4 | 0 |  0 | 0 |  0 | 1 |  3 |

**Useful observations for Phase 4:**
- **`obscura` exposes only 4 tools.** Sparsity is a real signal — its S1 worked but every subsequent stage Write-failed because the MCP surface lacks the interaction primitives needed for S4–S8.
- **`firecrawl` has 24 tools but 0 in `interaction`.** It's a pure scraping/search MCP; "interaction" in the rubric sense is structurally absent. Phase 4 should consider whether the matrix's interaction column even applies to firecrawl, or whether it should be N/A-marked rather than 0-scored.
- **`chrome-devtools` leads in `diagnostics` (10).** This aligns with its DevTools-protocol heritage and explains why its S1 evidence directory carries the richest network/console/perf footprint.
- **`playwright` leads in `interaction` (11).** Consistent with its `browser_*` action surface; the batch-fill claim would predict that ONE of those 11 tools (`browser_fill_form`) reduces the per-call count materially vs. the per-field type pattern observed in cloakbrowser.

## Gaps surfaced

1. **`playwright/tool_call_counts.json` is NO_EVIDENCE.** Phase 2 never ran the Playwright harness. The plan's headline angle (browser_fill_form's batch-fill claim) is unverified. Recommendation for plan 03-05 synthesis: either schedule a one-off Playwright harness run during Phase 3 wall-clock budget (≈ 30 min for 3 passes), OR mark the matrix cell `evidence: pending` rather than synthesizing a number.

2. **`firecrawl` has 0 tool calls in every pass.** PASS dirs contain only the FAILED/NA stage markers, no `raw_stream.jsonl`. This is the env-mismatch evidence (cloud API can't see loopback fixtures); Phase 4 should display this as an explicit "harness-incompatible" row rather than a 0-call efficiency claim.

3. **Stage attribution is fragile when a pass crashes early.** A pass that writes stage_s1 but no further markers attributes all subsequent tool calls to "unattributed". This is currently observed in obscura PASS2 (only 22 lines total) and chrome-devtools PASS3 (140 lines but only 7 stage_s writes — one stage skipped). Downstream consumers should treat the `unattributed` bucket as a known-noisy bucket and not include it in stage-level analysis.

4. **`s5_calls_per_field_filled` is intentionally null** in every tool_call_counts.json. Plan 03-05 synthesis is expected to populate it by parsing `stage_s5.yml` artifacts for the count of fields actually filled and dividing the S5 non-Write tool count by that number — yielding the canonical "calls per field" metric for the matrix. The schema is locked so 03-05 can land its update without re-running this aggregator.

## Path forward for plan 03-05 synthesis

Plan 03-05 consumes these artifacts via:
```python
import json, pathlib
date_dir = pathlib.Path("results/2026-05-26")
for mcp_dir in date_dir.iterdir():
    if not mcp_dir.is_dir(): continue
    counts = json.loads((mcp_dir / "tool_call_counts.json").read_text())
    inv    = json.loads((mcp_dir / "tools_inventory.json").read_text())
    # consume counts["median_per_stage"]["S5"] for the batch-fill claim
    # consume inv["categories"]["interaction"] for the surface-area context
```

The 03-05 synthesis can populate `interesting.s5_calls_per_field_filled`
in-place (the field is already present; just overwrite null → int) without
re-running this aggregator. The aggregator IS idempotent — re-running it
would overwrite that field, so 03-05 should consume + transform but not
re-trigger aggregation.

## Verification

```bash
.venv/bin/python -m pytest tests/test_aggregate_tool_calls.py tests/test_aggregate_tools_inventory.py -v
# 17 passed in 0.02s

.venv/bin/python -m pytest -q
# 193 passed in 8.69s  (no regressions; scoring/score.py byte-unchanged)

test -f results/2026-05-26/TOOLS_INVENTORY_SUMMARY.md                       # OK
test -f results/2026-05-26/playwright/tools_inventory.json                  # OK
test -f results/2026-05-26/cloakbrowser/tools_inventory.json                # OK
test -f results/2026-05-26/browser-use-direct/tools_inventory.json          # OK
test -f results/2026-05-26/browser-use-agent/tools_inventory.json           # OK

# tool_call_counts.json exists for every MCP dir (including SKIPPED/NO_EVIDENCE)
ls results/2026-05-26/*/tool_call_counts.json | wc -l
# 8
```

## Deviations from Plan

None — plan executed exactly as written. The `s5_calls_per_field_filled`
field was added per the schema spec in the plan's Task 1 action block;
it stays `null` until plan 03-05 synthesis populates it.

## Self-Check: PASSED

- `bench/aggregate_tool_calls.py` — exists (commit c068df4)
- `bench/aggregate_tools_inventory.py` — exists (commit c5105a1)
- `tests/test_aggregate_tool_calls.py` — 11 tests pass (commit c068df4)
- `tests/test_aggregate_tools_inventory.py` — 6 tests pass (commit c5105a1)
- 7 `tool_call_counts.json` files exist (one per scored MCP + 1 NO_EVIDENCE playwright + 1 SKIPPED browser-use-agent = 8 total under results/2026-05-26/)
- 4 new `tools_inventory.json` files added (playwright, browser-use-direct, browser-use-agent, cloakbrowser) — commit c5105a1
- `results/2026-05-26/TOOLS_INVENTORY_SUMMARY.md` — 8-row Markdown rollup, 0 gaps (commit c5105a1)
- `scoring/score.py` — unchanged (verified `git diff HEAD scoring/score.py` empty across both commits)
- Full test suite 193/193 pass — no regressions
