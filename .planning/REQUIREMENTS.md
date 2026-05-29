# Requirements — v1.1 General-purpose fixture expansion + stealth axis

**Milestone:** v1.1
**Status:** Defining (post-`/gsd:new-milestone`)
**Predecessor:** v1.0 (shipped 2026-05-28); v1.0.x patches through v1.0.3 (2026-05-29)
**Source documents:**
- `~/Projects/web-agent-comparison-launch-drafts/05-v1.1-general-fixtures-proposal.md` — fixture-expansion design proposal
- v1.0.x tracking tickets: G-737 (Obscura Linux re-test), G-738 (bot-detection adversary), G-739 (TLS fingerprint), G-744 (BrowserMCP candidate decision)
- v1.0.3 finding: React 404 cascade hits all real-Chrome MCPs identically → fixtures must differentiate via `evaluate`/request-interception availability

**Core invariants** (carried from v1.0; NOT requirements of v1.1, just locked context):
- Rubric (`scoring/rubric.md`) byte-for-byte unchanged from v1.0
- Scoring engine (`scoring/score.py`) byte-for-byte unchanged from v1.0
- Existing 7 candidates in `.mcp.json` byte-for-byte unchanged from v1.0
- Stage IDs S1-S8 locked in `prompts/stage_walk.md`; new stages begin at S9
- All fixtures byte-for-byte loopback only (no live URLs in scored harness)

---

## v1.1 Requirements

### Fixture additions (S9+)

- [ ] **FIXTURE-01**: Stage S9 — e-commerce product detail page (PDP) extraction (synthetic Shopify-equivalent product page; ≤ 5 MB)
- [ ] **FIXTURE-02**: Stage S10 — e-commerce cart-add interaction with AJAX state mutation
- [ ] **FIXTURE-03**: Stage S11 — verify cart state after S10 (post-mutation extraction)
- [ ] **FIXTURE-04**: Stage S12 — SERP parsing (DuckDuckGo HTML SERP + Brave SERP snapshots for comparison)
- [ ] **FIXTURE-05**: Stage S13 — long-form content body extraction (Wikipedia article snapshot, CC BY-SA)
- [ ] **FIXTURE-06**: Stage S14 — table-in-article + infobox extraction (same Wikipedia fixture as S13)
- [ ] **FIXTURE-07**: Stage S15 — footnote / reference-list harvesting (same fixture)
- [ ] **FIXTURE-08**: Stage S16 — multi-page pagination (paginated forum index or changelog, 3-5 pages, ~20 items/page, dedup on aggregation)
- [ ] **FIXTURE-09**: Stage S17 — synthetic auth-walled login form submit (no real auth; snapshot-based post-auth-state rehydration)
- [ ] **FIXTURE-10**: Stage S18 — post-auth dashboard widget extraction (same synthetic auth-walled fixture)
- [ ] **FIXTURE-11**: Stage S19 — complex multi-section form fill (multi-select + search + date range + dependent fields)
- [ ] **FIXTURE-12**: Stage S20 — recover from client-side validation error in the complex form (S19 sets up; S20 tests error-state recovery)
- [ ] **FIXTURE-13**: Stage S21 — sortable HTML table extraction as records
- [ ] **FIXTURE-14**: Stage S22 — sort-by-column then re-extract (same table fixture)
- [ ] **FIXTURE-15**: Stage S23 — same-content extraction from Next.js SSR-with-hydration fixture
- [ ] **FIXTURE-16**: Stage S24 — same-content extraction from SvelteKit fixture
- [ ] **FIXTURE-17**: Stage S25 — same-content extraction from Vue 3 SPA fixture
- [ ] **FIXTURE-18**: Stage S26 — same-content extraction from vanilla static HTML fixture (baseline for the framework comparison)

### Fixture design principles

- [ ] **DESIGN-01**: Read-vs-drive parity — v1.1 fixture set lands roughly 50/50 between "extract structured data" and "drive UI to complete task" (v1.0 was 60/40 drive/read)
- [ ] **DESIGN-02**: Multi-page is its own muscle — at least one fixture (FIXTURE-08) requires state carried across 3+ pages
- [ ] **DESIGN-03**: Per-fixture use-case tag — every new fixture has a one-sentence "what agent task does this proxy" tag in fixtures/PROVENANCE.md

