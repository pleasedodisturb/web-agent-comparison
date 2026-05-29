---
phase: 1
plan: 07
type: execute
wave: 4
depends_on:
  - 01-01
  - 01-02
  - 01-03
  - 01-04
  - 01-05
  - 01-06
files_modified:
  - scripts/verify_calibration.sh
  - tests/test_calibration_math.py
  - results/.gitkeep   # ensures dir exists; the run itself populates results/<date>/playwright/
requirements:
  - HARNESS-05
success_criteria_advanced: [1, 2, 3, 4, 5]
status: planned
autonomous: false  # final gate; if calibration fails it MUST stop and surface to user per HANDOFF-GSD-AUTO STOP #1
estimate_hours: 2

must_haves:
  truths:
    - "`make bench-playwright && make score` produces a Playwright composite within ±0.5 of 9.07 (i.e. in the range [8.57, 9.57])."
    - "All 5 phase success-criteria are demonstrably met by the end of this plan."
    - "If the composite falls outside ±0.5, the harness STOPS and emits a structured diagnostic listing the most likely root causes (rubric drift, harness bug, fixture drift, Playwright MCP regression)."
    - "Inducing a synthetic transient failure (kill the MCP child mid-S5) triggers the retry gate; matrix records median pass-count of 2/3 instead of failing the run."
    - "Attempting to commit a fixture .mcp.json with an inline literal API key is rejected by the pre-commit hook; the ${VAR}-reference variant passes."
  artifacts:
    - path: "scripts/verify_calibration.sh"
      provides: "End-to-end gate: runs bench-playwright, score_with_na, compares against 9.07 ±0.5, exits non-zero if outside band; on failure, emits diagnostic report"
    - path: "tests/test_calibration_math.py"
      provides: "Unit test of the ±0.5 band logic + a regression test pinning the 2026-03 Playwright row's expected dimension scores"
    - path: "results/<date>/playwright/"
      provides: "Real evidence directory from a full end-to-end Playwright run on the snapshot fixtures"
  key_links:
    - from: "scripts/verify_calibration.sh"
      to: "results/<date>/scores.json"
      via: "reads aggregated scores; compares to 2026-03 baseline"
      pattern: "scores\\.json"
    - from: "scripts/verify_calibration.sh"
      to: "results/2026-03-31_run.md"
      via: "calibration target (Playwright composite 9.07)"
      pattern: "9\\.07"
---

## Goal

The go/no-go gate. Phase 1 has shipped successfully if and only if `make bench-playwright && make score` produces a Playwright composite within ±0.5 of the 2026-03-31 baseline of 9.07 against the self-hosted snapshot fixtures. If it doesn't, the harness is wrong or Playwright has regressed and Phase 2 cannot start — STOP and surface to the user (HANDOFF-GSD-AUTO STOP condition #1).

