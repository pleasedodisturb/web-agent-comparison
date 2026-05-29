# Roadmap: web-agent-comparison

## Milestones

- ✅ **v1.0 MCP-layer browser-server benchmark** — Phases 1-5 (shipped 2026-05-28) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- 🚧 **v1.1 General-purpose fixture expansion + stealth axis** — Phases 6-11 (active 2026-05-29)

## Overview (v1.1)

v1.1 expands the fixture set from job-application-only (S1-S8) to general-purpose web tasks (S9-S26 — 18 new stages across 8 categories: e-commerce, SERP, long-form content, pagination, auth-walled, complex forms, table extraction, framework variants) AND adds a stealth axis (TLS fingerprint + bot-detection adversary set) that lives **alongside** the composite, not inside it. The 8-dim rubric, `scoring/score.py`, and the 7-row `.mcp.json` stay byte-for-byte locked vs v1.0 — comparability with the v1.0 scoreboard is the load-bearing claim of v1.1.

Work is **horizontally layered** (mode: standard, granularity: standard): fixtures must land before any re-validation can run; harness portability must land before cross-platform re-baseline can produce honest Linux numbers; per-MCP re-validation runs in parallel against the new fixture set; stealth axis runs independently of the composite track; synthesis closes the wave.

**Two vendor-fix-gated tracks** (VALIDATE-04 browser-use-agent on `browser-use#4846`; VALIDATE-08 Obscura Linux on `h4ckf0r0day/obscura#197`) are designed to be **conditionally skippable** — phases ship with the available evidence and document the still-broken state if upstream fixes haven't landed.

## Phases

<details>
<summary>✅ v1.0 MCP-layer browser-server benchmark (Phases 1-5) — SHIPPED 2026-05-28</summary>

- [x] **Phase 1: Harness Foundation** (7/7 plans) — completed 2026-05-26
- [x] **Phase 2: Per-MCP Scoring Runs** (7/7 plans) — completed 2026-05-27
- [x] **Phase 3: Cross-Cutting Measurements** (5/5 plans) — completed 2026-05-27
- [x] **Phase 4: Synthesis** (6/6 plans) — completed 2026-05-27
- [x] **Phase 5: Close v1.0 governance debt** (5/5 plans) — completed 2026-05-28

</details>

**v1.1 Phase Numbering:** continues from v1.0 — phases start at **Phase 6** (no reset).

- [ ] **Phase 6: Fixture authoring (S9-S26)** — Author 18 new loopback fixtures across 8 categories + extend scrub/snapshot infra; freeze the v1.1 fixture set before any re-validation runs
- [ ] **Phase 7: Harness portability + Linux v1.0 baseline** — OS-detect `ulimit -v` in `run_mcp_session.sh`; re-run v1.0 fixtures (S1-S8) on Linux x86_64 to establish the cross-OS baseline
- [ ] **Phase 8: Re-validate v1.0 candidates on v1.1 fixtures** — Score all 7 v1.0 MCPs on S9-S26 with median-of-3 on both macOS arm64 + Linux x86_64; publish cross-platform per-OS matrix
- [ ] **Phase 9: BrowserMCP candidate decision (G-744)** — Formal include/category/exclude decision; if included, atomic `.mcp.json` extension to 8-candidate roster + median-of-3 scoring on S1-S26
- [ ] **Phase 10: Stealth axis (TLS fingerprint + bot-detection adversary)** — Per-MCP JA3/JA3n/JA4 capture vs real-Chrome baseline + per-detector pass/fail (Cloudflare/DataDome/reCAPTCHA/Akamai); published as a separate verdict column, NOT folded into composite
- [ ] **Phase 11: v1.1 synthesis + publication** — Dual-row scoreboard (v1.0 + v1.1 composite per MCP) + stealth verdict column + cross-platform matrix + per-MCP DEEP_ANALYSIS-v1.1 + GitHub release

## Phase Details

### Phase 6: Fixture authoring (S9-S26)

