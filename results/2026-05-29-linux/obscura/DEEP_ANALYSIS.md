# Obscura — Linux Cross-Platform A/B (v1.0.x patch evidence)

**Run date:** 2026-05-29
**Host:** Hetzner dedicated box, Ubuntu 24.04 LTS, kernel 6.8, Intel i7-8700 @ 3.2 GHz, 125 GB RAM
**Container:** Docker 29.1.5, `node:22-bookworm` base + Python 3.12 + uv + Claude Code + `obscura-mcp@0.1.4-3` (npm)
**MCP under test:** `obscura-mcp --stealth` (Linux-specific flag enablement — different from v1.0 macOS which ran without `--stealth` per SAFETY-03 to avoid the `Sec-CH-UA-Platform-Mac` leak)
**Tracking:** [GitHub issue #9](https://github.com/pleasedodisturb/web-agent-comparison/issues/9), [Linear G-737](https://linear.app/abandoned-yachts/issue/G-737)

## Headline finding

**Obscura's Linux x86_64 build cannot reach our loopback fixtures via either path.** Two independent fatal failure modes, both structural:

1. **CDP path: phantom listener.** The `obscura serve` binary prints `Obscura CDP server listening on ws://127.0.0.1:9222` to stderr but **never actually binds the TCP port**. Verified directly via `ss -ltn | grep 9222` after a 15s+ grace window — the port is never opened. Consequently `obscura-mcp`'s CDP client times out and every browser tool returns `Obscura CDP client is not connected`.
2. **Cloud-scrape path: SSRF guard.** `browse_scrape` routes through Obscura's cloud worker pool. The cloud rejects `127.0.0.1` with `Access to private/internal IP address 127.0.0.1 is not allowed`. Structural mismatch with our loopback-only fixture contract.

**Score:** N/A on Linux (binary cannot complete *any* harness stage). Treated as `INSTALL_FAILED` per the existing CLAUDE.md guidance for environment-specific failures (do not replace the macOS row's 3.27 composite — that stands).

## Bisection vs macOS

| Configuration | Engine starts? | CDP port 9222 bound? | Cloud loopback OK? | Composite | Stages passed |
|---------------|----------------|---------------------|---------------------|-----------|----------------|
| **v1.0 macOS arm64** (Mac Mini, no `--stealth`) | ✅ yes | ✅ yes | n/a (not used) | 3.27 / 10 | 3-pass median per FAIRNESS-01 |
| **v1.0.x Linux x86_64** (Hetzner Ubuntu 24.04, `--stealth`) | ✅ yes | ❌ no (phantom log) | ❌ blocked by SSRF guard | N/A | 0/8 (deterministic) |

The Linux failure is **deterministic and reproducible** in the raw stdio path (`echo "..." | obscura-mcp` reproduces the CDP-not-connected error without any harness involvement). Variance is zero; running passes 2+3 would burn ~$6 in LLM budget for redundant evidence. We stopped at PASS1.

## What we ruled out

- **Container restrictions.** The host has 125 GB RAM, no cgroup memory limits applied, Docker daemon's default ulimits. The container ran with `--network host` so 127.0.0.1 access is genuinely local.
- **Misconfigured `.mcp.json`.** The overlay (`results/2026-05-29-linux/mcp.linux.json`) is the canonical invocation: `{"command": "obscura-mcp", "args": ["--stealth"]}`. Same as macOS but with the `--stealth` flag (intentional — Linux doesn't have the macOS `Sec-CH-UA-Platform-Mac` leak).
- **Binary architecture mismatch.** `file dist/bin/obscura` confirms `ELF 64-bit LSB pie executable, x86-64`. Binary runs, parses args, prints version. Not the documented arm64/x86_64 packaging gap.
- **First-cold-start latency.** Gave the engine a >25s grace window across retries; port 9222 never appears regardless.
- **Harness `ulimit -v 4G` cap on Linux.** This was an **earlier blocker** — we patched it locally to `16G` and re-ran. The CDP failure persists post-patch, so the ulimit was a separate issue, not the root cause. See "Harness portability finding" below.

## Harness portability finding (worth its own callout)

The v1.0 macOS harness applies `ulimit -v 4194304` (4 GB virtual address space) inside `scripts/run_mcp_session.sh`. **This is enforced strictly on Linux but loosely on macOS** for `mmap`-style reservations. Node 22's V8 pointer-compression sandbox alone reserves 4 GB virtual space on startup, exhausting the cap before any allocation. Result: every MCP that spawns a Node-22 child (Obscura, browser-use, chrome-devtools-mcp, firecrawl, BrowserMCP) hits a `WebAssembly.instantiate(): Out of memory` failure on first WASM init when running under this ulimit on Linux.

This means **v1.0's `ulimit -v 4G` is effectively a macOS-only convention** — it serves as defense-in-depth on macOS (which doesn't enforce it strictly) and as a hard blocker on Linux. Any Linux reproducer needs to drop or raise the cap.

**Recommendation for a future harness change:** detect OS at script start; on Linux either drop the `ulimit -v` entirely (rely on cgroup limits if running in a container) or raise to ≥16 GB. Track this as a portability follow-up; **not patched in v1.0.x** because changing harness scripts mid-version would invalidate the v1.0 sacrosanct-invariants property.

## Cross-platform implication for the matrix

The v1.0 published composite for Obscura is **macOS arm64 only**. v1.0.x doesn't replace it; instead the row gets a footnote:

> *Composite 3.27 reflects measurement on macOS arm64. Obscura on Linux x86_64 cannot reach loopback fixtures (phantom CDP listener bug + cloud-scrape SSRF guard) — see `results/2026-05-29-linux/obscura/`.*

The SKIP tier remains correct. **Obscura's value-proposition (stealth on Linux where `Sec-CH-UA-Platform-Linux` is honest) was the motivation for G-737** — that question now has an empirical answer different from what we hoped: stealth-on-Linux isn't testable with this Obscura version because the engine doesn't start. The proper Linux-vs-macOS stealth comparison requires either a fixed Obscura release or a different stealth MCP.

## Cost ledger

- Pass 1 (Anthropic-keyed harness, with `--stealth`, raised ulimit): ~$3 in Claude Code session retries
- Stdio probe (raw): $0
- **Total v1.0.x Obscura Linux investigation:** ~$3

Compared to the v1.0.1 browser-use-agent rescore at ~$6, this came in cheaper because pass 1 produced a definitive structural finding that didn't warrant 3-pass median.

## Evidence files in this directory

- `PASS1/transcript.md` — the Claude-session-driven transcript of the 8-stage walk with detailed diagnosis of both failure modes
- `PASS1/stage_s1.FAILED..stage_s8.FAILED` — per-stage failure files (all reference the CDP phantom-listener root cause)
- `PASS1/raw_stream.jsonl` — full stream-json output of the Claude Code session
- `PASS1/tools_inventory.json` — Obscura's 4-tool surface (browse_page, browse_interact, browse_session, browse_scrape) confirmed via inventory probe (post-ulimit-fix)
- `PASS1/cold_start.json`, `tokens.json`, `tls.json`, `stability.log`, `orphan_audit.log` — standard v1.0 harness artifacts

## Reproducer (for the upstream issue)

Minimum steps on a Linux x86_64 host:

```bash
# 1. Install Node 22 + Obscura wrapper + engine
npm install -g obscura-mcp@0.1.4-3
obscura-mcp install   # downloads /usr/local/lib/.../dist/bin/obscura

# 2. Confirm binary is functional (it runs, parses args)
obscura --version
obscura --help

# 3. Launch the engine directly and observe phantom listener
obscura serve &
sleep 5
ss -ltn | grep 9222  # → empty; port never bound

# 4. Sanity: kill the phantom and confirm the wrapper's CDP client agrees
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"r","version":"0.1"}}}' | obscura-mcp 2>&1 | head -5
# → "Obscura CDP client is not connected" on any tool call
```

## Upstream filing recommendation

This is reportable to whichever upstream maintains the obscura engine binary (the `dist/bin/obscura` ELF — separate from the `obscura-mcp` npm wrapper). Per the v1.0 STACK research, the engine source is at `github.com/h4ckf0r0day/obscura`. Issue filing is **not done in this patch** (vendor courtesy disclosure remains G-710-deferred) but the minimal reproducer above is sufficient for triage when filed.
