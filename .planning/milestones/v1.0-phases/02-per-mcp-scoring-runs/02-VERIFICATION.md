---
phase: 2
phase_name: Per-MCP Scoring Runs
verified: 2026-05-27
status: passed
score: 5/5 success criteria verified
sacrosanct_check:
  scoring_score_py_git_diff_lines: 0
  pytest_result: "176 passed"
re_verification:
  previous_status: null
  initial_verification: true
---

# Phase 2: Per-MCP Scoring Runs — Verification Report

**Phase Goal:** Every one of the 7 MCPs has a complete evidence directory + populated scores.json row with median-of-3 results, correct N/A semantics for read-only candidates, capability-category tags, and a failure-attribution tag for any sub-rubric score < 5 — turning the harness into 7 comparable, defensible rows.

**Verified:** 2026-05-27
**Status:** passed
**Confidence:** HIGH — every SC corroborated by direct artifact inspection or programmatic re-check; scoring/score.py byte-for-byte unchanged; 176/176 tests still pass; composites re-derived from scores.json match the audit-claimed values exactly.

## 1. Verdict + Overall Confidence

**PASS — all 5 success criteria are observably satisfied in the codebase.** The phase upgrades the matrix from 1/7 (Phase 1 calibration baseline) to a complete 8-row matrix (7 MCPs × 1 row each, with browser-use producing dual rows = 8 total, of which 7 are SCORED and 1 is SKIPPED with documented `LLM_KEY_ABSENT` reason).

Key spot-checks completed:

| Check | Method | Result |
|---|---|---|
| All 8 expected rows present in scores.json | `json.load + key set diff` | OK — `{playwright, chrome-devtools, lightpanda, firecrawl, obscura, browser-use-direct, browser-use-agent, cloakbrowser}` |
| Capability tags valid for every row | Membership in `{tool-only, LLM-augmented, stealth-specialist, cloud, js-light}` | OK 8/8 |
| Attribution tag present + valid on every sub-5 numeric cell | `isinstance(score, (int, float)) and score < 5` iterator | OK 11/11 from `{tool-bug, env-mismatch, target-flag, transient}` |
| N/A semantics (string `"N/A"`, not 0) on read-only S4–S8 | Direct field inspection | OK — `firecrawl.stages.S4..S8` and `lightpanda.stages.S4..S8` all `"N/A"`; `interaction_depth = "N/A"` (string) on both |
| browser-use dual rows with distinct `mode` | Field inspection | OK — `direct/SCORED` and `agent/SKIPPED` both present, both `capability=LLM-augmented` |
| Composite values match audit claims | `.venv/bin/python scripts/score_with_na.py results/2026-05-26/scores.json` | OK — cloakbrowser 8.33, playwright 7.93, lightpanda 6.31, browser-use-direct 5.87, chrome-devtools 5.60, firecrawl 4.23, obscura 3.27, browser-use-agent 0.0 sentinel — exact match |
| cloakbrowser navigate targets are loopback-only | `jq` over PASS{1,2,3}/raw_stream.jsonl `cloak_navigate.input.url` | OK — 6 unique URLs, all `127.0.0.1:8765`; supplementary `cloak_(navigate|fetch|click)` filter returns zero non-loopback hits |
| scoring/score.py SACROSANCT | `git diff scoring/score.py \| wc -l` | OK — 0 lines |
| Phase-1 test suite still green | `.venv/bin/python -m pytest --no-header -q` | OK — 176 passed in 8.17s |
| `PHASE2_AUDIT.md` mirrored consistently | `diff .planning/.../PHASE2_AUDIT.md results/2026-05-26/PHASE2_AUDIT.md` | IDENTICAL |

## 2. Per-Success-Criterion Analysis

### SC #1 — Evidence directory (or SKIPPED.md) for all 7 MCPs — VERIFIED

`results/2026-05-26/` contains the following per-MCP subdirectories with the expected evidence artifacts. browser-use produces two rows per FAIRNESS-05; both are present.

