---
phase: 03-cross-cutting-measurements
plan: 03
subsystem: measurement
tags: [cold-start, mcp-stdio, perf_counter_ns, pkill, median, python]

requires:
  - phase: 01-harness-foundation
    provides: "mcp.client.stdio probe pattern in bench/tools_inventory.py; cold_start.json deferred-marker stub contract"
  - phase: 03-cross-cutting-measurements/02
    provides: "v0.12.7 browser-use initialize-timeout fixed (confirmed in 03-01); tokens.json 3-scope shape unaffected"
provides:
  - "bench/measure_cold_start.py module + pytest suite (13 tests)"
  - "3-segment median cold + warm samples for all 7 MCPs (8 rows incl. browser-use-agent variant)"
  - "Phase-1 deferred cold_start stubs overwritten with real OK measurements"
  - "Makefile cold-start[-<mcp>] targets (N_RUNS overridable)"
affects: [phase-4-synthesis, scoring-speed-dimension, recommendations-md]

tech-stack:
  added: ["statistics.median for cross-sample aggregation"]
  patterns:
    - "Inject-the-coroutine-factory test seam pattern (test surface for async timing)"
    - "PKILL_PATTERNS allowlist + skip-flag safety contract for destructive sub-shell ops"
    - "Cold+warm sweep pattern: cold = pkill+sleep before each sample, warm = no pkill"

key-files:
  created:
    - "bench/measure_cold_start.py"
    - "tests/test_measure_cold_start.py"
    - "results/2026-05-26/playwright/cold_start.json"
    - "results/2026-05-26/cloakbrowser/cold_start.json"
    - "results/2026-05-26/browser-use-direct/cold_start.json"
    - "results/2026-05-26/browser-use-agent/cold_start.json"
  modified:
    - "Makefile (cold-start targets, help text)"
    - "results/2026-05-26/chrome-devtools/cold_start.json"
    - "results/2026-05-26/firecrawl/cold_start.json"
    - "results/2026-05-26/lightpanda/cold_start.json"
    - "results/2026-05-26/obscura/cold_start.json"

key-decisions:
  - "Approximated t_resolve as stdio_client.__aenter__ duration (the SDK doesn't expose first-byte-of-stdout); documented in metadata.timing_decomposition."
  - "Cache eviction = process_only (pkill -f + 200ms sleep). Sudo purge not invoked per global constraint and 03-CONTEXT.md."
  - "browser-use-agent variant shares the direct binary's cold_start.json (same spawn path); divergence is at agent-session time, not at MCP init."
  - "Per-run timeout 30s matches tools_inventory.py; failure rows preserve sample-list shape so partial failures yield a valid median over remaining samples."
  - "PKILL_PATTERNS is an allowlist enforced by Test 5; substrings cannot match python/bash/.venv to prevent harness self-immolation."

patterns-established:
  - "Three-anchor async-timing decomposition (open_streams → initialize → list_tools) usable for future MCP performance benchmarks"
  - "Cold/warm dual-sweep pattern: median of N each, single JSON file, status=OK iff at least one sample in either scope succeeded"

requirements-completed: [MEAS-01]

duration: 41min
completed: 2026-05-26
---

# Phase 3 Plan 03: Cold-Start Measurement Summary

**3-segment cold + warm spawn-time medians for all 8 MCP rows via `mcp.client.stdio` + `time.perf_counter_ns`, overwriting Phase-1 deferred stubs.**

## Performance

- **Duration:** ~41 min (TDD RED+GREEN ~25 min, sweep + summary ~16 min)
- **Started:** 2026-05-26T22:48:00Z
- **Completed:** 2026-05-26T23:29:00Z
- **Tasks:** 2 (Task 1 TDD with 13 tests; Task 2 Makefile + 8-MCP sweep)
- **Files modified:** 11 (2 created code + 9 cold_start.json + Makefile)

## Accomplishments
- MEAS-01 satisfied — every MCP has a 3-segment cold + warm median measurement.
- `bench/measure_cold_start.py` is a reusable, test-driven measurement module (13/13 tests pass; 216/216 suite-wide).
- Cold-vs-warm delta is empirically tiny (±5 ms across every MCP) — important finding for the Phase-4 narrative that process-only cache eviction is not the dominant cost factor.
- Phase-4 Speed dimension now has real numbers for every row instead of the neutral 5 the aggregator was scoring against deferred stubs.

## Task Commits

1. **Task 1 RED — tests for measure_cold_start** — `301c090` (test)
2. **Task 1 GREEN — bench/measure_cold_start.py implementation** — `271904c` (feat)
3. **Task 2 — Makefile target + 8-MCP cold_start.json sweep** — `807052a` (feat)

## Findings Matrix

Per-MCP 3-segment medians (5 runs cold + 5 runs warm), ms — sorted by cold total ascending:

| MCP                  | t_resolve | t_spawn  | t_first_useful | **cold total** | warm total | delta (cold − warm) |
|----------------------|----------:|---------:|---------------:|---------------:|-----------:|--------------------:|
| **lightpanda**       |       3   |      10  |             1  |         **13** |        12  |              **+1** |
| **obscura**          |       3   |     154  |             1  |        **158** |       158  |               **0** |
| **firecrawl**        |       2   |     164  |             6  |        **171** |       169  |              **+2** |
| **playwright**       |       3   |     189  |             3  |        **197** |       198  |              **−1** |
| **cloakbrowser**     |       2   |     232  |             1  |        **235** |       240  |              **−5** |
| **chrome-devtools**  |       3   |     352  |             3  |        **358** |       361  |              **−3** |
| **browser-use-direct** | 3       |     665  |             1  |        **668** |       671  |              **−3** |
| **browser-use-agent**  | 3       |     665  |             1  |        **668** |       671  |              **−3** |

