# Web Agent Scoring Rubric

## Dimensions (8 total, weighted)

| Dimension | Weight | 0 (Fail) | 5 (Partial) | 10 (Perfect) |
|-----------|--------|----------|-------------|---------------|
| **Data Quality** | 3x | >50% fields missing | Core fields found | All fields, correctly structured |
| **Reliability** | 3x | Crashed / didn't complete | Required retries or workarounds | Completed first try, no errors |
| **Speed** | 2x | >30s per stage | 10-30s | <10s |
| **Token Efficiency** | 2x | >50KB context consumed | 10-50KB | <10KB |
| **Interaction Depth** | 2x | Read-only | Can navigate/click but not fill | Full form automation + file upload |
| **JS Rendering** | 1x | No JS execution | Partial (misses dynamic content) | Full SPA rendering |
| **Setup Complexity** | 1x | Multi-step scripting required | Config + 1 manual step | Zero setup / built-in |
| **Error Handling** | 1x | Crashes on unexpected state | Partial recovery | Graceful degradation, useful errors |

## Composite Score

`sum(score_i * weight_i) / sum(weight_i)` → 0-10 scale

Total weight = 3+3+2+2+2+1+1+1 = 15

## Test Stages

| ID | Stage | Type |
|----|-------|------|
| S1 | Extract job data (Lever) | Read-only |
| S2 | Extract job data (Ashby SPA) | Read-only |
| S3 | Platform detection | Read-only |
| S4 | Navigate to apply form | Interactive |
| S5 | Fill application form | Interactive |
| S6 | Upload resume | Interactive |
| S7 | Handle source dropdown | Interactive |
| S8 | Screenshot filled form | Interactive |
