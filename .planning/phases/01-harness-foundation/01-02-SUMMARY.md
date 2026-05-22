---
phase: 1
plan: 02
subsystem: safety-gates
tags: [safety, secrets, pii, cloakbrowser, linear, break-before-cycle]
provides:
  - regex-secret-blocking-pre-commit-hook
  - pii-scrub-script-with-ocr
  - cloakbrowser-loopback-only-guard
  - g-703-sub-ticket-split
requires:
  - python-3.12-uv-lock-from-01-01
affects:
  - .git/hooks/pre-commit
  - bench/
  - tests/
  - docs/
  - pyproject.toml / uv.lock
tech-stack:
  added:
    - pytesseract>=0.3.10 (OCR backend; runtime falls back to text-only if tesseract binary missing)
    - Pillow>=10.0 (pytesseract dependency)
    - pytest>=8 (dev-deps; tests use stdlib unittest by default for portability)
  patterns:
    - bash 3.2-portable pre-commit hook (no mapfile, while-read + here-string)
    - in-repo hook source at scripts/hooks/ symlinked from .git/hooks/ (idempotent installer)
    - unittest-via-subprocess for CLI exit-code contracts
key-files:
  created:
    - .git/hooks/pre-commit (symlink → scripts/hooks/pre-commit)
    - scripts/hooks/pre-commit
    - scripts/install_hooks.sh
    - bench/__init__.py
    - bench/scrub_artifacts.py
    - bench/cloakbrowser_guard.py
    - tests/__init__.py
    - tests/test_secret_guard.sh
    - tests/test_scrub_artifacts.py
    - tests/test_cloakbrowser_guard.py
    - docs/LINEAR_SUBTICKETS.md
  modified:
    - pyproject.toml (added pytesseract, Pillow, pytest)
    - uv.lock (regenerated)
decisions:
  - shell over Python for the pre-commit hook (per CONTEXT.md "Claude's discretion — shell-heavy repo")
  - bash 3.2-portable (no mapfile/readarray; matches macOS system bash)
  - in-repo hook source at scripts/hooks/, symlinked from .git/hooks/, so edits propagate without reinstall
  - default scrub allow-list is just {"Jane Testworth"}; legitimate non-PII names extended via --allow file rather than relaxing the regex
  - cloakbrowser allow-list is exact-match loopback only (127.0.0.1, localhost, ::1, [::1]); DNS-rebinding lookalikes (localhost.example.com) and RFC1918 LAN addresses explicitly rejected
metrics:
  duration: 16m
  completed: 2026-05-22T15:30:26Z
  tasks_completed: 7
  files_created: 11
  files_modified: 2
  commits: 4
  tests_passing: 15 (Python unittest) + 1 shell test (2 cases)
requirements:
  - SAFETY-01
  - SAFETY-02
  - SAFETY-04
  - OUTREACH-03
---

# Phase 1 Plan 02: Secret Guard + Linear Split Summary

Three "do-no-harm" gates landed before any MCP-driving code: pre-commit hook blocks
inline secrets in `.mcp.json` (SAFETY-01), `bench/scrub_artifacts.py` flags any
non-Jane-Testworth two-word name in evidence directories (SAFETY-02),
`bench/cloakbrowser_guard.py` refuses cloakbrowser spawn against anything other than
loopback (SAFETY-04). Plus the Linear sub-ticket split: G-703 → 8 children
(G-714..G-721) filed via `linearis`, which is the break-before-cycle gate for Phase 2
(OUTREACH-03).

## What Was Built

### 1. Pre-commit hook for inline-secret blocking (SAFETY-01)

`scripts/hooks/pre-commit` — bash 3.2-portable script, source-of-truth for the
hook. `.git/hooks/pre-commit` is an idempotent symlink to it (set up via
`scripts/install_hooks.sh`). The hook runs on every commit, scans staged
`*.mcp.json` files, strips `${VAR}` env references, then OR's two regexes:

- Key-value: `(api[_-]?key|token|secret).*"[A-Za-z0-9_-]{20,}"`
- Prefix: `(fc-|sk-|Bearer )[A-Za-z0-9_-]{20,}`

