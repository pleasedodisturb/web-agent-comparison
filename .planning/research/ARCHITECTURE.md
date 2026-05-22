# Architecture — MCP Comparison Test Harness (Wave 2)

**Domain:** Reproducible benchmark harness for 7 browser-MCP servers across 8 dimensions and 8 test stages, with cross-cutting measurements (cold start, TLS fingerprint, token use, 1hr stability).
**Researched:** 2026-05-22
**Confidence:** HIGH on orchestration model and data layout (existing scaffolding + Claude Code docs); MEDIUM on TLS-capture and stability-loop specifics (chosen from multiple workable approaches).

---

## TL;DR Recommendation

- **Orchestration:** one Claude Code session per MCP, driven by per-MCP **prompt scripts** that walk all 8 stages in order. Project-scope `.mcp.json` already spawns the servers; the session log IS the transcript. Rejected the standalone-stdio / pure-Python-harness options because they would re-implement what Claude Code already does for free and would diverge from the production driver we are actually trying to characterise.
- **Evidence layout:** `results/2026-05-XX/<mcp>/{stage_s1..s8.{ext}, transcript.md, cold_start.json, tokens.json, tls.json, stability.log}` plus a top-level `scores.json` the existing `scoring/score.py` already consumes.
- **Cold start:** wrapper script wraps the MCP binary with `time` + a one-shot stdin script that writes a JSON-RPC `initialize` then `tools/list` and exits on first reply. Records process-spawn → first-`tools/list`-result.
- **TLS:** point each MCP at `https://tls.peet.ws/api/all` as a 9th synthetic stage (S0/S9). Capture the JSON response — server-side it reports JA3, JA3N, JA4, ALPN, HTTP/2 frames. Zero local infra needed. Cross-check the 1–2 most-suspect MCPs with local `mitmproxy` for full pcap.
- **Tokens:** drive each session via `claude --print` with `--output-format stream-json` and parse the `usage` blocks, then run `/mcp` inside the session and capture its per-server token report to `tokens.json`. (Claude Code surfaces both.)
- **Stability:** synthetic load = a 1hr `while true; do <S1>+<S5>+sleep 30; done` driver script per MCP. Logs to `stability.log`; PID watch confirms no crash. Not "do nothing for 1hr" — that just measures TCP keep-alive.
- **Score aggregation:** existing `scoring/score.py` is reused as-is. Drop a new `results/2026-05-XX/scores.json` in the same shape and re-run.
- **Reproducibility surface:** single `Makefile` target. `make bench` runs all 7 MCPs, captures evidence, regenerates `scores.json`, and prints the ranking. README documents `make bench-<mcp>` for one-at-a-time runs.

---

