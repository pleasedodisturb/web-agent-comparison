---
phase: 1
plan: 03
type: execute
wave: 2
depends_on:
  - 01-02   # uses bench/scrub_artifacts.py to verify the snapshot is PII-clean
files_modified:
  - scripts/snapshot_fixtures.sh
  - scripts/serve_fixtures.sh
  - fixtures/snapshots/greenhouse_2026-05-22/PROVENANCE.md
  - fixtures/snapshots/ashby_2026-05-22/PROVENANCE.md
  - fixtures/snapshots/.gitkeep
  - tests/test_snapshot_serves.sh
requirements:
  - REPRO-04
  - REPRO-05
success_criteria_advanced: [1, 2]
status: planned
autonomous: true
estimate_hours: 2

must_haves:
  truths:
    - "`scripts/snapshot_fixtures.sh` produces a self-contained mirror of the Greenhouse + Ashby targets under `fixtures/snapshots/<platform>_<date>/`."
    - "`scripts/serve_fixtures.sh` boots `python3 -m http.server` on 127.0.0.1:8765 and serves the snapshot tree."
    - "Each snapshot dir carries a `PROVENANCE.md` recording source URL, capture date, capture tool version, scrubbing applied, and a SHA256 over the served-content directory."
    - "`bench/scrub_artifacts.py` (from plan 01-02) reports zero PII findings against the committed snapshots."
    - "Fetching `http://127.0.0.1:8765/greenhouse_2026-05-22/index.html` returns the snapshot's HTML (not a 404)."
  artifacts:
    - path: "scripts/snapshot_fixtures.sh"
      provides: "wget --mirror + sed-scrub + sha256 wrapper that captures a target URL into fixtures/snapshots/<platform>_<date>/"
    - path: "scripts/serve_fixtures.sh"
      provides: "Loopback HTTP server boot/teardown; binds 127.0.0.1:8765; writes pidfile for harness cleanup"
    - path: "fixtures/snapshots/greenhouse_2026-05-22/"
      provides: "Mirrored Greenhouse posting from the prior 2026-03-31 wave URL (or a fresh equivalent if 404'd)"
    - path: "fixtures/snapshots/greenhouse_2026-05-22/PROVENANCE.md"
      provides: "Source URL, capture date, wget version, scrubbing log, dir SHA256"
    - path: "fixtures/snapshots/ashby_2026-05-22/"
      provides: "Mirrored Ashby React SPA posting"
    - path: "fixtures/snapshots/ashby_2026-05-22/PROVENANCE.md"
      provides: "Source URL, capture date, wget version, scrubbing log, dir SHA256"
  key_links:
    - from: "scripts/serve_fixtures.sh"
      to: "fixtures/snapshots/"
      via: "python3 -m http.server --directory fixtures/snapshots/ --bind 127.0.0.1 8765"
      pattern: "http\\.server.*--bind 127\\.0\\.0\\.1"
    - from: "fixtures/snapshots/<platform>_<date>/PROVENANCE.md"
      to: "directory SHA256"
      via: "tar -cf - --sort=name <dir> | sha256sum"
      pattern: "SHA256 .* <dir>"
---

## Goal

Capture the Greenhouse and Ashby target pages as self-hosted, PII-scrubbed snapshots so the harness drives MCPs against `127.0.0.1` rather than live URLs. Pitfall 8 (public-fixture rot) and Pitfall 6 (live-site rate limiting) both die at this gate. Per CONTEXT.md, snapshot dates use `2026-05-22` (capture date) explicitly — no `_latest_` symlinks.

The Ashby SPA is the critical case: it's a React app, so a naive `wget --mirror` returns a 0-byte shell. The script captures both the initial HTML AND the runtime-fetched bundle endpoints so a local server can replay the SPA without an internet round-trip.

## Files Modified

| File | New / Modified | Purpose |
|---|---|---|
| `scripts/snapshot_fixtures.sh` | NEW | Wrapper around `wget --mirror`. Takes `<platform> <url>`. Mirrors + scrubs + records provenance. |
| `scripts/serve_fixtures.sh` | NEW | Boots `python3 -m http.server 8765 --bind 127.0.0.1 --directory fixtures/snapshots/`. Writes pidfile to `/tmp/wac_fixture_server.pid`. Has `start`/`stop`/`status` subcommands. |
| `fixtures/snapshots/.gitkeep` | NEW | Ensure dir exists before snapshot. |
| `fixtures/snapshots/greenhouse_2026-05-22/` | NEW (mirrored tree) | The wget output. |
| `fixtures/snapshots/greenhouse_2026-05-22/PROVENANCE.md` | NEW | Source URL, capture date + UTC time, wget version, scrub log, SHA256. |
| `fixtures/snapshots/ashby_2026-05-22/` | NEW (mirrored tree) | The wget output for Ashby. |
| `fixtures/snapshots/ashby_2026-05-22/PROVENANCE.md` | NEW | Same shape. |
| `tests/test_snapshot_serves.sh` | NEW | Boots `serve_fixtures.sh start`, curls both snapshot index URLs, asserts 200 + non-empty body, then `serve_fixtures.sh stop`. |

