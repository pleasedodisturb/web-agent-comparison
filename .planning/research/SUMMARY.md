# Project Research Summary

**Project:** web-agent-comparison — Wave 2 (MCP-layer browser servers)
**Domain:** Public, reproducible benchmark / test harness (Stage 1 of 3-stage pipeline → terminal-craft → Kestrel/Eyas)
**Researched:** 2026-05-22
**Confidence:** HIGH on the 7 candidate versions + measurement tooling + prior-wave constraints; MEDIUM on bot-detection probe stability and the cross-machine reproducibility target

---

## Executive Summary

This wave benchmarks 7 MCP-layer browser servers (`playwright`, `browser-use`, `chrome-devtools`, `lightpanda`, `obscura`, `firecrawl`, `cloakbrowser`) against the locked 8-dimension rubric and locked S1-S8 Greenhouse + Ashby fixtures inherited from the 2026-03-31 app-level wave. The product is a **reproducible comparison report**, not software — its primary downstream consumer is the Stage 2 terminal-craft toolkit selection decision, which is gated on this wave's `recommendations.md`.

The recommended build is a **custom shell+Python harness** that drives one `claude --print --output-format stream-json` session per MCP with `--allowedTools "mcp__${MCP}__*,Read,Write,Bash"` (forcing each MCP to live or die on its own surface), captures per-MCP evidence to `results/<date>/<mcp>/`, and re-runs the existing unchanged `scoring/score.py` over an aggregated `scores.json`. No Docker, no devcontainer — they contaminate the cold-start and TLS-fingerprint measurements that are this wave's main differentiators. The harness is split into 4 phases: foundation (Phase 1), per-MCP scoring runs (Phase 2, parallelisable), cross-cutting measurements (Phase 3, parallel to Phase 2), and synthesis + reproducibility validation (Phase 4).

The largest risks are **measurement-fairness traps** (single-pass scoring tanks a candidate on a transient failure; cold-start hides Node module resolution; token counts mix tool-schema overhead with payload; TLS captures get attributed to the wrong process), **vendor blowback** (browser-use scored 0/15 in a prior testbench because of a *harness* bug, not the MCP), and **reproducibility decay** (Greenhouse/Ashby URLs 404 within 6 months — fixtures must be self-hosted snapshots, not live URLs). Each is solvable with discipline encoded in the harness from Phase 1, but they cannot be retrofitted in Phase 4.

---

## Key Findings

### Recommended Stack

A bespoke harness extending `scoring/score.py`, driven by `claude --print` with stream-json. Reuses the project's existing Python/shell idiom; adds the official Python MCP SDK for cold-start probing and the Anthropic SDK's free `count_tokens` for clean per-MCP token accounting.

**Core technologies:**
- **Python 3.12 + uv (0.7.x) with committed `uv.lock`** — extends existing `scoring/score.py`; bit-for-bit reproducibility via `uv sync --locked`. Avoid 3.14 (too new for MCP SDK extras).
- **Node 22 LTS + `package-lock.json`** — runtime for the 4 npm MCPs (`@playwright/mcp@0.0.75`, `chrome-devtools-mcp@1.0.1`, `obscura-mcp@0.1.4-3` ← bump one patch from handoff, `firecrawl-mcp@3.17.0`).
- **Bash 5+ orchestration via Makefile** — matches 2026-03 wave style; `make bench`, `make bench-<mcp>`, `make score`. NOT Docker / NOT devcontainer (both contaminate the metrics that matter).
- **`mcp` Python SDK 1.16.x (`mcp.client.stdio`)** — direct stdio measurement for cold-start (~30-50ms overhead vs ~300-500ms for MCP Inspector CLI).
- **Anthropic SDK `count_tokens`** — free, separate rate limit; the only clean apples-to-apples per-MCP token measurement.
- **Scrapfly `tools.scrapfly.io/api/fp/ja3?extended=1`** primary TLS-fingerprint capture, `tls.peet.ws/api/all` backup, `mitmproxy` upstream-mode local fallback.

**Verified versions to pin (re-checked live 2026-05-22):** all 7 confirmed current; `obscura-mcp` is one patch behind handoff (0.1.4-2 → 0.1.4-3); `chrome-devtools-mcp` just GA'd v1.0.x four days before research; `firecrawl-mcp` GitHub releases are dead (last v3.2.1 Sept 2025) — npm is the only source of truth; `lightpanda` has a semantic version mismatch (binary says 0.3.0 / handshake says 0.1.0) — pin nightly@2026-05-22 OR `v0.2.6`.

Full details: `.planning/research/STACK.md`.

### Expected Features

The "product" is the **comparison report** (`results/2026-05-XX-mcp-comparison.md` + `results/recommendations.md`). "Features" = measurement axes, per-MCP capability checks, sections, and artifacts.

