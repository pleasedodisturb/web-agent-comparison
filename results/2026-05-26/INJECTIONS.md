# Phase 2 Audit Injections — 2026-05-26

**Plan:** 02-07 (cross-row attribution audit)
**Linear ticket:** G-703

This file records every byte-level change the audit made to
`scores.json`. The audit's contract: scoring values byte-for-byte
preserved; only missing capability / attribution / mode tags may be
injected, and every injection is documented here for the audit trail.

## Injection inventory

### Injection 1 — `playwright.capability` + `playwright.mode`

| Field | Before | After | Justification |
|-------|--------|-------|---------------|
| `playwright.capability` | (absent) | `"tool-only"` | CONTEXT.md `## Decisions § Capability Tags` explicitly maps `playwright → tool-only`. The row was authored during Phase 1 calibration (plan 01-07) before the FAIRNESS-04 capability-tag contract crystallised. |
| `playwright.mode` | (absent) | `"default"` | Precedent: every other non-mode-switching MCP in this matrix (chrome-devtools, lightpanda) uses `mode: "default"`. Stealth-specialists and dual-mode MCPs use distinct values (`sandbox-loopback`, `no-stealth-flag`, `direct`, `agent`). |

**Unambiguous:** Yes. Both tag values were specified in
`02-CONTEXT.md` and match the precedent set by all 6 prior Phase 2
plans (02-01..02-06). No alternative interpretation exists.

**Diff (the entire scope of this injection set):**
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

## Non-injections (preserved as-is)

The audit considered and **did NOT** modify the following, even though
the gotchas section of the executor prompt flagged them for review:

### browser-use-direct.{interaction_depth,error_handling} attribution

- **Prompt gotcha said:** "browser-use-direct row has sub-5 cells from
  S4-S7 fixture-side React-hydration clobber. Should be tagged
  `target-flag` (the fixture itself, not the MCP) — verify per 02-05
  SUMMARY."
- **Actual existing tag:** `tool-bug`
- **Decision:** Preserve as-is. The browser-use-direct DEEP_ANALYSIS.md
  explicitly considered the same question and chose `tool-bug` with
  full documentation: "the 4-element taxonomy doesn't offer
  `target-flag` for 'MCP cannot reach the form'" and "Phase 4
  synthesis should note this attribution ambiguity (same caveat
  applies to chrome-devtools and obscura's S4-S8 attribution)." The
  interpretive nuance lives in DEEP_ANALYSIS.md per FAIRNESS-06's
  single-tag aggregator-default contract. Re-attributing to
  `target-flag` would CHANGE the scored data (the tag IS data), which
  violates the audit's byte-for-byte preservation contract.
- **Sacrosanct invariant:** "the byte-for-byte scoring values in
  scores.json MUST NOT change from the audit — only missing tags are
  added." The tag was NOT missing; it was set with intentional
  documentation. PHASE2_AUDIT.md `## Attribution interpretation
  caveats` lifts the DEEP_ANALYSIS.md nuance for Phase 4 to honour.

### chrome-devtools, obscura, lightpanda, firecrawl attribution tags

- All pre-existing, set in their originating plans (02-01, 02-02, 02-03,
  02-04). No changes.

### scores values (every row, every dimension)

- All preserved byte-for-byte. The `git diff` on `scores.json` shows
  EXCLUSIVELY the two-line `playwright` capability/mode addition.

## Verification

Re-run the Plan Task 1 audit script after injection:

```
.venv/bin/python -c "
import json, sys
data = json.load(open('results/2026-05-26/scores.json'))
expected_rows = {'playwright','chrome-devtools','lightpanda','firecrawl','obscura','browser-use-direct','browser-use-agent','cloakbrowser'}
allowed_caps = {'tool-only','LLM-augmented','stealth-specialist','cloud','js-light'}
allowed_attr = {'tool-bug','env-mismatch','target-flag','transient'}
errors = []
# ... full validation ...
"
# Output: AUDIT PASS
```

Result: **AUDIT PASS** after the single injection set above.
