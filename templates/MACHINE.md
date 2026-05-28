<!--
  MACHINE.md template — populated once per run by
  scripts/run_mcp_session.sh into results/<date>/MACHINE.md.

  Fields are deliberately generic — NO hostname, NO username, NO MAC
  addresses, NO hardware UUIDs. Per CLAUDE.md "PUBLIC repo. No PII or
  machine identifiers in committed artifacts."

  Placeholders use `${VAR}` syntax substituted by envsubst.
-->

# Machine Manifest — `${DATE}` run

*Captured at:* `${CAPTURED_AT_UTC}` (UTC, NTP-disciplined)
*Run script:* `scripts/run_mcp_session.sh`

## Host

| Field        | Value             |
| ------------ | ----------------- |
| OS           | `${HOST_OS}`      |
| Kernel       | `${HOST_KERNEL}`  |
| Arch         | `${HOST_ARCH}`    |
| macOS ver    | `${MACOS_VERSION}` |

## Tooling

| Tool         | Version              |
| ------------ | -------------------- |
| Claude Code  | `${CLAUDE_VERSION}`  |
| Node         | `${NODE_VERSION}`    |
| npm          | `${NPM_VERSION}`     |
| Python       | `${PYTHON_VERSION}`  |
| uv           | `${UV_VERSION}`      |

## Notes

- Companion file: `versions.json` (machine-readable) +
  `versions.lock.md` (per-MCP SHA256 + version table).
- Per-MCP evidence directories live at
  `results/${DATE}/<mcp-name>/`.
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
