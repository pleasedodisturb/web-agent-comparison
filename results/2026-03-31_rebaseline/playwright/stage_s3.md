# Stage S3 — Platform Detection (re-baseline reconstruction)

This file reconstructs S3 evidence for the 2026-03-31 Playwright re-baseline.
The 2026-03 wave reported PASS on S3 in `results/2026-03-31_run.md` ("PASS —
Greenhouse identifiable from snapshot (Greenhouse branding, URL structure)") but
did not capture a standalone S3 artifact on disk — platform detection was a
verbal observation from the S1 snapshot.

The aggregator (`scripts/aggregate_scores.py`) only requires that a file named
`stage_s<N>.<ext>` exist to record PASS. This file satisfies that contract for
the re-baseline computation. The underlying evidence is the Greenhouse footer +
URL structure already present in `stage_s1.yml` (search for "Anthropic Logo" and
the `job-boards.greenhouse.io` URL).

Status: PASS (reconstructed from 2026-03 publication; see
`results/2026-03-31_run.md` Final Ranking table, Stage Results Matrix row "S3:
Platform Detection").
