---
phase: 04-synthesis
reviewed: 2026-05-28T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - bench/build_report.py
  - bench/build_recommendations.py
  - bench/wave_close_check.py
  - tests/test_build_report.py
  - tests/test_build_recommendations.py
  - tests/test_wave_close_check.py
findings:
  critical: 2
  warning: 7
  info: 6
  total: 15
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-05-28
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

The Phase 4 builders (`build_report.py`, `build_recommendations.py`, `wave_close_check.py`) and their tests all execute correctly — 68 tests pass cleanly, stdlib-only constraint is honored (only `argparse`, `json`, `re`, `subprocess`, `datetime`, `pathlib`, `sys`, `typing`), `scoring/score.py` and `scoring/rubric.md` are byte-identical to `main` per `git diff` (SACROSANCT honored), and no PII (`/Users/…`, `pleasedodisturb`, `whoami`, MAC, hardware UUID) leaks into the source.

That said, this review found two BLOCKER-tier defects that contradict the project's stated reproducibility guarantee, plus seven WARNING-tier defects that degrade correctness, robustness, or auditability of the published artifacts. The most serious finding (CR-01) is a self-contradiction in the public Linear traceability footer: `recommendations.md` and `2026-05-27-mcp-comparison.md` cite **different** MCP→ticket mappings for G-715/G-719/G-720, and the report file even contradicts itself internally. This ships in the artifact that is the Stage 2 unblock gate.

A secondary BLOCKER (CR-02) is that `~/.claude/docs/browser-tools.md` — a private path on the maintainer's machine — is hard-coded as evidence into both public Markdown artifacts (`results/recommendations.md` line 89 and `results/2026-05-27-mcp-comparison.md` lines 909, 975, 1542, 1661). The repo's CLAUDE.md explicitly states "Reproducibility: methodology must be runnable by a third party with only the public repo." A reader who clones the repo cannot follow those citations; the SAFETY-03 and stealth-leak claims are unverifiable.

## Critical Issues

### CR-01: Linear ticket→MCP mapping contradicts itself across published artifacts

**File:** `bench/build_report.py:879-880` and `bench/build_recommendations.py:553-559`
**Issue:**
The two builders hard-code DIFFERENT MCP→ticket mappings for the same G-715..G-720 ticket range, and both ship into the public artifacts.

- `build_report.py` footer says: `G-715 (chrome-devtools), G-716 (lightpanda), G-717 (firecrawl), G-718 (obscura), G-719 (browser-use direct + agent), G-720 (cloakbrowser)`
- `build_recommendations.py` footer says: `G-715 (browser-use), G-716 (lightpanda), G-717 (firecrawl), G-718 (obscura), G-719 (chrome-devtools), G-720 (SANDBOX-ONLY tier)`

These disagree on G-715 (chrome-devtools vs browser-use), G-719 (browser-use vs chrome-devtools), and G-720 (cloakbrowser specifically vs SANDBOX-ONLY tier generically). The report ALSO contradicts itself internally because the embedded per-MCP `DEEP_ANALYSIS.md` content carries its own ticket attributions: line 270 says "G-715 (browser-use sub-ticket of G-703)" while line 677 says "G-715 (chrome-devtools sub-ticket of G-703)". REPORT-12 explicitly requires Linear traceability; today the traceability footer points readers at the wrong tickets.

No `LINEAR_SUBTICKETS.md` file exists in the repo to disambiguate, and 04-CONTEXT.md just says "cite G-703 + per-MCP sub-tickets" without specifying the mapping.

**Fix:**
1. Decide the canonical mapping by querying Linear: `linearis list G --grep="per-MCP"` and pin to actual ticket subjects, OR
2. Stop citing specific G-71x ticket IDs entirely until they exist — replace with a single placeholder block (e.g., `G-703 sub-tickets — see LINEAR_SUBTICKETS.md when filed`).
3. Pull the mapping into a single source of truth (a constant in one module, imported by the other) so the two files cannot drift.

```python
# bench/_linear_subtickets.py
SUBTICKETS: dict[str, str] = {
    # MUST be backfilled from Linear — placeholder pending OUTREACH-03 sweep
    "chrome-devtools": "G-715",
    "lightpanda":      "G-716",
    "firecrawl":       "G-717",
    "obscura":         "G-718",
    "browser-use":     "G-719",
    "cloakbrowser":    "G-720",
}
```

