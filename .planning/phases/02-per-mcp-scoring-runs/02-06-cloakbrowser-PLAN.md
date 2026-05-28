---
phase: 2
plan: 06
mcp: cloakbrowser
type: execute
wave: 6
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
  - 02-05
files_modified:
  - results/<DATE>/cloakbrowser/                        # full evidence dir OR SKIPPED.md
  - results/<DATE>/cloakbrowser/PASS{1,2,3}.json
  - results/<DATE>/cloakbrowser/DEEP_ANALYSIS.md
  - results/<DATE>/cloakbrowser/SANDBOX_PROOF.md        # MANDATORY per CONTEXT.md `## Decisions § cloakbrowser Sandbox-Only Enforcement`
  - results/<DATE>/scores.json                          # adds cloakbrowser row OR SKIPPED
requirements:
  - FAIRNESS-04
  - FAIRNESS-05
success_criteria_advanced: [1, 4, 5]
status: planned
autonomous: true
estimate_hours: 1

must_haves:
  truths:
    - "cloakbrowser has a complete `results/<DATE>/cloakbrowser/` evidence directory OR a SKIPPED.md; if scored, capability tag = `stealth-specialist`."
    - "MANDATORY: `SANDBOX_PROOF.md` exists and proves zero requests to any hostname other than 127.0.0.1 (Phase 2 SC #5 — the closed-binary sandbox-only contract per CLAUDE.md `## Constraints` + SAFETY-04)."
    - "The harness refused (via `bench/cloakbrowser_guard.py` `assert_local_only`) to spawn cloakbrowser against any non-loopback target. Verified pre-flight; documented in SANDBOX_PROOF.md."
    - "Every cloakbrowser mention in DEEP_ANALYSIS.md AND the eventual Phase 4 report carries an explicit `**Sandbox only — do not point at authenticated sessions**` callout per REPORT-08."
    - "If the closed-source binary fails to install or run, SKIPPED.md documents the failure WITHOUT attempting workarounds (no `--no-sandbox`, no `--allow-net=*`, no whitelist relaxation)."
  artifacts:
    - path: "results/<DATE>/cloakbrowser/SANDBOX_PROOF.md"
      provides: "Per-run sandbox enforcement proof — grep results over transcript.md + raw_stream.jsonl for any non-127.0.0.1 hostname; expected to be empty"
    - path: "results/<DATE>/cloakbrowser/DEEP_ANALYSIS.md"
      provides: "Capability = stealth-specialist; sandbox-only callout; source-patched-Chromium empirical claim re Cloudflare/reCAPTCHA/FingerprintJS — DEFERRED to G-710 per CONTEXT.md, document the deferral here"
    - path: "results/<DATE>/scores.json"
      provides: "cloakbrowser row with capability tag + attribution OR SKIPPED"
  key_links:
    - from: "scripts/run_mcp_session.sh cloakbrowser (line 127)"
      to: "bench/cloakbrowser_guard.assert_local_only"
      via: "pre-flight guard; raises HostnameNotAllowedError for any non-loopback"
      pattern: "cloakbrowser_guard.*assert_local_only"
    - from: "results/<DATE>/cloakbrowser/SANDBOX_PROOF.md"
      to: "results/<DATE>/cloakbrowser/transcript.md + raw_stream.jsonl"
      via: "post-run grep verification — must show zero non-127.0.0.1 hostnames"
      pattern: "grep.*127\\.0\\.0\\.1"
---

## Goal

Drive the harness against **cloakbrowser** — the closed-source stealth-Chromium MCP — **STRICTLY** against the loopback snapshot fixtures, producing a scored row capability-tagged `stealth-specialist`. The non-negotiable deliverable is `SANDBOX_PROOF.md` validating Phase 2 SC #5 ("zero requests to any hostname other than 127.0.0.1"). This is the LAST per-MCP plan because the closed-binary risk is highest; running it after the harness has been validated against 6 prior MCPs gives the cleanest signal of cloakbrowser-specific issues.

## Files Modified

- `results/<DATE>/cloakbrowser/` — full evidence dir OR SKIPPED.md
- `results/<DATE>/cloakbrowser/PASS{1,2,3}.json` — per-pass aggregations
- `results/<DATE>/cloakbrowser/SANDBOX_PROOF.md` — MANDATORY; SC #5 evidence
- `results/<DATE>/cloakbrowser/DEEP_ANALYSIS.md`
- `results/<DATE>/scores.json` — cloakbrowser row OR SKIPPED metadata

## Tasks

### Task 1: Sandbox-guarded harness execution + sandbox proof

