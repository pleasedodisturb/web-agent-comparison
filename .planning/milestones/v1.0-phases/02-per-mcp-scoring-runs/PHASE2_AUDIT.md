# Phase 2 Audit — 2026-05-26

**Plan:** 02-07 (cross-row attribution audit)
**Linear ticket:** G-703 (umbrella), G-715..G-720 (per-MCP sub-tickets)
**Auditor:** GSD executor (Plan 02-07 Task 1+2)
**Verdict:** **PASS — Phase 2 contracts upheld. Phase 3 + 4 are unblocked.**

## Per-MCP status table

| MCP | Status | Capability | Mode | Composite (N/A-aware) | Sub-5 cells w/ attribution | Issues |
|-----|--------|-----------|------|----------------------|----------------------------|--------|
| `playwright`         | SCORED | tool-only          | default            | **7.93** | 0/0  | Capability+mode injected by this audit (was missing) — scoring values preserved byte-for-byte |
| `chrome-devtools`    | SCORED | tool-only          | default            | **5.60** | 2/2  | — |
| `browser-use-direct` | SCORED | LLM-augmented      | direct             | **5.87** | 2/2  | — (Vitalik headline-claim CONFIRMED/REFUTED — see DEEP_ANALYSIS.md) |
| `browser-use-agent`  | SKIPPED | LLM-augmented     | agent              | 0.0\*    | 0/0  | reason=LLM_KEY_ABSENT; SKIPPED.md has re-run procedure |
| `cloakbrowser`       | SCORED | stealth-specialist | sandbox-loopback   | **8.33** | 0/0  | SANDBOX_PROOF.md attests zero non-loopback hostnames |
| `obscura`            | SCORED | stealth-specialist | no-stealth-flag    | **3.27** | 4/4  | `--stealth` disabled per SAFETY-03 |
| `firecrawl`          | SCORED | cloud              | markdown           | **4.23** | 2/2  | S1-S3 FAIL → env-mismatch (cloud-vs-loopback architectural caveat) |
| `lightpanda`         | SCORED | js-light           | default            | **6.31** | 1/1  | js_rendering=2 architectural-by-design |

\* `browser-use-agent` composite=0.0 is a `score_with_na.py`
   degenerate-case fallback (all-N/A → total_weight=0 → 0.0). The
   `status: "SKIPPED"` field is the source of truth. **Known
   limitation for Phase 4 to address** — `score_with_na.py` is
   adjacent-to-sacrosanct and was not modified this wave.

## Phase 2 Success Criteria — per-SC verdict

### SC #1 — All 7 MCPs have evidence dirs or SKIPPED.md → **PASS**

scores.json contains all 8 expected rows (browser-use is dual-mode per
FAIRNESS-05). One row (`browser-use-agent`) is SKIPPED with
`SKIPPED.md` present; the other 7 are SCORED with full evidence
directories.

| Row | Evidence path |
|-----|---|
| `playwright` | (Phase 1 calibration — no per-MCP dir; scored row in scores.json) |
| `chrome-devtools` | `results/2026-05-26/chrome-devtools/DEEP_ANALYSIS.md` + PASS{1,2,3}/ |
| `lightpanda` | `results/2026-05-26/lightpanda/DEEP_ANALYSIS.md` + PASS{1,2,3}/ |
| `firecrawl` | `results/2026-05-26/firecrawl/DEEP_ANALYSIS.md` + PASS{1,2,3}/ |
| `obscura` | `results/2026-05-26/obscura/DEEP_ANALYSIS.md` + PASS{1,2,3}/ |
| `browser-use-direct` | `results/2026-05-26/browser-use-direct/DEEP_ANALYSIS.md` + PASS{1,2,3}/ |
| `browser-use-agent` | `results/2026-05-26/browser-use-agent/SKIPPED.md` |
| `cloakbrowser` | `results/2026-05-26/cloakbrowser/DEEP_ANALYSIS.md` + SANDBOX_PROOF.md + PASS{1,2,3}/ |

### SC #2 — Read-only MCPs show N/A (not 0) for S4-S8 → **PASS**

| MCP | interaction_depth | stages.S4 | stages.S5 | stages.S6 | stages.S7 | stages.S8 |
|-----|-------------------|-----------|-----------|-----------|-----------|-----------|
| `lightpanda` | `"N/A"` (string) | `"N/A"` | `"N/A"` | `"N/A"` | `"N/A"` | `"N/A"` |
| `firecrawl`  | `"N/A"` (string) | `"N/A"` | `"N/A"` | `"N/A"` | `"N/A"` | `"N/A"` |

Both rows use the FAIRNESS-03 N/A semantics. `score_with_na.py` drops
N/A cells from the weighted denominator (verified via composite
recomputation: lightpanda=6.31 with interaction_depth dropped vs.
~5.65 if treated as 0).

