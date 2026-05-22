# HANDOFF — Web-Agent MCP Comparison

**Created:** 2026-05-22 (Mac Mini session)
**Purpose:** Context dump for the next Claude session that picks up the web-agent comparison & benchmarking work.

---

## Why this repo exists (the bigger picture)

`web-agent-comparison` is the **interim, public, research-heavy** stage of a 3-stage pipeline:

```
   web-agent-comparison              terminal-craft                  Kestrel + Eyas
   ─────────────────────             ─────────────────               ──────────────
   research + tests +         →      harness + rating +       →     agent tools for
   results + scoring                 toolkit packaging               job-hunting tasks
   (PUBLIC, this repo)               (PRIVATE, internal use)         (production agents)
```

**Stage 1 (HERE):** dogfood every candidate MCP on standardized fixtures, score them, publish findings.
**Stage 2 (terminal-craft):** convert the winners into a packaged web-agent toolkit + harness for ongoing use.
**Stage 3 (Kestrel + Eyas):** wire the toolkit into the job-hunting agents as their browser/web tools.

This handoff covers **Stage 1 only**. Stages 2-3 should NOT begin until Stage 1 produces actionable comparison results.

---

## State as of 2026-05-22

### MCPs available in this repo (project scope via `.mcp.json`)

7 browser MCPs are registered in `./.mcp.json` and will auto-spawn whenever Claude is opened in this directory:

| Name | Command | Status | Notes |
|---|---|---|---|
| `playwright` | `playwright-mcp` (npm @playwright/mcp@0.0.75) | Ready | Microsoft baseline, 28 tools, accessibility tree |
| `browser-use` | `browser-use --mcp` (uv tool v0.12.7) | Ready | 95k-star framework, direct mode no-LLM-key |
| `chrome-devtools` | `chrome-devtools-mcp` (npm v1.0.1) | Ready | Official Chrome team, DevTools panel access |
| `lightpanda` | `lightpanda mcp` (binary v0.3.0) | Ready | Zig headless, 1.8s cold start, no React support |
| `obscura` | `obscura-mcp` (npm v0.1.4-2) | **Engine pending** | Rust + CDP, ~30MB RAM; needs `obscura-mcp install` to download engine |
| `firecrawl` | `firecrawl-mcp` (npm v3.17.0) | **Needs API key** | Set `FIRECRAWL_API_KEY` in shell env before launching Claude here |
| `cloakbrowser` | `cloakbrowsermcp` (uv tool v2.0.4) | Ready | Stealth Chromium, Cloudflare/reCAPTCHA bypass. **Sandbox only — never point at authenticated sessions** |

A separate `browsermcp` was *not* moved here from terminal-craft (it's a different beast — needs the Chrome Agent profile + browser extension). Add it later if comparison demands.

### What was removed today

These 7 were previously at **user scope** (~/.claude.json) and were spawning in every Claude session everywhere — clogging the macOS dock with rocket-icon Python.app processes (one per session × per Python-based MCP). The 2026-05-22 fix moved them to project scope (this repo) and removed them from user scope. Now they only spawn when Claude is opened in this directory.

Memory MCP (`memory` server) stays at user scope — that's intentional.

### Prior comparison work

Per `git log`, there's already a "Web agent comparison: 5 agents tested on real job application flows" commit (sha `6827253`). The 5 agents tested were *application-level* (Skyvern, Manus, browser-use the framework, etc.) — different from this comparison wave which focuses on **MCP-layer browser servers** that Claude Code can drive directly.

Read `README.md`, `results/`, `scoring/`, `fixtures/` before proposing new methodology — there's existing scaffolding worth reusing.

---

## What the next session should do

### Immediate (Day 1 of new session)
1. **Initialize GSD** (if you want full structure): `/gsd-new-project` in this repo. Otherwise this HANDOFF.md + a Linear ticket is enough scaffolding to start.
2. **Verify all 7 MCPs connect** when Claude is opened here: check `/mcp` panel. Expect 6/7 connected (firecrawl needs API key, obscura needs `obscura-mcp install` for engine).
3. **Read existing research** in `results/` and `fixtures/` — don't redo what's already done.

### Research questions to answer (the actual comparison)
1. **Cold-start latency** per MCP — time from "spawn" to "first usable tool call." Already gathered for lightpanda (1.8s); need others.
2. **DOM coverage** — which sites does each MCP successfully navigate + extract from? Use `fixtures/` for standardized targets.
3. **Bot-detection resilience** — which sites flag/block each MCP? Especially: Cloudflare, DataDome, reCAPTCHA, Akamai.
4. **TLS fingerprint (JA3/JA4)** — only real Chrome (via BrowserMCP / CloakBrowser) passes 2025-2026 detection. Confirm or refute per MCP.
5. **Token efficiency** — measure tokens/task. browser-use is verbose; playwright accessibility-tree is compact. Numbers needed.
6. **Stability** — does each MCP survive 1hr of continuous use without crashing the Python.app process?

### Deliverables for Stage 1 completion
- `results/2026-05-XX-mcp-comparison.md` — scored matrix
- `results/recommendations.md` — which MCPs graduate to the Stage 2 toolkit
- One Linear ticket update per major finding
- Public blog post / README update summarizing methodology + verdict

### Stop conditions
You are DONE with Stage 1 when:
- All 7 MCPs have a scored row in the comparison matrix
- The "graduate to toolkit" recommendation is explicit (which MCPs, in which order of preference)
- The methodology is reproducible (someone else can clone this repo, run the fixtures, and get similar scores)

Do **NOT** start Stage 2 (terminal-craft harness) or Stage 3 (Kestrel/Eyas wiring) from this session. Those are separate scoped efforts that should reference the Stage 1 results.

---

## Cross-machine notes

- This repo is **public** on GitHub (`pleasedodisturb/web-agent-comparison`). The `.mcp.json` is committed — anyone cloning sees which MCPs are being benchmarked. For a research repo, that's a feature.
- Mac Mini has all 7 binaries installed (uv tools + npm packages). **MacBook may not** — verify with `which playwright-mcp browser-use chrome-devtools-mcp lightpanda obscura-mcp firecrawl-mcp cloakbrowsermcp` before relying on the project-scope config there.
- `~/.claude.json` syncs via Syncthing. The user-scope removal already propagated to MacBook (no further action needed).

## References

- MCP master list: `~/.claude/MCP_REGISTRY.md`
- Linear ticket: **G-703** — https://linear.app/abandoned-yachts/issue/G-703 (Mac Setup & Environment, estimate=16 "break-before-cycle", label `route/agent`, priority High). Split into per-MCP sub-tickets before pulling into a cycle.
- Memory layer 3 (Mac Mini): `~/.claude/projects/-Users-pleasedodisturb-Projects-screenpipe/memory/MEMORY.md` — G-688 install wave notes
- Prior install context: G-688, G-695 (Linear)
