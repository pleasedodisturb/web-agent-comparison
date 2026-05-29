---
phase: 2
plan: 02
mcp: lightpanda
type: execute
wave: 2
depends_on:
  - 01-01
  - 01-02
  - 01-03
  - 01-04
  - 01-05
  - 01-06
  - 01-07
  - 02-01   # chrome-devtools validates harness generalizes; reduces lightpanda-N/A-semantics ambiguity
files_modified:
  - results/<DATE>/lightpanda/                      # full evidence dir (transcript.md, raw_stream.jsonl, stage_s{1,2,3}.*, stage_s{4..8}.NA, cold_start.json, tokens.json, tls.json, stability.log, orphan_audit.log, tools_inventory.json)
  - results/<DATE>/lightpanda/PASS1.json
  - results/<DATE>/lightpanda/PASS2.json
  - results/<DATE>/lightpanda/PASS3.json
  - results/<DATE>/lightpanda/DEEP_ANALYSIS.md      # capability tag = js-light; documents Ashby SPA finding (2026-03: 0 bytes; 2026-05 nightly: ???)
  - results/<DATE>/scores.json                       # adds lightpanda row with S4-S8 = N/A (not 0)
requirements:
  - FAIRNESS-04
  - FAIRNESS-05
success_criteria_advanced: [1, 2, 4]
status: planned
autonomous: true
estimate_hours: 1

must_haves:
  truths:
    - "lightpanda has a complete `results/<DATE>/lightpanda/` evidence directory; stages S1-S3 are attempted and recorded; stages S4-S8 are marked NA (via stage_s<N>.NA sentinels), NOT 0 — per FAIRNESS-03 + CONTEXT.md `## Decisions § N/A Semantics`."
    - "scores.json contains a lightpanda row scored as the median of 3 passes; S4-S8 dimensions and `interaction_depth` are `N/A` (string, not 0); composite via `scripts/score_with_na.py` reflects only attempted dimensions."
    - "The row carries capability tag = `js-light`."
    - "DEEP_ANALYSIS.md documents the falsifiable Ashby SPA finding: 2026-03 claim was 0-byte response on Ashby; this plan captures whether the 2026-05 lightpanda nightly produces the same / better / worse output. Captures S2 raw response bytes."
    - "lightpanda's known version-string inconsistency (binary self-reports 0.3.0 in some builds vs 0.1.0 in JSON-RPC handshake per browser-tools.md 2026-05-21) is recorded verbatim in `versions.json` and `DEEP_ANALYSIS.md` — neither resolves the contradiction, both are documented."
  artifacts:
    - path: "results/<DATE>/lightpanda/stage_s{4,5,6,7,8}.NA"
      provides: "Sentinel files telling the aggregator that S4-S8 are N/A by design, not failed attempts"
    - path: "results/<DATE>/lightpanda/stage_s2.{md,yml}"
      provides: "Ashby SPA response capture — the falsifiable 2026-03 claim ('React-blind, 0 bytes') gets re-tested"
    - path: "results/<DATE>/lightpanda/DEEP_ANALYSIS.md"
      provides: "Capability = js-light; S2-on-Ashby empirical finding (PASS/PARTIAL/FAIL with raw-byte count); version-mismatch documentation"
    - path: "results/<DATE>/scores.json"
      provides: "Lightpanda row with N/A for S4-S8 + interaction_depth; passes through score_with_na.py to drop N/A from weighted denominator"
  key_links:
    - from: "scripts/aggregate_scores.py"
      to: "READ_ONLY_MCPS = {'lightpanda', 'firecrawl'}"
      via: "hard-coded fairness-policy constant"
      pattern: "READ_ONLY_MCPS.*lightpanda"
    - from: "scripts/score_with_na.py"
      to: "weighted denominator"
      via: "drops N/A cells per FAIRNESS-03"
      pattern: "score_with_na"
---

## Goal

Drive the harness against **lightpanda** — the Zig JS-light engine — and produce a complete evidence row with **correct N/A semantics for S4-S8** (per FAIRNESS-03), capability-tagged `js-light`. This is the load-bearing validation of CONTEXT.md's `## Decisions § N/A Semantics`: read-only MCPs MUST score N/A, not 0, on interactive stages. Also closes the falsifiable empirical claim: "lightpanda is React-blind, returned 0 bytes on Ashby in 2026-03" — this plan tests whether the 2026-05 nightly is better/same/worse.