Then both `build_report.render_linear_traceability_footer` and `build_recommendations` import from this module. Until the mapping is verified against Linear, prefer option (2) — omit the specific IDs rather than ship a wrong attribution.

### CR-02: Private `~/.claude/docs/browser-tools.md` cited as evidence in public report

**File:** `bench/build_report.py:773`, `bench/build_recommendations.py:172`
**Issue:**
Both builders embed citations to `~/.claude/docs/browser-tools.md` — a private file on the maintainer's machine that is NOT part of the public repo. The strings land verbatim in the published artifacts:

- `results/recommendations.md:89`: `SAFETY-03 macOS stealth leak — \`~/.claude/docs/browser-tools.md\` (2026-05-21)`
- `results/2026-05-27-mcp-comparison.md:909, 975, 1542, 1661`: similar references

CLAUDE.md is explicit: "Reproducibility: methodology must be runnable by a third party with only the public repo. No internal-only fixtures, no rbw-gated secrets in the core flow." A third-party reader cannot verify the SAFETY-03 macOS stealth-leak claim, the Sec-CH-UA-Platform-* finding, or the cookie-touch observation — each is "trust me, see this private doc."

This also reveals the maintainer's local FS structure (`~/.claude/docs/…`), which is a soft form of PII (signals a specific Claude Code setup, narrows fingerprinting surface).

**Fix:**
Move the evidence into the repo: create a `docs/external-findings/browser-tools-2026-05-21.md` that summarizes the relevant SAFETY-03 paragraphs verbatim (with attribution), commit it to the public repo, and re-point every `~/.claude/docs/browser-tools.md` citation to `docs/external-findings/browser-tools-2026-05-21.md`. The builders should reference the in-repo copy.

```python
# bench/build_report.py — replace
"(per `~/.claude/docs/browser-tools.md` 2026-05-21 verification). "
# with
"(per [`docs/external-findings/browser-tools-2026-05-21.md`](../docs/external-findings/browser-tools-2026-05-21.md) § SAFETY-03). "
```

Apply the same change in `bench/build_recommendations.py` and regenerate both artifacts.

## Warnings

### WR-01: `render_audit_md` raises `KeyError` on minimal audit dicts despite docstring inviting partial input

**File:** `bench/wave_close_check.py:287-322`
**Issue:**
The function's defensive code at lines 297-309 explicitly derives `*_pass` flags when absent ("Allow callers (especially tests) to pass minimal audit dicts that contain only the headline value fields"), but it then unconditionally dereferences `audit["actual_keys"]` and `audit["baseline_keys"]` at lines 317-321 and `audit["all_pass"]` at line 311. A minimal dict without these keys crashes:

```python
>>> render_audit_md({"candidate_count": 7, "rubric_columns": 8, "terminal_craft_commits": 0, "no_new_mcps": True, "all_pass": True}, "now")
KeyError: 'actual_keys'
```

The docstring and the partial-`_pass` derivation imply minimal dicts should work; the actual behavior contradicts that contract. Tests pass only because `TestRenderAuditMd._good_audit()` includes `baseline_keys` + `actual_keys`.

**Fix:**
Apply the same `.get(..., default)` pattern used for `*_pass` flags:

```python
actual_keys = audit.get("actual_keys", sorted(WAVE2_BASELINE))
baseline_keys = audit.get("baseline_keys", sorted(WAVE2_BASELINE))
all_pass = audit.get("all_pass", all([
    candidate_count_pass, rubric_columns_pass,
    terminal_craft_commits_pass, no_new_mcps_pass,
]))
```

### WR-02: `audit_terminal_craft_commits` silently passes when `git` fails

**File:** `bench/wave_close_check.py:161-198`
**Issue:**
Both subprocess invocations (`result_a`, `result_b`) use `check=False` and the code only processes output when `returncode == 0`. A non-zero return code — git not installed, repo corrupt, cwd not a git repo, OOM — causes the function to return `0` commits, which the auditor interprets as PASS for SAFETY-05.

This is a silent-failure vector on a security-adjacent gate: a future user running the audit outside a git repo would get a green PASS even though the audit was unable to inspect anything. The SAFETY-05 ritual is supposed to prove "no Stage 2 leak"; today it proves "no Stage 2 leak OR git is broken."

