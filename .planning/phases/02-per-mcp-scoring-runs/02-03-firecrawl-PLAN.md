---
phase: 2
plan: 03
mcp: firecrawl
type: execute
wave: 3
depends_on:
  - 01-01
  - 01-02
  - 01-03
  - 01-04
  - 01-05
  - 01-06
  - 01-07
  - 02-01
  - 02-02   # second N/A-semantics validation builds on lightpanda's
files_modified:
  - results/<DATE>/firecrawl/                          # full evidence dir OR SKIPPED.md
  - results/<DATE>/firecrawl/PASS{1,2,3}.json           # only if key is present
  - results/<DATE>/firecrawl/stage_s{4..8}.NA           # cloud-only, no interactive surface
  - results/<DATE>/firecrawl/DEEP_ANALYSIS.md
  - results/<DATE>/scores.json                          # firecrawl row OR firecrawl SKIPPED row
requirements:
  - FAIRNESS-04
  - FAIRNESS-05
success_criteria_advanced: [1, 2, 4]
status: planned
autonomous: true
estimate_hours: 1

must_haves:
  truths:
    - "firecrawl either has a complete `results/<DATE>/firecrawl/` evidence directory (key present) OR a `SKIPPED.md` documenting API_KEY_ABSENT (key absent) — both are valid SC #1 outcomes per CONTEXT.md `## Decisions § SKIPPED.md Pattern` + REPORT-09."
    - "If scored: S4-S8 + `interaction_depth` are `N/A` (string, not 0) per FAIRNESS-03; row carries capability tag `cloud`."
    - "If skipped: SKIPPED.md contains `reason: API_KEY_ABSENT`, `attempted_command`, `error_excerpt`, `linear_ticket`, `partial_evidence_path`; aggregator treats it as N/A composite per CONTEXT.md."
    - "DEEP_ANALYSIS.md documents the falsifiable claim: 'firecrawl cloud LLM-extraction lifts Data Quality above raw-page MCPs at cost of latency + tokens; 96% success on JS-heavy sites' — capturing default markdown S1+S2+S3 latency vs Playwright/chrome-devtools baselines."
    - "FIRECRAWL_API_KEY is read from environment ONLY; never written to disk; never echoed in transcripts or commit messages."
  artifacts:
    - path: "results/<DATE>/firecrawl/stage_s{4,5,6,7,8}.NA"
      provides: "Sentinel files marking interactive stages N/A by design"
    - path: "results/<DATE>/firecrawl/DEEP_ANALYSIS.md"
      provides: "Capability = cloud; data-quality vs latency tradeoff; LLM-extraction claim with evidence"
    - path: "results/<DATE>/firecrawl/SKIPPED.md (alternative)"
      provides: "Partial-run disclosure if FIRECRAWL_API_KEY absent — per REPORT-09"
    - path: "results/<DATE>/scores.json"
      provides: "firecrawl row with N/A for S4-S8 (key present) OR SKIPPED metadata (key absent)"
  key_links:
    - from: "scripts/run_mcp_session.sh firecrawl"
      to: "$FIRECRAWL_API_KEY environment variable"
      via: ".mcp.json env reference (${FIRECRAWL_API_KEY})"
      pattern: "\\$\\{FIRECRAWL_API_KEY\\}"
    - from: "scripts/aggregate_scores.py"
      to: "READ_ONLY_MCPS = {'lightpanda', 'firecrawl'}"
      via: "hard-coded fairness-policy constant"
      pattern: "READ_ONLY_MCPS.*firecrawl"
---

## Goal

Drive the harness against **firecrawl** — the cloud markdown-extraction service — and produce a scored row with N/A semantics for S4-S8, capability-tagged `cloud`. OR, if `FIRECRAWL_API_KEY` is absent, write a clean `SKIPPED.md` documenting the partial-run per CONTEXT.md `## Decisions § SKIPPED.md Pattern` (this is the canonical SKIPPED-flow validation; the pattern carries into obscura / browser-use / cloakbrowser plans). Either outcome satisfies SC #1.

## Files Modified

- `results/<DATE>/firecrawl/` — full evidence dir OR SKIPPED.md
- `results/<DATE>/firecrawl/stage_s{4,5,6,7,8}.NA` — sentinel files (key-present path only)
- `results/<DATE>/firecrawl/DEEP_ANALYSIS.md`
- `results/<DATE>/scores.json` — firecrawl row OR firecrawl SKIPPED metadata

## Tasks

