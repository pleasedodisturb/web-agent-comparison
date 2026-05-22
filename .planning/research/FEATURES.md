# Feature Research — Comparison Report Contents

**Domain:** Public, reproducible benchmark report for 7 browser-automation MCP servers
**Researched:** 2026-05-22
**Confidence:** HIGH (rubric, stages, prior wave are locked; per-MCP angles confirmed against current 2026-05 docs)

## Scope of "Features" in This Document

The "product" here is the **comparison report** (`results/2026-05-XX-mcp-comparison.md` + `results/recommendations.md`), not a piece of software. "Features" therefore means: **measurement axes, per-MCP capability checks, sections, and artifacts that the report must / should / must-not contain.** The locked 8-dimension rubric (Data Quality 3x, Reliability 3x, Speed 2x, Token Efficiency 2x, Interaction Depth 2x, JS Rendering 1x, Setup Complexity 1x, Error Handling 1x) is the **scoring core**; everything below sits *alongside* it as either inputs to those scores or cross-cutting evidence the reader needs to trust the result.

---

## Feature Landscape

### Table Stakes (Report Is Not Credible Without These)

Missing any of these = a reader cannot trust, reproduce, or use the comparison. Non-negotiable for shipping.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Per-dimension score table (8 dims × 7 MCPs)** | The rubric IS the comparison. Reader's first lookup. | LOW | Mirror table format of `results/2026-03-31_run.md` §"Scoring Comparison" — direct comparability with prior wave. Use the locked rubric exactly. |
| **Weighted composite (0-10) per MCP** | One-number summary readers scan first | LOW | Already in `scoring/score.py`. Run unchanged. |
| **Final ranked list with "Best For" one-liner** | Decision-support — most readers stop here | LOW | Same shape as 2026-03-31 §"Final Ranking" table. |
| **Stage-by-stage matrix (S1-S8 × 7 MCPs, PASS/FAIL/PARTIAL/UNTESTED)** | Composite scores hide which stages drove the result | LOW | Same shape as 2026-03-31 §"Stage Results Matrix". UNTESTED must be marked, not silently omitted. |
| **Version pinning per MCP (binary version + install command)** | Without versions, the report is not reproducible | LOW | Already in HANDOFF.md table; lift directly. Include npm `@version`, uv tool version, binary SHA where available. |
| **Methodology section (machine spec, Claude Code version, model, date, target URLs)** | Reproducibility floor — third party needs all of this | LOW | Same shape as 2026-03-31 §"Test Environment". Add: Mac model, RAM, OS version, network conditions. |
| **Raw evidence files per MCP per stage** | Score is only as trustworthy as the underlying capture | MED | Already established in 2026-03-31 (yml/png/md/txt artifacts in `results/`). One artifact per (MCP × stage) where applicable. |
| **`scores.json` machine-readable output** | Programmatic consumers + future runs need diffable data | LOW | Already produced by `scoring/score.py`. Commit alongside the report. |
| **Per-MCP "Deep Analysis" section (Strengths / Weaknesses / Verdict)** | Composite scores lie when one dimension dominates — qualitative context is required | MED | Mirror 2026-03-31 §"Deep Analysis by Agent". 3-6 bullets per side, plus 1-paragraph verdict. **Verdict is task-fit, not vibes.** |
| **Explicit "graduate to Stage 2 toolkit" recommendation** | This IS the Core Value per `.planning/PROJECT.md`. If this is absent, Stage 2 is blocked. | LOW | Lives in `results/recommendations.md`. Ranked list with rationale; "primary / secondary / sandbox-only / skip" tiers. |
| **Decision framework (which MCP for which task type)** | Readers need a routing answer, not just scores | LOW | Mirror 2026-03-31 §"Decision Framework" pseudocode block. |
| **Cold-start latency per MCP (spawn → first usable tool call)** | Explicitly in `.planning/PROJECT.md` Active requirements; lightpanda is 1.8s, others unknown | MED | Already captured for lightpanda. Measure: time from `claude` open → first MCP tool call returns. Repeat 3x, median. |
| **DOM coverage per MCP across S1-S8** | "Which pages does each MCP successfully extract from" — explicitly in PROJECT.md Active | LOW | Falls out of the stage matrix once stages run. |
| **Token efficiency measurement (KB or tokens consumed per task)** | Already a rubric dimension (Token Efficiency 2x) — needs raw numbers | LOW | Measure per stage: input/output bytes returned by each MCP tool call. WebFetch was 20× more efficient than snapshots last wave — confirm whether snapshot MCPs are getting closer. |
| **Partial-run disclosure (Firecrawl 6/7 if no API key)** | Per PROJECT.md constraints, partial scoring is acceptable; must be **flagged**, not hidden | LOW | If Firecrawl is skipped, the report must say so in the executive summary, the matrix (UNTESTED row), and the recommendations. |
| **Sandbox-only marker on cloakbrowser** | Safety / policy — readers must not point it at authenticated sessions | LOW | Big bold callout in cloakbrowser's section and in the recommendations matrix. |
| **Repro instructions (how a third party clones + runs)** | "Reproducibility validated" is an explicit PROJECT.md AC | MED | New section. Steps: clone, install MCPs (commands from HANDOFF.md), set `FIRECRAWL_API_KEY` (or accept partial run), open Claude in repo, run test harness, regenerate `scores.json`. |
| **Linear traceability footer (G-703 + per-MCP sub-tickets)** | User-policy: every commit references a ticket; report should too | LOW | One-line footer linking the umbrella + per-MCP sub-tickets. |