## Component Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                              repo root                                  │
│                                                                         │
│  fixtures/                  scoring/                results/2026-05-XX/ │
│  ├ mock_data.json           ├ rubric.md             ├ scores.json       │
│  └ mock_resume.pdf          └ score.py (unchanged)  ├ playwright/       │
│                                ▲                    ├ browser-use/      │
│                                │ reads              ├ chrome-devtools/  │
│                                │                    ├ lightpanda/       │
│  Makefile  ──────┐             │                    ├ obscura/          │
│   bench          │             │                    ├ firecrawl/        │
│   bench-<mcp>    │             │                    └ cloakbrowser/     │
│   tls            │             │                       │                │
│   coldstart      │             │                       │ each contains: │
│   stability      │             │                       │   stage_s1.*   │
│                  │             │                       │   ...          │
│                  ▼             │                       │   transcript.md│
│  scripts/                      │                       │   cold_start.  │
│  ├ run_mcp_session.sh ───┐     │                       │     json       │
│  │   per-MCP Claude     │      │                       │   tokens.json  │
│  │   driver             │      │                       │   tls.json     │
│  ├ measure_cold_start.sh│      │                       │   stability.log│
│  ├ capture_tls.sh       │      │                       │                │
│  ├ stability_loop.sh    │      │                       │                │
│  └ aggregate_scores.py ─┼──────┘ writes scores.json    │                │
│         │               │                              │                │
│         └─reads─────────┴──────────────────────────────┘                │
│                                                                         │
│  prompts/                       .mcp.json (already exists)              │
│  ├ stage_walk.md   ─── fed to Claude with --append-system-prompt        │
│  ├ stability.md                                                         │
│  └ tls.md                                                               │
└────────────────────────────────────────────────────────────────────────┘
```

### Component boundaries

| Component | Owns | Inputs | Outputs |
|-----------|------|--------|---------|
| `.mcp.json` (project scope) | MCP server lifecycle | (none — Claude Code reads on launch) | 7 spawned stdio MCP processes |
| `prompts/stage_walk.md` | The S1–S8 task script Claude runs against the assigned MCP | `fixtures/mock_data.json`, target URLs | (consumed by Claude session) |
| `scripts/run_mcp_session.sh <mcp>` | Drives one Claude Code session per MCP, restricted to that MCP's tools only | prompt, fixtures, MCP name | `results/<date>/<mcp>/{transcript.md, stage_s*.*, tokens.json}` |
| `scripts/measure_cold_start.sh <mcp>` | Spawns the MCP stdio binary cold, times to first `tools/list` reply, exits | `.mcp.json` (for command + args) | `results/<date>/<mcp>/cold_start.json` |
| `scripts/capture_tls.sh <mcp>` | Drives the MCP to fetch `tls.peet.ws/api/all` and writes the body | per-MCP "navigate + read" prompt | `results/<date>/<mcp>/tls.json` |
| `scripts/stability_loop.sh <mcp>` | Runs the S1+S5 cycle for 60min, logs PID + heartbeat, fails on crash | per-MCP loop prompt | `results/<date>/<mcp>/stability.log` |
| `scripts/aggregate_scores.py` | Reads each `<mcp>/` dir, derives per-dimension scores per the rubric, writes `scores.json` | all evidence directories | `results/<date>/scores.json` |
| `scoring/score.py` (existing) | Computes weighted composite + ranking table | `scores.json` | stdout markdown |
| `Makefile` | Single-command reproducibility surface | (none) | invokes the above in dependency order |

**Boundary rules:**
- **`.mcp.json` is the only place MCP server commands are declared.** Wrapper scripts read it (with `jq`) instead of hard-coding commands — keeps the candidate list authoritative in one file.
- **`scripts/` never talks to `scoring/` directly.** It only writes to `results/<date>/`. `scoring/score.py` reads `scores.json` and knows nothing about MCPs.
- **Per-MCP evidence directories are self-contained.** Anyone inspecting `results/2026-05-XX/playwright/` can reconstruct what that MCP did, in what order, with what timings, without reading any other directory.
- **`fixtures/` is read-only.** No script ever writes back to fixtures.

---

## Data Flow

```
.mcp.json ──spawns──▶ MCP stdio process
                        ▲
                        │ JSON-RPC over stdio
                        │
prompts/stage_walk.md ──▶ Claude Code session ──writes──▶ results/<date>/<mcp>/transcript.md
                          (one per MCP)        ──writes──▶ results/<date>/<mcp>/stage_s*.{yml,md,png,txt}
                                                ──/cost──▶ results/<date>/<mcp>/tokens.json (parsed from stream-json)

.mcp.json ──jq──▶ measure_cold_start.sh ──writes──▶ results/<date>/<mcp>/cold_start.json
.mcp.json ──jq──▶ capture_tls.sh        ──writes──▶ results/<date>/<mcp>/tls.json
prompts/stability.md ──▶ stability_loop.sh ──writes──▶ results/<date>/<mcp>/stability.log

