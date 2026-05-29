---
phase: 1
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - .git/hooks/pre-commit
  - scripts/install_hooks.sh
  - bench/__init__.py
  - bench/scrub_artifacts.py
  - bench/cloakbrowser_guard.py
  - tests/test_secret_guard.sh
  - tests/test_scrub_artifacts.py
  - tests/test_cloakbrowser_guard.py
  - docs/LINEAR_SUBTICKETS.md
requirements:
  - SAFETY-01
  - SAFETY-02
  - SAFETY-04
  - OUTREACH-03
success_criteria_advanced: [5]
status: planned
autonomous: false  # OUTREACH-03 task creates a Linear checkpoint for confirmation
estimate_hours: 2

must_haves:
  truths:
    - "Attempting to commit a .mcp.json that contains a literal API key (regex `fc-[A-Za-z0-9_-]{20,}` or similar) is rejected by the pre-commit hook with an explicit message; `${VAR}` references pass cleanly."
    - "`bench/scrub_artifacts.py` rejects any artifact under `results/` containing a name other than `Jane Testworth`."
    - "Attempting to drive cloakbrowser at any hostname other than 127.0.0.1 / localhost is rejected by `bench/cloakbrowser_guard.py` before the MCP spawns."
    - "G-703 has 8 sub-tickets in Linear (one per MCP × 7 + 1 synthesis ticket) recorded in docs/LINEAR_SUBTICKETS.md, BEFORE Phase 2 starts."
  artifacts:
    - path: ".git/hooks/pre-commit"
      provides: "Regex-blocks inline secrets in .mcp.json; installable via scripts/install_hooks.sh"
    - path: "scripts/install_hooks.sh"
      provides: "Idempotent installer that symlinks .git/hooks/pre-commit to the in-repo source"
    - path: "bench/scrub_artifacts.py"
      provides: "OCR + name-regex scanner that walks results/<date>/ and rejects PII not matching the Jane Testworth mock"
    - path: "bench/cloakbrowser_guard.py"
      provides: "Pre-run guard: refuses cloakbrowser spawn if target hostname != 127.0.0.1/localhost"
    - path: "docs/LINEAR_SUBTICKETS.md"
      provides: "Mapping of G-703 → 8 sub-tickets (7 per-MCP + 1 synthesis) created via linearis"
  key_links:
    - from: ".git/hooks/pre-commit"
      to: ".mcp.json"
      via: "regex scan on staged content"
      pattern: "(api[_-]?key|token|secret|fc-|sk-|Bearer ).*[A-Za-z0-9_-]{20,}"
    - from: "bench/cloakbrowser_guard.py"
      to: "scripts/run_mcp_session.sh"
      via: "imported and called when MCP == cloakbrowser"
      pattern: "from bench.cloakbrowser_guard import assert_local_only"
---

## Goal

Land the three "do-no-harm" gates before any MCP-driving code is written, and split G-703 into the 8 sub-tickets that must exist in Linear before Phase 2 starts. The three gates: (a) pre-commit hook regex-blocking inline secrets in `.mcp.json` (SAFETY-01), (b) `bench/scrub_artifacts.py` rejecting any non-Jane-Testworth name in committed artifacts (SAFETY-02), (c) `bench/cloakbrowser_guard.py` refusing cloakbrowser spawn against any host other than 127.0.0.1 (SAFETY-04). Plus the Linear sub-ticket split (OUTREACH-03), which is the break-before-cycle signal for G-703.

Plan 01-03 will also call `bench/scrub_artifacts.py` on the snapshot directories — having it in place first keeps the dependency clean.

## Files Modified

