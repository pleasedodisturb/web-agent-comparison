---
phase: 3
plan: 02
subsystem: cross-cutting-measurements/token-efficiency-3-scope
tags: [meas-02, aggregation, raw-stream, anthropic-sdk, count-tokens, headline-column]
dependency_graph:
  requires:
    - 01-06   # bench/tools_inventory.py — schema-scope input
    - 02-XX   # Phase 2 raw_stream.jsonl evidence per MCP × pass
    - 03-01   # tools_inventory.json gap-fill landed there
  provides:
    - bench/measure_tokens.py                          # MEAS-02 3-scope aggregator
    - tests/test_measure_tokens.py                     # 10 tests
    - results/2026-05-26/<mcp>/tokens.json             # 8 files overwritten
  affects:
    - Phase 4 synthesis (consumes headline_payload_bytes as the Token
      Efficiency column; 3-unit methodology note prevents conflation)
tech_stack:
  added: []  # uses already-installed anthropic 0.49 + stdlib
  patterns:
    - "3-scope split: schema (Anthropic-tokenizer), payload (byte count), turn (actual billing). Methodology note in every tokens.json's notes array so Phase 4 can't conflate units."
    - "Headline column = median_total_payload_bytes (sum of per-stage medians, excluding the noisy 'unattributed' bucket). Single integer per MCP for the matrix."
    - "Write-marker stage attribution mirrors 03-01 inclusive convention. Bytes attribute to the stage of the next Write marker; bytes seen before the first marker land in 'unattributed' (excluded from headline)."
    - "browser-use deduplication: schema_tokens is the SAME number for direct + agent (same tools/list); compute once, copy. Payload + turn diverge by mode."
    - "Stub-overwrite contract: existing Phase-1 tokens.json carries a captured 'turn' block; the aggregator reuses it when a pass's raw_stream lacks the result envelope. Deferred key removed on success."
key_files:
  created:
    - bench/measure_tokens.py
    - tests/test_measure_tokens.py
    - results/2026-05-26/playwright/tokens.json
    - results/2026-05-26/browser-use-direct/tokens.json
    - results/2026-05-26/browser-use-agent/tokens.json
    - results/2026-05-26/cloakbrowser/tokens.json
  modified:
    - results/2026-05-26/chrome-devtools/tokens.json     # deferred → OK
    - results/2026-05-26/firecrawl/tokens.json           # deferred → OK (payload=0; honest)
    - results/2026-05-26/lightpanda/tokens.json          # deferred → OK
    - results/2026-05-26/obscura/tokens.json             # deferred → OK
decisions:
  - "Headline column = median_total_payload_bytes excluding 'unattributed' bucket. 03-01 SUMMARY documented that early-crash leakage pollutes 'unattributed'; keeping it out of the headline prevents that noise from corrupting Phase 4's matrix ranking."
  - "ANTHROPIC_API_KEY absent at execution time → ran with --skip-schema; schema_tokens null on every row, note recorded in tokens.json. Re-runnable when the key is set; payload + turn data is unaffected by the skip."
  - "Firecrawl payload = 0 is the HONEST number, not a bug. Phase 2 captured only FAILED stage markers for firecrawl (cloud API can't reach loopback fixtures); no Claude session ran for it, so there is no raw_stream.jsonl to parse. Recording 0 mirrors 03-01's tool_call_counts=0 finding and surfaces the env-mismatch in Phase 4."
  - "Playwright status=NO_EVIDENCE — its PASS dirs live at results/2026-05-25/, not 2026-05-26/. The 03-01 SUMMARY surfaced the same gap; pointing the aggregator at the older date is not the right fix because Phase 4 expects all MCPs in one date dir. The Phase 4 synthesis (03-05) must decide whether to backfill (one harness re-run) or mark the cell evidence: pending."
  - "Cloakbrowser S5 payload = 6,657 bytes is 10-13x heavier than the next-highest scored MCP at the same stage. Matches the 03-01 finding that cloakbrowser ran cloak_type×4 + cloak_evaluate×1 at S5 (per-field type pattern + screenshot envelope around it). Phase 4 should annotate this as the falsifiable-claim foil for Playwright's batch-fill once 03-01's NO_EVIDENCE is closed."