This plan also exercises and confirms the other four success criteria:
- (SC #2) the evidence directory is complete
- (SC #3) `scripts/check_prereqs.sh` detects missing binaries
- (SC #4) the retry gate handles a synthetic transient failure
- (SC #5) the pre-commit hook blocks inline secrets

## Files Modified

| File | New / Modified | Purpose |
|---|---|---|
| `scripts/verify_calibration.sh` | NEW | End-to-end gate that drives the run + reads the score + compares to baseline. |
| `tests/test_calibration_math.py` | NEW | Unit-test the ±0.5 band logic AND check that score_with_na produces the same result as score.py on the 2026-03 Playwright row (with all 8 dims scored — no N/A). |
| `results/<date>/playwright/` | NEW (populated by the run) | Real artifacts. |

## Tasks

1. **Write `tests/test_calibration_math.py`.**
   - Pin the 2026-03 Playwright row's dimension scores (from `results/scores.json`):
     ```python
     PLAYWRIGHT_2026_03 = {
       "data_quality": 10, "reliability": 9, "speed": 9, "token_efficiency": 7,
       "interaction_depth": 10, "js_rendering": 10, "setup_complexity": 9, "error_handling": 8,
     }
     ```
   - Compute via `scoring.score.compute_composite(PLAYWRIGHT_2026_03)`; assert == 9.07.
   - Compute via `scripts.score_with_na.compute_na_aware_composite(PLAYWRIGHT_2026_03)`; assert == 9.07 (with no N/A, the two should match).
   - Test the band logic:
     ```python
     def in_band(score: float, target: float = 9.07, tolerance: float = 0.5) -> bool:
         return target - tolerance <= score <= target + tolerance
     ```
   - Assert `in_band(9.07)` True, `in_band(8.57)` True (lower bound), `in_band(9.57)` True (upper bound), `in_band(8.56)` False, `in_band(9.58)` False.
   - **verify:** `uv run python -m unittest tests.test_calibration_math` passes.

2. **Write `scripts/verify_calibration.sh`.**
   - Shebang `#!/usr/bin/env bash`, `set -euo pipefail`.
   - Phase 1 steps, in order, each exiting fast on failure:
     1. **Prereq check (SC #3):** Run `scripts/check_prereqs.sh`. Must exit 0 (Mac Mini has all 7 binaries per HANDOFF). Also test: temporarily `mv $(command -v playwright-mcp) /tmp/.playwright-mcp.hidden`, re-run `scripts/check_prereqs.sh`, assert exit code 1 AND the output contains `playwright-mcp: missing`. Restore the binary.
     2. **Pre-commit hook test (SC #5):** Create a scratch git repo in `tmp/`, copy `scripts/hooks/pre-commit` into it, copy a fixture `.mcp.json` containing inline `"fc-abcdefghij1234567890..."`, attempt `git commit`. Assert exit code 1 + message contains `Inline secret detected`. Then replace the fixture with the `${FIRECRAWL_API_KEY}` variant and attempt `git commit`. Assert exit code 0.
     3. **Real run (SC #1 + SC #2):** `make bench-playwright`. After it returns, `make score` reading from `results/<date>/scores.json`.
     4. **Read the Playwright composite from scores.json:** `uv run python -c "import json, sys; data = json.load(open('results/<date>/scores.json')); from scripts.score_with_na import compute_na_aware_composite; pw = data.get('Playwright MCP') or data.get('playwright'); composite = compute_na_aware_composite(pw['scores']); print(composite); sys.exit(0 if 8.57 <= composite <= 9.57 else 1)"`.
     5. **Evidence-directory completeness (SC #2):** Check every required file exists:
        ```bash
        REQ=(transcript.md raw_stream.jsonl cold_start.json tokens.json tls.json stability.log orphan_audit.log tools_inventory.json)
        for f in "${REQ[@]}"; do
          test -f "results/${DATE}/playwright/$f" || { echo "MISSING: $f"; exit 1; }
        done
        # At least 3 stage_s*.* artifacts must exist
        test "$(ls results/${DATE}/playwright/stage_s*.* 2>/dev/null | wc -l)" -ge 3 || { echo "Fewer than 3 stage artifacts"; exit 1; }
        # orphan_audit.log must show 0 survivors
        grep -q "0 survivors\|SURVIVORS: 0\|KILLED pid=" results/${DATE}/playwright/orphan_audit.log || { echo "orphan_audit.log doesn't confirm clean state"; exit 1; }
        ```
     6. **Synthetic transient (SC #4):** This is the diagnostic-only step. Run a second Playwright session with a sidecar that kills the MCP child during the first tool call of S5: `( sleep 5; pkill -KILL -f playwright-mcp ) &` then `scripts/run_mcp_session.sh playwright`. Assert that `results/<date>/playwright_retry/raw.jsonl` shows 2 or 3 attempts AND the final stage status is PASS or N/3=2 (the retry recovered). The harness must NOT exit non-zero on this scenario; the retry should rescue it. Also test the `/etc/hosts` block scenario: temporarily add `127.0.0.1 tls.peet.ws` to `/etc/hosts` (sudo required — if not available in the runner's env, this sub-test is SKIPPED with a documented warning), run a session, assert the transient classifier flagged ECONNRESET. (Note: this is somewhat synthetic since TLS work is deferred to G-710 — the substitute is to use a stage that intentionally hits a synthetic 503-returning endpoint served by `scripts/serve_fixtures.sh` extended with a `/transient_test` route. Add this route in the script.)
     7. **Final report:** If all 6 sub-steps pass, emit `verify_calibration: PASS — composite=${COMPOSITE}, in_band=[8.57, 9.57], all 5 SC met` and exit 0.
   - **If any step fails:** emit a structured diagnostic to `results/<date>/CALIBRATION_DIAGNOSTIC.md` listing:
     - Which step failed
     - The observed value (e.g. `composite=7.42` if out of band)
     - The four most likely root causes (rubric drift, harness bug, fixture drift, Playwright MCP regression)
     - A copy-paste command to inspect: `cat results/<date>/playwright/transcript.md | head -50`, `cat results/<date>/playwright/orphan_audit.log`, `diff <(jq -S . results/scores.json) <(jq -S . results/<date>/scores.json) | head -100`
     - Exit code 1 and STOP per HANDOFF-GSD-AUTO STOP #1.
   - **verify:** `bash -n scripts/verify_calibration.sh` syntax-checks; running the script end-to-end on the Mac Mini either exits 0 (calibration passes) or exits 1 with a diagnostic.

3. **Execute the calibration.**
   - This is the actual go/no-go step.
   - Run `bash scripts/verify_calibration.sh`.
   - **Expected result:** exit 0 with `composite=9.X` somewhere in the 8.57–9.57 range, accompanied by a `results/<date>/playwright/` directory full of artifacts.
   - **If it fails:** STOP. Do not commit the failed run. Surface the `CALIBRATION_DIAGNOSTIC.md` to the user per the HANDOFF-GSD-AUTO STOP condition.
   - **verify:** Exit code 0 + a `results/<date>/scores.json` with a Playwright composite in the band + a populated evidence directory.

4. **Document the calibration result.**
   - If passing: write `results/<date>/PHASE1_CALIBRATION.md` containing:
     - Date + machine + Claude Code version (sourced from `versions.json`)
     - The observed composite
     - The 2026-03 baseline (9.07)
     - The delta
     - A statement: "Phase 1 calibration PASS. Harness reproduces the 2026-03 Playwright result within ±0.5. Phase 2 may proceed."
     - The orphan_audit summary (must say `0 survivors`)
   - If failing: do not write this file; the diagnostic from task 2 step 7 is the artifact.
   - **verify:** `cat results/<date>/PHASE1_CALIBRATION.md` shows the PASS statement.

## Acceptance

- All 5 phase success criteria pass through `scripts/verify_calibration.sh` end-to-end.
- `results/<date>/PHASE1_CALIBRATION.md` exists and records a PASS with composite in [8.57, 9.57].
- `tests/test_calibration_math.py` passes — the math layer is unit-tested independent of any real Playwright run, so a future re-calibration can rely on the band logic without re-running the full bench.
- `scoring/score.py` is byte-for-byte unchanged: `git diff scoring/score.py` shows zero lines changed across all of Phase 1 (verify at this final step).

## Dependencies

- ALL of plans 01-01 through 01-06. This is the final wave.

## Notes / Pitfalls

- **HANDOFF-GSD-AUTO STOP condition #1:** "Phase 1 cannot reproduce 2026-03 Playwright score (~9.07 ±0.5). This is the harness's go/no-go gate. If it fails, either the rubric is wrong, the harness is wrong, the fixtures drifted, or Playwright MCP regressed. STOP and surface." This plan operationalizes that condition.
- **Pitfall 8 (public-fixture rot):** If Playwright's S2 (Ashby SPA) regresses because the snapshot is an empty shell (per plan 01-03's Ashby caveat), the composite may drop below the band purely from S2. Diagnostic step recognizes this and surfaces "fixture drift" as a likely cause. **Mitigation:** if S2 is FAIL on the snapshot but PASS against the live URL, document the snapshot-only deficiency in `PHASE1_CALIBRATION.md` and decide with the user whether to accept the lower S2 score or invest in capturing the runtime API responses for the SPA (latter is out of scope per CONTEXT.md but may be the right call).
- **Pitfall 14 (scope creep):** This plan is the LAST plan in Phase 1. Resist the temptation to add "while we're here let's also..." additions. Lock the rubric + candidate set + harness.
- **Pitfall 9 (orphan accumulation):** Step 5 explicitly checks `orphan_audit.log`. A non-zero survivor count is a harness bug, not a Playwright bug — surface that distinction clearly in the diagnostic if it occurs.
- **Pitfall 1 (transient tank):** Step 6 confirms the retry gate works in practice, not just in unit tests.
- **Anti-Pattern 1 (paste transcripts):** All evidence lives in files. The verify script reads files; it does NOT re-execute prompts.

## Out of Scope

- Calibrating the OTHER 6 MCPs (Phase 2).
- Capturing cold-start / TLS / stability for Playwright in real (deferred — Phase 3 / G-710).
- The headline report document (`results/2026-05-XX-mcp-comparison.md`) — Phase 4.
- Updating the README with the headline verdict — Phase 4.
- Cross-machine validation (MacBook) — deferred to G-710.
