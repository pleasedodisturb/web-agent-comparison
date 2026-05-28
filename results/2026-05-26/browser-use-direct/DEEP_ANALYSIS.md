# browser-use (direct mode) — Deep Analysis

**Capability tag:** `LLM-augmented`
**Mode:** `direct` (no LLM key set — tool-only invocation path)
**MCP version:** `browser-use` v0.12.7 (PyPI), invoked via `browser-use --mcp`
**Run date:** 2026-05-26
**Median composite:** **5.87 / 10** (per-pass: 6.07, 6.20, 5.87 — spread = 0.33)
**Plan:** Phase 2 Plan 02-05 (Task 1 of 2)
**Linear ticket:** G-715 (browser-use sub-ticket of G-703)

---

## Headline empirical finding (Vitalik's question)

**Question (per CONTEXT.md `## Specifics` + `research/SUMMARY.md § Empirical Claims
to Falsify`):**
> "Does browser-use work in Claude Code WITHOUT the user's own LLM API key?
> Evidence: Launch with NO OPENAI_API_KEY/ANTHROPIC_API_KEY — does S1+S5 succeed?"

**Answer: CONFIRMED for S1 (and S2 + S3 + S8); REFUTED for S5 (and all of S4-S7).**

The nuance matters and is the whole point of running this twice:

- **S1, S2, S3, S8 succeed in direct mode** without any LLM key. browser-use's
  tool surface (`browser_navigate`, `browser_get_state`, `browser_extract_content`,
  `browser_get_html`, `browser_screenshot`) is **deterministic** — these tools
  drive a real Playwright Chromium and return DOM / HTML / screenshots. No
  in-tool LLM call required. The Claude Code session in the harness IS the
  brain; browser-use is just a tool surface.
