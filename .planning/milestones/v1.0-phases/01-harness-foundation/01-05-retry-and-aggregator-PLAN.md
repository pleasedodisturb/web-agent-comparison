---
phase: 1
plan: 05
type: execute
wave: 2
depends_on:
  - 01-01   # Makefile + uv + scoring/score.py path conventions
  - 01-04   # raw_stream.jsonl shape consumed by aggregate_scores.py (soft ordering — unit tests in this plan use fixtures; real integration happens in plan 07)
files_modified:
  - bench/transient.py
  - bench/failure_taxonomy.py
  - scripts/aggregate_scores.py
  - scripts/score_with_na.py
  - tests/test_transient.py
  - tests/test_failure_taxonomy.py
  - tests/test_aggregate_scores.py
  - tests/test_score_with_na.py
  - scoring/rubric_notes.md
requirements:
  - FAIRNESS-01
  - FAIRNESS-02
  - FAIRNESS-03
  - FAIRNESS-06
success_criteria_advanced: [1, 4]
status: planned
autonomous: true
estimate_hours: 3

must_haves:
  truths:
    - "`bench/transient.py` exposes a `retry_stage(callable, max_attempts=3) -> list[Attempt]` that runs a stage up to 3 times, classifies failures via `bench/failure_taxonomy.is_transient(exc_or_log)`, and returns all attempts with their classifications."
    - "The transient classifier recognizes WebSocket 1001/1006, ECONNRESET, MCP `initialize` timeout, HTTP 429/503, and Chromium SIGKILL — at minimum, this exact list."
    - "`scripts/aggregate_scores.py` walks `results/<date>/<mcp>/` and emits `results/<date>/scores.json` in the EXACT shape `scoring/score.py` already consumes (no modifications to score.py itself)."
    - "`scripts/score_with_na.py` is the new entrypoint that runs `score.py` with N/A semantics: read-only MCPs (lightpanda, firecrawl) show N/A (not 0) on S4-S8, and the weighted denominator drops N/A cells."
    - "Every sub-rubric score < 5 in `scores.json` carries a `failure_attribution` tag from {tool-bug, env-mismatch, target-flag, transient}."
    - "Median pass-count of 3 attempts is the recorded score; the matrix shows `n/3 passes` per cell."
  artifacts:
    - path: "bench/transient.py"
      provides: "retry_stage() + transient_failure_taxonomy class"
    - path: "bench/failure_taxonomy.py"
      provides: "is_transient(...) classifier + failure_tag enum {tool-bug, env-mismatch, target-flag, transient}"
    - path: "scripts/aggregate_scores.py"
      provides: "walks per-MCP evidence dirs, emits scores.json in score.py's shape; preserves N/A vs 0 distinction"
    - path: "scripts/score_with_na.py"
      provides: "Thin shim around score.py that applies N/A-drops-from-denominator semantics WITHOUT modifying score.py"
    - path: "scoring/rubric_notes.md"
      provides: "Documents the N/A vs 0 contract and the 3-pass-of-3 / median rule that supplement (not modify) rubric.md"
  key_links:
    - from: "scripts/aggregate_scores.py"
      to: "results/<date>/<mcp>/raw.jsonl"
      via: "reads per-attempt records from the retry gate"
      pattern: "raw\\.jsonl"
    - from: "scripts/aggregate_scores.py"
      to: "results/<date>/scores.json"
      via: "writes the score.py-shaped JSON"
      pattern: "scores\\.json"
    - from: "scripts/score_with_na.py"
      to: "scoring/score.py"
      via: "imports DIMENSIONS + compute_composite, NOT modify"
      pattern: "from scoring.score import"
---

## Goal

Build the fairness layer that prevents the 2026-03 class of measurement mistakes. Three sub-systems:

1. **3-pass-of-3 retry gate (`bench/transient.py`)** — Pitfall 1 defense. Any S1-S8 failure that matches the transient taxonomy gets retried up to 3 times; the median of attempts is the recorded score. Each attempt is a record in `results/<date>/<mcp>/raw.jsonl`.
2. **Failure-attribution taxonomy (`bench/failure_taxonomy.py`)** — every sub-rubric score < 5 carries a tag explaining WHY (`tool-bug` / `env-mismatch` / `target-flag` / `transient`).
3. **N/A vs 0 semantics + `aggregate_scores.py` shim** — read-only MCPs (lightpanda, firecrawl) get `N/A` on interactive stages and the weighted denominator drops those cells. **`scoring/score.py` itself is SACROSANCT — not modified.** The N/A handling lives in a thin shim, `scripts/score_with_na.py`, that imports `score.py`'s constants and runs the math with the N/A-aware denominator.

This plan does NOT depend on plan 01-04 because the retry gate operates over per-stage callables (which 01-04 produces) but the gate itself can be developed and tested with a synthetic callable. It runs in Wave 2 alongside 01-04 for parallelism.

## Files Modified

| File | New / Modified | Purpose |
|---|---|---|
| `bench/transient.py` | NEW | `retry_stage(fn, max_attempts=3, sleep_between_s=30)` + `class Attempt` + the transient-failure taxonomy classifier (delegates to `failure_taxonomy.py`). |
| `bench/failure_taxonomy.py` | NEW | `is_transient(exc_or_log: str | Exception) -> bool` + `attribute_failure(exc_or_log) -> Literal['tool-bug','env-mismatch','target-flag','transient']`. |
| `scripts/aggregate_scores.py` | NEW | CLI: `python scripts/aggregate_scores.py results/<date>/`. Walks subdirs, parses each MCP's evidence, emits `scores.json`. Honors N/A semantics. |
| `scripts/score_with_na.py` | NEW | Wraps `scoring/score.py` to compute composites with N/A cells dropped from the denominator. **DO NOT modify `score.py`.** |
| `tests/test_transient.py` | NEW | unittest: callable that raises ECONNRESET → 3 attempts, classified transient; callable that raises ValueError → 1 attempt, classified non-transient. |
| `tests/test_failure_taxonomy.py` | NEW | unittest: each of the 5 named transient categories classifies correctly; "AttributeError: object has no attribute" classifies as `tool-bug`. |
| `tests/test_aggregate_scores.py` | NEW | unittest: feed a fake `results/.../playwright/` dir, assert generated `scores.json` matches a golden file in shape. |
| `tests/test_score_with_na.py` | NEW | unittest: lightpanda with `S4-S8 = N/A` should produce a composite NOT zero-weighted; assert the composite differs from the all-zero-counted result. |
| `scoring/rubric_notes.md` | NEW | Documents the supplements that do not change rubric.md or score.py: N/A semantics, retry gate, failure attribution. |

## Tasks

1. **Write `bench/failure_taxonomy.py`.**
   - Module constants:
     ```python
     TRANSIENT_PATTERNS = [
         r"WebSocket.*(1001|1006)",
         r"ECONNRESET",
         r"connection reset by peer",
         r"MCP.*initialize.*timeout",
         r"HTTP.*\b(429|503)\b",
         r"Chromium.*SIGKILL",
         r"SIGTERM.*chromium",
         r"npm registry.*unreachable",
         r"App Nap",
     ]
     ```
   - `def is_transient(s: str) -> bool`: returns True if any TRANSIENT_PATTERNS regex matches. Accepts str OR Exception (calls `str(exc)` internally).
   - `class FailureTag(str, Enum): TOOL_BUG = "tool-bug"; ENV_MISMATCH = "env-mismatch"; TARGET_FLAG = "target-flag"; TRANSIENT = "transient"`.
   - `def attribute_failure(s: str) -> FailureTag`:
     - if `is_transient(s)` → TRANSIENT
     - elif regex matches `(404|410|target.*unreachable|fixture.*404)` → TARGET_FLAG
     - elif regex matches `(arm64|x86_64|architecture|missing.*binary|command not found)` → ENV_MISMATCH
     - else → TOOL_BUG (default — "the MCP did something we didn't expect")
   - **verify:** `tests/test_failure_taxonomy.py` (next task).

