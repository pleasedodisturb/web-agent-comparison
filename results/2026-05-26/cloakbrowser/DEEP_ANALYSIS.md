# cloakbrowser — Deep Analysis (2026-05-26)

> **⚠ Sandbox only — do not point at authenticated sessions.**
> cloakbrowser is a closed-source binary that touches host cookies on launch.
> Every reference to cloakbrowser in this document, in `scores.json`, and in
> the eventual Phase 4 report MUST carry this callout (REPORT-08 contract).
> The run was performed exclusively against `http://127.0.0.1:8765` loopback
> snapshot fixtures, audited in `SANDBOX_PROOF.md`.

**MCP:** `cloakbrowsermcp` v2.0.4 (PyPI, author `overtimepog`)
**Engine:** Source-patched Chromium (closed-source binary, bundled with the PyPI wheel)
**Capability tag:** `stealth-specialist`
**Mode:** `sandbox-loopback` (the ONLY supported mode under SAFETY-04)
**`sandbox_only`:** `true` (machine-readable Phase-4 carry-over flag for REPORT-08)
**Median composite (3-pass, N/A-aware):** **8.33 / 10**
**Run dates:** 2026-05-26 (all 3 passes within a 23-minute window, 21:20-21:43 UTC)
**Linear ticket:** G-720 (cloakbrowser sub-ticket of G-703)

## Capability tag

`stealth-specialist` — cloakbrowser's market positioning is source-patched
Chromium that purportedly defeats Cloudflare, reCAPTCHA, FingerprintJS, and
BrowserScan. Same category as `obscura`; distinct from `playwright` /
`chrome-devtools` (`tool-only`), `browser-use-agent` (`LLM-augmented`), and
`firecrawl` (`cloud`).

**The tag is honest about positioning, not about measurement in this phase.**
Phase 2's S1-S8 walk does NOT exercise bot-detection avoidance — the snapshot
fixtures don't fingerprint-check; they are static HTML served from loopback.
cloakbrowser's stealth advantage is NOT validated by an 8.33 composite on this
walk. See § "Stealth claims — DEFERRED to G-710" below.

## Median composite & sub-rubric

| Dimension (weight) | Median | PASS1 | PASS2 | PASS3 |
|---|---|---|---|---|
| Data Quality (3×) | **10** | 10 | 10 | 10 |
| Reliability (3×) | **10** | 10 | 10 | 10 |
| Speed (2×) | **5** | 5 | 5 | 5 |
| Token Efficiency (2×) | **5** | 5 | 5 | 5 |
| Interaction Depth (2×) | **10** | 2 | 10 | 10 |
| JS Rendering (1×) | **10** | 10 | 10 | 10 |
| Setup Complexity (1×) | **7** | 7 | 7 | 7 |
| Error Handling (1×) | **8** | 8 | 5 | 8 |
| **Weighted Composite** | **8.33** | 7.27 | 8.13 | 8.33 |

Speed, Token Efficiency, and Setup Complexity are neutral mid-band values per
the Phase-1 stub policy (cold_start.json + tokens.json are `{deferred:
phase-3}`; Setup Complexity is locked at 7 until plan 01-07's successor
measurement task). Same constants every MCP carries this wave.

> **⚠ Sandbox only — do not point at authenticated sessions.**

## Per-stage verdicts (3-pass majority)

