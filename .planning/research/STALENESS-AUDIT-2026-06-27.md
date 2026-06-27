# Staleness Audit — MCP Browser-Server Benchmark

**Audited:** 2026-06-27
**Scope:** Drift check on the 7 v1.0 candidates + field scan, ~5 weeks after the STACK.md research wave (2026-05-22) and the v1.0 scoreboard publication (2026-05-27).
**Method:** Live registry sweep (npm/PyPI/GitHub) cross-checked by 9 parallel research agents (1 per candidate + field-developments + directory scrape). Primary sources only; confidence tagged per finding.
**Relation to other docs:** Supersedes the version pins in [`STACK.md`](STACK.md) §1 (the dated 2026-05-22 body is preserved for traceability). Feeds the v1.1 milestone ([`../ROADMAP.md`](../ROADMAP.md), Phases 6–11).

---

## 0. Bottom line

The published v1.0 scoreboard (2026-05-27) is **not broadly invalid** — 4 of 7 candidates are unchanged or only cosmetic drift (2 confirmed unchanged + 2 cosmetic), while **3 are genuinely stale**, and **all 3 already fall inside v1.1's Phase 8 re-validation scope**.

- **Do NOT run a standalone maintenance rescore.** v1.1 Phase 8 re-runs the entire corpus (new fixtures + Linux, median-of-3); a separate rescore now produces a throwaway scoreboard.
- **Do refresh the version pins now** (documentation-level; cheap hygiene) — §2.
- **Do execute v1.1 as its own session**, entry at Phase 6 (fixture authoring). This audit is the *input* to that work.

---

## 1. Per-candidate drift + verdict