### Task 1: Pre-flight check + branch on API key presence

<files>results/&lt;DATE&gt;/firecrawl/, results/&lt;DATE&gt;/firecrawl/SKIPPED.md (conditional)</files>

<action>
Pre-flight: validate `FIRECRAWL_API_KEY` is present in the runtime environment. CONTEXT.md notes: "User confirmed key is set via rbw — should be available." But the partial-run pattern must be exercised regardless.

1. Confirm key presence WITHOUT echoing it:
   ```
   if [[ -z "${FIRECRAWL_API_KEY:-}" ]]; then KEY_PRESENT=0; else KEY_PRESENT=1; fi
   echo "FIRECRAWL_API_KEY present: $KEY_PRESENT"   # never echo the value
   ```
   If the key is absent and is expected per CLAUDE.md (rbw `firecrawl.dev` → `Firecrawl_API`), TRY: `export FIRECRAWL_API_KEY=$(rbw get firecrawl.dev --field Firecrawl_API 2>/dev/null)` once. If still absent after that, proceed to the SKIPPED branch.

2. **SKIPPED branch (key absent):** Write `results/<DATE>/firecrawl/SKIPPED.md`:
   ```markdown
   # firecrawl — SKIPPED (API key absent)

   - **reason:** API_KEY_ABSENT
   - **attempted_command:** `bash scripts/run_mcp_session.sh firecrawl`
   - **error_excerpt:** `FIRECRAWL_API_KEY environment variable not set; firecrawl MCP cannot authenticate to Firecrawl cloud`
   - **linear_ticket:** <firecrawl sub-ticket from G-715..G-720>
   - **partial_evidence_path:** results/<DATE>/firecrawl/ (empty)

   Per PROJECT.md, partial scoring (6/7) is acceptable when FIRECRAWL_API_KEY
   is absent. Per REPORT-09, the Phase 4 report MUST surface this in its
   executive-summary disclosure + matrix-row note + recommendations note.
   ```
   Then update `results/<DATE>/scores.json` to insert a firecrawl row of shape:
   ```json
   "firecrawl": {
     "status": "SKIPPED",
     "reason": "API_KEY_ABSENT",
     "capability": "cloud",
     "mode": "skipped",
     "scores": {},
     "stages": {"S1":"UNTESTED","S2":"UNTESTED","S3":"UNTESTED","S4":"NA","S5":"NA","S6":"NA","S7":"NA","S8":"NA"}
   }
   ```
   `scripts/score_with_na.py` should treat the absent `scores` map as N/A composite (CONTEXT.md: "The aggregator treats a SKIPPED row as N/A composite, not 0"). If the existing aggregator does not natively handle the empty-scores case, write the row manually with a `composite: null` field and document the deviation. Skip Task 2.

3. **NORMAL branch (key present):** Run the harness 3 times following the same pattern as plan 02-01 (PASS{1,2,3}/ subdirs + per-pass aggregation + ≥30 min gap between passes). Explicitly write N/A sentinels for S4-S8 after each pass:
   ```
   for n in 4 5 6 7 8; do
     rm -f "results/<DATE>/firecrawl/PASS<N>/stage_s${n}".{md,yml,png,txt,FAILED}
     touch "results/<DATE>/firecrawl/PASS<N>/stage_s${n}.NA"
   done
   ```

4. Special-handling note for firecrawl: it's CLOUD, so cold-start (Speed) is "0ms locally; network-bound for first byte." The Phase-1 stub `cold_start.json` returns neutral 5 from `_score_speed` per aggregator line 191. Phase 3 (MEAS-01) is responsible for the 3-segment split; do NOT touch the scorer.

Wall-clock gate: same 60-min STOP rule as plan 02-01.

Secret hygiene: at no point write `$FIRECRAWL_API_KEY` to disk, transcripts, or commit messages. The .mcp.json reference `${FIRECRAWL_API_KEY}` is the only legitimate path; pre-commit hook (plan 01-02) blocks inline literals.
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
# Branch A: SKIPPED path
if [[ -f "results/$DATE/firecrawl/SKIPPED.md" ]]; then
  grep -q "API_KEY_ABSENT" "results/$DATE/firecrawl/SKIPPED.md" &&
  .venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