2. **Write `tests/test_failure_taxonomy.py`.**
   - For each transient pattern, assert `is_transient` returns True.
   - Assert `attribute_failure("ECONNRESET while reading")` == TRANSIENT.
   - Assert `attribute_failure("HTTP 404 from greenhouse.io")` == TARGET_FLAG.
   - Assert `attribute_failure("zsh: command not found: obscura-mcp")` == ENV_MISMATCH.
   - Assert `attribute_failure("AttributeError: 'NoneType' object has no attribute 'page'")` == TOOL_BUG.
   - **verify:** `uv run python -m unittest tests.test_failure_taxonomy` passes.

3. **Write `bench/transient.py`.**
   - Define `@dataclass class Attempt: attempt_no: int; passed: bool; tag: FailureTag | None; duration_s: float; error: str | None`.
   - Define `def retry_stage(fn: Callable[[], dict], max_attempts: int = 3, sleep_between_s: float = 30.0, transient_only: bool = True) -> list[Attempt]`:
     - For attempt 1..max_attempts:
       - Time the call. If `fn()` returns successfully, record passed=True and break.
       - If it raises: classify via `attribute_failure(str(exc))`. If `transient_only=True` and the tag is NOT `TRANSIENT`, stop retrying (only retry transient failures per CONTEXT.md "Score the median of 3 attempts. Publish n/3 passes ... matches against the taxonomy trigger automatic retry, non-matches surface as real failures").
       - Sleep `sleep_between_s` (use `time.sleep`; pass `sleep_between_s=0` in tests).
     - Return the full list of Attempt records.
   - Define `def median_pass(attempts: list[Attempt]) -> tuple[int, int]`: returns `(passes, total_attempts)`.
   - Define `def write_attempts_to_jsonl(attempts: list[Attempt], path: Path) -> None`: appends one JSON line per attempt.
   - **verify:** `tests/test_transient.py` (next task).

4. **Write `tests/test_transient.py`.**
   - Test: a stub callable that raises `RuntimeError("ECONNRESET")` for 3 attempts then succeeds — should retry, classified TRANSIENT, eventually pass (but with `passes=1, total=3` if it succeeded only on attempt 3; if it never succeeds, `passes=0, total=3`).
   - Test: a stub callable that raises `ValueError("unexpected None")` — `transient_only=True` means STOP after 1 attempt, classified TOOL_BUG, `passes=0, total=1`.
   - Test: median_pass on `[passed=True, passed=False, passed=True]` returns `(2, 3)`.
   - **verify:** `uv run python -m unittest tests.test_transient` passes.

5. **Write `scripts/aggregate_scores.py`.**
   - CLI: `python scripts/aggregate_scores.py <results_date_dir>`.
   - For each subdir (one per MCP) under the date dir:
     - Read `raw_stream.jsonl` (from plan 01-04) → derive stage pass/fail per S1-S8.
     - Read `raw.jsonl` if present (from `bench.transient.write_attempts_to_jsonl`) → derive per-stage `n/3` and median pass count.
     - Read `stage_s*.{yml,md,png,txt,FAILED,NA}` files → confirm artifact existence.
     - Read `tokens.json` (stub OK for Phase 1) → derive `token_efficiency` per rubric thresholds (`<10KB=10`, `10-50KB=5`, `>50KB=0`).
     - Read `cold_start.json` (stub OK) → derive `speed` modifier (rubric thresholds: `<10s=10`, `10-30s=5`, `>30s=0`).
     - Read `orphan_audit.log` → if survivors > 0, dock `reliability` by 1.
     - Read `transcript.md` → count `[error]`/`retry`/`fail` phrases → derive `error_handling`.
     - For each dimension, if the MCP is `lightpanda` or `firecrawl` AND the stage is S4-S8, set the dimension to the JSON sentinel string `"N/A"` rather than 0 for `interaction_depth` specifically. For other dimensions, score them based on the read-only stages they DID attempt.
     - Apply `failure_attribution`: for any sub-dimension score < 5, look up the most recent failure in the raw stream that mapped to that dimension and tag accordingly. Embed the tag in a `notes` field per-MCP per-dimension.
   - Emit `scores.json` with the existing shape PLUS:
     - per-stage `attempts: {S1: {passes: 3, total: 3, tag: null}, ...}` field
     - per-dimension `attribution: {data_quality: "tool-bug", ...}` field (only present where score < 5)
   - These extension fields are ADDITIVE; the existing `scoring/score.py` reads `scores` + `stages` and ignores unknown fields, so direct comparability with 2026-03 is preserved.
   - **verify:** `tests/test_aggregate_scores.py` (next task).