metrics:
  duration_minutes: 25
  completed_date: 2026-05-27
---

# Phase 3 Plan 02: Token Efficiency 3-Scope Split Summary

A stdlib + anthropic-SDK aggregator that recovers MEAS-02 (token efficiency
split across **schema** / **payload** / **turn** scopes) from existing Phase 2
evidence. Overwrites the Phase 1 `tokens.json` stubs. Surfaces the published
**headline_payload_bytes** column for Phase 4's matrix while preserving the
three-unit methodology note so readers don't conflate Anthropic-tokenized
schema, byte-counted payload, and Claude-billed turn into one number.

## What was built

### bench/measure_tokens.py (MEAS-02)

CLI: `python -m bench.measure_tokens <RESULTS_DATE_DIR> [--mcp NAME] [--model M] [--skip-schema]`

For each per-MCP subdirectory under the date dir:

1. **payload scope** — walks `PASS{1,2,3}/raw_stream.jsonl`, sums
   `len(json.dumps(input).encode())` for every `tool_use` and
   `len(json.dumps(content).encode())` for every `tool_result`. Stage
   attribution uses Write-marker boundaries (same `stage_s<N>.<ext>` regex
   as 03-01); bytes seen before the first marker land in `"unattributed"`
   and are excluded from the headline.
2. **turn scope** — extracts the last `{type:"result"}` envelope's `usage`
   block from each pass. Falls back to the existing stub's captured turn
   block if a pass's raw_stream lacks the envelope (stub-overwrite contract).
3. **schema scope** — once per MCP: converts `tools_inventory.json` to
   Anthropic's `tools=` schema shape (empty property dicts because the
   Phase-1 probe captured key names only, not types — count_tokens still
   tokenizes the JSON-stringified schema faithfully) and computes
   `schema_tokens = count_tokens(tools=schema) - count_tokens(tools=None)`.
   Per Plan 03-02 stop_conditions: 3 attempts × 2/4/8s backoff on failures.
   `--skip-schema` or `ANTHROPIC_API_KEY` absent → null with a note.
4. **browser-use deduplication** — `schema_tokens` for `browser-use-agent`
   is copied from `browser-use-direct` (same `tools/list` surface; mode
   diverges at session runtime, not at handshake).

Output shape per tokens.json:

```json
{
  "mcp": "<name>",
  "captured_at": "...",
  "status": "OK | SKIPPED | NO_EVIDENCE",
  "scope": "schema+payload+turn",
  "schema_tokens": <int|null>,
  "schema_source": "anthropic.count_tokens",
  "schema_model": "claude-opus-4-7",
  "schema_baseline_tokens": <int|null>,
  "schema_with_tools_tokens": <int|null>,
  "payload_bytes_per_stage": {"PASS1": {"S1": N, ...}, ...},
  "median_payload_bytes_per_stage": {"S1": N, ...},
  "median_total_payload_bytes": N,
  "turn_tokens_per_pass": {"PASS1": {"input_tokens": N, "output_tokens": N, ...}, ...},
  "median_turn_input_tokens": N,
  "median_turn_output_tokens": N,
  "headline_payload_bytes": N,
  "notes": ["schema = Anthropic-tokenizer-counted; payload = byte-count; turn = actual Claude billing — three units, do not conflate.", ...]
}
```

### tests/test_measure_tokens.py

10 tests covering all six behavior contracts from the plan:

| # | Test | What it locks down |
|---|------|--------------------|
| 1 | `test_two_tool_uses_and_two_results` | Payload bytes sum ≥ the four JSON-stringified payloads |
| 2 | `test_payload_bytes_attributed_per_stage` | Write-marker boundaries correctly route bytes into S1/S2 |
| 3 | `test_recovers_usage_block_intact` | `extract_turn_usage_from_jsonl` pulls the result envelope's usage as-is |
| 4 | `test_no_result_envelope_returns_none` | Absent envelope → None (caller handles fallback) |
| 5 | `test_build_tools_schema_uses_inventory_keys` | inventory → Anthropic tools-schema conversion preserves names + keys |
| 6 | `test_schema_count_via_mock` | Mocked `count_tokens_fn` injected; both baseline + with-tools calls; schema = delta |
| 7 | `test_median_payload_three_passes` | Median for S1 = [100,200,300] is 200 |
| 8 | `test_median_missing_stage_treats_as_zero` | Missing-stage-in-pass = 0 for median (03-01 convention) |
| 9 | `test_skipped_md_only` | SKIPPED.md → status=SKIPPED, **zero count_tokens calls** |
| 10 | `test_existing_stub_turn_reused` | Phase-1 stub's `turn` block reused when raw_stream lacks result; `deferred` key removed |

