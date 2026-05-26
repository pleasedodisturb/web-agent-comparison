---
phase: 2
plan: 05
mcp: browser-use
type: execute
wave: 5
depends_on:
  - 01-01
  - 01-02
  - 01-03
  - 01-04
  - 01-05
  - 01-06
  - 01-07
  - 02-01
  - 02-02
  - 02-03
  - 02-04
files_modified:
  - results/<DATE>/browser-use-direct/                 # full evidence dir OR SKIPPED.md (direct mode — no LLM key)
  - results/<DATE>/browser-use-agent/                  # full evidence dir OR SKIPPED.md (agent mode — LLM key set)
  - results/<DATE>/browser-use-direct/PASS{1,2,3}.json
  - results/<DATE>/browser-use-agent/PASS{1,2,3}.json
  - results/<DATE>/browser-use-direct/DEEP_ANALYSIS.md
  - results/<DATE>/browser-use-agent/DEEP_ANALYSIS.md
  - results/<DATE>/scores.json                          # adds TWO rows: browser-use-direct + browser-use-agent
requirements:
  - FAIRNESS-04
  - FAIRNESS-05
success_criteria_advanced: [1, 3, 4]
status: planned
autonomous: true
estimate_hours: 2

must_haves:
  truths:
    - "browser-use produces TWO rows in scores.json: `browser-use-direct` (no LLM key) and `browser-use-agent` (LLM key enabled). Each is its own evidence directory at `results/<DATE>/browser-use-direct/` and `results/<DATE>/browser-use-agent/`. This is the FAIRNESS-05 contract — explicitly enumerated in Phase 2 SC #3."
    - "browser-use-direct row carries capability tag `LLM-augmented` with mode `direct` (Vitalik's specific empirical question: 'does it work without user's own LLM API key?'). browser-use-agent row carries capability tag `LLM-augmented` with mode `agent`."
    - "If the 2026-05-21 testbench's `initialize` timeout is STILL PRESENT in v0.12.7: per HANDOFF-GSD-AUTO STOP #2 + CONTEXT.md, file a Linear bug ticket against vendor, score the affected row as `0/15 — tool-bug` with footnote, do NOT retry indefinitely."
    - "If the user's environment lacks an LLM key (no OPENAI_API_KEY or ANTHROPIC_API_KEY in env): browser-use-agent SKIPPED.md with reason=LLM_KEY_ABSENT; browser-use-direct continues independently. Both rows present in scores.json."
    - "Direct mode is run with `unset OPENAI_API_KEY ANTHROPIC_API_KEY` before spawning per CONTEXT.md `## Specifics`. Agent mode is run with the env intact."
  artifacts:
    - path: "results/<DATE>/browser-use-direct/"
      provides: "Evidence for direct mode (Vitalik's headline empirical question)"
    - path: "results/<DATE>/browser-use-agent/"
      provides: "Evidence for agent mode (LLM-augmented baseline)"
    - path: "results/<DATE>/browser-use-{direct,agent}/DEEP_ANALYSIS.md"
      provides: "Per-mode analysis: direct-mode no-key success/failure narrative; agent-mode comparison vs Playwright"
    - path: "results/<DATE>/scores.json"
      provides: "TWO rows under keys browser-use-direct and browser-use-agent (NOT a single browser-use row)"
  key_links:
    - from: "scripts/run_mcp_session.sh browser-use (direct)"
      to: "unset OPENAI_API_KEY ANTHROPIC_API_KEY"
      via: "env scrubbing before claude --print spawn"
      pattern: "unset.*OPENAI_API_KEY"
    - from: "scores.json schema"
      to: "two distinct row keys: browser-use-direct + browser-use-agent"
      via: "FAIRNESS-05 contract"
      pattern: "browser-use-(direct|agent)"
---

## Goal

Drive the harness against **browser-use** in BOTH modes — `direct` (no LLM key set) and `agent` (LLM key set) — producing TWO evidence directories and TWO rows in `scores.json`. This is the load-bearing validation of Phase 2 SC #3 ("browser-use produces two rows... each labeled with mode and scored independently") and FAIRNESS-05. Also re-tests the 2026-05-21 testbench's `initialize` timeout on v0.12.7 per HANDOFF-GSD-AUTO STOP #2. The 2-task structure pairs the two modes; this is the only Phase-2 plan that runs the harness 6 times total (3 per mode), so it gets the largest estimate.

