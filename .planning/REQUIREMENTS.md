# Requirements — web-agent-comparison Wave 2

## Project Structure Mode

**Horizontal Layers** (`PROJECT_MODE=standard`). The work is a benchmark/research deliverable, not a user-facing product — natural breakdown is harness → per-MCP runs → cross-cutting measurements → synthesis, where each layer is consumed by the next. A vertical MVP slice ("one MCP end-to-end") would force premature scoring decisions before the harness is validated and would lose the shared-measurement parallelism that lets Phases 2 + 3 overlap.

---

## v1 Requirements

All requirements below are hypotheses until the report ships with the explicit Stage 2 graduation recommendation. Phase mappings are guidance for the roadmapper; final phase assignment is the roadmapper's call.

### Harness — test orchestration & evidence capture

- [x] **HARNESS-01**: A user can run `make bench-<mcp>` to execute one Claude Code session against the named MCP, walked through stages S1-S8 by the locked prompt, with that MCP's tools as the only allowed surface (`--allowedTools "mcp__${MCP}__*,Read,Write,Bash"`) — no fallback to WebFetch.
- [ ] **HARNESS-02**: Each MCP session writes a self-contained evidence directory at `results/<date>/<mcp>/` containing `transcript.md`, `raw_stream.jsonl`, `stage_s*.{yml,md,png,txt}`, `cold_start.json`, `tokens.json`, `tls.json`, `stability.log`, `orphan_audit.log`.
- [x] **HARNESS-03**: `.mcp.json` (project scope, already committed) is the single source of truth for MCP commands; all harness scripts read it via `jq` rather than duplicating server-spawn commands.
- [x] **HARNESS-04**: The locked S1-S8 task script lives at `prompts/stage_walk.md`, parameterised by the MCP under test; the same prompt drives every MCP for direct comparability.
- [ ] **HARNESS-05**: A user can run `make bench-playwright && make score` and reproduce a composite within ±0.5 of the 2026-03-31 Playwright score (9.07) before any other MCP is added to the wave — this is the harness's go/no-go gate.
- [ ] **HARNESS-06**: A `scripts/check_prereqs.sh` Bash script verifies all 7 MCP binaries are installed, exits non-zero with a remediation message if any are missing, and is the first step of `make bench`.
- [x] **HARNESS-07**: Every MCP server child process is spawned under a `setsid` process-group; a `bench/orphan_audit.py` runs pre/post-bench, diffs `ps` output, and `kill -KILL`s any orphans before the run is considered clean.
- [x] **HARNESS-08**: A per-tool-call 30s timeout is enforced by the harness (Claude Code enforces none); a tool call that exceeds it is recorded as `TIMEOUT` in the failure-attribution taxonomy.
- [x] **HARNESS-09**: A `ulimit -v` memory ceiling is set per MCP session (default 4GB) so a runaway MCP crashes its own process instead of swapping the Mac Mini.

### Fairness — measurement discipline that prevents 2026-03 class mistakes

- [ ] **FAIRNESS-01**: Every S1-S8 stage failure triggers a 3-pass-of-3 retry via `bench/transient.py`; the published score uses the median across attempts; the matrix shows `n/3 passes` per cell so readers see variance, not a single bad run masquerading as intrinsic.
- [ ] **FAIRNESS-02**: A transient-failure taxonomy (`WebSocket 1001/1006`, `ECONNRESET`, `MCP initialize timeout`, `HTTP 429/503`, `Chromium SIGKILL`) is enumerated in `bench/transient.py`; matches against the taxonomy trigger automatic retry, non-matches surface as real failures.
- [ ] **FAIRNESS-03**: `N/A` and `0` are distinct in the stage matrix; a read-only MCP (lightpanda, firecrawl) is `N/A` for S4-S8 (interactive stages), not `0`; `scoring/score.py` drops `N/A` cells from the weighted denominator so the composite reflects only attempted dimensions.
- [ ] **FAIRNESS-04**: The published report contains TWO views: same-rubric composite AND a capability matrix with explicit category tags (cloud / stealth / JS-light / LLM-augmented / tool-only) so a reader can't accidentally compare firecrawl-the-cloud to playwright-the-local on a single number.
- [ ] **FAIRNESS-05**: Browser-use is run in dual mode — `direct` (no LLM) AND `agent` (with LLM key) — scored as two rows; the report explicitly states which mode each row represents.
- [ ] **FAIRNESS-06**: Every matrix row has a failure-attribution tag from the taxonomy (`tool-bug` / `env-mismatch` / `target-flag` / `transient`); readers can see why a score is what it is, not just that it's low.
- [x] **FAIRNESS-07**: The harness MUST NOT bypass an MCP-reported failure (e.g., browser-use `initialize` timeout) by reimplementing what Claude Code does; if the MCP fails Claude Code's normal lifecycle, the published score reflects that and a courtesy-disclosure ticket is filed.