### Differentiators (Make THIS Comparison More Useful Than Generic MCP Benchmarks)

These are not strictly required to ship, but they're what separates this report from the 200 "I tried 5 browser MCPs and here's my hot take" blog posts. Each one is **defensible because it's measured**, not asserted.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **TLS fingerprint (JA3 + JA4 + JA4T) captured per MCP** | 2026 industry consensus: JA4+ is at Cloudflare/AWS/VirusTotal and AUC 0.998 for bot detection per recent paper. Most MCP comparisons hand-wave "stealth"; we publish the actual fingerprints. | MED | Capture against `tls.peet.ws/api/all` or `scrapfly.io/web-scraping-tools/ja3-fingerprint`. Run once per MCP, log JA3/JA4/JA4T strings + Sec-CH-UA headers. Confirms or refutes the "only real Chrome passes" claim empirically. |
| **Bot-detection resilience matrix (Cloudflare / DataDome / Akamai / reCAPTCHA v2 / reCAPTCHA v3 / FingerprintJS / BrowserScan)** | Explicit PROJECT.md Active requirement. CloakBrowser claims 30/30 tests passed — verify against the same test set the others face. | HIGH | Use public detector pages: `bot.sannysoft.com`, `browserscan.net/bot-detection`, `fingerprint.com/demo`, `arh.antoinevastel.com/bots/areyouheadless`, Cloudflare's `nowsecure.nl`, `creepjs` from `abrahamjuliot.github.io/creepjs`. Capture screenshot + score per detector × MCP. Matrix output. |
| **1hr stability run per MCP** | PROJECT.md Active requirement; previously failed silently (BrowserMCP disconnect mid-test in 2026-03 wave). | MED | Loop S1+S2 for 1 hour per MCP, count crashes / restarts / silent failures. Pass = zero process death; partial = recovered ≥1x; fail = died and stayed dead. |
| **Tool-call count per stage per MCP** | The Playwright `browser_fill_form` "6 fields in 1 call" claim is the single most-cited differentiator from the last wave. Make it empirical, not anecdotal. | LOW | Log every tool call during S5 (Fill Form) with field count. Output: stage S5 took N calls on MCP X. The 2026-05 Microsoft data shows ~16× speedup from batch-fill skipping network-idle waits — record latency too. |
| **Tool-surface inventory (count + categorization)** | Playwright = 28 tools, BrowserMCP = 12 tools last wave. Readers want to know what each MCP can even attempt. | LOW | Capture `tools/list` JSON-RPC response per MCP. Categorize: navigate / interact / extract / debug / network / file. Publish as appendix table. |
| **Reproducibility manifest (lockfile of versions + checksums + env)** | "Methodology runnable by a third party" is an explicit AC. Pinned manifest = months from now, someone can replay. | MED | Single JSON: `{mcp: {name, version, command, sha256_of_binary, npm_lock_hash}}`. One file; published with results. |
| **Memory footprint per MCP (RSS at idle + RSS during S1)** | Mac Mini constraint (24GB RAM) per browser-tools.md — Obscura's 30MB/tab is its killer feature for parallel agents. Quantify. | LOW | `ps` snapshot every 5s during stage execution; report idle + peak. |
| **DevTools-only capability check (chrome-devtools)** | chrome-devtools MCP is unique in exposing network panel, performance traces, console capture. Most comparisons miss this. | MED | Add a 9th "DevTools probe" stage *only* for chrome-devtools: capture (a) network waterfall for S1, (b) performance trace for S1, (c) console messages during S5. Score is binary "exposed / didn't expose" — not part of the 8-dim composite, but a callout in chrome-devtools's deep-analysis section. |
| **Cloud-vs-local axis annotation per MCP** | Firecrawl is cloud-only; everything else is local. Pricing, latency, data-privacy, API-key dependency differ. Reader needs this dimension before picking. | LOW | One column in the summary matrix: `local-binary / cloud-API / local-Chrome / cloud-fallback`. |
| **LLM-extraction-layer scoring (Firecrawl + browser-use)** | Two MCPs add an LLM extraction layer on top of raw page content. That's a force-multiplier on Data Quality at a token cost. Quantify both sides. | MED | For Firecrawl + browser-use, record (a) Data Quality score with extraction enabled vs raw, (b) extra latency, (c) extra tokens. Asymmetric advantage if it works. |
| **Headed-vs-headless fingerprint delta** | browser-tools.md notes headless Playwright leaks `HeadlessChrome` UA + SwiftShader + zero plugins. Quantify which MCPs default to headless and whether they leak. | MED | For each MCP that drives Chromium, capture UA + WebGL renderer + `navigator.plugins.length` once. Annotate the bot-detection matrix. |
| **Failure-mode taxonomy** | "Failed" is uninformative. Was it: crashed, hung, returned empty, returned wrong data, rate-limited, blocked, MCP transport error? | LOW | When a stage fails, classify into the taxonomy. Aggregates into Error Handling (1x) rubric score and surfaces patterns. |
| **Per-MCP "what's interesting to evaluate" angle** (see below) | Forces each MCP to be evaluated on its actual differentiating claim, not just the generic rubric | MED | See dedicated section below — one focused experiment per MCP. |
| **Side-by-side "S5 Fill Form" deep dive** | The single most-revealing stage. Show all 7 MCPs side-by-side: tool calls, fields covered, fallbacks needed, total tokens, total seconds. | MED | One table, seven columns, lots of detail. The reader's best single-page summary of capability differences. |
| **2026-03 → 2026-05 comparison overlay** | Prior wave scored 5 *agents*; this wave scores 7 *MCPs*. The 3 overlapping technologies (Playwright, Lightpanda, BrowserMCP-ish via cloakbrowser-as-stealth-Chromium) deserve a "what changed" callout. | LOW | Small subsection: "Playwright MCP scored 9.07 in 2026-03; new score X.XX in 2026-05. Delta driven by Y." |
| **Negative-result honesty section** | What didn't work, what we couldn't measure, what we punted on. Most blog comparisons hide this. | LOW | "Known gaps" section: BrowserMCP not in this wave, obscura engine arch mismatch on Linux container (if relevant), Firecrawl partial-run if no key, cloakbrowser stealth not exercised by harness (sandbox-only). |