### SC #3 — browser-use produces two rows (direct + agent) → **PASS**

Both `browser-use-direct` (SCORED, mode=`direct`) AND
`browser-use-agent` (SKIPPED, mode=`agent`) present in scores.json
with distinct `mode` field values. FAIRNESS-05 contract upheld.
Capability shared (`LLM-augmented`); mode distinguishes the
measurement.

### SC #4 — Every row has capability tag + every sub-5 cell has attribution → **PASS (with 1 injection)**

- **Capability tags:** 8/8 rows have valid capability tags from
  `{tool-only, LLM-augmented, stealth-specialist, cloud, js-light}`.
  Pre-audit state: 7/8 had tags; `playwright` was missing both
  `capability` and `mode` (calibration row from Phase 1 was authored
  before the FAIRNESS-04 contract crystallised). Audit injected
  `capability: "tool-only"` and `mode: "default"` — see **Tag
  injections** below.
- **Attribution tags:** 11/11 sub-5 cells across all SCORED rows carry
  a valid tag from `{tool-bug, env-mismatch, target-flag, transient}`.
  Distribution: 9 `tool-bug`, 2 `env-mismatch`, 0 `target-flag`,
  0 `transient`. No injections required for attribution.

Sub-5 cell inventory (all already tagged pre-audit):
- `browser-use-direct.error_handling=2` → tool-bug
- `browser-use-direct.interaction_depth=2` → tool-bug
- `chrome-devtools.error_handling=2` → tool-bug
- `chrome-devtools.interaction_depth=0` → tool-bug
- `firecrawl.data_quality=0` → env-mismatch
- `firecrawl.js_rendering=2` → env-mismatch
- `lightpanda.js_rendering=2` → tool-bug
- `obscura.data_quality=0` → tool-bug
- `obscura.error_handling=2` → tool-bug
- `obscura.interaction_depth=0` → tool-bug
- `obscura.js_rendering=2` → tool-bug

### SC #5 — cloakbrowser evidence shows zero non-loopback hostnames → **PASS**

- `results/2026-05-26/cloakbrowser/SANDBOX_PROOF.md` exists.
- No `SANDBOX_VIOLATION.md` in the cloakbrowser/ dir.
- Phase 1 audit in SANDBOX_PROOF.md (`cloak_navigate` URLs across
  3 passes): all 6 unique navigate targets are `http://127.0.0.1:8765/...`.
- Phase 2 transcript hostname sweep: the 10 non-loopback hostnames
  surfaced in transcripts are CONTENT strings extracted from snapshot
  HTML (og:url, anchor hrefs, stylesheet links), NOT
  `cloak_navigate`/`fetch()` arguments.
- SAFETY-04 contract upheld: closed-source binary was only ever
  pointed at the loopback snapshot server.

## Tag injections

This audit made **exactly one** injection set. All scoring values
preserved byte-for-byte; only two field additions to the `playwright`
row in `scores.json`:

| Row | Field | Before | After | Source |
|---|---|---|---|---|
| `playwright` | `capability` | (absent) | `"tool-only"` | CONTEXT.md `## Decisions § Capability Tags` — playwright = tool-only |
| `playwright` | `mode` | (absent) | `"default"` | Precedent: chrome-devtools, lightpanda also use `mode: "default"` for non-mode-switching MCPs |

No attribution injections were required. The 11 pre-existing sub-5
cells all already carried valid attribution tags from prior plans
02-01 through 02-05. (Per **gotchas**: firecrawl `env-mismatch`,
obscura `tool-bug`, chrome-devtools `tool-bug`, lightpanda `tool-bug`,
browser-use-direct `tool-bug` were all set in their originating plans
and were NOT touched by this audit.)

Diff (additive only):
```diff
@@ -532,6 +532,8 @@
       }
     },
     "attribution": {},
+    "capability": "tool-only",
+    "mode": "default",
     "scores": {
       "data_quality": 10,
       "error_handling": 5,
```

## Attribution interpretation caveats

The 4-tag taxonomy (`tool-bug`, `env-mismatch`, `target-flag`,
`transient`) is documented in `bench/failure_taxonomy.py` and in
`02-CONTEXT.md`. Several rows use `tool-bug` as the **conservative
aggregator default** when the true root cause is more nuanced — the
DEEP_ANALYSIS.md for each MCP carries the interpretive paragraph that
the single tag cannot. Phase 4 synthesis must lift these caveats:

- `browser-use-direct.interaction_depth=2` tagged `tool-bug`: the real
  root cause is fixture-side React-hydration clobber on Greenhouse;
  browser-use-direct's tool surface is correctly capability-incomplete
  for the SSR-rescue workaround (no eval/CDP primitive). The
  DEEP_ANALYSIS.md explicitly notes "the taxonomy's 4 tags don't
  separate 'MCP fault' from 'agent fault'" — same Phase-4 footnote
  applies as for chrome-devtools and obscura.
