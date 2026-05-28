# Phase 1 Calibration — PASS

**Date (UTC):** 2026-05-25
**Gate:** `scripts/verify_calibration.sh`
**Result:** **PASS**

## Calibration

| | Value |
|---|---|
| 2026-03-31 published Playwright composite (historical, via `scoring/score.py`) | 9.07 |
| Harness re-baseline (2026-03 evidence re-scored via `aggregate_scores.py`) | 8.33 |
| Observed (2026-05-25, this run) | **7.93** |
| Delta vs re-baseline | -0.4 |
| Accept band | [7.83, 8.83] |
| Tolerance | ±0.5 |

**Phase 1 calibration PASS. Harness reproduces the 2026-03 Playwright
evidence under its own heuristic scoring within ±0.5 of the apples-to-
apples re-baseline. Phase 2 may proceed.**

The published 2026-03 composite (9.07) is unchanged and remains the
methodology's wave-to-wave anchor — see `scoring/rubric_notes.md`
"Calibration Re-Baseline (2026-05-26)" for why the gate validates
against the heuristic re-baseline (8.33) instead.

## Environment

| | Value |
|---|---|
| Host OS | Darwin |
| Claude Code | 2.1.142 (Claude Code) |
| Node | v26.0.0 |
| Python (venv) | Python 3.14.5 |

## Success criteria

- **SC #1 — Composite in band:** PASS (composite=7.93 ∈ [7.83, 8.83])
- **SC #2 — Evidence directory complete:** PASS (8 required files present, 8 stage artifacts)
- **SC #3 — `check_prereqs.sh` detects missing binaries:** PASS (hide-probe rejected the run)
- **SC #4 — Retry gate handles synthetic transient:** PASS (see `results/2026-05-25/.sc4_retry.json`)
- **SC #5 — Pre-commit hook blocks inline secrets:** PASS (scratch-repo probe rejected inline, accepted ${VAR})

## Process hygiene

ORPHANS=1
KILLED_COUNT=0

## Sacrosanct check

scoring/score.py: no uncommitted changes (SACROSANCT contract upheld)

## Reproducibility

```bash
bash scripts/verify_calibration.sh
```

Per-MCP evidence: `results/2026-05-25/playwright/`
Aggregated scores: `results/2026-05-25/scores.json`