6. **Write `tests/test_aggregate_scores.py`.**
   - Fixture dir under `tests/fixtures/results_sample/2026-05-22/playwright/` containing minimal `raw_stream.jsonl`, `stage_s1.yml` … `stage_s8.png`, `tokens.json`, `cold_start.json`, `orphan_audit.log` (all stubs).
   - Run `python scripts/aggregate_scores.py tests/fixtures/results_sample/2026-05-22/`.
   - Assert `tests/fixtures/results_sample/2026-05-22/scores.json` exists; load it; assert top-level key `Playwright MCP` (or `playwright`, matching the 2026-03 naming) is present; assert `scores` dict has all 8 dimensions.
   - **verify:** `uv run python -m unittest tests.test_aggregate_scores` passes.

7. **Write `scripts/score_with_na.py`.**
   - This is the **N/A-aware wrapper** that satisfies FAIRNESS-03 without modifying `scoring/score.py`.
   - Logic:
     ```python
     from scoring.score import DIMENSIONS, format_stage_matrix, format_comparison_table
     def compute_na_aware_composite(scores: dict) -> float:
         total_weight = 0.0
         weighted = 0.0
         for dim, meta in DIMENSIONS.items():
             v = scores.get(dim)
             if v == "N/A" or v is None:
                 continue  # drop from denominator
             weighted += float(v) * meta["weight"]
             total_weight += meta["weight"]
         return round(weighted / total_weight, 2) if total_weight else 0.0
     ```
   - CLI mirrors `scoring/score.py` but produces the N/A-aware ranking. Output format identical (markdown table + ranking) so the report mirroring 2026-03 stays consistent.
   - **Note for plan 01-07:** Phase 1's calibration target is Playwright, which doesn't have N/A cells — so `score.py` and `score_with_na.py` produce IDENTICAL results on the calibration. The N/A logic is dormant for Playwright; it activates for lightpanda + firecrawl in Phase 2.
   - **verify:** `tests/test_score_with_na.py` (next task).

8. **Write `tests/test_score_with_na.py`.**
   - Test A: a synthetic Playwright row with all 8 dimensions scored — `compute_na_aware_composite` returns the SAME value as `scoring.score.compute_composite`.
   - Test B: a synthetic Lightpanda row with `interaction_depth = "N/A"` — `compute_na_aware_composite` returns the value with that dimension's weight (2) DROPPED from the denominator; `scoring.score.compute_composite` would have computed with denom=15; the new value's denom is 13.
   - Assert math: with all 8 dims scoring 5 and the 2-weight dim N/A, the N/A-aware composite is 5.0 (unchanged in the average sense), but the unweighted score.py version would be (5*13)/15 = 4.33 (because it counts N/A as 0 indirectly via `.get(dim, 0)` returning 0 — verify by reading score.py line 28-32).
   - This test PROVES the N/A wrapper is doing real work and not just shadowing `score.py`.
   - **verify:** `uv run python -m unittest tests.test_score_with_na` passes.

