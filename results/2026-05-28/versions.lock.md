# Reproducibility Manifest — 2026-05-28

*Captured at:* `2026-05-28T18:13:24Z` (UTC)

## Host

| Field | Value |
|---|---|
| os | `Darwin` |
| macos_version | `26.5` |
| kernel_version | `25.5.0` |
| arch | `arm64` |

## Tooling

| Tool | Version |
|---|---|
| claude_code | `2.1.145 (Claude Code)` |
| node | `v26.0.0` |
| npm | `11.12.1` |
| python | `Python 3.14.5` |
| uv | `uv 0.11.16 (Homebrew 2026-05-21 aarch64-apple-darwin)` |

## MCPs

| MCP | Version | SHA256 (first 16) | Binary path | Notes |
|---|---|---|---|---|
| `browser-use` | `0.12.7` | `e0a00e383b7f32c8` | `~/.local/bin/browser-use` | handshake=0.1.0; **MISMATCH** |
| `chrome-devtools` | `1.1.1` | `9f380d06e1ac05b2` | `/opt/homebrew/bin/chrome-devtools-mcp` |  |
| `cloakbrowser` | `2.0.4` | `7219449a7a869c0a` | `~/.local/bin/cloakbrowsermcp` |  |
| `firecrawl` | `3.20.1` | `55d5fbb20270518f` | `/opt/homebrew/bin/firecrawl-mcp` |  |
| `lightpanda` | `0.3.0` | `4ca3897a1547c9b3` | `~/.local/bin/lightpanda` |  |
| `obscura` | `0.1.4-2` | `ec8b7bf0823c4ce2` | `/opt/homebrew/bin/obscura-mcp` |  |
| `playwright` | `0.0.75` | `70dab09ab9a5bc19` | `/opt/homebrew/bin/playwright-mcp` |  |

## Version mismatches

The following MCPs reported one version via their binary's self-report and a different version via the JSON-RPC `initialize` handshake. Lightpanda is the documented case (RESEARCH §1) — binary header says `0.3.0`, handshake says `0.1.0`. Both numbers are recorded above; do not pick one.

- **browser-use**: binary `0.12.7` vs handshake `0.1.0`