`.venv/bin/python -m pytest tests/test_measure_tokens.py -v` → 10 passed in 0.01s.

## Headline empirical findings

### Token efficiency ranking (median_total_payload_bytes — lower = leaner wire surface)

| Rank | MCP | Headline payload bytes | Median turn input | Median turn output | Tools (schema cost proxy) |
|---|---|---|---|---|---|
| 1 | `obscura`            |  16,394 |  27 |   8,356 |  4 |
| 2 | `lightpanda`         |  44,633 |  48 |  11,046 | 20 |
| 3 | `chrome-devtools`    |  62,318 |  55 |  20,942 | 29 |
| 4 | `cloakbrowser`       |  77,228 |  63 |  24,476 | 20 |
| 5 | `browser-use-direct` | 120,059 |  62 |  20,173 | 16 |
| — | `firecrawl`          |       0 | N/A | N/A | 24 |
| — | `playwright`         | NO_EVIDENCE | — | — | 23 |
| — | `browser-use-agent`  | SKIPPED | — | — | 16 |

**Spread among scored MCPs with payload > 0: 7.3× (16,394 .. 120,059).**

This is materially below the 20× spread the 2026-03 wave reported. The 2026-03
number conflated schema + payload + turn into one column; once the three units
are separated, the per-call payload spread tightens. Phase 4 should use this
7.3× number, not 20×.

### S5 form-fill payload (the falsifiable claim's data point)

| MCP | S5 median bytes | Note |
|---|---|---|
| `lightpanda`         |    481 | S5 short-circuited (React unsupported); minimal Write-only stage |
| `obscura`            |    541 | S5 never reached — upstream FAILED |
| `chrome-devtools`    |    564 | S5 never reached — S4 React-Select FAILED |
| `browser-use-direct` |    634 | S5 never reached — upstream FAILED |
| `cloakbrowser`       |  **6,657** | **S5 actually exercised**: `cloak_type×4 + cloak_evaluate×1` (per-field type pattern + snapshot envelope) |
| `playwright`         | N/A | NO_EVIDENCE (03-01 gap) |

**Cloakbrowser's S5 payload is 10-13× the next-highest non-zero row.** Matches
03-01's tool-call count finding (S5 = 6 tool calls for cloakbrowser). The
empirical "per-field type" cost is now quantifiable in bytes, not just call
counts. Phase 4 should annotate this as the foil for Playwright's
`browser_fill_form` batch-fill claim — pending 03-01's NO_EVIDENCE closure.

### Turn (actual Claude billing) ranking

Output tokens dominate the turn cost across MCPs. Ranked by median per-pass
output tokens (lower = less Claude-generated work to complete the walk):

| Rank | MCP | Output tokens (median per pass) |
|---|---|---|
| 1 | `obscura`            |  8,356 |
| 2 | `lightpanda`         | 11,046 |
| 3 | `browser-use-direct` | 20,173 |
| 4 | `chrome-devtools`    | 20,942 |
| 5 | `cloakbrowser`       | 24,476 |

**Observation:** obscura and lightpanda rank top-2 in BOTH payload bytes
(leanest wire) AND output tokens (least Claude reasoning). They're "cheap"
both on wire and on billing. The cause is the same in both cases: most
stages short-circuited (lightpanda can't render React; obscura's 4-tool
surface lacks interaction primitives). **A lean MCP that doesn't work
isn't actually cheap — Phase 4 must read this ranking next to the
capability matrix.**

### Schema scope — RECORDED AS NULL THIS RUN

