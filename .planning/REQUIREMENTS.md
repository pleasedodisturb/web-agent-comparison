# Requirements — web-agent-comparison Wave 2

## Project Structure Mode

**Horizontal Layers** (`PROJECT_MODE=standard`). The work is a benchmark/research deliverable, not a user-facing product — natural breakdown is harness → per-MCP runs → cross-cutting measurements → synthesis, where each layer is consumed by the next. A vertical MVP slice ("one MCP end-to-end") would force premature scoring decisions before the harness is validated and would lose the shared-measurement parallelism that lets Phases 2 + 3 overlap.

---

## v1 Requirements

All requirements below are hypotheses until the report ships with the explicit Stage 2 graduation recommendation. Phase mappings are guidance for the roadmapper; final phase assignment is the roadmapper's call.

### Harness — test orchestration & evidence capture

- [ ] **HARNESS-01**: A user can run `make bench-<mcp>` to execute one Claude Code session against the named MCP, walked through stages S1-S8 by the locked prompt, with that MCP's tools as the only allowed surface (`--allowedTools "mcp__${MCP}__*,Read,Write,Bash"`) — no fallback to WebFetch.
- [ ] **HARNESS-02**: Each MCP session writes a self-contained evidence directory at `results/<date>/<mcp>/` containing `transcript.md`, `raw_stream.jsonl`, `stage_s*.{yml,md,png,txt}`, `cold_start.json`, `tokens.json`, `tls.json`, `stability.log`, `orphan_audit.log`.
- [ ] **HARNESS-03**: `.mcp.json` (project scope, already committed) is the single source of truth for MCP commands; all harness scripts read it via `jq` rather than duplicating server-spawn commands.
- [ ] **HARNESS-04**: The locked S1-S8 task script lives at `prompts/stage_walk.md`, parameterised by the MCP under test; the same prompt drives every MCP for direct comparability.
- [ ] **HARNESS-05**: A user can run `make bench-playwright && make score` and reproduce a composite within ±0.5 of the 2026-03-31 Playwright score (9.07) before any other MCP is added to the wave — this is the harness's go/no-go gate.
- [ ] **HARNESS-06**: A `scripts/check_prereqs.sh` Bash script verifies all 7 MCP binaries are installed, exits non-zero with a remediation message if any are missing, and is the first step of `make bench`.
- [ ] **HARNESS-07**: Every MCP server child process is spawned under a `setsid` process-group; a `bench/orphan_audit.py` runs pre/post-bench, diffs `ps` output, and `kill -KILL`s any orphans before the run is considered clean.
- [ ] **HARNESS-08**: A per-tool-call 30s timeout is enforced by the harness (Claude Code enforces none); a tool call that exceeds it is recorded as `TIMEOUT` in the failure-attribution taxonomy.
- [ ] **HARNESS-09**: A `ulimit -v` memory ceiling is set per MCP session (default 4GB) so a runaway MCP crashes its own process instead of swapping the Mac Mini.

### Fairness — measurement discipline that prevents 2026-03 class mistakes

- [ ] **FAIRNESS-01**: Every S1-S8 stage failure triggers a 3-pass-of-3 retry via `bench/transient.py`; the published score uses the median across attempts; the matrix shows `n/3 passes` per cell so readers see variance, not a single bad run masquerading as intrinsic.
- [ ] **FAIRNESS-02**: A transient-failure taxonomy (`WebSocket 1001/1006`, `ECONNRESET`, `MCP initialize timeout`, `HTTP 429/503`, `Chromium SIGKILL`) is enumerated in `bench/transient.py`; matches against the taxonomy trigger automatic retry, non-matches surface as real failures.
- [ ] **FAIRNESS-03**: `N/A` and `0` are distinct in the stage matrix; a read-only MCP (lightpanda, firecrawl) is `N/A` for S4-S8 (interactive stages), not `0`; `scoring/score.py` drops `N/A` cells from the weighted denominator so the composite reflects only attempted dimensions.
- [ ] **FAIRNESS-04**: The published report contains TWO views: same-rubric composite AND a capability matrix with explicit category tags (cloud / stealth / JS-light / LLM-augmented / tool-only) so a reader can't accidentally compare firecrawl-the-cloud to playwright-the-local on a single number.
- [ ] **FAIRNESS-05**: Browser-use is run in dual mode — `direct` (no LLM) AND `agent` (with LLM key) — scored as two rows; the report explicitly states which mode each row represents.
- [ ] **FAIRNESS-06**: Every matrix row has a failure-attribution tag from the taxonomy (`tool-bug` / `env-mismatch` / `target-flag` / `transient`); readers can see why a score is what it is, not just that it's low.
- [ ] **FAIRNESS-07**: The harness MUST NOT bypass an MCP-reported failure (e.g., browser-use `initialize` timeout) by reimplementing what Claude Code does; if the MCP fails Claude Code's normal lifecycle, the published score reflects that and a courtesy-disclosure ticket is filed.

