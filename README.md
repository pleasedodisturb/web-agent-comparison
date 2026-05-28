# Web Agent Comparison Suite

A public, reproducible benchmark of browser-automation MCP servers driven by Claude Code on the same S1-S8 job-application fixtures. Stage 1 of a 3-stage pipeline: this repo scores candidate MCPs, the winners graduate into the private `terminal-craft` toolkit (Stage 2), which is wired into the `Kestrel` and `Eyas` job-hunting agents (Stage 3). Wave 2 (2026-05-27) compares **7 MCP-layer browser-automation servers** under Claude Code on the same fixture pipeline used by the 2026-03 app-level wave; the candidate matrix and the graduate-to-toolkit recommendation are what must exist at the end.

> **2026-05-27 update:** Wave 2 MCP-layer comparison published. See [results/recommendations.md](results/recommendations.md) for Stage 2 graduation tiers and [results/2026-05-27-mcp-comparison.md](results/2026-05-27-mcp-comparison.md) for full scored evidence. The historical 2026-03-31 app-level wave is preserved at [results/2026-03-31_run.md](results/2026-03-31_run.md) for traceability; it is no longer the primary headline.

## Headline verdict

Stage 2 graduation tiers across the **7 MCP candidates** in [`.mcp.json`](.mcp.json). Tier assignments are LOCKED — full rationale, evidence, and per-MCP citations live in [results/recommendations.md](results/recommendations.md).

| Tier | MCPs |
|------|------|
| PRIMARY | playwright, lightpanda |
| SECONDARY | browser-use (direct mode only — agent mode SKIPPED, see recommendations.md)[^1], chrome-devtools, firecrawl |
| SANDBOX-ONLY | cloakbrowser (**sandbox only — do not point at authenticated sessions**) |
| SKIP | obscura |

[^1]: browser-use produces TWO scored rows in `results/2026-05-26/scores.json` per FAIRNESS-05 (direct mode + agent mode), but counts as ONE candidate in the 7-MCP framing aligned with `.mcp.json`. Direct mode composite 5.87; agent mode SKIPPED (LLM_KEY_ABSENT). See [results/recommendations.md](results/recommendations.md) for the full dual-row narrative.

## Methodology summary

