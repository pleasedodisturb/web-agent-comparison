# Stack Research — MCP Browser-Server Benchmark (Wave 2)

**Domain:** Public benchmark / test harness for 7 MCP-layer browser servers, scored against a locked 8-dimension rubric on Greenhouse + Ashby job-application fixtures. Stage 1 of a 3-stage pipeline (this repo → terminal-craft toolkit → Kestrel/Eyas agents).
**Researched:** 2026-05-22
**Confidence:** HIGH on candidate versions and external measurement tooling; MEDIUM on internal harness orchestration (no off-the-shelf MCP benchmark fits exactly).

---

## 1. Verified Latest Stable Versions of the 7 Candidate MCPs

All seven version strings in `HANDOFF.md` / `.mcp.json` were re-checked against npm registry, PyPI, and GitHub on 2026-05-22. Two are stale, one has a non-obvious provenance change, and Lightpanda's "0.3.0" needs an asterisk.

| # | MCP (handoff name) | Handoff version | **Verified latest stable (2026-05-22)** | Status | Source of truth |
|---|---|---|---|---|---|
| 1 | `playwright` (`@playwright/mcp`) | 0.0.75 | **0.0.75** (`dist-tags.latest`, published 2026-05-07) | ✅ Current | npm — `next` tag at `0.0.75-alpha-2026-05-22` is a nightly, do not pin |
| 2 | `browser-use` (PyPI `browser-use`) | 0.12.7 | **0.12.7** (PyPI latest, GitHub tag `0.12.7`) | ✅ Current | PyPI + github.com/browser-use/browser-use |
| 3 | `chrome-devtools` (`chrome-devtools-mcp`) | 1.0.1 | **1.0.1** (npm latest, published 2026-05-18 — note the 0.26.0 → 1.0.0 → 1.0.1 GA jump four days before this research) | ✅ Current (just GA'd) | npm + github.com/ChromeDevTools/chrome-devtools-mcp releases |
| 4 | `lightpanda` (binary) | 0.3.0 | **`v0.2.6` tagged stable (2026-02-19)** vs `nightly` (rolling, asset updated 2026-05-22, binary self-identifies as `0.3.0` in some builds and `0.1.0` in the MCP JSON-RPC handshake per browser-tools.md 2026-05-21 verification) | ⚠️ Semantic mismatch | github.com/lightpanda-io/browser releases |
| 5 | `obscura` (`obscura-mcp` npm wrapper) | 0.1.4-2 | **0.1.4-3** (npm latest, published 2026-05-08 — one patch newer than handoff) | ⚠️ One patch behind | npm — wrapper around `h4ckf0r0day/obscura` Rust engine, separate install |
| 6 | `firecrawl` (`firecrawl-mcp` npm) | 3.17.0 | **3.17.0** on `dist-tags.latest` (published 2026-05-17). GitHub main is already at 3.18.0 (publish lag); GitHub release tags stop at v3.2.1 (Sept 2025) — they stopped cutting GitHub releases mid-2025 but kept publishing to npm | ✅ Current, **but** see Pitfall #1 below | npm + repo `git+https://github.com/firecrawl/firecrawl-mcp-server.git` |
| 7 | `cloakbrowser` (`cloakbrowsermcp` PyPI) | 2.0.4 | **2.0.4** (PyPI latest, only 5 releases ever: 2.0.0 → 2.0.4) | ✅ Current | PyPI — source repo `github.com/overtimepog/CloakMCP`, author `overtimepog`, closed-source binary |

**Pin recommendation for the reproducibility manifest:**

```text
# package.json (npm-based MCPs)
@playwright/mcp                 0.0.75
chrome-devtools-mcp             1.0.1
obscura-mcp                     0.1.4-3       # bump from handoff
firecrawl-mcp                   3.17.0

# pyproject.toml / uv tool install
browser-use                     0.12.7
cloakbrowsermcp                 2.0.4

# Binary (no package manager)
lightpanda (lightpanda-aarch64-macos asset, sha256 captured at install time)
                                nightly@2026-05-22  # the rolling release
                                — OR —
                                v0.2.6              # the last semver-tagged stable
```

**Recommendation:** pin to `v0.2.6` for Lightpanda if reproducibility outranks recency. The `nightly` asset is rebuilt continuously and will silently shift under the manifest. The 2026-03-31 wave used 0.3.0 (nightly); preserve that for direct comparability **and** add `v0.2.6` as a sanity sweep.

### Known breaking changes since the listed versions

- **chrome-devtools-mcp v0.26.0 → v1.0.0** (2026-05-18, 4 days before research): API stabilization release. Confirmed no schema break vs. v0.26.0 in the release notes, but treat the v1.0.x line as "officially GA" and re-snapshot tool inventory before scoring.
- **`@playwright/mcp` 0.0.74 → 0.0.75**: 24 hours apart, patch-only.
- **firecrawl-mcp 3.16.0 → 3.17.0**: 3 days apart, patch cadence is high — see Pitfall #1 for supply-chain hygiene.
- **browser-use 0.12.0 → 0.12.7**: 7 patch releases in ~2 months. Their `--mcp` stdio transport had a documented mismatch in the 2026-05-21 sandboxed testbench (browser-tools.md, score 0/15 with timeout on every `initialize`). **Re-test with 0.12.7 before scoring** — that bug may already be fixed.

**Confidence: HIGH.** All seven version strings were fetched live from the canonical registry today.

---

## 2. Test Harness — Recommended Core Stack

This is a custom harness, not a fork of an existing framework. The reasons are spelled out under §"Alternatives Considered."

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.12 (`.python-version`) | Scoring engine (extends existing `scoring/score.py`), harness orchestration, result aggregation | Project already standardized on Python 3 per CONSTRAINTS in `PROJECT.md`; existing `scoring/score.py` is the load-bearing artifact. 3.12 is the modern stable; avoid 3.14 (released 2026-05) — too new for downstream deps including some MCP SDK extras. |
| **uv** | 0.7.x (pin in CI) | Python environment + lockfile + `uv tool install` for `browser-use` and `cloakbrowsermcp` | Already in use across the toolchain. `uv.lock` committed gives bit-for-bit reproducibility. Avoid pip+requirements.txt — no transitive pinning. |
| **Node.js** | 22 LTS | Runtime for the 4 npm-based MCPs (playwright, chrome-devtools, obscura, firecrawl) and MCP Inspector | 22 LTS is the active LTS through 2027-04 (per nodejs.org schedule). Avoid Node 24 — too fresh, some MCP servers pin older engines. |
| **`@modelcontextprotocol/inspector`** | 0.21.2 | Per-MCP smoke test (`tools/list`, single tool call) in CLI mode for the cold-start measurement and tool-inventory snapshot | Official Anthropic tool, has a `--cli` flag with JSON output, exit codes suitable for CI. Replaces hand-rolled JSON-RPC clients for the "is this MCP alive?" check. |
| **Bash 5+** | system | Test orchestration (`scripts/*.sh`), already the project pattern | Per PROJECT.md constraint "shell (test orchestration). No framework — keep it dogfood-friendly." Don't introduce make/just unless the matrix grows past 30 cells. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `mcp` (Python SDK) | 1.16.x | Stdio client for the bespoke cold-start timer + 1-hour stability soak; raw `initialize → tools/list → first tool call` timings | Use when MCP Inspector's CLI mode is too coarse (it adds Node startup overhead to every measurement). The Python `mcp.client.stdio` lets you measure the server alone. |
| `anthropic` (Python SDK) | 0.40.x | Programmatic token counting via `client.messages.count_tokens()` for the Token Efficiency dimension | Use to score tool-call payloads independently of the live Claude Code session. Free, no rate-limit cost. |
| `httpx` | 0.28.x | One-shot calls to TLS fingerprint capture endpoints (Scrapfly, tls.peet.ws) from inside each MCP's browser | Lightweight, already a transitive dep of most of the toolchain. |
| `pytest` + `pytest-benchmark` | 8.x / 5.x | Wrap cold-start, latency-per-tool, and 1hr-stability runs in a single pytest matrix; emit JSON for the scoring engine | Only if the harness grows past ~7 scripts. Today's `scripts/` style is fine; add pytest when adding a 9th MCP or a third fixture site. |
| `jq` | 1.7+ (Homebrew) | Parse MCP Inspector CLI's JSON output in shell pipelines | Already standard in the workflow. |
| `tshark` | 4.x (Wireshark) | JA3/JA4 extraction from local pcap captures when external endpoints are blocked or rate-limited | Fallback. The primary path is Scrapfly's HTTP endpoint, not packet capture (see §3 Measurement Tooling). |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `direnv` + `.envrc` | Inject `FIRECRAWL_API_KEY` from `rbw` only when entering the repo dir | Per PROJECT.md secrets policy. Add `.envrc` to `.gitignore`; check in `.envrc.example`. |
| `pre-commit` | Lint shell + Python on commit, sanity-check `.mcp.json` JSON validity | Optional. Repo currently has no hooks — add only if multiple contributors land. |
| `bandit` | Python security lint, especially around the closed-source `cloakbrowser` invocation | Optional. CloakBrowser is sandbox-only per global policy; bandit is belt-and-suspenders. |

---

## 3. Measurement Tooling for the Cross-Cutting Concerns

These are the four "new" measurements this wave needs that the 2026-03-31 wave didn't formalize. Each gets ONE primary tool with a concrete invocation.

### 3.1 Cold-start latency (process spawn → first usable tool call)

**Primary tool:** Custom Python script using `mcp.client.stdio.stdio_client` from the official Python MCP SDK.
**Why not MCP Inspector?** Inspector's `--cli` mode adds ~300-500ms of Node.js startup to every measurement, which is the same order of magnitude as what we're measuring. The Python SDK over raw stdio is 30-50ms of overhead.

**Concrete recipe (drop into `scripts/measure_cold_start.py`):**

```python
import asyncio, time, json, statistics
from mcp.client.stdio import stdio_client, StdioServerParameters

async def measure(cmd: str, args: list[str], runs: int = 5) -> dict:
    samples = {"spawn_to_initialized": [], "spawn_to_first_tool_response": []}
    for _ in range(runs):
        t0 = time.perf_counter()
        params = StdioServerParameters(command=cmd, args=args)
        async with stdio_client(params) as (read, write):
            from mcp import ClientSession
            async with ClientSession(read, write) as session:
                await session.initialize()
                t1 = time.perf_counter()
                samples["spawn_to_initialized"].append(t1 - t0)
                tools = await session.list_tools()
                # Pick a no-op tool per MCP (e.g. browser_install for playwright is too heavy;
                # tools/list is the cheapest universal probe — already done above)
                t2 = time.perf_counter()
                samples["spawn_to_first_tool_response"].append(t2 - t0)
    return {
        k: {"median": statistics.median(v), "p95": sorted(v)[int(len(v)*0.95)], "samples": v}
        for k, v in samples.items()
    }

# Invoke per MCP from .mcp.json
```

Report **median of 5 cold starts**, not single-shot. Lightpanda's 1.8s number from the prior wave was single-shot — re-measure.

**Confidence: HIGH** — this is the canonical pattern in MCP Inspector source and `modelcontextprotocol/python-sdk` examples.

### 3.2 TLS fingerprint (JA3 / JA4) per MCP

**Primary tool:** Drive each MCP to navigate to `https://tools.scrapfly.io/api/fp/ja3?extended=1` and capture the JSON response.
**Verified live 2026-05-22** — endpoint returns: `ja3`, `ja3n`, `ja3_digest`, `ja3n_digest`, `scrapfly_fp`, `scrapfly_fp_digest`, `ja4`, `ja4_r`, `ja4_hash`, plus a `tls` object with cipher suites and extensions. One HTTP request, full result.

**Backup tools (in priority order):**
1. `https://tls.peet.ws/api/all` — TrackMe project (github.com/wwhtrbbtt/TrackMe), returns JA3 + Akamai HTTP/2 + custom `PeetPrint`. Use if Scrapfly rate-limits.
2. `https://www.browserscan.net/tls` — has an API, HTML response (parse it).
3. **Local capture fallback:** `sudo tshark -i any -f "host fp.endpoint.example and tcp port 443" -w cap.pcap` then `tshark -r cap.pcap -T fields -e tls.handshake.ja4`. Only use this if all external endpoints are blocked — adds sudo dependency that breaks reproducibility.

**What "drive the MCP to navigate" means per candidate:**
- `playwright`: `browser_navigate("https://tools.scrapfly.io/api/fp/ja3?extended=1")` + `browser_evaluate("() => document.body.innerText")`
- `chrome-devtools`: `navigate_page` + `evaluate_script` returning `document.body.innerText`
- `browser-use`: `act` or `extract` against the same URL
- `cloakbrowser`: `cloak_navigate` + `cloak_read_page`
- `obscura`: equivalent navigate + read
- `lightpanda`: `lightpanda fetch <url>` (cold path; cannot do MCP-native)
- `firecrawl`: `firecrawl_scrape` — this measures **Firecrawl's cloud TLS fingerprint**, not the local process's, which is the point (their cloud is what hits the target site).

**Critical caveat per browser-tools.md:** TLS fingerprinting (JA4) reports AUC 0.998 for bot/human classification — only `cloakbrowser` and BrowserMCP (excluded this wave) are expected to pass real-Chrome fingerprint discrimination. The benchmark's job is to **publish the JA3/JA4 hashes** so readers can independently verify which MCPs match the real-Chrome 125,000-sample reference set Scrapfly maintains.

**Confidence: HIGH** — endpoint tested live 2026-05-22, schema confirmed.

### 3.3 Bot-detection signal harvesting (Cloudflare, DataDome, reCAPTCHA, Akamai)

**Primary tool:** Direct HTTP response inspection via each MCP's `evaluate`/`fetch` capability against a curated probe set, plus snapshot of any 403/429/503 response body + headers.

**Concrete probe set to drive each MCP at:**

| Probe URL | Detector | What to capture |
|---|---|---|
| `https://nowsecure.nl/` | Cloudflare bot management (well-known canary) | Response status, `cf-mitigated` header, `cf-ray`, presence of challenge HTML (`/cdn-cgi/challenge-platform/`) |
| `https://www.g2.com/products/anthropic/reviews` | DataDome | Status, `x-datadome-cid` cookie, `x-datadome` response header, presence of `_dd_s` cookie |
| `https://www.google.com/recaptcha/api2/demo` | reCAPTCHA v2 challenge type | Page loads → eval `grecaptcha.getResponse()` shape, screenshot for visual challenge classification |
| `https://www.akamai.com/` | Akamai Bot Manager | `_abck` cookie, `bm_sz` cookie, status code |

**Signals to log per MCP per probe:**
1. HTTP status (200/403/429/503)
2. `cf-mitigated` header value (`challenge`, `block`, absent)
3. `cf-ray` (presence = Cloudflare in path; pattern of suffix = colo)
4. Cookie names matching `_dd_s|datadome|_abck|bm_sz|cf_clearance`
5. Final URL after redirects (challenge page vs. real content)
6. Page text length and presence of detector strings ("Just a moment...", "Please verify", "challenge-platform")

**Implementation:** A Python orchestrator drives the MCP, captures the snapshot/text, runs a `re.search` for each signal, and emits a JSON row per (mcp, probe). Score 0-10 per the rubric's Reliability dimension.

**Confidence: MEDIUM** — `cf-mitigated: challenge` is the canonical Cloudflare bot-managed-response signal (verified in Cloudflare community discussions and the curl_cffi #591 discussion thread), but the probe URLs above are externally hosted and may shift their detection posture between research and benchmark execution. **Re-validate the probe URL list immediately before the benchmark run** and pin the date of the probe in the published results.

### 3.4 Token accounting per MCP tool call

**Primary tool:** Anthropic SDK's `client.messages.count_tokens(model=..., system=..., tools=..., messages=...)` against the actual tool payload, run **out-of-band** from Claude Code.

**Why not just read Claude Code's session JSONL?** That's the easy path, but it mixes the harness's own tokens with the per-MCP tokens, and `ccusage` aggregates per-session, not per-MCP-tool-call. The clean signal comes from:

1. Capture the raw MCP tool response (the JSON-RPC `result` payload) per (mcp, stage) into `results/raw/{mcp}_{stage}.json`.
2. Run `count_tokens` on the response wrapped as a `tool_result` block to get the **exact** input-token cost that response would incur in a Claude turn.
3. For the schema overhead (tool list injected on every turn), call `count_tokens` once per MCP with just the `tools=` parameter populated from `tools/list`.

**Two-line snippet:**

```python
from anthropic import Anthropic
client = Anthropic()
resp = client.messages.count_tokens(
    model="claude-opus-4-7",  # match the model used in the live test
    tools=[{"name": t["name"], "description": t["description"], "input_schema": t["inputSchema"]}
           for t in mcp_tools_list],
    messages=[{"role": "user", "content": prompt}],
)
print(resp.input_tokens)
```

`count_tokens` is **free** (no API cost), separate rate limit from `messages.create`. This is the only way to get apples-to-apples token numbers across MCPs whose Claude turn isn't necessarily controllable.

**Confidence: HIGH** — verified against `platform.claude.com/docs/en/build-with-claude/token-counting` (Anthropic official docs).

---

## 4. Reproducibility Model

**Recommendation: shell script + `uv.lock` + `package-lock.json` + pinned binary checksums + a Justfile, all in the repo. No Docker, no devcontainer.**

### Why not Docker?

- The benchmark needs to measure **real cold-start latency** on the host. Docker adds a layer of indirection (image pull, container start, FS overlay) that contaminates the metric we care most about.
- `cloakbrowser` is sandbox-only with a closed-source binary that "touches cookies on launch" (per browser-tools.md). Running it in a container changes its launch profile.
- TLS fingerprint capture inside Docker yields a Docker TLS fingerprint, not the host's. Useless.
- Two of seven MCPs (cloakbrowser, browser-use Chromium tier) need GUI/display access on macOS that's painful to plumb through Docker.

### Why not devcontainer?

- Same TLS-fingerprint contamination as Docker (it IS Docker).
- The audience is people running the same MCPs from Claude Code on their own machine. Their reproducibility is what we want to validate.

### What to ship instead

```text
.tool-versions          # asdf-compatible: node 22, python 3.12, uv 0.7.x
.python-version         # 3.12
.envrc.example          # FIRECRAWL_API_KEY=... (real key from rbw)
.mcp.json               # already exists, already pins via command names — add SHA256 of binaries
uv.lock                 # generated by `uv lock`, committed
package.json + package-lock.json  # for the 4 npm-based MCPs as devDeps
justfile                # `just bench`, `just bench-cold-start`, `just bench-mcp playwright`
scripts/
  bootstrap.sh          # one-shot: installs all 7 MCPs at the pinned versions, prints SHA256
  measure_cold_start.py
  measure_tls_fp.py
  measure_bot_detection.py
  measure_tokens.py
  run_stages.sh         # drives S1-S8 per MCP, writes results/raw/
docs/REPRODUCIBILITY.md # exact "macOS aarch64 with Apple M-series, 16GB RAM, Claude Code 2.1.81" recipe
```

**The reproducibility manifest itself:** a `manifest.toml` (or `.json`) at repo root listing every pinned version + sha256:

```toml
[mcps.playwright]
package = "@playwright/mcp"
version = "0.0.75"
npm_integrity = "sha512-..."   # captured from npm view

[mcps.lightpanda]
asset_url = "https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-aarch64-macos"
asset_sha256 = "..."           # captured at install time, committed
asset_pinned_at = "2026-05-22T12:00:00Z"
```

This is the single document a reader uses to verify their install matches the one that produced the scores.

**Confidence: HIGH** on the structure (matches how AgentLab / WebArena-Verified ship — script + lockfile + optional container), MEDIUM on the "no Docker" call vs. AgentLab's pattern. The trade-off is conscious: AgentLab's Docker images are for the **test sites** (a frozen Reddit, a frozen GitLab); we don't need that because our test sites are **live external SaaS** (Greenhouse, Ashby), so Docker buys us nothing on the target side and costs us on the measurement side.

---

## 5. Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Custom harness extending `scoring/score.py` | **AgentLab + BrowserGym** (ServiceNow, the maintained 2026 successor to WebArena) | If we wanted to score 30+ MCPs across 100+ tasks. For 7 × 8, it's massive overkill and the BrowserGym task format would force a rewrite of all fixtures. |
| Custom harness | **MCP-Bench** (Accenture, arXiv 2508.20453) | MCP-Bench is for *LLM tool-use capability* — 250 tools across 28 MCP servers, scored on planning and trajectory quality. Wrong axis: we score the *MCP servers' browser capability*, not Claude's ability to chain them. |
| Custom harness | **MCPBench** (modelscope) | Same problem as MCP-Bench — server-quality benchmark for general MCPs, no browser-specific test stages. |
| Anthropic SDK `count_tokens` | Parse Claude Code session JSONL via `ccusage` / `ccstatusline` | Use as a **cross-check**, not a primary source. Session-level aggregation contaminates per-MCP-tool-call numbers. |
| Scrapfly JA3/JA4 endpoint | mitmproxy + custom JA3/JA4 extraction | Only if the external endpoint is unavailable. Mitmproxy itself has a distinctive TLS fingerprint and won't accurately MITM Cloudflare-protected fingerprint endpoints (per mitmproxy issue #4575). |
| Python `mcp.client.stdio` | `@modelcontextprotocol/inspector --cli` | Use Inspector CLI for ad-hoc developer smoke tests and the public `docs/REPRODUCIBILITY.md` reader-facing recipe. Use Python SDK for benchmark-critical measurements. |
| Justfile | Make | Make works fine; just is cleaner for ad-hoc recipes and is already in the user's toolchain (see browser-tools.md context). Either is fine; pick one. |
| Native macOS host | Docker / devcontainer | Use Docker only for the **test site** if we ever need a frozen-in-time Ashby / Greenhouse copy. We don't have that requirement today. |
| Bash orchestration | Python orchestration with `subprocess` | If the harness grows past ~20 scripts. Today, Bash matches the existing 2026-03-31 wave's style — preserve apples-to-apples. |

---

## 6. What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`pip install` without `uv.lock`** | No transitive pinning. `browser-use` has 50+ transitive deps that drift weekly. | `uv tool install` for tool-style installs, `uv pip sync` with committed `uv.lock` for the harness. |
| **The `next` dist-tag on `@playwright/mcp`** | Currently points at `0.0.75-alpha-2026-05-22`, rebuilt nightly. Pinning it = your benchmark drifts every 24h. | Always use the `latest` dist-tag, i.e. `0.0.75` pinned exactly. |
| **GitHub releases as the source of truth for `firecrawl-mcp`** | Last GitHub release was `v3.2.1` in 2025-09. npm has shipped 30+ patch versions since (now at 3.17.0). The GitHub release feed is dead. | Always check npm registry directly (`npm view firecrawl-mcp version`) for the real latest. Run `npm audit signatures` per global supply-chain hygiene rule, since the release/publish workflow is non-standard. |
| **mitmproxy as the primary TLS-fingerprint capture path** | mitmproxy has its own JA3 fingerprint and many fingerprinting endpoints will misreport when proxied through it (mitmproxy GitHub issue #4575). | Direct HTTP request from inside each MCP's browser to Scrapfly/tls.peet.ws. Mitmproxy is the local fallback only. |
| **WebArena Docker images as our test target** | Our targets are live SaaS (Greenhouse, Ashby). Mocking them defeats the purpose of testing real-world bot detection and React-Select quirks. | Live external URLs, pinned to the **specific job postings** used 2026-03-31 (URLs are documented in `results/2026-03-31_run.md`). Re-verify URLs are still live before the run; have backup postings ready. |
| **Headless Playwright Chromium with default settings as a "real Chrome" baseline** | Leaks three independently fingerprintable signals: `HeadlessChrome/` UA token, SwiftShader software renderer in WebGL, `navigator.plugins.length=0` (per browser-tools.md). | Either accept that Playwright headless is detectable (it IS, that's a real benchmark finding to publish), or run Playwright `--headed` for the JA3/JA4 capture and document the launch mode. |
| **`--stealth` on Obscura when running on macOS** | Sec-CH-UA-Platform-* client hints leak the real OS regardless of JS UA spoof (per browser-tools.md + G-602 measurement). | Run Obscura without `--stealth` on macOS, OR run it in a Linux VM (out of scope this wave). Document the limitation. |
| **`mcp__plugin_linear_linear__*` tools for ticket creation** | Per global rules, local sessions must use `linearis` CLI. | `linearis create G ...` for per-MCP tickets. |
| **Committing `FIRECRAWL_API_KEY` to `.envrc`** | Public repo. | `.envrc` in `.gitignore`, `.envrc.example` checked in, secret retrieved via `rbw get firecrawl.dev --field Firecrawl_API`. |

---

## 7. Stack Patterns by Variant

**If a third party wants to reproduce on Linux (x86_64):**
- Obscura's npm wrapper ships an x86_64 engine binary natively — they're luckier than us. The browser-tools.md note about arm64 packaging gap goes away.
- Lightpanda asset is `lightpanda-x86_64-linux`.
- CloakBrowser availability is the unknown — verify before promising parity.
- Document this explicitly in `docs/REPRODUCIBILITY.md` so Linux readers know what to grab.

**If only 6/7 MCPs are scoreable (no `FIRECRAWL_API_KEY`):**
- Per PROJECT.md, partial scoring (6/7) is acceptable.
- Emit a clearly-labeled `firecrawl: SKIPPED (API key absent)` row in the results matrix.
- Keep the scoring rubric's denominator at 7 candidates so the composite is honest about what was measured.

**If `cloakbrowser` fails to install on the reader's machine (closed-source binary, may not run unsigned):**
- Score 6/7. Document the failure mode (Gatekeeper rejection, sandbox restrictions).
- Keep the cloakbrowser column in published results with `INSTALL_FAILED: {reason}` so the next reader knows whether to retry.

---

## 8. Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `@playwright/mcp@0.0.75` | Node 18+ (Node 22 recommended) | Bundles its own Chromium download via `npx playwright install chromium` on first run; account for that in cold-start measurement (first run is uncached download). |
| `chrome-devtools-mcp@1.0.1` | Requires a running Chrome/Chromium instance on the host with `--remote-debugging-port` accessible. Will print a stderr warning about "exposes content of the browser instance to the MCP client" — not a failure, costs 1 point on the 2026-05 stability rubric per browser-tools.md. | Pair with the Chrome Agent profile (`~/.claude/scripts/chrome-agent.sh`) for consistency. |
| `browser-use@0.12.7` | Python 3.11+, Playwright Chromium (separate install: `uvx playwright install chromium`). Requires LLM key OR `--direct` mode for no-LLM execution. | The 2026-05-21 testbench reported transport mismatch on `initialize` — re-test on 0.12.7 before relying on `--mcp` mode. |
| `lightpanda nightly` (binary) | macOS aarch64 / x86_64, Linux aarch64 / x86_64. The Zig JS engine cannot render React; expect 0-byte output on Ashby (this IS the finding for that dimension). | Binary self-reports version inconsistently: the executable header says 0.3.0 in some builds, the JSON-RPC handshake says 0.1.0 (verified 2026-05-21 in browser-tools.md). Don't rely on the runtime version string. |
| `obscura-mcp@0.1.4-3` (npm wrapper) | Requires `obscura-mcp install` to download the Rust+V8 engine on first use. macOS aarch64 binary verified available; container x86_64 mismatch documented. | The wrapper's npm version (0.1.4-3) and the engine binary version are NOT the same number — log both at install time. |
| `firecrawl-mcp@3.17.0` | Requires `FIRECRAWL_API_KEY` env var. Cloud-only, no local browser process. | Run `npm audit signatures` before pinning — the GitHub-release vs. npm-publish drift is a supply-chain yellow flag. |
| `cloakbrowsermcp@2.0.4` | macOS aarch64 verified. Sandbox-only per global policy. Closed-source binary. | NEVER point at authenticated personal sessions per browser-tools.md. Only run against public Greenhouse + Ashby fixtures. |
| `mcp` (Python SDK) | Python 3.10+. Version 1.16.x | Used only by our harness, not by the MCPs themselves. Pin in `uv.lock`. |
| `anthropic` (Python SDK) | Python 3.8+. Version 0.40.x | For `count_tokens`. Needs `ANTHROPIC_API_KEY` env var, but `count_tokens` is free. |

---

## 9. Sources

**Verified live 2026-05-22 (HIGH confidence):**
- npm registry: `npm view @playwright/mcp`, `npm view chrome-devtools-mcp`, `npm view obscura-mcp`, `npm view firecrawl-mcp`, `npm view @modelcontextprotocol/inspector` — all version + time fields fetched
- PyPI: `curl https://pypi.org/pypi/browser-use/json`, `https://pypi.org/pypi/cloakbrowsermcp/json` — version, project_urls, releases
- GitHub releases API: `lightpanda-io/browser`, `microsoft/playwright-mcp`, `ChromeDevTools/chrome-devtools-mcp`, `browser-use/browser-use`, `firecrawl/firecrawl-mcp-server`
- Scrapfly JA3/JA4 endpoint `https://tools.scrapfly.io/api/fp/ja3?extended=1` — schema confirmed live, returns ja3/ja3n/ja4/ja4_hash + tls object

**Documentation references (HIGH confidence, official sources):**
- [MCP Inspector — modelcontextprotocol.io](https://modelcontextprotocol.io/docs/tools/inspector) — CLI mode, JSON output, exit codes
- [MCP Lifecycle spec — modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle) — initialize-first protocol
- [Anthropic token counting — platform.claude.com](https://platform.claude.com/docs/en/build-with-claude/token-counting) — `count_tokens` is free, separate rate limit
- [uv lockfile reproducibility — pydevtools](https://pydevtools.com/handbook/explanation/uv-complete-guide/) — `uv sync --locked` semantics
- [TrackMe / tls.peet.ws — github.com/wwhtrbbtt/TrackMe](https://github.com/wwhtrbbtt/TrackMe) — backup JA3 endpoint
- [FoxIO JA4 spec — github.com/FoxIO-LLC/ja4](https://github.com/FoxIO-LLC/ja4) — JA4 algorithm reference

**Domain references (MEDIUM confidence, secondary sources, cross-verified):**
- [AgentLab — github.com/ServiceNow/AgentLab](https://github.com/ServiceNow/AgentLab) — BrowserGym successor, 2026 reproducibility model
- [WebArena-Verified — github.com/ServiceNow/webarena-verified](https://github.com/ServiceNow/webarena-verified) — Docker reproducibility precedent
- [MCP-Bench — arXiv 2508.20453](https://arxiv.org/abs/2508.20453) — Accenture MCP benchmark (different axis, ruled out)
- [Scrapfly JA3/JA4 checker](https://scrapfly.io/web-scraping-tools/ja3-fingerprint) — fingerprint reference set (~125k samples)
- [Cloudflare cf-mitigated header discussion — github.com/lexiforest/curl_cffi #591](https://github.com/lexiforest/curl_cffi/discussions/591) — `cf-mitigated: challenge` canonical signal
- [Claude Code session token logging — github.com/anthropics/claude-code #49588](https://github.com/anthropics/claude-code/issues/49588) — confirms per-MCP-tool token attribution is not yet exposed natively

**Project-internal references:**
- `/Users/pleasedodisturb/.claude/docs/browser-tools.md` (2026-05-21) — TLS-fingerprint dominance claim, per-MCP testbench scores, OS-detection gotchas
- `/Users/pleasedodisturb/Projects/web-agent-comparison/scoring/rubric.md` — locked 8-dimension scoring
- `/Users/pleasedodisturb/Projects/web-agent-comparison/results/2026-03-31_run.md` — prior wave methodology to preserve apples-to-apples

---
*Stack research for: MCP browser-server benchmark (Stage 1 of pipeline)*
*Researched: 2026-05-22 by Claude Opus 4.7 (1M context)*
*Verified live against npm, PyPI, GitHub APIs, and Scrapfly fingerprint endpoint on the same day.*