<files>results/&lt;DATE&gt;/cloakbrowser/PASS{1,2,3}/, results/&lt;DATE&gt;/cloakbrowser/SANDBOX_PROOF.md, results/&lt;DATE&gt;/cloakbrowser/SKIPPED.md (conditional)</files>

<action>
Pre-flight: confirm cloakbrowser binary is installed (`scripts/check_prereqs.sh`). Confirm `SNAPSHOT_BASE_URL` is `http://127.0.0.1:8765` (loopback). Confirm `bench/cloakbrowser_guard.py` is in place from plan 01-02; the existing `run_mcp_session.sh` line 127-130 calls `assert_local_only(SNAPSHOT_BASE_URL)` ONLY for cloakbrowser — verify by reading.

1. Pre-flight HARD ASSERTION: run `bench/cloakbrowser_guard.assert_local_only(SNAPSHOT_BASE_URL)` directly. If it raises `HostnameNotAllowedError`, STOP — the configuration is unsafe. Do NOT modify the guard to relax (this is the SAFETY-04 contract).

2. Run the harness 3 times against cloakbrowser. The existing `run_mcp_session.sh` line 127-130 already invokes the guard; if it ever raises, the harness exits before Claude spawns:
   ```
   for n in 1 2 3; do
     bash scripts/run_mcp_session.sh cloakbrowser
     mv "results/<DATE>/cloakbrowser" "results/<DATE>/cloakbrowser-PASS${n}-tmp"
     mkdir -p "results/<DATE>/cloakbrowser/PASS${n}"
     mv "results/<DATE>/cloakbrowser-PASS${n}-tmp"/* "results/<DATE>/cloakbrowser/PASS${n}/"
     rmdir "results/<DATE>/cloakbrowser-PASS${n}-tmp"
     scripts/aggregate_scores.py "results/<DATE>/cloakbrowser/PASS${n}/"
     mv "results/<DATE>/cloakbrowser/PASS${n}/scores.json" "results/<DATE>/cloakbrowser/PASS${n}.json"
   done
   ```

3. **SKIPPED branch:** if the binary fails to launch (`INSTALL_FAILED`, `GATEKEEPER_BLOCKED`, etc.), write `results/<DATE>/cloakbrowser/SKIPPED.md` with the appropriate reason, mark scores.json row SKIPPED, skip Task 2. Do NOT attempt workarounds (no `xattr -d com.apple.quarantine`, no permission relaxation — closed-source binary trust is opt-in per machine, not automatable). Per CLAUDE.md `## Constraints`: cloakbrowser availability is "the unknown — verify before promising parity"; SKIPPED is a legitimate outcome.

4. **Sandbox-proof generation (MANDATORY for scored branch):** write `results/<DATE>/cloakbrowser/SANDBOX_PROOF.md`:
   ```markdown
   # cloakbrowser sandbox enforcement proof

   **Per Phase 2 SC #5:** "The cloakbrowser evidence directory contains zero requests
   to any hostname other than 127.0.0.1; the harness refuses to spawn it against any
   other target."

   ## Pre-flight guard

   - **`bench/cloakbrowser_guard.assert_local_only("${SNAPSHOT_BASE_URL}")`:** PASSED (raised no exception)
   - SNAPSHOT_BASE_URL: http://127.0.0.1:8765
   - All 3 passes spawned under this same guard

   ## Post-run hostname audit

   ```
   $ grep -rohE "https?://[^/[:space:]]+" results/<DATE>/cloakbrowser/PASS{1,2,3}/transcript.md results/<DATE>/cloakbrowser/PASS{1,2,3}/raw_stream.jsonl | sort -u
   ```

   Result (must show ONLY 127.0.0.1 hostnames, plus loopback variants):
   ```
   http://127.0.0.1:8765
   http://localhost:8765   (if any — note that bench/cloakbrowser_guard.assert_local_only accepts only 127.0.0.1, so localhost should NOT appear)
   ```

   ## Outcome

   - **All 3 passes:** zero non-loopback hostnames in transcript.md or raw_stream.jsonl
   - **SAFETY-04 contract upheld:** the closed-source cloakbrowser binary was only ever pointed at the loopback snapshot server
   - **REPORT-08 obligation:** every cloakbrowser mention in the Phase 4 report MUST carry
     `**Sandbox only — do not point at authenticated sessions**`
   ```

   If the grep DOES find a non-loopback hostname, STOP IMMEDIATELY:
   - Do NOT continue to Task 2
   - Write `results/<DATE>/cloakbrowser/SANDBOX_VIOLATION.md` with the offending hostname(s) + which pass + which file
   - Surface to user — this is the SAFETY-04 contract being broken, sub-ticket should be paused
   - The run is INVALID; scores.json cloakbrowser row must NOT be inserted