## Tasks

1. **Write `scripts/snapshot_fixtures.sh`.**
   - Args: `$1 = platform (greenhouse|ashby)`, `$2 = source_url`. Optional `$3 = date_override` (defaults to `$(date -u +%Y-%m-%d)`).
   - Output dir: `fixtures/snapshots/${platform}_${date}/`.
   - Steps:
     1. `mkdir -p` the output dir.
     2. Run `wget --mirror --convert-links --adjust-extension --page-requisites --no-parent --execute robots=off --user-agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36' --directory-prefix="${OUTDIR}" "${URL}"`. Capture exit code; non-zero = bail with a one-line message naming the URL.
     3. Apply PII scrubs via `find "${OUTDIR}" -type f \( -name '*.html' -o -name '*.htm' -o -name '*.js' -o -name '*.json' \) -print0 | xargs -0 sed -i.bak -E -e 's/[A-Z][a-z]+ [A-Z][a-z]+/Jane Testworth/g'`. (Aggressive: any two-word capitalized run becomes the mock applicant. This is intentionally over-zealous; the scrub log captures all replacements.)
     4. `find "${OUTDIR}" -name '*.bak' -delete` to clean up `sed`'s backups.
     5. Compute directory SHA256: `tar -cf - --sort=name "${OUTDIR}" | shasum -a 256 | awk '{print $1}' > "${OUTDIR}/.sha256"`.
     6. Write `${OUTDIR}/PROVENANCE.md` (next task).
   - Idempotency: if `${OUTDIR}` already exists, the script aborts with `snapshot already exists at ${OUTDIR}; rm -rf to re-capture`. No silent overwrite.
   - **verify:** `bash -n scripts/snapshot_fixtures.sh` syntax-checks; manual dry-run against a known-stable URL (e.g. `https://example.com/`) into a `tmp/` dir produces the expected file tree.

