<!--
  MACHINE.md template — populated once per run by
  scripts/run_mcp_session.sh into results/<date>/MACHINE.md.

  Fields are deliberately generic — NO hostname, NO username, NO MAC
  addresses, NO hardware UUIDs. Per CLAUDE.md "PUBLIC repo. No PII or
  machine identifiers in committed artifacts."

  Placeholders use `` syntax substituted by envsubst.
-->

# Machine Manifest — `` run

*Captured at:* `2026-05-26T18:41:53Z` (UTC, NTP-disciplined)
*Run script:* `scripts/run_mcp_session.sh`

## Host

| Field        | Value             |
| ------------ | ----------------- |
| OS           | `Darwin`      |
| Kernel       | `25.5.0`  |
| Arch         | `arm64`    |
| macOS ver    | `26.5` |

## Tooling

| Tool         | Version              |
| ------------ | -------------------- |
| Claude Code  | `2.1.142 (Claude Code)`  |
| Node         | `v26.0.0`    |
| npm          | `11.12.1`     |
| Python       | `Python 3.14.5`  |
| uv           | `uv 0.11.16 (Homebrew 2026-05-21 aarch64-apple-darwin)`      |

## Notes

- Companion file: `versions.json` (machine-readable) +
  `versions.lock.md` (per-MCP SHA256 + version table).
- Per-MCP evidence directories live at
  `results//<mcp-name>/`.
- This file is regenerable. Re-run `scripts/run_mcp_session.sh` to
  refresh.

## Public-repo hygiene

This file deliberately omits:

- `hostname`, `whoami`, `pleasedodisturb`
- MAC addresses, hardware UUIDs
- Absolute home-directory paths (collapsed to `~/...`)
- Any private network identifiers

If you notice anything machine-identifying that slipped in, file a
G-703 sub-ticket — that is a P0 leak.