results/<date>/<mcp>/* ──read──▶ aggregate_scores.py ──writes──▶ results/<date>/scores.json
results/<date>/scores.json ──read──▶ scoring/score.py ──prints──▶ ranking table (markdown)
                                                       ──redirect──▶ results/<date>/2026-05-XX_run.md
```

The flow is intentionally **one-way and file-mediated.** Each stage's output is durable on disk, so any step can be re-run independently and the harness recovers without re-running upstream work. This is the same pattern the 2026-03-31 wave used; we are scaling it horizontally (7 MCPs × 8 stages) rather than redesigning it.

---

## Per-Question Decisions

### 1. Test orchestration: one Claude Code session per MCP

**Decision: option (a) — one Claude Code session per MCP, all 8 stages walked in order via a shared prompt.**

Justification against each alternative:

- **(b) Standalone shell scripts that exec MCP servers directly via stdio** — Workable (the MCPs are JSON-RPC stdio servers and `mcptools`/`fastmcp` CLIs exist for this). But the production driver this benchmark is preparing for is *Claude Code itself*. Testing the servers in a different driver measures the server's protocol conformance, not the agent's ability to use it. We'd ship results that don't transfer to the actual use case.
- **(c) Python harness using mcp-cli / official SDK** — Same disqualification as (b), plus it would invent its own prompt-execution loop (effectively re-implementing Claude Code) to drive multi-step interactive stages like S5 (fill form) where the order and choice of tool calls matters. The 2026-05 sandboxed testbench at `~/Projects/terminal-craft/research/goodailist/browser-testbench.md` already showed this: it ran initialize + tools/list + one tool call per MCP and produced 0/15 for browser-use because the harness, not the server, timed out the JSON-RPC.
- **(d) `/mcp` panel + manual transcripts** — fastest to start, impossible to reproduce. Drops out as soon as the third party tries to clone-and-run.

**Implementation shape (`scripts/run_mcp_session.sh`):**
```bash
# Pseudocode
MCP=$1
DATE=$(date +%Y-%m-%d)
OUT=results/$DATE/$MCP
mkdir -p "$OUT"

# Run Claude Code headless, restricted to this MCP's tools only.
# --print = non-interactive, --output-format stream-json gives us per-message usage blocks.
# --allowedTools restricts the session to mcp__<mcp>__* + Read/Write (for stage artifacts).
claude --print \
  --output-format stream-json \
  --allowedTools "mcp__${MCP}__*,Read,Write,Bash" \
  --append-system-prompt "$(cat prompts/stage_walk.md)" \
  "Run stages S1-S8 using only the ${MCP} MCP. Save each stage's artifact to ${OUT}/stage_s<N>.<ext>." \
  | tee "$OUT/raw_stream.jsonl" \
  | jq -r 'select(.type=="assistant").message.content[]?.text' > "$OUT/transcript.md"

# Extract token usage from the stream-json
jq -s 'map(select(.type=="result").usage) | last' "$OUT/raw_stream.jsonl" > "$OUT/tokens.json"
```

Why this is the right call:
- Tools restricted at session boundary → no risk Claude reaches for `WebFetch` mid-task and silently rescues the MCP. Each session is forced to live or die on its assigned MCP.
- `--print` + `stream-json` is the Claude Code-blessed reproducibility surface (see `code.claude.com/docs/en/mcp`).
- Same prompt across all 7 sessions → results are directly comparable.
- The session log is the transcript. No "what did Claude do mid-test?" gap.

### 2. Evidence capture: per-MCP directory, fixed stage filenames

**Naming convention** (mirrors the 2026-03-31 wave but scoped under a date directory):

```
results/2026-05-XX/
  scores.json                          # consumed by scoring/score.py
  2026-05-XX_run.md                    # final published report
  playwright/
    transcript.md                      # Claude session as markdown
    raw_stream.jsonl                   # raw stream-json (audit trail)
    stage_s1_greenhouse.yml            # snapshot (yml for accessibility-tree MCPs)
    stage_s2_ashby.yml
    stage_s3_platform.md               # free-form for detection stages
    stage_s4_navigate.yml
    stage_s5_form_filled.yml
    stage_s6_resume_uploaded.md
    stage_s7_dropdown.md
    stage_s8_screenshot.png            # always a PNG for S8
    cold_start.json                    # {"spawn_to_initialize_ms": N, "spawn_to_tools_list_ms": N}
    tokens.json                        # {"input": N, "output": N, "cache_read": N, "mcp_tools_overhead": N}
    tls.json                           # the tls.peet.ws/api/all response body
    stability.log                      # 60min loop output, one line per heartbeat
  browser-use/
    (same structure)
  ...
```

Why fixed stage filenames per directory rather than `playwright_s1_greenhouse.yml` flat at the top level (which is what 2026-03 used): with 7 MCPs × 8 stages = 56 artifact files, the flat layout becomes unreadable. The per-MCP directory also lets `aggregate_scores.py` walk a single subtree per agent without filename-prefix matching.

Extensions follow what the MCP naturally outputs (the 2026-03 convention — `.yml` for accessibility trees, `.md` for markdown extractions, `.txt` for semantic-text, `.png` for screenshots).

### 3. Cold-start measurement: wrapper script with one-shot JSON-RPC

**Decision: a wrapper script that spawns the MCP binary cold, sends a JSON-RPC `initialize` + `tools/list` over stdin, records the wall-clock from spawn to first `tools/list` result, then SIGTERMs.**

Why "spawn → first `tools/list` reply" and not "spawn → `initialize` reply":
- `initialize` only confirms the protocol handshake; the agent can't actually do anything until it has the tool list.
- A well-behaved server returns tool definitions instantly (static const), but ones that do filesystem/network work at list time (cited in Fastio's MCP cold-start guide) will leak the cost there. That's what we want to surface.

**Implementation (`scripts/measure_cold_start.sh`):**
```bash
# Pseudocode
MCP=$1
CMD=$(jq -r ".mcpServers.${MCP}.command" .mcp.json)
ARGS=$(jq -r ".mcpServers.${MCP}.args | join(\" \")" .mcp.json)
DATE=$(date +%Y-%m-%d)
OUT="results/$DATE/$MCP/cold_start.json"

# Median of 5 runs to defeat OS cache jitter; first run reported separately as "cold-cold"
for i in 1 2 3 4 5; do
  START=$(gdate +%s%N)
  # Pipe two JSON-RPC requests; record time of first tools/list response line
  {
    printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"cold-start-probe","version":"1.0"}}}'
    sleep 0.05
    printf '%s\n' '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
  } | timeout 30 "$CMD" $ARGS \
    | awk -v start="$START" '
        /"id":1/ && !i { print "initialize_ms=" (systime_ns() - start) / 1000000; i=1 }
        /"id":2/ { print "tools_list_ms=" (systime_ns() - start) / 1000000; exit }
      ' >> "$OUT.tmp"
done
# Reduce to {cold_cold_ms, median_warm_ms, listTools_count}
python3 -c '...' > "$OUT"
```

(The `awk systime_ns` thing only works on GNU awk; macOS will need a Python or `gdate` shim. Detail for implementation phase.)

Output schema:
```json
{
  "mcp": "playwright",
  "spawn_to_initialize_ms": {"cold": 1840, "median_warm": 920},
  "spawn_to_tools_list_ms": {"cold": 1860, "median_warm": 935},
  "tools_count": 28,
  "runs": 5
}
```

The 1.8s lightpanda number cited in PROJECT.md is consistent with this method's expected output.

### 4. TLS fingerprint capture: `tls.peet.ws/api/all` as a synthetic stage; `mitmproxy` as the audit cross-check

**Decision: primary capture via `https://tls.peet.ws/api/all`. Secondary audit via local mitmproxy for 1–2 spot-checks.**

Why `tls.peet.ws`:
- It's an externally hosted service whose entire purpose is to echo back the inbound TLS handshake's JA3, JA3N, JA4, JA4_r, ALPN, HTTP/2 frame settings, and cipher list as JSON. Zero local infrastructure.
- It is the de-facto standard probe in TLS-fingerprinting research (cited by Scrapfly, ProxyHat, curl-impersonate's test suite).
- The MCP under test does the navigation — so the fingerprint reflects the actual TLS stack the MCP uses to talk to the internet, not a stub or proxy.
- `scrapfly.io/web-scraping-tools/ja3-fingerprint` is an alternative endpoint; we keep it as a backup if peet.ws is down on test day.

**Why a synthetic "S0" or "S9" stage and not a separate process probe:**
- The whole point is to characterise the MCP's TLS stack as the agent uses it. If we instead measured what `cloakbrowsermcp`'s underlying chromium does when launched directly, we'd miss any wrapper layer the MCP adds.
- Adds one prompt: "Navigate to https://tls.peet.ws/api/all and save the response body to `tls.json`." That's it.

**Implementation (`scripts/capture_tls.sh`):**
```bash
MCP=$1
DATE=$(date +%Y-%m-%d)
OUT="results/$DATE/$MCP/tls.json"

claude --print \
  --allowedTools "mcp__${MCP}__*,Write" \
  "Use ${MCP} to navigate to https://tls.peet.ws/api/all and save the full JSON response body to ${OUT}. Do not modify it. If the MCP can't fetch the body raw, save the markdown extraction instead."
```

**mitmproxy cross-check:** for any MCP where the `tls.json` looks suspicious (claims to be Chrome but JA4 disagrees), launch the MCP through `mitmproxy --listen-port 8080` with the MCP's HTTP_PROXY set, point at a controlled HTTPS endpoint, and capture the actual ClientHello pcap. This is reserve ammo, not part of the standard run — mitmproxy's own JA3 contaminates the fingerprint unless you use its `--mode regular --upstream-cert` carefully.

Output we care about per MCP: JA3 hash, JA3N hash, JA4 string, ALPN order, HTTP/2 frame settings. Score "matches real Chrome" by comparing JA4 against the JA4 of a stock Chrome 128 on the same machine (one-time baseline captured at the same `tls.peet.ws` endpoint).

### 5. Token accounting: parse `--output-format stream-json`, cross-check with `/mcp`

**Decision: token counts come from two places, cross-referenced.**

Primary source: **stream-json output of the headless Claude Code session.** Each assistant message in `--output-format stream-json` includes a `usage` block with `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`. The final `result` event has the cumulative session usage.

Secondary source: **`/mcp` command output captured inside the session.** Claude Code's `/mcp` reports per-MCP-server token overhead (the tool definitions loaded on every request, plus per-tool-call output budget). This separates "tokens the MCP cost just by being connected" from "tokens spent calling it."

Together they give us per-MCP:
- Tokens spent on tool definitions (overhead just by being installed)
- Tokens spent on tool outputs across S1–S8 (the actual "token efficiency" rubric dimension)
- Cache savings (relevant because MCPs that produce stable accessibility-tree IDs cache better)

**Implementation:**
```bash
# Inside run_mcp_session.sh, after the main session run:
claude --print \
  --output-format stream-json \
  --allowedTools "mcp__${MCP}__*" \
  "/mcp" \
  | jq -r 'select(.type=="assistant").message.content[]?.text' > "$OUT/mcp_panel.md"

# Combine into tokens.json
python3 scripts/extract_tokens.py "$OUT/raw_stream.jsonl" "$OUT/mcp_panel.md" > "$OUT/tokens.json"
```

Output schema:
```json
{
  "mcp": "playwright",
  "definitions_overhead_tokens": 7400,
  "session_input_tokens": 12300,
  "session_output_tokens": 4100,
  "cache_read_tokens": 800,
  "tokens_per_stage": {"S1": 1800, "S2": 1100, ..., "S8": 2400}
}
```

The `tokens_per_stage` breakdown is derived from the stream-json by partitioning tool-result events between the user-message boundaries of each stage in the prompt.

**Why not parse Claude Code's `~/.claude/logs/mcp.log`:** that log exists and captures protocol-level traffic, but it doesn't expose Claude's tokeniser's per-message counts (it's raw JSON-RPC, not the tokenised form Claude billed against). The `--output-format stream-json` route gives us the actual billed counts.

### 6. Stability check: synthetic load loop, not idle wait

**Decision: a 60-minute loop that repeats S1+S5 (read + interact) with a 30s sleep between iterations. Logs every iteration; fails the test if the process dies, drops the JSON-RPC connection, or starts returning errors.**

Why a load loop and not "leave it running for 1hr":
- An idle stdio MCP server just blocks on `read(stdin)`. Process can't crash from nothing. Measuring idle uptime tells us about TCP keep-alive, not the MCP's reliability under actual use.
- Production usage cycles between extraction and interaction; that's the workload pattern we care about surviving.

Why S1+S5 specifically: cheapest read-only stage + most state-mutating interactive stage. S5 (fill form) exercises the most tools per invocation and is where 2026-03 wave saw the most MCP-specific failures (BrowserMCP disconnect, Playwright React-Select fallback).

**Implementation (`scripts/stability_loop.sh`):**
```bash
MCP=$1
DATE=$(date +%Y-%m-%d)
OUT="results/$DATE/$MCP/stability.log"

END=$(($(date +%s) + 3600))  # 60 min from now
ITER=0
while [ $(date +%s) -lt $END ]; do
  ITER=$((ITER + 1))
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if claude --print --allowedTools "mcp__${MCP}__*" \
       "Run S1 then S5 from prompts/stage_walk.md. Report PASS or FAIL." \
       > /tmp/stability_$ITER.out 2>&1; then
    echo "$TS iter=$ITER status=PASS" >> "$OUT"
  else
    echo "$TS iter=$ITER status=FAIL exit=$?" >> "$OUT"
    # Keep going — failures within the hour are a finding, not a stop condition
  fi
  sleep 30
done
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) summary iterations=$ITER" >> "$OUT"
```

Scored per the rubric: `reliability` dimension treats <2% failure rate over the hour as 10/10, 2–10% as 5/10, >10% as 0/10. Crash mid-loop = 0/10 regardless of pre-crash success rate.

**Note on resource cost:** 60 cycles × 7 MCPs × ~30s session each = ~3.5 token-hours per MCP, ~25 hours of headless Claude across all 7 if run serially. Run them in parallel where the machine can stand it (Playwright + Chrome-devtools both want Chromium — don't run those concurrently). Document in README.

### 7. Score aggregation: existing `scoring/score.py` is reused; thin shim does the per-MCP → JSON conversion

**Decision: do NOT modify `scoring/score.py`. Add `scripts/aggregate_scores.py` that walks each `results/<date>/<mcp>/` directory and emits `scores.json` in the exact shape the existing scorer already consumes.**

Justification: `scoring/score.py` is 110 lines and clean. Its input contract is `{<agent>: {scores: {<dim>: 0-10}, stages: {<S#>: "PASS|FAIL|N/A"}}}`. Modifying it to know about MCP-specific evidence files (cold-start, TLS, stability) would couple the scorer to the harness and break direct comparability with the 2026-03 wave.

Instead, the shim:
- Reads `cold_start.json` → derives a `speed` modifier
- Reads `tokens.json` → derives `token_efficiency` (rubric thresholds: <10KB=10, 10-50KB=5, >50KB=0)
- Reads each `stage_s*.{yml,md,png,txt}` → derives `data_quality`, `interaction_depth`, `js_rendering` from presence + size + content checks
- Reads `tls.json` → records JA4 string in `notes` (not directly scored; informs `recommendations.md`)
- Reads `stability.log` → derives `reliability`
- Reads `transcript.md` → derives `error_handling` (count of `[error]`/retry phrases)

Output: `results/<date>/scores.json` in the existing shape. Run `python3 scoring/score.py results/<date>/scores.json` → markdown table → append to `results/<date>/2026-05-XX_run.md`.

This preserves direct comparability with 2026-03 (same scorer, same dimensions, same weighting).

### 8. Reproducibility surface: single Makefile

**Decision: a `Makefile` in repo root with targets — `bench`, `bench-<mcp>`, `tls`, `coldstart`, `stability`, `score`, `clean`.**

Why Makefile and not bash script or devcontainer:
- The 7 MCP binaries need to be on `$PATH`. A devcontainer can't install all 7 (CloakBrowser is closed-source binary, Obscura has arch packaging issues per the 2026-05 testbench, lightpanda is a Zig binary). Forcing a container hides those install gotchas; Makefile surfaces them as missing-binary errors at run time, which is more honest.
- A README "first do A, then B, then C" instructs nothing. `make bench` is one command. `make bench-playwright` is one command. `make clean && make bench` is one command.

```makefile
# Pseudocode
DATE := $(shell date +%Y-%m-%d)
MCPS := playwright browser-use chrome-devtools lightpanda obscura firecrawl cloakbrowser

.PHONY: bench score clean tls coldstart stability $(addprefix bench-,$(MCPS))

bench: $(addprefix bench-,$(MCPS)) tls coldstart stability score

bench-%: results/$(DATE)/%/
	scripts/run_mcp_session.sh $*

results/$(DATE)/%/:
	mkdir -p $@

tls:
	@for m in $(MCPS); do scripts/capture_tls.sh $$m; done

coldstart:
	@for m in $(MCPS); do scripts/measure_cold_start.sh $$m; done

stability:
	@for m in $(MCPS); do scripts/stability_loop.sh $$m; done

score: results/$(DATE)/scores.json
	python3 scoring/score.py results/$(DATE)/scores.json | tee -a results/$(DATE)/$(DATE)_run.md

results/$(DATE)/scores.json: $(wildcard results/$(DATE)/*/transcript.md)
	python3 scripts/aggregate_scores.py results/$(DATE)/ > $@
