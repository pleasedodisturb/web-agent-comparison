# firecrawl — transcript (cloud-vs-loopback empirical run)

This MCP is a cloud service. The Phase-1 fixture-loopback contract serves
S1-S3 targets at `http://127.0.0.1:8765/...`, which firecrawl cloud cannot
reach. Per plan 02-03 Stop Conditions § default (b): score as 3× FAIL with
`env-mismatch` attribution.

## Loopback probes (3 passes, identical verdict)

```
POST https://api.firecrawl.dev/v1/scrape
  url: http://127.0.0.1:8765/greenhouse_2026-05-22/
HTTP 400 BAD_REQUEST
{"success":false,"code":"BAD_REQUEST",
 "error":"URL must have a valid top-level domain or be a valid path"}
```

Identical response for `http://127.0.0.1:8765/ashby_2026-05-22/`.

## Interesting-angle: single-shot live-URL probes (not scored, evidence only)

To test the research/SUMMARY.md claim that "Cloud LLM-extraction lifts Data
Quality (3x weight) above raw-page MCPs at cost of latency + tokens":

| URL | Bytes returned | Wall clock | Title extracted |
|---|---|---|---|
| `https://job-boards.greenhouse.io/anthropic/jobs/5023394008` (S1 live) | 24,237 markdown | ~0.7s | "Job Application for Anthropic Fellows Program at Anthropic" |
| `https://jobs.ashbyhq.com/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13` (S2 live) | 203 markdown (footer chrome only) | ~1.7s | "Jobs" (static, not job posting) |

These single-shot live probes are NOT used for scoring — they violate the
Phase-1 fixture-loopback invariant. They ARE used in DEEP_ANALYSIS.md as
empirical evidence about the claim and the tradeoff.

## Conclusion

S1, S2, S3 → FAIL (env-mismatch). S4-S8 → N/A (read-only MCP, no interactive surface).