- `chrome-devtools.interaction_depth=0` + `error_handling=2` tagged
  `tool-bug`: 2-of-3 passes failed S4-S8 on the same Greenhouse
  React-clobber wall; 1-of-3 (PASS3) found the SSR-rescue workaround.
  The failure is in the agent's interaction with the MCP, not in the
  MCP binary — `tool-bug` is the aggregator default per FAIRNESS-06.
- `lightpanda.js_rendering=2` tagged `tool-bug`: architectural by
  design (Zig engine has no JS runtime). The "bug" is the
  differentiator. Documented as the headline negative result in
  lightpanda's DEEP_ANALYSIS.md.
- `obscura.{data_quality,error_handling,interaction_depth,js_rendering}`
  all tagged `tool-bug`: trace to a single root-cause chain (SSRF guard
  → agent strategy variance → CDP wedge), not four independent bugs.

These are not audit failures; they are documented interpretive
boundaries of the 4-tag taxonomy. The single-tag-per-cell rule is
preserved; the per-cell rationale is in each row's DEEP_ANALYSIS.md.

## SKIPPED rows summary

| Row | Reason | Re-run procedure |
|-----|--------|------------------|
| `browser-use-agent` | `LLM_KEY_ABSENT` (OPENAI_API_KEY zero-length sentinel) | `rbw unlock && export OPENAI_API_KEY=$(rbw get …) && bash scripts/run_mcp_session.sh browser-use --mode agent` (full procedure in `results/2026-05-26/browser-use-agent/SKIPPED.md`) |

## Known limitations for Phase 4

1. **`score_with_na.py` renders SKIPPED rows as composite=0.0** —
   degenerate-case fallback when `total_weight=0` (all-N/A row).
   Phase 4 matrix builder MUST consult the `status` field on each row,
   not just the composite. Documented in browser-use-direct
   DEEP_ANALYSIS.md and 02-05 SUMMARY.md as a known pre-Phase-4 fix.
   `score_with_na.py` was NOT modified by this audit (adjacent to
   sacrosanct `scoring/score.py`; should be revisited under G-710's
   scoring-engine PR, not as a Phase-2 patch).
2. **`tool-bug` aggregator default loses MCP-fault vs. agent-fault
   distinction** — the 4-tag taxonomy collapses fixture-side issues
   (React-clobber), capability gaps (no eval primitive in
   browser-use-direct), and harness-incompatibility (obscura SSRF
   guard) into a single tag. DEEP_ANALYSIS.md per row has the
   interpretive paragraph; Phase 4 should lift those paragraphs into
   `recommendations.md` rather than relying on the tag alone.
3. **playwright lacks per-MCP DEEP_ANALYSIS.md** — Phase 1 calibration
   baseline; the row data is comprehensive but there's no in-tree
   interpretive document equivalent to the other 7. Phase 4 should
   either generate one from `results/2026-03-31_run.md` lineage or
   explicitly call out the asymmetry.

## scoring/score.py SACROSANCT check

```
$ git diff main -- scoring/score.py | wc -l
0
```

**Confirmed.** Zero changes to `scoring/score.py` across all of Phase 2.

## scores.json scoring-value preservation

The audit injected `capability` and `mode` on the playwright row only.
All 8 rows' `scores`, `stages`, `attempts`, and `attribution` objects
are byte-for-byte preserved. Diff (full):

```diff
@@ -532,6 +532,8 @@
     "attribution": {},
+    "capability": "tool-only",
+    "mode": "default",
     "scores": { ... unchanged ... }
```

## Phase 1 test suite

```
$ .venv/bin/python -m pytest --no-header -q
176 passed in 8.92s
```

All Phase-1 tests still pass. No regressions.

## Linear coordination

- **G-703 (parent):** Phase 2 complete — 7 MCPs evaluated (6 SCORED +
  1 SKIPPED dual-mode). Capability tags + attribution validated. Ready
  for Phase 3 + 4.
- Per-MCP sub-tickets (G-715..G-720) referenced in each plan's
  SUMMARY.md but NOT created at run time (per OUTREACH-03 ownership —
  same pattern as 02-03/04/05/06). DEEP_ANALYSIS.md files are ready to
  lift into ticket comments when the per-MCP ticket sweep lands.

## Phase 3 + 4 readiness

- [x] Phase 3 can begin (cross-cutting measurements — uses scores.json
      as baseline; all 8 rows validated)
- [x] Phase 4 can wait on Phase 3 completion before synthesis;
      `CAPABILITY_MATRIX.md` is ready to lift verbatim as the
      FAIRNESS-04 second-view artifact
