<!--
  MACHINE.md template — populated once per run by
  scripts/run_mcp_session.sh into results/<date>/MACHINE.md.

  Fields are deliberately generic — NO hostname, NO username, NO MAC
  addresses, NO hardware UUIDs. Per CLAUDE.md "PUBLIC repo. No PII or
  machine identifiers in committed artifacts."

  Placeholders use `` syntax substituted by envsubst.
-->

# Machine Manifest — `2026-05-27` run

*Captured at:* `2026-05-27T22:00:43Z` (UTC, NTP-disciplined)
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
- Git-tracked lock-file bundle (phase SC3): `uv.lock` +
  `package-lock.json` at the repo root resolve the exact transitive
  dependency tree used by this wave.
- Per-MCP evidence directories live at
  `results/2026-05-27/<mcp-name>/`.
- This file is regenerable. Re-run `scripts/run_mcp_session.sh` to
  refresh.

## Public-repo hygiene

This file deliberately omits:

- `hostname`, `whoami`, `$USER`
- MAC addresses, hardware UUIDs
- Absolute home-directory paths (collapsed to `~/...`)
- Any private network identifiers

If you notice anything machine-identifying that slipped in, file a
G-703 sub-ticket — that is a P0 leak.