A match prints `Inline secret detected in <path> — use ${ENV_VAR} reference
instead.` plus the matched line numbers, then exits 1. No `--no-verify` bypass
is used in any tooling; the global CLAUDE.md forbids it explicitly.

**Why bash, not Python:** CONTEXT.md "Claude's discretion" entry says this repo
is shell-heavy → keep the hook in shell. Honored.

**Why bash 3.2-portable:** macOS system bash is 3.2; `mapfile`/`readarray` don't
exist there. The hook uses `while IFS= read -r path; do … done <<EOF` instead,
so it works on any `/usr/bin/env bash`.

### 2. `bench/scrub_artifacts.py` PII scanner (SAFETY-02)

CLI: `python -m bench.scrub_artifacts <dir> [--allow <file>]`. Walks a directory,
scans text files (`.md .txt .yml .yaml .jsonl .json .log .csv .html .htm .xml`)
by direct read and image files (`.png .jpg .jpeg .gif .webp`) via `pytesseract`
OCR. Two-word capitalized name regex (`[A-Z][a-z]+ [A-Z][a-z]+`, optionally
hyphenated last name) gated by an allow-list whose default is just
`{"Jane Testworth"}`.

Exit 0 if clean; exit 1 with `FLAG: <file>:<line>: <match>` lines on stderr for
every unauthorized name.

**OCR graceful degradation:** If `pytesseract` is missing or the `tesseract`
system binary is absent, image files emit `OCR_SKIPPED: <path>` to stderr and
the text-only scan continues. Mac Mini has `tesseract 5.5.2` (Homebrew); OCR is
active. The graceful-degradation path lets the script run on any host without
breaking.

**Allow-list extension:** `--allow <file>` reads one name per line (with
`#` comments). Use this for legitimate vendor/section names that appear in
PROVENANCE.md and run reports. Tested in `test_extends_allow_list_via_flag`.

### 3. `bench/cloakbrowser_guard.py` loopback-only gate (SAFETY-04)

`assert_local_only(url)` parses a URL and raises `HostnameNotAllowedError`
unless the hostname is in `ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1",
"[::1]"}`. The closed-source `cloakbrowser` binary touches cookies on launch
(per global browser-tools policy + project CONSTRAINTS), so the harness must
refuse any spawn targeting a non-loopback host. Plan 01-04's
`scripts/run_mcp_session.sh` will import and call `assert_local_only` when
`MCP == cloakbrowser`.