Wall-clock gate: 60 minutes per pass.
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
if [[ -f "results/$DATE/cloakbrowser/SKIPPED.md" ]]; then
  .venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
assert 'cloakbrowser' in data
assert data['cloakbrowser'].get('status') == 'SKIPPED'
print('OK (skipped)')
"
else
  test -d "results/$DATE/cloakbrowser/PASS1" &&
  test -d "results/$DATE/cloakbrowser/PASS2" &&
  test -d "results/$DATE/cloakbrowser/PASS3" &&
  test -f "results/$DATE/cloakbrowser/SANDBOX_PROOF.md" &&
  # SC #5: zero non-loopback hostnames in evidence
  test -z "$(grep -rohE 'https?://[^/[:space:]]+' results/$DATE/cloakbrowser/PASS*/transcript.md results/$DATE/cloakbrowser/PASS*/raw_stream.jsonl 2>/dev/null | grep -v -E '127\\.0\\.0\\.1|localhost' | sort -u)" &&
  ! test -f "results/$DATE/cloakbrowser/SANDBOX_VIOLATION.md"
fi
</automated>
</verify>

<done>
EITHER SKIPPED.md exists (binary failed to launch) + scores.json marked SKIPPED. OR 3 passes captured + SANDBOX_PROOF.md exists proving zero non-loopback hostnames + no SANDBOX_VIOLATION.md sentinel. SAFETY-04 contract is intact.
</done>

### Task 2: Median row + capability tag + sandbox-only callout (scored branch only)

<files>results/&lt;DATE&gt;/scores.json, results/&lt;DATE&gt;/cloakbrowser/DEEP_ANALYSIS.md</files>

<action>
SKIP THIS TASK if Task 1 took the SKIPPED branch OR if SANDBOX_VIOLATION.md exists.

Compute median row per plan 02-01 Task 2. Insert/update cloakbrowser row; preserve all earlier rows.

Row-level fields:
- `capability`: `"stealth-specialist"`
- `mode`: `"sandbox-loopback"`
- `sandbox_only`: true (REPORT-08 carry-over signal for Phase 4)

Write `results/<DATE>/cloakbrowser/DEEP_ANALYSIS.md`:
- **Sandbox-only callout AT THE TOP:** `**Sandbox only — do not point at authenticated sessions**` (REPORT-08 contract)
- **Capability tag:** `stealth-specialist`
- **Median composite** + per-stage verdicts
- **The falsifiable empirical finding — Stealth claims:**
  - Claim (research/SUMMARY.md): "Source-patched Chromium passes Cloudflare Turnstile, reCAPTCHA v3 (0.9 score), FingerprintJS, BrowserScan — 30/30 tests, no captcha solving needed"
  - **STATUS: DEFERRED to G-710** per CONTEXT.md `## Deferred Ideas` ("TLS fingerprint capture per MCP → G-710" + "Bot-detection adversary testing per MCP → G-710"). This plan does NOT test the stealth claim — the snapshot fixtures don't fingerprint-check, so a cloakbrowser PASS on Greenhouse/Ashby loopback proves nothing about Cloudflare/reCAPTCHA. Document this explicitly so Phase 4 doesn't accidentally claim stealth validation.
  - What IS captured: the harness-driven S1-S8 walk shows cloakbrowser CAN drive a browser session (forms, clicks, screenshots). That's the only Phase-2-scoped claim.
- **Sandbox-only deferred-tier note:** per recommendations.md (Phase 4): cloakbrowser will be tiered `SANDBOX-ONLY` regardless of S1-S8 score because the closed-binary trust model is the binding constraint, not the stealth claim. Pre-document.
- **Failure-attribution table.**
- **Linear sub-ticket reference.**

Final sanity: every reference to cloakbrowser in DEEP_ANALYSIS.md must be followed by the `**Sandbox only — do not point at authenticated sessions**` callout (or the document must open with it and refer back). REPORT-08 is non-negotiable.
</action>

<verify>
<automated>
DATE=$(date -u +%Y-%m-%d) &&
if [[ ! -f "results/$DATE/cloakbrowser/SKIPPED.md" ]] && [[ ! -f "results/$DATE/cloakbrowser/SANDBOX_VIOLATION.md" ]]; then
  .venv/bin/python -c "
import json
data = json.load(open('results/$DATE/scores.json'))
row = data['cloakbrowser']
assert row.get('capability') == 'stealth-specialist'
assert row.get('sandbox_only') == True
print('OK')
" &&
  test -f "results/$DATE/cloakbrowser/DEEP_ANALYSIS.md" &&
  grep -q 'Sandbox only' "results/$DATE/cloakbrowser/DEEP_ANALYSIS.md" &&
  grep -q 'do not point at authenticated' "results/$DATE/cloakbrowser/DEEP_ANALYSIS.md" &&
  grep -q -i 'G-710\|deferred' "results/$DATE/cloakbrowser/DEEP_ANALYSIS.md"