`ANTHROPIC_API_KEY` was absent at execution time. Per Plan 03-02
stop_conditions: ran with `--skip-schema`; every `schema_tokens` field is
null with the note `"schema scope unavailable: --skip-schema or
ANTHROPIC_API_KEY absent"` embedded in tokens.json.

**To backfill:** set `ANTHROPIC_API_KEY` and re-run

```bash
.venv/bin/python -m bench.measure_tokens results/2026-05-26 \
    --model claude-opus-4-7
```

The aggregator is idempotent for payload + turn (both deterministic from
raw_stream); only the four `schema_*` fields will populate. Expected schema
spread based on tool counts (from 03-01 SUMMARY): obscura (4 tools) and
browser-use (16 tools) lowest; chrome-devtools (29 tools), firecrawl (24
tools), playwright (23 tools) highest. **The chrome-devtools schema cost
will likely be the single largest "context overhead" line item** — its
tool descriptions include the strongest natural-language wording (e.g.,
"exposes content of the browser instance to the MCP client" stderr note
appears in the description excerpts).

## Gaps surfaced

1. **Playwright tokens.json status = NO_EVIDENCE.** Same root cause as
   03-01's `tool_call_counts.json` NO_EVIDENCE row: Playwright was not
   re-scored in Phase 2 (calibration baseline lives at
   `results/2026-05-25/playwright/`). Pointing measure_tokens at
   `results/2026-05-25 --mcp playwright` WOULD produce a record from
   that single calibration pass, but Phase 4 expects all MCPs in one date
   dir, and the calibration's single-pass nature is unsuitable for a
   3-pass median anyway. Phase 4 synthesis (03-05) must decide: backfill
   with a one-off Playwright harness run, OR mark the headline cell
   `evidence: pending`.

2. **Firecrawl tokens.json headline = 0 (legitimate).** No Claude session
   was ever run for firecrawl in Phase 2; the harness recorded only
   FAILED stage markers because the cloud API can't reach loopback
   fixtures (env-mismatch). The 0 byte payload IS the evidence — Phase 4
   should display firecrawl as a "harness-incompatible" row rather than
   pretending it competes on token efficiency. The turn-scope null is
   the corollary: no Claude turns, no usage block to extract. The
   research claim "Cloud LLM-extraction at cost of latency + tokens" is
   therefore UN-FALSIFIABLE from this evidence; would require a
   different fixture topology (public Greenhouse pages reachable from
   the firecrawl cloud) to test. Surface in Phase 4 as a methodology
   limitation, not a firecrawl deficiency.