## Files Modified

- `results/<DATE>/lightpanda/` — full evidence dir; stage_s{1,2,3}.* are real artifacts; stage_s{4,5,6,7,8}.NA are sentinel files (touched empty)
- `results/<DATE>/lightpanda/PASS{1,2,3}.json` — per-pass aggregations
- `results/<DATE>/lightpanda/DEEP_ANALYSIS.md`
- `results/<DATE>/scores.json` — adds lightpanda row with N/A for S4-S8 + `interaction_depth`

## Tasks

### Task 1: Three-pass harness execution + explicit N/A sentinels

<files>results/&lt;DATE&gt;/lightpanda/PASS{1,2,3}/, results/&lt;DATE&gt;/lightpanda/stage_s{4..8}.NA</files>

<action>
Pre-flight: confirm lightpanda binary is installed (`scripts/check_prereqs.sh`); verify the `.mcp.json` lightpanda entry resolves to the nightly@2026-05-22 binary per research/STACK.md `## 1 § Lightpanda`. Note the version mismatch (binary header says 0.3.0; MCP JSON-RPC handshake says 0.1.0 per browser-tools.md 2026-05-21) — both will land in `versions.json` from `bench/capture_versions.py`.

Run the harness 3 times:

1. Pass 1: `bash scripts/run_mcp_session.sh lightpanda`. The locked `prompts/stage_walk.md` walks S1-S8; lightpanda will succeed on S1-S3 (read-only stages — fetch + parse) and naturally fail S4-S8 (no interactive surface). The harness records whatever Claude produces; do NOT modify the prompt to skip stages.

2. After Pass 1 completes, write the N/A sentinels EXPLICITLY for S4-S8 (do NOT trust whatever stage_s4..s8 file Claude may have written — lightpanda has no form-fill capability, so any S4-S8 PASS artifact is misleading):
   ```
   for n in 4 5 6 7 8; do
     # Remove any FAILED or stub artifact Claude may have written
     rm -f "results/<DATE>/lightpanda/stage_s${n}".{md,yml,png,txt,FAILED}
     # Touch the NA sentinel
     touch "results/<DATE>/lightpanda/stage_s${n}.NA"
   done
   ```
   (`aggregate_scores.py._stage_status` will then return `"NA"` per its existing logic at line 134.)

3. Move evidence into `PASS1/`; run aggregator `scripts/aggregate_scores.py results/<DATE>/lightpanda/PASS1/` → `PASS1.json`.

4. Repeat for Pass 2 and Pass 3 (≥30 min gap between passes per Pitfall 1).

5. Falsifiable-claim capture: for EACH pass, after Claude writes whatever it writes for S2 (Ashby), preserve the raw Ashby response that lightpanda fetched. The natural artifact is `stage_s2.{md,yml}` containing whatever lightpanda produced. If it's empty (0 bytes) or contains only the loader-shell text (`"You need to enable JavaScript to run this app"`), record the byte count + content fingerprint in `PASS<N>/stage_s2.bytes.txt`. This is the data DEEP_ANALYSIS.md will summarize.

Wall-clock gate: same 60-minute STOP rule as plan 02-01.
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
test -d results/$DATE/lightpanda/PASS1 &&
test -d results/$DATE/lightpanda/PASS2 &&
test -d results/$DATE/lightpanda/PASS3 &&
# N/A sentinels must exist for S4-S8 in each pass (or at root if Claude wrote them)
for p in PASS1 PASS2 PASS3; do
  for n in 4 5 6 7 8; do
    test -f "results/$DATE/lightpanda/$p/stage_s${n}.NA" || test -f "results/$DATE/lightpanda/stage_s${n}.NA" || { echo "missing stage_s${n}.NA in $p"; exit 1; }
  done
done &&
# PASS<N>.json must show S4-S8 + interaction_depth as the string "N/A"
for p in PASS1 PASS2 PASS3; do
  .venv/bin/python -c "
