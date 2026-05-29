---
phase: 1
plan: 06
subsystem: harness-foundation/evidence-stubs
tags: [harness, evidence-dir, version-lock, reproducibility, stubs]
dependency_graph:
  requires:
    - 01-04   # scripts/run_mcp_session.sh
    - 01-05   # aggregator + N/A wrapper consume the shape this plan locks
  provides:
    - tls.json / cold_start.json / stability.log stubs (locked deferred contract)
    - tools_inventory.json (real, per-MCP, 6-category breakdown)
    - versions.json + versions.lock.md (per-run reproducibility manifest)
    - MACHINE.md (per-run host + tooling summary)
    - tokens.json (turn-scope only; schema/payload deferred to Phase 3)
  affects:
    - scripts/run_mcp_session.sh   # extended with five post-Claude steps
    - Makefile                     # new `make versions` target
tech_stack:
  added:
    - "mcp.client.stdio (already in pyproject.toml as mcp>=1.16) — for tools/list probes"
    - "shasum -a 256 + hashlib fallback — binary SHA256 capture"
  patterns:
    - "deferred-marker stub files: {\"deferred\": \"<ticket>\", ...} — aggregator-compatible neutral score"
    - "two-file manifest (.json + .lock.md) generated from one dict — cannot drift"
    - "envsubst-from-versions.json: MACHINE.md placeholders pulled from versions.json single-source-of-truth"
key_files:
  created:
    - bench/stub_writers.py
    - bench/tools_inventory.py
    - bench/capture_versions.py
    - tests/test_stub_writers.py
    - tests/test_tools_inventory.py
    - tests/test_capture_versions.py
    - tests/test_run_mcp_session_evidence_dir.sh
    - templates/MACHINE.md
    - results/.gitkeep
  modified:
    - scripts/run_mcp_session.sh   # +5 post-session steps (13-18)
    - Makefile                     # +`make versions` target
decisions:
  - "Stubs use literal {\"deferred\": \"G-710\"} marker because the existing aggregator already recognizes this shape (see scripts/aggregate_scores.py _score_speed / _score_token_efficiency); no aggregator changes needed."
  - "tools_inventory uses 6 categories (navigation/inspection/interaction/capture/diagnostics/other) following chrome-devtools-mcp scheme."
  - "Failed tools_inventory writes the error to disk and exits non-zero but does NOT crash the harness — INITIALIZE_TIMEOUT is the failure mode the wave needs to surface."
  - "Lightpanda binary-vs-handshake mismatch is recorded in BOTH versions.json (binary_self_report + handshake_protocol_version + version_mismatch flag) AND versions.lock.md (a 'Version mismatches' section). Don't pick one."
  - "Strict fail-on-mismatch gate (versions.lock.md vs live env) deferred to Phase 4 REPRO-01 per plan's Out of Scope; Phase 1 logs only."
  - "tokens.json captures turn-scope only (from stream-json usage); schema/payload split deferred to Phase 3 MEAS-02 per CONTEXT.md."
  - "MACHINE.md template is envsubst-driven from versions.json — single source of truth for host/tooling fields, no possibility of drift between the two files."
metrics:
  duration_minutes: 35
  completed_date: 2026-05-25
---

# Phase 1 Plan 06: Evidence Stubs + Version Lock Summary

Closes the Phase 1 evidence-directory contract: every per-MCP run now writes the
full HARNESS-02 file set (transcript, raw_stream, stage_s\*, tools_inventory,
cold_start, tokens, tls, stability, orphan_audit) plus per-run reproducibility
artifacts (versions.json, versions.lock.md, MACHINE.md). Deferred dimensions
(TLS, full cold-start, stability soak) ship as `{"deferred": ...}` stubs so
plan 01-07's calibration gate sees a complete evidence dir.

## What Shipped

| File | Lines | Purpose |
| --- | --- | --- |
| `bench/stub_writers.py` | 248 | Emit canonical-shape stubs (tls.json, cold_start.json, stability.log) with `{"deferred": "G-710"}` markers. CLI refuses to clobber real measurement files; `--force` overrides. Atomic writes via `.tmp.<inode>` + rename. |
| `bench/tools_inventory.py` | 374 | Real measurement. Spawns each MCP via `mcp.client.stdio` (SDK 1.16), runs `initialize` + `tools/list`, categorizes every tool into 6 buckets, writes `tools_inventory.json`. 30 s total timeout. Three exit codes (1=INITIALIZE_TIMEOUT, 2=SPAWN_OR_RPC_ERROR, 3=MCP_CONFIG_ERROR). |
| `bench/capture_versions.py` | 449 | Reproducibility manifest. Two-file output (versions.json + versions.lock.md). Captures host (os/kernel/arch), tooling (claude/node/npm/python/uv), per-MCP (binary_path / sha256 / package_version OR binary_self_report). Flags lightpanda-style binary-vs-handshake mismatch. NO PII fields. |
| `tests/test_stub_writers.py` | 17 cases | Per-writer shape, CLI safety (refuse-to-clobber + --force + idempotency), `_is_deferred_stub` recognition. |
| `tests/test_tools_inventory.py` | 16 cases | Categorization keyword tables (7-MCP coverage), `.mcp.json` parsing, three failure-path tests, one live playwright spawn (skipped if binary missing). |
| `tests/test_capture_versions.py` | 21 cases | `_sha256_file` round-trip, `_which` ~/-collapsing, capture_host/tooling shape + no-PII assertions, `_collect_handshake_versions` scraping, `_capture_mcp` mismatch detection, render_markdown sections + mismatch block, CLI end-to-end. |
| `tests/test_run_mcp_session_evidence_dir.sh` | 6 sections | Always-runnable shell test that exercises every step the wrapper added without spawning Claude. Asserts file presence, JSON shape, MACHINE.md placeholder resolution, public-repo hygiene (no MacBook/iMac/`/Users/` patterns). |
| `templates/MACHINE.md` | template | envsubst-driven; placeholders pulled from versions.json. NO PII fields. |
| `scripts/run_mcp_session.sh` | +106 lines | Steps 13-18 added: tokens.json jq extraction, tools_inventory probe, stub_writers invocation, capture_versions (idempotent — once per date), MACHINE.md rendering, final missing-file audit (log-only). |
| `Makefile` | +12 lines | `make versions` target (regenerate manifest on demand). |
| `results/.gitkeep` | empty | Ensure the directory exists in fresh clones. |

