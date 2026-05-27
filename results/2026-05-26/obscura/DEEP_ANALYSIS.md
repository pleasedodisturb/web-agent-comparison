# obscura — Deep Analysis (2026-05-26)

**MCP:** `obscura-mcp` v0.1.4-2 (npm wrapper) wrapping a closed-source Rust+V8 engine binary self-reporting `Headless Browser v0.1.0` (CDP server on `ws://127.0.0.1:9222`)
**Capability tag:** `stealth-specialist`
**Mode:** `no-stealth-flag` (SAFETY-03 enforcement on macOS — see § "Stealth flag suppression")
**Median composite (3-pass, N/A-aware):** **3.27 / 10**
**Run dates:** 2026-05-26 (all 3 passes within a 15-minute window, 20:07–20:22 UTC)
**Linear ticket:** G-718 (obscura sub-ticket of G-703)

## Capability tag

`stealth-specialist` — obscura's market positioning and architectural choice is anti-detection: a CDP-direct (not Playwright-on-CDP) engine intended for scraping behind bot-detection layers. Same category as `cloakbrowser`; distinct from `playwright` / `chrome-devtools` (`tool-only`), `browser-use-agent` (`LLM-augmented`), and `firecrawl` (`cloud`).

The tag is honest about positioning, not about measurement. Phase 2's S1-S8 walk does NOT exercise bot-detection avoidance (that is deferred to G-710). The tag flags that obscura's competitive advantage lives outside the dimensions this phase scores.

## Stealth flag suppression (SAFETY-03)

Obscura's tool surface exposes a per-call `stealth` parameter, and the underlying engine supports a `--stealth` command-line flag. **Neither was enabled in this benchmark.** The reason:

- Per CLAUDE.md `## Conventions` + [`docs/external-findings/browser-tools-2026-05-21.md`](../../../docs/external-findings/browser-tools-2026-05-21.md) § SAFETY-03: enabling `--stealth` on macOS leaks `Sec-CH-UA-Platform-*` client hints emitted by the network stack, regardless of any JS-level User-Agent shim. Cloudflare cross-checks this. The MCP would be tagged `stealth: leaks` under SAFETY-03 — a methodology-honesty choice, not a workaround.
- Per `.mcp.json` (verified pre-flight): `obscura` entry has `command: "obscura-mcp"`, `args: []`. No `--stealth`. The harness `scripts/run_mcp_session.sh` invokes the entry verbatim — no override.

```bash
$ jq -r '.mcpServers.obscura' .mcp.json
{
  "command": "obscura-mcp",
  "args": []
}
$ jq -r '.mcpServers.obscura.args[]?' .mcp.json | grep -- '--stealth' || echo "SAFETY-03 OK"
SAFETY-03 OK
```

**Acceptable alternatives (deferred per CONTEXT.md `## Decisions § Claude's Discretion`):** run obscura in a Linux VM where Sec-CH-UA-Platform-* is honest, OR compare obscura's headers WITH and WITHOUT `--stealth` from a Linux host to characterize the leak surface. Both are G-710 / Phase 3 territory, not this wave.

**Phase 4 implication:** `recommendations.md` must NOT promote obscura to SECONDARY-tier toolkit graduation on the basis of "stealth-specialist" without first running the Linux comparison. On macOS, the stealth claim is conditional.

## Median composite & sub-rubric

| Dimension (weight) | Median | PASS1 | PASS2 | PASS3 |
|---|---|---|---|---|
| Data Quality (3×) | **0** | 3 | 0 | 0 |
| Reliability (3×) | **6** | 3 | 9 | 6 |
| Speed (2×) | **5** | 5 | 5 | 5 |
| Token Efficiency (2×) | **5** | 5 | 5 | 5 |
| Interaction Depth (2×) | **0** | 0 | 0 | 0 |
| JS Rendering (1×) | **2** | 2 | 5 | 2 |
| Setup Complexity (1×) | **7** | 7 | 7 | 7 |
| Error Handling (1×) | **2** | 2 | 2 | 2 |
| **Weighted Composite** | **3.27** | 3.27 | 4.07 | 3.27 |

