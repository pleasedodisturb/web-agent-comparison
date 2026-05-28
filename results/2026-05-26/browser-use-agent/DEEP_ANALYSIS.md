# browser-use (agent mode) — Deep Analysis

**Wave:** v1.0.1 (2026-05-28)
**MCP:** browser-use 0.12.7 (PyPI), `browser-use --mcp` stdio transport
**Composite:** 0.00 / 10.00 (all 8 dimensions = 0)
**Failure attribution:** `tool-bug` (per FAIRNESS-06)
**Status:** scored (was SKIPPED in v1.0; filled in by v1.0.1 re-run)

## Headline finding

**`browser-use --mcp` does not start a browser when an LLM API key is present in the process environment.** A 30-second `BrowserStartEvent` timeout fires on the first `browser_navigate` call. Every downstream tool (`browser_get_state`, `browser_get_html`, `browser_screenshot`, etc.) then errors with `Root CDP client not initialized`. The same binary, same harness, same fixtures complete S1/S2/S3/S8 cleanly when `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are *unset* (the v1.0 direct-mode result).

The bug is reproducible **without** the harness, **without** a Claude Code session, **without** any orchestrator at all — see `stdio_probe_evidence.log` in this directory. That isolates the failure to browser-use's own startup path when it detects an LLM key.

## Bisection summary

| Configuration | LLM key in env | CDP starts? | Stages passed |
|---------------|----------------|-------------|---------------|
| v1.0 direct mode, PASS1 | none (env scrubbed) | ✅ yes | S1, S2, S3, S8 (4/8 by design — S4-S7 fail on React-Select form interaction, not on CDP) |
| v1.0 direct mode, PASS2 | none | ✅ yes | similar (median 5.87 composite) |
| v1.0 direct mode, PASS3 | none | ✅ yes | similar |
| v1.0.1 agent mode, PASS1 (Anthropic key) | `ANTHROPIC_API_KEY` set | ❌ no | 0/8 (all stage_s*.FAILED) |
| v1.0.1 agent mode, PASS1 (OpenAI key) | `OPENAI_API_KEY` set | ❌ no | 0/8 (all stage_s*.FAILED) |
| v1.0.1 raw stdio probe (no harness) | `OPENAI_API_KEY` set | ❌ no | first `browser_navigate` → 30s `BrowserStartEvent` timeout |

The only variable that flips CDP from working to broken is the presence of an LLM key in env. Tested with two different LLM providers (Anthropic and OpenAI) — same result.

## What we ruled out

- **Harness misimplementation.** The raw stdio probe (`stdio_probe_evidence.log`) reproduces the bug with no harness, no Claude Code session, no orchestrator. Just direct JSON-RPC to the `browser-use --mcp` subprocess.
- **`.mcp.json` misconfiguration.** The entry is `{"command": "browser-use", "args": ["--mcp"]}` — the canonical invocation per `browser-use --help`. There is no separate "agent-mode" subcommand; `--mcp` serves both tool-only and agent paths from the same binary.
- **LLM provider mismatch.** Browser-use's error message says "set OPENAI_API_KEY", but we reproduced the CDP failure with `ANTHROPIC_API_KEY` set too. The CDP failure is independent of which key is set; the LLM-key error only surfaces on `browser_extract_content` and `retry_with_browser_use_agent` (downstream of the dead browser).
- **`~/.browser-use/config.json` (the `api_key` field).** That field is for browser-use Cloud (`cloud_connect_*` neighbors), not for the LLM. `browser-use doctor` confirms the field is "not set" and that's irrelevant to the bug.
- **Snapshot fixture server health.** The fixture server at `http://127.0.0.1:8765/` was running and responsive throughout (verified by direct curl in the harness pre-stage check). The browser never starts; it never gets to make a request.

## Probable root cause (informed guess)

Browser-use 0.12.7's MCP startup path almost certainly tries to instantiate an LLM-driven agent or pre-flight LLM check when it detects an API key in env. That instantiation either:

1. Spawns a subprocess that conflicts with the MCP stdio transport (Python multiprocessing on macOS notoriously hangs with mixed stdin/stdout consumers), or
2. Awaits a `BrowserStartEvent` that depends on an agent worker that itself depends on the browser — a deadlock.

Either way the symptom is: 30-second `BrowserStartEvent` timeout, then `Root CDP client not initialized` on every subsequent call. Without source-diving browser-use 0.12.7 this is a probable-cause not a confirmed one; the upstream maintainers would need to confirm.

## Scoring rationale

All 8 weighted dimensions score **0/10**. The MCP could not perform a single action — not even the simplest read (`browser_navigate` returns a misleading success string while the browser hangs). Per the FAIRNESS-06 attribution rubric this is `tool-bug`, not `env-mismatch`:

- The MCP failed at its own startup, not at a fixture-side or harness-side contract.
- The harness and env satisfied the documented prerequisites (valid LLM key in env, fixture server reachable, `browser-use --mcp` canonical invocation).
- The failure is structurally reproducible across LLM providers and across raw stdio (no harness involved).