**Must have (table stakes — report not credible without these):**
- 8-dim scoring table (7 MCPs × 8 dims + composite) + stage matrix S1-S8 × 7 MCPs
- Per-MCP "Deep Analysis" stanza (strengths / weaknesses / verdict) — composite scores lie when one dimension dominates
- Explicit "graduate to Stage 2 toolkit" recommendation with primary / secondary / sandbox-only / skip tiers — **this IS the Core Value; absence blocks Stage 2**
- Cold-start latency per MCP (explicit PROJECT.md AC) — median of ≥5 cold starts, not single-shot
- DOM coverage per MCP across S1-S8 (falls out of stage matrix)
- Token efficiency per task (rubric dimension; 2026-03 wave found 20× spread between WebFetch and snapshot MCPs)
- Bot-detection resilience matrix (Cloudflare / DataDome / Akamai / reCAPTCHA) — explicit PROJECT.md AC
- TLS fingerprint per MCP (JA3 + JA4) — explicit PROJECT.md AC; confirms/refutes the "only real Chrome passes 2026 detection" claim
- 1hr stability run per MCP — explicit PROJECT.md AC
- Methodology section + reproducibility manifest (version lockfile + machine spec + date + fixtures)
- `scores.json` machine-readable output (consumed by existing `scoring/score.py` unchanged)
- README headline verdict + sandbox-only callouts for cloakbrowser
- Partial-run disclosure if Firecrawl key absent (6/7 acceptable per PROJECT.md)