### Anti-Features (Deliberately NOT in the Report)

Each anti-feature has a reason — this is not "out of scope" laziness, this is "would actively harm the report."

| Feature | Why Tempting | Why We Don't Include It | Alternative |
|---------|--------------|-------------------------|-------------|
| **Framework recommendations the reader didn't ask for** ("you should use Stagehand instead") | Easy to seem helpful | This report is about the 7 candidates; off-list recommendations dilute focus and break reproducibility (no scores to back them). | If a non-candidate is worth flagging, put it in a single "Future waves to consider" appendix line — no advocacy. |
| **Qualitative "I liked this one" / vibes-based ranking** | Easy filler | Indistinguishable from a hot-take blog. The whole point is reproducible scores. | Every claim ties back to a score, a tool call count, an artifact, or a measured number. |
| **Marketing-style executive summary** ("Revolutionary AI-native browser automation!") | Sounds confident | Loses reader trust; tells them nothing. Prior wave's exec summary worked because it named winners + losers in one sentence each. | Two paragraphs max: winner, surprise finding, biggest disappointment. Concrete. |
| **Training-data / "what do I know" inferences as findings** | Faster than measuring | Training data is 6-18 months stale per global research discipline; for a 2026 benchmark of mid-2026 MCPs, training-only claims are almost always wrong. | Mark anything not measured this wave as "not measured" or move to "Open questions." |
| **Cross-MCP combo recommendations as primary content** | Last wave had a nice "WebFetch + Playwright + BrowserMCP" combo | Stage 2 (terminal-craft) is where combos get designed. Stage 1 evaluates each MCP **alone** on the rubric. Combos that emerge naturally can be noted in recommendations, not headlined. | One small "Optimal combo" subsection at the end — like 2026-03 — but Stage 2 is where it lives for real. |
| **Per-MCP sales pitch / "key strengths" without "key weaknesses"** | Pleasant tone | Single-sided summaries are noise. Every MCP gets a paired strengths/weaknesses pair. | Always paired, always concrete (with stage references). |
| **Speculation about MCP roadmaps / future features** | "browser-use might add X soon" | Unverifiable, dates the report instantly, biases the verdict. | "As of [version X on date Y]" framing. If a roadmap matters, link to the issue. |
| **Authenticated-session testing (LinkedIn, Greenhouse logged-in, banking)** | "Real-world" feel | Global policy + cloakbrowser sandbox rule. Explicit PROJECT.md Out of Scope. | Public fixtures only — Greenhouse + Ashby anon. |
| **Benchmark against application-level agents (Skyvern, Manus, Comet)** | "Apples to apples with last wave" | Different layer; explicit PROJECT.md Out of Scope. Last wave's results stand as historical reference, not as direct competitors. | Single sentence cross-reference to 2026-03-31_run.md; do not re-score. |
| **Building shared abstractions over the MCPs to "normalize" comparison** | "Fair comparison" instinct | That's literally Stage 2's job. Doing it in Stage 1 contaminates scores with abstraction-design choices. Explicit PROJECT.md Out of Scope. | Test each MCP on its native tool surface. Differences in ergonomics ARE the signal. |
| **Generic "MCPs are great!" advocacy** | Easy to write | Reader is here for picks, not for an MCP introduction. | One-sentence framing at the top; rest is data. |
| **Star counts, "popularity" rankings, GitHub badges** | Decoration | Popularity ≠ fitness for production agent use. Misleads readers. | If a project's maintenance velocity matters (e.g. browser-use's daily commits), include it as a single "last commit / release cadence" fact in the deep-analysis section. |
| **Reading the README to score the MCP** | Faster than testing | The whole point is empirical. If the README says it does X and S5 shows it doesn't, the rubric score reflects S5, not the README. | Tool-call logs and artifacts are ground truth. |
| **Scores under partial data presented as authoritative** | Avoids the awkwardness of "we didn't test this" | Misleads the reader. Six dimensions out of eight with confidence "low" is worse than two dimensions with confidence "high". | If a stage is UNTESTED, mark it; if a dimension lacks evidence, drop it from the composite for that MCP with a footnote. |
| **Cloakbrowser pointed at authenticated targets to "really stress-test it"** | Tempting for stealth claims | Explicit PROJECT.md + global policy violation. Closed-source binary touches cookies. | Stealth claims tested against public detector pages only. |