**Goal**: All 18 new v1.1 stages (S9-S26) exist as byte-for-byte loopback snapshots in `fixtures/`, scrubbed + PROVENANCE-tagged, served by the existing 127.0.0.1 fixture server, and the harness's stage-walk prompt can render every new stage end-to-end without harness modification — turning v1.1's design proposal into a frozen, reproducible asset set.
**Depends on**: Nothing (first v1.1 phase; pure fixture-authoring against the v1.0 harness)
**Requirements**: FIXTURE-01, FIXTURE-02, FIXTURE-03, FIXTURE-04, FIXTURE-05, FIXTURE-06, FIXTURE-07, FIXTURE-08, FIXTURE-09, FIXTURE-10, FIXTURE-11, FIXTURE-12, FIXTURE-13, FIXTURE-14, FIXTURE-15, FIXTURE-16, FIXTURE-17, FIXTURE-18, DESIGN-01, DESIGN-02, DESIGN-03, FAIRNESS-08, FAIRNESS-09, FAIRNESS-10, FAIRNESS-11, FAIRNESS-12, REPRO-09, REPRO-10, REPRO-11, REPRO-12, REPRO-13
**Success Criteria** (what must be TRUE):

  1. `fixtures/snapshots/` contains a directory + frozen HTML/asset bundle for every stage S9-S26 (18 directories); each is served at `http://127.0.0.1:<port>/<stage-slug>/...` by the existing fixture server with HTTP 200 and content-length > 0 on the root document.
  2. `fixtures/PROVENANCE.md` lists every new fixture with: source URL (or "synthetic"), capture date, license (CC BY-SA / public domain / synthetic), one-sentence agent-task tag (DESIGN-03), and rendering archetype (server-HTML / Next.js-SSR / SvelteKit / Vue 3 SPA / vanilla static — covering FAIRNESS-08).
  3. The full v1.1 fixture set is ≤ 50 MB on disk (REPRO-11), no single fixture > 5 MB; `du -sh fixtures/snapshots/` confirms; `bench/scrub_artifacts.py` (extended for new fixture surface per REPRO-10) exits 0 on every committed fixture.
  4. `prompts/stage_walk.md` v1.1 extension contains S9-S26 prompt cells with read-vs-drive parity at ~50/50 (DESIGN-01); FIXTURE-08 (S16 pagination) prompt explicitly requires state across ≥3 pages (DESIGN-02); FIXTURE-11+12 prompt pair (S19 fill / S20 recover) exercises the form-error-recovery muscle in a single transcript.
  5. Sacrosanct triad audit (`bench/wave_close_check.py` — `scoring/score.py`, `scoring/rubric.md`, `.mcp.json`) reports `all_pass=True` with byte-for-byte hashes identical to v1.0 close (2026-05-28); no rubric column added for FAIRNESS-08..12 — fairness coverage is asserted via fixture-set composition, not new rubric dimensions.

**Plans**: 12 plans (4 waves: Wave 0 prep × 1; Wave 1 captured × 3; Wave 2 synthetic × 3; Wave 3 framework variants × 4; Wave 4 finalize × 1)
- [x] 06-00-PLAN.md — Wave 0 test infrastructure + shared data.json + stage_walk preamble
- [ ] 06-01-PLAN.md — Wave 1 Wikipedia capture (S13/14/15/21/22)
- [ ] 06-02-PLAN.md — Wave 1 HN pagination capture (S16)
- [ ] 06-03-PLAN.md — Wave 1 DDG + Brave SERP capture (S12) — human-verify before commit
- [ ] 06-04-PLAN.md — Wave 2 synthetic e-commerce PDP + cart + verify (S9-S11)
- [ ] 06-05-PLAN.md — Wave 2 synthetic auth-walled login + dashboard (S17-S18)
- [ ] 06-06-PLAN.md — Wave 2 synthetic complex form fill + recovery (S19-S20)
- [ ] 06-07-PLAN.md — Wave 3 vanilla framework variant baseline (S26) — establishes DOM contract
- [ ] 06-08-PLAN.md — Wave 3 Vue 3 + Vite variant (S25) — Wave 3 package-legitimacy gate
- [ ] 06-09-PLAN.md — Wave 3 SvelteKit + adapter-static variant (S24)
- [ ] 06-10-PLAN.md — Wave 3 Next.js output:export variant + Client Component hydration marker (S23, FAIRNESS-09)
- [ ] 06-11-PLAN.md — Wave 4 finalize: append S9-S26 cells to stage_walk.md, defer FAIRNESS-11, phase-close audit
**UI hint**: no