Evaluated 2026-05-27 with the locked 8-dimension weighted rubric (Data Quality 3×, Reliability 3×, Speed 2×, Token Efficiency 2×, Interaction Depth 2×, JS Rendering 1×, Setup Complexity 1×, Error Handling 1× — unchanged from the 2026-03 wave) against the **S1-S8 job-application pipeline** (Greenhouse SSR + Ashby React SPA fixtures). All fixtures are **self-hosted loopback snapshots** (REPRO-04) served from `127.0.0.1` and frozen byte-for-byte so any third party with the public repo can reproduce the scores — no live URL dependency. Seven MCP candidates were scored (one row per MCP in [`.mcp.json`](.mcp.json)); browser-use produces two scored rows per FAIRNESS-05 dual-mode contract while still counting as one candidate. Every stage failure triggers a 3-pass-of-3 retry per FAIRNESS-01 with the median across attempts published; `N/A` (categorically inapplicable, e.g. read-only MCP × interactive stage) and `UNTESTED` (no measurement taken) are deliberately distinct per FAIRNESS-03 so a read-only candidate is not penalised for not attempting form-fill. A capability-tagged dual view (per FAIRNESS-04) prevents apples-to-oranges comparison between cloud, stealth, JS-light, LLM-augmented, and tool-only categories. Full reproducibility recipe lives at [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

## Test stages

The locked S1-S8 job-application pipeline (same prompt drives every MCP for direct comparability — `prompts/stage_walk.md`):

1. **S1** Extract structured job data (Greenhouse — server-rendered)
2. **S2** Extract from React SPA (Ashby — client-rendered)
3. **S3** ATS platform detection
4. **S4** Navigate to apply form
5. **S5** Fill application form with mock data
6. **S6** Upload mock resume
7. **S7** Handle React-Select dropdown fields
8. **S8** Screenshot filled form

## Key findings (2026-05-27)

- **Lightpanda cold-start is 51× faster than browser-use-direct** (13 ms median vs ~660 ms), making it the read-only specialist for SSR-only paths; categorically N/A for S4-S8 per FAIRNESS-03 — and that's the point: pair with an interactive PRIMARY peer.
- **Playwright remains the interactive default** (composite **7.93**) but dropped from the 2026-03 live-URL baseline of 9.07 — same rubric, different fixture sourcing (loopback snapshot vs live URL) + 2026-05 vendor patches account for the delta. The `browser_fill_form` batch-fill claim is re-grounded by Phase 2 evidence.
- **Cloakbrowser leads the S1-S8 surface at composite 8.33** but is pre-tiered SANDBOX-ONLY by construction — the closed-source binary + cookie-touch trust model is the binding constraint, not the score. **Sandbox only — do not point at authenticated sessions.**
- **Firecrawl cloud cannot reach loopback fixtures by architecture** (cloud-API URL validator rejects `127.0.0.1` → tagged `env-mismatch` per FAIRNESS-06). The 9× byte-count lift on Greenhouse SSR (24,237 vs ~2.6 KB) is real; refuted on Ashby React SPA (203 bytes of footer chrome only).
- **Browser-use direct-mode works without a user LLM key** for the deterministic S1+S2+S3+S8 subset; **agent-mode SKIPPED** for `LLM_KEY_ABSENT` per the FAIRNESS-05 dual-row contract. Re-run procedure in `results/2026-05-26/browser-use-agent/SKIPPED.md`.

## Results

- **Full scored report:** [results/2026-05-27-mcp-comparison.md](results/2026-05-27-mcp-comparison.md)
- **Stage 2 recommendations** (the graduation gate): [results/recommendations.md](results/recommendations.md)
- **Reproducibility recipe:** [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)
- **Historical 2026-03 app-level wave** (preserved for traceability, not the primary headline): [results/2026-03-31_run.md](results/2026-03-31_run.md)

## Structure

```
.mcp.json          Project-scoped MCP server registry (the 7-candidate roster)
bench/             Harness + scoring + report builders (Python 3.12, uv-locked)
docs/              REPRODUCIBILITY recipe + run-environment docs
fixtures/          Mock data, resume PDF, and loopback snapshot fixtures (REPRO-04)
prompts/           Locked S1-S8 stage-walk prompt
scoring/           Locked 8-dimension rubric + N/A-aware scoring engine
scripts/           CLI agent test scripts + harness orchestration
results/           Per-wave dated subdirectories with scored evidence
```

## Scoring

Eight dimensions, weighted by importance for job-application automation (locked from the 2026-03 wave for direct comparability):

- Data Quality (3×), Reliability (3×), Speed (2×), Token Efficiency (2×)
- Interaction Depth (2×), JS Rendering (1×), Setup Complexity (1×), Error Handling (1×)

Composite is **N/A-aware**: cells marked `N/A` (categorically inapplicable) drop from the weighted denominator per FAIRNESS-03 rather than scoring 0. Run: `python3 bench/build_report.py` (regenerates the comparison matrix from `results/2026-05-26/scores.json` + cross-cutting JSON). Rubric: `scoring/rubric.md` — DO NOT MODIFY mid-wave.

## Future waves

The bot-detection + TLS-fingerprint + cross-machine reproducibility follow-up reuses this wave's harness and ships under [G-710](https://linear.app/abandoned-yachts/issue/G-710). Scope deferred from Wave 2:

- TLS fingerprint capture per MCP (JA3/JA4)
- Bot-detection adversary set (Cloudflare, reCAPTCHA, FingerprintJS, BrowserScan)
- Cross-machine reproducibility (MacBook parity vs the Mac Mini that ran this wave)
- Obscura Linux A/B (re-test `--stealth` from a Linux host where `Sec-CH-UA-Platform-*` is honest)
- Validation of the SANDBOX-ONLY tier's stealth claim against the live adversary set

This wave's umbrella is [G-703](https://linear.app/abandoned-yachts/issue/G-703).