| MCP | Pinned (05-22) | Current (06-27) | What actually changed | Rescore? |
|---|---|---|---|---|
| **playwright** `@playwright/mcp` | 0.0.75 | **0.0.76** (06-10) | Trivial: +2 opt-in video tools, opt-in `--output-max-size`. `browser_fill_form` / `browser_select_option` **byte-identical**. S7 React-Select weakness untouched (`browser_run_code` fallback still required). | **NO** — re-pin for baseline hygiene only |
| **chrome-devtools-mcp** | 1.0.1 | **1.4.0** (06-23) | Big version jump, **S1–S8 tool surface unchanged** (fill_form/upload_file already in 1.0.1). New = opt-in TOON output, screenshot-size cap, heap/memory tools, url allow/block patterns. Content-exposure stderr warning **still present** (−1 stands). New regression #2199 (silent input failure after re-nav). Agent-discovery issues persist (corroborates the 5.60↔8.33 pass variance). | **NO** (+ methodology flag) |
| **firecrawl-mcp** | 3.17.0 | **3.22.1** (06-26) | Surface expansion: new `firecrawl_interact` live browser automation, JSON-default output, `redactPII`, monitor/research/parse suites, keyless tier, MCP OAuth. ⚠️ **3.18.0–3.20.0 carry a stdio-killing regression** ("Unauthorized: API key required" on every call) fixed in **3.20.1** — never pin in that range. | **MAYBE (conditional)** |
| **browser-use** | 0.12.7 | **0.13.1** PyPI / 0.13.2 GH (06-12) | Bug **#4846 still OPEN** — all 3 fix PRs (#4847/#4881/#4993) unmerged. 0.13.0 Rust rewrite **explicitly leaves the Python MCP path untouched**. Agent-mode would still score 0.00; direct-mode 5.87 unchanged. | **NO** (gate not cleared) |
| **lightpanda** | nightly/0.3.0 | **0.3.3** (06-23) | 🔴 **No longer read-only** — native `lightpanda mcp` now exposes `click/fill/scroll/hover/press/selectOption/setChecked` + file-input. **Invalidates the v1.0 "N/A for S4–S8" classification.** React SPA still broken (#2829/#2828, filed 06-26: SPA route changes/redirects invisible over CDP); no paint pipeline → S8 screenshot still N/A. Handshake still hard-codes a lying `"0.1.0"`. `main` is `1.0.0-dev`. | **YES (partial)** |
| **obscura** `obscura-mcp` | 0.1.4-3 (`dev` tag) | **wrapper ARCHIVED** (05-17) | npm wrapper deprecated → MCP moved to native `obscura mcp`. Underlying engine `h4ckf0r0day/obscura` very active (v0.1.9, pushed 06-26, 16k★): **macOS `Sec-CH-UA-Platform` stealth leak fixed** (v0.1.8/9) + **`--allow-private-network` unblocks 127.0.0.1 loopback** (v0.1.6). Still **missing screenshot + file-upload** tools → S6/S8 still uncompletable. Linux phantom-9222: no fix found, re-verify. | **YES (re-test, capped ceiling)** |
| **cloakbrowser** `cloakbrowsermcp` | 2.0.4 | **2.0.4** (dormant) | Byte-identical to the benchmarked artifact (all releases 2026-04-04). No CVEs/disclosures/malware. (Note: the *wrapper* is Apache-2.0; the closed component is the `cloakbrowser>=0.3` engine dep.) Unreleased `main` flips default to `--caps all` — re-examine the SANDBOX caveat **if** a 2.0.5 ships. Stays SANDBOX-ONLY. | **NO** |

*Harness dep:* `@modelcontextprotocol/inspector` 0.21.2 → **0.22.0** (minor).

**Methodology flag (chrome-devtools):** it **auto-launches Chrome by default** — `--remote-debugging-port` is only required for manual attach via `--browser-url`. If the v1.0 setup-complexity penalty assumed a mandatory pre-running debug Chrome, that may be a harness-config artifact rather than a tool limitation. Re-check the run config in Phase 8.

### Net staleness, by candidate
- **Stale / changing (3):** lightpanda (read-only misclassification — the single most outdated v1.0 claim), firecrawl (premise partly stale), obscura (SKIP rationale partly cleared **and** pinned artifact deprecated).
- **Confirmed unchanged (2):** browser-use-agent (still 0.00, #4846 open), cloakbrowser (still 2.0.4).
- **Cosmetic drift (2):** playwright (+1 patch, no functional change), chrome-devtools (big version jump, S1–S8 surface identical).

---

## 2. Refreshed pin recommendations (2026-06-27)

Documentation-level refresh. **`make versions` must still run on the host with the binaries installed** to capture SHA256 checksums for the reproducibility manifest — these registry versions are the *targets*, not a captured manifest.

```text
# npm-based MCPs
@playwright/mcp                 0.0.76        # was 0.0.75 (+1 patch, no functional change)
chrome-devtools-mcp             1.4.0         # was 1.0.1 (S1–S8 surface unchanged)
firecrawl-mcp                   3.22.1        # was 3.17.0 — MUST be >= 3.20.1 (3.18.0–3.20.0 stdio-broken)
obscura      ->  USE NATIVE `obscura mcp` (engine v0.1.9)  # npm wrapper obscura-mcp is ARCHIVED/deprecated

# PyPI / uv tool install
browser-use                     0.13.1        # PyPI latest; GH tag is 0.13.2 — confirm which `--mcp` resolves to
cloakbrowsermcp                 2.0.4         # unchanged (dormant)

# Binary
lightpanda                      0.3.3         # tagged stable (NOT nightly); capture version from `lightpanda version`,
                                              # NOT the MCP handshake (which lies "0.1.0")

# Harness
@modelcontextprotocol/inspector 0.22.0        # was 0.21.2
```

**`.mcp.json` change required (Phase 8):** the `obscura` entry currently invokes the archived wrapper `obscura-mcp`; re-point it to the native engine subcommand (`obscura mcp`). This is a candidate-roster-adjacent change — keep it inside the v1.1 sacrosanct-triad discipline.

---

## 3. Impact on v1.1 gates (ROADMAP Phases 6–11)

- **VALIDATE-04** (browser-use-agent, gated on `browser-use#4846`): **still gated → stays SKIPPED.** Re-evaluate only when a fix PR merges and ships to PyPI.
- **VALIDATE-08** (Obscura Linux, gated on `h4ckf0r0day/obscura#197`): **partially cleared by new engine code.** Re-test the **native `obscura mcp` v0.1.9**, not the dead npm wrapper. Cap expectations: screenshot + file-upload tools are still absent, so S6/S8 remain structurally uncompletable regardless of platform.
- **Phase 8 / lightpanda:** N/A semantics for S4–S8 are now factually wrong — re-run the interaction stages (click/fill/dropdown/upload) on the Greenhouse SSR fixture. Expect S4–S7 + JS-Rendering to lift on SSR; do **not** expect the Ashby SPA 0-byte result or the S8 screenshot N/A to flip.
- **Phase 9 / BrowserMCP (G-744):** re-open the decision against a **live successor**, not the dead upstream — see §4.
- **Phase 10 / stealth axis:** JA4(+) is now the primary TLS signal across major detectors; BaaS platforms are TLS-detectable even when spoofing JS/UA — strengthens the rationale. WAREX (below) is a clean blueprint for the stubbed `make stability`.
- **Spec-proofing (harness):** before the MCP **2026-07-28 RC** lands, check `scoring/score.py` + the MCP client driver for two assumptions the RC breaks: (a) `structuredContent`/`outputSchema` being object-only (RC allows any JSON), and (b) the `initialize` handshake / session-id (RC goes stateless). Pin the client to spec **2025-11-25** for now.
- **Firecrawl measurability:** the marquee new SPA/`interact` capability **cannot be measured on the loopback fixtures** — firecrawl's cloud can't reach `127.0.0.1` (#284 persists). A real firecrawl Data-Quality rescore requires a publicly reachable host variant of the Ashby fixture (or self-hosted firecrawl). Otherwise its score stands at 4.23 SECONDARY.

---

## 4. Field developments

### New candidate MCPs
| Name | Repo | MCP? | License | Activity | Call |
|---|---|---|---|---|---|
| **Skyvern** | Skyvern-AI/skyvern | Official | AGPL-3.0 | v1.0.43, 06-18 (very active, 20k★) | **Add — strongest new free/local candidate.** Self-hostable, no key, 75+ tools, Playwright-compatible. **AGPL is the flag** — vet against the graduate-to-private-`terminal-craft` pipeline first. |
| Browserbase + Stagehand | browserbase/mcp-server-browserbase | Official | Apache-2.0 | v3.0.0, active | Cloud/API-key tier (alongside firecrawl), not core local set. |
| Hyperbrowser | hyperbrowserai/mcp | Official | MIT | wrapper stale (2025-11) | Cloud tier; wrapper untouched ~7 months. |
| Steel | steel-dev/steel-mcp-server | Official | MIT | wrapper stale (2025-05) | Local-capable (`STEEL_LOCAL=true`) but wrapper ~13 months stale. |

*Not candidates (end-user agentic browsers, no MCP/headless surface):* OpenAI Atlas, Perplexity Comet, Brave Leo, Edge Copilot Mode, Chrome auto-browse. Cite-only.

### BrowserMCP (Phase 9 / G-744) — re-open against a live successor
- Upstream `@browsermcp/mcp` is **confirmed abandoned** (v0.1.3, April 2025, ~14 months dead).
- The "drive the operator's real authenticated Chrome via extension" model is alive under **`@agent360/browser-mcp`** (MIT, local-only, v1.23.0 2026-06-09, CAPTCHA + emailed-code reading) and `ofershap/real-browser-mcp` (pushed 2026-06-22).
- These conflict with the cloakbrowser sandbox-only posture (authenticated real Chrome) → they'd be **fixtures-only** candidates.

### MCP spec / protocol
- **2025-11-25 (final):** Streamable HTTP replaced legacy SSE. Low impact if driving over stdio.
- **2026-07-28 RC** (locked 2026-05-21): stateless core (no `initialize` handshake), `outputSchema`/`structuredContent` may be any JSON value, error-code change `-32002`→`-32602`. See §3 spec-proofing.

### Benchmarks / research to cite
- **WAREX** (arXiv 2510.03285) — proxy-based fault injection + token/latency logging; cleanest blueprint for the stubbed `make stability` (G-710).
- MCP-Bench follow-ups: MCPAgentBench (2512.24565), MCP-Atlas (2602.00933), MCP-SafetyBench (2512.15163). Steel public leaderboards (leaderboard.steel.dev).

### Bot-detection landscape (informs the deferred stealth axis)
- **JA4(+) is now the primary TLS signal** across Cloudflare/Akamai/AWS WAF; missing GREASE = instant fail; BaaS platforms (Browserbase/Hyperbrowser) detectable by TLS even when spoofing JS/UA/IP.

---

## 5. goodailist scrape — could not complete (two independent reasons)

1. **Blocked in this environment:** `goodailist.com` returns **HTTP 403 at the egress proxy** (organization network-policy denial — not retryable per the proxy README).
2. **Wrong surface anyway:** "goodailist" is **Chip Huyen's tracker of open-source AI *GitHub repos***, not a browse-by-category AI-tools directory — it has no "AI Browser / Browser Automation" category to scrape even if reachable.

No listings were fabricated. The field scan (§4) surfaced the actually-relevant new entrants (Skyvern, Agent360, real-browser-mcp, Steel, Hyperbrowser) via direct GitHub/npm research — higher signal than a directory scrape. To pursue goodailist specifically, re-run from a network where it's allowed, or target a reachable directory (Product Hunt browser-automation, Toolify, Futurepedia).

---

## 6. Recommended next actions

1. **Now (this audit):** pins refreshed in §2 + STACK.md banner. No rescore.
2. **On host (Mac Mini):** run `make versions` to capture binary SHA256s once the refreshed versions are installed.
3. **v1.1 (separate GSD session):** start at Phase 6 (S9–S26 fixture authoring). Carry the §3 gate updates into Phase 8/9/10 planning.
4. **Before the 2026-07-28 MCP RC:** spec-proof `score.py` + MCP client (§3).

---

## 7. Sources (consolidated, primary)

- npm registry: `@playwright/mcp`, `chrome-devtools-mcp`, `obscura-mcp`, `firecrawl-mcp`, `@modelcontextprotocol/inspector` (dist-tags + publish times)
- PyPI JSON API: `browser-use` (0.13.1), `cloakbrowsermcp` (2.0.4)
- GitHub API: releases/commits/issues for `lightpanda-io/browser`, `microsoft/playwright-mcp`, `ChromeDevTools/chrome-devtools-mcp`, `browser-use/browser-use`, `firecrawl/firecrawl-mcp-server`, `h4ckf0r0day/obscura`, `Metadrama/obscura-mcp` (archived), `overtimepog/CloakMCP`, `BrowserMCP/mcp`, `Skyvern-AI/skyvern`, `Agent360dk/browser-mcp`
- Key issues: `browser-use#4846` (+PRs 4847/4881/4993), `firecrawl-mcp-server#284/#279/#255`, `chrome-devtools-mcp#2199`, `lightpanda#2829/#2828/#2400/#1798`, `obscura#203/#325`
- MCP spec: blog.modelcontextprotocol.io (2025-11-25 final; 2026-07-28 RC)
- arXiv: 2510.03285 (WAREX), 2508.20453 (MCP-Bench)

---
*Staleness audit for: MCP browser-server benchmark (Stage 1). Conducted 2026-06-27 via 9 parallel research agents + live registry sweep. Confidence HIGH on version/drift facts (machine-checked against registries/GitHub API); MEDIUM on rescore deltas (depend on an actual re-run against the fixtures).*