### Fairness (continued from v1.0; new constraints)

- [ ] **FAIRNESS-08**: Rendering archetype coverage — fixture set includes at least one each of classic server-rendered HTML (S15 from v1.0 baseline), React 18 / Next.js SSR-with-hydration (S23), SvelteKit (S24), Vue 3 SPA (S25), vanilla static (S26)
- [ ] **FAIRNESS-09**: Workload coverage — each new fixture exercises at least one rubric dimension that S1-S8 does not stress, or stresses it in a categorically different way (table extraction ≠ form extraction even if both score Data Quality)
- [ ] **FAIRNESS-10**: No MCP-specific bias — no fixture may be selected because it is known to favor any one v1.0 MCP; firecrawl's SSR strength does not exempt the set from including hard JS fixtures
- [~] **FAIRNESS-11**: Internationalization — at least one non-English fixture and at least one fixture with non-ASCII characters in extracted fields. **Deferred to v1.2** per Phase 6 CONTEXT.md D-15 (2026-05-29 discuss-phase decision). v1.1's report carries an explicit "i18n not measured — see v1.2" callout.
- [ ] **FAIRNESS-12**: Semantic vs div-soup — at least one fixture with rich ARIA + semantic HTML5 and at least one intentionally div-soup; MCPs that lean on accessibility tree should be measurably better on the first

### Reproducibility (continued from v1.0)

- [ ] **REPRO-09**: Byte-for-byte loopback only — every v1.1 fixture is a frozen snapshot served from `127.0.0.1` via the existing `fixtures/` infrastructure
- [ ] **REPRO-10**: PII-scrubbed at capture — any fixture captured from a real session is scrubbed via `bench/scrub_artifacts.py` (extended for new fixture surface) before commit
- [ ] **REPRO-11**: Snapshot size budget — single fixture ≤ 5 MB on disk; full v1.1 fixture set ≤ 50 MB
- [ ] **REPRO-12**: License-clean — Wikipedia (CC BY-SA), arXiv abstracts, public-domain stats, OSS project pages, intentionally-authored synthetic fixtures only; no paywalled, copyright-aggressive, or robots.txt-hostile sources
- [ ] **REPRO-13**: Cross-platform parity — v1.0 + v1.1 fixtures run identically on macOS arm64 and Linux x86_64 (no platform-specific failures in the harness itself; vendor bugs are out of scope)

### Re-validation of v1.0 candidates against v1.1 fixtures

