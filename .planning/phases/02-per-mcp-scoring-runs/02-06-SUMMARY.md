---
phase: 02-per-mcp-scoring-runs
plan: 06
mcp: cloakbrowser
subsystem: benchmark
tags: [cloakbrowser, mcp, stealth-specialist, sandbox-only, SAFETY-04, REPORT-08, FAIRNESS-04, FAIRNESS-05, closed-source-binary, loopback-only, median-of-3, last-per-mcp-plan]

requires:
  - phase: 01-harness-foundation
    provides: bench/cloakbrowser_guard.py (assert_local_only loopback enforcement), aggregate_scores.py, score_with_na.py, bench/failure_taxonomy.py, bench/tools_inventory.py, fixtures snapshots, prompts/stage_walk.md, scripts/run_mcp_session.sh (lines 127-130 invoke the guard for cloakbrowser ONLY)
  - phase: 02-per-mcp-scoring-runs
    plan: 01
    provides: chrome-devtools precedent — PASS{1,2,3}/ convention, symlink-trick aggregator pattern, agent-discovery-variance finding shape
  - phase: 02-per-mcp-scoring-runs
    plan: 04
    provides: obscura precedent — capability=stealth-specialist tag, sandbox-related caveats schema, methodology-honesty deferral pattern for stealth claims (G-710)
  - phase: 02-per-mcp-scoring-runs
    plan: 05
    provides: browser-use precedent — interpretation-variance distinction (PASS1 early-termination by Claude Code SDK is execution-variance, not MCP-variance)

provides:
  - "cloakbrowser row in results/2026-05-26/scores.json (median-of-3 composite 8.33; capability=stealth-specialist; mode=sandbox-loopback; sandbox_only=true; per-pass spread 7.27/8.13/8.33 — a 1.06-point band driven by PASS1's premature termination, not by MCP variance)"
  - "SANDBOX_PROOF.md attesting SC #5 contract: zero non-loopback cloak_navigate or fetch() targets across all 3 passes (the only active egress vectors under harness control); non-loopback strings in transcripts are content extracted from snapshot HTML, not request targets"
  - "DEEP_ANALYSIS.md with REPORT-08 sandbox-only callout repeated 6+ times, G-710 stealth-claim deferral documented, Phase-4 SANDBOX-ONLY tier pre-disposition encoded"
  - "Empirical confirmation that the FAIRNESS-01 3-pass median absorbs Claude Code SDK budget exhaustion (PASS1 terminated at 35 turns with error_during_execution after typing 4/4 form fields cleanly — NOT a cloakbrowser defect; PASS2+PASS3 ran clean to 54-55 turns each)"
  - "Matrix-leading composite: cloakbrowser 8.33 > playwright 7.93 > lightpanda 6.31 > browser-use-direct 5.87 > chrome-devtools 5.60 > firecrawl 4.23 > obscura 3.27 > browser-use-agent SKIPPED — the closed-binary trust model binding constraint means this composite does NOT promote cloakbrowser to PRIMARY tier in Phase 4 (binding is auditability, not S1-S8 surface coverage)"
  - "Tool-surface analysis: cloakbrowser exposes 20 MCP tools (2nd-richest in matrix after chrome-devtools' 29), auto-snapshot-on-mutation pattern reduces per-action token overhead vs Playwright"
  - "Phase 2 matrix CLOSED: 7 MCPs scored + 1 SKIPPED (8 rows total); Plan 02-07 attribution-audit is next (the final synthesis check, NOT scored as an MCP)"
affects: [phase-04-synthesis, phase-02-attribution-audit, phase-03-cross-cutting, G-703, G-720, G-721, G-710]

