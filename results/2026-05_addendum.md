# 2026-05 Addendum

*Posted 2026-05-22. The historical [2026-03-31 results](./2026-03-31_run.md) remain unchanged — they're a dated benchmark, valuable as such. This addendum captures what's changed since.*

## TL;DR

- **Agent Browser is gone.** vercel-labs/agent-browser is unmaintained; removed from the stack ([terminal-craft G-687](https://linear.app/vtolik/issue/G-687)).
- **New empirical ranking.** A 49-attempt Docker-sandboxed sweep across 7 tools puts CloakBrowser on top, Playwright MCP and chrome-devtools tied a tier below, Lightpanda mid-pack, browser-use and Obscura at zero (transport + arch packaging bugs respectively — fixable).
- **This repo is now the central dogfooding environment.** As of 2026-05-22, the seven browser MCPs (playwright, browser-use, chrome-devtools, lightpanda, obscura, firecrawl, cloakbrowser) are project-scoped here via `.mcp.json`.
- **Lightpanda #2072 closed.** The MCP instant-exit bug from earlier this year is *not reproduced* on the darwin-aarch64 host binary v0.3.0 ([G-695](https://linear.app/vtolik/issue/G-695)).

## Status changes since 2026-03-31

| Tool | 2026-03-31 score | 2026-05 status | Notes |
|------|------------------|----------------|-------|
| **Playwright MCP** | 9.07/10 ✅ | Confirmed top tier | 28 tools, accessibility-tree, deterministic. Default driver. |
| **WebFetch** | 7.87/10 ✅ | Confirmed | First choice for static-HTML reads — 20× more token-efficient than snapshots. |
| **Agent Browser CLI** | 7.60/10 | **REMOVED** | Project unmaintained ([G-687](https://linear.app/vtolik/issue/G-687)). Superseded by browser-use direct mode + Playwright MCP. |
| **Lightpanda CLI** | 5.87/10 | Verified working | MCP subcommand now responds correctly to JSON-RPC `initialize` on darwin-aarch64 host ([G-695](https://linear.app/vtolik/issue/G-695)). Still server-rendered HTML only. |
| **BrowserMCP** | 5.53/10 | Confirmed niche tier | Only path to authenticated host sessions (Greenhouse, LinkedIn). Project-level `.mcp.json` only. |

## New entrants (2026-05 install wave)

| Tool | Verdict | Mac Mini compat | Differentiator |
|------|---------|-----------------|----------------|
| **browser-use** (`mcp__browser-use__*`) | Use | Yes | Python agent framework with first-class MCP, ~95K stars. Direct mode is a strict superset of Playwright MCP primitives (adds session management). Container transport bug as of 2026-05; works on host. |
| **chrome-devtools MCP** (`mcp__chrome-devtools__*`) | Use | Yes | Official ChromeDevTools team. DevTools panel access (network/perf/console) — the only tool in the stack with this angle. |
| **Obscura** (`mcp__obscura__*`) | Use | Yes | Lightweight Rust headless (~70 MB binary, ~30 MB RAM/tab) with built-in stealth + 3,520-domain tracker blocklist. Engine binary download has arch packaging issues in linux-aarch64 containers; runs fine on darwin-aarch64 host. |
| **CloakBrowser** (`mcp__cloakbrowser__*`) | Use (sandbox-only) | Yes | Patched-Chromium stealth (~58 C++ fingerprint patches). Passes Cloudflare Turnstile, reCAPTCHA v3, FingerprintJS without solving CAPTCHAs. **Closed binary touches cookies — never point at authenticated personal sessions.** |
| **Firecrawl MCP** (`mcp__firecrawl__*`) | Use (cloud) | Yes (cloud-only) | Token-optimised cloud markdown scraping. 96% coverage / 0.638 F1 on 1000-URL benchmark, ~7s avg. Needs `FIRECRAWL_API_KEY`. |

## 2026-05 routing recipe (priority order)

For read-only / interactive flows in this order — fall through to the next tier when the previous fails:

1. **WebFetch** (built-in, no MCP) — static-HTML reads, AI-summarised
2. **Playwright MCP** — interactive baseline
3. **chrome-devtools** — when DevTools panel/network insight is needed
4. **browser-use** — Python agent framework, direct or agent mode
5. **Obscura** — low-RAM stealth for server-rendered scraping
6. **CloakBrowser** — escalation tier for fingerprint-blocked sites (sandbox only)
7. **Firecrawl** — token-optimised cloud markdown
8. **Lightpanda** — Zig headless, server-rendered HTML only
9. **BrowserMCP** — authenticated host pages (LinkedIn, Greenhouse with real cookies)

## Empirical ranking (G-688 §4 testbench, 2026-05-21)

49-attempt Docker-sandboxed sweep across 7 corpus URLs (mix of server-rendered + SPA + ATS forms). Score is sum of success_count across the corpus (out of 15).

| Tool | Score | Notes |
|------|-------|-------|
| cloakbrowser | **15** | Top of MCP correctness leaderboard (stealth performance not exercised by this harness) |
| playwright | **13** | Confirmed default driver |
| chrome-devtools | **12** | Strong second tier — DevTools-aware |
| lightpanda | **7** | Server-rendered only; SPA pages return empty (expected) |
| browser-use | 0 | Container transport bug — works on host |
| obscura | 0 | Arch packaging bug in linux-aarch64 container — works on darwin-aarch64 host |
| firecrawl | skipped | No `FIRECRAWL_API_KEY` in test environment |

Per [terminal-craft G-688 Phase 6 testbench](https://github.com/pleasedodisturb/terminal-craft/blob/main/research/goodailist/browser-testbench.md). Numbers stand as an *upper bound* for `success_count` per the HI-02 corrigendum in that doc.

## Project-scoped MCPs (this repo's `.mcp.json`)

As of 2026-05-22 (terminal-craft commit reverting these from `-s user` to project-scoped), the seven browser MCPs are scoped here:

```json
{
  "mcpServers": {
    "playwright":      { "command": "playwright-mcp",   "args": [] },
    "browser-use":     { "command": "browser-use",      "args": ["--mcp"] },
    "chrome-devtools": { "command": "chrome-devtools-mcp", "args": [] },
    "lightpanda":      { "command": "lightpanda",       "args": ["mcp"] },
    "obscura":         { "command": "obscura-mcp",      "args": [] },
    "firecrawl":       { "command": "firecrawl-mcp",    "args": [] },
    "cloakbrowser":    { "command": "cloakbrowsermcp",  "args": [] }
  }
}
```

That makes this repo the canonical environment for dogfooding + comparison. Sessions launched elsewhere (Eyas, kestrel, foxhound) do not have these MCPs loaded — they fall back to the global user scope, which now only includes `playwright` and the standard set. To run a comparison or bench, launch Claude Code from this directory.

## See also

- **[terminal-craft G-688 Phase 6 deep-review](https://github.com/pleasedodisturb/terminal-craft/blob/main/research/goodailist/deep-review-2026-05.md)** — 15-tool survey with full verdict + Mac Mini compat + integration cost
- **[terminal-craft G-688 Phase 6 browser-testbench](https://github.com/pleasedodisturb/terminal-craft/blob/main/research/goodailist/browser-testbench.md)** — full ranking methodology + per-tool report
- **[terminal-craft web-agent audit](https://github.com/pleasedodisturb/terminal-craft/blob/main/.planning/web-agent-audit-2026-05.md)** — migration backlog across all consumers
- **[~/.claude/docs/browser-tools.md](https://github.com/pleasedodisturb/dotfiles)** — Vitalik's personal routing matrix (Syncthing-replicated across both machines)

## Re-run plan

A full v2 bake-off — using the 2026-05 toolset (≥9 tools once Skyvern, Stagehand, and Firecrawl key are wired) — is tracked separately as [G-694](https://linear.app/vtolik/issue/G-694). Until that runs, the numbers above are the canonical 2026-05 ranking.