## Files Modified

- `results/<DATE>/browser-use-direct/` — direct-mode evidence dir (or SKIPPED.md if INIT_TIMEOUT)
- `results/<DATE>/browser-use-agent/` — agent-mode evidence dir (or SKIPPED.md if LLM_KEY_ABSENT or INIT_TIMEOUT)
- `results/<DATE>/scores.json` — adds TWO rows: `browser-use-direct` + `browser-use-agent`

## Tasks

### Task 1: Direct mode (no LLM key) — 3 passes + scoring

<files>results/&lt;DATE&gt;/browser-use-direct/PASS{1,2,3}/, results/&lt;DATE&gt;/browser-use-direct/DEEP_ANALYSIS.md, results/&lt;DATE&gt;/scores.json</files>

<action>
This is Vitalik's headline empirical question per CONTEXT.md `## Specifics`: "browser-use direct mode is the one Vitalik specifically wants validated (claim: 'works without user's own LLM API key')."

Pre-flight initialize-timeout check (HANDOFF STOP #2): before any full pass, run a quick `initialize` smoke test:
```
.venv/bin/python -m bench.tools_inventory browser-use --out /tmp/browser-use-init-check.json
```
If the smoke test returns a status indicating `INITIALIZE_TIMEOUT` (the failure mode `bench/tools_inventory.py` already classifies), STOP and surface:
- File a Linear bug ticket against the browser-use repo (note the vendor's GitHub issue tracker; do not commit a draft to this repo)
- Document the timeout in `results/<DATE>/browser-use-direct/INIT_TIMEOUT_REPORT.md` with the bench/tools_inventory.py output verbatim
- Write `results/<DATE>/browser-use-direct/SKIPPED.md` with `reason: INIT_TIMEOUT`
- Update `scores.json` with row `browser-use-direct` marked SKIPPED (per the same schema plan 02-03 uses)
- Skip the rest of Task 1; proceed to Task 2 (agent mode) which will hit the same timeout — Task 2 has identical handling

If the smoke test succeeds (initialize completes), proceed:

1. Scrub LLM env vars and run the harness 3 times in direct mode. The env scrub MUST happen in the shell that spawns `run_mcp_session.sh`:
   ```
   for n in 1 2 3; do
     env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY MCP_MODE=direct \
       bash scripts/run_mcp_session.sh browser-use
     # Move output into a per-mode dir
     mv "results/<DATE>/browser-use" "results/<DATE>/browser-use-direct/PASS${n}-tmp"
     mkdir -p "results/<DATE>/browser-use-direct"
     mv "results/<DATE>/browser-use-direct/PASS${n}-tmp" "results/<DATE>/browser-use-direct/PASS${n}"
     # Aggregate this pass
     scripts/aggregate_scores.py "results/<DATE>/browser-use-direct/PASS${n}/"
     mv "results/<DATE>/browser-use-direct/PASS${n}/scores.json" "results/<DATE>/browser-use-direct/PASS${n}.json"
     # ≥30 min gap before next pass (Pitfall 1)
   done
   ```
   Note: `run_mcp_session.sh` writes to `results/<DATE>/browser-use/` by default (using the MCP name). The plan needs to remap this; one pragmatic approach is to set `OUT_DIR` explicitly via a wrapper `MCP_NAME=browser-use OUT_DIR=results/<DATE>/browser-use-direct/PASS<N> bash scripts/run_mcp_session.sh browser-use`, but `run_mcp_session.sh` does NOT honor an external `OUT_DIR` per its line 70 (it sets it unconditionally). The cleanest path: let the harness run, then `mv results/<DATE>/browser-use results/<DATE>/browser-use-direct/PASS<N>` immediately after each pass before the next pass starts. Document this in `results/<DATE>/browser-use-direct/HARNESS_NOTES.md` so reproducers can follow.

2. In each pass's per-pass aggregation, the aggregator at `scripts/aggregate_scores.py` will key the row under whatever the MCP-dir basename is. The PASS<N>/ directory basename is `browser-use` (post-move), so PASS<N>.json contains a `"browser-use"` key. The merge step (Task 1 step 3) will rename this to `"browser-use-direct"` before inserting into `results/<DATE>/scores.json`.

3. Compute median row across PASS{1,2,3}.json per plan 02-01 Task 2 algorithm. RENAME the row from `"browser-use"` → `"browser-use-direct"` before inserting into scores.json. Add row-level fields:
   - `capability`: `"LLM-augmented"`
   - `mode`: `"direct"` (no LLM key)
   - `linear_ticket`: <browser-use sub-ticket from G-715..G-720>

4. Write `results/<DATE>/browser-use-direct/DEEP_ANALYSIS.md`:
   - Capability tag + median composite + per-stage verdicts
   - **The falsifiable empirical finding (Vitalik's question):** "Does browser-use work in Claude Code WITHOUT the user's own LLM API key?"
     - Pre-spawn env state confirmed: `OPENAI_API_KEY=<unset>` `ANTHROPIC_API_KEY=<unset>` (echo `env | grep -E "OPENAI|ANTHROPIC" || echo "none"` to confirm; do NOT echo values)
     - Pass-pass-pass: which stages succeeded? Did browser-use refuse to start, run with degraded behavior, or work fully?
     - Document outcome: claim CONFIRMED / PARTIALLY CONFIRMED / REFUTED
   - INIT timeout history note (testbench 2026-05-21 had it; v0.12.7 status: confirmed-fixed OR confirmed-broken)
   - Failure-attribution table + Linear sub-ticket reference

Wall-clock gate: 60 minutes per pass; 3 passes per mode × 2 modes = 6 total runs, so this plan is the most expensive Phase-2 plan. If passes are slow, surface early.
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
if [[ -f "results/$DATE/browser-use-direct/SKIPPED.md" ]]; then
  grep -q -E "(INIT_TIMEOUT|LLM_KEY)" "results/$DATE/browser-use-direct/SKIPPED.md" &&
  .venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
assert 'browser-use-direct' in data
assert data['browser-use-direct'].get('status') == 'SKIPPED'
print('OK (skipped)')
"
else
  test -d "results/$DATE/browser-use-direct/PASS1" &&
  test -d "results/$DATE/browser-use-direct/PASS2" &&
  test -d "results/$DATE/browser-use-direct/PASS3" &&
  .venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
row = data['browser-use-direct']
assert row.get('capability') == 'LLM-augmented'
assert row.get('mode') == 'direct'
print('OK (scored)')
"
fi
</automated>
</verify>

<done>
EITHER direct-mode SKIPPED.md exists with INIT_TIMEOUT or related reason + scores.json marked SKIPPED. OR 3 passes captured + scores.json has `browser-use-direct` row with capability=LLM-augmented, mode=direct + DEEP_ANALYSIS.md answers Vitalik's empirical question explicitly.
</done>

### Task 2: Agent mode (LLM key enabled) — 3 passes + scoring

<files>results/&lt;DATE&gt;/browser-use-agent/PASS{1,2,3}/, results/&lt;DATE&gt;/browser-use-agent/DEEP_ANALYSIS.md, results/&lt;DATE&gt;/scores.json</files>

<action>
Pre-flight: check whether an LLM key is available in the env:
```
HAS_LLM_KEY=0
if [[ -n "${OPENAI_API_KEY:-}" || -n "${ANTHROPIC_API_KEY:-}" ]]; then HAS_LLM_KEY=1; fi
```

If `HAS_LLM_KEY == 0`: per CONTEXT.md `## Decisions § Claude's Discretion` — "Whether to capture browser-use-agent runs at all if no LLM key is locally available... SKIPPED.md for the agent row, complete row for direct mode." Write `results/<DATE>/browser-use-agent/SKIPPED.md`:
```markdown
# browser-use-agent — SKIPPED (LLM API key absent)

- **reason:** LLM_KEY_ABSENT
- **attempted_command:** `bash scripts/run_mcp_session.sh browser-use` (with OPENAI_API_KEY or ANTHROPIC_API_KEY in env)
- **error_excerpt:** "No OPENAI_API_KEY or ANTHROPIC_API_KEY in env; cannot test agent mode"
- **linear_ticket:** <browser-use sub-ticket from G-715..G-720>
- **partial_evidence_path:** results/<DATE>/browser-use-direct/  (direct mode IS scored)
- **diagnosis:** Per CONTEXT.md, the harness allows BYO key via env. Operator did not set a key.
```
Update `scores.json` with `browser-use-agent` row marked SKIPPED. Skip the rest of Task 2.

If `HAS_LLM_KEY == 1`: run the harness 3 times in agent mode (env intact):
```
for n in 1 2 3; do
  MCP_MODE=agent bash scripts/run_mcp_session.sh browser-use
  mv "results/<DATE>/browser-use" "results/<DATE>/browser-use-agent/PASS${n}"
  scripts/aggregate_scores.py "results/<DATE>/browser-use-agent/PASS${n}/"
  mv "results/<DATE>/browser-use-agent/PASS${n}/scores.json" "results/<DATE>/browser-use-agent/PASS${n}.json"
done
```

INIT timeout: same handling as Task 1. If Task 1 already hit INIT_TIMEOUT, agent mode WILL too (same MCP binary) — write SKIPPED.md for agent mode with `reason: INIT_TIMEOUT` referencing direct mode's report.

Compute median row + insert into scores.json under key `browser-use-agent`. Row-level fields:
- `capability`: `"LLM-augmented"`
- `mode`: `"agent"` (LLM key enabled)
- `linear_ticket`: <same sub-ticket as direct mode>

Write `results/<DATE>/browser-use-agent/DEEP_ANALYSIS.md`:
- Capability tag + median composite + per-stage verdicts
- **Agent vs Direct comparison:** explicitly compare the two browser-use rows (agent should outperform direct on S4-S8 form-handling per the LLM-driven `retry_with_browser_use_agent` escape hatch per research/SUMMARY.md). Cite specific dimensional deltas.
- **Apples-to-oranges caveat:** per FAIRNESS-04, agent-mode uses an internal LLM that other MCPs don't have. The capability tag carries the disclaimer; recommendations.md must surface this. State explicitly in DEEP_ANALYSIS.md.
- **The browser-use init-timeout note:** if the 2026-05-21 testbench bug appeared in either mode, document. If both modes worked, document THAT (testbench bug confirmed fixed in v0.12.7).
- Failure-attribution table + Linear sub-ticket reference

Wall-clock gate: 60 min per pass.
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
if [[ -f "results/$DATE/browser-use-agent/SKIPPED.md" ]]; then
  grep -q -E "(LLM_KEY_ABSENT|INIT_TIMEOUT)" "results/$DATE/browser-use-agent/SKIPPED.md" &&
  .venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
assert 'browser-use-agent' in data
assert data['browser-use-agent'].get('status') == 'SKIPPED'
print('OK (skipped)')
"
else
  test -d "results/$DATE/browser-use-agent/PASS1" &&
  test -d "results/$DATE/browser-use-agent/PASS2" &&
  test -d "results/$DATE/browser-use-agent/PASS3" &&
  .venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
row = data['browser-use-agent']
assert row.get('capability') == 'LLM-augmented'
assert row.get('mode') == 'agent'
print('OK (scored)')
"
fi &&
# Both rows must exist in scores.json (the FAIRNESS-05 contract)
.venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
assert 'browser-use-direct' in data
assert 'browser-use-agent' in data
print('Both rows present')
"
</automated>
</verify>

<done>
scores.json has BOTH `browser-use-direct` and `browser-use-agent` rows (each may be SKIPPED or scored independently). The two rows are clearly distinguished by `mode` field. DEEP_ANALYSIS.md exists for any scored mode; agent-mode DEEP_ANALYSIS.md explicitly compares to direct-mode results.
</done>

## Acceptance

- [ ] `results/<DATE>/browser-use-direct/` exists (SKIPPED.md or full evidence + 3 passes + DEEP_ANALYSIS.md).
- [ ] `results/<DATE>/browser-use-agent/` exists (SKIPPED.md or full evidence + 3 passes + DEEP_ANALYSIS.md).
- [ ] `scores.json` contains BOTH `browser-use-direct` AND `browser-use-agent` rows (each scored independently OR marked SKIPPED).
- [ ] Each scored row has capability=`LLM-augmented`, mode=`direct` or `agent`.
- [ ] If INIT_TIMEOUT bug surfaced: documented in INIT_TIMEOUT_REPORT.md + Linear ticket filed against vendor (per HANDOFF STOP #2).
- [ ] Direct-mode DEEP_ANALYSIS.md explicitly answers Vitalik's "works without user's LLM key" question.
- [ ] Agent-mode DEEP_ANALYSIS.md compares its scores to direct-mode (FAIRNESS-04 apples-to-oranges caveat).
- [ ] No LLM API key strings (sk-*, etc.) appear in any file under `results/<DATE>/browser-use-*/`.
- [ ] `scoring/score.py` byte-for-byte unchanged.
- [ ] Previously-existing rows in `scores.json` byte-for-byte unchanged.

## Dependencies

All of Phase 1 + plans 02-01 through 02-04. Reason for last position before cloakbrowser: SKIPPED.md flow is well-validated, the harness has now been driven against 4 different MCPs, and the INIT_TIMEOUT risk is the highest-uncertainty per-MCP issue — better to know the harness works against playwright/chrome-devtools/lightpanda/firecrawl/obscura before discovering a hardlock in browser-use.

## Per-MCP Risks

From CONTEXT.md `## Decisions § Known Per-MCP Risks` + HANDOFF-GSD-AUTO STOP #2 + research/SUMMARY.md:

- **INIT timeout in v0.12.7** (2026-05-21 testbench reported this on the `--mcp` mode). HIGH risk. Task 1 pre-flight smoke test catches it BEFORE running 3 full passes. If present: file vendor bug, score row as SKIPPED (or 0/15 if some stages partially worked per CONTEXT.md), do NOT retry indefinitely.
- **Dual-mode harness routing:** `run_mcp_session.sh` doesn't natively support mode-suffix output dirs. The plan uses explicit `mv` after each pass to remap. Document in HARNESS_NOTES.md.
- **LLM cost in agent mode:** 3 passes × full S1-S8 walk × LLM-driven decisions could cost real $$ on the user's LLM key. NOT a blocker (CLAUDE.md `Vitalik is fine with this`), but worth flagging in DEEP_ANALYSIS.md so future reproducers know.
- **Apples-to-oranges:** agent mode IS comparing an LLM-augmented MCP to tool-only MCPs. This is the FAIRNESS-04 reason for capability tags. DEEP_ANALYSIS.md must call it out.

## Interesting Angle

From `.planning/research/SUMMARY.md § Empirical Claims to Falsify`:

> **browser-use** — "Direct mode" works in Claude Code without user's own LLM API key. Evidence: Launch with NO OPENAI_API_KEY/ANTHROPIC_API_KEY — does S1+S5 succeed? Also re-test the 2026-05 testbench's `initialize` timeout on v0.12.7.

Headline question for direct-mode DEEP_ANALYSIS.md is exactly: with both LLM env vars unset, does browser-use complete S1 (navigate + extract) and S5 (form-fill)? If yes — direct mode is real. If no — claim REFUTED.

## Stop Conditions

- **INIT_TIMEOUT smoke test fails repeatedly (3+ attempts):** STOP per HANDOFF STOP #2. Write SKIPPED.md, file vendor bug, do NOT retry indefinitely.
- **LLM cost > $5 during agent-mode passes:** STOP and surface — agent mode may be in an infinite tool-call loop.
- **Per-pass wall-clock > 60 minutes** (more likely for agent mode than direct).
- **Direct mode succeeds but agent mode hits INIT_TIMEOUT:** unlikely (same MCP binary) but document if observed.
- **scores.json doesn't end up with BOTH browser-use-direct AND browser-use-agent rows:** the FAIRNESS-05 contract is broken — STOP and fix before next plan.