---

## Per-MCP "What's Interesting to Evaluate" Angles

This is the section that elevates the report. Each MCP has **one specific thing the comparison should empirically nail down**, beyond the generic rubric. These angles are what make the test-harness designer's job concrete.

### playwright (@playwright/mcp@0.0.75)
**The interesting claim:** `browser_fill_form` batch-fills N fields in ONE tool call vs other MCPs needing N calls.
**What to measure (and log):**
- For S5, log every `tools/call` JSON-RPC request. Count: total calls, fields filled per call, total wall-clock seconds.
- Compare against the same stage on every other MCP that supports filling. Publish as a 7-row table.
- **Microsoft's own published claim (2026):** batch-fill is ~16× faster than per-field due to skipping network-idle detection. Verify or refute against the Greenhouse + Ashby fixtures.
- Side-effect to capture: does `browser_fill_form` handle React Select comboboxes natively in this version (the 2026-03 wave had to fall back to `browser_run_code`)?
**Pass criterion:** "Playwright batches" is either supported by call-count evidence or downgraded.

### browser-use (`browser-use --mcp`, v0.12.7)
**The interesting claim:** "Direct mode" works without the user's own LLM API key when invoked from Claude Code, because it uses the host LLM.
**What to measure:**
- Launch with NO `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / etc. in env. Does S1 succeed? S5?
- Inspect the MCP server stderr / logs at startup — does it complain about missing keys?
- Compare tool surface to `mcp-browser-use` (the alternative that explicitly uses host LLM) — is this actually two different products marketed similarly?
- Token cost: browser-use is reputed to be verbose. Quantify input+output tokens per stage and compare to Playwright.
**Pass criterion:** The "no LLM key needed" claim is either confirmed (works without keys) or refuted (silently uses internal model / fails). HANDOFF.md says "direct mode no-LLM-key"; PROJECT.md needs the empirical answer.
**Known issue to flag:** 2026-05 testbench had transport mismatch (initialize timeout at 60s) per browser-tools.md. If this reproduces, score 0 and document, don't hide.

### chrome-devtools (chrome-devtools-mcp v1.0.1, Chrome team official)
**The interesting claim:** DevTools panel access surfaces signals no other MCP can — network waterfall, performance traces, console messages with source-mapped stacks.
**What to measure:**
- Run a "DevTools probe" mini-suite as a 9th stage (chrome-devtools only — not scored on rubric):
  - `list_network_requests` / `get_network_request` during S1 — record N requests, total bytes, slowest request.
  - `performance_start_trace` / `performance_stop_trace` / `performance_analyze_insight` during S1 — capture LCP, TBT, Core Web Vitals.
  - `list_console_messages` during S5 — capture any React Select warnings / errors.
- Publish the captured artifacts (trace.json, network.json) alongside other evidence.
- Verify the 26-tool surface (per Continue docs) actually exposes all 6 categories: Performance / Input / Navigation / Debugging / Network / Emulation.
**Pass criterion:** Concrete artifacts the other 6 MCPs structurally cannot produce. This is chrome-devtools's moat; the report should show it.
**Known quirk to flag:** Stderr `exposes content of the browser instance to the MCP client` warning on every launch — cost 1 stability point in 2026-05 testbench. Not a failure, but worth a footnote.

### lightpanda (v0.3.0)
**The interesting claim (under audit):** "React-blind" — cannot render SPAs (returned 0 bytes for Ashby in 2026-03).
**What to measure:**
- S2 (Ashby SPA) on current v0.3.0 with current Zig JS runtime. Does it still return 0 bytes? Current research (2026 sources, `roundproxies.com`, `webfuse.com`) says "compatibility tax shows up as silent rendering failures on SPAs whose hydration paths touch unimplemented APIs" — softer than 2026-03's "fatal."
- If S2 partially works, capture which React APIs are now implemented vs missing (use chrome-devtools-mcp side-by-side on the same URL for the diff).
- Cold-start: PROJECT.md says 1.8s. Confirm; this is a differentiator for high-volume scraping.
- Tool surface: lightpanda's MCP mode (`lightpanda mcp`) was untested in 2026-03. Capture `tools/list` — is it just `fetch`, or more?
- Memory: ~30MB/tab claim (browser-tools.md) — confirm with `ps` during stability run.
**Pass criterion:** Empirically resolve "React-blind 2026-03 → ??? in 2026-05" — either confirm regression-or-stagnation or report measured progress.

### obscura (obscura-mcp v0.1.4-2, Rust+V8)
**The interesting claim:** CDP-direct (not Playwright-on-CDP) gives lower overhead + lighter RAM than Chromium MCPs while keeping full JS rendering. Plus built-in stealth + 3,520-domain blocklist.
**What to measure:**
- **First:** confirm `obscura-mcp install` ran and the engine downloaded (HANDOFF.md says "engine pending"). If install fails on macOS arm64 today, that's a finding — capture the error.
- Memory: ~30MB RAM/tab claim — confirm with `ps` during S1. Compare to Playwright (~300MB).
- Stealth: run the bot-detection resilience matrix (see Differentiators). Compare against Playwright (no stealth) and CloakBrowser (heavy stealth) — where does Obscura sit?
- CDP gaps: browser-tools.md notes "in-page fetch silent-fail" as a known issue. Probe with an XHR-heavy stage; report.
- **Do NOT enable `--stealth` on macOS** — Sec-CH-UA-Platform-* leaks per global policy. Flag this prominently if the MCP exposes the option.
**Pass criterion:** Empirical RAM number, empirical stealth score, empirical CDP-fetch behaviour. Cleared-eye comparison of "Rust-CDP-direct vs Playwright-on-CDP" tradeoffs.

### firecrawl (firecrawl-mcp v3.17.0)
**The interesting claim:** Cloud LLM-extraction layer makes Data Quality (3x rubric weight) jump well above what raw-page MCPs achieve, at the cost of latency, money, and API-key dependency.
**What to measure:**
- If `FIRECRAWL_API_KEY` is present: run S1 + S2 + S3 (read-only) with default markdown extraction AND with structured-schema extraction. Score Data Quality both ways.
- Latency: time S1 round-trip (Firecrawl is cloud — expect higher network latency than local MCPs). Independent benchmark says ~7s average; verify.
- Token efficiency: Firecrawl returns clean markdown — measure bytes vs Playwright accessibility snapshot vs Lightpanda raw markdown. Last wave: WebFetch was 20× more efficient than snapshots. Where does Firecrawl land?
- Reliability claim: "96% success on JS-heavy sites" — does S2 (Ashby SPA) succeed without local browser? That's the killer feature if true.
- Interactive stages (S4-S8): Firecrawl is read-only. Mark UNTESTED / NOT-APPLICABLE; do not score Interaction Depth as 0 vs other MCPs because that would punish a tool used for what it's not (instead: include the dimension but flag it).
- **If no API key:** Skip cleanly. Report as 6/7 partial run in the executive summary.
**Pass criterion:** Quantified cloud-vs-local tradeoff. Reader can answer: "When is paying Firecrawl better than running Playwright?"

### cloakbrowser (cloakbrowsermcp v2.0.4)
**The interesting claim:** Source-patched Chromium passes Cloudflare Turnstile, reCAPTCHA v3 (0.9 score), FingerprintJS, BrowserScan, 30/30 tests — WITHOUT solving captchas (it prevents them appearing).
**What to measure:**
- Run the full bot-detection resilience matrix (see Differentiators) — this is the MCP where the matrix matters most. Targets: `bot.sannysoft.com`, `browserscan.net`, `fingerprint.com/demo`, `arh.antoinevastel.com`, `creepjs`, public Cloudflare-protected sites (`nowsecure.nl`).
- Compare scores to Playwright (no stealth) and Obscura (some stealth) on the same detector set. Publish a detector × MCP matrix.
- TLS fingerprint: capture JA3/JA4/JA4T. The claim "passes Cloudflare" implies the TLS fingerprint matches real Chrome. Verify with `tls.peet.ws`.
- Source-level patch list: claims 58 C++ patches (canvas, WebGL, audio, fonts, GPU, automation, CDP input). Cannot verify (closed source) — but can verify the outputs: `navigator.webdriver`, `window.chrome.runtime`, plugins.length, WebGL renderer, canvas hash stability per session.
- **Sandbox-only enforcement:** Every report mention of CloakBrowser must include the sandbox-only warning. Score on public fixtures + public detector pages. Never authenticated sessions.
**Pass criterion:** Empirical "passes / fails" rows for each bot-detection service, with screenshots. The 30/30 claim is testable; this report tests it.

---

## Feature Dependencies

```
Per-MCP scoring (8-dim rubric)
    └──requires──> Stage execution (S1-S8 × 7 MCPs)
                       └──requires──> Mock data + Mock resume + Greenhouse + Ashby fixtures (locked)
                       └──requires──> Working MCP install (HANDOFF.md table) + version pinning