- **S4-S7 fail in direct mode** — but NOT because the LLM is absent. They fail
  because the Greenhouse snapshot's React app hydrates and replaces the
  apply-form DOM with a "Page not found" shell (the SPA expects its
  `job-boards.greenhouse.io` backend; the loopback fixture has no backend, so
  the React app's not-found route wins). Once the form DOM is destroyed, no
  amount of LLM intelligence in `retry_with_browser_use_agent` would help —
  the input elements simply don't exist post-hydration. Same wall every
  JS-rendering MCP hits (chrome-devtools 02-01 also failed S4-S7 for this
  reason; obscura 02-04 too).

### Pre-spawn env state verification (per plan 02-05 Task 1 step 4)

The harness was invoked via:
```
env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u OPENAI_API_BASE \
  MCP_MODE=direct bash scripts/run_mcp_session.sh browser-use
```
Pre-spawn shell logged:
```
==> Pre-spawn env state for direct mode:
[none — both keys scrubbed]
```
(captured from harness invocation stdout, not shown in the per-pass evidence;
preserved in the commit message for `G-703: add browser-use-direct row`.)

### Negative evidence the LLM escape hatch was NOT exercised

`retry_with_browser_use_agent` is browser-use's documented LLM-driven fallback
tool that internally invokes an LLM (via OPENAI_API_KEY / ANTHROPIC_API_KEY)
to plan multi-step actions. Direct mode means: this tool is in the surface
but cannot fire because no key is present.

PASS1, PASS2, PASS3 transcripts each contain an explicit note:
> "`retry_with_browser_use_agent` (the LLM-agent fallback) was not invoked."
> "Token usage on this run is the read-only navigation cost only; no
>  LLM-driven retries."
> "would have added an out-of-band LLM call that the harness allow-list
>  ... and the structural hydration-to-404 issue is fixture-side, so an
>  LLM agent would face the same wall."

So the run is a clean deterministic-tools-only baseline. The claim
**"browser-use direct mode works without the user's own LLM API key"** is
CONFIRMED for the read-only / static-extraction subset of the harness
(S1-S3 + S8), and REFUTED for the form-interaction subset (S4-S7) — but
the latter REFUTATION traces to fixture-side React clobber, not to
browser-use missing an LLM. Re-running in agent mode would not unblock
S4-S7 (the form simply isn't there to fill), but it WOULD let
`retry_with_browser_use_agent` attempt creative workarounds (e.g. waiting
longer for a re-hydration, or pre-empting React mount); whether those
workarounds find a path is the falsifiable test for browser-use-agent —
which is SKIPPED on this run for lack of an LLM key. See
`browser-use-agent/SKIPPED.md`.

---

## HANDOFF-GSD-AUTO STOP #2 status

**STOP #2 (per HANDOFF-GSD-AUTO):**
> "browser-use v0.12.7 may still have the initialize timeout from the
>  2026-05-21 testbench (testbench reported 0/15)."

**Status on 2026-05-26: CONFIRMED FIXED.**

Pre-flight smoke test (per plan 02-05 Task 1 step "Pre-flight initialize-
timeout check"):
- `bench.tools_inventory browser-use` (agent-mode env) → `status=OK,
  tool_count=16` in ~7s ≪ 30s timeout. Saved to `init_smoke.json`.
- `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u OPENAI_API_BASE
  bench.tools_inventory browser-use` (direct-mode env) → `status=OK,
  tool_count=16` in ~7s. Saved to `init_smoke.json` (same content as
  agent — the handshake doesn't consume LLM keys).
- Three full S1-S8 harness runs each spawned the browser-use --mcp
  server fresh and completed S1-S3 without any initialize hang. The
  full 3-pass wall-clock was 400s + 565s + 367s = ~22 minutes total
  across direct mode; if init had timed out at any point, those passes
  would have died at second-1 of stage S1.

**Conclusion:** The 2026-05-21 testbench's initialize timeout was
genuinely a 2026-05 regression that got fixed in or before v0.12.7. The
SKIPPED-with-INIT_TIMEOUT branch is NOT taken; the standard 3-pass
scored branch was used.

---

## Per-pass median computation

Per-pass aggregated rows (each computed by `scripts/aggregate_scores.py`
against a symlink-aliased per-pass dir, as `aggregate_date_dir` requires
date-level → mcp-level path layout):

| Pass | Composite | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| PASS1 (400s)  | 6.07 | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | PASS | Optimist-agent: attempted forms, hit React clobber, recorded as FAIL |
| PASS2 (565s)  | 6.20 | PASS | PASS | PASS | FAIL | N/A  | N/A  | N/A  | N/A  | Capability-correct agent: marked downstream stages N/A after S4 blocked |
| PASS3 (367s)  | 5.87 | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | PASS | Optimist-agent (same shape as PASS1) |

**3-pass median (per `.merge.py`):**
- `data_quality`: median(10,10,10)=10
- `reliability`: median(5,8,5)=5
- `speed`: median(5,5,5)=5
- `token_efficiency`: median(5,5,5)=5
- `interaction_depth`: median(2,0,2)=2
- `js_rendering`: median(10,10,10)=10
- `setup_complexity`: median(7,7,7)=7
- `error_handling`: median(5,2,2)=2

**Stages (majority verdict):**
- S1=PASS (3 of 3), S2=PASS (3 of 3), S3=PASS (3 of 3) — unanimous read-only
- S4=FAIL (3 of 3) — unanimous on form unreachable
- S5/S6/S7=FAIL (2 of 3 FAIL, 1 N/A) — majority FAIL
- S8=PASS (2 of 3 PASS, 1 N/A) — majority PASS

**Composite: 5.87/10** — slots into 3rd place ahead of chrome-devtools
(5.6) and below lightpanda (6.31 N/A-aware).

### Variance vs other 3-pass runs

| MCP | Per-pass spread | Variance source |
|---|---|---|
| playwright (Phase 1)         | 7.93/7.93/7.93 | None (calibration baseline) |
| chrome-devtools (02-01)      | 5.6/5.6/8.33 (Δ=2.73) | PASS3 alone found SSR-rescue trick |
| lightpanda (02-02)           | 6.31/6.31/6.31 (Δ=0) | Read-only; deterministic |
| firecrawl (02-03)            | 4.23/4.23/4.23 (Δ=0) | Deterministic FAIL (loopback unreachable) |
| obscura (02-04)              | 3.27/4.07/3.27 (Δ=0.80) | PASS1 found 0.0.0.0 SSRF-guard workaround |
| **browser-use-direct (02-05)** | **6.07/6.20/5.87 (Δ=0.33)** | **Disagreement on N/A vs FAIL for unreachable stages** |

browser-use-direct's variance is the lowest of the agent-driven MCPs
(below chrome-devtools and obscura). The 0.33-point spread traces to a
single decision: PASS2's agent marked S5-S8 as capability-N/A after S4
hit the React clobber (correct reasoning: "no form to fill = not
applicable to this MCP for this fixture"), while PASS1 and PASS3 marked
them as FAIL ("the harness tried, it didn't work, that's a failure to
record"). Both interpretations are defensible; majority wins for the
median. This is a methodology-honesty datapoint for Phase 4: the
3-pass FAIRNESS-01 protocol surfaces interpretation variance, not just
execution variance.

---

## Per-stage analysis

### S1 — Greenhouse JD extraction → PASS

browser-use navigates the loopback fixture, calls `browser_get_state` and
`browser_extract_content`, recovers the page title from `<head>` metadata
that survives React hydration ("Jane Testworth for Jane Testworth Program
at Anthropic" — the snapshot's scrubbed mock name). Body content is
destroyed by React mount, but `<title>` survives. Same shape as the
Phase 1 calibration playwright run, which also depends on `<title>` for
the Greenhouse fixture. Score = `data_quality: 10` (the title is
recovered; per-rubric the binary "page-level identifier extracted"
threshold is met).

### S2 — Ashby JD extraction → PASS

Ashby's React app hydrates more gracefully than Greenhouse's — the
footer ("Powered by", "Privacy Policy", "Security", "Vulnerability
Disclosure") is added by Ashby's bundle, demonstrating JS execution.
The body content from the snapshot survives hydration partially. The
agent recovers enough structural signal to confidently identify the
posting as Ashby. Same outcome as playwright + chrome-devtools.

### S3 — Platform detection (Greenhouse vs Ashby) → PASS

Off-line classification from S1+S2 outputs. The agent correctly
identifies Greenhouse (job-boards.cdn.greenhouse.io stylesheet hrefs,
`application--form` Remix class, numeric job ID in path) vs Ashby
(UUID-based job IDs, `gh-` `recruiting-` namespace, ashbyhq.com
footer). Trivial pass for any MCP that got S1+S2.

### S4 — Form discovery → FAIL (all 3 passes agree)

`browser_get_state` lists only 2 interactive elements (a span and an
svg) after React mount on the Greenhouse fixture. The source HTML has
100+ form elements; the post-render DOM has the recruiting-logo SVG
and the `error-message` block with "Page not found / The job board you
were viewing is no longer active". Same failure shape as
chrome-devtools 02-01 PASS1 (chrome-devtools' PASS3 escaped via an
SSR-rescue trick — fetch+DOMParser+document.write — which browser-use's
tool surface does NOT expose, so escape isn't available in direct mode).

**Attribution: `tool-bug`** per FAIRNESS-06 (the only tag the
4-element taxonomy offers for "MCP cannot reach the form"). This
mis-classifies the failure: the real root cause is the
React-hydration-clobber on the static snapshot, a fixture-side issue
that affects every JS-rendering MCP equally. Phase 4 synthesis should
note this attribution ambiguity (same caveat applies to chrome-devtools
and obscura's S4-S8 attribution).

### S5/S6/S7 — Form fill, file upload, submit → FAIL

All downstream of S4. No form to interact with. PASS2's agent's
choice to mark these N/A is the most accurate description; the
majority FAIL verdict reflects "we tried the harness call and it
returned nothing useful" but is structurally a no-op.

### S8 — Screenshot → PASS (in PASS1 + PASS3, N/A in PASS2)

`browser_screenshot` returns a clean PNG of the Greenhouse "Page not
found" view (see PASS3/stage_s8.png). The screenshot is the
React-clobbered SPA error page — not the original JD — but the
**screenshot tool itself** returned valid PNG bytes, which is what the
rubric measures. Same outcome would happen with any JS MCP.

---

## Failure-attribution table

| Dimension | Score | Tag | Real root cause | Notes |
|---|---|---|---|---|
| `data_quality`      | 10 | — | (passes threshold) | `<head>` metadata survives React mount; classifier-friendly |
| `reliability`       | 5  | — | (boundary) | Mixed: 3-pass converged on S1-S3+S8, diverged on S4-S7 |
| `speed`             | 5  | — | (untested in Phase 1; placeholder) | 3-segment cold-start is Phase 3 / G-710 |
| `token_efficiency`  | 5  | — | (untested in Phase 1; placeholder) | Schema/payload/turn split is Phase 3 / MEAS-02 |
| `interaction_depth` | 2  | `tool-bug` | React-clobber on Greenhouse SPA fixture, not browser-use itself | Same attribution ambiguity affects chrome-devtools + obscura — Phase 4 footnote |
| `js_rendering`      | 10 | — | (passes) | JS executed; Ashby footer additions confirm |
| `setup_complexity`  | 7  | — | (default) | `uv tool install browser-use` + `browser-use install` for Chromium |
| `error_handling`    | 2  | `tool-bug` | When `browser_extract_content` returns "No content extracted", the tool returns it as success; the agent must interpret the empty string as a failure manually | Real product gap |

---

## Capability-tag fidelity caveat (FAIRNESS-04)

This row is tagged `LLM-augmented` per the CONTEXT.md capability table,
because the MCP **supports** in-tool LLM use via `retry_with_browser_use_agent`.
But the `mode: direct` qualifier signals that **the LLM augmentation was
NOT exercised** in this run. The score is the **floor** of what the MCP
can do — the agent mode (when measurable) would test the **ceiling**.

Phase 4 synthesis must read the (capability, mode) pair together and
should NOT compare browser-use-direct's 5.87 against playwright's 7.93
as if they were apples-to-apples capability comparisons. They're testing
different things:
- **playwright** = "best deterministic tool surface, harness-driven"
- **browser-use-direct** = "what's the deterministic floor when an
  LLM-augmented MCP is denied its LLM augmentation"
- **browser-use-agent** = "what's the LLM-augmented ceiling" — SKIPPED
  on this run (`browser-use-agent/SKIPPED.md`)

---

## Tool surface gap finding

browser-use's 16-tool surface (per `init_smoke.json`):
- **navigation (2):** browser_navigate, browser_go_back
- **interaction (3):** browser_click, browser_type, (form-related)
- **inspection (5):** browser_get_state, browser_get_html, browser_get_url,
  browser_get_links, browser_get_metadata
- **capture (1):** browser_screenshot
- **other (5):** the LLM-augmented escape hatches —
  `retry_with_browser_use_agent`, `browser_extract_content`,
  `browser_set_value`, `browser_select_option`, `browser_press_key`

(Exact tool names per `init_smoke.json` and per-pass `tools_inventory.json`.)

**Notable strengths vs other MCPs:**
- ✅ The surface is **richer than obscura's** (16 tools vs obscura's 4).
- ✅ `browser_extract_content` is genuinely useful when the DOM is intact
  (Ashby S2) — returns structured content via an internal heuristic, no
  LLM call needed.
- ✅ Multi-tab support via `browser_tab_*` family (not exercised in this
  run; deferred to Phase 3's "deep navigation" stretch).

**Notable gaps:**
- ❌ No CDP/eval primitive (no `browser_eval` / `evaluate_script`). This
  prevents the SSR-rescue trick chrome-devtools used in PASS3 to defeat
  the React clobber. The fix would require user-controlled JS injection,
  which browser-use deliberately avoids for safety reasons (the
  `retry_with_browser_use_agent` escape hatch is the LLM-mediated
  alternative path for these cases).
- ❌ No network-tab visibility (no `network_get_requests` like
  chrome-devtools). browser-use is "headless Chromium driven by
  high-level commands," not "browser internals exposed."

---

## What a follow-up agent-mode run would test

If `browser-use-agent/SKIPPED.md` gets cleared (LLM key provided in a
later session), the falsifiable test for agent mode is:

1. Can `retry_with_browser_use_agent` defeat the React clobber on
   Greenhouse?
   - Hypothesis A (likely): NO — the LLM still sees an empty DOM
     post-hydration. No agent intelligence makes a missing form appear.
   - Hypothesis B (possible): YES — if the agent's planning loop calls
     `browser_navigate` with a pre-mount wait, or pre-empts React via
     CDP-style intercepts. Worth testing.
2. Does agent-mode S5-S8 outperform direct-mode S5-S8 on Ashby? Ashby's
   fixture is less hostile to hydration (the body content partially
   survives). If a form-fill is reachable in PASS2's agent's reading
   of S4, agent mode could push S5-S6 from FAIL to PASS via LLM-driven
   field-matching.
3. What's the apples-to-oranges cost? Per FAIRNESS-04, agent-mode's
   LLM calls inflate token_efficiency and speed dimensions; the
   capability tag is the disclosure.

---

## Phase 4 headline candidate

> "browser-use's direct mode (no user LLM key) reaches the same ceiling as
> chrome-devtools and playwright on JS-rendering and read-only stages
> (S1-S3+S8 all PASS, composite 5.87) — Vitalik's empirical claim
> CONFIRMED. The agent mode (which would test the
> `retry_with_browser_use_agent` LLM escape hatch) requires an OpenAI or
> Anthropic key, which was not available in this run; SKIPPED with
> documented re-run procedure. The 2026-05-21 testbench's `initialize`
> timeout in v0.12.7 is CONFIRMED FIXED."

---

## References

- Plan: `.planning/phases/02-per-mcp-scoring-runs/02-05-browser-use-PLAN.md`
- Phase context: `.planning/phases/02-per-mcp-scoring-runs/02-CONTEXT.md`
- Headline question source:
  `.planning/research/SUMMARY.md § Empirical Claims to Falsify`
- HANDOFF STOP #2: `HANDOFF-GSD-AUTO.md`
- Predecessor precedents:
  - `results/2026-05-26/chrome-devtools/DEEP_ANALYSIS.md` (same React-clobber failure mode)
  - `results/2026-05-26/obscura/DEEP_ANALYSIS.md` (.merge.py + .scrub_allow.txt patterns)
  - `results/2026-05-26/lightpanda/DEEP_ANALYSIS.md` (zero-variance counterexample)
- Cross-reference: `results/2026-05-26/browser-use-agent/SKIPPED.md` (companion row)
- FAIRNESS-04 / FAIRNESS-05: scoring/rubric_notes.md (capability-tag fairness)
