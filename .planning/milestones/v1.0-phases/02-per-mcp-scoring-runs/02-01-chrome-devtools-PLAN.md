---
phase: 2
plan: 01
mcp: chrome-devtools
type: execute
wave: 1
depends_on:
  - 01-01
  - 01-02
  - 01-03
  - 01-04
  - 01-05
  - 01-06
  - 01-07
files_modified:
  - results/<DATE>/chrome-devtools/                       # full evidence dir (transcript.md, raw_stream.jsonl, stage_s{1..8}.*, cold_start.json, tokens.json, tls.json, stability.log, orphan_audit.log, tools_inventory.json)
  - results/<DATE>/chrome-devtools/PASS1.json             # per-pass aggregated row (3-pass median per FAIRNESS-01)
  - results/<DATE>/chrome-devtools/PASS2.json
  - results/<DATE>/chrome-devtools/PASS3.json
  - results/<DATE>/chrome-devtools/DEEP_ANALYSIS.md       # capability tag + failure-attribution notes + interesting-angle finding
  - results/<DATE>/scores.json                            # adds chrome-devtools row (median of 3 passes) alongside playwright row
requirements:
  - FAIRNESS-04
  - FAIRNESS-05
success_criteria_advanced: [1, 4]
status: planned
autonomous: true
estimate_hours: 1

must_haves:
  truths:
    - "chrome-devtools has a complete `results/<DATE>/chrome-devtools/` evidence directory with all 8 required files plus stage_s{1..8} artifacts."
    - "scores.json contains a chrome-devtools row scored as the median of 3 full harness passes per FAIRNESS-01."
    - "The row carries capability tag = `tool-only`."
    - "Every sub-rubric cell < 5 in the chrome-devtools row has a failure-attribution tag from bench/failure_taxonomy.py."
    - "If the per-pass wall-clock exceeds 60 minutes for the first pass, the plan STOPS, writes a partial-evidence + pace report, and surfaces to user before continuing — per CONTEXT.md `## Specific Ideas` pragmatic concession."
    - "DEEP_ANALYSIS.md documents the chrome-devtools `interesting angle` empirical finding (DevTools-exclusive signals: network waterfall / performance trace / console with source-mapped stacks) — captured as observed bonus evidence, NOT a scored 9th stage (out-of-scope per CONTEXT.md deferred)."
  artifacts:
    - path: "results/<DATE>/chrome-devtools/transcript.md"
      provides: "Human-readable session text driving S1-S8 against the snapshot fixture server"
    - path: "results/<DATE>/chrome-devtools/raw_stream.jsonl"
      provides: "Original stream-json from claude --print --output-format stream-json"
    - path: "results/<DATE>/chrome-devtools/tools_inventory.json"
      provides: "tools/list probe — count + 6-category breakdown for chrome-devtools (~26 tools per research/SUMMARY.md)"
    - path: "results/<DATE>/chrome-devtools/DEEP_ANALYSIS.md"
      provides: "Capability tag = tool-only; failure-attribution per sub-rubric cell < 5; interesting-angle finding text for Phase 4 synthesis"
    - path: "results/<DATE>/scores.json"
      provides: "Adds chrome-devtools row (median-of-3) to existing playwright row; preserves schema score.py consumes"
  key_links:
    - from: "scripts/run_mcp_session.sh chrome-devtools"
      to: ".mcp.json"
      via: "jq -r .mcpServers.chrome-devtools"
      pattern: "mcpServers.*chrome-devtools"
    - from: "results/<DATE>/chrome-devtools/scores aggregation"
      to: "scripts/aggregate_scores.py + scripts/score_with_na.py"
      via: "per-pass aggregation then median across PASS{1,2,3}.json"
      pattern: "aggregate_scores\\.py.*results/.*chrome-devtools"
---

## Goal