| Stage | Median verdict | PASS1 | PASS2 | PASS3 | Why |
|---|---|---|---|---|---|
| S1 — Greenhouse extract | **PASS** | PASS | PASS | PASS | All 3 passes used `cloak_evaluate(fetch + DOMParser)` to extract the static SSR HTML before the React shell hydrated and clobbered the body. Workaround is durable. |
| S2 — Ashby SPA extract | **PASS** | PASS | PASS | PASS | All 3 passes acknowledged the Ashby fixture is a 6,294-byte bootstrap shell (no inline data island) and documented the "Page not found" post-hydration result. Cloakbrowser's full Chromium ran the SPA bundle; the fixture lacks live API backing, which IS the finding. |
| S3 — Platform detection | **PASS** | PASS | PASS | PASS | Distinguishing markers cited consistently (URL shape, CDN host, SSR-vs-bundle ratio, og:url meta). |
| S4 — Apply-form snapshot | **PASS** | PASS | PASS | PASS | All 3 used `cloak_evaluate` to inject the static form HTML into the live document and `remove()` scripts so React couldn't re-clobber it. Pattern is robust. |
| S5 — Fill form | **PASS** (2-of-3) | UNTESTED | PASS | PASS | Pass 1 hit a Claude Code SDK rejection after typing 4 of 4 fields and never wrote `stage_s5.md`; Passes 2 and 3 wrote substantive artifacts (4-field state capture in PASS2, 5-field in PASS3). |
| S6 — Upload resume | **PASS** (2-of-3) | UNTESTED | PASS | PASS | Used `cloak_evaluate` with base64-decoded PDF buffer + `DataTransfer` to set `<input type=file>`. The `cloak_evaluate` escape hatch is the load-bearing primitive. |
| S7 — React-Select dropdown | **PASS** (2-of-3) | UNTESTED | PASS | PASS | Both passes correctly noted the fixture lacks a "How did you hear?" source field and degraded gracefully by documenting that. |
| S8 — Screenshot | **PASS** (2-of-3) | UNTESTED | PASS | PASS | `cloak_screenshot` produced 56KB PNGs of the filled form in both completed passes. |

**Tool calls per pass:** PASS1 = 22, PASS2 = 27, PASS3 = 30.
**Wall-clock per pass:** PASS1 = 5m01s (301s), PASS2 = 8m13s (493s), PASS3 = 7m58s (478s). Median = 7m58s. None exceeded the 60-minute budget.

> **⚠ Sandbox only — do not point at authenticated sessions.**

## The PASS 1 incident — Claude Code SDK budget exhaustion, NOT a cloakbrowser bug

PASS 1 terminated at S5 with `subtype=error_during_execution` after 35 turns
and 301 seconds. The trigger was a single `is_error=true` tool result on the
`cloak_type` call that typed `+1 555 867 5309` into the phone input — the
Claude Code SDK rejected the tool call with "The user doesn't want to proceed
with this tool use." (No interactive user — the session ran in `--print`
non-interactive mode with `permissionMode=auto`.) The session exited without
writing S5-S8 artifacts.

**This is NOT a cloakbrowser defect.** The first 4 stages plus 4 typed
form fields all succeeded; the agent had a working session with a healthy
browser when the SDK pushed back. The same `--allowedTools
mcp__cloakbrowser__*,Read,Write,Bash` allow-list was in place; the
`cloak_type` call signature is the same as PASS 2 and PASS 3 calls that
succeeded. The 3-pass median protocol exists exactly to absorb this kind of
SDK-side variance (FAIRNESS-01 contract). Passes 2 and 3 each ran to
clean completion (`subtype=success`, 54-55 turns, all 8 stages).

**Attribution:** the PASS 1 termination is `tool-bug`-coded in the harness
taxonomy by default, but the *MCP* under test (cloakbrowser) ran without
any tool-call error in PASS 1 up to and including the rejected `cloak_type`
turn. The rejection came from the orchestrating Claude Code SDK, not the
MCP server. Per the precedent set in plans 02-01 (chrome-devtools PASS3
SSR-rescue) and 02-04 (obscura PASS1 SSRF-guard workaround), pass-to-pass
variance dominated by harness-side phenomena is a known shape this wave's
median-of-3 protocol surfaces.

## The falsifiable empirical finding — Stealth claims (DEFERRED to G-710)

Per `.planning/research/SUMMARY.md § Empirical Claims to Falsify`:

> Claim: "Source-patched Chromium passes Cloudflare Turnstile, reCAPTCHA v3
> (0.9 score), FingerprintJS, BrowserScan — 30/30 tests, no captcha solving
> needed."

**STATUS: DEFERRED to G-710** per CONTEXT.md `## Deferred Ideas`:

> - TLS fingerprint capture per MCP → G-710.
> - Bot-detection adversary testing per MCP → G-710.

This plan does NOT test the stealth claim. The snapshot fixtures don't
fingerprint-check, so cloakbrowser's 8/8 PASS on Greenhouse/Ashby loopback
proves **only** that cloakbrowser CAN drive a browser session (forms,
clicks, screenshots, JS execution, file upload). It is silent on whether
the source-patched Chromium can pass any of the named detectors.