Speed, Token Efficiency, and Setup Complexity are neutral mid-band values per the Phase-1 stub policy (cold_start.json + tokens.json are `{deferred: phase-3}`; Setup Complexity is locked at 7 until plan 01-07's successor measurement task). Same constants every MCP carries this wave.

**Median per pass (N/A-aware):** PASS1=3.27, PASS2=4.07, PASS3=3.27 — narrow band, indicating low PER-DIMENSION variance after accounting for the agent-strategy spread. The 4.07 PASS2 outlier is reliability=9 (only 1 stage attempted = 0 fails out of 1 attempt) rather than improved obscura performance; this is a numerator/denominator artifact of stopping at S1.

## Per-stage verdicts (3-pass majority)

| Stage | Median verdict | PASS1 | PASS2 | PASS3 | Why |
|---|---|---|---|---|---|
| S1 — Greenhouse extract | **FAIL** | PASS (degraded) | FAIL | FAIL | Pass 1 discovered the `0.0.0.0` SSRF-guard workaround; the resulting extraction was the React-hydrated "Page not found" component, not the SSR job content. Pass 2 and Pass 3 stopped at the loopback rejection. The DEGRADED Pass 1 was scored PASS by the aggregator (artifact present); 2-of-3 FAIL gives majority FAIL. |
| S2 — Ashby SPA extract | **FAIL** | FAIL (CDP wedge) | UNTESTED | FAIL | Pass 1 wedged the CDP target with a sync XHR (see §3); Pass 2 stopped at S1; Pass 3 hit the same loopback rejection. |
| S3 — Platform detection | **FAIL** | FAIL | UNTESTED | FAIL | Cannot detect without two extractions. |
| S4 — Apply-form snapshot | **FAIL** | FAIL | UNTESTED | FAIL | Wedge or loopback rejection. |
| S5 — Fill form | **FAIL** | FAIL | UNTESTED | NA | Pass 3 marked NA on the (correct) basis that obscura has no batch-fill primitive comparable to Playwright `browser_fill_form` — though `browse_interact(action="type")` would have worked element-by-element. |
| S6 — Upload resume | **FAIL** | FAIL | UNTESTED | NA | Obscura's tool surface (4 tools, see `tools_inventory.json`) has NO file-upload primitive. NA on capability grounds is the honest verdict; FAIL via cascade is the aggregator's. |
| S7 — React-Select dropdown | **FAIL** | FAIL | UNTESTED | NA | Eval-driven React-Select pattern IS viable via `browse_session.evaluate` but the form never loaded. |
| S8 — Screenshot | **FAIL** | FAIL | UNTESTED | NA | Obscura's tool surface has NO screenshot primitive. NA on capability grounds is the honest verdict. |

**Tool calls per pass:** PASS1 ≈ 20+ (CDP-wedge recovery attempts), PASS2 ≈ 5, PASS3 ≈ 10.
**Wall-clock:** PASS1=8m58s (the wedge ate ~6 minutes of useless retry), PASS2=2m18s, PASS3=2m05s. Median = 2m18s. None exceeded the 60-minute budget.

## Pass-to-pass variance — the load-bearing finding (same shape as chrome-devtools)

Three passes against an identical MCP/fixture/harness produced three different stage trajectories. The variance is in the **driving agent**'s discovery and inference, NOT in obscura itself:

- **PASS 1** (the optimist): tried `127.0.0.1` → got rejected → tried `localhost` → got rejected → tried `[::1]` → got rejected → tried `0.0.0.0` → it slipped through. Then ran S1 against `0.0.0.0:8765/greenhouse_2026-05-22/...`, got the React-hydrated 404 component (Greenhouse bundle attempted to fetch the live API for the snapshotted job ID, failed, replaced the body). Tried to extract raw SSR HTML via `eval`; first attempt (`async fetch`) returned literal string "Promise" because obscura's eval pipeline does not await thenables; second attempt (sync XHR) **wedged the CDP target permanently** for the remaining 6 minutes of the session.
- **PASS 2** (the conservative): hit the `127.0.0.1` rejection, inferred (incorrectly) that obscura is cloud-hosted like firecrawl, stopped at S1 per the prompt's "STOP if you cannot complete a stage" instruction. Did NOT discover `0.0.0.0`.
- **PASS 3** (the systematic): hit the `127.0.0.1` rejection, also concluded obscura was cloud-routed, walked S1-S4 marking each FAIL, then correctly marked S5-S8 as NA on capability grounds (no batch-fill, no upload, no screenshot primitive in obscura's 4-tool surface).

**The MCP is the same in all three runs. The agent's strategy differed.** This is the same finding chrome-devtools surfaced in plan 02-01 — agent-discovery-dependent outcomes. **A single-pass result for obscura could plausibly have landed at any of {3.27, 4.07, 3.27} depending on which session was sampled.** The 3-pass median (FAIRNESS-01 protocol) is what makes this row honest.

**Net diagnosis (independent of agent variance):** obscura's *true* surface-vs-harness compatibility is somewhere between PASS 1 and PASS 3:
- It IS reachable via `0.0.0.0` (Pass 1 proves this).
- It IS a local Chromium engine, NOT a cloud worker (the bundled binary + CDP server on `127.0.0.1:9222` prove this — see INSTALL_LOG.md).
- It WOULD score better if the harness bound the fixture server to a non-private IP — but the SSRF block is by design (anti-SSRF for the cloud product use-case) and the rubric is fixed.
- Pass 1's S1 PASS-but-degraded outcome would have repeated in Passes 2 and 3 if their agents had found `0.0.0.0`, BUT the wedge would also have repeated for Pass 1's sync-XHR attempt or any equivalent — the stability defect is real.

## The falsifiable empirical finding — CDP-direct memory footprint

Per `.planning/research/SUMMARY.md § Empirical Claims to Falsify`:

> Claim: "obscura — CDP-direct (not Playwright-on-CDP) gives lower overhead +
>         ~30MB RAM vs Playwright ~300MB while keeping full JS rendering"

**Memory measurement (from `MEMORY_SNAPSHOT.txt`, 20 samples × 10s interval during PASS 1):**

| Statistic | Obscura RSS | Claim | Verdict |
|---|---|---|---|
| Min (just-spawned) | 6,720 KB (6.6 MB) | — | — |
| Mean (steady state) | 33,137 KB (32.4 MB) | ~30 MB | **SUPPORTED** (within 10%) |
| Max (during S1 nav+eval) | 59,152 KB (57.8 MB) | ~30 MB | **EXCEEDED** (~2× under load) |
| Implicit Playwright comparison | — | ~300 MB | NOT MEASURED THIS WAVE (cf. G-710) |

**Verdict on the memory claim:** PARTIALLY SUPPORTED. Steady-state matches the published "~30 MB" number; peak load is ~2× higher. Still ~5× smaller than the unverified Playwright "~300 MB" baseline, which a fair test requires measuring directly (Phase 3 / G-710).

**Caveat — measurement is the wrapper, not the engine:** the `ps`-measured PID 57077 is `node /opt/homebrew/lib/node_modules/obscura-mcp/bin/obscura serve`, the Node-wrapper process. The actual Chromium worker backing the CDP server (port 9222) has its own RSS not reflected in the wrapper number. The *total architecture footprint* is HIGHER than 57.8 MB. The 30 MB figure in the research summary is itself ambiguous about scope — it should be re-stated as "wrapper RSS" if it applies, or re-measured to include the Chromium worker if "architectural footprint" is the claim.

**Verdict on the "full JS rendering" claim:** SUPPORTED.
- S1 explicitly triggered the Greenhouse React bundle (clobbered SSR with a "Page not found" component — see §3 below).
- The bundle executed. obscura is NOT JS-light like lightpanda; it runs a real Chromium under the CDP server.
- The Ashby SPA stage (S2) failed for a different reason (CDP target wedge), NOT because JS didn't run.

**Cross-reference:** Playwright's row at 7.93 (`results/2026-05-25/playwright/`) demonstrates the JS-rendering ceiling with the same harness. Direct memory comparison is deferred. The obscura row's S2 FAIL is on stability, not JS capability.

## Surface gaps that are obscura's, not the agent's

Independent of the agent-variance + SSRF-guard story, obscura's tool surface is **structurally narrow**:

- 4 tools total: `browse_page`, `browse_interact`, `browse_session`, `browse_scrape`
- **No screenshot primitive.** S8 is uncompletable on obscura's surface, period.
- **No file-upload primitive.** S6 is uncompletable on obscura's surface, period.
- **No batch-fill primitive** (no Playwright-style `browser_fill_form`). S5 would have to be done element-by-element via `browse_interact(action="type")` × 6 calls.
- **`eval` has no async path.** Async functions returned as literal string "Promise" rather than resolved values. Workarounds require sync XHR or DOM mutation — both fragile.
- **Sync XHR wedges the CDP target** with no client-side reset primitive. A single bad eval call permanently disables the MCP for the remainder of the session.

If obscura is graduated to the toolkit (Stage 2), these surface gaps need to be either (a) accepted with documented workarounds for upload + screenshot, OR (b) addressed by the maintainer. Neither path is unblocked by this Phase-2 row.

## Failure-attribution table

Sub-rubric cells scoring < 5 in the median row, each tagged per `bench/failure_taxonomy.py`:

| Dimension | Score | Tag | Justification |
|---|---|---|---|
| `data_quality` | 0 | `tool-bug` | 2-of-3 passes failed S1-S3 outright; PASS 1 returned the React-hydrated 404, not actual job data. Root cause is a mix of: (a) the engine's SSRF guard refusing 127.0.0.1, (b) Greenhouse's React bundle clobbering SSR on cache-miss, (c) obscura's lack of a "disable JS before navigate" option to bypass the clobber. (a) and (c) are MCP-side; (b) is target-side. The taxonomy's 4-tag system collapses them to `tool-bug` — see this row for the breakdown. |
| `interaction_depth` | 0 | `tool-bug` | S4-S8 PASS rate is 0/15. PASS 1 wedged at S2 before reaching interactive stages; PASS 2 stopped at S1; PASS 3 hit the loopback rejection at S4. *Independent* of the harness-incompatibility, S6 (upload) and S8 (screenshot) are uncompletable on obscura's tool surface — a structural capability gap, not a fault. Tag is `tool-bug` per FAIRNESS-06 aggregator default. |
| `js_rendering` | 2 | `tool-bug` | S2 (Ashby React SPA) failed in 2-of-3 passes due to CDP wedge (PASS 1) and SSRF rejection (PASS 3). Obscura *can* render JS (proved in PASS 1 S1 by the React bundle clobbering SSR), so this score is misleading: the dimension grades "did S2 produce a rendered DOM?" not "can the engine render React?". The honest read is "JS rendering capability is present but unreachable through the harness on this fixture." Tag is `tool-bug` because the failure is in the obscura↔harness coupling, not in the Chromium runtime. |
| `error_handling` | 2 | `tool-bug` | The transcript heuristic counts `error|retry|fail` lexemes; the 3 transcripts collectively contain dozens of "Network error" / "FAILED" / "wedge" mentions. PASS 2's transcript alone has ~12 such hits. Same root cause as `data_quality` — not an independent MCP defect. |

All four tags trace to a single root cause chain (SSRF-guard incompatibility → agent-strategy variance in finding `0.0.0.0` → CDP wedge on the agent's recovery attempt). Not four independent obscura bugs.

## XHR-silent-fail status — claim refuted (different failure mode)

The plan flagged a "known in-page-fetch silent-fail" — i.e. obscura sometimes drops in-page-initiated fetch responses. **This was NOT observed in any of the 3 passes.** What was observed was different:

- **PASS 1's wedge** was a CDP-target failure (`CDP request timed out: Target.createTarget`) triggered by a SYNCHRONOUS XHR in eval blocking the renderer thread. That's a different bug class — sync XHR + CDP coordinator is the bad pattern, not async fetch silently dropping responses.
- Async `fetch` in eval returned the literal string "Promise" (not silently dropping — explicitly returning the unresolved value). Also a different bug.

If the "silent in-page-fetch fail" is real, it lives somewhere the S1-S8 walk did not exercise. Phase 4 should NOT cite obscura with this attribution unless a follow-up wave reproduces it.

## SSRF guard — methodology-vs-product mismatch (key Phase-4 finding)

The dominant signal across all 3 passes was obscura's hardcoded refusal of `127.0.0.1`, `localhost`, and `[::1]`. This is **not a bug** — it is anti-SSRF policy for obscura's cloud-product use case (preventing users from scraping internal AWS metadata endpoints, etc.). It IS a methodology mismatch with this benchmark, which serves fixtures on loopback to maximize reproducibility.

**Three possible Phase-4 responses, in increasing cost:**

1. **Document and move on (recommended).** The harness uses loopback for reproducibility; obscura's market is public-internet scraping; the SSRF block surfaces an honest mismatch. Phase 4 `recommendations.md` cites obscura's row with this caveat. Cost: zero.
2. **Re-bind the fixture server to a non-private LAN IP.** Would let obscura through but breaks the "anyone can clone and run" reproducibility promise for users behind NAT. Cost: moderate.
3. **Run an obscura-specific PASS variant against the same fixtures hosted publicly.** Would let obscura score on a fair surface but breaks the apples-to-apples comparison with other MCPs. Cost: high (need to host public fixtures, ensure version-frozen).

Per CONTEXT.md `## Decisions § Pragmatic concession`, option 1 is the wave's response.

## Wall-clock budget posture

| | Time |
|---|---|
| PASS1 wall-clock | 8m58s (538s) |
| PASS2 wall-clock | 2m18s (138s) |
| PASS3 wall-clock | 2m05s (125s) |
| Total (3 passes) | 13m21s (801s) |
| Budget per pass | 60m |
| Single-pass fallback invoked? | **No** |

PASS 1's wall-clock is dominated by the post-wedge retry loop (~6 minutes of `Target.createTarget` timeouts). PASS 2 and PASS 3 were short because the agents stopped at S1 per the prompt instruction.

## Tools inventory snapshot

From `tools_inventory.json` (probed via `mcp.client.stdio` after PASS 1):

| Category | Count | Tools |
|---|---|---|
| interaction | 0 | (none) |
| diagnostics | 0 | (none) |
| inspection | 1 | `browse_scrape` |
| navigation | 0 | (none) |
| capture | 0 | (none) |
| other | 3 | `browse_page`, `browse_interact`, `browse_session` |
| **TOTAL** | **4** | |

`browse_interact` is mis-categorized as `other` rather than `interaction` (it does click/type). The categorizer in `bench/tools_inventory.py` heuristics on tool name — `browse_*` doesn't match its `interaction` predicate. Minor noise; the count is what matters: 4 tools total, vs chrome-devtools' 29, vs playwright's ~30.

**Interesting**: every tool exposes a `stealth` parameter in its input schema (`browse_page`, `browse_interact`, `browse_session`-via-create). The per-call stealth knob is what SAFETY-03 disables on macOS, separate from any engine-level `--stealth` flag.

## Linear ticket

Per CONTEXT.md `## Decisions § Execution Order`, this row belongs under sub-ticket **G-718** (obscura split of G-703). A summary comment referencing this DEEP_ANALYSIS.md + the 3.27 median composite + the SAFETY-03 enforcement + the CDP-direct memory-footprint finding will be posted via `linearis comments create G-718`.

## Sources

- `results/2026-05-26/obscura/PASS{1,2,3}/` — per-pass evidence (transcripts, raw_stream, stage artifacts)
- `results/2026-05-26/obscura/PASS{1,2,3}.json` — per-pass aggregated rows
- `results/2026-05-26/obscura/INSTALL_LOG.md` — engine install attempt outcome (success; wrapper 0.1.4-2, engine 0.1.0, binary SHA256 captured)
- `results/2026-05-26/obscura/MEMORY_SNAPSHOT.txt` — 20-sample RSS trace during PASS 1
- `results/2026-05-26/obscura/tools_inventory.json` — 4-tool inventory probe
- `results/2026-05-26/scores.json` — median row alongside playwright/chrome-devtools/lightpanda/firecrawl
- `results/2026-05-26/obscura/.composite_check.txt` — `score_with_na.py` output

**Sacrosanct check:** `scoring/score.py` byte-for-byte unchanged
(`git diff main -- scoring/score.py | wc -l` must return 0; verified in SUMMARY).