Drive the locked Phase-1 harness against the **chrome-devtools** MCP and produce a complete, defensible evidence row in `scores.json` — median-of-3 passes per FAIRNESS-01, capability-tagged `tool-only`, with every sub-rubric cell < 5 attributed via `bench/failure_taxonomy.py`. Validates the harness generalizes beyond the Playwright calibration baseline; this is the lowest-risk follow-on MCP (Google-shipped reference implementation, GA'd v1.0.x on 2026-05-18 — fresh but not flaky).

## Files Modified

- `results/<DATE>/chrome-devtools/` — full evidence dir (8 required files + stage_s{1..8}.* + per-pass aggregations + DEEP_ANALYSIS.md)
- `results/<DATE>/scores.json` — adds chrome-devtools row alongside the existing playwright row

## Tasks

### Task 1: Three-pass harness execution (median-of-3 per FAIRNESS-01)

<files>results/&lt;DATE&gt;/chrome-devtools/PASS{1,2,3}/, results/&lt;DATE&gt;/chrome-devtools/</files>

<action>
Pre-flight: confirm `FIRECRAWL_API_KEY` is set (not required for chrome-devtools but versions.json gets written once per date). Confirm `make check` passes via `scripts/check_prereqs.sh`. Confirm fixture server can boot via `scripts/serve_fixtures.sh status`.

Run the harness 3 times against chrome-devtools, each pass producing its own complete evidence subdirectory:

1. Pass 1: `bash scripts/run_mcp_session.sh chrome-devtools` — wait for clean exit (rc=0 from Claude, orphan_audit logged). Move/copy resulting `results/<DATE>/chrome-devtools/` into `results/<DATE>/chrome-devtools/PASS1/` (preserve all files including raw_stream.jsonl, transcript.md, stage_s*, tools_inventory.json, orphan_audit.log).

2. Wall-clock gate: if Pass 1 exceeds 60 minutes wall-clock, STOP. Write `results/<DATE>/chrome-devtools/PACE_REPORT.md` explaining duration + partial evidence captured + recommendation (drop to 1-pass for remaining MCPs per CONTEXT.md "pragmatic concession"). Surface to user before running passes 2/3.

3. Pass 2: same command. Move output into `PASS2/`. Allow ≥30 minute gap between passes per Pitfall 1 (different wall-clock window prevents shared environment bleed-through).

4. Pass 3: same command. Move output into `PASS3/`.

5. For each pass directory, run `scripts/aggregate_scores.py results/<DATE>/chrome-devtools/PASS<N>/` to emit `PASS<N>.json` at the chrome-devtools dir root. Each PASS<N>.json carries the score.py-shape `scores` + `stages` + `attempts` + `attribution` fields for that single pass.

Reuse the final pass's `tools_inventory.json`, `orphan_audit.log`, `tokens.json`, and `stage_s*` artifacts as the canonical evidence dir contents (copy them up from PASS3/ if not already at root). The 3 PASS<N>.json files are the median-of-3 source data.

Do NOT use the `--allowedTools` flag to extend beyond `mcp__chrome-devtools__*,Read,Write,Bash` — the harness handles that. Do NOT touch `scoring/score.py` (SACROSANCT).
</action>

<verify>
<automated>
test -d results/$(date -u +%Y-%m-%d)/chrome-devtools/PASS1 &&
test -d results/$(date -u +%Y-%m-%d)/chrome-devtools/PASS2 &&
test -d results/$(date -u +%Y-%m-%d)/chrome-devtools/PASS3 &&
test -f results/$(date -u +%Y-%m-%d)/chrome-devtools/PASS1.json &&
test -f results/$(date -u +%Y-%m-%d)/chrome-devtools/PASS2.json &&
test -f results/$(date -u +%Y-%m-%d)/chrome-devtools/PASS3.json &&
for p in PASS1 PASS2 PASS3; do
  jq -e '.["chrome-devtools"].scores | length >= 8' "results/$(date -u +%Y-%m-%d)/chrome-devtools/$p.json" || exit 1
done &&
test -f results/$(date -u +%Y-%m-%d)/chrome-devtools/transcript.md &&
test -f results/$(date -u +%Y-%m-%d)/chrome-devtools/raw_stream.jsonl &&
test -f results/$(date -u +%Y-%m-%d)/chrome-devtools/tools_inventory.json
</automated>
</verify>

<done>
Three full passes captured; PASS{1,2,3}.json each contain a chrome-devtools row with all 8 rubric dimensions scored; canonical evidence files exist at the chrome-devtools dir root for Phase 4 synthesis to consume.
</done>

### Task 2: Compute median-of-3 row + write capability + attribution tags

<files>results/&lt;DATE&gt;/scores.json, results/&lt;DATE&gt;/chrome-devtools/DEEP_ANALYSIS.md</files>

<action>
Compute median row across the 3 per-pass score files and merge into the date-level `scores.json` (which already contains the Playwright row from plan 01-07).

1. Write a short inline Python script (no new file — use `.venv/bin/python -c "..."` or a tmp script in `results/<DATE>/chrome-devtools/.merge.py`) that:
   - Loads `PASS{1,2,3}.json`
   - For each of the 8 rubric dimensions (`data_quality`, `reliability`, `speed`, `token_efficiency`, `interaction_depth`, `js_rendering`, `setup_complexity`, `error_handling`), computes statistics.median across the 3 values. If any value is the string "N/A", treat that pass as N/A for that dim and median over remaining; if all 3 are N/A, the merged value is "N/A".
   - For `stages`, take the majority verdict per stage (PASS if ≥2 pass; FAIL if ≥2 fail; NA only if all 3 are NA; otherwise PARTIAL).
   - For `attempts`, sum across passes (e.g., `{"S5": {"passes": 5, "total": 9}}` when 3 passes each ran S5 three times).
   - For `attribution`, prefer the most-frequent failure tag per stage; ties → the last failure's tag.
   - Add `capability` field at the row level: `"tool-only"`.
   - Add `mode` field: `"default"` (no special invocation flags).
2. Load existing `results/<DATE>/scores.json`. Insert/update the `chrome-devtools` row, preserve the existing `playwright` row byte-for-byte. Write back.
3. Run `scripts/score_with_na.py results/<DATE>/scores.json` to print the N/A-aware composite for chrome-devtools as a sanity check — capture stdout to `results/<DATE>/chrome-devtools/.composite_check.txt`.
4. Validate: every sub-rubric score < 5 in the chrome-devtools row MUST have a failure-attribution tag from `{tool-bug, env-mismatch, target-flag, transient}` (per FAIRNESS-06, enforced by aggregator). If a score-<5 cell lacks a tag, manually classify via `bench.failure_taxonomy.attribute_failure(<error string from raw_stream.jsonl>)` and inject into the row's `attribution` map before writing.

5. Write `results/<DATE>/chrome-devtools/DEEP_ANALYSIS.md` (~1-2 pages) containing:
   - **Capability tag:** `tool-only` (raw browser-automation tooling, no built-in LLM) — for Phase 4 capability matrix.
   - **Median composite:** the number from `score_with_na.py`.
   - **Per-stage verdicts:** 8-row table (S1..S8) with verdict + tool-call count (parsed from `raw_stream.jsonl`).
   - **Interesting-angle finding:** narrative — was chrome-devtools' tool surface exposed by the harness? Did the prompt produce calls to network/performance/console tools (those exist per chrome-devtools-mcp v1.0.1 docs but the S1-S8 walk doesn't explicitly require them)? Cite specific tool names called from `tools_inventory.json` + raw_stream.jsonl. NOTE: the chrome-devtools 9th DevTools-Probe stage is OUT OF SCOPE per CONTEXT.md deferred — only document what naturally appeared.
   - **Failure-attribution table:** any sub-rubric cell < 5, with its tag + a 1-sentence justification.
   - **Linear sub-ticket reference:** the chrome-devtools sub-ticket from G-715..G-720 split (see Phase 1 OUTREACH-03; CONTEXT.md `## Decisions § Execution Order`). Add a Linear comment via `linearis comments create <ticket> --body "..."` summarizing the row.