**Fix:**
Distinguish "ran successfully, found 0 leaks" from "could not run". Either raise:

```python
if result_a.returncode != 0:
    raise RuntimeError(
        f"git log failed (rc={result_a.returncode}): {result_a.stderr}"
    )
```

…or return a sentinel (`-1` or `None`) and have `run_audit` mark the check as FAIL with a reason field. The current swallowed failure is the worst of both worlds.

### WR-03: `render_negative_results` accepts `scores` and `cross_cut` parameters but uses neither

**File:** `bench/build_report.py:741-819`
**Issue:**
The signature is `render_negative_results(scores: dict, cross_cut: dict) -> str`, but the entire body is a static, hand-written list of 5 bullets. Neither parameter is referenced. This is misleading dead code:

1. Future maintainers will assume the negative results are data-driven and will be surprised when changing `scores.json` does not change the output.
2. If a SKIPPED MCP changes (e.g., firecrawl becomes SCORED and obscura becomes SKIPPED in some future wave), the hard-coded bullets will silently lie.
3. The function violates its own naming convention — every other `render_*` function reads from its parameters.

**Fix:**
Either (a) drop the parameters and rename to `render_negative_results_text()` to signal it's a static block, or (b) actually derive bullets from `scores` + `cross_cut`. Option (b) is the design intent per the planner — at minimum, derive the firecrawl + browser-use-agent bullets from `scores[mcp].get("status")` and `attribution` fields:

```python
def render_negative_results(scores: dict, cross_cut: dict) -> str:
    parts = ["## Negative Results", ""]
    # SKIPPED-row bullets are data-driven
    for mcp, row in scores.items():
        if row.get("status") == "SKIPPED":
            parts.append(f"- **`{mcp}` SKIPPED** — reason `{row.get('skip_reason')}`; "
                         f"see `{row.get('skip_evidence')}`.")
    # env-mismatch attribution is also data-driven
    for mcp, row in scores.items():
        env_dims = [d for d, tag in row.get("attribution", {}).items() if tag == "env-mismatch"]
        if env_dims:
            parts.append(f"- **`{mcp}` env-mismatch** on {env_dims}.")
    # ...etc
```

### WR-04: `inject_sandbox_callouts` divergence between the two builders

**File:** `bench/build_report.py:241-285` vs `bench/build_recommendations.py:474-498`
**Issue:**
The two implementations have different idempotency strategies and produce different outputs on identical input. For `"cloakbrowser one\ncloakbrowser two\ncloakbrowser three\n"`:

- `build_report.inject_sandbox_callouts` plants ONE callout (after the first cloakbrowser) and considers all three within window of that callout.
- `build_recommendations.inject_sandbox_callouts` plants THREE callouts (one after each cloakbrowser line) because its window-check uses the original `lines` array and does not track planned insertions.

Both are idempotent on the second pass. Both satisfy "every cloakbrowser is within 5 lines of a callout." But they produce different concrete artifacts, which means a maintainer who reads one cannot predict the other. The plan (04-04 Task 1) even invites this: "May be lifted from `bench/build_report.py` if implemented there first." It wasn't lifted; two near-duplicate implementations now exist.

**Fix:**
Move `inject_sandbox_callouts` to a single shared module (e.g., `bench/_sandbox.py`) and import from both. Pick the `build_report.py` algorithm — it produces less noise and is more carefully written.

```python
# bench/_sandbox.py
from .build_report import inject_sandbox_callouts, SANDBOX_CALLOUT_CANONICAL  # or move both here
```

### WR-05: `build_report.py` and `build_recommendations.py` do not create parent directories before writing output

**File:** `bench/build_report.py:971`, `bench/build_recommendations.py:572`
**Issue:**
Both call `out_path.write_text(...)` directly without `out_path.parent.mkdir(parents=True, exist_ok=True)`. If the user invokes the CLI with `--out results/2026-05-27/new-dir/file.md` and `new-dir/` does not exist, the call raises `FileNotFoundError`. Compare with `wave_close_check.py:443`, which correctly calls `args.out.parent.mkdir(parents=True, exist_ok=True)` first.

This is inconsistent UX across three sibling builders.

