# Pitfalls Research

**Domain:** MCP-layer browser-server benchmark, Claude-Code-driven, 7-candidate comparison (playwright, browser-use, chrome-devtools, lightpanda, obscura, firecrawl, cloakbrowser)
**Researched:** 2026-05-22
**Confidence:** HIGH for items grounded in the 2026-03-31 wave + Vitalik's `browser-tools.md` + verified Claude Code upstream issues; MEDIUM for cross-cutting bot-detection items where the evidence is upstream-research-current but not re-run in this wave yet.

This file is **scoped to MCP-layer browser benchmarks driven by Claude Code**. It is not a generic "how to benchmark" doc. Every pitfall below has been observed in this exact pipeline (Stage 1 → terminal-craft → Kestrel/Eyas) or is a near-miss flagged by a verified upstream issue. Generic "test in isolation" advice has been deliberately omitted.

The five roadmap phases used for the "Phase to address" field:

| Code | Phase | What lives here |
|------|-------|-----------------|
| **HARNESS** | Harness build | The `bench/` runner: spawn MCP, drive tools, capture timings, write JSONL trace |
| **PER-MCP** | Per-MCP runs | One scoring pass per candidate MCP against S1-S8 fixtures |
| **CROSS** | Cross-cutting concerns | Cold-start, bot-detection, TLS fingerprint, 1hr stability, token efficiency (new this wave) |
| **SCORE** | Scoring & adjudication | Apply rubric, weight, run sanity gates, decide pass/retry/discard |
| **REPORT** | Public report & graduation | `results/2026-05-XX-mcp-comparison.md`, `recommendations.md`, README update |

---

## Critical Pitfalls

### Pitfall 1: Transient-failure tank (the BrowserMCP-disconnect class)

**What goes wrong:**
A candidate MCP hits a one-time, environment-specific failure during its scoring window (mid-test disconnect, npm registry blip, target site rate-limit on this IP today, MCP child process killed by macOS App Nap). The single failure score gets baked into the public matrix. The MCP gets 3/10 reliability on what would otherwise be an 8/10 day. The 2026-03-31 wave did exactly this to BrowserMCP — disconnected mid-session, Reliability scored 3, untested on S1-S8, but the 5.53 composite went into the published table.

**Why it happens:**
Single-pass scoring treats one run as ground truth. There's no distinction between "MCP failed because it's broken" and "MCP failed because it was Tuesday afternoon and the WebSocket dropped." Vendors don't get a retry. Readers see the number, not the asterisk.

**How to avoid:**
Implement a **3-pass-of-3 retry gate** before recording a failure: any S1-S8 task that fails gets re-run twice more in fresh MCP sessions, on a different wall-clock window (≥30 min gap). Record pass/fail per attempt in `results/<date>/<mcp>/raw.jsonl`. Score the **median** of the 3 attempts, not the worst. Define a `transient_failure_taxonomy` in `bench/transient.py` that recognizes: WebSocket close codes 1001/1006, ECONNRESET, MCP `initialize` timeout, HTTP 429/503 from target, Chromium SIGKILL by OS. Any failure that matches the taxonomy is automatically a retry-eligible event, not a recorded reliability hit. The published matrix shows `n/3 passes` so readers can see the variance, not just the final score.

**Warning signs:**
- A single failure-score row in the matrix with no companion explanation
- Reliability score < 5 for a candidate that has > 7 on every other dimension
- Vendor disagreement on score after publication ("we ran it 10 times and it worked")
- The failure timestamp is the only one in the run that's > 2σ slower than the rest of the session (process under memory pressure / swap)

**Phase to address:** HARNESS (build the retry gate) + SCORE (apply the median rule + publish n/3 visibility) + REPORT (every score row that involved retries gets a footnote).

---

### Pitfall 2: Apples-to-oranges candidate categories

**What goes wrong:**
The 7 candidates are not the same category of thing. `browser-use` ships its own LLM-driven `retry_with_browser_use_agent` escape hatch — it can solve a task Claude Code couldn't have driven directly. `firecrawl` is a cloud service; cold-start is `0ms` because the process is in someone else's datacenter. `cloakbrowser` is a stealth-Chromium wrapper meant for sites that flag Playwright — measuring it on Greenhouse (which doesn't flag Playwright) wastes its differentiator. `lightpanda` is a JS-light Zig engine that scores 0 on Ashby by design. Scoring all 7 on the same composite without segmentation gives `cloakbrowser` 15/15 on the harness but readers walk away thinking it's the best for everything.

**Why it happens:**
Single composite scores compress multi-dimensional tradeoffs into one number. Readers love rankings. Researchers ship rankings. The composite is a lie of convenience.

**How to avoid:**
Publish **two views**, not one:
1. **Same-rubric composite** (the 8-dim weighted score) — the public ranking, prior-wave-compatible
2. **Capability matrix** with explicit category tags per MCP: `tool-only` (playwright, chrome-devtools), `LLM-augmented` (browser-use), `stealth-specialist` (cloakbrowser, obscura), `cloud` (firecrawl), `js-light` (lightpanda)
Add a **disqualification footnote** per candidate when its category makes a dimension N/A (lightpanda Ashby = N/A not 0; firecrawl cold-start = N/A not 0). In `scoring/score.py`, an `N/A` cell drops out of the weighted denominator instead of counting as 0.
For browser-use specifically: run it in **two modes** — `direct` (tools only, comparable to playwright) and `agent` (LLM escape hatch enabled). Score both. Make the LLM-mode result transparently labeled "this MCP solved it via internal LLM call; not a like-for-like Claude-driven score."

**Warning signs:**
- A candidate's headline score is dominated by one dimension where it has a structural advantage (cloud cold-start, internal LLM, stealth)
- A candidate scores 0 on a dimension that doesn't apply to its category
- Reader on Hacker News asks "why is firecrawl beating playwright? oh, because cold-start is in someone else's datacenter"

**Phase to address:** SCORE (define category tags + N/A semantics + dual-mode for browser-use) + REPORT (publish both views, explain segmentation up front).

---

### Pitfall 3: Cold-start measurement that hides Node module resolution

**What goes wrong:**
"Cold start" measured as `time-to-first-tool-response` includes wildly different things across candidates. For an npm-based MCP (playwright, chrome-devtools, firecrawl, obscura), the first invocation includes `npm` resolving the package, `node` parsing all transitive deps, and stdio handshake. For a uv-tool-based MCP (browser-use, cloakbrowser), it includes uv's resolution cache check + Python interpreter spawn + Playwright's Chromium download check. For lightpanda, it's a static binary launch. Comparing them as one number is comparing four different start sequences. Worse: a warm npm cache after the first run makes attempt #2 look 10x faster than attempt #1, but if the harness reuses the same npm cache the "cold start" is actually warm.

**Why it happens:**
"Time from spawn to first usable tool call" sounds rigorous but the spawn point isn't well-defined. The harness usually times `mcp__<name>__initialize` round-trip and calls it cold-start.

**How to avoid:**
Split cold-start into **three timed segments**, recorded per MCP per run:
1. `t_resolve` — npm/uv/binary resolution (clean cache: `rm -rf ~/.npm/_cacache && rm -rf ~/.cache/uv && rm -rf ~/Library/Caches/ms-playwright`)
2. `t_spawn` — process spawn + stdio handshake + `initialize` reply
3. `t_first_useful` — first non-meta tool call returning a non-empty result (e.g., `browser_navigate` to a 200-byte fixture page on `127.0.0.1`)
Run cold-start measurement with **both fresh and warm caches** and publish both. For cloud MCPs (firecrawl), `t_resolve` and `t_spawn` are sub-100ms and `t_first_useful` is network-bound — note this explicitly. Local `127.0.0.1` fixture isolates from upstream-target variance. Use `hyperfine --warmup 0 --runs 5` for warm-cache numbers; manual cache-flush + single run for cold.

**Warning signs:**
- A candidate's cold-start delta between runs in the same session is > 10x (you're measuring cache warmth, not start)
- The "cold-start" winner is just the candidate with the smallest binary
- Numbers don't reproduce on a different machine because the npm cache state differs
- `t_first_useful` is dominated by network round-trip to the real target site, not by MCP start

