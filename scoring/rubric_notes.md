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
