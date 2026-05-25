# Plan 01-05 SUMMARY — Retry Gate + Aggregator + N/A-Aware Composite

**Plan:** 01-05  ·  **Phase:** 1 (Harness Foundation)  ·  **Status:** complete
**Tasks:** 9/9  ·  **Commits:** 5 (`17de356`, `688ada2`, `cf6c440`, `f51d1c2`, `ff6e42e`)
**Duration:** ~50 min (the SUMMARY write was orphaned by the prior session's 500-tool-call dead-man switch; recovered here from the executor's structured return)

## What was built

- **bench/failure_taxonomy.py** — `is_transient(exc_or_log) → (bool, tag)` classifier. Recognises WebSocket 1001/1006, ECONNRESET, MCP `initialize` timeout, HTTP 429/503, Chromium SIGKILL, EAGAIN. Failure tags: `{tool-bug, env-mismatch, target-flag, transient}`.
- **bench/transient.py** — `retry_stage(callable, max_attempts=3, sleep_between_s=30)` returns a `list[Attempt]` with classifications. Median pass-count is the recorded score; published as `n/3 passes` in the matrix.
- **scripts/aggregate_scores.py** — walks `results/<DATE>/<mcp>/` directories and emits `results/<DATE>/scores.json` in the EXACT shape `scoring/score.py` already consumes (no changes to `score.py`).
- **scripts/score_with_na.py** — N/A-aware composite wrapper. Imports `DIMENSIONS` from `score.py`; recomputes the composite for rows where any cell is N/A by dropping N/A cells from the weighted denominator. Read-only MCPs (lightpanda, firecrawl) show N/A on S4-S8 instead of 0.
- **scoring/rubric_notes.md** — addendum documenting the N/A semantics + failure-attribution taxonomy. `rubric.md` is untouched (locked).
- **Test files (4)** — `tests/test_failure_taxonomy.py` (18 tests), `tests/test_transient.py` (25), `tests/test_aggregate_scores.py` (21), `tests/test_score_with_na.py` (9). Total 73 plan-required tests pass.
- **Fixture trees** — `tests/fixtures/results_sample/2026-05-22/playwright/` (10 files) + `tests/fixtures/results_sample/2026-05-22/lightpanda/` (8 files) for integration testing the aggregator + N/A wrapper.

## Sacrosanct contract — verified

- `git diff scoring/score.py` → empty ✓
- `git diff scoring/rubric.md` → empty ✓

The N/A semantics live entirely in `scripts/score_with_na.py` (wrapper) and `scripts/aggregate_scores.py` (adapter). The locked scorer is unchanged from the 2026-03-31 wave.

## End-to-end regression

- Running `score_with_na.py` against the existing `results/scores.json` reproduces **Playwright composite = 9.07 exactly** — identical to `score.py` and to the 2026-03-31 published number.
- Sample fixture test: playwright composite **9.67** (no N/A cells); lightpanda composite **7.31** (N/A on S4-S8 drops weight from the denominator instead of zeroing it).

## Tests

- 73 plan-required tests pass (`uv run python -m unittest discover tests/ -v`).
- 105 project-total tests pass after this plan (52 new this plan + 53 from 01-01..01-04).

## Deviations

None. Two minor in-dev-loop fixes (stricter orphan-survivor regex; test refactor to assert that `score.py`'s literal-N/A crash IS the expected behaviour — confirming the wrapper is the only safe path) were caught before any commit.

## Files created

- `bench/failure_taxonomy.py`
- `bench/transient.py`
- `scripts/aggregate_scores.py`
- `scripts/score_with_na.py`
- `scoring/rubric_notes.md`
- `tests/test_failure_taxonomy.py`
- `tests/test_transient.py`
- `tests/test_aggregate_scores.py`
- `tests/test_score_with_na.py`
- `tests/fixtures/results_sample/2026-05-22/playwright/` (10 fixture files: raw_stream.jsonl, raw.jsonl, stage_s1.yml, stage_s{2..8}.md, cold_start.json, tokens.json, orphan_audit.log, transcript.md)
- `tests/fixtures/results_sample/2026-05-22/lightpanda/` (8 fixture files)

## Requirements satisfied

- **FAIRNESS-01** — 3-pass-of-3 retry gate active
- **FAIRNESS-02** — median-of-3 published as the recorded score
- **FAIRNESS-03** — N/A semantics enforced via wrapper; sacrosanct `score.py` preserved
- **FAIRNESS-06** — failure-attribution taxonomy enforced per row

## Notes for the next plan

- `scripts/aggregate_scores.py` consumes the `raw_stream.jsonl` shape produced by `scripts/run_mcp_session.sh` (plan 01-04). Soft-ordering: unit tests in this plan use static fixtures; real integration happens in plan 01-07's calibration run.
- Default `sleep_between_s=30` in `retry_stage` is intentional for Phase 1 calibration (Playwright is reliable; calibration is not adversarial). Phase 3's 1hr stability run may want a longer sleep — revisit then.