```

External user contract documented in README:
```bash
# Prereqs (one-time): all 7 MCP binaries installed (see scripts/check_prereqs.sh)
# Optional: FIRECRAWL_API_KEY in env (firecrawl scored as N/A if absent)
make bench           # full run, ~3hrs serial
make bench-playwright # one MCP only, ~5min
make score           # re-score from existing evidence without re-running
```

`scripts/check_prereqs.sh` does `which` for every binary in `.mcp.json` and prints a one-line install command per missing one. That's the entire "setup" surface for an external reader.

---

## Build Order with Phase Dependencies

The roadmap should split this into **4 phases** at Standard granularity:

### Phase 1 — Harness foundation (BLOCKER for everything downstream)

Deliverables:
- `scripts/run_mcp_session.sh` working end-to-end against Playwright (the known-good baseline from 2026-03)
- `prompts/stage_walk.md` finalised — same 8 stages, parameterised on the MCP under test
- `results/<date>/playwright/` populated with a full run as the format reference
- `scripts/aggregate_scores.py` producing valid `scores.json` from one MCP's evidence
- `scripts/check_prereqs.sh` and the Makefile skeleton

Stop condition: `make bench-playwright && make score` produces a comparable score to the 2026-03 Playwright row (~9/10). If the harness can't reproduce a known result, fix the harness before adding more MCPs.

Dependencies: none — pure scaffolding work.

### Phase 2 — Per-MCP scoring runs (depends on Phase 1)

Deliverables:
- One full evidence directory per MCP (6 more: browser-use, chrome-devtools, lightpanda, obscura, firecrawl, cloakbrowser)
- Per-MCP findings notes recorded in transcript.md
- `scores.json` populated for all 7

This phase can be **parallelised across the 7 MCPs** once Phase 1 is done — they share no state except the Makefile. Mac Mini probably runs 2 concurrent sessions cleanly (one Chromium-based MCP + one headless lightweight) before resource contention shows; Playwright + Chrome-devtools both want their own Chromium, don't pair those.

Stop condition: all 7 MCPs have at least the read-only stages (S1–S3) attempted, with PASS/FAIL/N_A clearly recorded. Interactive stages (S4–S8) are N_A for read-only MCPs (lightpanda, firecrawl) by definition — that IS the scoring signal.

Known risks:
- Firecrawl needs `FIRECRAWL_API_KEY` (gracefully skip, score 6/7)
- Obscura needs `obscura-mcp install` for engine + arm64 Linux packaging gap (skip if unavailable per 2026-05 testbench, score 6/7)
- Browser-use has the transport-mismatch bug from 2026-05 testbench — may need investigation, mark as a blocker for that MCP's row
- CloakBrowser is sandbox-only — only run against the public Greenhouse + Ashby fixtures, NEVER against a target that holds the user's cookies

Dependencies: Phase 1 complete and validated on Playwright.

### Phase 3 — Cross-cutting measurements (depends on Phase 1, parallel to Phase 2)

Deliverables:
- `scripts/measure_cold_start.sh` → `cold_start.json` per MCP
- `scripts/capture_tls.sh` → `tls.json` per MCP + a baseline JA4 from real Chrome
- `scripts/stability_loop.sh` → `stability.log` per MCP (60min × 7 = 7 hrs serial; can parallelise where machine supports it)

Important: this phase **can start the moment Phase 1 is done** and runs in parallel with Phase 2. The cross-cutting scripts don't need the per-MCP scoring runs to have completed; they read `.mcp.json` directly. If the machine has spare capacity, run cross-cuts on already-completed MCPs while per-MCP scoring runs continue on the others.

Stop condition: all 7 MCPs have all 3 cross-cut artifacts (cold_start, tls, stability), even if some are "FAIL: would not connect."

Dependencies: Phase 1 complete (needs `.mcp.json` and the per-MCP output dir convention to exist).

### Phase 4 — Synthesis + reproducibility validation (depends on Phases 2 and 3)

Deliverables:
- `aggregate_scores.py` enriched to incorporate cold-start, TLS, and stability into the rubric scores
- `results/<date>/scores.json` final
- `results/<date>/<date>_run.md` final report (the headline comparison matrix, same shape as `results/2026-03-31_run.md`)
- `results/recommendations.md` — explicit "graduate to Stage 2 toolkit" verdict, ranked
- README updated with methodology + headline verdict
- Third-party reproducibility validated: clone repo, `make bench`, get similar scores. Document any non-reproducible findings as known-fragile.

Stop condition: a clean checkout on the MacBook (not the Mini, where development happened) runs `make bench` and produces a `scores.json` that ranks MCPs in the same order, within ±0.5 composite points per MCP. This is the actual "reproducibility validated" requirement from PROJECT.md.

Dependencies: Phase 2 (per-MCP runs) and Phase 3 (cross-cutting measurements) both complete.

### Phase dependency graph

```
Phase 1 (harness)
   │
   ├──▶ Phase 2 (per-MCP runs, parallelisable across MCPs)
   │       │
   │       └──┐
   │          │
   ├──▶ Phase 3 (cross-cutting, parallel to Phase 2)
   │          │
   │       ┌──┘
   │       │
   │       ▼
   └──▶ Phase 4 (synthesis + reproducibility)
