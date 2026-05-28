---
phase: 2
plan: 07
mcp: audit
type: execute
wave: 7
depends_on:
  - 02-01
  - 02-02
  - 02-03
  - 02-04
  - 02-05
  - 02-06
files_modified:
  - results/<DATE>/scores.json                          # AUDIT-ONLY: validates, may add missing tags; preserves all scoring
  - results/<DATE>/PHASE2_AUDIT.md                      # the audit report — capability + attribution matrix for all 7 rows
  - results/<DATE>/CAPABILITY_MATRIX.md                 # FAIRNESS-04 second view: capability matrix with category tags
requirements:
  - FAIRNESS-04
  - FAIRNESS-05
success_criteria_advanced: [1, 2, 3, 4, 5]
status: planned
autonomous: true
estimate_hours: 1

must_haves:
  truths:
    - "Every row in `scores.json` (all 7 expected: playwright, chrome-devtools, lightpanda, firecrawl, obscura, browser-use-direct, browser-use-agent, cloakbrowser — note that's 8 distinct rows since browser-use is dual-mode) carries a capability tag from the allowed set: `{tool-only, LLM-augmented, stealth-specialist, cloud, js-light}`."
    - "Every sub-rubric cell < 5 across ALL rows carries an attribution tag from `{tool-bug, env-mismatch, target-flag, transient}` per FAIRNESS-06 + CONTEXT.md `## Decisions § Failure-Attribution Tags`."
    - "Read-only MCPs (lightpanda, firecrawl) show N/A (string) for S4-S8 + interaction_depth; NOT 0; aggregator drops N/A from weighted denominator per FAIRNESS-03."
    - "browser-use produces TWO rows (`browser-use-direct` + `browser-use-agent`) per FAIRNESS-05 + Phase 2 SC #3 — neither is missing, neither is merged."
    - "cloakbrowser SANDBOX_PROOF.md exists and confirms zero non-loopback hostnames per SC #5 (or SKIPPED.md exists)."
    - "PHASE2_AUDIT.md exists and summarizes: per-MCP status (scored / SKIPPED), capability tag, composite, count-of-cells-with-attribution, and which Phase 2 SC each row advances."
    - "CAPABILITY_MATRIX.md is the FAIRNESS-04 second view — a capability matrix with explicit category tags, separate from the same-rubric composite table that Phase 4 will assemble."
    - "If ANY of the above conditions fail, this plan exits non-zero and writes a `PHASE2_AUDIT_FAILURES.md` listing each violation; Phase 3 cannot start until violations are resolved."
  artifacts:
    - path: "results/<DATE>/PHASE2_AUDIT.md"
      provides: "Per-MCP status + capability + composite + attribution-cell-count + SC-advancement summary across all 7+ rows"
    - path: "results/<DATE>/CAPABILITY_MATRIX.md"
      provides: "FAIRNESS-04 second view — capability matrix with category tags; Phase 4 will lift this as-is"
    - path: "results/<DATE>/scores.json"
      provides: "Validated + tag-completed (any missing attribution tags injected with FailureTag default + sourced from raw_stream.jsonl error strings); previously-scored values preserved byte-for-byte"
  key_links:
    - from: "PHASE2_AUDIT.md"
      to: "scores.json + per-MCP DEEP_ANALYSIS.md + SANDBOX_PROOF.md"
      via: "validates capability + attribution + N/A semantics + dual-mode browser-use"
      pattern: "PHASE2_AUDIT.*scores\\.json"
    - from: "CAPABILITY_MATRIX.md"
      to: "FAIRNESS-04 contract (two-view publication)"
      via: "explicit category-tag matrix separate from composite ranking"
      pattern: "capability.*tool-only.*LLM-augmented.*stealth-specialist.*cloud.*js-light"
---

## Goal

Cross-cutting Phase 2 audit: validate that ALL of Phase 2's success criteria are met across the 7 MCPs (8 rows counting browser-use's dual mode), inject any missing attribution tags, emit `CAPABILITY_MATRIX.md` (the FAIRNESS-04 second-view artifact), and write `PHASE2_AUDIT.md` summarizing per-MCP status. This is the gate: if Phase 2 passes this audit, Phases 3 + 4 can begin. If it fails, the orchestrator surfaces violations before continuing.