assert 'firecrawl' in data
row = data['firecrawl']
assert row.get('status') == 'SKIPPED', f'expected SKIPPED, got {row.get(\"status\")}'
assert row.get('capability') == 'cloud'
print('OK (skipped branch)')
"
else
  # Branch B: scored path
  test -d "results/$DATE/firecrawl/PASS1" &&
  test -d "results/$DATE/firecrawl/PASS2" &&
  test -d "results/$DATE/firecrawl/PASS3" &&
  for n in 4 5 6 7 8; do
    test -f "results/$DATE/firecrawl/PASS1/stage_s${n}.NA" || exit 1
  done &&
  .venv/bin/python -c "
import json
row = json.load(open('results/$DATE/firecrawl/PASS1.json'))['firecrawl']
assert row['scores'].get('interaction_depth') == 'N/A', 'interaction_depth must be N/A for firecrawl'
print('OK (scored branch)')
"
fi &&
# Secret hygiene: API key must not appear in any committed file under results/$DATE/firecrawl/
! grep -rE "fc-[a-zA-Z0-9]{20,}" "results/$DATE/firecrawl/" 2>/dev/null
</automated>
</verify>

<done>
EITHER (SKIPPED branch): SKIPPED.md exists with all 5 required fields, scores.json firecrawl row has `status: SKIPPED`. OR (scored branch): 3 passes captured, S4-S8 sentinels exist, PASS<N>.json shows interaction_depth = "N/A". In both branches: no `fc-*` literal API key string appears anywhere in `results/<DATE>/firecrawl/`.
</done>

### Task 2: Median row + capability tag + cloud-LLM-extraction finding (scored branch only)

<files>results/&lt;DATE&gt;/scores.json, results/&lt;DATE&gt;/firecrawl/DEEP_ANALYSIS.md</files>

<action>
SKIP THIS TASK if Task 1 took the SKIPPED branch.

For the scored branch, compute median row per plan 02-01 Task 2 algorithm. N/A handling identical to plan 02-02:
- If a dimension is N/A in ANY of the 3 passes, it MUST be N/A in the median row.

Insert/update `firecrawl` row in `results/<DATE>/scores.json`. Preserve all earlier rows.

Row-level fields:
- `capability`: `"cloud"`
- `mode`: `"markdown"` (default firecrawl_scrape mode; structured-schema extraction is deferred per v2 requirements)

Run `scripts/score_with_na.py results/<DATE>/scores.json` → capture firecrawl composite (N/A-aware).

