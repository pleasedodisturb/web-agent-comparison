"""_sandbox — shared sandbox-callout constants + injector.

Single source of truth for the two Phase 4 builders that need to insert a
"Sandbox only — do not point at authenticated sessions" callout near
every cloakbrowser mention in their generated artifacts. Previously each
builder defined its own SANDBOX_CALLOUT constant + its own
inject_sandbox_callouts implementation, with the two implementations
producing different output on the same input (WR-04 + IN-03).

This module consolidates both:

- `SANDBOX_CALLOUT` — the canonical callout string (with trailing period
  to match the CAPABILITY_MATRIX.md convention).
- `SANDBOX_RECOGNITION_RE` — case-insensitive regex matching any
  "sandbox-only" / "sandbox only" / "sandboxonly" variant. Idempotency
  rests on this recognising every callout form in the wild.
- `inject_sandbox_callouts(md)` — the build_report.py algorithm (it
  plants one callout per cloakbrowser cluster, not one per mention, and
  tracks planned insertions so adjacent mentions share a single callout).
  This is the less-noisy of the two original implementations.

Stdlib-only (re only).
"""

from __future__ import annotations

import re

# Canonical callout string. The trailing period matches the form used in
# the embedded CAPABILITY_MATRIX.md content; recognition is regex-based
# so a future caller that omits the period still works.
SANDBOX_CALLOUT: str = (
    "**Sandbox only — do not point at authenticated sessions.**"
)

# Recognition regex — case-insensitive, tolerant of hyphen/space/none
# between "sandbox" and "only".
SANDBOX_RECOGNITION_RE: re.Pattern[str] = re.compile(
    r"sandbox[\- ]?only", re.IGNORECASE
)


def inject_sandbox_callouts(md: str) -> str:
    """Ensure every cloakbrowser mention is within 5 lines of a sandbox callout.

    Idempotent: running twice yields the same output. Recognises existing
    callouts via the case-insensitive `sandbox[- ]?only` regex so embedded
    content (which already carries the callout, sometimes with a trailing
    period) does not trigger double-injection.

    Algorithm (lifted from the original build_report.py implementation):

    1. Find all lines containing "cloakbrowser" (case-insensitive).
    2. Find all lines that already carry a recognised callout.
    3. For each cloakbrowser mention, check if ANY callout (existing or
       previously-planned) is within ±5 lines. If yes, skip. If no, plan
       a callout for insertion immediately after this line, and add the
       planned position to the effective callout set so adjacent
       cloakbrowser mentions share the callout.
    4. Apply planned insertions in reverse order so positions stay valid.

    Per WR-04 + IN-03: this is the canonical implementation used by both
    `bench/build_report.py` and `bench/build_recommendations.py`.
    """
    if not md:
        return md
    lines = md.splitlines()
    cloak_idx = [
        i for i, ln in enumerate(lines) if "cloakbrowser" in ln.lower()
    ]
    if not cloak_idx:
        return md
    callout_idx_set = {
        i for i, ln in enumerate(lines) if SANDBOX_RECOGNITION_RE.search(ln)
    }
    insertions: list[int] = []  # positions AFTER which to insert
    effective_callout_set = set(callout_idx_set)
    for idx in cloak_idx:
        window_min = max(0, idx - 5)
        window_max = idx + 5
        has_nearby = any(
            window_min <= c <= window_max for c in effective_callout_set
        )
        if has_nearby:
            continue
        insertions.append(idx)
        effective_callout_set.add(idx + 1)
    if not insertions:
        return md
    for pos in sorted(insertions, reverse=True):
        lines.insert(pos + 1, SANDBOX_CALLOUT)
    return "\n".join(lines)
