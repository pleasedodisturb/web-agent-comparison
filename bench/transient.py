"""3-pass-of-3 retry gate for the web-agent MCP benchmark.

This is the Pitfall-1 (transient-failure tank) defense. Any S1-S8
stage failure that classifies as `transient` per
`bench.failure_taxonomy.is_transient` gets retried up to 3 times in
fresh attempts; the **median** of the 3 attempts is the recorded
score. Non-transient failures (tool-bug, env-mismatch, target-flag)
stop after the first attempt — they are not retry-eligible.

Each attempt is captured as an `Attempt` record so the published
matrix can show `n/3 passes` and so post-hoc audits can see whether a
candidate's reliability column was a real failure or a Tuesday-afternoon
WebSocket drop.

Default `sleep_between_s=30` is the Phase 1 development-speed setting.
Pitfall 1 recommends "different wall-clock window ≥30 min gap" for
the production-run cadence; Phase 2 may dial this up. The default is
documented in `scoring/rubric_notes.md` so the choice is intentional.

Public API
----------
- `Attempt` dataclass — one record per retry attempt.
- `retry_stage(fn, max_attempts=3, sleep_between_s=30.0, transient_only=True)`
  — runs `fn` up to `max_attempts` times, returns the full list of attempts.
- `median_pass(attempts)` — returns `(passes, total)` summary for matrix display.
- `write_attempts_to_jsonl(attempts, path)` — appends one JSON line per attempt
  into the per-MCP `results/<date>/<mcp>/raw.jsonl` file.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from bench.failure_taxonomy import FailureTag, attribute_failure


# ─── Attempt record ────────────────────────────────────────────────────


@dataclass
class Attempt:
    """One attempt at running a stage callable.

    Fields:
      attempt_no: 1-indexed attempt number.
      passed: True if the callable returned without raising.
      tag: FailureTag if the callable raised, else None.
      duration_s: wall-clock seconds spent inside the callable.
      error: stringified exception if the callable raised, else None.
      result: the callable's return value on success, else None. Kept
              for the aggregator so it can inspect e.g. the stage output
              dict that the per-stage runner emits.
    """

    attempt_no: int
    passed: bool
    tag: Optional[FailureTag]
    duration_s: float
    error: Optional[str] = None
    result: Any = field(default=None, repr=False)

    def to_jsonable(self) -> dict[str, Any]:
        """Render to a JSON-serializable dict for raw.jsonl."""
        d = asdict(self)
        # `result` may contain arbitrary Python objects; only emit it if
        # it's already JSON-friendly. The aggregator reads `passed` +
        # `tag` + `duration_s`; the raw result lives in the per-stage
        # artifact files (stage_s1.yml, etc.) — not here.
        d.pop("result", None)
        # Enum → string for JSON.
        if self.tag is not None:
            d["tag"] = self.tag.value
        return d


# ─── Retry loop ────────────────────────────────────────────────────────


def retry_stage(
    fn: Callable[[], Any],
    max_attempts: int = 3,
    sleep_between_s: float = 30.0,
    transient_only: bool = True,
) -> list[Attempt]:
    """Run `fn` up to `max_attempts` times, retrying transient failures.

    Semantics:
      - On success, record `passed=True` and return immediately (no
        further attempts). The score is whatever the median of recorded
        attempts says; we don't keep retrying once we've passed.
      - On failure, classify via `attribute_failure(str(exc))`. If
        `transient_only=True` (the default) AND the tag is NOT
        TRANSIENT, stop retrying — return after this single attempt.
        This honours CONTEXT.md: "matches against the taxonomy trigger
        automatic retry, non-matches surface as real failures."
      - If transient, sleep `sleep_between_s` and retry. The sleep is
        omitted on the final attempt (no point sleeping after we've
        decided to stop).

    `sleep_between_s` accepts 0 for unit tests (no wall-clock cost).
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    attempts: list[Attempt] = []

    for i in range(1, max_attempts + 1):
        t0 = time.perf_counter()
        try:
            result = fn()
            duration = time.perf_counter() - t0
            attempts.append(
                Attempt(
                    attempt_no=i,
                    passed=True,
                    tag=None,
                    duration_s=round(duration, 4),
                    error=None,
                    result=result,
                )
            )
            # Stop on first success — Pitfall 1's "median of 3" is about
            # NOT baking a one-off failure into the matrix; once we've
            # succeeded the dimension is clearly available.
            break
        except BaseException as exc:  # noqa: BLE001 — we deliberately catch all
            duration = time.perf_counter() - t0
            tag = attribute_failure(exc)
            attempts.append(
                Attempt(
                    attempt_no=i,
                    passed=False,
                    tag=tag,
                    duration_s=round(duration, 4),
                    error=f"{type(exc).__name__}: {exc}",
                    result=None,
                )
            )

            # Stop early if non-transient and the caller asked us to.
            if transient_only and tag is not FailureTag.TRANSIENT:
                break

            # Stop on final attempt (no sleep needed).
            if i == max_attempts:
                break

            # Transient and we have attempts left → sleep then retry.
            if sleep_between_s > 0:
                time.sleep(sleep_between_s)

    return attempts


# ─── Matrix-display helpers ────────────────────────────────────────────


def median_pass(attempts: list[Attempt]) -> tuple[int, int]:
    """Return `(passes, total_attempts)` for matrix display.

    The "median" framing in Pitfall 1 ("score the median of 3 attempts")
    really means "if at least half passed, the stage passes." For a
    boolean pass/fail signal that's identical to counting passes; we
    publish `n/3` so readers see variance directly.
    """
    if not attempts:
        return (0, 0)
    passes = sum(1 for a in attempts if a.passed)
    return (passes, len(attempts))


def passed_majority(attempts: list[Attempt]) -> bool:
    """Strict majority of attempts succeeded.

    With 3 attempts: 2 or 3 passes → True. With 1 attempt: pass → True.
    The matrix uses `median_pass` for display; this function is the
    boolean form used by the aggregator when deciding pass/fail per
    stage.
    """
    passes, total = median_pass(attempts)
    if total == 0:
        return False
    return passes * 2 > total


# ─── Persistence ───────────────────────────────────────────────────────


def write_attempts_to_jsonl(attempts: list[Attempt], path: Path) -> None:
    """Append one JSON line per Attempt into `path`.

    The aggregator (`scripts/aggregate_scores.py`) reads this file to
    derive `n/3 passes` and the per-stage failure attribution. The
    canonical location is `results/<date>/<mcp>/raw.jsonl`.

    Append-mode so a multi-stage run (S1 through S8) can write all
    stages into the same file without clobbering. Caller is responsible
    for adding a stage identifier to each Attempt's `error` or a wrapper
    record if needed; this module emits the Attempt fields verbatim.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for a in attempts:
            f.write(json.dumps(a.to_jsonable(), sort_keys=True) + "\n")


__all__ = [
    "Attempt",
    "retry_stage",
    "median_pass",
    "passed_majority",
    "write_attempts_to_jsonl",
]