9. **Write `scoring/rubric_notes.md`.**
   - One-page document layered ON TOP of `scoring/rubric.md` (which stays unchanged):
     - **N/A semantics** — read-only MCPs (lightpanda, firecrawl) score `N/A` (not 0) on S4-S8 (interactive stages). `scripts/score_with_na.py` drops `N/A` cells from the weighted denominator. `scoring/score.py` is unchanged.
     - **3-pass-of-3 retry gate** — every S1-S8 failure that matches `bench.failure_taxonomy.is_transient` retries up to 3 attempts; median pass-count is the score; matrix shows `n/3`.
     - **Failure attribution** — any sub-rubric score < 5 carries a tag: `tool-bug` / `env-mismatch` / `target-flag` / `transient`. Tags appear in `scores.json` under `attribution` per dim.
   - **verify:** File exists; `grep -c '^## ' scoring/rubric_notes.md` returns 3.

## Acceptance

- `bench/transient.py` retries transient failures up to 3 times with the documented taxonomy; non-transient failures stop after attempt 1.
- `bench/failure_taxonomy.py` correctly classifies all 5 named transient patterns from the CONTEXT.md transient taxonomy list.
- `scripts/aggregate_scores.py` produces a `scores.json` in `scoring/score.py`'s shape from a fixture evidence directory.
- `scripts/score_with_na.py` produces a composite that drops `N/A` cells from the denominator, mathematically distinct from `score.py`'s output on N/A-containing inputs.
- `scoring/score.py` is BYTE-FOR-BYTE UNCHANGED (verify with `git diff scoring/score.py` showing zero changes).
- All four test files pass.

## Dependencies

- **Plan 01-01:** Makefile + uv (the test commands run via `uv run`).
- Can technically be developed BEFORE plan 01-04 because the retry gate operates over abstract callables. Sequencing in Wave 2 means it runs in parallel with 01-04.

## Notes / Pitfalls

- **Pitfall 1 (transient-failure tank):** This plan's primary defense.
- **Pitfall 2 (apples-to-oranges):** Partially addressed via N/A semantics. Capability matrix (FAIRNESS-04) is Phase 2.
- **SACROSANCT contract:** `scoring/score.py` is locked. Any extension lives in `score_with_na.py` or `aggregate_scores.py`. Verify with `git diff` before finalizing the commit.
- **CONTEXT.md decision honored:** "N/A vs 0 semantics — `scoring/score.py` is SACROSANCT — preserve 2026-03 comparability. If N/A handling needs a change, write a thin adapter in `scripts/aggregate_scores.py`." Implemented exactly — the adapter is `scripts/score_with_na.py` + `aggregate_scores.py` cooperating; no modifications to `score.py`.
- **CONTEXT.md decision honored:** "Failure-attribution taxonomy — Any sub-rubric score < 5 carries a tag: `tool-bug` / `env-mismatch` / `target-flag` / `transient`. Per-row, per-stage. Enforced at `scores.json` emit time." Implemented exactly in `aggregate_scores.py`.
- **Edge case — `score.py`'s `format_stage_matrix` does emit `N/A` already** (see line 67 of `score.py`: `results[a]["stages"].get(stage, "N/A")`). This plan extends N/A to the **scores dict** (numerical dimensions) too — that's the part `score.py` doesn't currently handle (line 29: `scores.get(dim, 0)` would treat N/A-string as 0 if it crept in; the wrapper's job is to override that).
- **CONTEXT.md decision honored:** "Retry gate + transient taxonomy — `bench/transient.py` implements 3-pass-of-3 with explicit transient classifier (WebSocket 1001/1006, ECONNRESET, MCP `initialize` timeout, HTTP 429/503, Chromium SIGKILL). Score the median of 3 attempts."

## Out of Scope

- The 30-min sleep between retry attempts mentioned in Pitfall 1 ("on a different wall-clock window ≥30 min gap"). In Phase 1 we use a configurable `sleep_between_s` defaulting to 30 SECONDS for development speed; the production runner in Phase 2 may dial this up to honor the literal pitfall recommendation. Note in `rubric_notes.md` so the choice is intentional.
- Capability-matrix tags (`tool-only`, `LLM-augmented`, `cloud`, `stealth-specialist`, `js-light`) — FAIRNESS-04 is Phase 2.
- Browser-use dual-mode scoring (`direct` + `agent`) — FAIRNESS-05 is Phase 2.
- Vendor courtesy-disclosure window — deferred to G-710.