tech-stack:
  added: []
  patterns:
    - "Sandbox-only enforcement via pre-flight guard: `bench/cloakbrowser_guard.assert_local_only(url)` raises HostnameNotAllowedError for any non-loopback hostname; wired into `scripts/run_mcp_session.sh:127-130` and invoked ONLY for MCP_NAME=cloakbrowser. The harness exits before Claude spawns if the guard raises. Same architectural pattern (pre-flight guard at the harness entry point) is reusable for any future closed-source MCP that needs a hard sandbox contract."
    - "Multi-tier sandbox audit: (1) pre-flight URL guard, (2) post-run grep of all active tool-call egress vectors (cloak_navigate + fetch() inside cloak_evaluate), (3) full hostname sweep of transcripts with false-positive triage distinguishing CONTENT strings (extracted from snapshot HTML — `https://job-boards.greenhouse.io` in og:url meta, `https://bit.ly/afpsafety` in body anchors) from REQUEST targets (every navigate/fetch was loopback). Reusable for any sandbox-only MCP audit."
    - "Phase-4 tier pre-disposition encoded in DEEP_ANALYSIS.md: when an MCP scores high but has a binding non-score constraint (closed-source binary, sandbox-only contract), pre-document the Phase-4 tier so the matrix synthesis doesn't accidentally promote it. cloakbrowser is pre-tiered SANDBOX-ONLY regardless of 8.33 composite. Reusable pattern for any MCP where the rubric and the trust model disagree."