### Measurements — cross-cutting per-MCP signals

- [ ] **MEAS-01**: Cold-start latency per MCP is captured as a 3-segment split (`t_resolve` / `t_spawn` / `t_first_useful`) for BOTH cold and warm cache; published value is the median of ≥5 runs; lives in `results/<date>/<mcp>/cold_start.json`.
- [ ] **MEAS-02**: Token efficiency per MCP per task is captured as a 3-scope split (`schema` / `payload` / `turn`); the published headline column is `payload` (the apples-to-apples per-call cost); `schema` uses Anthropic SDK `count_tokens` (free, deterministic); `turn` parses `stream-json` `usage` blocks (actual billed cost); `payload` parses raw JSON-RPC. Lives in `results/<date>/<mcp>/tokens.json`.
- [ ] **MEAS-03**: TLS fingerprint per MCP captures JA3 + JA3N + JA4 + JA4_h + ALPN order + HTTP/2 frame settings via Scrapfly primary (`tools.scrapfly.io/api/fp/ja3?extended=1`) and peet.ws cross-check (`tls.peet.ws/api/all`); disagreement between the two fails the run with explicit error. Lives in `results/<date>/<mcp>/tls.json`.
- [ ] **MEAS-04**: A real-Chrome JA4 baseline is captured ONCE per wave (from the host's installed Chrome, same machine) and committed as `results/<date>/_baseline/chrome_tls.json`; per-MCP TLS reports cite their delta from this baseline.
- [ ] **MEAS-05**: Bot-detection resilience per MCP is tested against a STABLE adversary set: `bot.sannysoft.com`, `fingerprint.com/demo`, `creepjs`, `browserscan.net/bot-detection`, plus ≥1 self-deployed Cloudflare Worker for controlled-tier testing; per attempt records IP + ASN + observed challenge tier; lives in `results/<date>/<mcp>/bot_detection.json`.
- [ ] **MEAS-06**: Live commercial bot-detection targets (`nowsecure.nl` etc.) are excluded from the per-MCP measurement loop; at most ONE live-canary run per wave as a drift detector, not a per-candidate score input.
- [ ] **MEAS-07**: A 1hr stability run per MCP loops S1+S5 with 30s sleeps against the local snapshot-fixture server (NOT live targets) and writes to `results/<date>/<mcp>/stability.log`; post-run orphan-process audit must be 0.
- [ ] **MEAS-08**: Per-stage tool-call count is captured for every S1-S8 attempt; this empirically grounds the Playwright "browser_fill_form fills 6 fields in 1 call" claim and equivalents.
- [ ] **MEAS-09**: A per-MCP tool-surface inventory (count + 6-category breakdown per chrome-devtools-mcp's category scheme) is captured at harness start; lives in `results/<date>/<mcp>/tools_inventory.json`.

### Reproducibility — third party can clone, run, get similar scores

- [ ] **REPRO-01**: A reproducibility manifest at `results/<date>/versions.lock.md` + `versions.json` records exact pinned versions of all 7 MCP servers, their binary SHA256s, Node + uv + Python versions, OS + arch + Chromium version where applicable; `bench/capture_versions.py` produces it from the live environment, not from a hand-edited file.
- [ ] **REPRO-02**: `uv.lock` (Python) and `package-lock.json` (Node) are committed at repo root; `uv sync --locked` + `npm ci` reproduce the exact dependency closure.
- [ ] **REPRO-03**: A `MACHINE.md` per `results/<date>/` records the machine specs, network conditions, IP/ASN, time of run, NTP-synced timestamp; the report's methodology section cites it.
- [ ] **REPRO-04**: Fixtures are self-hosted snapshots at `fixtures/snapshots/<platform>_<date>/` (`wget --mirror`d from the original public URLs, then PII-scrubbed by `bench/scrub_artifacts.py`); the harness serves them via `python3 -m http.server` on `127.0.0.1`; tests target the loopback address, not the live URL.
- [ ] **REPRO-05**: A `fixtures/snapshots/<platform>_<date>/PROVENANCE.md` documents source URL, mirror date, scrubbing steps applied, and a SHA256 over the served-content directory.
- [ ] **REPRO-06**: A `docs/REPRODUCIBILITY.md` documents the single command (`make bench`) third parties run; calls out the FIRECRAWL_API_KEY requirement (6/7 acceptable if absent), CloakBrowser Linux availability uncertainty, and the bot-detection IP-rotation strategy.
- [ ] **REPRO-07**: The report is reproducible on a second machine (MacBook): a clean checkout + `make bench` + `make score` produces per-MCP composites within ±0.5 of the primary (Mac Mini) run; cross-machine validation is a Phase 4 deliverable.

### Report — public-facing deliverables

- [ ] **REPORT-01**: A scored 8-dim weighted score table (7 MCPs × 8 dims + composite) appears in `results/2026-05-XX-mcp-comparison.md`, same shape as `results/2026-03-31_run.md` for direct comparability.
- [ ] **REPORT-02**: A stage matrix (S1-S8 × 7 MCPs) with cells in `{PASS, FAIL, PARTIAL, N/A, UNTESTED}` appears alongside the score table; `N/A` and `UNTESTED` are distinct.
- [ ] **REPORT-03**: A per-MCP "Deep Analysis" stanza (3-6 strengths + 3-6 weaknesses + 1-paragraph verdict + the per-MCP "interesting angle" finding) appears for each of the 7 MCPs.
- [ ] **REPORT-04**: A methodology section explains the rubric, fixtures, harness, measurement approach, and reproducibility model; cites `MACHINE.md` for run-specific specifics.
- [ ] **REPORT-05**: A methodology disclaimer header on the public report states "evaluated as of `<date>` with configuration `<X>`; not intrinsic tool quality" so future readers see the snapshot framing.
- [ ] **REPORT-06**: `results/recommendations.md` contains an explicit Stage 2 graduation recommendation with tiers: PRIMARY (graduates into terminal-craft toolkit), SECONDARY (fallback / specialised use), SANDBOX-ONLY (cloakbrowser tier), SKIP (excluded from toolkit with reason). This recommendation IS the Stage 2 unblock gate.
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

- [ ] **OUTREACH-01**: Any MCP scoring below 5/10 composite triggers a courtesy pre-publication disclosure: a Linear ticket per vendor with the draft score, repro steps, and ≥7-day comment window before the report goes public.
- [ ] **OUTREACH-02**: The disclosure ticket includes a polite invitation for the vendor to verify the methodology and a commit to publishing their response inline in the report if they provide one.
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

(empty — filled by roadmapper, one row per requirement → phase mapping)

---

## Definition of Done

This wave ships when:
1. All 38 v1 requirements above are `[x]` checked or explicitly converted to v2 with a written reason
2. `results/2026-05-XX-mcp-comparison.md` and `results/recommendations.md` are committed
3. `README.md` is updated with the headline verdict
4. Cross-machine reproducibility validated (MacBook clean-checkout `make bench` produces ±0.5 composite per MCP)
5. Every vendor scoring below 5 has a Linear courtesy ticket with the ≥7-day window either elapsed or with vendor input incorporated
6. G-703 is closed; per-MCP sub-tickets created from G-703 are closed
7. A wave-close ritual confirms no scope-creep snuck in; what didn't make the cut is documented in `results/recommendations.md` "Future Waves" section

---
*Last updated: 2026-05-22 after initial requirements definition*
