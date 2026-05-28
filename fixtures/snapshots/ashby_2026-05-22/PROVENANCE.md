# Snapshot provenance — ashby_2026-05-22

- **Source URL:** https://jobs.ashbyhq.com/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13
- **Capture date:** 2026-05-22 (UTC)
- **Capture timestamp:** 2026-05-22T15:49:41Z
- **Capture tool:** GNU Wget 1.25.0 built on darwin25.2.0.
- **Captured by:** scripts/snapshot_fixtures.sh
- **Scrubbing applied:**
  - Two-word capitalized strings replaced with `Jane Testworth` using the
    same `NAME_REGEX` as `bench/scrub_artifacts.py`, iterated to convergence.
  - Count of pre-scrub non-allow-listed matches: 0
  - Allow-list deltas: none
- **Directory SHA256:** af89d108d20bdb707cbd85698ec39773999748a5550b54d88ad449418b213a46  ashby_2026-05-22
- **Files captured:** 1
- **Total bytes (served content):** 6294
- **Primary HTML:** `replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html` (6294 bytes)
- **Reason for capture:** Pitfall 8 (public-fixture rot) — live URLs 404 within 6 months. This snapshot is the test target; live-URL drift is a separate daily-smoke gate (deferred to G-710).
- **Drift detection:** ONE live-URL smoke test per platform — `make smoke-live` (diagnostic only, not part of the scored bench flow).

## SPA-shell caveat

**SPA-shell detected:** primary HTML contains a `<div id="root">` mount point and a `<noscript>You need to enable JavaScript</noscript>` banner, indicating no server-rendered listing content. wget --mirror cannot capture the runtime-fetched API responses that hydrate this SPA; the harness will see the shell (and the loading-spinner CSS) only. Acceptable for Phase 1 — this IS the reproducibility surface, and the snapshot is what every MCP gets measured against. The recording-proxy fix is deferred per CONTEXT.md scope cut.