**Fix:**
Add the mkdir before each write_text call:

```python
# bench/build_report.py:970
if out_path is not None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final, encoding="utf-8")
```

Same pattern in `build_recommendations.py:572`.

### WR-06: `audit_rubric_columns` brittle to the section heading literal "Dimensions"

**File:** `bench/wave_close_check.py:103-132`
**Issue:**
The function counts rubric dimensions only when they appear under a heading matching `## dimensions` (case-insensitive). The actual rubric heading is `## Dimensions (8 total, weighted)` and matches because `.lower().startswith("## dimensions")` is permissive enough. But a future rubric edit that renames the section (e.g., "## Weighted Dimensions" or "## Scoring Dimensions") will silently return 0 and the audit will FAIL even though the rubric is intact.

The comment claims this is "belt and suspenders against a future rubric.md that grows a second `**bold**`-rowed table elsewhere," which is reasonable. But the audit is also load-bearing for SAFETY-05; a false FAIL is almost as bad as a false PASS because it disrupts wave-close flow and trains operators to ignore the check.

**Fix:**
Either (a) loosen the heading-matching to allow "Dimensions" anywhere in the H2 (`"dimensions" in stripped.lower()`), or (b) drop the section-gating entirely and accept that any `**bolded**` row at the start of a table line counts — the locked-rubric constraint via `git diff scoring/rubric.md` is the real defense.

### WR-07: `render_methodology_disclaimer` accepts None/empty dict without warning, emits empty bolded date

**File:** `bench/build_report.py:364-386`
**Issue:**
Called with `None` or `{}`, the function emits "evaluated on ****" (empty bold). The CLI requires `--run-date` so this won't fire from the CLI, but the function is also called from tests and could be called programmatically.

No validation; no warning; the artifact ends up with a visibly broken header. Since this is a methodology disclaimer it should fail loudly rather than render a malformed date.

**Fix:**
Add a guard:

```python
if not date_str:
    raise ValueError("render_methodology_disclaimer requires a non-empty run_date")
```

Or default to `datetime.date.today().isoformat()` with a stderr warning that the date was auto-supplied.

## Info

### IN-01: `build_report._safe_load_json` silently swallows JSON parse errors

**File:** `bench/build_report.py:122-129`
**Issue:**
On `JSONDecodeError`, returns `None` and the caller silently produces a report with no MCP rows. There is no warning to stderr, no exit nonzero from the CLI. Verified: `build_report` with malformed `scores.json` produces a 19,504-character "report" containing zero MCP data.

This is a silent-failure smell — `_safe_load_json` is too eager to be silent.

**Fix:** Log a warning to stderr when JSON parsing fails: `print(f"WARN: failed to parse {path}: {exc}", file=sys.stderr)`. The CLI can then exit nonzero if `scores` is empty after the load.

### IN-02: Hardcoded composite map in `bench/build_recommendations.py:212-221` ignores its own input

**File:** `bench/build_recommendations.py:205-222`
**Issue:**
`_composite_for(mcp, scores)` has a `scores` parameter but completely ignores it — the function returns from a hard-coded `HARDCODED_COMPOSITES` dict instead. If `scores.json` ever updates (different wave, re-scoring, etc.), the recommendations file will quietly cite stale composites.

This is the same anti-pattern as WR-03 — a "data builder" that has hard-coded its outputs.

**Fix:** Compute composites from `scores[mcp]["scores"]` using the same N/A-aware formula as `build_report._composite_for_row`. Keep `HARDCODED_COMPOSITES` only as a fallback (or remove entirely).

### IN-03: Duplicate `SANDBOX_CALLOUT` string constants across the two builders

**File:** `bench/build_report.py:99-101`, `bench/build_recommendations.py:184-186`
**Issue:**
`build_report.py` defines: `**Sandbox only — do not point at authenticated sessions**` (no trailing period)
`build_recommendations.py` defines: `**Sandbox only — do not point at authenticated sessions.**` (trailing period)

Both files claim the constant is "canonical." Two different "canonical" strings in two files is the textbook duplicate-source-of-truth bug. The recognition regex catches both, so output looks fine, but a future code-grep for the exact phrase will miss one or the other depending on which period is used.