2. **Capture the Greenhouse + Ashby snapshots.**
   - Prior-wave URLs (from `results/2026-03-31_run.md`):
     - Greenhouse: `https://job-boards.greenhouse.io/anthropic/jobs/4017544008`
     - Ashby: `https://jobs.ashbyhq.com/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13`
   - Run `scripts/snapshot_fixtures.sh greenhouse https://job-boards.greenhouse.io/anthropic/jobs/4017544008`.
   - Run `scripts/snapshot_fixtures.sh ashby https://jobs.ashbyhq.com/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13`.
   - **If either URL returns 404** (per HANDOFF-GSD-AUTO STOP condition #4), pause and surface to user: "Prior-wave URL is dead. Identify a fresh Greenhouse/Ashby posting from the same ATS and re-run. New URL must be a live application form, not a closed listing." Do not silently substitute a different URL.
   - **If both 404:** STOP and surface; this is the "the world has changed" case.
   - **verify:** `ls fixtures/snapshots/greenhouse_2026-05-22/` shows files; `ls fixtures/snapshots/ashby_2026-05-22/` shows files; both directories have non-zero size.

3. **Write the two `PROVENANCE.md` files.**
   - Template:
     ```markdown
     # Snapshot Provenance — <platform>_2026-05-22

     - **Source URL:** <url>
     - **Capture date:** 2026-05-22 (UTC)
     - **Capture tool:** wget <version from `wget --version | head -1`>
     - **Captured by:** scripts/snapshot_fixtures.sh
     - **Scrubbing applied:**
       - Two-word capitalized strings replaced with `Jane Testworth` (sed regex)
       - Count of substitutions: <count from sed output>
       - Allow-list deltas: none
     - **Directory SHA256:** <from .sha256 file>
     - **Reason for capture:** Pitfall 8 (public-fixture rot) — live URLs 404 within 6 months. This snapshot is the test target; live-URL drift is a separate daily-smoke gate (deferred to G-710).
     - **Drift detection:** ONE live-URL smoke test per platform documented in `results/<date>/MACHINE.md` (Phase 4 plan).
     ```
   - **verify:** `cat fixtures/snapshots/greenhouse_2026-05-22/PROVENANCE.md` and `cat fixtures/snapshots/ashby_2026-05-22/PROVENANCE.md` both render with all 6 sections filled.

4. **Run `bench/scrub_artifacts.py` against the snapshots.**
   - `uv run python -m bench.scrub_artifacts fixtures/snapshots/` must exit 0. Any flagged match → the scrub `sed` missed a case; expand the regex or allow-list and re-capture.
   - **verify:** Exit code 0.

5. **Write `scripts/serve_fixtures.sh`.**
   - Subcommands: `start`, `stop`, `status`.
   - `start`:
     - Refuse if pidfile exists and the PID is alive: `serve_fixtures: already running at PID $(cat /tmp/wac_fixture_server.pid)`.
     - Otherwise: `nohup python3 -m http.server 8765 --bind 127.0.0.1 --directory fixtures/snapshots/ > /tmp/wac_fixture_server.log 2>&1 &`. Echo `$!` to `/tmp/wac_fixture_server.pid`.
     - Wait up to 5s for a `curl -fsS http://127.0.0.1:8765/ > /dev/null` to succeed; fail with the log tail if it doesn't.
   - `stop`: if pidfile exists, `kill $(cat /tmp/wac_fixture_server.pid)` and remove pidfile. If not, no-op silently.
   - `status`: print `running|stopped` based on pidfile + live check.
   - **verify:** `scripts/serve_fixtures.sh start` succeeds; `curl -fsS http://127.0.0.1:8765/greenhouse_2026-05-22/` returns 200 with body listing the directory; `scripts/serve_fixtures.sh stop` exits 0; second `stop` is a no-op (idempotent).

6. **Write `tests/test_snapshot_serves.sh`.**
   - `set -euo pipefail`.
   - Run `scripts/serve_fixtures.sh start`. trap-exit `scripts/serve_fixtures.sh stop`.
   - Curl `http://127.0.0.1:8765/greenhouse_2026-05-22/` and assert HTTP 200 + body length > 1024.
   - Curl `http://127.0.0.1:8765/ashby_2026-05-22/` and same assertion.
   - **verify:** `bash tests/test_snapshot_serves.sh` exits 0.

7. **Wire `serve_fixtures.sh start` into the Makefile (light edit to plan 01-01).**
   - Add a `fixtures-serve` and `fixtures-stop` target to the Makefile. `bench-%` (defined in plan 01-04) will depend on `fixtures-serve` so the harness boots the server before driving an MCP.
   - For now, just add the bare targets; the dependency wiring lands in plan 01-04.
   - **verify:** `make fixtures-serve` boots the server (use `make fixtures-stop` to clean up afterward).

## Acceptance

- `fixtures/snapshots/greenhouse_2026-05-22/` and `fixtures/snapshots/ashby_2026-05-22/` exist with non-zero content and PROVENANCE.md files.
- `bench/scrub_artifacts.py` reports clean against both snapshot directories.
- `scripts/serve_fixtures.sh start` boots a loopback server reachable at `http://127.0.0.1:8765/<platform>_<date>/`.
- `tests/test_snapshot_serves.sh` exits 0.
- Both PROVENANCE.md files record the source URL, capture date, capture tool + version, scrubbing log, and directory SHA256 (per REPRO-05 literal wording).

## Dependencies

- **Plan 01-02:** `bench/scrub_artifacts.py` must exist before this plan runs (task 4 uses it). 01-02 and 01-03 can technically run concurrently if 01-02's `scrub_artifacts.py` lands first; mark as sequential for safety (this plan is Wave 2).

## Notes / Pitfalls

- **Pitfall 8 (public-fixture rot):** This plan's purpose. The snapshots commit to the repo (a few MB total) — that's the entire point of public reproducibility.
- **Pitfall 6 (target rate-limiting):** Deferred to G-710 (bot-detection scope cut), but the snapshot defense protects the 1hr stability loop in Phase 3 from rate-limiting against live targets.
- **Pitfall 12 (PII):** Aggressive sed scrub may over-scrub. Re-running `scrub_artifacts.py` against the result is the safety net. If the scrub destroys a load-bearing UI element (form field labels, etc.), expand the allow-list — but ONLY for words that aren't human names.
- **Ashby SPA caveat:** `wget --mirror` captures only the initial HTML + linked assets. The runtime-fetched API responses (`/api/...` calls the React app makes) are NOT captured by default. For Phase 1's Playwright calibration (plan 01-07), the Ashby fixture may render an empty shell because the app's JS will try to call the live API. If this contaminates the calibration, plan 01-07 falls back to the live URL with a documented caveat. The proper fix is to capture the API responses via a recording proxy — deferred to a future wave per CONTEXT.md (`scope_cut: live-URL smoke test as drift detector — NOT scored`).
- **CONTEXT.md decision:** "Snapshot capture script: shell wrapper around `wget --mirror` vs Python `requests`+`BeautifulSoup` — pick `wget --mirror` for fidelity to the original DOM (Greenhouse + Ashby React state matters)." Honored.
- **Per CONTEXT.md:** "Each snapshot directory carries `PROVENANCE.md`" — implemented exactly.

## Out of Scope

- Snapshotting the runtime API responses for the Ashby SPA — deferred (see Ashby caveat above).
- The live-URL smoke test as a drift detector — CONTEXT.md flags this as "NOT scored — drift signal only"; the smoke target lands in Phase 4 alongside the report.
- Cloudflare / DataDome adversary fixtures — deferred to G-710.
- The echo-server fixture for Sec-CH-UA-Platform leak detection — deferred to G-710 (per CONTEXT.md "Echo-server fixture ... deferred to G-710").