### Phase 7: Harness portability + Linux v1.0 baseline

**Goal**: `scripts/run_mcp_session.sh` runs identically on macOS arm64 + Linux x86_64 (OS-detected `ulimit -v`); `bench/wave_close_check.py` passes the same sacrosanct-triad audit on both OSes; the v1.0 S1-S8 fixture set produces published Linux x86_64 numbers for the 5 MCPs whose Linux behavior is unknown (Playwright, browser-use-direct, chrome-devtools, lightpanda, firecrawl), establishing the honest cross-OS baseline that Phase 8's v1.1 cross-platform re-baseline depends on.
**Depends on**: Phase 6 (sacrosanct-triad audit needs the v1.1 fixture set in place but unchanged-from-v1.0 invariants must still hold — fixture additions are out-of-triad)
**Requirements**: HARNESS-10, HARNESS-11, HARNESS-12, VALIDATE-10
**Success Criteria** (what must be TRUE):

  1. `scripts/run_mcp_session.sh` contains an OS-detect branch (uname -s) setting `ulimit -v 4194304` on macOS (existing behavior preserved) and `ulimit -v 16777216` OR an explicit no-op-with-rationale-comment on Linux (HARNESS-10 per the v1.0.2 Hetzner finding); no separate Linux fork of the script exists.
  2. `bench/wave_close_check.py` exits 0 on BOTH macOS arm64 AND Linux x86_64 with identical sacrosanct-triad hashes (rubric, scoring engine, `.mcp.json` byte-for-byte vs v1.0 close); `candidate_count=7` and `rubric_columns=8` unchanged (HARNESS-11).
  3. `docs/RUNNING_ON_LINUX.md` is updated to cover the v1.1 expanded fixture surface (S9-S26 added to the recipe; fixture-set total size note updated to ≤ 50 MB) (HARNESS-12).
  4. `results/<date>-cross-platform/v1.0-linux/` contains evidence directories for all 5 unknown-Linux-behavior v1.0 candidates (playwright, browser-use-direct, chrome-devtools, lightpanda, firecrawl) — each with the same `scores.json` row shape v1.0 used, scored on S1-S8 with median-of-3 per FAIRNESS-01, capability + failure-attribution tags carried forward (VALIDATE-10).
  5. Linux baseline run does NOT modify any v1.0 published artifact (`results/2026-05-27-mcp-comparison.md`, `results/recommendations.md`, `results/2026-05-26/scores.json`) — `git diff main -- results/2026-05-27-mcp-comparison.md results/recommendations.md` produces zero output; new Linux numbers live exclusively under `results/<date>-cross-platform/`.

**Plans**: TBD
**UI hint**: no

### Phase 8: Re-validate v1.0 candidates on v1.1 fixtures

