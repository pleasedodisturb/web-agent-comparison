# Rubric Notes — Phase 1 Fairness Supplements

**Phase:** 1 (Harness Foundation), Plan 01-05
**Status:** Active
**Relationship to `rubric.md`:** This file LAYERS ON TOP of `scoring/rubric.md`.
The 8 dimensions, weights, and 0/5/10 anchors in `rubric.md` are LOCKED — this
document only adds the operational supplements that the Phase 1 harness needs.
`scoring/score.py` is also LOCKED — its 2026-03 comparability contract is
preserved by routing the supplements through `scripts/score_with_na.py` and
`scripts/aggregate_scores.py` rather than modifying `score.py`.

---

## N/A vs 0 semantics

Read-only MCPs (`lightpanda`, `firecrawl`) score **`N/A`** — not `0` — on the
interactive stages (S4-S8) and on the `interaction_depth` dimension. The
weighted composite is computed by `scripts/score_with_na.py`, which **drops
N/A cells from the denominator** rather than treating them as zero.

**Why this matters.** `score.py`'s `compute_composite` uses `scores.get(dim, 0) *
weight`, which silently treats missing or unknown values as zero. Counting an
N/A as zero penalises a candidate for not having a capability it never claimed
to have — apples-to-oranges (Pitfall 2). The wrapper restores fairness by
dropping the cell entirely.

**Math example.** All 8 dimensions at 5, except `interaction_depth = "N/A"`
(weight 2):
- **`score.py` (zero-fill behaviour, with N/A stripped)**: `(5 × 13) / 15 = 4.33`
- **`score_with_na.py` (N/A-drop behaviour)**: `(5 × 13) / 13 = 5.00`

The 0.67-point spread is exactly the bias the wrapper exists to correct.

**When does this fire?** Only when a row carries a literal `"N/A"` string (or
`None`). Phase 1's calibration target (Playwright) has no N/A cells, so
`score.py` and `score_with_na.py` produce **identical** composites for it —
the wrapper is dormant. The N/A logic activates in Phase 2 when lightpanda and
firecrawl land.

**Sentinels recognised**: `"N/A"`, `"NA"`, `"n/a"`, `"n_a"`, `None`. Anything
else is treated as numeric.

---

## 3-pass-of-3 retry gate

Any S1-S8 stage failure that classifies as `transient` per
`bench.failure_taxonomy.is_transient` is retried up to **3 attempts** in
fresh sessions, with a `sleep_between_s` gap between them. The **median** of
the 3 attempts is the recorded result; the matrix shows `n/3 passes` per cell
so readers see the variance, not just the final score.

**Transient classification set** (locked):
- WebSocket close codes 1001 / 1006
- `ECONNRESET` / `connection reset by peer`
- MCP `initialize` timeout
- HTTP 429 / 503 from the target
- Chromium `SIGKILL` / `SIGTERM`
- npm-registry hiccups (`ENETUNREACH`, `ETIMEDOUT`)
- macOS App Nap stalls
- `EAGAIN` / resource temporarily unavailable

Non-transient failures (tool-bug, env-mismatch, target-flag — see
"Failure attribution" below) stop after the first attempt. They are real
reliability signals, not retry-eligible noise.

**`sleep_between_s` default = 30 seconds.** Pitfall 1 (transient-failure tank)
recommends "≥30 min" between retry attempts to clear out wall-clock-correlated
failure modes (target-site rate-limit windows, OS-power-management cycles).
Phase 1 uses 30 **seconds** for development speed; Phase 2's production runner
may dial this up to honour the literal pitfall recommendation. The choice is
intentional — documented here so it can be revisited without rediscovering
the rationale.

**Where the records live.** Each attempt is one JSON line in
`results/<date>/<mcp>/raw.jsonl`, written by
`bench.transient.write_attempts_to_jsonl`. `scripts/aggregate_scores.py`
reads this file and folds `passes/total/tag` into the stages dict so the
published matrix renders `PASS (2/3 transient)`-style cells.

---

## Failure attribution

Any sub-rubric score `< 5` in `scores.json` carries an `attribution` tag
explaining WHY it scored low. Four tags, priority order:

| Tag | Meaning | Example |
|-----|---------|---------|
| `transient` | Matches `bench.failure_taxonomy.is_transient` (retry-eligible). Highest priority. | `ECONNRESET while reading response` |
| `target-flag` | The target site refused us. | `HTTP 404 from greenhouse.io` |
| `env-mismatch` | Wrong binary arch, missing dep, command not found. | `zsh: command not found: obscura-mcp` |
| `tool-bug` | Default — "the MCP did something we didn't expect". | `AttributeError: 'NoneType' has no attribute 'page'` |

**Default is `tool-bug` by design.** An unclassified failure should point the
finger at the MCP under test, not the environment or the target. The
benchmark's job is to surface MCP-quality differences; if we cannot prove
otherwise, the MCP wears the failure.

**Where the tags live.** Per-MCP, per-dimension in `scores.json` under an
`attribution` map:
```json
{
  "lightpanda": {
    "scores": { "js_rendering": 2, ... },
    "attribution": { "js_rendering": "tool-bug" }
  }
}
```

Only sub-scores `< 5` get tagged — passing dimensions don't need a
"why did it pass" justification.

---

## What this file does NOT change

- The 8 dimensions in `rubric.md`. Locked.
- The weights (3/3/2/2/2/1/1/1, total 15). Locked.
- The 0/5/10 anchor language per dimension. Locked.
- `scoring/score.py` math. Sacrosanct — the 2026-03 wave's composite for
  Playwright (9.07) must reproduce byte-for-byte through `score.py` on the
  same scores dict.

If a future wave needs a real change to any of the above, that's a versioned
rubric bump, not a notes-addendum tweak. Cf. `.planning/research/PITFALLS.md`
Pitfall 1 (transient tank) and Pitfall 2 (apples-to-oranges).

---

## Calibration Re-Baseline (2026-05-26)

**Status:** Active. User-approved Option C from the 2026-05-25 calibration
diagnostic (see `results/2026-05-25/CALIBRATION_DIAGNOSTIC.md`).

### Why we re-baselined

The Phase 1 calibration gate (`scripts/verify_calibration.sh`) initially
targeted the 2026-03 published Playwright composite of **9.07** ±0.5 (accept
band [8.57, 9.57]). The 2026-05-25 actual run scored **7.93**, outside the
band — and the diagnostic proved the entire 1.14-point gap was *structural*,
not a regression:

- **4 of 8 dimensions** are scored by heuristic scorers in
  `scripts/aggregate_scores.py` whose real measurement is deferred to
  Phase 3 (G-710). These return neutral mid-band defaults:
  - `_score_speed` → 5 when `cold_start.json` is a `{"deferred": ...}` stub
  - `_score_token_efficiency` → 5 when `tokens.json.payload_bytes` is null
  - `_score_setup_complexity` → hardcoded 7 (versions.json-based scoring is a TODO)
  - `_score_error_handling` → regex density heuristic on `transcript.md`
- The 2026-03 published row was scored by **human judgment**: Speed=9,
  Token Efficiency=7, Setup Complexity=9, Error Handling=8.
- The heuristics CANNOT reproduce a human judge's number; the gap is by
  design.

Three options were laid out in the diagnostic:
- **A — Accept FAIL with caveat.** Violates HANDOFF STOP #1.
- **B — Reverse the scope cut.** Pulls in 4-8 hours of Phase 3 work into Phase 1.
- **C — Re-baseline.** Re-score the 2026-03 evidence through the SAME
  heuristics; compare apples-to-apples.

The user chose **Option C** on 2026-05-26.

### How we re-baselined

1. Copied the 4 on-disk 2026-03 Playwright evidence files
   (`playwright_s{1,2,4}_*.yml`, `playwright_s8_form_filled.png`) into
   `results/2026-03-31_rebaseline/playwright/` under the new
   `stage_s<N>.<ext>` naming.
2. Created lightweight reconstruction markdowns for S3, S5, S6, S7 — these
   stages PASSED in the 2026-03 publication but had no on-disk artifacts;
   the markdowns satisfy the aggregator's "any `stage_s<N>.*` file =
   PASS" contract while documenting their reconstructive nature.
3. Emitted the Phase-1 deferred-marker stubs (`cold_start.json`, `tls.json`,
   `stability.log`, `tokens.json`) via `bench/stub_writers.py`. The same
   stubs that ship in 2026-05 evidence directories — apples-to-apples
   deferred-scorer treatment.
4. Wrote a `transcript.md` reconstructed verbatim from the 2026-03
   publication's Playwright narrative (`results/2026-03-31_run.md` lines
   78-94), so the `_score_error_handling` heuristic sees the same words
   the original wave would have seen.
5. Wrote a clean `orphan_audit.log` (`ORPHANS=0`) because the 2026-03
   wave predates the orphan-audit machinery — it would be unfair to dock
   the row for a measurement that didn't exist.
6. Ran `scripts/aggregate_scores.py` → `scripts/score_with_na.py`.

The verdict: re-baseline composite = **8.33**. New accept band: **[7.83, 8.83]**
(±0.5 preserved as the harness-noise tolerance). The 2026-05-25 actual 7.93
falls inside this band → PASS, delta -0.40.

### What the new band documents

The published 2026-03 wave-1 number (**9.07**) is **unchanged**. It remains:

- The historical record in `results/scores.json` and `results/2026-03-31_run.md`.
- The methodology's wave-to-wave anchor when comparing humans-vs-humans across waves.
- The SACROSANCT contract that `scoring/score.py` reproduces — see
  `tests/test_calibration_math.py::TestCompositeReproducesFromPublishedResults`.

The new re-baseline number (**8.33**) is:

- The harness self-validation target.
- What `aggregate_scores.py` + `score_with_na.py` produce on the same 2026-03
  evidence under the Phase-1 heuristic-with-deferred-scorers configuration.
- The right number to gate the harness against, because it accounts for the
  documented Phase-1-vs-Phase-3 scope cut without confusing it with a real
  Playwright regression or fixture drift.

When G-710 (Phase 3) wires the real Speed / Token Efficiency / Setup Complexity
/ Error Handling scorers, the re-baseline can be re-computed and converge back
toward 9.07. At that point this section can be replaced with a "Calibration
Re-Convergence (Phase 3)" subsection documenting the new band.

### Regenerable artifact

The re-baseline is reproducible from the public repo:

```bash
# Re-emit the rebaseline directory (no-op if already present).
mkdir -p results/2026-03-31_rebaseline/playwright
cp results/playwright_s1_greenhouse.yml     results/2026-03-31_rebaseline/playwright/stage_s1.yml
cp results/playwright_s2_ashby.yml          results/2026-03-31_rebaseline/playwright/stage_s2.yml
cp results/playwright_s4_form.yml           results/2026-03-31_rebaseline/playwright/stage_s4.yml
cp results/playwright_s8_form_filled.png    results/2026-03-31_rebaseline/playwright/stage_s8.png
# (S3/S5/S6/S7 reconstruction markdowns + transcript.md are checked in.)
.venv/bin/python -m bench.stub_writers results/2026-03-31_rebaseline/playwright \
    --mcp-name playwright

# Score it.
.venv/bin/python scripts/aggregate_scores.py results/2026-03-31_rebaseline
.venv/bin/python scripts/score_with_na.py    results/2026-03-31_rebaseline/scores.json
# Expected: Weighted Composite (N/A-aware) = 8.33
```

The `results/2026-03-31_rebaseline/` directory is checked in; the checked-in
`scores.json` is the canonical re-baseline value. If anyone re-runs the above
and gets a different number, the divergence is the bug to investigate — the
re-baseline target is the contract.