## Files Modified

- `results/<DATE>/scores.json` — read-validate-fix-write (audit-only changes: inject missing attribution tags; preserve all scoring)
- `results/<DATE>/PHASE2_AUDIT.md` — the audit report
- `results/<DATE>/CAPABILITY_MATRIX.md` — FAIRNESS-04 second view (capability matrix)
- `results/<DATE>/PHASE2_AUDIT_FAILURES.md` — only written if audit fails

## Tasks

### Task 1: Cross-row validation + attribution-tag completeness

<files>results/&lt;DATE&gt;/scores.json, results/&lt;DATE&gt;/PHASE2_AUDIT_FAILURES.md (conditional)</files>

<action>
Load `results/<DATE>/scores.json`. Expected rows (per Phase 2 SC #1 + FAIRNESS-05):
- `playwright` (already present from plan 01-07)
- `chrome-devtools`
- `lightpanda`
- `firecrawl`
- `obscura`
- `browser-use-direct`
- `browser-use-agent`
- `cloakbrowser`

For each row, validate:

1. **Row presence:** must be in scores.json (scored or SKIPPED). If missing, append to `PHASE2_AUDIT_FAILURES.md` with the row name + the per-MCP plan that should have populated it (e.g., "browser-use-direct missing — plan 02-05 Task 1 did not run or did not insert row").

2. **Capability tag:** must be in `{tool-only, LLM-augmented, stealth-specialist, cloud, js-light}`. Per CONTEXT.md `## Decisions § Capability Tags`:
   - `playwright` → `tool-only`
   - `chrome-devtools` → `tool-only`
   - `browser-use-direct` → `LLM-augmented` (the LLM-decision surface exists even if the user doesn't supply a key)
   - `browser-use-agent` → `LLM-augmented`
   - `cloakbrowser` → `stealth-specialist`
   - `obscura` → `stealth-specialist`
   - `firecrawl` → `cloud`
   - `lightpanda` → `js-light`
   If any row is missing or has a wrong tag, INJECT the correct tag (preserving scoring values byte-for-byte) and note the injection in PHASE2_AUDIT.md.

3. **N/A semantics (FAIRNESS-03):** for `lightpanda` and `firecrawl`:
   - `scores["interaction_depth"]` MUST be the string `"N/A"` (NOT 0, NOT null)
   - `stages["S4"]..stages["S8"]` MUST be `"NA"` (or `"N/A"`) — NOT `"UNTESTED"` (UNTESTED would suggest the harness skipped them; NA means the MCP doesn't have the surface)
   If wrong, fix or list as failure.

4. **Attribution completeness (FAIRNESS-06):** for EVERY row, iterate over `scores` dict. For any numeric value < 5, the row's `attribution` dict MUST have a tag for that dimension from `{tool-bug, env-mismatch, target-flag, transient}`. If missing:
   - Try to source from per-pass evidence: read `PASS{1,2,3}/raw_stream.jsonl` for error strings on the relevant stages, classify via `bench.failure_taxonomy.attribute_failure(<error_string>)`, inject the tag.
   - If no error string can be found (clean failure with no log), default to `tool-bug` (per `bench.failure_taxonomy.attribute_failure` Python docstring: "an unclassified failure should point the finger at the MCP").
   - Note every injection in PHASE2_AUDIT.md ("Injected attribution `tool-bug` for `<mcp>.scores.error_handling=3` — no error string in raw_stream.jsonl").

5. **Dual-mode browser-use (FAIRNESS-05 + Phase 2 SC #3):** both `browser-use-direct` AND `browser-use-agent` must be present. The `mode` field on each must be `"direct"` and `"agent"` respectively. If either is missing, this is a hard failure — plan 02-05 must be re-run.

6. **cloakbrowser sandbox (Phase 2 SC #5):** confirm `results/<DATE>/cloakbrowser/SANDBOX_PROOF.md` exists (scored branch) OR `results/<DATE>/cloakbrowser/SKIPPED.md` exists. Confirm no `SANDBOX_VIOLATION.md`. If `SANDBOX_VIOLATION.md` exists, this is a P0 failure — surface immediately, do not write `PHASE2_AUDIT.md` as if Phase 2 passed.

7. **scoring/score.py SACROSANCT check:** `git diff main -- scoring/score.py | wc -l` must return 0. If non-zero, hard failure.

Write back to `scores.json` if any tag injections occurred. Preserve all numerical scores byte-for-byte (only adds to `attribution` map and fixes `capability` field if missing/wrong).

If `PHASE2_AUDIT_FAILURES.md` has any entries, exit non-zero — do not proceed to Task 2 until failures are fixed. Surface to user.
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
.venv/bin/python -c "
import json, sys
data = json.load(open('results/$DATE/scores.json'))
expected_rows = {'playwright','chrome-devtools','lightpanda','firecrawl','obscura','browser-use-direct','browser-use-agent','cloakbrowser'}
allowed_caps = {'tool-only','LLM-augmented','stealth-specialist','cloud','js-light'}
allowed_attr = {'tool-bug','env-mismatch','target-flag','transient'}
errors = []
for row_name in expected_rows:
  if row_name not in data:
    errors.append(f'missing row: {row_name}')
    continue
  row = data[row_name]
  cap = row.get('capability')
  if cap not in allowed_caps:
    errors.append(f'{row_name}: bad capability {cap!r}')
  # Skip attribution check for SKIPPED rows (they have no scores)
  if row.get('status') == 'SKIPPED':
    continue
  for dim, score in row.get('scores', {}).items():
    if isinstance(score, (int, float)) and score < 5:
      attr = row.get('attribution', {}).get(dim) or row.get('attribution', {}).get(f'_{dim}')
      if attr is None or attr not in allowed_attr:
        errors.append(f'{row_name}.{dim}={score} missing attribution tag (got {attr!r})')
# Read-only N/A
for ro in ('lightpanda','firecrawl'):
  if ro in data and data[ro].get('status') != 'SKIPPED':
    if data[ro]['scores'].get('interaction_depth') != 'N/A':
      errors.append(f'{ro}.interaction_depth must be N/A')
# Dual-mode
if 'browser-use-direct' not in data or 'browser-use-agent' not in data:
  errors.append('FAIRNESS-05 broken: both browser-use-direct and browser-use-agent must exist')
if errors:
  print('AUDIT FAIL:')
  for e in errors:
    print('  -', e)
  sys.exit(1)
print('AUDIT PASS')
" &&
# SACROSANCT check
[[ \$(git diff main -- scoring/score.py 2>/dev/null | wc -l) -eq 0 ]]
</automated>
</verify>

<done>
All 8 expected rows present (or SKIPPED), all capability tags valid, all sub-5 cells have attribution, lightpanda+firecrawl have N/A for interactive dims, both browser-use modes exist, scoring/score.py byte-for-byte unchanged. No PHASE2_AUDIT_FAILURES.md.
</done>

### Task 2: Write CAPABILITY_MATRIX.md + PHASE2_AUDIT.md

<files>results/&lt;DATE&gt;/CAPABILITY_MATRIX.md, results/&lt;DATE&gt;/PHASE2_AUDIT.md</files>

<action>
Write `results/<DATE>/CAPABILITY_MATRIX.md` — the FAIRNESS-04 second view (separate from the same-rubric composite table Phase 4 will build). Format:

```markdown
# Capability Matrix — 2026-05-<XX>

Per FAIRNESS-04: this view groups MCPs by category so readers cannot accidentally
compare a cloud service to a local browser on a single composite number.

| MCP | Capability | Mode | Status | Notes |
|-----|-----------|------|--------|-------|
| playwright | tool-only | default | SCORED | calibration baseline (composite 7.93) |
| chrome-devtools | tool-only | default | SCORED | <composite> |
| browser-use-direct | LLM-augmented | direct (no LLM key) | <SCORED/SKIPPED> | <composite or reason> |
| browser-use-agent | LLM-augmented | agent (LLM key set) | <SCORED/SKIPPED> | <composite or reason> |
| cloakbrowser | stealth-specialist | sandbox-loopback | <SCORED/SKIPPED> | **Sandbox only — do not point at authenticated sessions** |
| obscura | stealth-specialist | no-stealth-flag (macOS) | <SCORED/SKIPPED> | --stealth disabled per SAFETY-03 |
| firecrawl | cloud | markdown | <SCORED/SKIPPED> | S4-S8 N/A by category |
| lightpanda | js-light | nightly@2026-05-22 | <SCORED/SKIPPED> | S4-S8 N/A by category; binary version mismatch documented |

## Category groupings

### tool-only (raw browser-automation, no built-in LLM)
- playwright
- chrome-devtools

### LLM-augmented (uses LLM in-tool for action planning)
- browser-use-direct (claims to work without user's LLM key)
- browser-use-agent (LLM key required)

### stealth-specialist (anti-detection focus)
- cloakbrowser (sandbox-only)
- obscura (CDP-direct; --stealth flag disabled on macOS per SAFETY-03)

### cloud (remote service, no local browser)
- firecrawl (cloud-vs-loopback architectural caveat documented)

### js-light (JS-light or JS-blind)
- lightpanda (React handling re-tested in 2026-05; see DEEP_ANALYSIS.md)

## Cross-category note

Comparing `firecrawl` (cloud) to `playwright` (local) on a single composite is
the apples-to-oranges trap (Pitfall 2). The same-rubric composite IS published
(Phase 4 REPORT-01), but readers MUST consult this capability matrix first to
understand what each tier of MCP is even attempting.
```

Pull actual composite numbers from `scores.json` (use `score_with_na.py` output for N/A-aware composites).

Then write `results/<DATE>/PHASE2_AUDIT.md`:

```markdown
# Phase 2 Audit — 2026-05-<XX>

## Per-MCP status

| MCP | Status | Capability | Composite (N/A-aware) | Sub-5 cells with attribution | Issues |
|-----|--------|-----------|----------------------|------------------------------|--------|
| playwright | SCORED | tool-only | 7.93 | <count> | — |
| chrome-devtools | <status> | tool-only | <X.XX> | <count> | <issues> |
| ... (all 8 rows) | | | | | |

## Phase 2 Success Criteria

- **SC #1 — All 7 MCPs have evidence dirs or SKIPPED.md:** <PASS/FAIL> — list which MCPs scored vs SKIPPED
- **SC #2 — Read-only MCPs show N/A (not 0) for S4-S8:** <PASS/FAIL> — confirm lightpanda + firecrawl
- **SC #3 — browser-use produces two rows (direct + agent):** <PASS/FAIL> — confirm both rows in scores.json
- **SC #4 — Every row has capability tag + every sub-5 cell has attribution:** <PASS/FAIL> — cite injection count if any
- **SC #5 — cloakbrowser evidence shows zero non-loopback hostnames:** <PASS/FAIL> — confirm SANDBOX_PROOF.md presence or SKIPPED.md

## Tag injections (if any)

Document every capability or attribution tag this audit injected (preserving the rest of the row's scoring). If none, state "no injections required."

## SKIPPED rows summary

For each row marked SKIPPED, cite the reason from the corresponding SKIPPED.md.

## Linear updates

- G-703 parent comment summarizing Phase 2 completion: `linearis comments create G-703 --body "Phase 2 complete: 7/7 MCPs evaluated (X scored, Y SKIPPED). Capability tags + attribution validated. Ready for Phase 3 + 4."`
- Each sub-ticket (G-715..G-720) closed with link to its DEEP_ANALYSIS.md and PASS<N>.json files.

## Phase 3 + 4 readiness

- [ ] Phase 3 can begin (cross-cutting measurements — needs scores.json as baseline)
- [ ] Phase 4 can wait on Phase 3 completion before synthesis

## scoring/score.py SACROSANCT check

`git diff main -- scoring/score.py | wc -l = 0` — confirmed.
```

Both files should be ready for Phase 4 synthesis to lift verbatim into the public report.
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
test -f "results/$DATE/PHASE2_AUDIT.md" &&
test -f "results/$DATE/CAPABILITY_MATRIX.md" &&
# CAPABILITY_MATRIX must list all 5 capability categories
for cap in tool-only LLM-augmented stealth-specialist cloud js-light; do
  grep -q "$cap" "results/$DATE/CAPABILITY_MATRIX.md" || { echo "missing capability: $cap"; exit 1; }
done &&
# CAPABILITY_MATRIX must mention sandbox-only callout for cloakbrowser
grep -q 'Sandbox only' "results/$DATE/CAPABILITY_MATRIX.md" &&
# PHASE2_AUDIT must cover all 5 SCs
for sc in 'SC #1' 'SC #2' 'SC #3' 'SC #4' 'SC #5'; do
  grep -q "$sc" "results/$DATE/PHASE2_AUDIT.md" || { echo "missing $sc"; exit 1; }
done &&
# SACROSANCT
[[ \$(git diff main -- scoring/score.py 2>/dev/null | wc -l) -eq 0 ]]
</automated>
</verify>

<done>
CAPABILITY_MATRIX.md exists with all 5 capability categories + sandbox-only callout for cloakbrowser; PHASE2_AUDIT.md exists covering all 5 Phase 2 SCs with explicit PASS/FAIL per SC + per-MCP status table.
</done>

## Acceptance

- [ ] All 8 expected rows (`playwright`, `chrome-devtools`, `lightpanda`, `firecrawl`, `obscura`, `browser-use-direct`, `browser-use-agent`, `cloakbrowser`) present in `scores.json` (scored or SKIPPED).
- [ ] Every row has a valid capability tag from the allowed set.
- [ ] Every sub-rubric cell < 5 across all rows has an attribution tag from `{tool-bug, env-mismatch, target-flag, transient}`.
- [ ] `lightpanda` + `firecrawl` show `"N/A"` (string) for S4-S8 + `interaction_depth`, not 0 or `null`.
- [ ] `browser-use-direct` AND `browser-use-agent` both exist with distinct `mode` fields.
- [ ] `cloakbrowser` evidence has SANDBOX_PROOF.md (scored) or SKIPPED.md; no SANDBOX_VIOLATION.md.
- [ ] `CAPABILITY_MATRIX.md` exists with all 5 capability categories + sandbox-only callout.
- [ ] `PHASE2_AUDIT.md` exists covering all 5 Phase 2 SCs explicitly (PASS/FAIL per SC).
- [ ] `scoring/score.py` byte-for-byte unchanged.
- [ ] All previously-existing rows in `scores.json` byte-for-byte unchanged (only `attribution` map injections + capability field fixes are allowed).
- [ ] If any acceptance check fails: `PHASE2_AUDIT_FAILURES.md` exists, plan exits non-zero, Phase 3 cannot start.

## Dependencies

All of Phase 2 (plans 02-01 through 02-06). This plan reads what they wrote.

## Per-MCP Risks

This is an audit, not a per-MCP run. The risks are cross-cutting:

- **Audit detects violation in a per-MCP plan's output:** PHASE2_AUDIT_FAILURES.md is the artifact; orchestrator must surface to user before continuing.
- **Tag-injection ambiguity:** if attribution can't be sourced from raw_stream.jsonl error strings, default to `tool-bug` per `bench.failure_taxonomy` docstring. Document defaults so reviewers see them.
- **SCORE.py mutation:** if any prior plan accidentally touched `scoring/score.py`, this audit catches it. The Phase-1 SACROSANCT contract carries forward — score.py is byte-for-byte locked until G-710.

## Interesting Angle

This plan's interesting angle IS the audit itself: it's the structural validation that Phase 2's FAIRNESS-04 + FAIRNESS-05 contracts are actually upheld in the artifacts, not just claimed in plans. Phase 4 synthesis trusts this output; if it's wrong, the public report ships with broken capability tags or missing N/A semantics.

## Stop Conditions

- **`PHASE2_AUDIT_FAILURES.md` has any entries:** STOP, surface to user, do not write `PHASE2_AUDIT.md` as if Phase 2 passed.
- **`scoring/score.py` byte-for-byte changed:** P0 — surface immediately, do not proceed.
- **`SANDBOX_VIOLATION.md` exists for cloakbrowser:** P0 safety event — surface immediately, the closed-binary sandbox contract was broken.
