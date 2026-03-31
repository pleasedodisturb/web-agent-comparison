# Web Agent Comparison Suite

A head-to-head comparison of 5 web automation agents tested against real job application flows (Anthropic Greenhouse + Replit Ashby).

## Agents Tested

| Agent | Type | Score |
|-------|------|-------|
| **Playwright MCP** | MCP (28 tools) | **9.07/10** |
| **WebFetch** | Built-in | **7.87/10** |
| **Agent Browser CLI** | Rust CLI | **7.60/10** |
| **Lightpanda CLI** | Zig binary | **5.87/10** |
| **BrowserMCP** | Chrome extension MCP | **5.53/10** |

## Test Flow

Real real job application pipeline stages:

1. **S1** Extract structured job data (Greenhouse — server-rendered)
2. **S2** Extract from React SPA (Ashby — client-rendered)
3. **S3** ATS platform detection
4. **S4** Navigate to apply form
5. **S5** Fill application form with mock data
6. **S6** Upload mock resume
7. **S7** Handle dropdown fields
8. **S8** Screenshot filled form

## Key Findings

- **Playwright MCP's `browser_fill_form`** fills 6 fields in 1 tool call vs 4+ commands for other agents
- **Lightpanda returns 0 bytes** on React SPA pages (Zig JS engine can't render React)
- **BrowserMCP disconnected** mid-session — connection instability is its defining weakness
- **WebFetch is 20x more token-efficient** than snapshot-based agents (1.5KB vs 28-33KB)
- **Agent Browser's cold start** takes 25-40 seconds (Chromium launch)

## Results

Full report: [results/2026-03-31_run.md](results/2026-03-31_run.md)

## Structure

```
fixtures/          Mock data and resume PDF
scripts/           CLI agent test scripts
scoring/           Rubric and scoring engine
results/           Test outputs, screenshots, scores
```

## Scoring

8 dimensions, weighted by importance for job application automation:

- Data Quality (3x), Reliability (3x), Speed (2x), Token Efficiency (2x)
- Interaction Depth (2x), JS Rendering (1x), Setup Complexity (1x), Error Handling (1x)

Run: `python3 scoring/score.py results/scores.json`