```

Phase 2 and Phase 3 can fully overlap. Phase 4 cannot start until both have populated every MCP's evidence directory.

---

## Scalability Considerations

| Concern | At 7 MCPs (now) | At 15 MCPs (hypothetical follow-up) | At 30 MCPs (research arms race) |
|---------|----------------|-------------------------------------|--------------------------------|
| Wall-clock per full `make bench` | ~3hrs serial, ~1hr with 3-way parallelism | ~6hrs / ~2hrs | rethink — split into nightly cron jobs |
| Disk per run | ~50MB (mostly screenshots) | ~120MB | ~250MB; consider compressing per-MCP dir into tar.zst |
| Token cost per full run | ~$5–10 of Claude Code usage | ~$15–25 | ~$40–80; consider Haiku for cold-start/TLS stages |
| Evidence-format churn | small — fixed stage filenames | small | small (the per-MCP-dir layout absorbs new MCPs cleanly) |
| `scoring/score.py` extensibility | unchanged | unchanged (rubric is fixed) | rubric may need new dimensions if SOTA shifts; that's a rubric-level decision, not a harness change |

The architecture scales linearly in MCP count with no central choke point. The bottleneck at any scale is parallel sessions vs Chromium memory (~400MB per Chromium-backed MCP); the Makefile should expose a `MAX_PARALLEL` knob.

---

## Patterns to Follow

### Pattern 1: File-mediated stage handoff
Every script writes to `results/<date>/<mcp>/`; every downstream reader reads from there. No script invokes another script directly with arguments beyond `<mcp>` and `<date>`. Makes any single step trivially re-runnable.

### Pattern 2: `.mcp.json` is the single source of truth for MCP definitions
Wrapper scripts read commands and args via `jq` from `.mcp.json`. Don't duplicate MCP commands into shell scripts. When a new MCP gets added to the comparison, `.mcp.json` is the only edit + a one-line addition to the Makefile's `MCPS` variable.

### Pattern 3: Existing scorer is sacrosanct
`scoring/score.py` and `scoring/rubric.md` are inputs to this wave, not outputs. The harness produces `scores.json` in the shape the scorer expects. This preserves comparability with 2026-03 and any future wave.

### Pattern 4: Stage prompts are versioned with the harness
`prompts/stage_walk.md` lives in git. Any change to what S1–S8 do invalidates prior runs. If we need to evolve the stages, we bump a version marker in the prompt and tag the run dir accordingly.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: "Just paste the transcripts into the report"
**Why bad:** Not reproducible. Anyone who can't see the transcripts can't verify the scores. 2026-03 got away with this because scope was small (5 agents, 1 person); 2026-05 has 7 MCPs × 8 stages × multiple sub-measurements — manual paste-up will silently drop entries.
**Instead:** every observation lives in a file under `results/<date>/<mcp>/`. The published `_run.md` reads files to populate tables.

### Anti-Pattern 2: Reimplementing Claude Code as a Python harness
**Why bad:** We are characterising MCPs *as Claude Code uses them*. A Python harness measures something different — protocol conformance, not agent-driven usability. The 2026-05 testbench at terminal-craft already shows this trap (browser-use scored 0/15 because of the harness, not the MCP).
**Instead:** drive everything through `claude --print` with stream-json. The session log IS the test transcript.

### Anti-Pattern 3: Letting Claude reach for fallback tools mid-test
**Why bad:** A Playwright session that silently falls back to WebFetch when Playwright fails will score Playwright as if it worked. We lose the failure signal.
**Instead:** `--allowedTools "mcp__${MCP}__*,Read,Write,Bash"` per session. No WebFetch, no other MCPs. Force each session to live or die on the assigned MCP.

### Anti-Pattern 4: Mixing cross-cut measurements into the main session
**Why bad:** Cold-start can't be measured from inside a session that's already warm. TLS capture pollutes the token count for that MCP. Stability loops invalidate "first usable tool call" timing.
**Instead:** four separate scripts (`run_mcp_session`, `measure_cold_start`, `capture_tls`, `stability_loop`), four separate artifact files, joined only at score-aggregation time.

### Anti-Pattern 5: Storing raw stream-json without a transcript view
**Why bad:** stream-json is reproducible but unreadable by humans. Future-you reading the report wants to skim what Claude actually did, not parse `jq` queries.
**Instead:** save both `raw_stream.jsonl` (audit trail) AND `transcript.md` (human-skimmable extraction). Cheap and one `jq` away.

---

## Sources

- **Claude Code MCP docs** (`code.claude.com/docs/en/mcp`) — `--allowedTools` syntax, `--output-format stream-json`, `/mcp` panel behaviour. HIGH confidence.
- **MindStudio "Claude Code MCP Token Overhead"** (`mindstudio.ai/blog/claude-code-mcp-server-token-overhead`) — per-MCP token cost surfacing via `/mcp` and `/context`. MEDIUM (vendor blog, but corroborated by GitHub issue #31564 on anthropics/claude-code about per-session token visibility).
- **Fastio "MCP Server Cold Start Optimization"** (`fast.io/resources/mcp-server-cold-start-optimization/`) — methodology for what counts as cold-start, why `tools/list` matters separately from `initialize`. MEDIUM (vendor blog, technically grounded).
- **mcptools** (`github.com/f/mcptools`) and **FastMCP CLI** (`gofastmcp.com/clients/cli`) — confirm stdio-direct invocation is well-supported, used to validate (and reject) option (b) for orchestration. HIGH.
- **tls.peet.ws / scrapfly JA3 endpoint** (`tls.peet.ws`, `scrapfly.io/web-scraping-tools/ja3-fingerprint`) — established external probes for JA3/JA4 capture. HIGH (multiple independent corroborating sources: ProxyHat, Scrapfly blog, curl-impersonate test suite).
- **Browserless "TLS Fingerprinting in Playwright/Puppeteer"** (`browserless.io/blog/tls-fingerprinting-explanation-detection-and-bypassing-it-in-playwright-and-puppeteer`) — headless browser TLS stack uses the real browser TLS, which is why probing from inside the MCP session is the right level. HIGH.
- **JA4+ paper / Althouse Medium** (`medium.com/foxio/ja4-network-fingerprinting-9376fe9ca637`) — JA4 supersedes JA3 because of TLS extension permutation in Chrome 110+/Firefox 114+. Why we record JA4 (not just JA3) as the durable fingerprint. HIGH.
- **Existing repo:** `scoring/rubric.md`, `scoring/score.py`, `results/2026-03-31_run.md`, `.mcp.json`, `PROJECT.md`, `HANDOFF.md` — direct constraints. HIGH.
- **`~/.claude/docs/browser-tools.md`** — the 2026-05 sandboxed testbench prior art at `~/Projects/terminal-craft/research/goodailist/browser-testbench.md`, MCP per-tool gotchas, sandbox-only constraints on CloakBrowser, Obscura macOS Sec-CH-UA-Platform leak. HIGH (user's own validated notes).