else
  echo "OK (skipped or violation — task 2 N/A)"
fi
</automated>
</verify>

<done>
Scored branch: scores.json cloakbrowser row has capability="stealth-specialist", sandbox_only=true; DEEP_ANALYSIS.md leads with sandbox-only callout, documents G-710 deferral of the stealth claim, and pre-tiers as SANDBOX-ONLY for recommendations.md.
</done>

## Acceptance

- [ ] EITHER `SKIPPED.md` (binary failed to launch — common per CLAUDE.md `## Constraints`) + scores.json row marked SKIPPED.
- [ ] OR full evidence: 3 passes + `SANDBOX_PROOF.md` (MANDATORY) + scores.json row with capability=stealth-specialist + sandbox_only=true + DEEP_ANALYSIS.md with sandbox-only callout.
- [ ] NO `SANDBOX_VIOLATION.md` sentinel exists.
- [ ] Phase 2 SC #5 is met: zero non-127.0.0.1 hostnames in cloakbrowser evidence files.
- [ ] Every cloakbrowser mention in DEEP_ANALYSIS.md carries `**Sandbox only — do not point at authenticated sessions**` (REPORT-08).
- [ ] Every sub-rubric cell < 5 has attribution.
- [ ] `scoring/score.py` byte-for-byte unchanged.
- [ ] All previously-existing rows in `scores.json` byte-for-byte unchanged (including browser-use-direct + browser-use-agent).

## Dependencies

All of Phase 1 + plans 02-01 through 02-05. Last per-MCP plan: closed-binary risk is highest, so it gets the most-validated harness state.

## Per-MCP Risks

From CONTEXT.md + research/STACK.md `## 8` + CLAUDE.md `## Constraints` + SAFETY-04 + REPORT-08:

- **Sandbox-only is a HARD CONTRACT.** Per CLAUDE.md `## Constraints`: "Closed-source binary touching cookies — never point at authenticated host pages. Tested only against the public Greenhouse + Ashby fixtures." The harness guard at `bench/cloakbrowser_guard.py` enforces this; if it ever fails, the run is INVALID.
- **Binary availability cross-platform:** "CloakBrowser availability is the unknown — verify before promising parity" (CLAUDE.md). macOS install may fail (Gatekeeper, missing entitlements, closed-source quirks). SKIPPED is a legitimate outcome.
- **Stealth claim is DEFERRED to G-710:** the snapshot fixtures don't fingerprint-check. A Phase-2 PASS on S1-S8 does NOT validate the Cloudflare/reCAPTCHA claims. DEEP_ANALYSIS.md MUST document this so Phase 4 doesn't overclaim.
- **No fallback to live URLs:** even to "validate stealth," do NOT spawn cloakbrowser against live Greenhouse/Ashby. The cloud-vs-loopback architectural-mismatch principle (plan 02-03 firecrawl risk) does NOT apply here — cloakbrowser is local-only by sandbox contract.

## Interesting Angle

From `.planning/research/SUMMARY.md § Empirical Claims to Falsify`:

> **cloakbrowser** — Source-patched Chromium passes Cloudflare Turnstile, reCAPTCHA v3 (0.9 score), FingerprintJS, BrowserScan — 30/30 tests, no captcha solving needed. Evidence: Full bot-detection matrix vs Playwright + Obscura on same detectors; JA4 cross-check vs real Chrome 128 baseline; sandbox-only enforcement in every report mention.

**Scope cut for this wave (per CONTEXT.md `## Deferred Ideas`):** the bot-detection adversary set + TLS fingerprint capture moved to G-710. This plan captures ONLY the S1-S8 walk against loopback fixtures. DEEP_ANALYSIS.md MUST explicitly note the deferral.

## Stop Conditions

- **`bench/cloakbrowser_guard.assert_local_only` raises HostnameNotAllowedError** during pre-flight: STOP, surface — configuration is unsafe.
- **Any non-loopback hostname found in evidence post-run** (`SANDBOX_VIOLATION.md` triggered): STOP IMMEDIATELY, do NOT score, surface to user. The closed-binary sandbox contract is broken — this is a P0 safety event.
- **Cloakbrowser binary fails to launch**: SKIPPED branch is correct outcome — do NOT relax sandbox or trust settings as a workaround.
- **Per-pass wall-clock > 60 minutes**: standard rule.
- **Genuine "world has changed" surprise** (per HANDOFF STOP #4): cloakbrowser binary pulled, repo gone, signature invalid. Surface to user.
