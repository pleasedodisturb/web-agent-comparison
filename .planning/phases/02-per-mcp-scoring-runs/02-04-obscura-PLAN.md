---
phase: 2
plan: 04
mcp: obscura
type: execute
wave: 4
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
  - 02-03   # SKIPPED.md pattern proven by firecrawl branch first
files_modified:
  - results/<DATE>/obscura/                           # full evidence dir OR SKIPPED.md (engine install gap)
  - results/<DATE>/obscura/PASS{1,2,3}.json            # only if install succeeds
  - results/<DATE>/obscura/DEEP_ANALYSIS.md
  - results/<DATE>/obscura/INSTALL_LOG.md              # records obscura-mcp install attempt outcome
  - results/<DATE>/scores.json                         # obscura row OR SKIPPED metadata
requirements:
  - FAIRNESS-04
  - FAIRNESS-05
success_criteria_advanced: [1, 4]
status: planned
autonomous: true
estimate_hours: 1

must_haves:
  truths:
    - "obscura either has a complete `results/<DATE>/obscura/` evidence directory (engine installed) OR a `SKIPPED.md` documenting INSTALL_FAILED (engine install gap on macOS arm64) — per CONTEXT.md `## Decisions § Known Per-MCP Risks` + HANDOFF-GSD-AUTO STOP #3."
    - "If scored: row carries capability tag `stealth-specialist`; `--stealth` flag is DISABLED on macOS per SAFETY-03 + CLAUDE.md `## Conventions` (Sec-CH-UA-Platform leak); the disabling is documented in DEEP_ANALYSIS.md."
    - "INSTALL_LOG.md documents the `obscura-mcp install` attempt: success → engine version + binary SHA256; failure → exact error output + diagnosis."
    - "If skipped: SKIPPED.md has reason=INSTALL_FAILED + the actual install-attempt error + diagnostic; aggregator treats as N/A composite."
  artifacts:
    - path: "results/<DATE>/obscura/INSTALL_LOG.md"
      provides: "Engine-install attempt outcome (success or failure); engine version separate from npm wrapper version (they differ per research/STACK.md `## 8`)"
    - path: "results/<DATE>/obscura/DEEP_ANALYSIS.md"
      provides: "Capability = stealth-specialist; --stealth-disabled-on-macOS rationale; CDP-direct architectural finding; memory-footprint observation (~30MB/tab claim)"
    - path: "results/<DATE>/scores.json"
      provides: "obscura row with capability tag + attribution OR SKIPPED metadata"
  key_links:
    - from: "obscura-mcp install"
      to: "rust+V8 engine binary download (separate from npm wrapper)"
      via: "wrapper's `install` subcommand"
      pattern: "obscura-mcp.*install"
    - from: "scripts/run_mcp_session.sh obscura"
      to: ".mcp.json obscura entry"
      via: "command spec without --stealth flag (SAFETY-03 enforcement on macOS)"
      pattern: "obscura.*(?!--stealth)"
---

## Goal