</action>

<verify>
<automated>
.venv/bin/python -c "
import json, sys
data = json.load(open('results/$(date -u +%Y-%m-%d)/scores.json'))
row = data['chrome-devtools']
assert row.get('capability') == 'tool-only', f'capability tag missing or wrong: {row.get(\"capability\")}'
# Every sub-rubric score < 5 must have an attribution
attr = row.get('attribution', {})
for dim, score in row['scores'].items():
  if isinstance(score, (int, float)) and score < 5:
    assert dim in attr or any(dim in str(k) for k in attr), f'score {dim}={score} < 5 but no attribution'
print('OK')
" &&
test -f results/$(date -u +%Y-%m-%d)/chrome-devtools/DEEP_ANALYSIS.md &&
grep -q 'tool-only' results/$(date -u +%Y-%m-%d)/chrome-devtools/DEEP_ANALYSIS.md &&
grep -q -i 'interesting angle\|interesting-angle\|deep analysis' results/$(date -u +%Y-%m-%d)/chrome-devtools/DEEP_ANALYSIS.md
</automated>
</verify>

<done>
chrome-devtools row in `scores.json` carries `capability: tool-only`, a median-of-3 score per dimension, and an `attribution` tag for every cell < 5. DEEP_ANALYSIS.md is ready for Phase 4 synthesis to lift verbatim into the per-MCP "Deep Analysis" stanza.
</done>

## Acceptance