- [ ] **VALIDATE-01**: Playwright re-scored on S9-S26 with median-of-3 per FAIRNESS-01
- [ ] **VALIDATE-02**: Lightpanda re-scored on S9-S26 (expect categorical N/A on JS-requiring fixtures)
- [ ] **VALIDATE-03**: browser-use (direct mode) re-scored on S9-S26
- [ ] **VALIDATE-04**: browser-use (agent mode) — re-scored only if upstream browser-use#4846 ships a fix per v1.0.1 GitHub issue #8 / G-735; otherwise documented as still-broken
- [ ] **VALIDATE-05**: Chrome DevTools MCP re-scored on S9-S26
- [ ] **VALIDATE-06**: Firecrawl re-scored on S9-S26 (cloud-can't-reach-loopback constraint persists; document new N/A stages)
- [ ] **VALIDATE-07**: Cloakbrowser re-scored on S9-S26 (sandbox-only callout per SAFETY-04 holds)
- [ ] **VALIDATE-08**: Obscura re-scored on S9-S26 (macOS only until h4ckf0r0day/obscura#197 fixes Linux per G-737)
- [ ] **VALIDATE-09**: v1.0 + v1.1 stage-walk results published side-by-side per MCP (preserves comparability claim)

### BrowserMCP candidate decision

- [ ] **CANDIDATE-01**: Formal decision on BrowserMCP as 8th v1.1 candidate — include with `extension-attached` capability tag, add separate "authenticated-session" category in rubric, OR keep out (track via G-744)
- [ ] **CANDIDATE-02**: If included — BrowserMCP scored on full S1-S26 with median-of-3 (v1.0.3 was single-pass exploratory at composite 6.20)
- [ ] **CANDIDATE-03**: If included — `.mcp.json` extended to 8-candidate roster; `bench/wave_close_check.py` baseline updated from `candidate_count=7` → `candidate_count=8` (atomic commit, never silent)

### Stealth axis — TLS fingerprint capture (G-739)

- [ ] **STEALTH-01**: TLS fingerprint capture (JA3 / JA3n / JA4 / scrapfly_fp) per MCP via `tools.scrapfly.io/api/fp/ja3?extended=1` probe
- [ ] **STEALTH-02**: Per-MCP fingerprint cross-reference against the real-Chrome baseline captured in v1.0.2 (`ja4_hash: 3fc5444b6956`)
- [ ] **STEALTH-03**: Published `results/<date>-tls/per-mcp.json` containing each MCP's fingerprint + match-vs-baseline verdict + Scrapfly reference-set cross-check
- [ ] **STEALTH-04**: Fallback probe via `tls.peet.ws/api/all` documented for hosts where Scrapfly is unreachable

### Stealth axis — bot-detection adversary set (G-738)

- [ ] **STEALTH-05**: Per-MCP probe against Cloudflare canary (`nowsecure.nl/`) — capture status, `cf-mitigated` header, `cf-ray`, challenge HTML presence
- [ ] **STEALTH-06**: Per-MCP probe against DataDome canary (G2 reviews or equivalent) — capture status, `x-datadome-cid` cookie, `x-datadome` header, `_dd_s` cookie
- [ ] **STEALTH-07**: Per-MCP probe against reCAPTCHA v2 challenge (Google demo page) — capture page-side `grecaptcha.getResponse()` shape + visual challenge classification
- [ ] **STEALTH-08**: Per-MCP probe against Akamai Bot Manager (`akamai.com`) — capture `_abck` cookie, `bm_sz` cookie, status
- [ ] **STEALTH-09**: Published `results/<date>-adversary/` per-MCP × per-detector pass/fail matrix with methodology disclaimer (Cloudflare ruleset version, DataDome tier, etc.)
- [ ] **STEALTH-10**: Stealth verdict column added to the published comparison report as a **separate axis** from composite (does NOT modify composite calculation — preserves v1.0 rubric lock per the locked-rubric invariant)

### Harness portability

- [ ] **HARNESS-10**: `scripts/run_mcp_session.sh` OS-detection: `ulimit -v` set to 4 GB on macOS (existing) and 16 GB OR dropped on Linux (the v1.0.2 Hetzner finding) — implementation in same script; no separate Linux fork
- [ ] **HARNESS-11**: `bench/wave_close_check.py` cross-platform invariants — same sacrosanct checks (rubric, scoring, mcp candidate count) pass identically on macOS + Linux
- [ ] **HARNESS-12**: Container/Docker recipe (`docs/RUNNING_ON_LINUX.md` already in repo from v1.0.2) updated for v1.1's expanded fixture surface

### Cross-platform re-baseline

- [ ] **VALIDATE-10**: v1.0 fixtures (S1-S8) re-run on Linux x86_64 for all v1.0 candidates whose Linux behavior is unknown (Playwright, browser-use-direct, chrome-devtools, lightpanda, firecrawl) — provides honest cross-OS numbers
- [ ] **VALIDATE-11**: v1.1 fixtures (S9-S26) run on BOTH macOS arm64 and Linux x86_64 for all candidates
- [ ] **VALIDATE-12**: Published `results/<date>-cross-platform.md` per-MCP × per-OS comparison

### Published artifacts

- [ ] **REPORT-13**: `results/<date>-v1.1-comparison.md` — 8-dim × N-MCP composite table (v1.0 + v1.1 stages combined) with explicit v1.0-comparison column preserved
- [ ] **REPORT-14**: `results/<date>-v1.1-recommendations.md` — updated graduation tiers (PRIMARY / SECONDARY / SANDBOX-ONLY / SKIP) reflecting v1.1 evidence
- [ ] **REPORT-15**: Per-MCP DEEP_ANALYSIS-v1.1.md (8-9 files) — comparison vs v1.0 macOS composite + v1.0.x findings + v1.1 stage outcomes
- [ ] **REPORT-16**: README scoreboard updated with v1.1 composite alongside v1.0 (dual-row per MCP)
- [ ] **REPORT-17**: `docs/REPRODUCIBILITY.md` updated for v1.1 fixture set + cross-platform recipe
- [ ] **REPORT-18**: v1.1 GitHub release with full evidence + scoreboard + stealth verdict per MCP

---

## Future Requirements (Deferred — v1.2 or later)

- **FAIRNESS-11 (i18n)** if scope tight — non-English + non-ASCII fixtures
- **FIXTURE-19**: Media-heavy / lazy-loaded fixtures (S27)
- **FIXTURE-20**: Iframe-embedded content (S28-S29)
- **FIXTURE-21**: PDF rendering (S32 stretch)
- **FAIRNESS-13**: rubric re-weighting (Interaction Depth 2× → 3×, JS Rendering 1× → 2×) — belongs in v2.0 with explicit "v1 vs v2 not directly comparable" disclosure
- **Vendor courtesy disclosure (OUTREACH-01/02 deferred from v1.0)** — only if v1.1's stealth axis surfaces vendor-confidential findings worth pre-publication courtesy

## Out of Scope (Explicitly excluded from v1.1)

- **Rubric reset or re-weighting** — v1.0 rubric byte-for-byte locked; rubric reset belongs in v2.0
- **New v1.0 candidate additions other than BrowserMCP** — the 7-MCP v1.0 set + (optional) BrowserMCP defines v1.1's candidate scope
- **Skyvern / Manus / Comet / other app-level agents** — covered in 2026-03-31 wave; v1.1 stays MCP-layer
- **TLS-impersonation libraries** (curl_cffi, undici hacks) — we test what each MCP ships, not what could be hacked in
- **Adversary-evasion source patches** to any MCP — same reason
- **Container build / signing / supply-chain hardening** for the harness itself — separate engineering concern, not a v1.1 deliverable

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIXTURE-01 | Phase 6 | Pending |
| FIXTURE-02 | Phase 6 | Pending |
| FIXTURE-03 | Phase 6 | Pending |
| FIXTURE-04 | Phase 6 | Pending |
| FIXTURE-05 | Phase 6 | Pending |
| FIXTURE-06 | Phase 6 | Pending |
| FIXTURE-07 | Phase 6 | Pending |
| FIXTURE-08 | Phase 6 | Pending |
| FIXTURE-09 | Phase 6 | Pending |
| FIXTURE-10 | Phase 6 | Pending |
| FIXTURE-11 | Phase 6 | Pending |
| FIXTURE-12 | Phase 6 | Pending |
| FIXTURE-13 | Phase 6 | Pending |
| FIXTURE-14 | Phase 6 | Pending |
| FIXTURE-15 | Phase 6 | Pending |
| FIXTURE-16 | Phase 6 | Pending |
| FIXTURE-17 | Phase 6 | Pending |
| FIXTURE-18 | Phase 6 | Pending |
| DESIGN-01 | Phase 6 | Pending |
| DESIGN-02 | Phase 6 | Pending |
| DESIGN-03 | Phase 6 | Pending |
| FAIRNESS-08 | Phase 6 | Pending |
| FAIRNESS-09 | Phase 6 | Pending |
| FAIRNESS-10 | Phase 6 | Pending |
| FAIRNESS-11 | Phase 6 | Pending |
| FAIRNESS-12 | Phase 6 | Pending |
| REPRO-09 | Phase 6 | Pending |
| REPRO-10 | Phase 6 | Pending |
| REPRO-11 | Phase 6 | Pending |
| REPRO-12 | Phase 6 | Pending |
| REPRO-13 | Phase 6 | Pending |
| HARNESS-10 | Phase 7 | Pending |
| HARNESS-11 | Phase 7 | Pending |
| HARNESS-12 | Phase 7 | Pending |
| VALIDATE-10 | Phase 7 | Pending |
| VALIDATE-01 | Phase 8 | Pending |
| VALIDATE-02 | Phase 8 | Pending |
| VALIDATE-03 | Phase 8 | Pending |
| VALIDATE-04 | Phase 8 | Pending (gated on browser-use#4846) |
| VALIDATE-05 | Phase 8 | Pending |
| VALIDATE-06 | Phase 8 | Pending |
| VALIDATE-07 | Phase 8 | Pending |
| VALIDATE-08 | Phase 8 | Pending (gated on h4ckf0r0day/obscura#197) |
| VALIDATE-09 | Phase 8 | Pending |
| VALIDATE-11 | Phase 8 | Pending |
| VALIDATE-12 | Phase 8 | Pending |
| CANDIDATE-01 | Phase 9 | Pending |
| CANDIDATE-02 | Phase 9 | Pending |
| CANDIDATE-03 | Phase 9 | Pending |
| STEALTH-01 | Phase 10 | Pending |
| STEALTH-02 | Phase 10 | Pending |
| STEALTH-03 | Phase 10 | Pending |
| STEALTH-04 | Phase 10 | Pending |
| STEALTH-05 | Phase 10 | Pending |
| STEALTH-06 | Phase 10 | Pending |
| STEALTH-07 | Phase 10 | Pending |
| STEALTH-08 | Phase 10 | Pending |
| STEALTH-09 | Phase 10 | Pending |
| STEALTH-10 | Phase 10 | Pending |
| REPORT-13 | Phase 11 | Pending |
| REPORT-14 | Phase 11 | Pending |
| REPORT-15 | Phase 11 | Pending |
| REPORT-16 | Phase 11 | Pending |
| REPORT-17 | Phase 11 | Pending |
| REPORT-18 | Phase 11 | Pending |

**Coverage:** 65/65 requirements mapped to exactly one phase. No orphans. No duplicates.

### Phase Coverage Summary

| Phase | Requirements | Count |
|-------|--------------|-------|
| Phase 6 (Fixture authoring) | FIXTURE-01..18, DESIGN-01..03, FAIRNESS-08..12, REPRO-09..13 | 31 |
| Phase 7 (Harness portability + Linux v1.0 baseline) | HARNESS-10..12, VALIDATE-10 | 4 |
| Phase 8 (Re-validate v1.0 on v1.1) | VALIDATE-01..09, VALIDATE-11, VALIDATE-12 | 11 |
| Phase 9 (BrowserMCP decision) | CANDIDATE-01..03 | 3 |
| Phase 10 (Stealth axis) | STEALTH-01..10 | 10 |
| Phase 11 (Synthesis + publication) | REPORT-13..18 | 6 |
| **Total v1.1 requirements mapped** | | **65** |

### Coverage Summary (by category)

| Category | Requirements | Count |
|----------|--------------|-------|
| FIXTURE | FIXTURE-01..18 | 18 |
| DESIGN | DESIGN-01..03 | 3 |
| FAIRNESS | FAIRNESS-08..12 | 5 |
| REPRO | REPRO-09..13 | 5 |
| VALIDATE | VALIDATE-01..12 | 12 |
| CANDIDATE | CANDIDATE-01..03 | 3 |
| STEALTH | STEALTH-01..10 | 10 |
| HARNESS | HARNESS-10..12 | 3 |
| REPORT | REPORT-13..18 | 6 |
| **Total v1.1 requirements** | | **65** |

---

## Definition of Done (v1.1)

This wave ships when:

1. All 65 v1.1 requirements above are `[x]` checked OR explicitly converted to v1.2+ with a written reason
2. `results/<date>-v1.1-comparison.md` and `results/<date>-v1.1-recommendations.md` are committed
3. README updated with v1.1 scoreboard (dual-row per MCP showing v1.0 + v1.1 composites)
4. BrowserMCP candidate decision is recorded (in scores.json or in EXPLORATORY/RECOMMENDATIONS.md, depending on the decision)
5. Stealth verdict per MCP published as a separate axis from composite
6. Cross-platform re-baseline published with per-MCP × per-OS numbers
7. `bench/wave_close_check.py all_pass=True` (potentially with `candidate_count=8` if BrowserMCP joined; rubric_columns=8 unchanged; sacrosanct triad byte-for-byte vs v1.0)
8. 309/309 test baseline holds (plus any new tests added for v1.1 fixtures / scoring extensions)
9. v1.1 GitHub Release published
10. Wave-close ritual (SAFETY-05-equivalent) confirms no scope-creep snuck in