import json,sys
row = json.load(open('results/$DATE/lightpanda/$p.json'))['lightpanda']
assert row['scores'].get('interaction_depth') == 'N/A', f'$p interaction_depth should be N/A, got {row[\"scores\"].get(\"interaction_depth\")}'
for n in (4,5,6,7,8):
  s = row.get('stages', {}).get(f'S{n}')
  assert s == 'NA' or s == 'N/A', f'$p stage S{n} should be NA, got {s}'
" || exit 1
done
</automated>
</verify>

<done>
3 passes executed; S4-S8 explicitly marked NA via sentinel files; PASS<N>.json shows S4-S8 + interaction_depth = "N/A" string; S2 raw-byte capture recorded for each pass.
</done>

### Task 2: Median row + capability tag + Ashby SPA finding

<files>results/&lt;DATE&gt;/scores.json, results/&lt;DATE&gt;/lightpanda/DEEP_ANALYSIS.md</files>

<action>
Compute median row across the 3 PASS<N>.json files per the algorithm in plan 02-01 Task 2 step 1. Special handling for N/A dimensions:
- If a dimension is `"N/A"` in ANY of the 3 passes, it MUST be `"N/A"` in the median row (a single non-N/A pass for an interactive dimension would indicate harness misclassification — surface as a warning in DEEP_ANALYSIS.md).
- For `data_quality` (driven by S1-S3 only per aggregator line 244), median normally.
- For `js_rendering` (driven by S2 verdict), median normally.

Insert/update the `lightpanda` row in `results/<DATE>/scores.json`. Preserve existing playwright + chrome-devtools rows byte-for-byte.

Add row-level fields:
- `capability`: `"js-light"`
- `mode`: `"default"` (nightly@2026-05-22 build)

Run `scripts/score_with_na.py results/<DATE>/scores.json` and capture stdout. The lightpanda composite MUST be computed with N/A cells dropped from the weighted denominator — NOT counted as 0. Confirm by reading `score_with_na.py` output: if it reports the composite as `(weighted_sum / weighted_denominator_excluding_NA)`, the math is correct.

Write `results/<DATE>/lightpanda/DEEP_ANALYSIS.md` containing:
- **Capability tag:** `js-light` — JS-light Zig engine, fetch-mode read-only (no interactive surface)
- **Median composite:** the N/A-aware number (only S1-S3-derived dimensions weighted)
- **N/A semantics callout:** explicit statement that S4-S8 + interaction_depth scored N/A (not 0); composite reflects S1-S3 only. Reference FAIRNESS-03 + the score_with_na.py mechanism.
- **The falsifiable empirical finding — Ashby SPA test (2026-03 → 2026-05):**
  - 2026-03 claim: "lightpanda returned 0 bytes on Ashby" (research/SUMMARY.md § Empirical Claims to Falsify; results/2026-03-31_run.md if present)
  - 2026-05 observed across 3 passes: cite byte counts from `PASS{1,2,3}/stage_s2.bytes.txt`. Possible outcomes:
    - 0 bytes (or loader-shell only) → claim CONFIRMED, lightpanda still React-blind, attribute S2 dock to `tool-bug` (the MCP has the limitation)
    - Partial content (>1KB of meaningful HTML) → claim REFUTED, document which React APIs lightpanda nightly now implements
    - Full content → claim STRONGLY REFUTED, S2 PASS, headline finding for Phase 4
  - Whatever the outcome, this is "the empirical finding" — document explicitly. The point of the comparison is to publish empirical truth, not to confirm priors.
- **Version-string inconsistency:** lightpanda binary self-reports 0.3.0 in some headers vs 0.1.0 in MCP JSON-RPC handshake (per browser-tools.md 2026-05-21). Note BOTH from `versions.json` and `tools_inventory.json` (handshake field). Phase 4 report's "Negative Results" section can cite this.
- **Failure-attribution table:** any sub-rubric cell < 5 with tag + 1-sentence justification.
- **Linear sub-ticket reference:** the lightpanda sub-ticket from G-715..G-720.
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
.venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
row = data['lightpanda']
assert row.get('capability') == 'js-light', f'capability missing: {row.get(\"capability\")}'
assert row['scores'].get('interaction_depth') == 'N/A', 'interaction_depth must be N/A'
print('OK')
" &&
test -f results/$DATE/lightpanda/DEEP_ANALYSIS.md &&
grep -q 'js-light' results/$DATE/lightpanda/DEEP_ANALYSIS.md &&
grep -q -i 'ashby\|SPA\|react' results/$DATE/lightpanda/DEEP_ANALYSIS.md &&
grep -q -i 'N/A\|not zero' results/$DATE/lightpanda/DEEP_ANALYSIS.md
</automated>
</verify>

