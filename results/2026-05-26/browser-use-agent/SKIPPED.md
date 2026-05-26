# browser-use-agent — SKIPPED (LLM API key absent)

- **reason:** LLM_KEY_ABSENT
- **attempted_command:** `bash scripts/run_mcp_session.sh browser-use` (with
  intent to spawn browser-use's --mcp server in agent mode; the harness's
  Claude session would call browser-use's tool surface, which internally
  invokes an LLM via OPENAI_API_KEY / ANTHROPIC_API_KEY for action planning)
- **error_excerpt:** "No OPENAI_API_KEY or ANTHROPIC_API_KEY with non-empty
  value present in env; cannot test agent mode."
- **linear_ticket:** G-715 (browser-use sub-ticket of G-703)
- **partial_evidence_path:** results/2026-05-26/browser-use-direct/  (direct
  mode IS scored — 3-pass median composite 5.87/10)
- **diagnosis:**
  Per plan 02-05 Task 2 and CONTEXT.md `## Decisions § Claude's Discretion`,
  the harness allows BYO key via env. On this host (2026-05-26), the env
  contains `OPENAI_API_KEY=<empty>` and `ANTHROPIC_API_KEY=<unset>` —
  zero-length sentinels that signal "intentionally not provided." rbw (the
  Bitwarden CLI) is locked, and the autonomous executor cannot prompt the
  user for unlock. The plan explicitly anticipates this branch:
  > If `HAS_LLM_KEY == 0`: write SKIPPED.md for the agent row, complete
  > row for direct mode.
- **what was verified before skipping:**
  - browser-use initialize handshake works in both modes (see
    `init_smoke.json`) — HANDOFF-GSD-AUTO STOP #2 is CONFIRMED FIXED in
    v0.12.7. The 2026-05-21 testbench's `initialize` timeout no longer
    reproduces. This is the headline empirical re-test required by the plan.
  - `bench.tools_inventory browser-use --out ...` returns
    `status=OK, tool_count=16` within ~7s with EITHER empty or unset
    OPENAI_API_KEY/ANTHROPIC_API_KEY. The LLM key is consumed only when
    an agent-driven tool call is invoked (extract / agent-planning), NOT
    at the MCP handshake. So the harness can spawn the server but cannot
    exercise the agent-mode code path.
- **what a follow-up run would need to do:**
  1. Unlock rbw: `rbw unlock` (requires interactive password)
  2. Retrieve a real LLM key, e.g. `rbw get "Anthropic API"` (or OpenAI
     equivalent), export ANTHROPIC_API_KEY=... in the spawning shell
  3. Re-run plan 02-05 Task 2 against THIS evidence directory
  4. The expected outcome (per research/SUMMARY.md): agent mode should
     outperform direct mode on S4-S8 form-handling via browser-use's
     internal LLM-driven `retry_with_browser_use_agent` escape hatch
- **scores.json row treatment:** marked `status: SKIPPED` so the
  N/A-aware composite excludes it (does not count as 0/10 — that's
  reserved for actually-attempted-and-failed runs per the SKIPPED.md
  pattern documented in CONTEXT.md `## Decisions § SKIPPED.md Pattern`)
- **FAIRNESS-05 contract:** preserved. scores.json still contains BOTH
  `browser-use-direct` AND `browser-use-agent` rows. The agent row is
  SKIPPED-with-reason rather than absent.