**Fix:** Consolidate into a single shared constant in `bench/_sandbox.py` (see WR-04). Pick one form (with or without trailing period) and apply it everywhere.

### IN-04: `render_score_table` writes the same composite into two distinct call-sites

**File:** `bench/build_report.py:493-498`
**Issue:**
Lines 493-498 compute `comp = _composite_for_row(row, rubric_weights)` and emit `cells.append(f"**{comp:.2f}**" if comp is not None else "—")`. But the executive summary (line 321) also computes the same composite per row via the same function. There is no caching — `_composite_for_row` runs at least twice per row for the report.

Not a correctness bug (the function is pure), but it's the kind of duplication that bites when someone changes the weights and forgets one call site.

**Fix:** Compute composites once in `build_report` (top of orchestrator), store in a dict `{mcp: composite}`, pass to the render functions. Avoids redundant computation and creates a single audit point for "what composite did this report cite."

### IN-05: `SCORE_TABLE_ORDER` and `SEVEN_MCPS` are two parallel constants with overlapping semantics

**File:** `bench/build_report.py:73-95`
**Issue:**
`SCORE_TABLE_ORDER` (8 names) and `SEVEN_MCPS` (7 names) carry overlapping but distinct content. They will silently drift if a future MCP is added — adding to one and forgetting the other is a frequent class of bug in this kind of duplicated-list pattern.

**Fix:** Derive `SCORE_TABLE_ORDER` from `SEVEN_MCPS` programmatically:

```python
SEVEN_MCPS = ("playwright", "browser-use", "chrome-devtools", ...)
# browser-use expands to two rows; everything else is itself
SCORE_TABLE_ORDER = tuple(
    "browser-use-direct" if m == "browser-use" else m
    for m in SEVEN_MCPS
) + ("browser-use-agent",)
```

### IN-06: `test_secondary_section_exact_membership` substring-check is unsound for "playwright" containing "play" etc.

**File:** `tests/test_build_recommendations.py:234-245`
**Issue:**
The test does `assert other not in sec_text` for each off-tier MCP. This works for the current set because no MCP name is a substring of another except `browser-use` ⊂ `browser-use-direct` ⊂ `browser-use-agent`. The test handles this with the comment "Be careful: 'browser-use-direct' substring contains nothing else" but does not actually enforce the boundary. If a future MCP is named e.g. `playwright-stealth`, the check `"playwright" not in sec_text` would falsely trip.

**Fix:** Use word-boundary regex `r"\b{mcp}\b"` instead of `in`, so adjacent characters are checked.

```python
import re
for other in (...):
    pattern = rf"(?<![\w-]){re.escape(other)}(?![\w-])"
    assert not re.search(pattern, sec_text), f"{other} found in section"
```

---

## Cross-cutting Confirmations (informational, not findings)

- **stdlib-only:** Verified — all imports are `argparse`, `json`, `re`, `subprocess`, `datetime`, `pathlib`, `sys`, `typing`, `tempfile`, `unittest`, `unittest.mock`, `pytest`. (The two test modules use `pytest` and `unittest`; both are pre-installed in the project's venv per CLAUDE.md, but pytest is technically third-party. Not flagged because tests are not in the deployed module surface.)
- **`scoring/score.py` + `scoring/rubric.md` SACROSANCT:** `git diff main..HEAD -- scoring/score.py scoring/rubric.md` is empty. None of the three builder modules import from or call into `scoring.score`. Two doc-only references in builders (`build_report.py:837`, `build_recommendations.py:464-465`) merely cite the file by path.
- **Idempotency claim of `inject_sandbox_callouts`:** Empirically holds for both implementations across the cases I tested (adjacent cloakbrowser mentions, boundary-window cases, embedded callouts with trailing-period variant). The two implementations differ in how many callouts they emit (see WR-04) but both reach a fixed point on the second pass.
- **PII regex:** No matches for `/Users/<username>/`, `pleasedodisturb`, MAC, or hardware UUID in the source or in the generated artifacts. The only path that leaks user-local state is `~/.claude/docs/browser-tools.md` (see CR-02).
- **Test execution:** `python3 -m pytest tests/test_build_report.py tests/test_build_recommendations.py tests/test_wave_close_check.py -q` reports `68 passed in 0.10s`.

---

_Reviewed: 2026-05-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