<done>
scores.json lightpanda row has `capability: "js-light"`, interactive dimensions are `"N/A"` (not 0), composite via score_with_na.py reflects only attempted dimensions. DEEP_ANALYSIS.md documents the falsifiable Ashby SPA finding and the version-string inconsistency.
</done>

## Acceptance

- [ ] `results/<DATE>/lightpanda/` exists with all 8 required files + stage_s{1,2,3}.* artifacts + stage_s{4,5,6,7,8}.NA sentinels.
- [ ] `PASS{1,2,3}.json` each show interactive dimensions as the string `"N/A"`, not 0.
- [ ] `scores.json` lightpanda row has `capability: "js-light"`, all of S4-S8 stages = `"NA"`, `interaction_depth = "N/A"`.
- [ ] `score_with_na.py` confirmation: lightpanda composite computed over only attempted dimensions (i.e., the weighted denominator excludes N/A cells per FAIRNESS-03).
- [ ] Every sub-rubric cell < 5 has an attribution tag (excluding N/A cells, which are not failures).
- [ ] `DEEP_ANALYSIS.md` documents: capability tag, median composite, N/A semantics callout, Ashby SPA empirical finding (byte-count evidence across 3 passes), version-string inconsistency, failure-attribution.
- [ ] `scoring/score.py` byte-for-byte unchanged.
- [ ] Existing playwright + chrome-devtools rows in `scores.json` byte-for-byte unchanged.

## Dependencies

All of Phase 1 + plan 02-01 (chrome-devtools — validated harness generalizes; if 02-01 hit issues, those need surfaced before lightpanda runs).

## Per-MCP Risks

From CONTEXT.md `## Decisions § Known Per-MCP Risks` + research/STACK.md `## 8`:

- **React-blind by design:** Expected 0-byte or loader-shell-only response on Ashby (Ashby is React SPA per `fixtures/snapshots/ashby_2026-05-22/PROVENANCE.md`). This IS the empirical finding — do NOT classify as harness bug. Per CONTEXT.md: "Score S2 as PARTIAL or FAIL with attribution, NOT as a harness bug."
- **Version-string inconsistency:** binary self-reports differently in different places. Document BOTH; do not pick one. Phase 4 "Negative Results" will cite.
- **Harness records may write spurious S4-S8 stage files** if Claude doesn't realize lightpanda can't do interactive work — Task 1 step 2 EXPLICITLY overwrites with NA sentinels to enforce the fairness policy.
- **Nightly binary, not a tagged release:** asset is rolling per research/STACK.md. The `versions.json` SHA256 is captured at run time; treat it as the canonical version reference, not the human-facing version string.

## Interesting Angle

From `.planning/research/SUMMARY.md § Empirical Claims to Falsify`:

> **lightpanda** — "React-blind" — returned 0 bytes on Ashby in 2026-03; check whether 2026-05 nightly is better/same/worse. Evidence: S2 (Ashby SPA) on current nightly; if partial, capture which React APIs are now implemented; cold-start (was 1.8s).

The headline question for this plan's DEEP_ANALYSIS.md is exactly: did lightpanda's React handling improve in 14 months? Whatever the answer, it's a publishable finding for Phase 4.

## Stop Conditions

- **Per-pass wall-clock > 60 minutes:** unlikely for lightpanda (its differentiator is speed) but enforced uniformly across MCPs.
- **All 3 passes produce drastically different S1-S3 outcomes** (e.g., Pass 1 PASS S2, Pass 2 FAIL S2, Pass 3 PASS S2): could indicate flakiness in fixture serving OR lightpanda nondeterminism — surface to user before scoring.
- **lightpanda binary cannot be invoked at all** (`make check` reports MISSING for lightpanda): write `SKIPPED.md` per CONTEXT.md partial-run pattern (reason: `BINARY_MISSING`), continue. The aggregator treats a SKIPPED row as N/A composite, not 0.