**Phase to address:** CROSS (specify the 3-segment definition + cache-flush protocol) + HARNESS (instrument the three timers + drive the local fixture server).

---

### Pitfall 4: Token-count contamination (Claude's prompt counted as MCP I/O)

**What goes wrong:**
Token efficiency in the 2026-03 wave (WebFetch 10/10, Playwright 7/10) compared raw output sizes. For this MCP-layer wave the temptation is to count "tokens that hit Claude's context per task" — but that number includes Claude's own system prompt, the MCP tool schema (which differs per MCP: playwright = 28 tools, browsermcp = 12), prior conversation turns, and the actual MCP tool-response payload. If the measurement scope isn't pinned to **just the MCP-response payload**, an MCP with a verbose tool schema (browser-use's `act/extract/observe/retry_with_browser_use_agent` with rich descriptions) will look token-heavy even on a task where its response payload is small. Conversely, an MCP whose tool descriptions are minimal looks artificially efficient until the agent needs to read 33KB of accessibility tree.

**Why it happens:**
"Tokens per task" is ambiguous between three scopes: (a) tool-schema overhead, (b) MCP-response payload, (c) full conversation-turn delta. Most benchmarks accidentally measure (c) because it's what Claude Code's `/cost` reports.

**How to avoid:**
Define and instrument **all three scopes** separately in `bench/tokens.py`:
- `tokens_schema` — sum of `len(json.dumps(tool_definition))` across the MCP's tool list, measured once per MCP after `initialize`. Constant overhead.
- `tokens_payload` — sum of `len(tool_response.content)` across all tool calls in the task. The pure "MCP I/O" number.
- `tokens_turn` — Claude Code's reported input + output tokens for the task. The "real cost" number.
Tokenize with `tiktoken` (`cl100k_base` as a Claude-adjacent proxy) for byte-stable counts; document that this is a proxy, not Anthropic's actual tokenizer. The published table shows `payload` as the primary token-efficiency column (apples-to-apples), `schema` as a one-time-per-session footnote, and `turn` as a cost-context column.

**Warning signs:**
- Token-per-task numbers vary 5x between runs of the same task (you're measuring conversation history, not MCP I/O)
- A candidate's token efficiency improves dramatically when run as task #5 vs task #1 (Claude's prompt cache is doing the work)
- The verbose-tool-schema MCP (browser-use) is penalized on a task that uses one tool
- Token counts don't add up — the harness reports 10K but `/cost` reports 30K

**Phase to address:** CROSS (define the 3-scope split + tokenizer choice) + HARNESS (instrument `tokens_schema/payload/turn` per task into the JSONL trace).

---

### Pitfall 5: TLS-fingerprint captured from the wrong process

**What goes wrong:**
JA3/JA4 fingerprinting is the dominant 2025-2026 bot-detection axis ([CatBoost+JA4 → AUC 0.998 on the 2026-02 arXiv paper](https://arxiv.org/abs/2602.09606)) so this wave needs to characterize the TLS fingerprint each MCP actually presents to the target. The naive approach is `tshark -i en0 -Y tls.handshake.type==1` and inspect the ClientHello — but that captures **every TLS connection from the machine**, including Claude Code's own API calls, the npm registry, telemetry, etc. The fingerprint attributed to "playwright MCP" might actually be Claude Code's connection to api.anthropic.com. Worse: some MCPs (firecrawl) talk to the target from a remote datacenter — the fingerprint captured on your machine is the firecrawl-cloud connection, not the target-facing one (which you can't see).

**Why it happens:**
TLS captures are coarse — they see packets, not processes. Without per-process filtering, you mix candidate traffic with everything else. Cloud MCPs introduce a fundamentally unseeable hop.

**How to avoid:**
For each MCP, do TLS capture with **per-process isolation**:
1. Use `mitmproxy` with `--mode upstream` and force the MCP's child Chromium to route through it (`HTTP_PROXY=127.0.0.1:8080`). mitmproxy logs ClientHello per-connection with the originating process visible.
2. Or use `lsof -p <chromium-pid> -i` to bind socket→pid, then correlate with `tshark -i lo` capture filtered by `tcp.port == <socket-port>`.
3. Compute JA3 + JA4 + JA4_h fingerprints using [`ja4-tools`](https://github.com/FoxIO-LLC/ja4) — JA4_h covers HTTP/2 header order which is also fingerprinted.
4. Always cross-check the captured fingerprint against `https://tls.peet.ws/api/all` (browser visits, returns its observed JA3/JA4). The MCP-captured fingerprint must match peet.ws within one cipher-list permutation; if not, you captured the wrong connection.
5. For **cloud MCPs (firecrawl)**: mark TLS fingerprint as `unmeasurable from harness; documented as <firecrawl's published value>` and link to firecrawl's docs. Don't fabricate a number.

**Warning signs:**
- The JA4 you captured matches what `curl --tlsv1.3 https://tls.peet.ws/api/all` reports (you captured the wrong process)
- All 7 MCPs produce the same JA4 fingerprint (you're seeing the OS's shared TLS library, not the Chromium each MCP ships)
- Firecrawl has a "real Chrome" JA4 (impossible — you're seeing your machine's connection to firecrawl, not firecrawl's connection to the target)

**Phase to address:** CROSS (specify the mitmproxy-or-lsof protocol + cross-check rule) + HARNESS (build the per-MCP fingerprint capture into the runner, fail fast if cross-check disagrees with peet.ws).

---

### Pitfall 6: Bot-detection threshold drift mid-benchmark

**What goes wrong:**
Cloudflare/DataDome/Akamai/reCAPTCHA tune their challenge difficulty **dynamically** based on day-of-week, IP reputation, time-of-day, and per-target risk score. An MCP tested at 09:00 Tuesday on a target with low risk may pass cleanly; the next MCP tested at 14:00 Friday on the same target after the prior 6 candidates already pinged it from the same IP hits a hardened challenge tier. "cloakbrowser passes Cloudflare" might be true Tuesday and false Friday. Worse: the IP gets flagged after run #3 and runs #4-7 score badly on a problem caused by run #1-3.

**Why it happens:**
Bot-detection vendors do not publish their decisioning. Defaults are adversarial. Treating "passed Cloudflare today" as a stable property attributes the result to the MCP when half the variance is the target's mood.

**How to avoid:**
1. **Run order matters** — randomize MCP order across runs (`shuf` the candidate list per session) so no MCP is systematically last. Record the order in each run's JSONL.
2. **IP reputation hygiene** — run bot-detection tests from a **fresh residential IP per candidate** if budget allows (BrightData / IPRoyal residential, ~$5-15 for the test wave). If using a single IP, insert ≥10min idle between candidates and run 3 candidates per day max across 3 days. Record IP + ASN + first-seen-by-target timestamp per attempt.
3. **Use stable adversaries, not live commercial sites** — test bot-detection against [`bot.sannysoft.com`](https://bot.sannysoft.com/), [`fingerprint.com/demo`](https://fingerprint.com/demo), [`creepjs.example`](https://abrahamjuliot.github.io/creepjs/), [`browserscan.net/bot-detection`](https://www.browserscan.net/bot-detection), and a local Cloudflare-protected Worker you deploy + tear down (control the challenge tier). These don't change weekly.
4. **Record the challenge tier** observed (no-challenge / managed-challenge / interactive-CAPTCHA / blocked) per target per candidate per run, not just pass/fail. Tier drift between attempts of the same candidate is the signal that the target changed, not the MCP.
5. **Never claim "passes Cloudflare"** in the report — claim "observed challenge tier X on target Y on date Z from ASN W." Vendors get less defensive when claims are timestamped + scoped.

**Warning signs:**
- A candidate that passed bot-detection on day 1 fails on day 2 with no MCP version change (target changed, not MCP)
- All candidates start failing after run #4 (your IP got flagged; run #1-3 burned the reputation)
- The pass/fail pattern correlates with run order more than with MCP identity
- Cloudflare returns a 1020 ("access denied") that the harness records as a generic "fail" without recording the tier

**Phase to address:** CROSS (define the IP-rotation + stable-adversary protocol + challenge-tier taxonomy) + HARNESS (record IP/ASN/tier into JSONL) + REPORT (every bot-detection claim is timestamped + scoped to the observed tier).

---

### Pitfall 7: Sec-CH-UA-Platform leak from headless-on-macOS

**What goes wrong:**
A "stealth" MCP claims to spoof a Linux Chrome UA. The JS `navigator.userAgent` returns the spoof. But Chromium emits **Sec-CH-UA-Platform** and **Sec-CH-UA-Platform-Version** HTTP headers ([User-Agent Client Hints](https://web.dev/articles/user-agent-client-hints)) that come from the OS, not from the JS UA override. On macOS arm64 these will say `"macOS"` and `"15.0.0"` regardless of what JS reports. Cloudflare cross-checks UA against Sec-CH-UA-Platform — a "Linux Chrome" with `Sec-CH-UA-Platform: "macOS"` is a contradiction that flags instantly. This was documented in Vitalik's existing browser-tools doc for obscura's `--stealth` flag; it applies more broadly to any MCP that spoofs the platform at the JS layer without patching the network layer. CloakBrowser's C++ patches may or may not cover this — needs empirical verification per fixture, not vendor-marketing trust.

**Why it happens:**
JS-shim stealth (playwright-stealth, obscura `--stealth`, naive UA overrides) only patches what's visible inside the page. UA client hints are emitted by the network stack before the page loads.

**How to avoid:**
1. Per MCP, capture the **full request headers** to a local echo server (`python3 -m http.server` with a logging handler, or a `caddy` reverse proxy that logs `request_headers`). Compare what the MCP claims to be (JS-visible `navigator.userAgent`) against what it actually sends (Sec-CH-UA, Sec-CH-UA-Platform, Sec-CH-UA-Mobile, Sec-CH-UA-Model, Sec-CH-UA-Platform-Version, Sec-CH-UA-Arch, Sec-CH-UA-Bitness).
2. Any mismatch = automatic "stealth: leaks" tag in the matrix. No charitable reading.
3. Add `tests/stealth_leak_test.py` that runs against the local echo server and fails CI if the platform header doesn't match the JS UA's claimed platform.
4. For obscura: **document the `--stealth` macOS rule from Vitalik's `browser-tools.md`** in the per-MCP notes ("do not enable on macOS hosts; Sec-CH-UA-Platform leaks") and either disable the flag in the harness or score the flagged-on configuration as "leaks" with a footnote.

**Warning signs:**
- JS `navigator.userAgent` says "Linux x86_64" but request headers say `Sec-CH-UA-Platform: "macOS"`
- bot.sannysoft.com row shows green checks but real Cloudflare flags
- Stealth MCP scores well on fingerprint-test sites that only inspect JS but fails on sites that inspect HTTP headers
- WebGL renderer says "SwiftShader" on a tool that claims real Chrome (headless leak: real-Chrome reports Apple M-series Metal, headless reports SwiftShader)

**Phase to address:** CROSS (define the header-vs-JS cross-check protocol) + HARNESS (echo-server fixture + stealth-leak test) + REPORT (every stealth claim cites which leak tests it passed/failed, never a vendor-marketing claim).

---

### Pitfall 8: Public-fixture rot (Greenhouse/Ashby job 404s)

**What goes wrong:**
The 2026-03-31 wave used live URLs: `https://job-boards.greenhouse.io/anthropic/jobs/4017544008` and `https://jobs.ashbyhq.com/replit/1e1a651f-...`. Greenhouse listings are closed when the role is filled. Ashby URLs change when reqs are re-opened. Six months from now, the public reproducibility guarantee dies silently — third parties run the harness, hit 404s on every S1-S2, conclude every MCP "failed extraction," and write angry blog posts. The prior wave's URLs may already be dead.

**Why it happens:**
Real public URLs are convenient (no fixture maintenance) but they're someone else's mutable state. The benchmark inherits their lifecycle without controlling it.

**How to avoid:**
1. **Snapshot and self-host the fixtures.** For each target page, run `wget --mirror --convert-links --adjust-extension --page-requisites --no-parent <url>` once, store the resulting tree in `fixtures/snapshots/greenhouse_2026-05-22/` and `fixtures/snapshots/ashby_2026-05-22/`. Serve via `python3 -m http.server 8765` (or `caddy file-server`) from `fixtures/snapshots/` during the bench run.
2. **Pin the fixture date in the test config.** Tests target `http://127.0.0.1:8765/greenhouse_2026-05-22/...`, not the live URL.
3. **Keep ONE live-URL smoke test per platform** to detect when the live ATS schema diverges from the snapshot (signal that the snapshot is stale; doesn't break the benchmark).
4. **Record snapshot provenance** in `fixtures/snapshots/<dir>/PROVENANCE.md`: original URL, capture date, capture tool + version, mock-data substitutions applied.
5. **Strip identifying data on capture.** `sed -i '' 's/<real-applicant-name>/Jane Testworth/g'` etc. Use the prior wave's mock-applicant pattern.
6. **Commit the snapshots to the repo** (a few MB; this is the whole point of public reproducibility).

**Warning signs:**
- A reproducibility attempt by a third party gives wildly different scores than the published table — first check is "did our fixture URLs still resolve?"
- The live-URL smoke test passes but the snapshot test fails on the same MCP (schema drift; refresh snapshot)
- The fixture serves a 200 but the page content is a "this job is no longer accepting applications" stub instead of the apply form

**Phase to address:** HARNESS (build the snapshot + local-server runner before any PER-MCP run) + CROSS (the live-URL smoke is a daily cross-cutting check, not per-candidate).

---

### Pitfall 9: Orphan-process accumulation (the Python.app dock pollution returns)

**What goes wrong:**
G-688 already burned us on this once at a different layer (MCPs at user scope spawning everywhere). The benchmark-layer version: each MCP run spawns a child Chromium (playwright, chrome-devtools, obscura, cloakbrowser, browser-use) which spawns helper processes. Claude Code does not reliably clean up MCP server child processes on session exit ([verified upstream issues #1935, #22612, #33947, #15211, #40207 — open across macOS, Linux, Windows](https://github.com/anthropics/claude-code/issues/33947)). On macOS, orphaned MCP children get adopted by `launchd` (PPID=1) and accumulate indefinitely; on a 24GB Mac Mini after a multi-hour 1hr-stability run, you can leak 2-4GB of orphaned Chromiums + Python processes. The 1hr-stability test then runs under memory pressure that wasn't the MCP's fault, scoring it "unstable" because the harness leaked.

Also: stdio MCPs that fail to initialize hang the harness indefinitely with no timeout ([upstream #35287, current as of 2025-2026](https://github.com/anthropics/claude-code/issues/35287)). The harness needs its own timeout because Claude Code doesn't enforce one.

**Why it happens:**
MCP lifecycle is the host's job, but the host (Claude Code) has known bugs in cleanup. The benchmark adds another lifecycle layer (the run script) that needs to cover both Claude Code's gaps and its own.

**How to avoid:**
1. **Sentinel process tree.** Spawn each MCP under a process-group (`setsid` on Linux, `setpgid` on macOS) so the entire MCP + child Chromium + helper tree can be `kill -TERM -<pgid>` followed by `kill -KILL -<pgid>` after a 5s grace window. The harness owns this; do not trust Claude Code to do it.
2. **Pre-run + post-run process audit.** Before each MCP run, snapshot `ps -axo pid,ppid,rss,command | grep -E '(chrome|chromium|playwright|obscura|cloak|firecrawl|lightpanda|browser-use)'`. After the run, snapshot again. Diff. Any survivor not in the pre-run set is an orphan — `kill -KILL` it and log to `results/<date>/<mcp>/orphan_audit.log`. Fail the run if orphan count > 0 (forces the harness to fix its cleanup, not the candidate's score).
3. **Memory ceiling enforcement.** `ulimit -v <mb-limit>` per MCP spawn, or run each MCP under `systemd-run --user --scope -p MemoryHigh=2G -p MemoryMax=3G` on Linux / `launchctl limit` analog on macOS. Memory exhaustion that crashes a candidate gets surfaced as "exceeded memory budget" instead of "crashed."
4. **Per-tool-call timeout** in the harness — default 30s, configurable per task. Claude Code doesn't enforce one; the harness must.
5. **Reboot between full passes** for 1hr-stability tests. Yes, really. Cleaner than fighting OS-level state leaks.

**Warning signs:**
- `Activity Monitor.app` shows a forest of rocket icons after a benchmark run (Python.app dock pollution = the same G-688 tell, different layer)
- The Nth candidate in a sequential run gets a worse stability score than the (N-1)th regardless of which MCP is in which slot
- Memory pressure swap-out events in `vm_stat` increase monotonically over the run
- `ps -axo ppid,command | awk '$1==1'` shows MCP children adopted by launchd after the bench script exits

**Phase to address:** HARNESS (process-group spawn + pre/post audit + per-call timeout + memory ceiling — all of this lives in the runner) + CROSS (1hr-stability test enforces the audit before recording a score).

---

### Pitfall 10: Version drift across the candidate matrix

**What goes wrong:**
Seven MCPs, each with its own version-pin story. `playwright` is `@playwright/mcp@0.0.75` per `.mcp.json` — pinned. But it depends on a Chromium that's downloaded by `playwright install` and is NOT pinned in `.mcp.json`; a fresh clone will pull whichever Chromium playwright-core's latest install script wants. `cloakbrowser` ships its own patched Chromium binary; the version of that binary is bundled in `cloakbrowsermcp@2.0.4` but a `uv tool upgrade` silently bumps it. `firecrawl-mcp@3.17.0` is a thin client — the actual scraping logic is server-side at firecrawl.dev, which can change anytime without a version bump on the client. `browser-use --mcp` depends on `browser-use` Python package + its Playwright dependency + its bundled-or-not Chromium. Two researchers running the "same `.mcp.json`" can get materially different scores because their Chromium versions differ.

**Why it happens:**
"Pin the MCP version" feels sufficient but each MCP is a stack with un-pinned layers underneath. The reproducibility surface area is larger than the version-control surface area.

**How to avoid:**
1. **Lock the full stack per MCP** in `bench/versions.lock.md`. For each candidate:
   - MCP package name + exact version
   - Runtime version (Node X.Y.Z / Python X.Y.Z / uv X.Y.Z)
   - Browser binary version (`chromium --version` for playwright/chrome-devtools/obscura/cloakbrowser; `lightpanda --version`; N/A for firecrawl + browser-use direct mode)
   - All transitive dep manifests committed: `package-lock.json` for npm MCPs, `uv.lock` for uv-tool MCPs
2. **Capture the lock at run time** — before scoring starts, `bench/capture_versions.py` writes `results/<date>/versions.json` with every version observed in the running processes. Mismatches between `versions.lock.md` and `versions.json` fail the run.
3. **Pin Chromium downloads** by setting `PLAYWRIGHT_DOWNLOAD_HOST` + a `PLAYWRIGHT_BROWSERS_PATH=fixtures/browsers/` directory committed once per wave (yes, multi-hundred-MB; or store in git-lfs / S3 and `sha256sum` verify).
4. **Cloud MCPs (firecrawl): pin to a documented API version** via header (`X-Firecrawl-Version: v3`) if supported; if not, capture `firecrawl-cli config get` output and record server response signatures.
5. **Re-lock on every wave**, not silently. Bumping `playwright-mcp` from 0.0.75 → 0.0.80 mid-wave invalidates prior scores; either re-run all prior candidates or scope the bump to the next wave.

**Warning signs:**
- Two clones of the repo run the same harness and get different scores
- `package-lock.json` is gitignored or out of date
- Chromium revision in `versions.json` differs from `versions.lock.md` after `npm install`
- A score regresses for a candidate and the MCP package version didn't change (probably Chromium did)

**Phase to address:** HARNESS (the `versions.lock.md` + `capture_versions.py` + fail-on-mismatch gate is part of the runner skeleton) + REPORT (publish `versions.json` alongside the matrix; "what you ran" is part of the result).

---

### Pitfall 11: Secrets-in-public-config (the `.mcp.json` env trap)

**What goes wrong:**
`firecrawl-mcp` needs `FIRECRAWL_API_KEY`. The path of least resistance is to add `"env": {"FIRECRAWL_API_KEY": "fc-abc123..."}` to the committed `.mcp.json`. The repo is **public**. The key leaks in the first commit. Bitwarden vault entry gets revoked, firecrawl bills get audited, and the linear ticket gets an embarrassing G-XXX postmortem. Per Vitalik's global CLAUDE.md, this is a never-do-it offense, but it's a one-character mistake during a benchmark sprint.

**Why it happens:**
MCP configs accept env inline. Convenience > security in the moment. `git secret-scan` hooks don't always fire on `.mcp.json` paths.

**How to avoid:**
1. **`.mcp.json` env values must be `${VAR}` references, never literals.** Add a pre-commit hook in `.git/hooks/pre-commit` that fails if `.mcp.json` contains anything matching `(api[_-]?key|token|secret).*"[A-Za-z0-9_-]{20,}"`. Per the global rule, secrets live in rbw — load into shell env before launching Claude.
2. **Document the env-loader pattern** in `README.md`: `eval "$(rbw get 'firecrawl.dev' --field Firecrawl_API | sed 's/^/export FIRECRAWL_API_KEY=/')" && claude` (or a `./bench/start-claude.sh` wrapper that does it).
3. **Add `.env*` to `.gitignore` proactively** and confirm via `git check-ignore -v .env`.
4. **`gh secret-scanning` enabled on the public repo.** GitHub will flag leaked credentials on push; respond within minutes.
5. **For reproducibility**: third parties without a Firecrawl key score firecrawl as `N/A — requires FIRECRAWL_API_KEY (see README)` per the existing `PROJECT.md` constraint. Don't fabricate a degraded score; partial coverage (6/7) is acceptable and already in the AC.

**Warning signs:**
- `git diff` of `.mcp.json` shows an inline string > 20 chars that doesn't look like a path
- `gitleaks detect --source .` flags a finding
- The Firecrawl dashboard shows API calls from an IP you don't recognize
- A GitHub security alert email arrives

**Phase to address:** HARNESS (pre-commit hook + `start-claude.sh` env-loader) + REPORT (README documents the rbw → env → claude flow for third-party reproduction).

---

### Pitfall 12: PII / real-applicant data in published artifacts

**What goes wrong:**
The prior wave used the "Jane Testworth" mock applicant — correct call. The risk this wave: screenshots, JSONL traces, accessibility-tree dumps, error logs may capture **other applicants' data** that leaks through the ATS. E.g., a Greenhouse "you have X applications in progress" sidebar might render real names if the test account picked up state from a prior session. CloakBrowser snapshots may include other tabs' content if the sandbox state leaks. Token-efficiency captures of "what came back from the MCP" may include autocomplete suggestions sourced from the browser profile's history. Once the screenshot is in `results/2026-05-XX/artifacts/`, it's on the public CDN forever.

**Why it happens:**
Real ATS pages have richer state than test fixtures suggest. Defaults expose more than the researcher notices. "I didn't see anything sensitive in the screenshot" is not the same as "there is nothing sensitive in the screenshot."

**How to avoid:**
1. **All MCP runs target the self-hosted snapshot fixtures from Pitfall 8, not live ATS pages.** Snapshots are pre-scrubbed for PII before commit (`sed` substitutions for any human name detected via `presidio-analyzer`).
2. **Screenshot diff-scan before commit.** `bench/scrub_artifacts.py` runs OCR (tesseract) on every PNG in `results/<date>/` and greps for the mock-applicant name; if anything else looks name-like (regex `[A-Z][a-z]+ [A-Z][a-z]+`), flag for human review. Don't auto-publish.
3. **JSONL trace scrub.** Every `tool_response.content` field gets the same name-regex scrub; flagged matches go to `results/<date>/REVIEW.md`.
4. **Fresh browser profile per MCP run.** No autocomplete history, no saved logins, no extensions. The harness deletes the profile dir before each MCP spawn.
5. **CloakBrowser specifically: sandbox-only per global rule.** Never run it against a Chromium that has touched a personal session. The harness uses a clean `--user-data-dir=<tmpdir>` per run.

**Warning signs:**
- `bench/scrub_artifacts.py` flags any name that isn't "Jane Testworth"
- A screenshot shows a sidebar with content you can't explain from the test fixture
- `vm_stat` shows browser profile bytes growing > 50MB during a run (history accumulating)
- Hacker News commenter posts "is that John Smith's real LinkedIn URL?"

**Phase to address:** HARNESS (snapshot-only fixtures + scrub script + clean-profile-per-run) + REPORT (every artifact passes scrub before commit; `REVIEW.md` resolved before publishing).

---

### Pitfall 13: Vendor-relationship blowback on low scores

**What goes wrong:**
This is a public, named comparison. The candidate MCPs are maintained by humans with feelings, Twitter accounts, and sometimes commercial interests. A 0/15 score for `browser-use` (because of a transport-mismatch bug per the testbench) or `obscura` (arch packaging gap) reads as "this tool is bad" to a casual reader, even when the failure is environment-specific and not the tool's fault. Vendors push back publicly. The repo gets an angry issue. The maintainer of a 95K-star project feels publicly punched-down-on. Trust in the methodology erodes regardless of whether the scoring was correct.

**Why it happens:**
Numbers travel without context. The composite score becomes the only thing readers remember. Vendors have a legitimate complaint when "they didn't test it right" is the actual story but the headline says "browser-use scored 0/15."

**How to avoid:**
1. **Per-MCP "as-evaluated" stanza in every result.** Each MCP row in the matrix has a hover-text / footnote: "Evaluated as `<package>@<version>` on `<date>` against `<fixture-set>` on `<machine-spec>` with `<config>`. Failures attributed to `<root cause taxonomy: tool-bug / env-mismatch / target-flag / transient>`." Failure attribution is part of the score.
2. **Pre-publication courtesy disclosure window.** Before publishing, file a draft `results/2026-05-XX.md` as a GitHub Draft PR + open a Linear ticket per vendor with the score + repro steps + 7-day comment window. Vendors get to flag "you ran it wrong" before the public sees the number. Honest pushback gets a re-run; PR feedback ignored = published as-is with the feedback linked.
3. **Methodology disclaimer header** on the public report:
   > Methodology evaluates MCPs as configured by their default install procedure on `<machine spec>` on `<date>`. Scores reflect this specific configuration and fixture set; they do not represent intrinsic tool quality. Reproducibility instructions in `README.md`; vendors and third parties are encouraged to challenge or rerun with corrections.
4. **Lead with capabilities, not failures.** Each MCP gets a "what it's best at" line before its score. Even the 0/15 entries get "best for X if Y" — `browser-use` is the SOTA AI-agent framework; the harness mismatch is a harness problem.
5. **Don't editorialize in scoring.** Numbers + neutral rationale only. Save opinions for `recommendations.md` where they're labeled as such.
6. **Use the public-comments-style rule** from global CLAUDE.md — Einstein's razor, reader-first, no AI-slop bullet ladders.

**Warning signs:**
- A vendor opens an issue titled "your benchmark is unfair"
- The 0/15 row's failure is something the harness could fix in < 1 hour
- A score row attributes a failure to "the MCP" when the root cause taxonomy would say "env-mismatch"
- Reddit/HN comments focus on the number, not the methodology — you didn't lead with the disclaimer

**Phase to address:** SCORE (define the failure-attribution taxonomy + per-row methodology stanza) + REPORT (disclaimer header + capabilities-first row format + courtesy-disclosure window).

---

### Pitfall 14: Scope creep mid-wave (the "while we're at it" tax)

**What goes wrong:**
Three days into the benchmark, someone notices `browsermcp` should really be tested too. Or "let's also score on a Lever fixture since we have time." Or "the rubric is missing a dimension for headless-vs-headful — let's add it." Each addition feels small in isolation. Cumulatively: the candidate set bloats from 7 to 9, the rubric grows from 8 to 10 dimensions invalidating all prior measurements, the comparison can't ship because new dimensions retroactively require all 7 candidates to be re-measured, and the Stage 1 → Stage 2 gating gets pushed by weeks. PROJECT.md already calls out `browsermcp` exclusion explicitly — but explicit exclusions get eroded under pressure.

**Why it happens:**
The MCP ecosystem is moving fast — new tools (Stagehand, Skyvern, Camoufox) appear weekly. Adding "one more" feels marginal. Rubric dimensions feel completable. PROJECT.md's "Out of Scope" gets reinterpreted as "we'll see."

**How to avoid:**
1. **Lock the candidate set + rubric on day 1 of the wave.** Sign-off commit: "Wave 2026-05 candidates: [7 names], rubric: [8 dims, weights as 2026-03]. Changes require closing the wave + opening Wave 2026-06."
2. **Scope-creep ledger.** Any "what if we also..." gets a row in `WAVE_DEFERRED.md` with date + proposer + linear ticket. Not implemented this wave. Reviewed at wave-close for the next wave's scope.
3. **`browsermcp` specifically: stays excluded.** Per PROJECT.md "different operational model." Add to `WAVE_DEFERRED.md` for a future wave with the Chrome-Agent profile rule documented.
4. **New cross-cutting dimensions (cold-start, TLS, bot-detection, token, stability) are already in this wave's scope** per PROJECT.md "Active" section. These are not creep. New dimensions beyond these five are creep.
5. **Stage 2 toolkit work is forbidden this wave.** PROJECT.md gates it. If the temptation to "start sketching the harness in terminal-craft" appears, file a Stage 2 ticket and stop touching that repo.

**Warning signs:**
- The candidate count in `.mcp.json` changes mid-wave
- A new column appears in `scoring/rubric.md` after the first PER-MCP run
- A linear sub-ticket gets opened for a candidate not in the original 7
- Someone opens a PR titled "while we're at it..."
- Stage 2 / terminal-craft commits appear in `git log` while Stage 1 results aren't published

**Phase to address:** REPORT (wave-close ritual: lock + ledger + sign-off) — but the scope guard runs every phase. Each phase's pre-flight is "is this in PROJECT.md Active? if no, ledger it."

---

### Pitfall 15: Cross-machine / cross-day non-reproducibility

**What goes wrong:**
The handoff notes the Mac Mini has all 7 binaries installed; the MacBook may not. If half the wave runs on Mac Mini and the other half on MacBook (different Chromium revisions, different network paths, different IP reputations, different CPU thermal profiles affecting timing), scores between candidates aren't directly comparable. Different days: TLS root-CA-bundle updates, npm registry latency, target site changes, network routing — all introduce variance.

**Why it happens:**
"Run it when I have time" feels innocent. Multi-day, multi-machine sprawl is invisible until the matrix doesn't reproduce.

**How to avoid:**
1. **Designate ONE benchmark machine for the wave.** Mac Mini per the handoff. Record machine spec in `results/<date>/MACHINE.md`: CPU, RAM, macOS version, Chromium version (from `versions.json`), network interface, ISP, ASN, IP-rotation strategy.
2. **Run all candidates in one calendar week** if possible. Within-week variance < between-week variance for live-target tests.
3. **Daily smoke gate.** Each benchmark day starts with a single canary task on a known-stable candidate (playwright-mcp on the local snapshot fixture). If canary timing > 2σ of historical, abort the day (likely network / OS state changed).
4. **NTP-synced timestamps** in every JSONL trace so cross-run timing is comparable.
5. **MacBook is for results-review only this wave.** Not for running benchmarks. Per handoff "MacBook parity not yet verified" — verify is a follow-up wave task, not a Stage 1 task.

**Warning signs:**
- `results/<date>/MACHINE.md` missing from any run
- Benchmark runs across > 14 calendar days for the same wave
- Cold-start numbers drift > 30% between runs of the same MCP a week apart
- Canary task fails the smoke gate but you run anyway "to save time"

**Phase to address:** HARNESS (canary smoke + `MACHINE.md` template + NTP-timestamp instrumentation) + CROSS (one-machine-one-week rule enforced at wave kickoff).

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hand-typed scores into the matrix without raw JSONL | Faster on day 1 | Cannot recompute when rubric changes; cannot audit single-run failures; vendors can't reproduce | **Never** — JSONL trace is non-negotiable from HARNESS onward |
| Live ATS URLs as fixtures (no snapshot) | No fixture-setup time | Reproducibility dies in 3-6 months (Pitfall 8); third parties get 404s | **Never** for a published wave |
| Skip the 3-pass retry gate "to save time" | 7x fewer test runs | Transient failure tanks a candidate (the BrowserMCP-disconnect class, Pitfall 1) | **Never** for the final scoring pass; OK for exploratory dry-runs |
| Single composite score, no capability matrix | Simpler headline | Apples-to-oranges hidden (Pitfall 2); vendors object to category-mismatched rankings | **Never** in the public report; OK in internal triage |
| `.mcp.json` with inline API key for "testing" | Skip rbw lookup | Public-repo leak (Pitfall 11); revoke + rotate + postmortem | **Never** — pre-commit hook enforces |
| Stealth claims based on vendor marketing | No empirical work needed | Stage 3 production failure when "passes Cloudflare" turns out to mean "passed the easy tier in March" | **Never** for a comparison artifact |
| Skip orphan-process audit | Faster runs | Memory pressure tanks late-run candidates (Pitfall 9); 1hr-stability scores are lies | **Only** for runs that don't feed the published matrix |
| Add a new rubric dimension mid-wave | Captures a new insight | Invalidates all prior measurements; wave can't ship | **Never** — defer to next wave per `WAVE_DEFERRED.md` |
| Skip the courtesy-disclosure window before publishing | Ship 1 week earlier | Vendor blowback (Pitfall 13) erodes trust in the methodology | **Never** for the public report |
| MacBook + Mac Mini split for "speed" | Parallel benchmark runs | Hardware-induced variance contaminates timing/stability scores (Pitfall 15) | **Only** if both machines pre-pass the canary smoke + lock the same `versions.json` |

---

## Integration Gotchas

Common mistakes when connecting to these specific services & runtimes.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **Claude Code → stdio MCP** | Trust Claude Code's MCP lifecycle to clean up child Chromiums | Wrap MCP spawn in `setsid` process group; harness owns `kill -KILL -<pgid>` cleanup (Pitfall 9; verified by [#33947](https://github.com/anthropics/claude-code/issues/33947)) |
| **Claude Code → stdio MCP** | Trust Claude Code's `initialize` timeout | Harness enforces its own 30s `initialize` timeout — Claude Code has no enforced timeout ([#35287](https://github.com/anthropics/claude-code/issues/35287)) |
| **firecrawl MCP** | Hardcode `FIRECRAWL_API_KEY` in `.mcp.json` | `"env": {"FIRECRAWL_API_KEY": "${FIRECRAWL_API_KEY}"}`; load via rbw before launching Claude |
| **cloakbrowser MCP** | Point at a logged-in Chrome session for "stealth + auth" testing | Sandbox-only per global rule; closed-source binary touches cookies; clean `--user-data-dir` per run |
| **obscura MCP** | Enable `--stealth` on macOS | Don't. Sec-CH-UA-Platform-* leaks (Pitfall 7 + Vitalik's existing browser-tools doc). Use without `--stealth`, accept the JA4 hit |
| **browser-use MCP** | Score it head-to-head with playwright on a Claude-driven composite | Run two modes (`direct` + `agent`); label `agent` mode as "MCP solved via internal LLM call"; segment in the capability matrix (Pitfall 2) |
| **lightpanda MCP** | Score Ashby S2 as `0` reliability | Score as `N/A — JS engine doesn't support React/SPA`; document the structural limit, don't penalize |
| **chrome-devtools MCP** | Treat the `exposes content of the browser instance to the MCP client` stderr warning as a failure | Suppress in the harness (`stderr=DEVNULL` after capturing once); the 2026-05 testbench docked it 1 stability point — don't repeat |
| **playwright MCP** | Use `browser_select_option` on Greenhouse React Select dropdowns | Use `browser_run_code` or type+Enter pattern (documented in prior wave + Vitalik's `browser-tools.md` Recipes) |
| **All MCPs that spawn Chromium** | Let them share `~/Library/Caches/ms-playwright` | Set `PLAYWRIGHT_BROWSERS_PATH=fixtures/browsers/` per MCP run to a pinned version path; isolates from "another MCP's `playwright install` upgraded my Chromium" races |
| **All MCPs** | Single-pass scoring | 3-pass-of-3 with median + transient-failure taxonomy (Pitfall 1) |

---

## Performance Traps

Patterns that work for 1-2 candidates but fail at the 7-candidate wave scale.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential candidate runs with no idle gap | Run #4+ scores poorly; IP reputation flagged | 10+min idle between bot-detection candidates; randomized order; per-candidate residential IP if budget allows | At candidate #3-4 on the same /24 hitting Cloudflare |
| Single benchmark machine, multi-hour run, no orphan audit | Memory pressure + swap; late-run candidates score "unstable" | Process-group spawn + post-run kill; `ulimit -v` per MCP (Pitfall 9) | At ~45min of a 60min stability test on a 24GB machine running 3 Chromiums |
| Shared `~/.npm/_cacache` / shared Chromium download dir | Race condition on parallel `npm install` / `playwright install` | Per-MCP `PLAYWRIGHT_BROWSERS_PATH` + `npm_config_cache=<per-mcp-dir>` | When `bench/` parallelizes candidate setup, even one race corrupts the cache for all |
| Capturing all-tab JS context for token analysis | Multi-GB JSONL traces; grep takes minutes | Capture only `tool_response.content`; tokenize at write-time; rotate JSONL per task | After ~50 tasks of full-capture |
| Live ATS pages for the 1hr stability test | Target rate-limits mid-test; reliability score for stability collapses | 1hr stability test uses the self-hosted snapshot server; live-URL smoke is separate, daily | At ~minute 20 of 60 on a Greenhouse target |
| `tshark` capturing all interfaces for TLS fingerprinting | Captures Claude Code's API calls, npm, telemetry — wrong fingerprint attributed (Pitfall 5) | `mitmproxy` upstream-mode per MCP + cross-check vs peet.ws | First run; the data is plausibly wrong without anyone noticing |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| API key in committed `.mcp.json` | Public-repo leak, billing/abuse, rotation pain | `${VAR}` references only; rbw env-load; pre-commit hook regex-checks `.mcp.json` (Pitfall 11) |
| Screenshot artifacts contain other applicants' PII | Public CDN leak of real user data — GDPR/CCPA exposure | Snapshot-only fixtures, scrub all PNGs via tesseract+regex, fresh browser profile per run (Pitfall 12) |
| CloakBrowser run against authenticated personal Chrome session | Closed-source binary touches cookies; credential exfil risk | Sandbox-only; clean `--user-data-dir=<tmpdir>`; never against `~/Library/Application Support/Google/Chrome` (matches global rule) |
| `cloakbrowser` / `browser-use` self-update during a wave | Untested binary in the published matrix; reproducibility breaks | `versions.lock.md` + `versions.json` capture + fail-on-mismatch (Pitfall 10); pin `uv tool install <name>==<version>` |
| Cloud MCPs (firecrawl) — assume server-side is benchmarked | Server-side scraping logic isn't pinned; vendor changes invalidate scores silently | Capture response signatures + API version header; treat firecrawl score as "as-of date X" with explicit caveat |
| Sharing the `.mcp.json` between Stage 1 (this repo) and Stage 2 (terminal-craft) | Sandbox-only MCPs accidentally promoted to authenticated contexts | Stage 2 packaging is gated; Stage 1's `.mcp.json` stays in this repo; per G-703 scope discipline |
| TLS-capture artifacts include `Authorization` headers from incidental requests | Leaked tokens in `results/<date>/tls_captures/` | `mitmproxy` flow files are gitignored; only `.ja4` summary lines committed; pre-commit regex-checks for `Bearer ` / `Authorization:` |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **All 7 MCPs scored:** verify each has `n/3 passes` recorded, not just "passed" — single-pass scores are vulnerable to the BrowserMCP-disconnect class
- [ ] **Cold-start measured:** verify the 3-segment split (`t_resolve` / `t_spawn` / `t_first_useful`) was captured both cold and warm, not just one number
- [ ] **Token efficiency measured:** verify all three scopes (`schema` / `payload` / `turn`) are in the JSONL, with the payload number as the published headline
- [ ] **Bot-detection tested:** verify each result includes IP + ASN + observed-challenge-tier, not just pass/fail, and target was a stable adversary (bot.sannysoft / fingerprint.com / a controlled CF Worker) not just "Cloudflare-protected site we found"
- [ ] **TLS fingerprint captured:** verify the JA4 was cross-checked against peet.ws within the same MCP process, not the host's default TLS stack
- [ ] **Stealth claims verified:** verify the JS UA matches the Sec-CH-UA-Platform HTTP header for every "stealth" MCP — Pitfall 7 catches obscura's `--stealth`-on-macOS leak by default
- [ ] **Stability ran 1hr:** verify the post-run orphan audit shows 0 survivors and memory-ceiling enforcement was active — otherwise the score is "harness leaked, not MCP unstable"
- [ ] **Reproducibility:** verify `versions.lock.md` + `versions.json` + `MACHINE.md` are all committed and present for every run in `results/<date>/`
- [ ] **Public-repo hygiene:** `git diff main -- .mcp.json` shows no inline secrets; `gitleaks detect --source .` clean; `bench/scrub_artifacts.py` clean on `results/<date>/`
- [ ] **Methodology disclaimer:** report header explicitly says "evaluated as of `<date>` with configuration `<X>`; not intrinsic tool quality" — vendors get the framing right
- [ ] **Courtesy disclosure window:** every vendor with score < 5 has had ≥7 days with the draft + Linear ticket before publication
- [ ] **Stage 2 not started:** `git log --oneline ~/Projects/terminal-craft/` shows no Stage-2-toolkit commits dated after this wave's kickoff

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Transient failure tanked a score (Pitfall 1) | LOW (if retry gate exists) | Re-run failed task 3x in fresh sessions on a different day; replace score with median; footnote the matrix row |
| Apples-to-oranges score published (Pitfall 2) | MEDIUM | Republish with capability matrix + segmentation; redirect old URL to corrected; vendor mea culpa in `recommendations.md` |
| Cold-start measured wrong (Pitfall 3) | LOW-MEDIUM | Re-run all 7 candidates with 3-segment + cold/warm split; replace single number with the 6-cell expansion |
| Token count contaminated (Pitfall 4) | LOW | Re-tokenize from the raw JSONL captures (assuming `tool_response.content` was captured); republish `payload` column |
| TLS fingerprint wrong process (Pitfall 5) | MEDIUM | Re-run TLS capture per MCP via mitmproxy + peet.ws cross-check; mark prior numbers as "captured incorrectly, see corrected" |
| Bot-detection target flagged the IP (Pitfall 6) | HIGH | Rotate IP, wait 24-48hr, re-run all bot-detection tests in randomized order with 10min gaps; document the burned IP in `MACHINE.md` |
| Sec-CH-UA-Platform leak shipped (Pitfall 7) | LOW (test) / HIGH (production) | Add the echo-server header diff test; re-score stealth claims; for production: never trust a stealth MCP that didn't pass the header test |
| Public fixture URL 404'd (Pitfall 8) | MEDIUM | Snapshot now; switch tests to self-hosted; commit; document in `PROVENANCE.md` why the snapshot date is "after-the-fact" |
| Orphan-process accumulation (Pitfall 9) | LOW (reboot) | `pkill -9 -f '(chromium\|playwright\|obscura\|cloak\|firecrawl\|browser-use)'`; reboot; add process-group + audit before next run |
| Version drift between researchers (Pitfall 10) | MEDIUM | Capture both `versions.json`s; diff; the run that doesn't match `versions.lock.md` is discarded; re-run with locked versions |
| API key leaked to public repo (Pitfall 11) | HIGH | Rotate immediately (firecrawl dashboard); `git filter-repo` to scrub history; force-push (notify Vitalik first per the never-force-push-main rule); audit billing for unauthorized use; postmortem in Linear |
| PII in published artifact (Pitfall 12) | HIGH | Delete artifact + force-push history scrub + GitHub support ticket to purge from CDN; notify affected individuals if identifiable; postmortem |
| Vendor blowback (Pitfall 13) | MEDIUM | Public response: link the methodology stanza + offer to re-run with vendor's correction; if methodology was wrong, republish with the fix and a top-of-page correction note |
| Scope creep mid-wave (Pitfall 14) | MEDIUM | Stop. Lock current scope at last clean point. New additions → `WAVE_DEFERRED.md` for next wave. Don't re-litigate the current wave |
| Cross-machine/cross-day variance (Pitfall 15) | HIGH | Re-run all affected candidates on one machine in one week; mark prior data as exploratory; rebuild the matrix from the consistent set |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| **1. Transient-failure tank** | HARNESS + SCORE + REPORT | JSONL shows 3 attempts per task; published matrix shows `n/3`; failed candidates have a footnote |
| **2. Apples-to-oranges categories** | SCORE + REPORT | Capability matrix exists alongside composite; N/A cells correctly drop from weighted denominator; browser-use scored in both modes |
| **3. Cold-start hides Node resolution** | CROSS + HARNESS | All cold-start cells have 3 timed segments + cold/warm pair; cache-flush script committed |
| **4. Token-count contamination** | CROSS + HARNESS | JSONL has `tokens_schema/payload/turn`; report column is `payload`; tokenizer documented |
| **5. TLS fingerprint wrong process** | CROSS + HARNESS | Each MCP's JA4 captured via mitmproxy; cross-check vs peet.ws logged; harness fails if mismatch |
| **6. Bot-detection threshold drift** | CROSS + HARNESS + REPORT | Each bot-test result includes IP/ASN/tier/timestamp; stable adversaries used; live-target claims are scoped not absolute |
| **7. Sec-CH-UA-Platform leak** | CROSS + HARNESS + REPORT | `stealth_leak_test.py` runs in CI; every stealth row in matrix cites which tests passed/failed; obscura `--stealth`-on-macOS disabled |
| **8. Public-fixture rot** | HARNESS + CROSS | `fixtures/snapshots/<date>/` committed; tests target `127.0.0.1`; daily live-URL smoke gate separate |
| **9. Orphan-process accumulation** | HARNESS + CROSS | Process-group spawn + pre/post audit log + memory ceiling per run; orphan count = 0 enforced |
| **10. Version drift** | HARNESS + REPORT | `versions.lock.md` committed; `versions.json` per run; harness fails on mismatch |
| **11. Secrets in `.mcp.json`** | HARNESS | Pre-commit hook regex-blocks inline secrets; `start-claude.sh` env-loader documented in README |
| **12. PII in artifacts** | HARNESS + REPORT | Snapshot-only fixtures; `scrub_artifacts.py` clean; clean profile per run; `REVIEW.md` resolved before commit |
| **13. Vendor blowback** | SCORE + REPORT | Per-row methodology stanza; 7-day courtesy disclosure window logged in Linear; failure attribution taxonomy applied |
| **14. Scope creep** | REPORT (wave-close ritual) + every phase pre-flight | `WAVE_DEFERRED.md` exists; `.mcp.json` candidate count unchanged from wave start; rubric column count unchanged |
| **15. Cross-machine/cross-day variance** | HARNESS + CROSS | `MACHINE.md` per run; one-machine-one-week rule enforced; canary smoke gate fails the day on drift |

---

## Sources

- **Prior wave artifacts** — `/Users/pleasedodisturb/Projects/web-agent-comparison/results/2026-03-31_run.md` (BrowserMCP disconnect documented; rubric established; React Select gotcha; token-efficiency 20x spread)
- **Vitalik's global browser-tools doc** — `/Users/pleasedodisturb/.claude/docs/browser-tools.md` (Sec-CH-UA-Platform-* leak on macOS, TLS-fingerprint dominance, headless-vs-headful leak triplet, CloakBrowser sandbox-only rule, chrome-devtools stderr warning)
- **G-688 scope discipline lesson** — `/Users/pleasedodisturb/.claude/projects/-Users-pleasedodisturb-Projects-screenpipe/memory/feedback_mcp_scope_discipline.md` (Python.app dock-pollution tell; user-vs-project scope rule)
- **Project scope & constraints** — `/Users/pleasedodisturb/Projects/web-agent-comparison/.planning/PROJECT.md` (8-dimension rubric, candidate set, Stage 1 gating, partial-scoring rule for missing firecrawl key, public-repo `.mcp.json` acceptance)
- **Handoff for the next session** — `/Users/pleasedodisturb/Projects/web-agent-comparison/HANDOFF.md` (MacBook parity unverified, Mac Mini all-installed, Stage 1/2/3 pipeline)
- **TLS-fingerprint primary research** — [When Handshakes Tell the Truth: Detecting Web Bad Bots via TLS Fingerprints (arXiv 2602.09606, 2026)](https://arxiv.org/abs/2602.09606) — CatBoost+JA4 AUC 0.998; XGBoost feature importance places `ja4_b` first, then cipher_count + ext_count
- **Cloudflare / Auth0 on JA4 in production bot-detection** — [Strengthening Bot Detection with JA4 Signals (Auth0, 2026)](https://auth0.com/blog/strengthening-bot-detection-ja4-signals/), [TLS Fingerprinting Guide 2026 (proxies.sx)](https://www.proxies.sx/use-cases/privacy/tls-fingerprint)
- **Claude Code MCP lifecycle bugs** — [stdio hang on init (#35287)](https://github.com/anthropics/claude-code/issues/35287), [orphan accumulation macOS PPID=1 (#33947)](https://github.com/anthropics/claude-code/issues/33947), [orphan processes general (#1935, #22612)](https://github.com/anthropics/claude-code/issues/22612), [SIGTERM-to-healthy-MCPs (#40207)](https://github.com/anthropics/claude-code/issues/40207), [Windows orphan (#15211)](https://github.com/anthropics/claude-code/issues/15211)
- **User-Agent Client Hints reference** — [web.dev: User-Agent Client Hints](https://web.dev/articles/user-agent-client-hints) (Sec-CH-UA-Platform emitted by network stack, not JS)
- **JA4 fingerprinting tooling** — [FoxIO-LLC/ja4 (GitHub)](https://github.com/FoxIO-LLC/ja4); cross-check service `https://tls.peet.ws/api/all`

---
*Pitfalls research for: MCP-layer browser-server benchmark, Claude-Code-driven, 7-candidate comparison (wave 2026-05)*
*Researched: 2026-05-22*