**Conservative allow-list:** explicit exact-match. Tests cover the
DNS-rebinding lookalike `localhost.example.com` (must reject) and RFC1918 LAN
addresses like `192.168.1.10` and `10.0.0.5` (must reject — they're not
loopback, even though they're "local"). Empty, None, `file://`, and
relative-path inputs all reject.

### 4. Linear sub-ticket split for G-703 (OUTREACH-03)

Via `linearis issues create --team G --project "Mac Setup & Environment"
--parent-ticket G-703 --labels agent --priority 3`:

| ID | MCP / Role |
|---|---|
| G-714 | playwright |
| G-715 | browser-use |
| G-716 | chrome-devtools |
| G-717 | lightpanda |
| G-718 | obscura |
| G-719 | firecrawl |
| G-720 | cloakbrowser |
| G-721 | synthesis (blocked on G-714..G-720) |

Linear has no `--estimate` flag; estimates are documented inline in each
ticket's description body (4-6h per MCP scoring ticket). Parent G-703 received
a comment listing all 8 IDs (comment id `3d084853-ae87-4811-b53c-8f48b674ce63`).
In-repo record at `docs/LINEAR_SUBTICKETS.md` with status `COMPLETE`.

## What Was Verified

| Verification | Result |
|---|---|
| `scripts/install_hooks.sh` creates `.git/hooks/pre-commit` symlink | PASS |
| `scripts/install_hooks.sh` is idempotent (run twice, same symlink, no error) | PASS |
| Hook blocks real-repo commit when `.mcp.json` contains literal `fc-...` (manual end-to-end test on the real repo, then restored) | PASS (rc=1 with expected message) |
| Hook allows `${FIRECRAWL_API_KEY}` reference (commits in this plan have an unchanged `.mcp.json`; all 4 commits passed the hook) | PASS |
| `tests/test_secret_guard.sh` — case A (inline secret rejected) + case B (env-ref accepted) | PASS |
| `tests/test_scrub_artifacts.py` — 4 cases (Jane Testworth only / John Smith flagged / missing path / --allow extension) | PASS |
| `tests/test_cloakbrowser_guard.py` — 11 cases (loopback IPv4/v6/localhost accepted; greenhouse.io, google.com, RFC1918, DNS-rebinding lookalike, empty, None, file://, relative path all rejected) | PASS |
| `uv run python -m unittest discover tests` — 15 tests | PASS |
| `docs/LINEAR_SUBTICKETS.md` contains all 8 IDs | PASS (G-714..G-721) |
| Pre-commit hook accepted all 4 plan commits | PASS |

## Decisions Made

- **Shell over Python for the hook.** Per CONTEXT.md "Claude's discretion"
  entry — this repo is shell-heavy; keep the hook idiomatic. The hook is
  bash 3.2-portable (no `mapfile`) so it runs under macOS system bash without
  requiring Homebrew bash.
- **Hook source in-repo, .git/hooks/pre-commit as symlink.** Future edits to
  `scripts/hooks/pre-commit` take effect without reinstall. `scripts/install_hooks.sh`
  is idempotent (removes existing pre-commit file/symlink before re-symlinking).
- **PII scrub allow-list default is exactly `{"Jane Testworth"}`.** The regex
  is intentionally conservative — section titles in legitimate result files
  (e.g. "Final Ranking", "Test Environment") also match the two-word regex.
  Callers extend via `--allow <file>` rather than relaxing the regex. This
  trades a noisier first scan for a hard guarantee that real human names
  can't slip through.
- **cloakbrowser allow-list is exact-match loopback.** RFC1918 LAN addresses
  and DNS-rebinding lookalikes (e.g. `localhost.example.com`) explicitly
  reject. The harness only ever points cloakbrowser at the self-hosted
  snapshot server bound to 127.0.0.1.
- **OCR graceful degradation.** If `pytesseract` or `tesseract` is unavailable
  on a future host, image files emit `OCR_SKIPPED: <path>` and the text-only
  scan continues. Tests run with OCR available (Mac Mini has tesseract 5.5.2);
  graceful-degradation path was implemented but not unit-tested in this wave.
- **Linear estimate stored inline in description body.** `linearis` has no
  `--estimate` flag (confirmed via `linearis issues create --help`); the
  HANDOFF-GSD-AUTO.md cheat sheet anticipated this.

## Deviations from Plan

### None of the four deviation rules fired.

- No bugs found in plan instructions.
- No critical missing functionality requiring auto-add (Rule 2): the plan's
  cloakbrowser allow-list spec was complete; tests adding `localhost.example.com`
  + RFC1918 rejection are belt-and-suspenders, not adds.
- One blocking issue surfaced and was auto-fixed inline (Rule 3): macOS
  system bash 3.2 lacks `mapfile`. The pre-commit hook initially used
  `mapfile -t staged_files < <(...)`; running `tests/test_secret_guard.sh`
  surfaced `mapfile: command not found` from the spawned `git commit` shell.
  Replaced with a portable `while IFS= read -r path; do … done <<EOF` block
  + here-string. Tests re-ran and passed. **Files affected:**
  `scripts/hooks/pre-commit`. **Tracked as:** [Rule 3 - Blocking] bash 3.2
  portability fix.

## Authentication Gates

None. `LINEAR_API_TOKEN` was present in env (`~/.zshrc` rbw-loaded);
`linearis` authenticated cleanly on first call. The plan's STOP-condition
fallback (`docs/LINEAR_SUBTICKETS.md` with `STATUS: PENDING`) was not needed —
all 8 tickets created autonomously.

## Files Created

| Path | Purpose |
|---|---|
| `.git/hooks/pre-commit` (symlink) | Active hook installed via `scripts/install_hooks.sh` |
| `scripts/hooks/pre-commit` | Hook source-of-truth; bash 3.2-portable |
| `scripts/install_hooks.sh` | Idempotent symlink installer |
| `bench/__init__.py` | Empty package marker |
| `bench/scrub_artifacts.py` | OCR + name-regex PII sweep, CLI + library |
| `bench/cloakbrowser_guard.py` | `assert_local_only(url)` loopback-only gate |
| `tests/__init__.py` | Empty package marker |
| `tests/test_secret_guard.sh` | End-to-end test via scratch git repo |
| `tests/test_scrub_artifacts.py` | 4 unittest cases |
| `tests/test_cloakbrowser_guard.py` | 11 unittest cases |
| `docs/LINEAR_SUBTICKETS.md` | In-repo record of G-714..G-721 |

## Files Modified

| Path | Change |
|---|---|
| `pyproject.toml` | Added `pytesseract>=0.3.10`, `Pillow>=10.0` deps; added `pytest>=8` dev-dep |
| `uv.lock` | Regenerated via `uv lock` + `uv sync --locked` (7 packages added: pillow, pytesseract, pytest, iniconfig, packaging, pluggy, pygments) |

## Commits

| Hash | Message |
|---|---|
| `127ca5d` | G-703: pre-commit hook + installer for inline-secret blocking (SAFETY-01) |
| `b62a2b2` | G-703: bench/scrub_artifacts.py PII sweep (SAFETY-02) |
| `4ccea0d` | G-703: bench/cloakbrowser_guard.py loopback-only gate (SAFETY-04) |
| `3dfa6a8` | G-703: split into 8 sub-tickets G-714..G-721 (OUTREACH-03) |

## Known Stubs

None. All three safety gates are fully wired and verified end-to-end. The
plan was scoped to safety gates only; the gates that consume them (e.g.,
`scripts/run_mcp_session.sh` importing `assert_local_only`) land in plan 01-04
per the original Files Modified table in the plan.

## Deferred Issues

- `scripts/run_mcp_session.sh` integration of `bench.cloakbrowser_guard.assert_local_only`
  is deferred to plan 01-04 per PLAN.md scope. The guard module is importable
  and unit-tested; the integration call site is not yet exercised.
- OCR graceful-degradation path (pytesseract/tesseract missing) is implemented
  but not unit-tested (the test host has tesseract 5.5.2). Could be exercised
  in a follow-up test by mocking the import; not in scope this plan.
- Real-world scrub of existing `results/2026-03-31_run.md` flagged 40+ matches
  that are all legitimate section titles ("Final Ranking", "Test Environment",
  etc.) — NOT PII. Documents that the conservative regex requires an `--allow`
  file when applied to prose files; the gate is calibrated for evidence
  artifacts (form-field captures, screenshots, JSONL traces), not narrative
  reports. Future caller can pass `--allow docs/legitimate_names.txt` or
  scope the scrub target to `results/<date>/<mcp>/stage_*.{yml,png,jsonl}`.

## Self-Check: PASSED

**Files (all exist):**
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/.git/hooks/pre-commit` (symlink)
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/scripts/hooks/pre-commit`
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/scripts/install_hooks.sh`
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/bench/__init__.py`
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/bench/scrub_artifacts.py`
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/bench/cloakbrowser_guard.py`
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/tests/__init__.py`
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/tests/test_secret_guard.sh`
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/tests/test_scrub_artifacts.py`
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/tests/test_cloakbrowser_guard.py`
- FOUND: `/Users/pleasedodisturb/Projects/web-agent-comparison/docs/LINEAR_SUBTICKETS.md`

**Commits (all exist on G-703/phase-01-harness-foundation):**
- FOUND: 127ca5d (pre-commit hook + installer)
- FOUND: b62a2b2 (scrub_artifacts)
- FOUND: 4ccea0d (cloakbrowser_guard)
- FOUND: 3dfa6a8 (Linear sub-ticket split)

**Linear sub-tickets (8 created, verified via `linearis issues read G-703 → .subIssues[]`):**
- FOUND: G-714 (playwright), G-715 (browser-use), G-716 (chrome-devtools),
  G-717 (lightpanda), G-718 (obscura), G-719 (firecrawl), G-720 (cloakbrowser),
  G-721 (synthesis).