3. **Schema scope deferred to a re-run.** Listed above; not a blocker
   for Phase 4 IF the synthesis is willing to publish payload + turn
   without schema. Note that several research-claim columns (especially
   chrome-devtools' "context overhead") cannot land until schema arrives.

4. **'unattributed' bytes are intentionally hidden from the headline but
   visible in `payload_bytes_per_stage`.** Per 03-01 SUMMARY: a pass that
   crashes before the first Write marker attributes its tool_use payload
   bytes to 'unattributed', which would inflate the headline by
   uncomparable amounts across MCPs. The bucket is kept in the raw
   `payload_bytes_per_stage` so a forensic reader can audit it, but the
   `headline_payload_bytes` and `median_payload_bytes_per_stage` exclude
   it. cloakbrowser's S8 absence + the corresponding 'unattributed'
   bucket is the example that motivated this design choice.

## Methodology disclosure (mandatory for Phase 4)

The three scopes use three DIFFERENT units. The phrase **"token efficiency"**
without qualification is misleading. The published matrix MUST use one of:

| Scope | Unit | Source | Use in Phase 4 |
|---|---|---|---|
| `schema_tokens`              | Anthropic tokens | `count_tokens(tools=...)` delta | Annotation column ("context overhead Claude pays just to load this MCP") |
| `headline_payload_bytes`     | UTF-8 bytes      | `len(json.dumps(...).encode())` | **Headline column** in the matrix |
| `median_turn_output_tokens`  | Anthropic tokens | terminal result envelope's usage | Secondary column ("Claude billing per walk") |

Cross-unit ratios (e.g., "payload-bytes-per-turn-output-token") are NOT
meaningful and must not appear in the published matrix. The note
`"schema = Anthropic-tokenizer-counted; payload = byte-count (proxy for
tokens); turn = actual Claude billing — three units, do not conflate."`
is embedded in every tokens.json's `notes` array so a future reader of an
individual file never loses this caveat.

## Verification

```bash
.venv/bin/python -m pytest tests/test_measure_tokens.py -v
# 10 passed in 0.01s

.venv/bin/python -m pytest -q
# 203 passed in 8.51s  (193 prior + 10 new; no regressions)

# All 8 tokens.json files have status, no deferred marker:
for mcp in playwright browser-use-direct browser-use-agent chrome-devtools \
           firecrawl lightpanda obscura cloakbrowser; do
  f="results/2026-05-26/$mcp/tokens.json"
  test -f "$f" || { echo "MISSING $f"; exit 1; }
  .venv/bin/python -c "
import json
d=json.load(open('$f'))
assert 'deferred' not in d or d.get('status')=='SKIPPED', '$f still deferred'
print(f\"OK $mcp scope={d['scope']} headline={d['headline_payload_bytes']}\")
"
done
# 8 OK rows

git diff HEAD scoring/score.py
# (empty — scoring engine untouched per plan rule)
```

## Path forward for Plan 03-05 synthesis

Plan 03-05 consumes these artifacts via:

```python
import json, pathlib
date_dir = pathlib.Path("results/2026-05-26")
for mcp_dir in date_dir.iterdir():
    if not mcp_dir.is_dir(): continue
    p = mcp_dir / "tokens.json"
    if not p.exists(): continue
    d = json.loads(p.read_text())
    # Phase 4 matrix column = headline_payload_bytes; null for SKIPPED/NO_EVIDENCE rows
    headline = d.get("headline_payload_bytes")
    # Annotation columns:
    schema_overhead = d.get("schema_tokens")            # null until ANTHROPIC_API_KEY re-run
    billing_output  = d.get("median_turn_output_tokens")
    # Methodology note for the matrix footer:
    note = d["notes"][0]  # always the three-unit caveat at index 0
```

The aggregator is idempotent — re-running it with `ANTHROPIC_API_KEY` set
will populate the four `schema_*` fields without touching payload/turn.
Plan 03-05 must NOT re-implement this logic.

## Deviations from Plan

**1. [Rule 3 - Blocking issue] `ANTHROPIC_API_KEY` unavailable at run time**
- **Found during:** Task 2 execution
- **Issue:** Local `rbw` agent was locked; the API key could not be
  retrieved automatically. Per Plan 03-02 stop_conditions: "ANTHROPIC_API_KEY
  absent → run with `--skip-schema` and surface in SUMMARY.md; do NOT
  block."
- **Fix:** Ran `python -m bench.measure_tokens results/2026-05-26
  --skip-schema`. All payload + turn data captured normally; schema_tokens
  null on every row with a note. Re-runnable when the key is available.
- **Files affected:** All 8 results/2026-05-26/<mcp>/tokens.json
  (`schema_tokens: null`, `schema_source: null`).
- **Commit:** c32f98f.

**2. [Design choice — not a deviation, but worth recording]
'unattributed' bucket excluded from headline median.** The plan's spec
said "Emit `payload_bytes_per_stage[PASS_N] = {S1: bytes, ...}`" and
"median_total_payload_bytes". The implementation keeps `unattributed` in
the per-pass dict (so forensic auditors can find it) but EXCLUDES it from
the headline median, mirroring 03-01's treatment of the same noisy
bucket. Documented in the decisions block above and the code comment.

## Self-Check: PASSED

- `bench/measure_tokens.py` — exists (commit 5fe3d30)
- `tests/test_measure_tokens.py` — 10 tests pass (commit 1bb6df3 RED → 5fe3d30 GREEN)
- 8 tokens.json files exist, 0 still carry the `deferred` key (verified by the loop above)
- `scoring/score.py` — unchanged (git diff HEAD scoring/score.py empty)
- Full test suite 203/203 pass — no regressions
- `headline_payload_bytes` populated for 6 of 8 (firecrawl=0 honest, playwright=NO_EVIDENCE, browser-use-agent=SKIPPED)