**Goal**: All 7 v1.0 MCPs have evidence directories + populated `scores.json` rows for the v1.1 fixture set (S9-S26) on BOTH macOS arm64 + Linux x86_64, with median-of-3 per FAIRNESS-01, correct N/A semantics for read-only candidates, vendor-fix-gated tracks (VALIDATE-04 browser-use-agent, VALIDATE-08 Obscura-Linux) running OR documented-as-still-broken with the gating ticket cited — turning the v1.1 fixture set into 7 (or 8 incl. agent-mode) comparable, defensible rows on the same 8-dim rubric.
**Depends on**: Phase 6 (fixtures must exist), Phase 7 (Linux harness must work; cross-platform run schema established)
**Requirements**: VALIDATE-01, VALIDATE-02, VALIDATE-03, VALIDATE-04, VALIDATE-05, VALIDATE-06, VALIDATE-07, VALIDATE-08, VALIDATE-09, VALIDATE-11, VALIDATE-12
**Success Criteria** (what must be TRUE):

  1. `results/<date>-v1.1/` contains complete evidence directories for all 7 v1.0 candidates (playwright, browser-use-direct, chrome-devtools, lightpanda, obscura-macos, firecrawl, cloakbrowser) on macOS arm64, each with 3-pass S9-S26 transcripts + median-of-3 `scores.json` row (VALIDATE-01, 02, 03, 05, 06, 07).
  2. `results/<date>-cross-platform/v1.1-linux/` contains complete evidence directories for all v1.0 candidates whose Linux behavior is in-scope on the v1.1 fixture set (VALIDATE-11), with the same row shape + median-of-3 contract; Linux-broken MCPs (obscura pending h4ckf0r0day/obscura#197 per VALIDATE-08) carry an explicit `SKIPPED.md` citing the gating ticket and the still-broken verdict — NOT a synthesized N/A.
  3. Vendor-fix-gated tracks are recorded with explicit gate-state evidence: `results/<date>-v1.1/browser-use-agent/` either contains a 3-pass agent-mode evidence directory (if `browser-use#4846` shipped; LLM key present per FAIRNESS-04 dual-row contract) OR a `SKIPPED.md` citing `browser-use#4846` + G-735 + GitHub issue #8 with the same shape v1.0 used for `LLM_KEY_ABSENT` (VALIDATE-04); `results/<date>-cross-platform/v1.1-linux/obscura/` either contains a 3-pass Linux evidence directory (if `h4ckf0r0day/obscura#197` shipped) OR a `SKIPPED.md` citing that ticket + G-737 (VALIDATE-08).
  4. `results/<date>-cross-platform.md` publishes the per-MCP × per-OS comparison matrix (rows: candidates; cols: macOS arm64 v1.0 composite, Linux x86_64 v1.0 composite, macOS arm64 v1.1 composite, Linux x86_64 v1.1 composite); SKIPPED cells carry the gating-ticket citation inline (VALIDATE-12).
  5. v1.0 + v1.1 stage-walk results are published side-by-side per MCP in every per-MCP evidence directory — `results/<date>-v1.1/<mcp>/STAGE_WALK.md` references the v1.0 row for the same MCP and links to its v1.0 `DEEP_ANALYSIS.md` (VALIDATE-09); sacrosanct triad unchanged (`bench/wave_close_check.py all_pass=True`, `candidate_count=7` unless Phase 9's CANDIDATE-03 atomic commit has already landed promoting to 8).

**Plans**: TBD
**UI hint**: no

### Phase 9: BrowserMCP candidate decision (G-744)

**Goal**: The G-744 BrowserMCP candidate decision is recorded as a written verdict (include-as-8th / include-with-separate-category / exclude-with-rationale) and — if INCLUDE — `.mcp.json` is atomically extended to 8 candidates, `bench/wave_close_check.py` baseline lifted from `candidate_count=7` → `candidate_count=8` in the same commit, and BrowserMCP scored on full S1-S26 with median-of-3 (replacing the v1.0.3 single-pass exploratory composite 6.20).
**Depends on**: Phase 6 (S9-S26 fixtures must exist before BrowserMCP can be scored on them); independent of Phase 7/8 and runs in parallel with Phase 8 if the decision lands EXCLUDE or runs after Phase 8 if INCLUDE (avoids candidate-count drift during the per-MCP re-validation pass).
**Requirements**: CANDIDATE-01, CANDIDATE-02, CANDIDATE-03
**Success Criteria** (what must be TRUE):

  1. `.planning/phases/<phase-9-dir>/DECISION.md` (or equivalent committed evidence file) records the G-744 verdict with one of three explicit outcomes: INCLUDE-AS-8TH, INCLUDE-WITH-EXTENSION-ATTACHED-CATEGORY, or EXCLUDE; the file cites the v1.0.3 exploratory composite 6.20 and the rationale for the chosen path (CANDIDATE-01).
  2. **If INCLUDE** — `results/<date>-v1.1/browsermcp/` contains a 3-pass median-of-3 evidence directory for S1-S26 with the same row shape v1.0 used (CANDIDATE-02); `scores.json` carries the BrowserMCP row with capability tag + failure-attribution per FAIRNESS-04 + FAIRNESS-05.
  3. **If INCLUDE** — `.mcp.json` is extended to 8 candidates in a single atomic commit that also bumps `bench/wave_close_check.py` baseline from `candidate_count=7` → `candidate_count=8` and updates any test asserting the value (CANDIDATE-03); pre-commit diff shows BOTH changes in the same commit (never silent, never split).
  4. **If EXCLUDE** — `.mcp.json` is byte-for-byte unchanged from v1.0 close; `bench/wave_close_check.py` reports `candidate_count=7` unchanged; the DECISION.md rationale explicitly addresses why v1.0.3's exploratory finding does not warrant promotion to a scored row.
  5. Whichever branch is taken, downstream Phase 11 synthesis can reference the decision without re-litigation — `results/<date>-v1.1-comparison.md` is built against the decision-time `.mcp.json` candidate roster and `results/<date>-v1.1-recommendations.md` reflects the decision in the graduation tiers.

**Plans**: TBD
**UI hint**: no

### Phase 10: Stealth axis (TLS fingerprint + bot-detection adversary)

**Goal**: Every in-scope v1.1 candidate has a captured JA3/JA3n/JA4/scrapfly_fp fingerprint (vs the v1.0.2 real-Chrome baseline `ja4_hash: 3fc5444b6956`) and a per-detector pass/fail verdict against Cloudflare (`nowsecure.nl/`), DataDome (G2 reviews canary), reCAPTCHA v2 (Google demo), and Akamai (`akamai.com`); a Stealth Verdict column is added to the published comparison report as a **separate axis from composite** — a real-Chrome MCP that fails Cloudflare does NOT receive a composite penalty (preserves v1.0 rubric byte-for-byte lock).
**Depends on**: Phase 6 (fixture set frozen so the candidate roster is settled); Phase 9 (BrowserMCP decision so stealth runs include the correct row count). Runs in parallel with Phase 8 (different probe targets — live URLs for stealth axis, loopback fixtures for composite — no contention).
**Requirements**: STEALTH-01, STEALTH-02, STEALTH-03, STEALTH-04, STEALTH-05, STEALTH-06, STEALTH-07, STEALTH-08, STEALTH-09, STEALTH-10
**Success Criteria** (what must be TRUE):

  1. `results/<date>-tls/per-mcp.json` contains a fingerprint record for every in-scope candidate: each record has fields `ja3`, `ja3n`, `ja4`, `scrapfly_fp`, `baseline_match` (boolean — comparison vs `ja4_hash: 3fc5444b6956`), and `capture_method` (scrapfly | tls.peet.ws fallback per STEALTH-04); cloakbrowser captured against the public Greenhouse/Ashby probe target ONLY per the sandbox-only invariant.
  2. `results/<date>-tls/per-mcp.json` includes the Scrapfly reference-set cross-check verdict per MCP (`real_chrome` / `headless_chrome` / `automation_framework` / `unknown`) drawn from the live Scrapfly `?extended=1` payload (STEALTH-02, STEALTH-03).
  3. `results/<date>-adversary/` contains a per-MCP × per-detector pass/fail matrix as JSON + Markdown — every cell records: status code, mitigation-header presence (`cf-mitigated`, `x-datadome`, `_abck`, etc. per STEALTH-05..08), challenge-HTML detection, and captured-cookie inventory; methodology disclaimer block names the Cloudflare ruleset version + DataDome tier + reCAPTCHA challenge type captured on probe date.
  4. `results/<date>-v1.1-comparison.md` carries a Stealth Verdict column that is **NOT** an input to `composite`; `scoring/score.py` is byte-for-byte unchanged from v1.0 (`bench/wave_close_check.py` sacrosanct-triad audit reports `all_pass=True`); STEALTH-10 verified by inspection: the comparison report's stealth column lives in a separate section from the 8-dim rubric table.
  5. Live-URL probes never touch authenticated host pages — cloakbrowser stealth runs only hit the public Greenhouse + Ashby fixtures + the bot-detection canary URLs (global sandbox-only policy); evidence directory for cloakbrowser stealth probes contains a `SANDBOX_PROOF.md` analogous to v1.0 Plan 02-06's pattern.

**Plans**: TBD
**UI hint**: no

### Phase 11: v1.1 synthesis + publication

**Goal**: The public-facing v1.1 artifacts ship — dual-row scoreboard (v1.0 + v1.1 composite per MCP), Stealth Verdict column as a separate axis, cross-platform matrix per MCP × per OS, per-MCP DEEP_ANALYSIS-v1.1.md, updated `docs/REPRODUCIBILITY.md`, and a v1.1 GitHub Release — so external readers can confirm the v1.1 verdict against the same fixtures every candidate was measured against, and Stage 2 (`terminal-craft`) can read the updated graduation tiers without re-litigating v1.0.
**Depends on**: Phase 8 (v1.1 composite rows must exist), Phase 9 (candidate roster must be locked), Phase 10 (stealth verdict column must exist)
**Requirements**: REPORT-13, REPORT-14, REPORT-15, REPORT-16, REPORT-17, REPORT-18
**Success Criteria** (what must be TRUE):

  1. `results/<date>-v1.1-comparison.md` publishes the 8-dim × N-MCP composite table (N=7 or 8 depending on Phase 9 outcome) with an explicit `v1.0 composite (macOS arm64)` column preserved adjacent to the v1.1 composite column (REPORT-13); reading order is `MCP | v1.0 macOS | v1.1 macOS | v1.1 Linux | Stealth Verdict`; sacrosanct triad audit (`bench/wave_close_check.py all_pass=True`) passes against this committed report.
  2. `results/<date>-v1.1-recommendations.md` publishes updated graduation tiers (PRIMARY / SECONDARY / SANDBOX-ONLY / SKIP) reflecting v1.1 evidence + the stealth verdict per MCP; cloakbrowser carries the same SANDBOX-ONLY callout + 3-mention sandwich pattern v1.0 used (REPORT-14); the file links to v1.0 `results/recommendations.md` so the v1.0 verdict remains discoverable.
  3. Per-MCP `results/<date>-v1.1/<mcp>/DEEP_ANALYSIS-v1.1.md` exists for every scored row (7-9 files depending on Phase 9 + VALIDATE-04 outcomes), each comparing the MCP's v1.1 composite to the v1.0 macOS composite, naming the v1.1 fixture set winners + losers, and citing the v1.0.x findings the MCP encountered (REPORT-15).
  4. `README.md` scoreboard is updated to show v1.1 composite alongside v1.0 (dual-row per MCP) + the Stealth Verdict column (REPORT-16); `docs/REPRODUCIBILITY.md` is updated with the v1.1 fixture set + cross-platform recipe (REPORT-17).
  5. v1.1 GitHub Release is published containing the full v1.1 evidence + scoreboard + stealth verdict per MCP (REPORT-18); wave-close ritual (SAFETY-05-equivalent) confirms candidate_count matches Phase 9 outcome (7 or 8), rubric_columns=8 unchanged, no Stage 2 commits in `terminal-craft`, sacrosanct-triad hashes byte-for-byte vs v1.0 close.

**Plans**: TBD
**UI hint**: no

## Dependencies

```
Phase 6 (Fixtures)
   │
   ├──► Phase 7 (Harness portability + Linux v1.0 baseline)
   │       │
   │       └──► Phase 8 (Re-validate v1.0 candidates on v1.1, macOS + Linux)
   │               │
   │               └──► Phase 11 (Synthesis + publication)
   │
   ├──► Phase 9 (BrowserMCP decision — runs parallel with Phase 8 if EXCLUDE; after Phase 8 if INCLUDE)
   │       │
   │       └──► Phase 11
   │
   └──► Phase 10 (Stealth axis — runs parallel with Phase 8, independent probe targets)
           │
           └──► Phase 11
```

**Execution notes:**

- **Phase 6 is the hard prerequisite** for everything else — no MCP can be re-scored on fixtures that don't exist yet.
- **Phase 7 must precede Phase 8's Linux runs** — `ulimit -v` OS-detect is the gating fix for Linux harness execution.
- **Phase 8 runs in parallel with Phase 10** — composite track uses loopback fixtures; stealth track uses live probe URLs; no resource contention.
- **Phase 9 sequencing depends on outcome** — if INCLUDE, the `.mcp.json` extension must land BEFORE Phase 8's per-MCP runs to avoid candidate-roster drift mid-pass. If EXCLUDE, Phase 9 can ship anytime before Phase 11.
- **Vendor-fix gates** (browser-use#4846 for VALIDATE-04, h4ckf0r0day/obscura#197 for VALIDATE-08) are tracked inside Phase 8; both tracks are conditionally skippable with explicit `SKIPPED.md` citing the gating ticket — phase ships either way.

## Sacrosanct Invariants (v1.1)

These are **byte-for-byte locked from v1.0 close (2026-05-28)** and audited by `bench/wave_close_check.py` at every plan boundary:

- `scoring/score.py` — unchanged through v1.1
- `scoring/rubric.md` — unchanged through v1.1 (8 dimensions, weights, composite formula)
- `.mcp.json` — unchanged through v1.1 **EXCEPT** the single atomic CANDIDATE-03 commit if Phase 9 lands INCLUDE (7 → 8 candidates, baseline lifted in the same commit)
- `rubric_columns=8` — unchanged through v1.1 (stealth axis is a separate column, NOT a rubric dimension)
- `candidate_count=7` — unchanged through v1.1 unless CANDIDATE-03 lifts it to 8

Stealth axis additions (Phase 10) live **alongside** the composite, never inside it — a real-Chrome MCP that fails Cloudflare does NOT receive a composite penalty.

## Progress

| Phase                                                | Milestone | Plans Complete | Status      | Completed  |
| ---------------------------------------------------- | --------- | -------------- | ----------- | ---------- |
| 1. Harness Foundation                                | v1.0      | 7/7            | Complete    | 2026-05-26 |
| 2. Per-MCP Scoring Runs                              | v1.0      | 7/7            | Complete    | 2026-05-27 |
| 3. Cross-Cutting Measurements                        | v1.0      | 5/5            | Complete    | 2026-05-27 |
| 4. Synthesis                                         | v1.0      | 6/6            | Complete    | 2026-05-27 |
| 5. Close v1.0 governance debt                        | v1.0      | 5/5            | Complete    | 2026-05-28 |
| 6. Fixture authoring (S9-S26)                        | v1.1      | 1/12 | In Progress|  |
| 7. Harness portability + Linux v1.0 baseline         | v1.1      | 0/0            | Not started | -          |
| 8. Re-validate v1.0 candidates on v1.1 fixtures      | v1.1      | 0/0            | Not started | -          |
| 9. BrowserMCP candidate decision (G-744)             | v1.1      | 0/0            | Not started | -          |
| 10. Stealth axis (TLS fingerprint + bot-detection)   | v1.1      | 0/0            | Not started | -          |
| 11. v1.1 synthesis + publication                     | v1.1      | 0/0            | Not started | -          |