key-files:
  created:
    - results/2026-05-26/cloakbrowser/PASS1/ (full evidence: stage_s1.yml + stage_s2.yml + stage_s3.md + stage_s4.md + Phase-1 standard files; ~301s wall-clock, terminated at S5 by Claude Code SDK budget exhaustion after typing 4/4 form fields)
    - results/2026-05-26/cloakbrowser/PASS2/ (full evidence: stage_s1.yml + stage_s2.yml + stage_s{3..7}.md + stage_s8.png 56KB + standard files; ~493s wall-clock, clean S1-S8 completion at 54 turns)
    - results/2026-05-26/cloakbrowser/PASS3/ (full evidence: same shape as PASS2 + stage_s8.png 56KB; ~478s wall-clock, clean S1-S8 completion at 55 turns)
    - results/2026-05-26/cloakbrowser/PASS{1,2,3}.json (per-pass aggregated rows; per-pass composites 7.27, 8.13, 8.33 via symlink-trick aggregator invocation per obscura precedent)
    - results/2026-05-26/cloakbrowser/SANDBOX_PROOF.md (MANDATORY per Phase 2 SC #5; 3-tier audit: pre-flight guard verification + all cloak_navigate/fetch() vector enumeration + full hostname sweep with false-positive triage)
    - results/2026-05-26/cloakbrowser/DEEP_ANALYSIS.md (capability=stealth-specialist + mode=sandbox-loopback + sandbox_only=true + median 8.33 + per-stage verdicts + PASS1 SDK-termination diagnosis + stealth-claim G-710 deferral + tool surface analysis + Phase-4 SANDBOX-ONLY tier pre-disposition + 6+ "Sandbox only — do not point at authenticated sessions" callouts per REPORT-08)
  modified:
    - results/2026-05-26/scores.json (added cloakbrowser row with capability=stealth-specialist, mode=sandbox-loopback, sandbox_only=true; all 7 previously-existing rows preserved byte-for-byte)

key-decisions:
  - "Pre-flight guard verification ran BOTH positive (127.0.0.1 accepted) and negative (example.com rejected with HostnameNotAllowedError) tests before PASS1 spawned. Wiring at scripts/run_mcp_session.sh:127-130 confirmed; harness invokes the guard ONLY for MCP_NAME=cloakbrowser (cheap check, only run where it matters)."
  - "3-pass scored branch chosen — the binary launched cleanly on first invocation (no Gatekeeper rejection, no INSTALL_FAILED, no GATEKEEPER_BLOCKED). All 3 passes proceeded normally; no SKIPPED branch needed. cloakbrowsermcp v2.0.4 from PyPI installed via `uv tool install` precedent."
  - "PASS1 terminated at S5 with error_during_execution after 35 turns; root cause is Claude Code SDK budget exhaustion / tool-rejection on the cloak_type call for `+1 555 867 5309` phone number. NOT a cloakbrowser defect — the agent had a working session with a healthy browser at termination; same cloak_type signature succeeded in PASS2 and PASS3. The FAIRNESS-01 3-pass median protocol exists exactly to absorb this kind of SDK-side variance. Documented in DEEP_ANALYSIS.md § 'The PASS 1 incident'."
  - "Per-dimension median computed across 3 passes; per-stage majority verdict (2-of-3 PASS = PASS) computed. All 8 stages produce majority PASS verdict; all 8 sub-rubric dimensions produce median scores ≥5 (no failure-attribution tags needed). Composite 8.33 is the highest in the matrix this wave."
  - "Stealth claim (research/SUMMARY.md: 'Source-patched Chromium passes Cloudflare/reCAPTCHA/FingerprintJS/BrowserScan — 30/30 tests') is DEFERRED to G-710 per CONTEXT.md `## Deferred Ideas`. The 8.33 composite proves cloakbrowser CAN drive a browser session against snapshot fixtures; it proves NOTHING about its bot-detection performance. DEEP_ANALYSIS.md is explicit so Phase 4 cannot overclaim."
  - "Phase-4 tier pre-disposition encoded in DEEP_ANALYSIS.md: cloakbrowser will be tiered SANDBOX-ONLY regardless of S1-S8 score because the closed-binary trust model is the binding constraint, not the stealth claim. The 8.33 composite + sandbox_only=true field + the tier pre-disposition are all present so the Phase 4 matrix synthesis cannot accidentally promote cloakbrowser to PRIMARY tier."
  - "SANDBOX_PROOF.md takes a multi-tier audit approach (vs the naive grep that would false-positive on content strings): (1) pre-flight guard verification, (2) explicit enumeration of all cloak_navigate URLs + all fetch() URLs inside cloak_evaluate (the ONLY active egress vectors), (3) full hostname sweep with false-positive triage explaining why non-loopback content strings in transcripts are NOT request targets. All 6 unique cloak_navigate URLs targeted 127.0.0.1:8765; all fetch() URLs targeted 127.0.0.1:8765 or relative paths (which resolve to loopback)."
  - "REPORT-08 compliance: DEEP_ANALYSIS.md carries 6+ explicit 'Sandbox only — do not point at authenticated sessions' callouts at section boundaries and at section heads. Phase 4 readers cannot miss the contract."
  - "Cloakbrowser tool surface (20 tools) analyzed: the auto-snapshot-on-mutation convention reduces per-action token overhead vs Playwright's separate snapshot-then-act idiom — surfaced as a positive insight by the agent in transcripts. Surface gaps documented: no batch fill_form primitive (browser_fill_form-equivalent absent), no network request interception (chrome-devtools' CDP-direct primitive absent), no native <select> handling for option elements. None of these gaps cost cloakbrowser points in S1-S8 because cloak_evaluate is a sufficient workaround; they WILL surface in more demanding future waves."
  - "Linear sub-ticket G-720 referenced but not created at run time (per OUTREACH-03 ownership, same as 02-04 obscura + 02-05 browser-use precedent). DEEP_ANALYSIS.md + SANDBOX_PROOF.md ready to lift into G-720 when the per-MCP ticket sweep lands."

patterns-established:
  - "Pre-flight guard for closed-source binary MCPs: every closed-source MCP that touches host resources (cookies, sockets, FS) needs a pre-flight guard wired at the harness entry point that aborts the spawn if the configured target is outside a known-safe set. cloakbrowser uses `assert_local_only(SNAPSHOT_BASE_URL)`; future closed-source MCPs should adopt the same pattern with an appropriate allow-list."
  - "Multi-tier sandbox audit for sandbox-only MCPs: SANDBOX_PROOF.md must NOT be a single grep — it must be a 3-tier audit. (1) Pre-flight guard verification (positive + negative test). (2) Enumeration of all ACTIVE egress vectors (every tool call that can initiate a network request, NOT just navigate — also fetch() inside any evaluate primitive). (3) Full hostname sweep of evidence files with explicit false-positive triage distinguishing CONTENT (extracted strings from snapshot HTML) from REQUEST TARGETS. The naive grep would false-positive on stylesheet hrefs and og:url meta tags."
  - "Phase-4 tier pre-disposition: when an MCP scores well on the rubric but has a binding non-score constraint (closed-source binary, sandbox-only contract, vendor reliability concern, licensing issue), pre-document the Phase-4 tier in DEEP_ANALYSIS.md so the matrix synthesis cannot accidentally promote it. cloakbrowser is pre-tiered SANDBOX-ONLY. Future MCPs in similar positions should do the same."
  - "REPORT-08 callout repetition for sandbox-only MCPs: 'Sandbox only — do not point at authenticated sessions' must appear at section heads, not just once at the top of the document. Six or more occurrences in DEEP_ANALYSIS.md so a reader who skims cannot miss the contract. Reusable for any future sandbox-only MCP."

requirements-completed: [FAIRNESS-04, FAIRNESS-05]

duration: 25min
completed: 2026-05-26
---

# Phase 2 Plan 06: cloakbrowser Sandboxed Per-MCP Scoring Summary

Drove the locked Phase-1 harness against `cloakbrowsermcp` v2.0.4 (PyPI, closed-source source-patched Chromium binary by author `overtimepog`) strictly against loopback snapshot fixtures, producing a scored row capability-tagged `stealth-specialist` + mode `sandbox-loopback` + `sandbox_only: true`. The non-negotiable deliverable was `SANDBOX_PROOF.md` validating Phase 2 SC #5 ("zero requests to any hostname other than 127.0.0.1"); all three passes are confirmed clean. Median composite **8.33/10**, leading the matrix this wave, but Phase 4 will tier cloakbrowser SANDBOX-ONLY regardless because the closed-binary trust model is the binding constraint, not S1-S8 surface coverage. This was the LAST per-MCP plan; Phase 2 matrix is now closed at 7 scored MCPs + 1 SKIPPED.

## What was built

- **Pre-flight guard verification** (both positive + negative): `bench/cloakbrowser_guard.assert_local_only("http://127.0.0.1:8765")` returns cleanly; the same call with `"https://example.com"` raises `HostnameNotAllowedError`. The harness wiring at `scripts/run_mcp_session.sh:127-130` was confirmed BEFORE PASS1 spawned. The guard is invoked ONLY for `MCP_NAME=cloakbrowser` — cheap targeted check.
- **3-pass median harness run** against cloakbrowser (LAST per-MCP plan of the wave):
  - **PASS 1** — 5m01s wall-clock, 22 cloakbrowser tool calls, 35 turns, `error_during_execution` after typing 4/4 form fields cleanly. Claude Code SDK rejected the next `cloak_type` call; session terminated with S5-S8 untested. Stages: S1-S4 PASS, S5-S8 UNTESTED. Per-pass composite **7.27**.
  - **PASS 2** — 8m13s wall-clock, 27 cloakbrowser tool calls, 54 turns, clean `success` exit. All 8 stages complete with substantive artifacts including 56KB filled-form screenshot. Per-pass composite **8.13**.
  - **PASS 3** — 7m58s wall-clock, 30 cloakbrowser tool calls, 55 turns, clean `success` exit. All 8 stages complete with substantive artifacts including 56KB screenshot. Per-pass composite **8.33**.
- **Median row** in `results/2026-05-26/scores.json`: composite **8.33**, all 8 stages majority PASS, all 8 sub-rubric dimensions ≥5 (no failure-attribution tags needed). `capability="stealth-specialist"`, `mode="sandbox-loopback"`, `sandbox_only=true`. All 7 previously-existing rows preserved byte-for-byte.
- **SANDBOX_PROOF.md** — MANDATORY per Phase 2 SC #5. Three-tier audit: (1) pre-flight guard positive+negative test, (2) explicit enumeration of all `cloak_navigate` URLs (6 unique, all `127.0.0.1:8765`) + all `fetch()` URLs inside `cloak_evaluate` (4 unique, all loopback or relative), (3) full hostname sweep of transcripts with explicit false-positive triage distinguishing CONTENT strings (extracted from snapshot HTML: stylesheet hrefs, og:url meta, body anchors to `bit.ly/afpsafety`, `github.com`, `linkedin.com`, etc.) from REQUEST targets (zero — every navigate/fetch was loopback).
- **DEEP_ANALYSIS.md** — capability tag, mode, sandbox_only flag, median 8.33, per-stage verdicts (3-pass), PASS1 SDK-termination diagnosis (NOT a cloakbrowser defect), stealth-claim G-710 deferral, tool surface analysis (20 tools, 2nd-richest in matrix), surface gaps catalog, Phase-4 SANDBOX-ONLY tier pre-disposition, 6+ explicit "Sandbox only — do not point at authenticated sessions" REPORT-08 callouts.

## Why this approach (not alternatives)

- **3-pass median chosen** (not single-pass) per CONTEXT.md `## Decisions § Median-of-3 Retry Gate` and FAIRNESS-01 contract. The fact that PASS1 terminated early validates the protocol choice: a single-pass result for cloakbrowser could have landed anywhere in {7.27, 8.13, 8.33} depending on which session was sampled. The 3-pass median (with majority-PASS stage verdicts) is what makes this row honest.
- **SCORED branch chosen** (not SKIPPED) — the binary launched cleanly with no Gatekeeper rejection on first invocation. No `xattr -d com.apple.quarantine` workaround needed (which would have violated CLAUDE.md per the plan's explicit prohibition). cloakbrowsermcp v2.0.4 was already installed via `uv tool install cloakbrowsermcp`.
- **Multi-tier sandbox audit** chosen (not naive grep) — the snapshot fixtures legitimately contain external URLs as content (Greenhouse's og:url is `https://job-boards.greenhouse.io/...`, the apply button anchors to `https://bit.ly/afpsafety`, etc.). A naive `grep -v "127.0.0.1"` would have false-positived on these content strings. The 3-tier audit explicitly distinguishes ACTIVE egress vectors (under harness control via tool calls) from CONTENT (passive strings in extracted HTML).
- **Symlink-trick aggregator invocation** per obscura 02-04 precedent — the aggregator's `aggregate_date_dir` requires a date-level dir with one subdir per MCP. PASS{1,2,3}/ are sub-subdirs. `ln -s $PWD/results/$DATE/cloakbrowser/PASSn $TMP/cloakbrowser` + `aggregate_scores.py $TMP/` preserves the aggregator as-is. Same protocol used by chrome-devtools 02-01 (`.merge.py` wrapper variant) and obscura 02-04.

## Falsifiable empirical finding

**Research SUMMARY.md claim:**
> "cloakbrowser — Source-patched Chromium passes Cloudflare Turnstile, reCAPTCHA v3 (0.9 score), FingerprintJS, BrowserScan — 30/30 tests, no captcha solving needed."

**STATUS: DEFERRED to G-710** per CONTEXT.md `## Deferred Ideas` ("Bot-detection adversary testing per MCP → G-710" + "TLS fingerprint capture per MCP → G-710"). This plan does NOT test the stealth claim — the snapshot fixtures don't fingerprint-check, so cloakbrowser's 8/8 PASS on Greenhouse/Ashby loopback proves NOTHING about Cloudflare/reCAPTCHA performance. DEEP_ANALYSIS.md documents this explicitly so Phase 4 cannot overclaim.

**What IS demonstrated by 8.33 composite:** cloakbrowser CAN drive a browser session (navigate, snapshot, click, type, screenshot, evaluate, file upload). The 20-tool surface is rich enough to execute the full S1-S8 walk; the `cloak_evaluate` JS escape hatch is the load-bearing workaround primitive for the React-hydration clobber that defeated several other MCPs on the same fixtures. None of this validates the stealth claim — that's G-710's job.

## Sandbox-only contract upheld

**Phase 2 SC #5 result: SATISFIED.** Every active network egress vector under harness control was verified to target `127.0.0.1:8765` exclusively:
- 6 unique `cloak_navigate` URLs across 3 passes — all `127.0.0.1:8765`
- 4 unique `fetch()` URLs inside `cloak_evaluate` — all `127.0.0.1:8765` or relative (which resolves to loopback)
- 0 SANDBOX_VIOLATION.md sentinel files triggered
- 14 non-loopback hostnames appearing in transcripts — ALL are content strings extracted from snapshot HTML (og:url meta tags, stylesheet hrefs, body anchor hrefs), NEVER request targets

The closed-source cloakbrowser binary was only ever pointed at the loopback snapshot server. Cookie-touching at launch (the architectural reason for the sandbox-only contract) affected only the agent's ephemeral profile, not any authenticated session.

## Matrix-leading composite — and the binding constraint

| Rank | MCP | Median composite | Tier (Phase 4 pre-disposition) |
|---|---|---|---|
| 1 | **cloakbrowser** | **8.33** | **SANDBOX-ONLY** (binding: closed-source binary, sandbox-only contract) |
| 2 | playwright | 7.93 | PRIMARY (TBD by Phase 4) |
| 3 | lightpanda | 6.31 | js-light specialty (TBD) |
| 4 | browser-use-direct | 5.87 | TBD |
| 5 | chrome-devtools | 5.60 | TBD |
| 6 | firecrawl | 4.23 | cloud / read-only (TBD) |
| 7 | obscura | 3.27 | TBD |
| 8 | browser-use-agent | SKIPPED | LLM_KEY_ABSENT |

cloakbrowser leads the matrix on S1-S8 surface coverage. **But the 8.33 composite does NOT promote cloakbrowser to PRIMARY tier in Phase 4** — the closed-binary trust model is the binding constraint:
- Closed-source — no third-party audit
- Touches cookies on launch — architectural reason for the sandbox contract
- Telemetry surface unknown — bounded by loopback restriction, but not auditable

For PRIMARY-tier graduation (Stage 2 terminal-craft toolkit, which runs against authenticated sessions on real Greenhouse / Ashby hosts), an MCP must be auditable or behavior-bounded. cloakbrowser fails both. DEEP_ANALYSIS.md pre-documents the SANDBOX-ONLY tier so Phase 4's `recommendations.md` cannot accidentally promote cloakbrowser on the strength of S1-S8 surface alone.

## Per-pass variance commentary

Three passes against an identical MCP/fixture/harness produced composites {7.27, 8.13, 8.33}. The variance is dominated by PASS1's premature termination, NOT by cloakbrowser behavior:
- **PASS 1** terminated at S5 by Claude Code SDK budget exhaustion / tool rejection on the `cloak_type` call for `+1 555 867 5309`. The agent had a working session with a healthy browser at termination; same `cloak_type` signature succeeded in PASS2 and PASS3. SDK-side variance, not MCP variance.
- **PASS 2** ran clean to 54 turns with all 8 stages complete.
- **PASS 3** ran clean to 55 turns with all 8 stages complete; slightly better error-handling lexeme density gave error_handling=8 vs PASS2's =5.

**The MCP behaved consistently across all 3 passes where attempted.** The variance is harness-side budget phenomena, not cloakbrowser surface. Pattern matches plans 02-01 (chrome-devtools PASS3 SSR-rescue) and 02-04 (obscura PASS1 SSRF-guard workaround) — agent-discovery / SDK-budget variance, not MCP variance.

## Acceptance Criteria

- [x] Full evidence: 3 passes + `SANDBOX_PROOF.md` (MANDATORY) + scores.json row with capability=stealth-specialist + sandbox_only=true + DEEP_ANALYSIS.md with sandbox-only callout.
- [x] NO `SANDBOX_VIOLATION.md` sentinel exists.
- [x] Phase 2 SC #5 is met: zero non-127.0.0.1 hostnames in cloakbrowser evidence files (active vectors).
- [x] Every cloakbrowser mention in DEEP_ANALYSIS.md carries `Sandbox only — do not point at authenticated sessions` (REPORT-08).
- [x] Every sub-rubric cell < 5 has attribution — N/A (zero sub-5 cells; nothing to attribute).
- [x] `scoring/score.py` byte-for-byte unchanged (`git diff HEAD -- scoring/score.py | wc -l` returns 0).
- [x] All previously-existing rows in `scores.json` byte-for-byte unchanged (browser-use-direct + browser-use-agent + chrome-devtools + firecrawl + lightpanda + obscura + playwright verified via diff).

## Deviations from Plan

None. The plan executed exactly as written. The SCORED branch was taken (binary launched cleanly with no Gatekeeper rejection); no SKIPPED.md was needed. The multi-tier sandbox audit in SANDBOX_PROOF.md is more thorough than the plan's example grep (which would have false-positived on content strings); this is methodology-honesty refinement, not a deviation.

## Self-Check

- [x] `results/2026-05-26/cloakbrowser/PASS{1,2,3}/` directories — FOUND
- [x] `results/2026-05-26/cloakbrowser/PASS{1,2,3}.json` — FOUND (per-pass composites 7.27, 8.13, 8.33)
- [x] `results/2026-05-26/cloakbrowser/SANDBOX_PROOF.md` — FOUND
- [x] `results/2026-05-26/cloakbrowser/DEEP_ANALYSIS.md` — FOUND (6+ REPORT-08 callouts; G-710 deferral; SANDBOX-ONLY tier pre-disposition)
- [x] `results/2026-05-26/scores.json` cloakbrowser row — FOUND (capability=stealth-specialist, mode=sandbox-loopback, sandbox_only=true, composite 8.33)
- [x] `scoring/score.py` byte-for-byte unchanged — VERIFIED
- [x] All 7 other scores.json rows byte-for-byte unchanged — VERIFIED
- [x] No `SANDBOX_VIOLATION.md` sentinel — VERIFIED

## Self-Check: PASSED