Cold-start latency measurement
    └──requires──> Clean Claude Code session per MCP (no warm process)

Bot-detection resilience matrix
    └──requires──> Per-MCP ability to navigate to a public detector URL (= S1-equivalent)
    └──enhances──> Reliability score (3x) — failures here flow into Reliability
    └──enhances──> JS Rendering score (1x) — detectors that need JS execution reveal rendering gaps
    └──enhances──> Stealth claim adjudication (per-MCP Verdict)

TLS fingerprint capture
    └──requires──> Bot-detection matrix infrastructure (same target hosting)
    └──enhances──> Per-MCP Verdict (informs "will this pass Cloudflare in production")

Tool-call count per stage
    └──requires──> MCP server stderr/stdout logging during stage execution
    └──enhances──> Speed score (2x) — fewer calls = lower latency at fixed network
    └──enhances──> Token Efficiency score (2x) — fewer calls = less protocol overhead

1hr stability run
    └──requires──> Stage execution working end-to-end first
    └──enhances──> Reliability score (3x) — recovery / crash data
    └──enhances──> Error Handling score (1x) — graceful degradation evidence

Repro instructions
    └──requires──> Reproducibility manifest (version lockfile)
    └──requires──> All install commands captured per MCP (already in HANDOFF.md)

"Graduate to Stage 2" recommendation
    └──requires──> Per-MCP Verdict completed
    └──requires──> Composite scores finalized
    └──requires──> Bot-detection matrix (for "where will this break in production")
    └──blocks──> Stage 2 (terminal-craft) — explicit pipeline gate per PROJECT.md