(`browser-use-agent` shares the `browser-use-direct` measurement: identical MCP binary, identical spawn path; divergence only at agent-session time. Metadata note flags the shared-spawn provenance.)

## Headline Findings

1. **Lightpanda is ~50× faster cold than browser-use (13 ms vs 668 ms).** Zig binary with no JS runtime warmup beats Python-based MCPs by an order of magnitude. This is the strongest single-dimension signal in Phase 3 so far.
2. **`t_spawn` (initialize) dominates the budget for every MCP.** `t_resolve` is 2–3 ms across the board (Python SDK overhead); `t_first_useful` (list_tools) is 1–6 ms. The entire variance comes from the MCP server's own initialize handler.
3. **Cold ≈ warm within ±5 ms.** Process-only cache eviction (pkill + 200 ms sleep) does NOT meaningfully exercise the OS file cache — the binaries are already mmap'd in kernel buffers. True uncached-filesystem cold-start would require `sudo purge` (deferred to G-710). The Phase-4 narrative should treat the "warm" column as the reproducible reference number, not a separate signal.
4. **browser-use cold-start is 668 ms median.** Heavy Python + uv import chain. The v0.12.7 initialize-timeout bug reported 2026-05-21 is confirmed fixed (10/10 runs succeeded without TimeoutError).
5. **chrome-devtools is 358 ms.** This number excludes Chrome's own launch (the MCP server attaches to a `--remote-debugging-port` instance); Chrome warmup is paid once per session, not per cold-start.
6. **firecrawl cold-start is 171 ms** — the LOCAL Node-process spawn of `firecrawl-mcp`. It does NOT include the cloud roundtrip; that's a payload-time cost not a spawn-time cost, and the methodology disclosure in `metadata.notes` makes this explicit.

## Cold-vs-Warm Delta Analysis

The largest absolute delta is **cloakbrowser at −5 ms** (warm SLOWER than cold). With n=5 each and 1-ms resolution, deltas of this magnitude are within noise. **No MCP showed a >10 ms cold-vs-warm gap.** The honest published finding: process-only cache eviction yields no measurable difference on macOS arm64.

## Decisions Made
- **t_resolve approximation:** The MCP Python SDK doesn't expose a "first byte of stdout" hook; we approximate as `stdio_client.__aenter__` duration. Documented in `metadata.timing_decomposition` for every output file. Faithful enough for cross-MCP comparison.
- **No sudo purge:** Per global constraint and 03-CONTEXT.md, cache_eviction stays at "process_only". Cold-vs-warm finding above shows this is the dominant honesty issue; preserved as a deferred item.
- **browser-use shared-spawn copy:** browser-use-agent's cold_start.json is a copy of browser-use-direct's with `metadata.mode` annotation. Avoids spawning the same binary twice for an identical measurement.
- **Per-run timeout 30s:** Matches `tools_inventory.py` precedent; the only MCP that historically wedged was browser-use < 0.12.7 (now fixed). 60s would be silly given the slowest observed cold was 668 ms.

## Deviations from Plan
None — plan executed as written. Test 5's pkill safety contract (allowlist + skip flag + no python/bash/.venv) was added preemptively per the plan's stop_conditions about "pkill matches our own python process by accident"; that's the spec, not a deviation.

## Issues Encountered
- **Cloakbrowser disconnection during the run:** Bash tool reported `cloakbrowser MCP disconnected` after the cold-start sweep killed its background process group. Harmless — the cold-start tool intentionally pkills between samples, and the disconnection is the cloakbrowser MCP-host shim noticing the kill. No impact on measurement; samples completed cleanly.

## Self-Check: PASSED

**Files exist:**
- FOUND: `bench/measure_cold_start.py`
- FOUND: `tests/test_measure_cold_start.py`
- FOUND: 8/8 `results/2026-05-26/<mcp>/cold_start.json` (playwright, browser-use-direct, browser-use-agent, chrome-devtools, firecrawl, lightpanda, obscura, cloakbrowser)
- FOUND: Makefile `cold-start[-<mcp>]` targets

**Commits exist:**
- FOUND: `301c090` (RED)
- FOUND: `271904c` (GREEN)
- FOUND: `807052a` (sweep)

**Tests pass:** 216/216 (was 203/203 pre-plan; +13 cold-start tests)

**scoring/score.py + scores.json:** byte-for-byte unchanged (`git diff` confirms).

## Next Plan Readiness

Plan 03-04 (60min stability soak) and Plan 03-05 (cross-cut synthesis) are unblocked.

- The 3-segment data is in a stable JSON shape that Phase 4's matrix consumer can read with `d['cold']['median']['total_ms']` (headline) or per-segment if needed.
- `metadata.notes` in every file flags the methodology caveats so the eventual `recommendations.md` doesn't have to re-derive them.
- One Phase-1 deferred dimension (Speed/cold-start) is now genuine; three remain (Stability via 03-04, Setup Complexity heuristic, Error Handling heuristic).

---
*Phase: 03-cross-cutting-measurements*
*Completed: 2026-05-26*