| File | New / Modified | Purpose |
|---|---|---|
| `.git/hooks/pre-commit` | NEW (in-repo source at `scripts/hooks/pre-commit`; symlinked from `.git/hooks/`) | Regex-block inline secrets in any staged `.mcp.json`. |
| `scripts/install_hooks.sh` | NEW | Symlinks `.git/hooks/pre-commit` → `../../scripts/hooks/pre-commit`. Idempotent. Documented in README later. |
| `scripts/hooks/pre-commit` | NEW | The actual hook source (versioned in-repo; `.git/hooks/pre-commit` is just a symlink). |
| `bench/__init__.py` | NEW | Empty (makes `bench` a Python package). |
| `bench/scrub_artifacts.py` | NEW | OCR + name-regex scanner. CLI: `python -m bench.scrub_artifacts results/<date>/`. Returns non-zero on any PII match. |
| `bench/cloakbrowser_guard.py` | NEW | `assert_local_only(target_url: str) -> None`. Raises `cloakbrowser_guard.HostnameNotAllowedError` if `urlparse(target_url).hostname not in {"127.0.0.1", "localhost", "[::1]"}`. |
| `tests/test_secret_guard.sh` | NEW | Bash test exercising the pre-commit hook against fixture `.mcp.json` files (one with inline `"fc-..."`, one with `"${FIRECRAWL_API_KEY}"`). |
| `tests/test_scrub_artifacts.py` | NEW | pytest-style (run via `uv run python -m unittest`). Asserts: (a) directory containing only "Jane Testworth" passes; (b) directory containing "John Smith" fails with exit code 1 and the matched line in stderr. |
| `tests/test_cloakbrowser_guard.py` | NEW | Asserts: (a) `127.0.0.1` and `localhost` accepted; (b) `greenhouse.io` and any non-loopback raise `HostnameNotAllowedError`. |
| `docs/LINEAR_SUBTICKETS.md` | NEW | Records the 8 sub-ticket IDs created in Linear (filled in during the checkpoint task). |

## Tasks

1. **Write the pre-commit hook (in-repo source + installer).**
   - `scripts/hooks/pre-commit`: Bash. `set -euo pipefail`. For each staged path matching `*.mcp.json` (via `git diff --cached --name-only --diff-filter=ACM | grep -E '\.mcp\.json$'`), `git show :"$path"` and pipe through the regex check. Regex: `(api[_-]?key|token|secret).*"[A-Za-z0-9_-]{20,}"` AND `"(fc-|sk-|Bearer )[A-Za-z0-9_-]{20,}"`. Both patterns OR'd. Match → print `Inline secret detected in $path — use \${ENV_VAR} reference instead.` and `exit 1`. No match → silent pass.
   - Allow-list `${VAR}` shape explicitly: a value of `"${ANYTHING}"` (curly-braced shell-style) must NOT match. Test by adding a negative-lookahead-like construct or by stripping `${...}` substitutions before the regex pass.
   - `scripts/install_hooks.sh`: `#!/usr/bin/env bash`, `set -euo pipefail`. `ln -sf ../../scripts/hooks/pre-commit .git/hooks/pre-commit && chmod +x scripts/hooks/pre-commit && echo "pre-commit hook installed"`.
   - Run `scripts/install_hooks.sh` and confirm `.git/hooks/pre-commit` is a symlink to `../../scripts/hooks/pre-commit`.
   - **verify:** `tests/test_secret_guard.sh` (next task).

2. **Write `tests/test_secret_guard.sh`.**
   - Create `tests/fixtures/mcp_json_with_secret/.mcp.json` containing `{"mcpServers":{"firecrawl":{"command":"firecrawl-mcp","env":{"FIRECRAWL_API_KEY":"fc-1234567890abcdefghij1234567890"}}}}` — this is a FIXTURE FILE, not the repo's real `.mcp.json`. Keep it under `tests/fixtures/` so the path-name filter on the hook (`*.mcp.json`) still hits it during the test (the test uses `git apply --check` semantics or a scratch repo, see below).
   - Test approach: create a `tmpdir` scratch git repo, copy in the hook, copy in a fixture `.mcp.json`, run `git add . && git commit -m test` — assert exit code 1 with the expected message.
   - Run the same test with a fixture that uses `"${FIRECRAWL_API_KEY}"` — assert exit code 0.
   - **verify:** `bash tests/test_secret_guard.sh` exits 0; both cases pass.

