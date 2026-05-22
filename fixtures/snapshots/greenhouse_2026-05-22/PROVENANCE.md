# Snapshot provenance — greenhouse_2026-05-22

- **Source URL:** https://job-boards.greenhouse.io/anthropic/jobs/5023394008
- **Capture date:** 2026-05-22 (UTC)
- **Capture timestamp:** 2026-05-22T15:49:32Z
- **Capture tool:** GNU Wget 1.25.0 built on darwin25.2.0.
- **Captured by:** scripts/snapshot_fixtures.sh
- **Scrubbing applied:**
  - Two-word capitalized strings replaced with `Jane Testworth` using the
    same `NAME_REGEX` as `bench/scrub_artifacts.py`, iterated to convergence.
  - Count of pre-scrub non-allow-listed matches: 190
  - Allow-list deltas: none
- **Directory SHA256:** 450ad57fa370c5f1d847855e294503c27b9446dcf9d83cb9d8d133e6b6a616e1  greenhouse_2026-05-22
- **Files captured:** 1
- **Total bytes (served content):** 84609
- **Primary HTML:** `anthropic/jobs/5023394008.html` (84609 bytes)
- **Reason for capture:** Pitfall 8 (public-fixture rot) — live URLs 404 within 6 months. This snapshot is the test target; live-URL drift is a separate daily-smoke gate (deferred to G-710).
- **Drift detection:** ONE live-URL smoke test per platform — `make smoke-live` (diagnostic only, not part of the scored bench flow).