```

### Dependency Notes

- **Bot-detection matrix is a force multiplier:** running it captures evidence for Reliability, JS Rendering, AND each MCP's stealth verdict simultaneously. Build it once, score multiple dimensions.
- **TLS fingerprint capture piggybacks on bot-detection infrastructure:** same target hosts (`tls.peet.ws`, BrowserScan) — no extra setup beyond extracting the JA3/JA4 from response JSON.
- **Tool-call logging needs to be set up before ANY stage runs.** Retrofitting is painful; design the harness to capture JSON-RPC traffic from the start.
- **Recommendations block Stage 2.** This is the single most important downstream consumer. If the "graduate" verdict is unclear or absent, terminal-craft (Stage 2) cannot begin per the PROJECT.md pipeline gating.

---

## MVP Definition

### Launch With (v1 = the Stage 1 ship gate)

Minimum the report needs to satisfy the explicit PROJECT.md Active requirements AND be credible to a third-party reader.

- [ ] **Full 8-dim scoring table (7 MCPs × 8 dims + composite)** — the rubric core
- [ ] **Stage matrix (S1-S8 × 7 MCPs)** — pass/fail/partial evidence
- [ ] **Per-MCP deep analysis (strengths / weaknesses / verdict)** — qualitative context
- [ ] **Per-MCP "interesting angle" finding** — the differentiating empirical check
- [ ] **Cold-start latency per MCP** — explicit PROJECT.md Active
- [ ] **Bot-detection resilience matrix** — explicit PROJECT.md Active (Cloudflare/DataDome/Akamai/reCAPTCHA)
- [ ] **TLS fingerprint per MCP (JA3 + JA4)** — explicit PROJECT.md Active; confirms/refutes "only real Chrome passes" claim
- [ ] **Token efficiency numbers per task** — explicit PROJECT.md Active
- [ ] **1hr stability run per MCP** — explicit PROJECT.md Active
- [ ] **Methodology section (machine, model, date, fixtures, repro steps)**
- [ ] **Reproducibility manifest (version lockfile)**
- [ ] **`results/2026-05-XX-mcp-comparison.md` published** — explicit PROJECT.md Active
- [ ] **`results/recommendations.md` with graduate-to-Stage-2 tiers** — explicit PROJECT.md Active
- [ ] **`scores.json` machine-readable output**
- [ ] **README updated with methodology + headline verdict** — explicit PROJECT.md Active
- [ ] **Sandbox-only callouts for cloakbrowser** — safety floor
- [ ] **Partial-run disclosure if Firecrawl key absent** — per PROJECT.md constraints

### Add After Validation (v1.x — same report, follow-up update)

Trigger: after v1 ships and gets read. Add when reader questions or Stage 2 design surfaces a gap.

- [ ] **Detailed S5 (Fill Form) side-by-side deep dive** — adds polish, expands the most-revealing stage
- [ ] **2026-03 → 2026-05 overlay** — compares overlapping technologies across waves
- [ ] **Memory footprint snapshots** — adds context for Mac Mini RAM-constrained users
- [ ] **DevTools probe artifacts (chrome-devtools)** — strengthens chrome-devtools verdict; needed if Stage 2 wants debug tooling
- [ ] **LLM-extraction-layer split scoring (Firecrawl + browser-use with/without)** — only worth doing if Stage 2 considers cloud-extraction
- [ ] **Headed-vs-headless fingerprint delta** — only if bot-detection matrix surfaces tooling Q's

### Future Consideration (v2 = next wave)

Defer to a follow-up comparison wave. Adding now bloats the report.

- [ ] **BrowserMCP scored alongside the 7** — explicit PROJECT.md Out of Scope this wave; revisit if Stage 2 wants authenticated targets
- [ ] **Skyvern / Stagehand / Comet** — explicit Out of Scope (different layer)
- [ ] **Workday / Lever / SmartRecruiters fixture expansion** — new stages; Lever is currently 404 anyway
- [ ] **Authenticated-flow testing on test accounts** — needs sandbox infra; safety risk
- [ ] **Long-running 24hr stability** — current 1hr is the floor; only extend if Stage 2 surfaces stability questions

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 8-dim scoring table (locked rubric) | HIGH | LOW | P1 |
| Stage matrix S1-S8 × 7 MCPs | HIGH | MED | P1 |
| Per-MCP deep analysis | HIGH | MED | P1 |
| Per-MCP "interesting angle" findings | HIGH | MED | P1 |
| Recommendations / graduate-to-toolkit | HIGH | LOW | P1 |
| Cold-start latency | HIGH | MED | P1 |
| Bot-detection resilience matrix | HIGH | HIGH | P1 |
| TLS fingerprint capture | HIGH | MED | P1 |
| 1hr stability run | HIGH | MED | P1 |
| Token efficiency numbers | HIGH | LOW | P1 |
| Tool-call count per stage | HIGH | LOW | P1 |
| Reproducibility manifest | HIGH | MED | P1 |
| Repro instructions section | HIGH | MED | P1 |
| Methodology section | HIGH | LOW | P1 |
| Tool-surface inventory | MED | LOW | P2 |
| Memory footprint snapshots | MED | LOW | P2 |
| DevTools probe (chrome-devtools) | MED | MED | P2 |
| LLM-extraction split scoring | MED | MED | P2 |
| S5 side-by-side deep dive | MED | MED | P2 |
| 2026-03 → 2026-05 overlay | MED | LOW | P2 |
| Failure-mode taxonomy | MED | LOW | P2 |
| Headed-vs-headless fingerprint delta | LOW | MED | P3 |
| Cross-MCP optimal-combo recommendations | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for Stage 1 ship (= report publication)
- P2: Should add when possible; not blocking ship
- P3: Nice to have, defer to v1.x or v2

---

## Competitor Feature Analysis

"Competitors" here = other published browser-MCP / browser-agent comparisons. What do they include, what do we add?

| Feature | Generic blog "I tried 5 MCPs" posts | 2026-05 sandboxed testbench (G-688) | 2026-03 web-agent-comparison wave | This wave (target) |
|---------|--------------------------------------|--------------------------------------|------------------------------------|---------------------|
| Per-dimension rubric | Rarely | 5-dim (different rubric) | 8-dim (this rubric) | 8-dim (same rubric — locked) |
| Stage-by-stage matrix | No | Limited (7 tasks) | Yes (S1-S8) | Yes (S1-S8) — same fixtures |
| Version pinning | Often missing | Yes | Yes | Yes (formalized into manifest) |
| Cold-start latency | Sometimes | Yes (one MCP) | No | **Yes — all 7** |
| TLS fingerprint per MCP | Almost never | No | No | **Yes (new this wave)** |
| Bot-detection matrix | Rare; usually one detector | No | No (different scope) | **Yes — full matrix (new)** |
| 1hr stability | No | No | No | **Yes (new this wave)** |
| Tool-call count empirics | No | No | Anecdotal | **Yes — logged** |
| Reproducibility manifest | No | No | Partial | **Yes — JSON lockfile** |
| Per-MCP "interesting angle" | Sometimes (single-MCP focus) | No | Yes (per agent) | **Yes — formalized** |
| Sandbox-only safety callouts | No | Yes | N/A | **Yes (cloakbrowser)** |
| Graduate-to-toolkit verdict | No | No (different repo) | No (different stage) | **Yes — pipeline-aware** |
| LLM-extraction split scoring | Rare | No | No | **Yes (Firecrawl + browser-use)** |

**Where this wave is uniquely useful:**
1. TLS fingerprint capture is essentially absent from public MCP comparisons.
2. Bot-detection resilience matrix at this granularity (7 MCPs × ~6 detectors) is unique.
3. Reproducibility manifest + repro instructions make this the first MCP comparison a third party can actually replay.
4. Pipeline-aware verdict (graduate-to-toolkit) integrates the report into a real production-tooling decision, not just a popularity contest.

---

## Sources

- `/Users/pleasedodisturb/Projects/web-agent-comparison/.planning/PROJECT.md` — locked scope, Active requirements, decisions (HIGH)
- `/Users/pleasedodisturb/Projects/web-agent-comparison/HANDOFF.md` — pipeline framing, install commands, version pinning (HIGH)
- `/Users/pleasedodisturb/Projects/web-agent-comparison/scoring/rubric.md` — locked 8-dim rubric (HIGH)
- `/Users/pleasedodisturb/Projects/web-agent-comparison/.mcp.json` — exact MCP commands committed for repro (HIGH)
- `/Users/pleasedodisturb/Projects/web-agent-comparison/results/2026-03-31_run.md` — report shape to mirror, prior wave findings (HIGH)
- `/Users/pleasedodisturb/.claude/docs/browser-tools.md` — 2026-05 testbench findings, current ranking, known gotchas per MCP (HIGH)
- [Playwright MCP Forms tool reference](https://playwright.dev/mcp/tools/forms) — confirms `browser_fill_form` batch-fill API (HIGH)
- [Playwright Issue #39437 — batch API](https://github.com/microsoft/playwright/issues/39437) — Microsoft's ~16× speedup claim from skipping network-idle (HIGH)
- [browser-use MCP docs](https://docs.browser-use.com/open-source/customize/integrations/mcp-server) — direct-mode invocation; "requires your own LLM API keys" confirmation (HIGH)
- [chrome-devtools-mcp tool reference](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md) — 26 tools across 6 categories (HIGH)
- [Chrome DevTools MCP — Chrome for Developers blog](https://developer.chrome.com/blog/chrome-devtools-mcp) — official Chrome team product framing (HIGH)
- [Continue docs: chrome-devtools-mcp performance cookbook](https://docs.continue.dev/guides/chrome-devtools-mcp-performance) — `performance_start_trace` / `list_network_requests` confirmed (HIGH)
- [obscura-mcp on Glama](https://glama.ai/mcp/servers/Metadrama/obscura-mcp) — Rust-CDP-direct, ~30MB RAM, install command (MED)
- [Obscura GitHub (h4ckf0r0day/obscura)](https://github.com/h4ckf0r0day/obscura) — engine releases, arm64 macOS binary URL (MED)
- [Firecrawl MCP Server GitHub](https://github.com/firecrawl/firecrawl-mcp-server) — official MCP, cloud + self-hosted modes (HIGH)
- [Firecrawl 2026 capabilities (TokenMix blog)](https://tokenmix.ai/blog/firecrawl-mcp-server-web-scraping-via-mcp-2026) — 96% JS-site success, ~7s avg (MED)
- [CloakBrowser GitHub (CloakHQ)](https://github.com/CloakHQ/CloakBrowser) — 30/30 bot-detection tests, 58 C++ patches (HIGH)
- [CloakBrowse review (Pramod Dutta, Medium, May 2026)](https://scrolltest.medium.com/cloakbrowse-stealth-chromium-build-that-passes-14-out-of-14-bot-detection-tests-ca73fc52f5fa) — independent reCAPTCHA v3 0.9 score (MED)
- [Lightpanda vs Browser-Use vs Stagehand (Webfuse, 2026)](https://www.webfuse.com/blog/lightpanda-vs-browser-use-vs-stagehand-2026) — current Lightpanda SPA compatibility framing (MED)
- [Auth0 — Strengthening Bot Detection with JA4 Signals](https://auth0.com/blog/strengthening-bot-detection-ja4-signals/) — JA4 industry adoption (HIGH)
- [Scrapfly — JA3/JA4 TLS fingerprint tool](https://scrapfly.io/web-scraping-tools/ja3-fingerprint) — capture target for the TLS fingerprint feature (HIGH)
- [Scrapfly — Post-Quantum TLS bot detection](https://scrapfly.io/blog/posts/post-quantum-tls-bot-detection) — Akamai PQ default since 2026-01-31, relevant to "production agent" framing (MED)

---
*Feature research for: browser-MCP comparison report (Stage 1 of web-agent → terminal-craft → Kestrel/Eyas pipeline)*
*Researched: 2026-05-22*