### Measurements — cross-cutting per-MCP signals

- [x] **MEAS-01**: Cold-start latency per MCP is captured as a 3-segment split (`t_resolve` / `t_spawn` / `t_first_useful`) for BOTH cold and warm cache; published value is the median of ≥5 runs; lives in `results/<date>/<mcp>/cold_start.json`.
- [x] **MEAS-02**: Token efficiency per MCP per task is captured as a 3-scope split (`schema` / `payload` / `turn`); the published headline column is `payload` (the apples-to-apples per-call cost); `schema` uses Anthropic SDK `count_tokens` (free, deterministic); `turn` parses `stream-json` `usage` blocks (actual billed cost); `payload` parses raw JSON-RPC. Lives in `results/<date>/<mcp>/tokens.json`.
- [x] **MEAS-07**: A 1hr stability run per MCP loops S1+S5 with 30s sleeps against the local snapshot-fixture server (NOT live targets) and writes to `results/<date>/<mcp>/stability.log`; post-run orphan-process audit must be 0.
- [x] **MEAS-08**: Per-stage tool-call count is captured for every S1-S8 attempt; this empirically grounds the Playwright "browser_fill_form fills 6 fields in 1 call" claim and equivalents.
- [x] **MEAS-09**: A per-MCP tool-surface inventory (count + 6-category breakdown per chrome-devtools-mcp's category scheme) is captured at harness start; lives in `results/<date>/<mcp>/tools_inventory.json`.

### Reproducibility — third party can clone, run, get similar scores

- [ ] **REPRO-01**: A reproducibility manifest at `results/<date>/versions.lock.md` + `versions.json` records exact pinned versions of all 7 MCP servers, their binary SHA256s, Node + uv + Python versions, OS + arch + Chromium version where applicable; `bench/capture_versions.py` produces it from the live environment, not from a hand-edited file.
- [ ] **REPRO-02**: `uv.lock` (Python) and `package-lock.json` (Node) are committed at repo root; `uv sync --locked` + `npm ci` reproduce the exact dependency closure.
- [ ] **REPRO-03**: A `MACHINE.md` per `results/<date>/` records the machine specs, network conditions, IP/ASN, time of run, NTP-synced timestamp; the report's methodology section cites it.
- [ ] **REPRO-04**: Fixtures are self-hosted snapshots at `fixtures/snapshots/<platform>_<date>/` (`wget --mirror`d from the original public URLs, then PII-scrubbed by `bench/scrub_artifacts.py`); the harness serves them via `python3 -m http.server` on `127.0.0.1`; tests target the loopback address, not the live URL.
- [ ] **REPRO-05**: A `fixtures/snapshots/<platform>_<date>/PROVENANCE.md` documents source URL, mirror date, scrubbing steps applied, and a SHA256 over the served-content directory.
- [ ] **REPRO-06**: A `docs/REPRODUCIBILITY.md` documents the single command (`make bench`) third parties run; calls out the FIRECRAWL_API_KEY requirement (6/7 acceptable if absent), CloakBrowser Linux availability uncertainty.

### Report — public-facing deliverables

- [ ] **REPORT-01**: A scored 8-dim weighted score table (7 MCPs × 8 dims + composite) appears in `results/2026-05-XX-mcp-comparison.md`, same shape as `results/2026-03-31_run.md` for direct comparability.
- [ ] **REPORT-02**: A stage matrix (S1-S8 × 7 MCPs) with cells in `{PASS, FAIL, PARTIAL, N/A, UNTESTED}` appears alongside the score table; `N/A` and `UNTESTED` are distinct.
- [ ] **REPORT-03**: A per-MCP "Deep Analysis" stanza (3-6 strengths + 3-6 weaknesses + 1-paragraph verdict + the per-MCP "interesting angle" finding) appears for each of the 7 MCPs.
- [ ] **REPORT-04**: A methodology section explains the rubric, fixtures, harness, measurement approach, and reproducibility model; cites `MACHINE.md` for run-specific specifics.
- [ ] **REPORT-05**: A methodology disclaimer header on the public report states "evaluated as of `<date>` with configuration `<X>`; not intrinsic tool quality" so future readers see the snapshot framing.
- [x] **REPORT-06**: `results/recommendations.md` contains an explicit Stage 2 graduation recommendation with tiers: PRIMARY (graduates into terminal-craft toolkit), SECONDARY (fallback / specialised use), SANDBOX-ONLY (cloakbrowser tier), SKIP (excluded from toolkit with reason). This recommendation IS the Stage 2 unblock gate.
- [ ] **REPORT-07**: The repo `README.md` is updated with the headline verdict, the methodology summary, and a link to `results/recommendations.md`.
- [ ] **REPORT-08**: Every cloakbrowser mention in any report file carries an explicit `**Sandbox only — do not point at authenticated sessions**` callout.
- [ ] **REPORT-09**: If the run is partial (e.g., Firecrawl skipped because no API key), an executive-summary disclosure + matrix-row note + recommendations note flags it; the report does NOT silently emit 6/7.
- [ ] **REPORT-10**: A "Negative Results" section explicitly documents what didn't work, what was skipped, what was punted to a follow-up wave; this is non-optional honesty content.
- [ ] **REPORT-11**: A 2026-03 → 2026-05 overlay notes how scores moved on overlapping technologies (Playwright MCP especially) so readers see progress / regression.
- [ ] **REPORT-12**: A Linear traceability footer cites G-703 (umbrella) + the per-MCP sub-tickets.

### Safety — gates that prevent secret leaks, PII leaks, scope creep

- [ ] **SAFETY-01**: `.mcp.json` env values use `${VAR}` references ONLY; a pre-commit hook regex-blocks inline literal API keys, tokens, or secrets in `.mcp.json` and is wired into `.git/hooks/pre-commit`.
- [ ] **SAFETY-02**: `bench/scrub_artifacts.py` runs OCR + name-regex over every screenshot in `results/<date>/<mcp>/` before commit; any artifact containing the real applicant data is rejected; only the "Jane Testworth" mock-applicant data may appear in evidence.
- [ ] **SAFETY-03**: An echo-server fixture + `tests/stealth_leak_test.py` captures HTTP headers each MCP sends; any mismatch between JS-visible UA and the Sec-CH-UA-Platform header tags the MCP with "stealth: leaks"; on macOS, `obscura --stealth` is DISABLED by default per `~/.claude/docs/browser-tools.md`.
- [ ] **SAFETY-04**: cloakbrowser is tested ONLY against the public Greenhouse + Ashby snapshot fixtures; the harness rejects any attempt to point it at an authenticated host (`hostname != 127.0.0.1` AND `mcp == cloakbrowser` → refuse).
- [ ] **SAFETY-05**: BrowserMCP, Stage 2 (terminal-craft), Stage 3 (Kestrel/Eyas), framework-comparison content, and "shared abstractions over the MCPs" are explicitly out of scope; a wave-close ritual at the end of Phase 4 audits whether any scope-creep snuck in.

### Outreach — vendor courtesy and public-rel hygiene

- [ ] **OUTREACH-03**: G-703 (the umbrella Linear ticket, estimate=16) is split into per-MCP scoring sub-tickets + 1 synthesis ticket before any Phase 2 work pulls into a cycle — the estimate=16 IS the break-before-cycle signal.

---

## v2 Requirements (deferred — explicit table-stakes the report could grow into)

- [ ] **v2: Memory-footprint snapshot per MCP during S1** (`ps` snapshot — surfaces Obscura's ~30MB-per-tab vs Playwright's ~300MB-per-tab differentiator; FEATURES "should have" rather than must)
- [ ] **v2: chrome-devtools-only "DevTools probe" 9th stage** producing `network.json` + `trace.json` + `console.json` — artifacts no other MCP can structurally produce. Defer because it changes the stage matrix and breaks 2026-03 comparability; revisit after Stage 1 ships.
- [ ] **v2: LLM-extraction split scoring for Firecrawl + browser-use** (run each in both raw-page and LLM-extraction modes, score both rows) — defer because dual-mode complicates the matrix and the primary recommendation can be made without it.
- [ ] **v2: Residential-IP rotation pool** for bot-detection cross-checks — defer pending Vitalik's $5-15 budget call; default v1 strategy is single-IP with 10min idle.

---

## Out of Scope (with reasoning)

- **Stage 2 terminal-craft toolkit packaging** — separate private repo; blocked on this wave's `recommendations.md`. Doing it here violates the pipeline gate and would be premature.
- **Stage 3 Kestrel + Eyas agent wiring** — production agent integration; blocked on Stage 2. Two stages downstream.
- **App-level agents (Skyvern, Manus, Comet, etc.)** — covered in the 2026-03-31 wave; this comparison is MCP-layer only. Mixing layers in one matrix would mislead readers.
- **BrowserMCP server in this wave** — different operational model (Chrome extension + Agent profile); would muddy apples-to-apples. May revisit in a follow-up wave.
- **Authenticated-session testing on real banking/credential pages** — global policy in `~/.claude/CLAUDE.md` prohibits browser MCPs on those.
- **Framework recommendations the reader didn't ask for** (Stagehand, Playwright-Python wrapper choices, etc.) — the report's job is scoring 7 named candidates, not generic framework discovery.
- **Qualitative "I liked this one" vibes-based ranking** — every claim in the report is backed by evidence in the per-MCP directory.
- **Cross-MCP combo recommendations as primary content** ("use lightpanda for read-only, playwright for forms") — that's Stage 2 terminal-craft's job. Surfacing it here is fine in the Negative Results section but not as a top-line recommendation.
- **Speculation about MCP roadmaps / future features** — only what works as of `<date>` is in scope.
- **Building shared abstractions to "normalize" MCP interfaces for comparison** — doing so contaminates per-MCP scores by hiding their actual surface. Compare what each ships, not a uniform shim.
- **Docker / devcontainer-based reproducibility** — contaminates cold-start latency and TLS fingerprint measurements; explicit decision per STACK + ARCHITECTURE.
- **Reading the README to score the MCP** — empirical only; the matrix reflects observed behaviour, not vendor self-reports.

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARNESS-01 | Phase 1 | Complete |
| HARNESS-02 | Phase 1 | Pending |
| HARNESS-03 | Phase 1 | Complete |
| HARNESS-04 | Phase 1 | Complete |
| HARNESS-05 | Phase 1 | Pending |
| HARNESS-06 | Phase 1 | Pending |
| HARNESS-07 | Phase 1 | Complete |
| HARNESS-08 | Phase 1 | Complete |
| HARNESS-09 | Phase 1 | Complete |
| FAIRNESS-01 | Phase 1 | Pending |
| FAIRNESS-02 | Phase 1 | Pending |
| FAIRNESS-03 | Phase 1 | Pending |
| FAIRNESS-04 | Phase 2 | Pending |
| FAIRNESS-05 | Phase 2 | Pending |
| FAIRNESS-06 | Phase 1 | Pending |
| FAIRNESS-07 | Phase 1 | Complete |
| MEAS-01 | Phase 3 | Complete |
| MEAS-02 | Phase 3 | Complete |
| MEAS-07 | Phase 3 | Complete |
| MEAS-08 | Phase 3 | Complete |
| MEAS-09 | Phase 3 | Complete |
| REPRO-01 | Phase 4 | Pending |
| REPRO-02 | Phase 1 | Pending |
| REPRO-03 | Phase 4 | Pending |
| REPRO-04 | Phase 1 | Pending |
| REPRO-05 | Phase 1 | Pending |
| REPRO-06 | Phase 4 | Pending |
| REPORT-01 | Phase 4 | Pending |
| REPORT-02 | Phase 4 | Pending |
| REPORT-03 | Phase 4 | Pending |
| REPORT-04 | Phase 4 | Pending |
| REPORT-05 | Phase 4 | Pending |
| REPORT-06 | Phase 4 | Complete |
| REPORT-07 | Phase 4 | Pending |
| REPORT-08 | Phase 4 | Pending |
| REPORT-09 | Phase 4 | Pending |
| REPORT-10 | Phase 4 | Pending |
| REPORT-11 | Phase 4 | Pending |
| REPORT-12 | Phase 4 | Pending |
| SAFETY-01 | Phase 1 | Pending |
| SAFETY-02 | Phase 1 | Pending |
| SAFETY-03 | Phase 1 | Pending |
| SAFETY-04 | Phase 1 | Pending |
| SAFETY-05 | Phase 4 | Pending |
| OUTREACH-03 | Phase 1 | Pending |

### Coverage Summary

| Phase | Requirements | Count |
|-------|--------------|-------|
| Phase 1 — Harness Foundation | HARNESS-01..09, FAIRNESS-01/02/03/06/07, REPRO-02/04/05, SAFETY-01..04, OUTREACH-03 | 22 |
| Phase 2 — Per-MCP Scoring Runs | FAIRNESS-04, FAIRNESS-05 | 2 |
| Phase 3 — Cross-Cutting Measurements | MEAS-01/02/07/08/09 | 5 |
| Phase 4 — Synthesis & Reproducibility Validation | REPRO-01/03/06, REPORT-01..12, SAFETY-05 | 16 |
| **Total** | **All 45 v1 requirements** | **45** |

Coverage: 45/45 v1 requirements mapped to exactly one phase. No orphans. No duplicates.

**Scope cut 2026-05-22 (commit `XXXXXXX`):** MEAS-03/04 (TLS fingerprint capture), MEAS-05/06 (bot-detection adversary set + live-canary exclusion), REPRO-07 (MacBook cross-machine validation), and OUTREACH-01/02 (vendor courtesy disclosure) were cut from v1 because (a) Greenhouse/Ashby targets don't aggressively fingerprint-check, so detection-resilience metrics don't bear on the Kestrel/Eyas use case, and (b) cross-machine reproducibility is below the abstraction level the project actually cares about (agents working with Claude). Detection + fingerprint work moved to follow-up wave **[G-710](https://linear.app/abandoned-yachts/issue/G-710)** which reuses this wave's harness once it ships and adds the anti-captcha.com integration. Total v1 reqs: 52 → 45.

**Note on Phase 2 lightness:** Phase 2 only carries 2 requirements explicitly because most per-MCP work is operational execution against the Phase-1 harness (the harness IS the mechanism). FAIRNESS-04/05 land here because dual-mode browser-use scoring and capability-tag matrix-row authoring are decisions made during per-MCP runs, not during harness build. The bulk of Phase 2 work is producing 7 evidence directories worth of artifacts that Phase 4 then aggregates.

---

## Definition of Done

This wave ships when:
1. All 45 v1 requirements above are `[x]` checked or explicitly converted to v2 with a written reason
2. `results/2026-05-XX-mcp-comparison.md` and `results/recommendations.md` are committed
3. `README.md` is updated with the headline verdict
4. G-703 is closed; per-MCP sub-tickets created from G-703 are closed; G-710 (detection follow-up) is referenced in `results/recommendations.md` "Future Waves" section
5. A wave-close ritual confirms no scope-creep snuck in; what didn't make the cut is documented in `results/recommendations.md` "Future Waves" section

---
*Last updated: 2026-05-22 after initial requirements definition*
