# Web Agent Comparison

**Which browser-automation MCP server should your AI agent use?**

Vendors all claim "real Chrome." Cold-start latencies vary **51×** across the field. One leader ships as a closed-source binary that touches your cookies on launch. Real tradeoffs are hidden behind marketing copy.

So we ran 7 of them on identical, frozen fixtures, scored every dimension that matters, and published the evidence. Pick a row.

> ⚠ **Scope of v1.0:** Job-application fixtures (Greenhouse server-rendered + Ashby React SPA). It's a useful proxy for "real, modern web pages" — but it is one specific use case. **v1.1 will expand the fixture set to general-purpose web tasks** (search, e-commerce, content extraction, multi-page navigation). The harness and rubric are designed to absorb the new fixtures without re-baselining.

## The verdict (2026-05-27)

| MCP | Composite | Cold-start (median) | Tier | Use it for | Skip it for |
|-----|----------:|--------------------:|------|------------|-------------|
| **[playwright](https://github.com/microsoft/playwright-mcp)** | **7.93** | 197 ms | 🟢 **PRIMARY** | Interactive forms, batch fills, the safe default | Nothing — it's the baseline |
| **[lightpanda](https://github.com/lightpanda-io/browser)** | **6.31** | **13 ms** ⚡ | 🟢 **PRIMARY** | Read-only SSR extraction — pair with Playwright as a 51× faster cold-start specialist | JS-heavy SPAs (it's a Zig engine with no JS runtime — React-blind by design) |
| [browser-use](https://github.com/browser-use/browser-use) (direct) | 5.87 | 668 ms | 🟡 SECONDARY | Direct tool mode without an LLM key for S1+S2+S3+S8 | Interactive form fill (S4–S7) — use Playwright |
| [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) | 5.60 | 358 ms | 🟡 SECONDARY | DevTools-specific debugging (network, perf, console) | First-pass scraping — use Playwright |
| [firecrawl](https://github.com/firecrawl/firecrawl-mcp-server) | 4.23 | 171 ms | 🟡 SECONDARY | Cloud SSR scraping at scale (9× byte-count lift on Greenhouse) | Local/loopback fixtures (cloud rejects 127.0.0.1) and React SPAs (203 bytes on Ashby) |
| [cloakbrowser](https://pypi.org/project/cloakbrowsermcp/) | **8.33** | 235 ms | 🔴 **SANDBOX-ONLY** | Public-fixture stealth research only | **Authenticated sessions** — closed-source binary touches cookies on launch |
| [obscura](https://www.npmjs.com/package/obscura-mcp) | 3.27 | 158 ms | ⚫ SKIP | (nothing on macOS today — wait for the Linux A/B in our follow-up wave) | macOS production use — `Sec-CH-UA-Platform-*` leaks the real OS |
| browser-use (agent mode) | **0.00** | — | ⚫ **TOOL-BUG** | (nothing — it doesn't start) | **Everything in v0.12.7's MCP path.** 30s `BrowserStartEvent` timeout when any LLM key is in env; reproducible without the harness (`stdio_probe_evidence.log`). Direct mode in the same binary scores 5.87. |

> 🐞 **v1.0.1 finding — browser-use 0.12.7 MCP-agent path is broken.** Setting `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) in env makes `browser_navigate` hang for 30s then return a misleading success string; every CDP-dependent tool then errors with `Root CDP client not initialized`. Same binary with env-LLM-keys unset (direct mode) scores 5.87. Reproducer + bisection in [`results/2026-05-26/browser-use-agent/DEEP_ANALYSIS.md`](results/2026-05-26/browser-use-agent/DEEP_ANALYSIS.md).

**One-line takeaway:** Pair Playwright (interactive) with Lightpanda (read-only). Reach for Firecrawl when you need cloud SSR at scale and your targets are publicly reachable. Treat Cloakbrowser as a research sandbox. Wait on Obscura until a Linux re-test lands.

Full per-MCP rationale and citations: [`results/recommendations.md`](results/recommendations.md). Full 8-dimension score breakdown + S1-S8 stage matrix: [`results/2026-05-27-mcp-comparison.md`](results/2026-05-27-mcp-comparison.md).

## What we actually measured

**8 weighted dimensions** (composite is a 0-10 blend, locked from the prior wave for direct comparability):

| Dimension | Weight | What it captures |
|-----------|--------:|------------------|
| Data Quality | 3× | Did the extracted JSON/structure match the source page faithfully? |
| Reliability | 3× | Did the same prompt produce the same answer across 3 retry passes? |
| Speed | 2× | Wall-clock per stage |
| Token Efficiency | 2× | Tokens consumed per task completed |
| Interaction Depth | 2× | How many of S4–S8 (form fill, upload, dropdown, screenshot) succeeded? |
| JS Rendering | 1× | Did the MCP see the client-rendered DOM, not just the SSR shell? |
| Setup Complexity | 1× | How painful was getting the MCP running at all? |
| Error Handling | 1× | When something broke, did we get a useful error or silence? |

**N/A-aware composite.** A read-only MCP (Lightpanda, Firecrawl) marked `N/A` for "fill the form" cells **drops those cells from its weighted denominator** rather than being penalised with a 0. That's why Lightpanda's 6.31 is honest, not inflated. The handler is `scoring/score_with_na.py`; the rubric is `scoring/rubric.md` (sacrosanct — byte-for-byte unchanged from the start of the wave).

**Median of 3 passes.** Every run is repeated 3× and the median is published. This surfaced agent-discovery variance (Chrome DevTools MCP ran 5.6 / 5.6 / 8.33 across passes — one pass alone found a server-side-rendering rescue trick that the other two missed). Single-shot scores would have lied.

**Frozen loopback fixtures.** Every MCP hits a byte-for-byte snapshot of the same Greenhouse + Ashby pages served from `127.0.0.1`. No live URLs, no network jitter, no "the site changed under us." Anyone with this repo can reproduce the scores: [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

## The S1–S8 stage walk

Every MCP runs the same prompt ([`prompts/stage_walk.md`](prompts/stage_walk.md)). The first three stages are read-only; the last five are interactive:

| Stage | What the MCP must do | Page type |
|------:|----------------------|-----------|
| S1 | Extract structured job data | Greenhouse (server-rendered) |
| S2 | Extract from a React SPA | Ashby (client-rendered) |
| S3 | Detect the ATS platform | both |
| S4 | Navigate to the apply form | both |
| S5 | Fill the application form with mock data | both |
| S6 | Upload a mock resume PDF | both |
| S7 | Handle React-Select dropdowns | both |
| S8 | Screenshot the filled form | both |

S1–S3 measure read-only extraction quality; S4–S8 measure interactive depth. Read-only MCPs (Lightpanda, Firecrawl) are categorically `N/A` for S4–S8 — and that's the point: don't pick a read-only specialist for a form-fill workload, and don't penalize it for being honest about its surface.

## Key findings worth your time

- **51× cold-start spread.** Lightpanda 13 ms vs Browser-Use direct 668 ms. If you're spawning MCPs per-request, this is your latency budget.
- **Cloakbrowser leads the raw score (8.33)** but is **pre-tiered SANDBOX-ONLY** by construction. Closed-source binary + cookie-touch trust model is the binding constraint, not the score. Composite alone cannot drive graduation tier.
- **Firecrawl confirms the SSR lift, refutes the SPA claim.** 9× byte-count lift on Greenhouse SSR (24 KB markdown vs Playwright's 2.6 KB structured YAML) — real. Same approach on Ashby React SPA: 203 bytes of footer chrome. Cloud LLM-extraction is the right tool for SSR-heavy targets, not a universal JS-SPA fallback.
- **Browser-Use direct mode works without an LLM key** for the deterministic S1+S2+S3+S8 subset; the `retry_with_browser_use_agent` LLM escape hatch was never invoked. Agent mode SKIPPED for `LLM_KEY_ABSENT` per the dual-row contract.
- **Headless Chromium leaks three independently fingerprintable signals** by default (`HeadlessChrome/` UA, SwiftShader WebGL, `navigator.plugins.length=0`). That's a fingerprint-resilience finding worth carrying into your stack — the deferred follow-up wave will quantify it against the live adversary set.

## Try it yourself

```bash
git clone https://github.com/pleasedodisturb/web-agent-comparison
cd web-agent-comparison

# Inspect the rubric and rules
cat scoring/rubric.md

# Read the third-party reproducibility recipe
cat docs/REPRODUCIBILITY.md

# Reproduce the Playwright calibration row (~10 min)
make bench-playwright && make score
```

The recipe in [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) walks you through prereq checking, snapshot serving, and per-MCP runs with the exact pinned binary SHA256s.

## What's coming next (the follow-up wave: G-710)

v1.0 deliberately deferred four expensive measurement axes so the headline could ship. They live in the next wave:

- **TLS fingerprint capture per MCP** (JA3/JA4) — does any of these actually pass 2025-26 bot-detection, or is "real Chrome" marketing copy?
- **Bot-detection adversary set** — Cloudflare, DataDome, Akamai Bot Manager, reCAPTCHA v2/v3
- **Cross-machine reproducibility** — MacBook parity vs the Mac Mini that ran this wave
- **Obscura Linux A/B** — re-test `--stealth` from a Linux host where `Sec-CH-UA-Platform-*` is honest, so the tier can actually move off SKIP
- **General-purpose fixture expansion** — beyond the job-application use case, into search, e-commerce, content extraction, multi-page navigation

Follow-up wave anchor: [G-710](https://linear.app/abandoned-yachts/issue/G-710). v1.0 umbrella: [G-703](https://linear.app/abandoned-yachts/issue/G-703).

## How the repo is laid out

```
.mcp.json          Project-scoped MCP server registry (the 7-candidate roster)
bench/             Harness + scoring + report builders (Python 3.12, uv-locked)
docs/              Reproducibility recipe + run-environment docs
fixtures/          Mock data, resume PDF, loopback snapshot fixtures
prompts/           Locked S1–S8 stage-walk prompt
scoring/           Locked 8-dimension rubric + N/A-aware scoring engine
scripts/           Test orchestration + harness CLI
results/           Per-wave dated subdirectories with scored evidence
```

`.mcp.json` is project-scoped (not user-scoped) so the 7 MCPs only spawn when Claude opens this repo. That isolation matters — the same trick keeps your other Claude sessions free of rocket-icon dock pollution.

## Why this exists

Stage 1 of a 3-stage pipeline:

1. **This repo (public)** — score candidate browser MCPs on standardized fixtures
2. **`terminal-craft` (private)** — package the winners as a production toolkit
3. **Kestrel + Eyas (private)** — wire the toolkit into job-hunting agents

The repo's job is to produce defensible, third-party-verifiable graduation tiers so Stage 2 isn't picking tooling based on vendor marketing. The graduation gate is `results/recommendations.md`. v1.0 shipped it.

---

**Historical wave (preserved for traceability):** the 2026-03-31 app-level comparison of 5 application-layer agents (Playwright MCP 9.07, WebFetch 7.87, Agent Browser 7.60, Lightpanda 5.87, BrowserMCP 5.53) lives at [`results/2026-03-31_run.md`](results/2026-03-31_run.md). Same rubric, different candidate set (apps, not MCP-layer servers).