- [ ] `results/<DATE>/chrome-devtools/` exists and contains all 8 required files (`transcript.md`, `raw_stream.jsonl`, `cold_start.json` (stub OK), `tokens.json`, `tls.json` (stub OK), `stability.log` (stub OK), `orphan_audit.log`, `tools_inventory.json`) plus `stage_s{1..8}.*` artifacts.
- [ ] `PASS{1,2,3}.json` each contain a complete chrome-devtools row (8 dimensions scored).
- [ ] `scores.json` chrome-devtools row carries `capability: "tool-only"`.
- [ ] Every sub-rubric cell < 5 in the chrome-devtools row has an attribution tag from `{tool-bug, env-mismatch, target-flag, transient}`.
- [ ] `DEEP_ANALYSIS.md` exists with: capability tag, median composite, per-stage verdicts table, interesting-angle paragraph, failure-attribution table.
- [ ] `scoring/score.py` byte-for-byte unchanged (`git diff main -- scoring/score.py | wc -l` returns 0).
- [ ] Existing Playwright row in `scores.json` is byte-for-byte unchanged.
- [ ] If wall-clock exceeded 60 minutes per pass: `PACE_REPORT.md` exists and user was surfaced.

## Dependencies

All of Phase 1 (the harness must be fully built and calibrated). Specifically:
- `scripts/run_mcp_session.sh` (plan 01-04) — the per-MCP driver
- `scripts/aggregate_scores.py` + `scripts/score_with_na.py` (plan 01-05) — scoring pipeline
- `bench/transient.py` + `bench/failure_taxonomy.py` (plan 01-05) — retry gate + attribution
- `bench/orphan_audit.py`, `bench/tools_inventory.py`, `bench/stub_writers.py`, `bench/capture_versions.py` (plans 01-04, 01-06) — evidence-dir population
- `prompts/stage_walk.md` (plan 01-04) — locked S1-S8 prompt
- `fixtures/snapshots/{greenhouse,ashby}_2026-05-22/` (plan 01-03) — loopback fixtures
- Plan 01-07 — proves the harness reproduces 2026-03 Playwright within the re-baseline band [7.83, 8.83]; chrome-devtools is the first MCP to validate the harness generalizes

## Per-MCP Risks

From CONTEXT.md `## Decisions § Known Per-MCP Risks` and research/STACK.md `## 8. Version Compatibility`:

- **Stderr warning is expected, not a failure:** chrome-devtools-mcp v1.0.1 prints a stderr warning about "exposes content of the browser instance to the MCP client" per browser-tools.md 2026-05 stability rubric. Document in DEEP_ANALYSIS.md but do NOT score as failure.
- **Requires a running Chrome/Chromium instance** with `--remote-debugging-port` accessible on the host. The `.mcp.json` spawn command handles this; if the first pass fails with a Chrome-connection error, document in PACE_REPORT.md and check chrome-devtools-mcp install instructions before retrying.
- **GA'd 4 days before the original research (2026-05-18, v1.0.x line):** while v1.0.1 is the locked version, treat any new instability as `tool-bug` attribution if it cannot be classified as `transient` per `bench/failure_taxonomy.py`.

## Interesting Angle

From `.planning/research/SUMMARY.md § Empirical Claims to Falsify`:

> **chrome-devtools** — DevTools panel exposes signals no other MCP can (network waterfall, performance trace, console with source-mapped stacks). Evidence: 9th "DevTools probe" stage producing artifacts (`network.json`, `trace.json`, `console.json`) the other 6 MCPs structurally cannot produce.

**Scope cut for this plan:** the 9th DevTools-Probe stage is OUT OF SCOPE per CONTEXT.md `## Deferred Ideas`. What this plan DOES capture: `tools_inventory.json` records the exposed tool surface (expected ~26 tools across 6 categories per chrome-devtools-mcp docs), and DEEP_ANALYSIS.md notes which DevTools-exclusive tools were observed in the natural S1-S8 walk vs. only listed in inventory. That naturally-occurring evidence is sufficient for Phase 4 to claim "chrome-devtools exposes N tools unique to it."

## Stop Conditions

- **Per-pass wall-clock > 60 minutes:** Per CONTEXT.md `## Specific Ideas` pragmatic concession. Write `PACE_REPORT.md`, surface to user, await decision on dropping to 1-pass for remaining MCPs.
- **Phase-1 calibration regression:** If `results/<DATE>/scores.json` no longer contains the Playwright row from plan 01-07 (e.g., overwritten or corrupted), STOP and restore from git before adding chrome-devtools row.
- **Genuine "world has changed" surprise** (per HANDOFF-GSD-AUTO STOP #4): chrome-devtools-mcp pulled from npm, `.mcp.json` no longer resolves, Chrome/Chromium API contract changed since the harness was built. Surface to user, do not retry blindly.