3. **Write `bench/scrub_artifacts.py`.**
   - Use `pytesseract` for OCR on `*.png` files and direct read for `*.md`, `*.txt`, `*.yml`, `*.jsonl`, `*.json`. (Add `pytesseract` to `pyproject.toml` deps; re-`uv lock`. If `tesseract` system binary isn't available, the script falls back to text-only scan and emits `OCR_SKIPPED` for PNGs — document this fallback.)
   - For each file: collect strings via regex `\b[A-Z][a-z]+ [A-Z][a-z]+\b` (two-word capitalized). Allow-list: `Jane Testworth`. Any other match → record `{file, line_no, match}`.
   - CLI: `python -m bench.scrub_artifacts <dir>`. Exit 0 if no flagged matches. Exit 1 otherwise, print each match to stderr as `FLAG: <file>:<line_no>: <match>`.
   - Optional `--allow <file>` to extend the allow-list (useful for legitimate names in `PROVENANCE.md` like vendor names — but default-strict).
   - **verify:** `tests/test_scrub_artifacts.py` (next task).

4. **Write `tests/test_scrub_artifacts.py`.**
   - Test case A: `tmp_path / "ok" / "stage_s5.md"` containing `Jane Testworth filled the form.` — assert `subprocess.run([sys.executable, "-m", "bench.scrub_artifacts", str(tmp_path / "ok")])` exits 0.
   - Test case B: `tmp_path / "bad" / "stage_s1.md"` containing `Applicant: John Smith.` — assert exit code 1 and `John Smith` in stderr.
   - Run via `uv run python -m unittest tests.test_scrub_artifacts -v`.
   - **verify:** `uv run python -m unittest tests.test_scrub_artifacts` passes both cases.

5. **Write `bench/cloakbrowser_guard.py`.**
   - Define `class HostnameNotAllowedError(RuntimeError)`. Define `ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}`. Define `def assert_local_only(url: str) -> None`: parse via `urllib.parse.urlparse(url)`, raise `HostnameNotAllowedError(f"cloakbrowser refused: hostname {host!r} not in {ALLOWED_HOSTS}")` if hostname not allowed.
   - Document in a module docstring: "Closed-source binary touches cookies. Per global SAFETY policy, never point at authenticated host pages. SAFETY-04 contract."
   - **verify:** `tests/test_cloakbrowser_guard.py` (next task).

6. **Write `tests/test_cloakbrowser_guard.py`.**
   - Test the four allow-list cases pass; `https://greenhouse.io/...` and `https://google.com` raise `HostnameNotAllowedError`.
   - **verify:** `uv run python -m unittest tests.test_cloakbrowser_guard` passes.

7. **Linear sub-ticket split (CHECKPOINT).**
   - This is a `checkpoint:human-action` style step because `linearis` requires the user's API token in env. The executor MUST attempt to run these commands; if `linearis` is on PATH and authenticated (LINEAR_API_TOKEN set per global CLAUDE.md), the executor creates the tickets autonomously and writes the resulting IDs into `docs/LINEAR_SUBTICKETS.md`.
   - Commands to run (per HANDOFF-GSD-AUTO § "Linear automation cheat sheet"):

     ```bash
     for mcp in playwright browser-use chrome-devtools lightpanda obscura firecrawl cloakbrowser; do
       linearis issues create "G-703 sub: score ${mcp} MCP end-to-end" \
         --team G \
         --project "Mac Setup & Environment" \
         --parent-ticket G-703 \
         --labels "agent" \
         --priority 3
     done

     linearis issues create "G-703 sub: synthesis — aggregate scores + write recommendations.md" \
       --team G \
       --project "Mac Setup & Environment" \
       --parent-ticket G-703 \
       --labels "agent" \
       --priority 3

     linearis comments create G-703 \
       --body "Sub-tickets filed for Phase 2 break-before-cycle: <list IDs here>"
     ```
   - Capture the 8 returned ticket IDs and write `docs/LINEAR_SUBTICKETS.md`:

     ```markdown
     # G-703 Sub-Tickets (created 2026-05-XX)

     | Sub-Ticket | Title | Status |
     |---|---|---|
     | G-XXX | G-703 sub: score playwright MCP end-to-end | Backlog |
     | ... | ... | ... |
     ```
   - **STOP condition:** If `linearis` is missing or auth fails, write `docs/LINEAR_SUBTICKETS.md` with `STATUS: PENDING — linearis unavailable in this environment; user must create 8 sub-tickets manually before Phase 2 starts.` and surface the gap to the user. Do NOT proceed past this task silently.
   - **verify:** `cat docs/LINEAR_SUBTICKETS.md` shows 8 sub-ticket IDs, OR a STATUS: PENDING line that explicitly surfaces the gap to the user.

## Acceptance

- Pre-commit hook is installed (`.git/hooks/pre-commit` is a symlink) and rejects a fixture `.mcp.json` with an inline secret while passing a `${VAR}`-reference variant. `tests/test_secret_guard.sh` exits 0.
- `bench/scrub_artifacts.py` exits 1 on a `John Smith` test directory and exits 0 on a `Jane Testworth`-only directory. `tests/test_scrub_artifacts.py` passes.
- `bench/cloakbrowser_guard.py` exposes `assert_local_only(url)` that accepts loopback and rejects everything else. `tests/test_cloakbrowser_guard.py` passes.
- `docs/LINEAR_SUBTICKETS.md` contains 8 sub-ticket IDs (or an explicit STATUS: PENDING with a surfacing message).
- Pre-commit hook installation is idempotent — running `scripts/install_hooks.sh` twice produces the same symlink with no error.

## Dependencies

- None. This plan is Wave 1 and runs in parallel with 01-01 and 01-03.
- `pyproject.toml` from plan 01-01 is already established; this plan adds `pytesseract` to it. If 01-01 hasn't landed yet, this plan creates the entries inline and 01-01 merges them.

## Notes / Pitfalls

- **Pitfall 11 (secrets):** This plan's primary defense. Backup defense: GitHub secret-scanning on the public repo (enabled by repo owner).
- **Pitfall 12 (PII):** `scrub_artifacts.py` is the gate. Allow-list is intentionally tiny (one name). If a legitimate non-Jane string surfaces later, expand via `--allow` rather than relaxing the regex.
- **Pitfall 13 (vendor blowback) — partially relevant:** cloakbrowser sandbox-only is a vendor-policy commitment as much as a safety constraint. The guard makes the policy machine-enforced.
- **Hook portability:** `.git/hooks/pre-commit` is symlinked, not copied, so future hook edits to the in-repo source take effect immediately. Mention this in the README later.
- **OCR fragility:** `pytesseract` requires the `tesseract` system binary. On Mac Mini, install via `brew install tesseract`. Document this in plan 01-04's update to README. If OCR is unavailable, the scrub falls back to text-only scan and emits `OCR_SKIPPED` warnings — acceptable for Phase 1 since screenshots get manual review before commit.
- **CONTEXT.md decision:** "Claude's Discretion — Pre-commit hook implementation: shell script vs Python — Claude picks whichever is more idiomatic for this repo (currently shell-heavy → shell)." Honored: hook is bash.

## Out of Scope

- Echo-server fixture for Sec-CH-UA-Platform leak detection (SAFETY-03 is partially stubbed in plan 01-06; the underlying TLS work is deferred to G-710 per CONTEXT.md).
- Courtesy-disclosure ticket templates per OUTREACH-01/02 — deferred to G-710 (scope cut 2026-05-22).
- Wave-close ritual / scope-creep audit — Phase 4 (SAFETY-05).
- `gitleaks` integration — global rule recommends it but this plan implements the specific `.mcp.json`-targeted hook required by SAFETY-01; `gitleaks` is a possible future extension.