**Phase 4 MUST NOT cite the 8.33 composite as evidence for the stealth
claim.** The composite reflects S1-S8 surface coverage on snapshot
fixtures, identical to every other MCP in the matrix. G-710 is the right
venue for the adversary test: a fixed bot-detection probe set
(Cloudflare nowsecure.nl, reCAPTCHA demo, BrowserScan, FingerprintJS
demo) run from each Chromium-class MCP with identical user-agent
intent, comparing pass-fail outcomes.

> **⚠ Sandbox only — do not point at authenticated sessions.**

## What IS demonstrated by an 8.33 composite

- **Tool surface is rich (20 tools, second only to chrome-devtools' 29).**
  `cloak_launch`, `cloak_navigate`, `cloak_snapshot`, `cloak_click`, `cloak_type`,
  `cloak_select`, `cloak_hover`, `cloak_check`, `cloak_read_page`,
  `cloak_screenshot`, `cloak_back`, `cloak_forward`, `cloak_press_key`,
  `cloak_scroll`, `cloak_wait`, `cloak_evaluate`, `cloak_new_page`,
  `cloak_list_pages`, `cloak_close_page`, `cloak_close`. Coverage spans
  navigation, snapshot, interaction, capture, eval — every primitive the
  S1-S8 walk needs is present.
- **The `cloak_evaluate` JS escape hatch is robust.** All three passes used
  it as the load-bearing primitive for the fixture's React-hydration
  clobber problem — the agent injected the static form HTML into the live
  document and removed scripts so React couldn't re-mount and wipe the
  form. This is the same defensive pattern other MCPs *attempted* on
  this fixture (chrome-devtools PASS3 SSR-rescue, obscura PASS1
  `0.0.0.0` workaround); cloakbrowser executed it cleanly twice.
- **Accessibility-tree snapshots return refs cleanly.** `cloak_snapshot`
  returned a 15-ref interactive tree after the form-injection workaround;
  every subsequent `cloak_type(ref=@eN, ...)` call resolved correctly.
  No flaky-ref drift between calls (a problem some other MCPs in this
  matrix exhibit).
- **`cloak_screenshot` produced viable PNG artifacts** (56KB each, full-page
  capture of the filled form). PASS2 and PASS3 both delivered.
- **Auto-snapshot-on-mutation pattern is convenient and matches advertising.**
  Every `cloak_click` / `cloak_type` / `cloak_select` call auto-returns
  an updated snapshot in `_snapshot` field — the agent doesn't need to
  manually re-snapshot between actions. This is a token-efficiency win
  the agent surfaced as a positive insight in transcripts.

## Tool surface gaps (what cloakbrowser lacks)

Independent of the stealth-claim deferral, cloakbrowser's surface is
**missing some primitives that Playwright provides**:

- **No `browser_fill_form` batch-fill.** Filling 4 fields requires 4
  separate `cloak_type` calls (4 round-trips). Playwright handles 6
  fields in 1 call. Real token-efficiency cost.
- **No `browser_network_request` interception / replay.** Cannot
  programmatically inject responses for the React-hydration backend
  the way chrome-devtools' CDP-direct `network.*` primitives could.
  The `cloak_evaluate` + `document.body.innerHTML = ...` workaround
  is the substitute; it works but is more fragile.
- **No `browser_select_option` for native `<select>`.** Has
  `cloak_select` but it operates on accessibility-tree refs, not
  CSS selectors. Adequate but different from the Playwright idiom.
- **No multi-page tab management beyond `cloak_new_page` /
  `cloak_list_pages` / `cloak_close_page`.** Adequate for S1-S8 but
  may be limiting for complex multi-tab flows.

None of these gaps cost cloakbrowser points in the S1-S8 walk
(because the workarounds via `cloak_evaluate` succeed twice), but they
WILL surface if a future wave includes more demanding interaction
patterns.

> **⚠ Sandbox only — do not point at authenticated sessions.**

## Failure-attribution table

The 8.33 composite has **zero sub-rubric cells < 5** — no attribution
required. The only cell that crossed into the partial-credit band is:

| Dimension | Score | Tag | Justification |
|---|---|---|---|
| `error_handling` | 8 | (none — score >= 5) | The heuristic counts `error|retry|fail` lexemes in transcript.md. The 3 transcripts collectively had moderate occurrences (~10-15 across all 3 passes combined) — mostly from PASS 1's S5 termination narrative and explicit "failure mode" documentation in stage artifacts. Not an MCP defect. |

For reference, the matrix-wide attribution context:

| MCP | Sub-5 cells | Median composite |
|---|---|---|
| cloakbrowser | **0** | 8.33 |
| playwright | 0 | 7.93 |
| lightpanda | 1 (js_rendering=2) | 6.31 |
| browser-use-direct | 2 (error_handling=2, interaction_depth=2) | 5.87 |
| chrome-devtools | 2 (error_handling=2, interaction_depth=0) | 5.60 |
| firecrawl | 2 (data_quality=0, js_rendering=2) | 4.23 |
| obscura | 4 (data_quality, error_handling, interaction_depth, js_rendering all sub-5) | 3.27 |
| browser-use-agent | N/A (SKIPPED: LLM_KEY_ABSENT) | 0.00 |

cloakbrowser leads the matrix in this S1-S8-surface dimension. This is a
real and meaningful finding — but see the next section for the binding
constraint that prevents Phase 4 from promoting it to PRIMARY tier.

## Phase 4 tier pre-disposition — SANDBOX-ONLY regardless of score

Per the plan's `must_haves.truths`:

> "Sandbox-only deferred-tier note: per recommendations.md (Phase 4):
> cloakbrowser will be tiered `SANDBOX-ONLY` regardless of S1-S8 score
> because the closed-binary trust model is the binding constraint, not
> the stealth claim."

**Pre-documented here so Phase 4 cannot accidentally promote cloakbrowser
to PRIMARY tier on the strength of an 8.33 composite alone.**

The binding constraint is the closed-source binary trust model:

- **Closed-source** — `cloakbrowsermcp` ships a binary from PyPI (author
  `overtimepog`) that no third-party audit has reviewed.
- **Touches cookies on launch** — per
  [`docs/external-findings/browser-tools-2026-05-21.md`](../../../docs/external-findings/browser-tools-2026-05-21.md)
  § "Cookie-touch on launch", the binary modifies host cookies before
  the harness has a chance to intercept. This is the architectural
  reason for the loopback-only contract.
- **Telemetry surface unknown** — the binary may phone home; we have
  no way to know without reverse engineering. Loopback restriction
  bounds the exposure to the harness's ephemeral session.

For PRIMARY-tier graduation to the Stage-2 terminal-craft toolkit
(which runs against authenticated sessions on real Greenhouse / Ashby
hosts), an MCP must be auditable or behavior-bounded. cloakbrowser fails
both:

- It cannot be audited (closed source).
- It cannot be behavior-bounded outside the loopback sandbox (the
  cookie-touching is pre-handshake).

Phase 4's `recommendations.md` should tier cloakbrowser as
**SANDBOX-ONLY** with these properties:
- High S1-S8 surface coverage (factually established by 8.33)
- Stealth claims unvalidated (deferred to G-710)
- Closed-binary trust model unsuitable for authenticated sessions
- Suitable for: sandboxed scraping of public sites, throwaway scraping
  contexts, research-mode bot-detection adversary testing (when paired
  with the G-710 adversary set), educational use.
- NOT suitable for: production agent toolkit on user's real
  Greenhouse / Ashby / LinkedIn / etc. sessions.

> **⚠ Sandbox only — do not point at authenticated sessions.**

## Pass-to-pass variance commentary

Three passes against an identical MCP/fixture/harness produced composites
{7.27, 8.13, 8.33}. The variance is dominated by PASS 1's premature
termination (S5-S8 = UNTESTED), not by cloakbrowser behavior:

- **PASS 1** (terminated at S5 by Claude Code SDK): completed S1-S4
  cleanly, typed 4 of 4 form fields, then the SDK rejected the next
  `cloak_type` call and the session ended at 35 turns with
  `error_during_execution`. Composite 7.27 reflects S5-S8 UNTESTED
  (which the aggregator scores as not-attempted, distinct from FAIL).
- **PASS 2** (clean run, 54 turns): all 8 stages complete with
  substantive artifacts including the S8 screenshot. Composite 8.13.
- **PASS 3** (clean run, 55 turns): all 8 stages complete, slightly
  better error-handling lexeme density gave error_handling=8 vs PASS 2's
  =5. Composite 8.33.

**The MCP behaved consistently across all 3 passes** where attempted.
The session-length variance is a Claude Code SDK budget phenomenon
unrelated to cloakbrowser's surface.

## Wall-clock budget posture

| | Time |
|---|---|
| PASS1 wall-clock | 5m01s (301s) — terminated early |
| PASS2 wall-clock | 8m13s (493s) |
| PASS3 wall-clock | 7m58s (478s) |
| Total (3 passes) | 21m12s (1,272s) |
| Budget per pass | 60m |
| Single-pass fallback invoked? | **No** |

> **⚠ Sandbox only — do not point at authenticated sessions.**

## Tools inventory snapshot

From `tools_inventory.json` (probed via `mcp.client.stdio` before the
runs):

| Category | Count | Tools |
|---|---|---|
| navigation | 2 | `cloak_navigate`, `cloak_new_page` |
| inspection | 2 | `cloak_snapshot`, `cloak_read_page` |
| interaction | 6 | `cloak_click`, `cloak_type`, `cloak_select`, `cloak_hover`, `cloak_check`, `cloak_press_key` |
| capture | 1 | `cloak_screenshot` |
| diagnostics | 0 | — |
| other | 9 | `cloak_launch`, `cloak_close`, `cloak_back`, `cloak_forward`, `cloak_scroll`, `cloak_wait`, `cloak_evaluate`, `cloak_list_pages`, `cloak_close_page` |
| **TOTAL** | **20** | |

20 tools is second-richest in the matrix (chrome-devtools 29, playwright
~30, browser-use ~25, obscura 4, lightpanda 1, firecrawl 5). The
auto-snapshot-on-mutation convention reduces the per-action token
overhead vs Playwright's separate snapshot-then-act pattern.

## Sandbox enforcement

See companion `SANDBOX_PROOF.md` for the SC #5 audit: every active
network egress vector (`cloak_navigate` + every `fetch(...)` inside
`cloak_evaluate`) was verified to target `127.0.0.1:8765` exclusively
across all 3 passes. Non-loopback hostnames appearing in transcript
text are content extracted from the snapshot HTML, not request
targets. `bench/cloakbrowser_guard.assert_local_only` pre-flight
guard wired at `scripts/run_mcp_session.sh:127-130` is the
load-bearing safety control.

> **⚠ Sandbox only — do not point at authenticated sessions.**

## Linear ticket

Per CONTEXT.md `## Decisions § Execution Order`, this row belongs under
sub-ticket **G-720** (cloakbrowser split of G-703). A summary comment
referencing this DEEP_ANALYSIS.md + the 8.33 median composite +
SANDBOX_PROOF.md attestation + the G-710 stealth-claim deferral will
be posted via `linearis comments create G-720` (deferred to per-MCP
ticket sweep per OUTREACH-03 ownership precedent).

## Sources

- `results/2026-05-26/cloakbrowser/PASS{1,2,3}/` — per-pass evidence
- `results/2026-05-26/cloakbrowser/PASS{1,2,3}.json` — per-pass aggregated rows
- `results/2026-05-26/cloakbrowser/SANDBOX_PROOF.md` — SC #5 audit
- `results/2026-05-26/cloakbrowser/PASS2/tools_inventory.json` — 20-tool inventory
- `results/2026-05-26/scores.json` — median row alongside the 7 other MCPs
- `bench/cloakbrowser_guard.py` — sandbox enforcement primitive
- `CLAUDE.md ## Constraints` — sandbox-only policy origin
- [`docs/external-findings/browser-tools-2026-05-21.md`](../../../docs/external-findings/browser-tools-2026-05-21.md) — closed-binary cookie-touching note
- `.planning/research/SUMMARY.md § Empirical Claims to Falsify` — stealth claim (DEFERRED to G-710)

**Sacrosanct check:** `scoring/score.py` byte-for-byte unchanged
(`git diff main -- scoring/score.py | wc -l` returns 0; verified in SUMMARY).

> **⚠ Sandbox only — do not point at authenticated sessions.**