**Should have (differentiators that elevate this above generic "I tried 5 MCPs" blogs):**
- **Per-MCP "interesting angle" empirical check** (the headline differentiator — one falsifiable claim per MCP, see "Empirical Claims to Falsify" below)
- Tool-call count per stage (especially S5 fill-form; Playwright's batch-fill claim is the single most-cited differentiator from 2026-03)
- Tool-surface inventory (count + 6-category breakdown per MCP)
- LLM-extraction split scoring for Firecrawl + browser-use (with vs without)
- Memory footprint snapshots (Obscura's ~30MB/tab vs Playwright's ~300MB is its killer feature for parallel agents)
- DevTools-only probe stage (chrome-devtools only; network waterfall, performance trace, console messages — artifacts no other MCP can produce)
- Failure-mode taxonomy (crashed / hung / empty / wrong-data / rate-limited / blocked / transport-error) rather than binary FAIL
- Negative-results honesty section (what didn't work, what we punted on)
- 2026-03 → 2026-05 overlay on overlapping technologies

**Defer (anti-features — deliberately NOT in the report):**
- Framework recommendations the reader didn't ask for ("you should use Stagehand")
- Qualitative "I liked this one" / vibes-based ranking
- Cross-MCP combo recommendations as primary content (that's Stage 2's job)
- Speculation about MCP roadmaps / future features
- Authenticated-session testing on real banking/credential pages (global policy)
- Application-level agents like Skyvern/Manus/Comet (different layer; 2026-03 wave covered them)
- Building shared abstractions to "normalize" comparison (Stage 2's job; doing it here contaminates scores)
- Reading the README to score the MCP (empirical only)
- BrowserMCP (excluded this wave per PROJECT.md — different operational model)

Full details: `.planning/research/FEATURES.md`.

### Empirical Claims to Falsify (per-MCP "interesting angles")

These are the falsifiable per-MCP claims the harness must capture evidence for — they elevate the report from "scores" to "scores plus the one thing each MCP actually claims to do."

| MCP | Claim under test | Evidence to capture |
|---|---|---|
| **playwright** | `browser_fill_form` batch-fills N fields in 1 call vs N calls; ~16× faster (skips network-idle wait) | Per-stage tool-call count + wall-clock for S5 across all 7 MCPs; React Select handling on Greenhouse |
| **browser-use** | "Direct mode" works in Claude Code without user's own LLM API key | Launch with NO `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` — does S1+S5 succeed? Also re-test the 2026-05 testbench's `initialize` timeout on v0.12.7 |
| **chrome-devtools** | DevTools panel exposes signals no other MCP can (network waterfall, performance trace, console with source-mapped stacks) | 9th "DevTools probe" stage producing artifacts (`network.json`, `trace.json`, `console.json`) the other 6 MCPs structurally cannot produce |
| **lightpanda** | "React-blind" — returned 0 bytes on Ashby in 2026-03; check whether 2026-05 nightly is better/same/worse | S2 (Ashby SPA) on current nightly; if partial, capture which React APIs are now implemented (chrome-devtools side-by-side diff); cold-start (was 1.8s) |
| **obscura** | CDP-direct (not Playwright-on-CDP) gives lower overhead + ~30MB RAM vs Playwright ~300MB while keeping full JS rendering | `ps` memory snapshot during S1; bot-detection score relative to Playwright/CloakBrowser; XHR-heavy stage to probe known in-page-fetch silent-fail; **DO NOT enable `--stealth` on macOS** (Sec-CH-UA-Platform leak) |
| **firecrawl** | Cloud LLM-extraction lifts Data Quality (3x weight) above raw-page MCPs at cost of latency + tokens; "96% success on JS-heavy sites" | S1+S2+S3 with default markdown AND structured-schema extraction; latency vs local; bytes/tokens vs Playwright snapshot; mark S4-S8 N/A not 0 |
| **cloakbrowser** | Source-patched Chromium passes Cloudflare Turnstile, reCAPTCHA v3 (0.9 score), FingerprintJS, BrowserScan — 30/30 tests, no captcha solving needed | Full bot-detection matrix vs Playwright + Obscura on same detectors; JA4 cross-check vs real Chrome 128 baseline; sandbox-only enforcement in every report mention |

### Architecture Approach

**Orchestration:** one Claude Code session per MCP, walked through S1-S8 by a shared prompt, restricted to that MCP's tools only (`--allowedTools "mcp__${MCP}__*,Read,Write,Bash"`) so it cannot silently fall back to WebFetch and rescue a failing MCP. Each session's `stream-json` IS the transcript; per-MCP evidence directories are self-contained.

**Major components:**
1. **`.mcp.json` (project-scope)** — single source of truth for MCP commands; wrapper scripts read it via `jq`. Already exists.
2. **`prompts/stage_walk.md`** — the locked S1-S8 task script Claude runs against each assigned MCP.
3. **`scripts/run_mcp_session.sh <mcp>`** — drives one Claude Code session per MCP; writes `transcript.md`, `raw_stream.jsonl`, `stage_s*.{yml,md,png,txt}`, `tokens.json`.
4. **`scripts/measure_cold_start.sh <mcp>`** — wrapper that spawns the MCP binary cold, sends `initialize` + `tools/list` over stdin, records 3-segment timings (`t_resolve` / `t_spawn` / `t_first_useful`) for both cold and warm cache; median of 5.
5. **`scripts/capture_tls.sh <mcp>`** — drives the MCP to fetch the Scrapfly fingerprint endpoint; writes `tls.json`; cross-check vs peet.ws within the same MCP process to detect wrong-process capture.
6. **`scripts/stability_loop.sh <mcp>`** — 60-min loop of S1+S5 with 30s sleeps + PID watch; uses the snapshot fixture server, NOT live URLs.
7. **`scripts/aggregate_scores.py`** — walks `results/<date>/<mcp>/` directories, emits `scores.json` in the shape `scoring/score.py` already consumes. Existing scorer stays UNTOUCHED to preserve 2026-03 comparability.
8. **`Makefile`** at repo root — single-command reproducibility surface (`make bench`, `make bench-<mcp>`, `make tls`, `make coldstart`, `make stability`, `make score`).

**Patterns to follow:**
- File-mediated stage handoff (any single step is re-runnable in isolation)
- `.mcp.json` is the only place MCP server commands are declared
- Existing `scoring/score.py` is SACROSANCT — `aggregate_scores.py` adapts to it, not the other way

**Anti-patterns to avoid:**
- Reimplementing Claude Code as a Python harness (the 2026-05 testbench scored browser-use 0/15 because of *its* harness, not the MCP — we are characterising MCPs *as Claude Code uses them*, not as raw protocol servers)
- Letting Claude reach for fallback tools mid-test
- Storing raw stream-json without a human-readable transcript view

Full details: `.planning/research/ARCHITECTURE.md`.

### Critical Pitfalls (top 5 of 15)

1. **Transient-failure tank (BrowserMCP-disconnect class)** — single-pass scoring banks one bad WebSocket drop / npm registry blip / macOS App Nap into the public matrix. The 2026-03 wave did exactly this to BrowserMCP (5.53 composite with no asterisk). **Mitigation:** 3-pass-of-3 retry gate in `bench/transient.py` with explicit transient-failure taxonomy (WebSocket 1001/1006, ECONNRESET, MCP `initialize` timeout, HTTP 429/503, Chromium SIGKILL); score the **median** of 3 attempts; publish `n/3 passes` so readers see variance.
2. **Apples-to-oranges candidate categories** — 7 candidates are not the same category of thing (cloud / stealth-specialist / JS-light / LLM-augmented / tool-only). Single composite score makes `firecrawl` look like it beats `playwright` because cold-start is in someone else's datacenter. **Mitigation:** publish TWO views — same-rubric composite AND capability matrix with explicit category tags + N/A semantics (lightpanda Ashby = N/A not 0; firecrawl S4-S8 = N/A not 0); `scoring/score.py` drops N/A cells from the weighted denominator instead of counting them as 0; run browser-use in dual mode (`direct` + `agent`).
3. **Public-fixture rot (Greenhouse/Ashby 404)** — 2026-03 wave used live URLs. Greenhouse listings close when roles are filled. Six months from now, third-party reproducers hit 404s on every S1-S2 and write angry blog posts. **Mitigation:** `wget --mirror` snapshot the targets into `fixtures/snapshots/<platform>_<date>/`, commit them, serve via local `python3 -m http.server`; ONE live-URL smoke test per platform as drift detector; provenance + PII-scrub documented per snapshot.
4. **Sec-CH-UA-Platform leak from headless-on-macOS** — JS-shim stealth (`obscura --stealth`, playwright-stealth, naive UA overrides) only patches what's visible inside the page. UA Client Hints are emitted by the network stack before the page loads; on macOS arm64 they say `"macOS"` regardless of JS UA override. Cloudflare cross-checks this and flags instantly. **Mitigation:** echo-server header diff test as part of harness; any JS-UA-vs-Sec-CH-UA-Platform mismatch = automatic "stealth: leaks" tag; **disable `obscura --stealth` on macOS by default** per Vitalik's `browser-tools.md` rule; CI fails if a stealth row claims a platform its headers contradict.
5. **Orphan-process accumulation (G-688 dock-pollution déjà vu, different layer)** — Claude Code has known cleanup bugs (#1935, #22612, #33947, #15211, #40207, #35287). Each MCP session spawns child Chromiums; orphans get adopted by `launchd` (PPID=1) and accumulate. After a multi-hour stability run on the 24GB Mac Mini you leak 2-4GB; the Nth candidate scores "unstable" because the harness leaked, not the MCP. **Mitigation:** spawn under `setsid` process-groups; pre/post-run `ps` diff with automatic `kill -KILL -<pgid>` of orphans; per-tool-call 30s timeout enforced by the harness (Claude Code enforces none); `ulimit -v` memory ceiling per MCP; reboot between full passes.

Full details (15 critical pitfalls + 11 integration gotchas + 7 security mistakes + recovery strategies + phase mapping): `.planning/research/PITFALLS.md`.

---

## Cross-Document Tensions

These are points where research files don't fully agree. The requirements author should resolve each before Phase 1 begins.

1. **`Makefile` (ARCHITECTURE) vs `Justfile` (STACK)** — ARCHITECTURE recommends `Makefile`; STACK recommends `Justfile` with a note that "either is fine, pick one." **Recommended resolution:** Makefile, per ARCHITECTURE — matches the existing project's dogfood-friendly idiom and works zero-install on macOS/Linux.
2. **Cold-start measurement primary tool** — STACK §3.1 proposes Python `mcp.client.stdio` with custom timing; ARCHITECTURE §3 proposes a shell wrapper that pipes JSON-RPC to the MCP binary's stdin and times with `awk systime_ns`; PITFALLS §3 demands a 3-segment split (`t_resolve` / `t_spawn` / `t_first_useful`) with both cold and warm cache runs. **Recommended resolution:** Python `mcp.client.stdio` (lower overhead, portable, no `gdate`/GNU `awk` shim needed) implementing PITFALLS' 3-segment + cold-vs-warm split. STACK and PITFALLS converge here; ARCHITECTURE's shell variant is a workable backup.
3. **TLS fingerprint endpoint** — STACK §3.2 names Scrapfly (`tools.scrapfly.io/api/fp/ja3?extended=1`) as primary, `tls.peet.ws/api/all` as backup; ARCHITECTURE §4 names `tls.peet.ws/api/all` as primary. PITFALLS §5 requires cross-check against peet.ws regardless. **Recommended resolution:** capture from BOTH (one request each, ~150ms total), use Scrapfly as primary value, peet.ws as the automatic cross-check that fails the run on disagreement.
4. **Bot-detection probe URLs** — STACK §3.3 names `nowsecure.nl`, `g2.com/products/anthropic/reviews`, `recaptcha/api2/demo`, `akamai.com`; FEATURES proposes `bot.sannysoft.com`, `browserscan.net`, `fingerprint.com/demo`, `creepjs`, `arh.antoinevastel.com`; PITFALLS §6 STRONGLY warns against live commercial targets (IP gets flagged after run #3, runs #4-7 score badly through no fault of the MCP) and recommends stable adversaries + a self-deployed Cloudflare Worker for tier control. **Recommended resolution:** PITFALLS wins. Use `bot.sannysoft.com` + `fingerprint.com/demo` + `creepjs` + `browserscan.net/bot-detection` as the primary probe set; deploy one CF Worker for controlled-tier challenge testing; keep `nowsecure.nl` as a single optional live-canary, NOT a per-candidate target.
5. **Stability test workload** — ARCHITECTURE §6 specifies S1+S5 loop for 60min on the snapshot fixture; PITFALLS §8 + §9 reinforce that this MUST use the local snapshot server (live targets rate-limit mid-test). **Resolved:** they agree, but the requirements author must surface "stability test uses snapshot fixture, NOT live URL" as an explicit requirement so it isn't lost.
6. **Lightpanda version pin** — STACK §1 gives two options (`nightly@2026-05-22` for 2026-03 comparability, `v0.2.6` for last semver-tagged stable). **Recommended resolution:** pin nightly@2026-05-22 with SHA256 captured at install, AND run v0.2.6 as a sanity-check column — directly addresses the "is the React-blindness improving?" empirical question.
7. **Token measurement primary source** — STACK §3.4 says Anthropic SDK `count_tokens` out-of-band; ARCHITECTURE §5 says parse `stream-json` `usage` blocks + cross-check with `/mcp`; PITFALLS §4 demands all three scopes (`schema` / `payload` / `turn`) be captured. **Recommended resolution:** all three sources cooperate; `count_tokens` for `schema` (clean, free, deterministic), `stream-json` for `turn` (actual billed cost), parsed JSON-RPC payloads for `payload` (the apples-to-apples publishable column). PITFALLS' 3-scope split is the contract; STACK and ARCHITECTURE name the tools that implement it.

---

## Report "MUST Contain" Checklist (for requirements author)

Direct convertible to REQ-IDs. Every item below has at least one supporting research file citation; check `FEATURES.md` § "Table Stakes" and PROJECT.md "Active" for the source.

- [ ] **REQ:** 8-dim weighted score table (7 MCPs × 8 dims + composite, same shape as `results/2026-03-31_run.md`)
- [ ] **REQ:** Stage matrix S1-S8 × 7 MCPs (PASS / FAIL / PARTIAL / N/A / UNTESTED — N/A and UNTESTED must be distinct)
- [ ] **REQ:** Per-MCP "Deep Analysis" stanza (3-6 strengths + 3-6 weaknesses + 1-paragraph verdict + the per-MCP "interesting angle" finding)
- [ ] **REQ:** `results/recommendations.md` with explicit primary / secondary / sandbox-only / skip tiers for Stage 2 graduation
- [ ] **REQ:** Cold-start latency per MCP, 3-segment (`t_resolve` / `t_spawn` / `t_first_useful`), cold AND warm cache, median of ≥5 runs
- [ ] **REQ:** Token efficiency per MCP per task, 3-scope (`schema` / `payload` / `turn`); published headline column = `payload`
- [ ] **REQ:** Bot-detection resilience matrix (stable adversaries: `bot.sannysoft.com`, `fingerprint.com/demo`, `creepjs`, `browserscan.net/bot-detection`, ≥1 controlled CF Worker); record IP + ASN + observed-challenge-tier per attempt
- [ ] **REQ:** TLS fingerprint per MCP (JA3 + JA3N + JA4 + JA4_h + ALPN order + HTTP/2 frame settings), cross-checked vs peet.ws (fail run on mismatch)
- [ ] **REQ:** 1hr stability run per MCP using the snapshot fixture (NOT live targets); post-run orphan-process audit = 0
- [ ] **REQ:** Methodology section (machine spec, Claude Code version, model, date, fixtures, repro steps); `MACHINE.md` per `results/<date>/`
- [ ] **REQ:** Reproducibility manifest (`versions.lock.md` + `versions.json` + `uv.lock` + `package-lock.json` + per-MCP binary SHA256)
- [ ] **REQ:** Per-MCP evidence directories (`results/<date>/<mcp>/transcript.md`, `raw_stream.jsonl`, `stage_s*.{yml,md,png,txt}`, `cold_start.json`, `tokens.json`, `tls.json`, `stability.log`, `orphan_audit.log`)
- [ ] **REQ:** `scores.json` machine-readable output consumable by unmodified `scoring/score.py`
- [ ] **REQ:** Sandbox-only callout on every cloakbrowser mention in the report
- [ ] **REQ:** Partial-run disclosure (executive summary + matrix row + recommendations) if `FIRECRAWL_API_KEY` absent — 6/7 acceptable per PROJECT.md
- [ ] **REQ:** README updated with methodology + headline verdict
- [ ] **REQ:** Self-hosted snapshot fixtures (`fixtures/snapshots/<platform>_<date>/`) with `PROVENANCE.md` and PII-scrubbed content; tests target `127.0.0.1`, not live URLs
- [ ] **REQ:** `.mcp.json` env values are `${VAR}` references (NEVER inline literals); pre-commit hook regex-blocks inline secrets
- [ ] **REQ:** 3-pass-of-3 retry gate for any S1-S8 failure; published matrix shows `n/3 passes`
- [ ] **REQ:** Per-row failure-attribution taxonomy (`tool-bug` / `env-mismatch` / `target-flag` / `transient`)
- [ ] **REQ:** Methodology disclaimer header on the public report ("evaluated as of `<date>` with configuration `<X>`; not intrinsic tool quality")
- [ ] **REQ:** Courtesy pre-publication disclosure window (≥7 days) for any vendor scoring < 5; Linear ticket per vendor with draft + repro steps
- [ ] **REQ:** Linear traceability footer (G-703 umbrella + per-MCP sub-tickets)

---

## Implications for Roadmap

The architecture research already proposes 4 phases; pitfalls research maps every prevention to a phase. The roadmap should adopt those 4 phases as-is, with each phase's pre-flight checklist explicitly including the pitfall mitigations.

### Phase 1: Harness Foundation (BLOCKER for everything)

**Rationale:** Nothing else can run until the harness exists. Pitfalls 1, 8, 9, 10, 11, 12 are all prevented (or made possible to prevent) by scaffolding decisions made in Phase 1 — they are nearly impossible to retrofit later.

**Delivers:**
- `scripts/run_mcp_session.sh` working end-to-end against Playwright (the known-good baseline from 2026-03)
- `prompts/stage_walk.md` finalised (locked S1-S8, parameterised on MCP under test)
- `scripts/aggregate_scores.py` producing valid `scores.json` from one MCP's evidence
- `scripts/check_prereqs.sh` + Makefile skeleton
- `fixtures/snapshots/greenhouse_<date>/` + `fixtures/snapshots/ashby_<date>/` snapshot fixtures + local server (Pitfall 8)
- `bench/transient.py` with retry gate + transient-failure taxonomy (Pitfall 1)
- `versions.lock.md` + `bench/capture_versions.py` (Pitfall 10)
- Pre-commit hook regex-blocking inline secrets in `.mcp.json` (Pitfall 11)
- `bench/scrub_artifacts.py` (OCR + name-regex; Pitfall 12)
- Process-group spawn + pre/post `ps` audit + per-tool-call timeout + `ulimit -v` (Pitfall 9)
- Echo-server fixture + `tests/stealth_leak_test.py` (Pitfall 7)
- `MACHINE.md` template + NTP-timestamp instrumentation (Pitfall 15)

**Stop condition:** `make bench-playwright && make score` reproduces a comparable score to 2026-03 Playwright (~9/10). If the harness can't reproduce a known result, fix the harness before adding more MCPs.

**Avoids:** Pitfalls 1, 7, 8, 9, 10, 11, 12, 15.

### Phase 2: Per-MCP Scoring Runs

**Rationale:** Parallelisable across the 7 MCPs once Phase 1 is done — they share no state except the Makefile. Where stage-failures need root-cause investigation (browser-use transport timeout, obscura install gap), this is the phase that surfaces them.

**Delivers:** one full evidence directory per MCP for the 6 not already done in Phase 1 (`browser-use`, `chrome-devtools`, `lightpanda`, `obscura`, `firecrawl`, `cloakbrowser`); per-MCP "interesting angle" findings recorded in `transcript.md`; populated `scores.json` for all 7.

**Stop condition:** all 7 MCPs have at least S1-S3 attempted with PASS/FAIL/N_A clearly recorded; S4-S8 marked N_A (not 0) for read-only MCPs (`lightpanda`, `firecrawl`).

**Avoids:** Pitfalls 1 (retry gate active), 2 (N/A semantics applied), 13 (failure-attribution taxonomy applied per row).

**Known per-MCP risks:**
- `firecrawl`: skip cleanly if no `FIRECRAWL_API_KEY` (6/7 acceptable)
- `obscura`: install may fail on macOS arm64 (2026-05 testbench gap); skip with documented error if so
- `browser-use`: 2026-05 testbench had `initialize` timeout on v0.12.7 — re-test before scoring; if still broken, file as MCP-side bug, score 0 with footnote, courtesy-disclosure window per Pitfall 13
- `cloakbrowser`: sandbox-only — only against public Greenhouse + Ashby fixtures, NEVER personal Chrome session

### Phase 3: Cross-Cutting Measurements

**Rationale:** Cold-start, TLS, bot-detection, 1hr stability are the four "new this wave" measurements PROJECT.md explicitly calls out. Can start the moment Phase 1 is done and runs **in parallel with Phase 2** — the cross-cut scripts read `.mcp.json` directly and don't depend on per-MCP scoring runs completing.

**Delivers:** `cold_start.json` per MCP (3-segment, cold+warm, median of 5); `tls.json` per MCP + real-Chrome JA4 baseline + peet.ws cross-check; `bot_detection.json` per MCP across the stable-adversary set + IP/ASN/tier per attempt; `stability.log` per MCP (60min × 7, parallelisable where machine supports it).

**Stop condition:** all 7 MCPs have all 4 cross-cut artifacts (cold_start, tls, bot_detection, stability), even if some are "FAIL: would not connect."

**Avoids:** Pitfalls 3 (3-segment cold-start), 4 (3-scope token), 5 (per-process TLS isolation + peet.ws cross-check), 6 (stable adversaries + IP rotation + tier recording), 9 (orphan audit at end of every loop iteration).

### Phase 4: Synthesis + Reproducibility Validation

**Rationale:** Can't start until both Phase 2 and Phase 3 have populated every MCP's evidence directory. This is also where vendor courtesy disclosure happens.

**Delivers:**
- `aggregate_scores.py` enriched to incorporate cold-start, TLS, stability, bot-detection into rubric scores
- `results/<date>/scores.json` final
- `results/<date>/<date>_run.md` final report (matrix + per-MCP deep analysis + per-MCP "interesting angle" findings + methodology disclaimer header)
- `results/recommendations.md` — explicit Stage 2 graduation tiers
- README updated with methodology + headline verdict
- Courtesy disclosure: Linear ticket per vendor with score < 5, 7-day comment window
- Third-party reproducibility validated: clean checkout on MacBook (not Mac Mini), `make bench`, scores within ±0.5 composite per MCP

**Stop condition:** clean checkout reproduces ranking order with ±0.5 composite per MCP — the actual PROJECT.md "reproducibility validated" requirement.

**Avoids:** Pitfalls 2 (dual view), 13 (courtesy disclosure + methodology disclaimer + capabilities-first row format), 14 (wave-close ritual: lock candidates, lock rubric, scope-creep ledger).

### Phase Ordering Rationale

- **Phase 1 is the only true blocker.** Once it ships, Phases 2 and 3 run in parallel because they share no state except `.mcp.json` and the per-MCP output dir convention.
- **Phase 2 and Phase 3 should overlap fully.** Use spare machine capacity on already-completed MCPs to run cross-cuts while per-MCP scoring runs continue on others. Total wall-clock ~3 hrs serial, ~1 hr with 3-way parallelism.
- **Phase 4 cannot start early.** Synthesis requires complete evidence; partial synthesis tempts publishing-before-courtesy-disclosure (Pitfall 13).
- **Stage 2 work (terminal-craft) is FORBIDDEN during all 4 phases.** PROJECT.md gates it. Pitfall 14 catches this.

### Research Flags

**Phases likely needing deeper research during planning (use `/gsd:plan-phase --research-phase <N>`):**
- **Phase 1:** Snapshot-fixture serving infrastructure — `python3 -m http.server` is suggested but PII-scrub pipeline + clean-profile-per-run + echo-server header diff test all need design before code. Process-group cleanup on macOS specifically (`setpgid` vs `setsid` portability) is platform-specific and the existing Claude Code issues suggest cleanup is non-obvious. Echo-server header capture for Sec-CH-UA-Platform leak detection needs the exact MCP→Chromium→header path nailed down per MCP.
- **Phase 3:** Bot-detection probe set is unstable — STACK and FEATURES disagree on the URLs; PITFALLS says don't use live commercial targets at all; a controlled CF Worker needs to be deployed. The cross-machine IP-rotation budget question ($5-15 for residential IPs from BrightData/IPRoyal vs single-IP with 10min idle) needs a call.

**Phases with standard patterns (skip research-phase):**
- **Phase 2:** The per-MCP scoring runs are mechanical given Phase 1's harness — the "interesting angle" experiments are well-specified in FEATURES.md; no further research needed beyond the existing `browser-tools.md`.
- **Phase 4:** Synthesis is a writing task with a locked template (mirror `results/2026-03-31_run.md` shape) — no research needed; the disciplined output is the work.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All 7 candidate versions re-verified live against npm/PyPI/GitHub on 2026-05-22; measurement tooling endpoints (Scrapfly, peet.ws, Anthropic `count_tokens`) verified live; only MEDIUM call is "no Docker" vs AgentLab's containerized precedent — but the trade-off is conscious (Docker contaminates the metrics this wave actually measures). |
| Features | HIGH | Rubric, stages, fixtures, and prior-wave report shape are LOCKED — no design judgement needed beyond mirroring them. Per-MCP "interesting angle" experiments are grounded in official MCP docs (Playwright Forms tools, chrome-devtools-mcp tool reference, browser-use MCP docs, CloakBrowser GitHub) and Vitalik's `browser-tools.md` testbench. |
| Architecture | HIGH | Orchestration model + data layout (Claude Code `--print` + `stream-json` is the official reproducibility surface; per-MCP directory layout matches 2026-03 wave's pattern at scale); MEDIUM on stability-loop specifics (60-min × 7 = 7 hrs serial; parallelism call depends on Mac Mini headroom) and the Makefile-vs-shell choice (workable either way). |
| Pitfalls | HIGH | for items grounded in the 2026-03-31 wave (BrowserMCP disconnect, React Select, token spread), Vitalik's `browser-tools.md` (Sec-CH-UA-Platform leak, CloakBrowser sandbox rule, headless-vs-headful leak triplet, Obscura `--stealth` macOS rule), and verified Claude Code upstream issues (orphan accumulation, stdio init hang); MEDIUM for bot-detection items where the evidence is upstream-research-current but not re-run in this exact wave yet. |

**Overall confidence:** HIGH. This wave reuses the locked rubric + fixtures + report shape from 2026-03 and adds well-specified new measurements (cold-start, TLS, bot-detection, stability, token efficiency) where the tooling and pitfalls are both characterized. The only judgement calls left (bot-detection probe set, residential-IP budget, Lightpanda nightly-vs-stable pin, Makefile-vs-Justfile) are surfaced in Cross-Document Tensions for the requirements author.

### Gaps to Address

- **Bot-detection probe set is undecided** between STACK's live-target list and PITFALLS' stable-adversary list. Resolve during requirements; PITFALLS' position is recommended.
- **Residential IP budget** ($5-15) is a yes/no call from Vitalik. If no, the rotation strategy is "single IP, 10min idle, 3 candidates/day max across 3 days" which extends Phase 3 wall-clock.
- **Cross-machine reproducibility target** says ±0.5 composite per MCP. The MacBook does NOT currently have all 7 binaries installed (per HANDOFF.md). The cross-machine validation IS a Stage 1 requirement but may need a Phase 4 sub-task to install missing binaries on MacBook before validation can run.
- **Browser-use `initialize` timeout** — 2026-05 testbench showed transport mismatch. Phase 2 must determine whether v0.12.7 fixed it; if not, the score is 0/15 with a Linear ticket to the vendor and a courtesy disclosure window. The harness must NOT bypass it (that would be reimplementing Claude Code, Anti-Pattern 2).
- **Obscura engine install on macOS arm64** — known gap from 2026-05 testbench. Phase 1 should attempt `obscura-mcp install` early; if it fails, Obscura scores 6/7 with documented error per the partial-run pattern.
- **Lightpanda `0.3.0` vs `0.1.0` handshake version inconsistency** — the binary self-reports differently in different places. `versions.json` capture should record BOTH and the report should note the inconsistency rather than picking one.
- **CloakBrowser availability cross-platform** — closed-source binary, macOS verified, Linux availability unknown. Document in `docs/REPRODUCIBILITY.md` so Linux readers know to expect 6/7 if cloakbrowser unavailable.

---

## Sources

### Primary (HIGH confidence — verified live 2026-05-22)
- npm registry (`@playwright/mcp`, `chrome-devtools-mcp`, `obscura-mcp`, `firecrawl-mcp`, `@modelcontextprotocol/inspector`) — all version + time fields fetched
- PyPI (`browser-use`, `cloakbrowsermcp`) — version, project_urls, releases
- GitHub releases API (`lightpanda-io/browser`, `microsoft/playwright-mcp`, `ChromeDevTools/chrome-devtools-mcp`, `browser-use/browser-use`, `firecrawl/firecrawl-mcp-server`)
- Scrapfly JA3/JA4 endpoint `https://tools.scrapfly.io/api/fp/ja3?extended=1` — schema confirmed live
- MCP Inspector — modelcontextprotocol.io/docs/tools/inspector
- MCP Lifecycle spec — modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle
- Anthropic token counting — platform.claude.com/docs/en/build-with-claude/token-counting — `count_tokens` is free, separate rate limit
- Claude Code MCP docs — code.claude.com/docs/en/mcp — `--allowedTools`, `--output-format stream-json`, `/mcp` panel
- Playwright MCP Forms tool reference + Issue #39437 — batch API, 16× speedup
- browser-use MCP docs — docs.browser-use.com/open-source/customize/integrations/mcp-server
- chrome-devtools-mcp tool reference — 26 tools, 6 categories
- CloakBrowser GitHub (CloakHQ) — 30/30 tests, 58 C++ patches
- User-Agent Client Hints — web.dev/articles/user-agent-client-hints — Sec-CH-UA-Platform emitted by network stack
- Auth0 — Strengthening Bot Detection with JA4 Signals
- FoxIO-LLC/ja4 (GitHub) + tls.peet.ws/api/all
- Claude Code MCP lifecycle bugs — anthropics/claude-code issues 33947, 1935, 22612, 15211, 40207, 35287 — orphan accumulation, stdio init hang
- TLS fingerprint research — arXiv 2602.09606 (2026) — CatBoost+JA4 AUC 0.998

### Secondary (MEDIUM confidence)
- obscura-mcp on Glama — Rust-CDP-direct, 30MB RAM
- Firecrawl 2026 capabilities (TokenMix blog) — 96% JS-site success
- Lightpanda vs Browser-Use vs Stagehand (Webfuse, 2026)
- CloakBrowse review (Pramod Dutta, Medium, May 2026) — independent reCAPTCHA v3 0.9 score
- MindStudio "Claude Code MCP Token Overhead"
- Fastio "MCP Server Cold Start Optimization"
- AgentLab — ServiceNow — reproducibility-model precedent
- Cloudflare cf-mitigated header discussion — lexiforest/curl_cffi
- Scrapfly — Post-Quantum TLS bot detection — Akamai PQ default 2026-01-31

### Tertiary (project-internal, LOAD-BEARING for this wave)
- `/Users/pleasedodisturb/Projects/web-agent-comparison/.planning/PROJECT.md` — locked scope, Active requirements, decisions
- `/Users/pleasedodisturb/Projects/web-agent-comparison/HANDOFF.md` — pipeline framing, install commands, version pinning
- `/Users/pleasedodisturb/Projects/web-agent-comparison/scoring/rubric.md` + `scoring/score.py` — locked 8-dim rubric (sacrosanct)
- `/Users/pleasedodisturb/Projects/web-agent-comparison/.mcp.json` — exact MCP commands committed for repro
- `/Users/pleasedodisturb/Projects/web-agent-comparison/results/2026-03-31_run.md` — report shape to mirror; prior-wave findings
- `/Users/pleasedodisturb/.claude/docs/browser-tools.md` (2026-05-21) — TLS-fingerprint dominance, per-MCP testbench scores, OS-detection gotchas, CloakBrowser sandbox rule, Obscura `--stealth` macOS leak
- `/Users/pleasedodisturb/.claude/projects/-Users-pleasedodisturb-Projects-screenpipe/memory/feedback_mcp_scope_discipline.md` (G-688) — Python.app dock-pollution tell

### Detailed research files (synthesized into this summary)
- `.planning/research/STACK.md` — 7 candidate versions, measurement tooling per cross-cutting concern, reproducibility model (no Docker), version compatibility
- `.planning/research/FEATURES.md` — table stakes vs differentiators vs anti-features, per-MCP "interesting angle" experiments, MVP gate, prioritization matrix
- `.planning/research/ARCHITECTURE.md` — orchestration (one Claude session per MCP), evidence layout, per-question decisions for cold-start / TLS / tokens / stability, 4-phase build order, patterns + anti-patterns
- `.planning/research/PITFALLS.md` — 15 critical pitfalls with phase mapping, technical debt patterns, integration gotchas, performance traps, security mistakes, "looks done but isn't" checklist, recovery strategies

---
*Research completed: 2026-05-22*
*Ready for roadmap: yes*