Composite calculation:
```
sum(score × weight) = 0 × (3+3+2+2+2+1+1+1) = 0
weighted_denominator = 15 (all 8 dimensions attempted, none N/A — this is a broken tool that COULD have done the work)
composite = 0 / 15 = 0.0
```

Note: this row is NOT N/A. N/A is reserved for "categorically inapplicable" (e.g., read-only MCP × interactive stage per FAIRNESS-03). A broken-but-applicable tool scores 0 with `tool-bug` attribution.

## Comparison to direct mode

| Dimension | direct mode (v1.0) | agent mode (v1.0.1) | Delta |
|-----------|---:|---:|---|
| Data Quality | 10 | 0 | -10 |
| Reliability | 5 | 0 | -5 |
| Speed | 5 | 0 | -5 |
| Token Efficiency | 5 | 0 | -5 |
| Interaction Depth | 2 | 0 | -2 |
| JS Rendering | 10 | 0 | -10 |
| Setup Complexity | 7 | 0 | -7 |
| Error Handling | 2 | 0 | -2 |
| **Composite** | **5.87** | **0.00** | **-5.87** |

The empirical answer to "does browser-use agent mode beat its own direct mode?" — at least in v0.12.7's MCP path with our reproduction — is **no, it can't even start**.

## Reproducer

Minimum steps to reproduce on a fresh checkout:

```bash
# 1. Install browser-use 0.12.7
uv tool install 'browser-use==0.12.7'

# 2. Set any non-empty OPENAI_API_KEY (real or placeholder — the bug doesn't depend on validity)
export OPENAI_API_KEY="sk-proj-anything"

# 3. Speak JSON-RPC to browser-use --mcp directly
python3 - <<'PY'
import json, subprocess, time
p = subprocess.Popen(['browser-use','--mcp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
def send(m): p.stdin.write(json.dumps(m)+'\n'); p.stdin.flush()
send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0.1"}}})
print('init:', p.stdout.readline()[:200])
send({"jsonrpc":"2.0","method":"notifications/initialized"})
time.sleep(0.5)
send({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"browser_navigate","arguments":{"url":"http://example.com/"}}})
t0 = time.time(); print(f'navigate ({time.time()-t0:.0f}s):', p.stdout.readline()[:300])
PY
```

**Expected output (bug present):**
```
navigate (30s): {"...","text":"Error: Event handler ...BrowserSession.on_BrowserStartEvent... timed out after 30.0s..."}
```

**Compare: same code with `unset OPENAI_API_KEY ANTHROPIC_API_KEY`** — `browser_navigate` returns successfully and `browser_get_state` reports a live page.

## Upstream

**Tracked at:** [`browser-use/browser-use#4846`](https://github.com/browser-use/browser-use/issues/4846) — open as of 2026-05-28. The original report (2026-05-16, browser-use 0.12.5/0.12.6 on Ubuntu + remote Edge via `--cdp-url`) describes the same symptom: `browser_navigate` returns a success string while `get_state`/`screenshot`/`list_tabs` fail with `Root CDP client not initialized` and `Expected at least one handler to return a non-None result`. Different platform, same MCP-mode failure shape.

Our v1.0.1 [follow-up comment](https://github.com/browser-use/browser-use/issues/4846#issuecomment-4567226373) adds the env-LLM-key bisection finding (Anthropic and OpenAI both trigger the bug; env-scrubbed direct mode works on the same binary) and a raw-stdio reproducer that bypasses the MCP client entirely. The trigger appears to be browser-use's MCP startup path running some LLM-related pre-flight when it detects a key in env.

**Status as of 2026-05-28:** issue open, awaiting maintainer triage. We'll revisit the score if a fix lands in a future browser-use release.

## Evidence files in this directory

- `PASS1/` — full evidence dir from the v1.0.1 OpenAI-keyed harness run (all 8 stage_s*.FAILED + transcript.md narrating the failure)
- `stdio_probe_evidence.log` — raw stdio probe (no harness, no Claude session) reproducing the 30-second BrowserStartEvent timeout
- `_SKIPPED_*/` — sequestered v1.0 SKIPPED.md and partial smoke-test artifacts (kept for traceability)
- `_failed_anthropic_attempt/` (under `results/2026-05-28/`) — first v1.0.1 attempt with Anthropic key (same failure mode); sequestered separately because the harness wrote it to today's date dir before we re-targeted the proper v1.0 evidence base

## Cost ledger

v1.0.1 rescore cost (out of pocket):
- Anthropic pass (failed CDP, all 8 stages retried by outer Claude session): ~$3
- OpenAI pass (failed CDP, all 8 stages retried by outer Claude session): ~$3
- Raw stdio probe: $0
- **Total:** ~$6 in LLM budget for what was already a definitive structural finding by pass 1.