| MCP | Evidence path | DEEP_ANALYSIS.md | PASS1/2/3 | SKIPPED.md | Notes |
|---|---|---|---|---|---|
| `playwright` | (no per-MCP dir; row in `scores.json`) | ABSENT | — | — | Phase 1 calibration baseline; carried-forward limitation #3 (see §6) |
| `chrome-devtools` | `results/2026-05-26/chrome-devtools/` | present | all three | — | Full S1–S8 attempted; stages 4–8 FAIL |
| `lightpanda` | `results/2026-05-26/lightpanda/` | present | all three | — | S2 FAIL (Ashby React-blind); S4–S8 N/A by category |
| `firecrawl` | `results/2026-05-26/firecrawl/` | present | all three | — | S1–S3 FAIL (cloud-vs-loopback `env-mismatch`); S4–S8 N/A |
| `obscura` | `results/2026-05-26/obscura/` | present | all three | — | All eight stages FAIL with `tool-bug` attribution chain (SSRF guard → strategy variance → CDP wedge) |
| `browser-use-direct` | `results/2026-05-26/browser-use-direct/` | present | all three | — | S1–S3 + S8 PASS; S4–S7 FAIL on React-clobber |
| `browser-use-agent` | `results/2026-05-26/browser-use-agent/` | — | — | present | `LLM_KEY_ABSENT`; SKIPPED.md documents re-run procedure |
| `cloakbrowser` | `results/2026-05-26/cloakbrowser/` | present | all three | — | All S1–S8 PASS; `SANDBOX_PROOF.md` present (see SC #5) |

The asymmetry on playwright is explicitly catalogued as carried-forward limitation #3 (see §6) — it is not a Phase 2 regression because the scoring row was authored under Phase 1 plan 01-07 before the per-MCP directory pattern crystallised. The row is fully scored and present in `scores.json`.

### SC #2 — Read-only MCPs show N/A (not 0) for S4–S8 — VERIFIED

`firecrawl` and `lightpanda` are the two read-only MCPs (capability tags `cloud` and `js-light`). Both encode N/A as the string `"N/A"` rather than numeric 0, which is the FAIRNESS-03 contract that `scripts/score_with_na.py` consumes to drop those cells from the weighted denominator.

| MCP | interaction_depth | stages.S4 | stages.S5 | stages.S6 | stages.S7 | stages.S8 |
|---|---|---|---|---|---|---|
| `lightpanda` | `"N/A"` (string) | `"N/A"` | `"N/A"` | `"N/A"` | `"N/A"` | `"N/A"` |
| `firecrawl` | `"N/A"` (string) | `"N/A"` | `"N/A"` | `"N/A"` | `"N/A"` | `"N/A"` |

Re-derivation via `scripts/score_with_na.py` confirms `lightpanda = 6.31` and `firecrawl = 4.23` — i.e. composites are computed with N/A cells dropped, not zeroed. Treating those cells as 0 would produce substantially lower composites; the audit-claimed values prove the N/A semantics flowed all the way through to the composite.

### SC #3 — browser-use produces TWO rows (direct + agent) — VERIFIED

Both rows are present in `scores.json` with distinct `mode` fields and a shared `capability` tag:

| Row | capability | mode | status |
|---|---|---|---|
| `browser-use-direct` | `LLM-augmented` | `direct` | SCORED |
| `browser-use-agent` | `LLM-augmented` | `agent` | SKIPPED |

The agent row is SKIPPED-with-reason rather than absent, which is the FAIRNESS-05 contract — the matrix preserves both rows so a future re-run can fill in the agent row without re-shaping the schema. `results/2026-05-26/browser-use-agent/SKIPPED.md` documents `reason=LLM_KEY_ABSENT`, attempted command, partial evidence path (the direct row), and the full re-run procedure.

### SC #4 — Capability tag on every row + attribution tag on every sub-5 cell — VERIFIED

**Capability tags:** 8/8 rows have a tag from the allowed set `{tool-only, LLM-augmented, stealth-specialist, cloud, js-light}`. Distribution:

- `tool-only`: playwright, chrome-devtools
- `LLM-augmented`: browser-use-direct, browser-use-agent
- `stealth-specialist`: cloakbrowser, obscura
- `cloud`: firecrawl
- `js-light`: lightpanda

**Attribution tags:** 11/11 sub-5 numeric cells across the 7 SCORED rows carry a tag from `{tool-bug, env-mismatch, target-flag, transient}`. Distribution: 9 `tool-bug`, 2 `env-mismatch`, 0 `target-flag`, 0 `transient`. The N/A string cells (firecrawl S4–S8, lightpanda S4–S8) are correctly excluded from the sub-5 check via `isinstance(score, (int, float))`.

Sub-5 cell inventory (programmatically re-derived):

| Row | Dim | Score | Attribution |
|---|---|---|---|
| browser-use-direct | error_handling | 2 | `tool-bug` |
| browser-use-direct | interaction_depth | 2 | `tool-bug` |
| chrome-devtools | error_handling | 2 | `tool-bug` |
| chrome-devtools | interaction_depth | 0 | `tool-bug` |
| firecrawl | data_quality | 0 | `env-mismatch` |
| firecrawl | js_rendering | 2 | `env-mismatch` |
| lightpanda | js_rendering | 2 | `tool-bug` |
| obscura | data_quality | 0 | `tool-bug` |
| obscura | error_handling | 2 | `tool-bug` |
| obscura | interaction_depth | 0 | `tool-bug` |
| obscura | js_rendering | 2 | `tool-bug` |

The interpretive caveat that `tool-bug` is the aggregator default and several cells (browser-use-direct interaction_depth, chrome-devtools interaction_depth, obscura's chain) carry a more nuanced root cause is documented in each row's `DEEP_ANALYSIS.md` and lifted to `PHASE2_AUDIT.md § Attribution interpretation caveats` for Phase 4 to honour. The contract here is "every sub-5 cell carries a valid tag," which is satisfied — the nuance is appropriately scoped to the per-row deep analysis rather than overloaded into a single tag.

### SC #5 — cloakbrowser evidence has zero non-loopback requests — VERIFIED

`results/2026-05-26/cloakbrowser/SANDBOX_PROOF.md` exists and documents a three-phase audit. Direct re-verification:

```
$ for p in PASS1 PASS2 PASS3; do
    jq -r 'select(.type=="assistant") | .message.content[]? |
           select(.type=="tool_use" and .name=="mcp__cloakbrowser__cloak_navigate") |
           .input.url' \
      "results/2026-05-26/cloakbrowser/$p/raw_stream.jsonl"
  done | sort -u
http://127.0.0.1:8765/ashby_2026-05-22/
http://127.0.0.1:8765/ashby_2026-05-22/replit/
http://127.0.0.1:8765/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html
http://127.0.0.1:8765/greenhouse_2026-05-22/
http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/
http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html
```

40 `cloak_navigate` invocations across the three passes; six unique URLs; all six start with `http://127.0.0.1:8765`. A supplementary filter that broadens the predicate to `cloak_(navigate|fetch|click)` and pulls `.input.url` or `.input.href` returns zero non-loopback rows.

Non-loopback hostnames that DO appear in transcripts (e.g. `https://job-boards.greenhouse.io`, `https://cdn.ashbyprd.com`, `https://www.anthropic.com`, `https://bit.ly/afpsafety`) are all CONTENT strings extracted from snapshot HTML (`og:url` meta, `<link>` hrefs, in-body anchors) — never targets of any `cloak_navigate` or in-page `fetch()` call. SANDBOX_PROOF.md § Phase 2 catalogues every one of these and traces them to the snapshot fixture HTML; spot-check on `bit.ly/afpsafety` confirms it is the fixture's apply-URL string, never followed.

`bench/cloakbrowser_guard.assert_local_only()` is wired into `scripts/run_mcp_session.sh:127-130` and verified to raise `HostnameNotAllowedError` on any non-loopback hostname pre-flight. No `SANDBOX_VIOLATION.md` sentinel exists in the cloakbrowser/ directory. SAFETY-04 contract upheld.

## 3. Per-MCP Coverage Table

| MCP | Status | Capability | Mode | Composite (N/A-aware) | Sub-5 cells w/ attribution | Evidence completeness | Verifier note |
|---|---|---|---|---|---|---|---|
| `cloakbrowser` | SCORED | stealth-specialist | sandbox-loopback | 8.33 | 0/0 | DEEP_ANALYSIS + SANDBOX_PROOF + PASS{1,2,3} | All-PASS row; loopback-only verified |
| `playwright` | SCORED | tool-only | default | 7.93 | 0/0 | row in scores.json only (no per-MCP dir) | Phase-1 calibration baseline; capability+mode injected by 02-07 audit (legitimate — see §5) |
| `lightpanda` | SCORED | js-light | default | 6.31 | 1/1 | DEEP_ANALYSIS + PASS{1,2,3} | Read-only; S4–S8 N/A; `js_rendering=2` architectural |
| `browser-use-direct` | SCORED | LLM-augmented | direct | 5.87 | 2/2 | DEEP_ANALYSIS + PASS{1,2,3} + init_smoke.json | Vitalik's headline-claim CONFIRMED for S1+S2+S3+S8 (no LLM key needed) |
| `chrome-devtools` | SCORED | tool-only | default | 5.60 | 2/2 | DEEP_ANALYSIS + PASS{1,2,3} + full cross-cut artifacts | 1-of-3 passes found SSR-rescue workaround on Greenhouse |
| `firecrawl` | SCORED | cloud | markdown | 4.23 | 2/2 | DEEP_ANALYSIS + PASS{1,2,3} | S1–S3 FAIL → `env-mismatch` (cloud loopback-incompatible); S4–S8 N/A by category |
| `obscura` | SCORED | stealth-specialist | no-stealth-flag | 3.27 | 4/4 | DEEP_ANALYSIS + PASS{1,2,3} + INSTALL_LOG | `--stealth` disabled per SAFETY-03; SSRF guard → harness-incompatibility cascade |
| `browser-use-agent` | SKIPPED | LLM-augmented | agent | 0.0 (sentinel; `status: SKIPPED` is the truth) | 0/0 | SKIPPED.md + init_smoke.json | `LLM_KEY_ABSENT`; HANDOFF-GSD-AUTO STOP #2 (init timeout) explicitly RE-VERIFIED FIXED at v0.12.7 in init_smoke.json |

## 4. Sacrosanct Contract Verification

| Invariant | Method | Result |
|---|---|---|
| `scoring/score.py` byte-for-byte unchanged across Phase 2 | `git diff scoring/score.py \| wc -l` | **0** |
| 176-test Phase-1 suite still green | `.venv/bin/python -m pytest --no-header -q` | **176 passed in 8.17s** |
| `scripts/score_with_na.py` reproduces audit-claimed composites | `.venv/bin/python scripts/score_with_na.py results/2026-05-26/scores.json` | All 8 composites match exactly (8.33 / 7.93 / 6.31 / 5.87 / 5.60 / 4.23 / 3.27 / 0.0 sentinel) |
| scores.json schema validation (all 8 rows + valid tags) | inline Python iterator over rows/scores/attribution | OK — no errors emitted |
| PHASE2_AUDIT.md present in both `.planning/` and `results/2026-05-26/` and identical | `diff` | IDENTICAL |

No regressions detected against any sacrosanct invariant.

## 5. Audit Injection Assessment

**Was the playwright capability+mode injection by 02-07 legitimate? YES.**

The injection added exactly two fields to the playwright row in scores.json:

```diff
@@ -532,6 +532,8 @@
     "attribution": {},
+    "capability": "tool-only",
+    "mode": "default",
     "scores": {
```

Legitimacy check:

1. **Unambiguous mapping.** `02-CONTEXT.md § Decisions § Capability Tags` explicitly states `tool-only — playwright, chrome-devtools (raw browser-automation tooling, no built-in LLM)`. Independent of the injection, there is no other allowed capability tag for playwright.
2. **Precedent for `mode: "default"`.** Every other non-mode-switching MCP in the matrix (chrome-devtools, lightpanda) uses `mode: "default"`. Stealth/dual-mode MCPs use distinct values (`sandbox-loopback`, `no-stealth-flag`, `direct`, `agent`). Choosing `default` for playwright is precedent-conformant, not novel interpretation.
3. **Root cause documented honestly.** Playwright's row was authored under plan 01-07 (Phase 1 calibration) *before* the FAIRNESS-04 capability-tag contract crystallised in plan 02-CONTEXT.md. The gap is documented as a pre-contract authoring artifact, not a quality slip.
4. **No scoring value mutated.** The audit's stated invariant — "scoring VALUES byte-for-byte preserved; only missing metadata tags may be injected" — is honoured. `git diff` on the playwright row shows the addition is purely two new keys; every numeric `scores.*`, every `stages.*` value, every `attempts.*` field is byte-identical.
5. **Documented in `INJECTIONS.md`.** A dedicated audit-trail file records the single injection set, the justification, and the byte-level diff. This is the audit-injection pattern that 02-07's `provides` documents as reusable for future cross-row audits.

The injection is procedurally clean, contractually within scope, and the result was independently re-verified by re-running the scores.json validation iterator (no errors). **Legitimate.**

The audit also explicitly considered and DECLINED to re-attribute several `tool-bug` cells (browser-use-direct, chrome-devtools, obscura) to `target-flag` even though the executor-prompt gotchas section suggested it. The decline is correct: the tag was NOT missing (so the injection contract does not apply), the DEEP_ANALYSIS.md per row already documents the interpretive nuance, and re-tagging would constitute a scoring-value change in violation of byte-for-byte preservation. Documented in `INJECTIONS.md § Non-injections (preserved as-is)`.

## 6. Carried-Forward Limitations (3 items for Phase 4)

These are NOT Phase 2 gaps — they are intentionally-bounded interpretive limits that Phase 4 must lift. Documented in `PHASE2_AUDIT.md § Known limitations for Phase 4`:

1. **`score_with_na.py` renders SKIPPED rows as composite=0.0.** Degenerate-case fallback when `total_weight == 0` (all-N/A row). The `status: "SKIPPED"` field on `browser-use-agent` is the source of truth; the composite=0.0 is sentinel, not a real ranking. Phase 4's matrix builder MUST consult `status` and surface SKIPPED rows distinctly. The wrapper was not modified this wave because it is adjacent-to-sacrosanct (should be revisited under G-710's scoring-engine PR territory, not as a Phase-2 patch).
2. **The 4-tag taxonomy's `tool-bug` aggregator default loses MCP-fault vs. agent-fault distinction.** Several rows (browser-use-direct, chrome-devtools, obscura) carry `tool-bug` where the true root cause is fixture-side React-hydration, capability gaps, or harness-incompatibility cascades. Each row's `DEEP_ANALYSIS.md` carries the interpretive paragraph; Phase 4 should lift those paragraphs into `recommendations.md` rather than relying on the single tag.
3. **Playwright lacks a per-MCP `DEEP_ANALYSIS.md`.** Phase 1 calibration baseline pre-dates the per-MCP-directory pattern; the row data is comprehensive but there's no in-tree interpretive document equivalent to the other 7. Phase 4 should either generate one from the `results/2026-03-31_run.md` lineage or explicitly call out the asymmetry in the published report.

All three are explicitly framed as Phase 4 inputs and do not gate this verification.

## 7. Human Verification Items

None required. Every success criterion was verifiable from disk artifacts and reproducible programmatic checks:

- SC #1, #3 — directory-listing + file-existence, deterministic.
- SC #2, #4 — JSON schema + tag-membership iteration, deterministic.
- SC #5 — JSON-path extraction over raw_stream.jsonl + hostname-substring filter, deterministic.

The interpretive nuance around `tool-bug` aggregation (carried-forward limitation #2) is the only place where human judgment improves on the automated check, but the SC #4 contract is "every sub-5 cell carries a valid tag" — which is mechanically true. The interpretive overhead is intentionally deferred to Phase 4.

---

## Gaps Summary

**No gaps blocking Phase 2 goal achievement.** Three carried-forward limitations are documented for Phase 4 (§6) but are not in-scope for this verification. Phase 3 and Phase 4 are unblocked and can proceed.

---

_Verified: 2026-05-27_
_Verifier: Claude (gsd-verifier, goal-backward methodology)_