Write `results/<DATE>/firecrawl/DEEP_ANALYSIS.md`:
- **Capability tag:** `cloud` — remote service, no local browser process
- **Median composite** + **N/A semantics callout** (same template as plan 02-02)
- **The falsifiable empirical finding — Cloud LLM-extraction:**
  - Claim (research/SUMMARY.md): "Cloud LLM-extraction lifts Data Quality (3x weight) above raw-page MCPs at cost of latency + tokens; 96% success on JS-heavy sites"
  - Evidence to surface from the 3 passes:
    - Data Quality score across S1+S2+S3 (vs playwright + chrome-devtools rows already in scores.json) — is firecrawl's markdown extraction richer or thinner?
    - Latency: tokens.json + raw_stream.jsonl event timing — wall-clock seconds for S1-S3 vs Playwright's S1-S3 (parsed from `results/<DATE>/playwright/raw_stream.jsonl` start/end timestamps)
    - Token cost: payload bytes from firecrawl tool responses (parsed from raw_stream.jsonl `tool_use_result` blocks) — is firecrawl heavier/lighter per-byte than Playwright snapshot output?
    - Ashby SPA outcome: did firecrawl cloud handle the React shell (cross-reference lightpanda's failure mode from plan 02-02)?
  - Document outcome: claim CONFIRMED / PARTIALLY CONFIRMED / REFUTED with specific numbers.
- **Failure-attribution table** for any sub-rubric cell < 5.
- **Linear sub-ticket reference.**
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
# Only enforce in scored branch (SKIPPED.md absent)
if [[ ! -f "results/$DATE/firecrawl/SKIPPED.md" ]]; then
  .venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
row = data['firecrawl']
assert row.get('capability') == 'cloud', f'capability missing: {row.get(\"capability\")}'
assert row['scores'].get('interaction_depth') == 'N/A'
print('OK')
" &&
  test -f "results/$DATE/firecrawl/DEEP_ANALYSIS.md" &&
  grep -q 'cloud' "results/$DATE/firecrawl/DEEP_ANALYSIS.md" &&
  grep -q -i 'LLM.extract\|markdown\|96%' "results/$DATE/firecrawl/DEEP_ANALYSIS.md"
else
  echo "OK (skipped branch; task 2 N/A)"
fi
</automated>
</verify>

<done>
Scored branch: scores.json firecrawl row has capability="cloud", interaction_depth="N/A", composite reflects only attempted dimensions; DEEP_ANALYSIS.md documents data-quality vs latency tradeoff with concrete numbers vs the Playwright and chrome-devtools baseline rows.
</done>

## Acceptance

- [ ] EITHER `SKIPPED.md` exists with all required fields AND scores.json firecrawl row has `status: SKIPPED` + `capability: cloud`.
- [ ] OR `results/<DATE>/firecrawl/` exists with all 8 required files + stage_s{1,2,3}.* + stage_s{4..8}.NA sentinels; PASS{1,2,3}.json each show interactive dims = "N/A"; scores.json row has capability="cloud" + valid attribution for any score < 5; DEEP_ANALYSIS.md documents the LLM-extraction empirical finding.
- [ ] Secret hygiene: no `fc-[a-zA-Z0-9]{20,}` strings in any file under `results/<DATE>/firecrawl/`.
- [ ] `scoring/score.py` byte-for-byte unchanged.
- [ ] Existing playwright + chrome-devtools + lightpanda rows in `scores.json` byte-for-byte unchanged.

## Dependencies

All of Phase 1, plus plans 02-01 (chrome-devtools — harness-generalization confidence) and 02-02 (lightpanda — N/A semantics already validated; firecrawl is the cloud N/A case that builds on the read-only N/A case).

## Per-MCP Risks

From CONTEXT.md + research/STACK.md `## 8` + HANDOFF-GSD-AUTO STOP #4:

- **Cloud API rate limits:** 3 full passes against firecrawl cloud could hit per-key rate limits. If 429s appear, `bench/transient.py` will retry (HTTP 429 is in `TRANSIENT_PATTERNS`); if rate limit is persistent, dock attribution as `transient` not `tool-bug` (the bug is rate-limit, not Firecrawl's code) and document.
- **firecrawl-mcp publish lag:** GitHub releases are dead (last v3.2.1 in 2025-09); npm is the only source of truth per research/STACK.md "Pitfall #1." `versions.json` from `bench/capture_versions.py` will record the installed npm version; ensure that matches `.mcp.json`.
- **Cloud LLM-extraction unstable scoring:** since firecrawl's cloud may change behavior between passes (model updates, A/B tests), inter-pass variance is expected. Median-of-3 is the defense.
- **Sandbox-only does not apply to firecrawl** — but the snapshot fixtures still run on loopback, so firecrawl cloud will see `127.0.0.1` and fail to reach it. This means firecrawl must be pointed at the live URLs OR firecrawl gets a URL-rewriting harness adapter. Decision: per research/SUMMARY.md and Phase-1 fixtures-loopback contract, firecrawl scores against the SAME loopback fixture URL Playwright et al. used — if firecrawl-cloud can't reach loopback, the response will be empty / error, and the row scores S1-S3 as FAIL with attribution `env-mismatch` (cloud-vs-loopback architectural mismatch). Document in DEEP_ANALYSIS.md as a methodology limitation, not as a Firecrawl bug. (Phase 4 "Negative Results" cites this.)

## Interesting Angle

From `.planning/research/SUMMARY.md § Empirical Claims to Falsify`:

> **firecrawl** — Cloud LLM-extraction lifts Data Quality (3x weight) above raw-page MCPs at cost of latency + tokens; "96% success on JS-heavy sites." Evidence: S1+S2+S3 with default markdown AND structured-schema extraction; latency vs local; bytes/tokens vs Playwright snapshot; mark S4-S8 N/A not 0.

Scope cut for v1 (research/PROJECT.md): structured-schema extraction split is deferred to v2; this plan covers default markdown only. Document the v2-deferral in DEEP_ANALYSIS.md so Phase 4 doesn't have to discover it.

## Stop Conditions

- **Cloud-vs-loopback architectural mismatch** (firecrawl cloud cannot reach `127.0.0.1`): if Pass 1 returns empty / 4xx on every stage, STOP and decide with user whether to (a) score firecrawl against live URLs (breaks reproducibility — discouraged), (b) score as 3x FAIL with `env-mismatch` attribution and document, (c) deploy a tunneling proxy (out of scope). Default to (b) per Phase-1 fixture-loopback contract.
- **Per-pass wall-clock > 60 minutes:** unlikely (cloud is fast) but enforced uniformly.
- **All 3 passes wildly disagree:** indicates cloud nondeterminism — record but score median anyway.