## Acceptance Checklist (from PLAN.md)

- [x] `tools_inventory.json` for Playwright shows `tool_count >= 20` — measured **23** tools, distributed `{interaction: 11, diagnostics: 5, navigation: 2, capture: 1, inspection: 1, other: 3}`.
- [x] `tls.json` content is `{"deferred": "G-710", ...}` — the stub locks the directory contract.
- [x] `results/<date>/versions.json` exists and `versions.lock.md` is its human-readable twin — both written; live capture on this machine reports SHA256 for **7/7** MCPs and clean version numbers (browser-use=0.12.7, chrome-devtools=1.0.1, cloakbrowser=2.0.4, firecrawl=3.17.0, lightpanda=0.3.0, obscura=0.1.4-2, playwright=0.0.75).
- [x] Lightpanda binary-vs-handshake mismatch is recorded — `binary_self_report: "0.3.0"`, `handshake_protocol_version: "0.1.0"`, `version_mismatch: true`. Surfaced in versions.lock.md "Version mismatches" section.
- [x] Evidence-directory contract complete (transcript.md, raw_stream.jsonl, cold_start.json, tokens.json, tls.json, stability.log, orphan_audit.log, tools_inventory.json) — exercised via `tests/test_run_mcp_session_evidence_dir.sh`.

## Test Run Results

```
.venv/bin/python -m unittest discover tests
Ran 159 tests in 8.215s — OK

bash tests/test_run_mcp_session_evidence_dir.sh — PASSED
bash tests/test_secret_guard.sh — PASSED
bash tests/test_snapshot_serves.sh — PASSED
```

54 of the 159 unit tests are new in this plan (17 stub_writers + 16 tools_inventory + 21 capture_versions).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Discovered binary-version-flag inconsistency across the 3 binary MCPs**

- **Found during:** Task 4 acceptance smoke run.
- **Issue:** Initial assumption that `<binary> --version` works for lightpanda/browser-use/cloakbrowser was wrong — `lightpanda --version` errors out (correct flag is `lightpanda version` as a subcommand), and both `browser-use --version` and `cloakbrowsermcp --version` cause argparse to reject the unrecognized argument and print usage to stderr.
- **Fix:** Replaced the flat `BINARY_VERSION_FLAG` dict with `BINARY_VERSION_ARGV` (list-valued, can be a multi-token argv) plus `UV_TOOL_LIST_NAMES` and a new `_uv_tool_version()` helper that parses `uv tool list` output. For browser-use and cloakbrowser the version is now resolved via uv's installed-tool ledger.
- **Result:** SHA256 + clean version captured for **7/7 MCPs** on the test machine instead of 4/7.
- **Files modified:** `bench/capture_versions.py` only; existing tests updated to use the new constant name.
- **Commit:** 9564d86

### Out-of-scope discoveries (deferred via `deferred-items.md`)

None — everything found was scoped to plan 01-06.

## Deferred Issues

None — every acceptance criterion met and every plan task completed.

## Architectural Notes

- **The aggregator did NOT need changes.** `scripts/aggregate_scores.py` (shipped in plan 01-05) already recognizes `{"deferred": ...}` payloads and assigns the neutral mid-band score (5/10) for the affected dimensions. The plan-01-06 stubs are exactly the shape the aggregator expects. This is the "lock the contract" payoff that the deferral strategy is built around.
- **MACHINE.md is rendered from versions.json**, not captured independently. Single-source-of-truth means the two files cannot drift — a divergence between MACHINE.md and versions.json on the same date would indicate file-system corruption, not a real semantic mismatch. The strict gate at the bottom of Pitfall 10 (Phase 4 REPRO-01) operates on versions.lock.md vs versions.json, not MACHINE.md vs anything.
- **tools_inventory categorization is heuristic, by design.** The 6 buckets follow chrome-devtools-mcp's scheme; first-match-wins keyword tables are documented inline in `bench/tools_inventory.py`. The "other" bucket is the catch-all — for Playwright it catches `browser_close`, `browser_resize`, `browser_tabs` (session management), which we deliberately leave uncategorized rather than force into a poor-fit bucket. The JSON output flags every uncategorized tool so a human can spot-check during the wave-2 calibration.

## Threat Flags

None — this plan added no new network endpoints, no new auth paths, no schema changes at trust boundaries. The MCP spawn paths reuse the existing `bench.process_group.spawn_setsid` pattern (covered by the threat model in plan 01-02's process-hygiene work).

## Public-Repo Hygiene Verified

`tests/test_run_mcp_session_evidence_dir.sh` includes a public-repo hygiene block that asserts:
- No `MacBook|iMac|Mini` substrings appear in versions.json or MACHINE.md.
- No uncollapsed `/Users/` paths appear in either file.

This catches the obvious slips (hostname injection, absolute home-dir paths) at every harness invocation, not just at PR-review time.

## Self-Check: PASSED

All commits exist in git log (1880458, 401c55f, 9564d86, 9c5ac29). All files created/modified are present on disk. All tests pass (159 unit + 3 shell). Acceptance criteria all green.