Drive the harness against **obscura** — the Rust+V8 CDP-direct stealth-specialist MCP — and produce either a scored row (capability=`stealth-specialist`, no `--stealth` flag on macOS) or a clean `SKIPPED.md` documenting the engine install gap (HANDOFF-GSD-AUTO STOP #3 — known macOS arm64 issue per 2026-05-21 testbench). This plan also handles the `npm wrapper version != engine version` quirk explicitly.

## Files Modified

- `results/<DATE>/obscura/` — full evidence dir OR SKIPPED.md
- `results/<DATE>/obscura/INSTALL_LOG.md` — engine install attempt outcome
- `results/<DATE>/obscura/PASS{1,2,3}.json` — only if install succeeds
- `results/<DATE>/obscura/DEEP_ANALYSIS.md`
- `results/<DATE>/scores.json` — obscura row OR SKIPPED metadata

## Tasks

### Task 1: Engine install + branch on success/failure

<files>results/&lt;DATE&gt;/obscura/INSTALL_LOG.md, results/&lt;DATE&gt;/obscura/SKIPPED.md (conditional), results/&lt;DATE&gt;/scores.json</files>

<action>
Pre-flight: confirm the obscura-mcp npm wrapper is installed (`scripts/check_prereqs.sh` covers this). Then run the engine install (a separate step from npm install per research/STACK.md `## 8`):

1. Capture install attempt:
   ```
   mkdir -p results/<DATE>/obscura/
   if obscura-mcp install >results/<DATE>/obscura/.install.stdout 2>results/<DATE>/obscura/.install.stderr; then
     INSTALL_RC=0
   else
     INSTALL_RC=$?
   fi
   ```

2. Write `results/<DATE>/obscura/INSTALL_LOG.md`:
   ```markdown
   # obscura engine install attempt

   - **date:** <ISO UTC timestamp>
   - **command:** `obscura-mcp install`
   - **exit_code:** <INSTALL_RC>
   - **wrapper_version:** <output of `npm view obscura-mcp version`>  (expected: 0.1.4-3 per research/STACK.md)
   - **engine_version:** <parsed from stdout if present; "unknown" if install failed>
   - **engine_binary_sha256:** <sha256 of installed engine binary if found; "absent" if not>
   - **stdout:** <last 50 lines from .install.stdout>
   - **stderr:** <last 50 lines from .install.stderr>
   ```

3. **SKIPPED branch (INSTALL_RC != 0):** Write `results/<DATE>/obscura/SKIPPED.md`:
   ```markdown
   # obscura — SKIPPED (engine install failed)

   - **reason:** INSTALL_FAILED
   - **attempted_command:** `obscura-mcp install`
   - **error_excerpt:** <first 10 lines of .install.stderr>
   - **linear_ticket:** <obscura sub-ticket from G-715..G-720>
   - **partial_evidence_path:** results/<DATE>/obscura/INSTALL_LOG.md
   - **diagnosis:** Known macOS arm64 install gap per HANDOFF-GSD-AUTO STOP #3 +
     2026-05-21 testbench. Per CONTEXT.md + PROJECT.md, 6/7 partial scoring is
     acceptable. Phase 4 report MUST surface this in REPORT-09 disclosure.
   ```
   Update `results/<DATE>/scores.json`:
   ```json
   "obscura": {
     "status": "SKIPPED",
     "reason": "INSTALL_FAILED",
     "capability": "stealth-specialist",
     "mode": "skipped",
     "scores": {},
     "stages": {"S1":"UNTESTED","S2":"UNTESTED","S3":"UNTESTED","S4":"UNTESTED","S5":"UNTESTED","S6":"UNTESTED","S7":"UNTESTED","S8":"UNTESTED"}
   }
   ```
   Skip Task 2. Done.

4. **NORMAL branch (INSTALL_RC == 0):** Verify `.mcp.json` obscura entry does NOT contain `--stealth` (SAFETY-03 + CLAUDE.md macOS rule: Sec-CH-UA-Platform leak). If the entry contains `--stealth`, STOP and surface — the .mcp.json must be updated to remove it before scoring continues. Then run the harness 3 times:
   - `bash scripts/run_mcp_session.sh obscura` × 3 with ≥30 min gaps
   - Move each output into `PASS<N>/`, run `scripts/aggregate_scores.py results/<DATE>/obscura/PASS<N>/` → `PASS<N>.json`

5. Capture the memory-footprint differentiator (research/SUMMARY.md angle) opportunistically: BEFORE Pass 1 starts and DURING Pass 1's S2 (Ashby SPA render), take a single `ps -o rss= -p <obscura-pid>` snapshot and append to `results/<DATE>/obscura/MEMORY_SNAPSHOT.txt`. This isn't a scored Phase-2 dimension (Phase 3 / v2 territory) but it's the obscura "interesting angle" — capture cheaply now.

Wall-clock gate: same 60-min STOP rule as plan 02-01.
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
test -f "results/$DATE/obscura/INSTALL_LOG.md" &&
if [[ -f "results/$DATE/obscura/SKIPPED.md" ]]; then
  grep -q "INSTALL_FAILED" "results/$DATE/obscura/SKIPPED.md" &&
  .venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
row = data['obscura']
assert row.get('status') == 'SKIPPED'
assert row.get('capability') == 'stealth-specialist'
print('OK (skipped branch)')
"
else
  test -d "results/$DATE/obscura/PASS1" &&
  test -d "results/$DATE/obscura/PASS2" &&
  test -d "results/$DATE/obscura/PASS3" &&
  # Critical: --stealth flag MUST NOT appear in .mcp.json obscura command
  ! jq -r '.mcpServers.obscura.args[]?' .mcp.json 2>/dev/null | grep -q -- '--stealth' &&
  echo "OK (scored branch)"
fi
</automated>
</verify>

<done>
EITHER SKIPPED.md exists with reason=INSTALL_FAILED + scores.json row marked SKIPPED. OR 3 passes captured AND `.mcp.json` obscura command does NOT contain `--stealth` on macOS (SAFETY-03 enforcement). INSTALL_LOG.md exists in both branches.
</done>

### Task 2: Median row + capability tag + stealth-specialist finding (scored branch only)

<files>results/&lt;DATE&gt;/scores.json, results/&lt;DATE&gt;/obscura/DEEP_ANALYSIS.md</files>

<action>
SKIP THIS TASK if Task 1 took the SKIPPED branch.

Compute median row per plan 02-01 Task 2. Insert/update obscura row; preserve earlier rows.

Row-level fields:
- `capability`: `"stealth-specialist"`
- `mode`: `"no-stealth-flag"` (per SAFETY-03 macOS rule)

Write `results/<DATE>/obscura/DEEP_ANALYSIS.md`:
- **Capability tag:** `stealth-specialist`
- **Median composite** + standard table
- **The `--stealth` SUPPRESSION on macOS:** explicit paragraph documenting why obscura was run without `--stealth`:
  - Per CLAUDE.md `## Conventions` + `~/.claude/docs/browser-tools.md`: `--stealth` leaks Sec-CH-UA-Platform-* header on macOS regardless of JS UA shim
  - Per SAFETY-03: any JS-UA-vs-Sec-CH-UA-Platform mismatch tags the MCP `stealth: leaks` — a methodology-honesty choice
  - Acceptable alternatives (deferred): run obscura in a Linux VM (out of scope this wave per CONTEXT.md `## Decisions § Claude's Discretion`)
  - Phase 4 report MUST cite this in obscura's "Deep Analysis" — `recommendations.md` SECONDARY-or-better tier depends on whether obscura's headers are honest on macOS
- **The falsifiable empirical finding — CDP-direct architecture:**
  - Claim (research/SUMMARY.md): "CDP-direct (not Playwright-on-CDP) gives lower overhead + ~30MB RAM vs Playwright ~300MB while keeping full JS rendering"
  - Evidence:
    - Memory snapshot from `MEMORY_SNAPSHOT.txt` (Task 1 step 5) — actual obscura process RSS during S2
    - Cross-reference Playwright row's stage_s2 wall-clock (parsed from `results/<DATE>/playwright/raw_stream.jsonl`)
    - S2 (Ashby React SPA) verdict: PASS proves "full JS rendering"; FAIL means CDP-direct didn't render React (claim REFUTED for this site)
  - Document outcome with concrete numbers
- **Failure-attribution table** for any cell < 5
- **Linear sub-ticket reference**

Run `scripts/score_with_na.py results/<DATE>/scores.json` and confirm obscura composite is a real number (not N/A — obscura has an interactive surface, unlike lightpanda/firecrawl).
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
if [[ ! -f "results/$DATE/obscura/SKIPPED.md" ]]; then
  .venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
row = data['obscura']
assert row.get('capability') == 'stealth-specialist'
assert row.get('mode') == 'no-stealth-flag'
# obscura HAS an interactive surface (unlike lightpanda/firecrawl), so interaction_depth should be numeric
id_score = row['scores'].get('interaction_depth')
assert isinstance(id_score, (int, float)), f'interaction_depth should be numeric for obscura, got {id_score}'
print('OK')
" &&
  test -f "results/$DATE/obscura/DEEP_ANALYSIS.md" &&
  grep -q 'stealth-specialist' "results/$DATE/obscura/DEEP_ANALYSIS.md" &&
  grep -q -i '\-\-stealth\|Sec-CH-UA' "results/$DATE/obscura/DEEP_ANALYSIS.md" &&
  grep -q -i 'CDP\|memory\|RAM' "results/$DATE/obscura/DEEP_ANALYSIS.md"
else
  echo "OK (skipped branch; task 2 N/A)"
fi
</automated>
</verify>

<done>
Scored branch: scores.json obscura row has capability="stealth-specialist", mode="no-stealth-flag", interaction_depth is numeric (not N/A); DEEP_ANALYSIS.md explicitly documents the --stealth suppression rationale and the CDP-direct memory-footprint finding with numbers.
</done>

## Acceptance

- [ ] `INSTALL_LOG.md` exists with engine install attempt outcome (always, both branches).
- [ ] EITHER `SKIPPED.md` with reason=INSTALL_FAILED + scores.json row marked SKIPPED.
- [ ] OR 3 passes + scores.json row with capability=stealth-specialist + mode=no-stealth-flag + DEEP_ANALYSIS.md documents `--stealth` suppression + CDP-direct empirical claim.
- [ ] `.mcp.json` obscura command does NOT contain `--stealth` on macOS (verified in scored branch).
- [ ] Every sub-rubric cell < 5 has attribution tag.
- [ ] `scoring/score.py` byte-for-byte unchanged.
- [ ] Existing playwright + chrome-devtools + lightpanda + firecrawl rows in `scores.json` byte-for-byte unchanged.

## Dependencies

All of Phase 1, plus 02-01 (chrome-devtools), 02-02 (lightpanda N/A semantics), 02-03 (firecrawl proves SKIPPED.md pattern works end-to-end before obscura uses the same flow).

## Per-MCP Risks

From CONTEXT.md `## Decisions § Known Per-MCP Risks` + research/STACK.md `## 8` + HANDOFF-GSD-AUTO STOP #3:

- **Engine install may fail on macOS arm64** (HANDOFF STOP #3 — known gap). Task 1 explicitly handles this via SKIPPED branch.
- **npm wrapper version ≠ engine version** per research/STACK.md `## 8`: "The wrapper's npm version (0.1.4-3) and the engine binary version are NOT the same number — log both at install time." INSTALL_LOG.md does both.
- **`--stealth` MUST be disabled on macOS** per SAFETY-03 + CLAUDE.md `## Conventions` — Sec-CH-UA-Platform leak. Pre-flight check verifies `.mcp.json` excludes the flag.
- **Closed-source engine binary** (per research/STACK.md notes): treat install as an opaque trust event. Document SHA256 for reproducibility.
- **XHR-heavy stage may silently fail** per research/SUMMARY.md "known in-page-fetch silent-fail" — if S3 (JSON-LD / structured data extraction) produces empty results, attribute as `tool-bug` and document specifically.

## Interesting Angle

From `.planning/research/SUMMARY.md § Empirical Claims to Falsify`:

> **obscura** — CDP-direct (not Playwright-on-CDP) gives lower overhead + ~30MB RAM vs Playwright ~300MB while keeping full JS rendering. Evidence: `ps` memory snapshot during S1; bot-detection score relative to Playwright/CloakBrowser; XHR-heavy stage to probe known in-page-fetch silent-fail; **DO NOT enable `--stealth` on macOS** (Sec-CH-UA-Platform leak).

Phase-2 captures: memory snapshot during S2 (cheaply, opportunistically); S2 PASS/FAIL evidences full-JS-rendering claim. Bot-detection comparison is deferred to G-710.

## Stop Conditions

- **`.mcp.json` obscura command contains `--stealth` on macOS:** STOP — SAFETY-03 violation. Surface to user to remove the flag before continuing.
- **Per-pass wall-clock > 60 minutes**.
- **Engine install fails repeatedly** with the SAME error across 2+ install attempts: SKIPPED branch is the correct outcome — do NOT escalate.
- **All 3 passes produce drastically different S1-S8 verdicts** (likely XHR-silent-fail nondeterminism): score median anyway but flag in DEEP_ANALYSIS.md as elevated variance.
