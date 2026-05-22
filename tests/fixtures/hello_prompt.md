<!--
hello_prompt.md — minimal stage_walk replacement for the smoke test.

The smoke test (tests/test_run_mcp_session_smoke.sh) sets
STAGE_WALK_PATH to point at this file instead of the real
prompts/stage_walk.md, so the driver can be exercised end-to-end
without running the full S1-S8 walk (which is 4+ minutes per run and
exercises the actual MCP, neither of which the smoke test wants).

The single instruction below uses Write (which is in the allow-list of
every MCP run, since --allowedTools is "mcp__${MCP}__*,Read,Write,Bash")
so it works against any MCP without touching the MCP itself.

Placeholders are the same as the real prompt: ${MCP},
${SNAPSHOT_BASE_URL}, ${OUT_DIR}. The wrapper substitutes them via
envsubst before piping to Claude Code.
-->

You are exercising the smoke-test path for the ${MCP} MCP harness driver.

DO NOT call any MCP tools. DO NOT navigate any URLs.

Your ONLY task: use the Write tool to create the file
`${OUT_DIR}/stage_s1.md` with exactly this content (and nothing else):

```
hello
```

Then STOP. Do not call any other tools. Do not write a transcript.
