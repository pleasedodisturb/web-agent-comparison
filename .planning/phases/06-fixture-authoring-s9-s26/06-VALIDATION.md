---
phase: 6
slug: fixture-authoring-s9-s26
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `06-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | unittest (Python stdlib) + bash test scripts |
| **Config file** | none — tests invoked directly via subprocess |
| **Quick run command** | `bash tests/test_snapshot_serves.sh && uv run python -m bench.scrub_artifacts fixtures/snapshots/<new-slug>/` |
| **Full suite command** | `uv run python -m unittest discover -s tests && bash tests/test_snapshot_serves.sh && bash tests/test_provenance_complete.sh && bash tests/test_size_budget.sh && uv run python -m unittest tests.test_stage_walk_balance && uv run python -m bench.scrub_artifacts fixtures/snapshots/ && uv run python -m bench.wave_close_check` |
| **Estimated runtime** | ~20-30s full suite; ~5-10s per-task quick run |

---

## Sampling Rate

- **After every task commit:** Run `bash tests/test_snapshot_serves.sh` + per-fixture `scrub_artifacts` + `wave_close_check` (~5-10s)
- **After every plan wave:** Run full suite (~20-30s)
- **Before `/gsd:verify-work`:** Full suite green AND `du -sh fixtures/snapshots/` ≤ 50 MB AND every PROVENANCE.md has all required v1.1 fields
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-00-01 | 00 | 0 | wave-0 infra | — | scrub script handles new allow-list shape | unit | `uv run python -m unittest tests.test_scrub_artifacts -v` | ✅ | ⬜ pending |
| 06-00-02 | 00 | 0 | DESIGN-01, DESIGN-02 | — | stage-walk balance grep passes | unit | `uv run python -m unittest tests.test_stage_walk_balance -v` | ❌ W0 | ⬜ pending |
| 06-00-03 | 00 | 0 | DESIGN-03, FAIRNESS-08 | — | every PROVENANCE has required v1.1 fields | grep | `bash tests/test_provenance_complete.sh` | ❌ W0 | ⬜ pending |
| 06-00-04 | 00 | 0 | REPRO-11 | — | size budget enforced | grep | `bash tests/test_size_budget.sh` | ❌ W0 | ⬜ pending |
| 06-CAP-WIKI | capture | 1 | FIXTURE-05, FIXTURE-06, FIXTURE-07, FIXTURE-13, FIXTURE-14, REPRO-12 | — | Wikipedia article HTTP 200 + body > 50KB + ≤ 5MB + CC BY-SA | smoke | `curl -fs http://127.0.0.1:8765/s13_15_21_22_wikipedia/ \| wc -c` | covered by 06-00-01 | ⬜ pending |
| 06-CAP-HN | capture | 1 | FIXTURE-08, DESIGN-02, REPRO-12 | — | 5-page HN serves; relative-link rewrite verified | smoke + grep | `for P in 1 2 3 4 5; do curl -fs ".../p${P}.html"; done` + `grep -q "p2.html" p1.html` | covered by 06-00-01 | ⬜ pending |
| 06-CAP-SERP | capture | 1 | FIXTURE-04, REPRO-12 | robots.txt | DDG + Brave SERP served; PROVENANCE notes robots.txt posture | smoke + checkpoint | `curl -fs .../s12_serp_ddg/` + `curl -fs .../s12_serp_brave/` + manual `checkpoint:human-verify` before commit | covered by 06-00-01 | ⬜ pending |
| 06-SYN-ECOM | synthetic | 2 | FIXTURE-01, FIXTURE-02, FIXTURE-03, FAIRNESS-12 | — | PDP + cart + verify-cart HTTP 200; AJAX cart mutation deterministic; ARIA on PDP | smoke + manual | `curl -fs .../s09_ecommerce_pdp/` + harness-driven S10 round-trip | covered by 06-00-01 | ⬜ pending |
| 06-SYN-AUTH | synthetic | 2 | FIXTURE-09, FIXTURE-10, FAIRNESS-12 | session cookie integrity | login → cookie set → dashboard reads cookie; div-soup style intentional | smoke + manual | `curl -fs .../s17_18_auth_walled/login.html` + harness-driven S17→S18 flow | covered by 06-00-01 | ⬜ pending |
| 06-SYN-FORM | synthetic | 2 | FIXTURE-11, FIXTURE-12 | — | complex form serves; validation-error round-trip works | smoke + manual | `curl -fs .../s19_20_complex_form/` + harness-driven S19→S20 flow | covered by 06-00-01 | ⬜ pending |
| 06-FV-VANILLA | framework | 3 | FIXTURE-18, FAIRNESS-08 | — | vanilla static HTML serves 10 products | smoke + jq | `curl -fs .../s26_framework_variant_vanilla/ \| grep -c "data-product-id="` ≥ 10 | covered by 06-00-01 | ⬜ pending |
| 06-FV-VUE | framework | 3 | FIXTURE-17, FAIRNESS-08 | — | Vue 3 SPA bundle serves; entry + main chunk 200 | smoke | `curl -fs .../s25_framework_variant_vue/` + asset chunk curl | covered by 06-00-01 | ⬜ pending |
| 06-FV-SVELTE | framework | 3 | FIXTURE-16, FAIRNESS-08 | — | SvelteKit adapter-static bundle serves | smoke | `curl -fs .../s24_framework_variant_sveltekit/` + asset chunk curl | covered by 06-00-01 | ⬜ pending |
| 06-FV-NEXT | framework | 3 | FIXTURE-15, FAIRNESS-08, FAIRNESS-09 | — | Next.js `output: 'export'` bundle serves; observable SSR vs hydration delta via post-mount Client Component mutation | smoke | `curl -fs .../s23_framework_variant_nextjs/` + asset chunk curl + read-only-MCP cross-check (Phase 8) | covered by 06-00-01 | ⬜ pending |
| 06-FINAL-WALK | finalize | 4 | DESIGN-01, DESIGN-02, DESIGN-03 | — | stage_walk.md appends 18 cells; read/drive ~9:9; S16 cell requires ≥3 pages | grep | `uv run python -m unittest tests.test_stage_walk_balance` | covered by 06-00-02 | ⬜ pending |
| 06-FINAL-AUDIT | finalize | 4 | FAIRNESS-09, FAIRNESS-10, REPRO-09, REPRO-10, REPRO-11, REPRO-12, REPRO-13, FAIRNESS-11 | — | sacrosanct triad audit passes; size budget ≤50MB; FAIRNESS-11 deferred-to-v1.2 note in REQUIREMENTS.md | unit + manual | `uv run python -m bench.wave_close_check` + `du -sh fixtures/snapshots/` + REQUIREMENTS.md grep | covered by 06-00-04 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> Test-file paths above are scoped at the plan-group level (`06-CAP-*`, `06-SYN-*`, `06-FV-*`, `06-FINAL-*`); the planner expands these into per-task IDs and finalizes paths during plan generation. Wave 0 (`06-00-*`) tests are file-creation tasks that block all downstream waves.

---

## Wave 0 Requirements

- [ ] `tests/test_snapshot_serves.sh` — extend the `expected_dirs=()` list with the 12 new fixture roots: `s09_ecommerce_pdp`, `s12_serp_ddg`, `s12_serp_brave`, `s13_15_21_22_wikipedia`, `s16_hn_pagination`, `s17_18_auth_walled`, `s19_20_complex_form`, `s23_framework_variant_nextjs`, `s24_framework_variant_sveltekit`, `s25_framework_variant_vue`, `s26_framework_variant_vanilla`
- [ ] `tests/test_provenance_complete.sh` — verify every PROVENANCE.md has the 5 v1.1 required fields: `Source URL`, `License`, `Agent-task tag` (DESIGN-03), `Rendering archetype` (FAIRNESS-08), `Scrub log`
- [ ] `tests/test_size_budget.sh` — assert `du -sh fixtures/snapshots/` ≤ 50 MB AND every direct child ≤ 5 MB
- [ ] `tests/test_stage_walk_balance.py` — verify S9-S26 prompt cells contain a `**Type:** read|drive` tag, the count is 9:9 ±1 (DESIGN-01), and S16's prompt explicitly requires ≥3 pages (DESIGN-02)
- [ ] `tests/fixtures/framework-variants/data.json` — shared 10-product source for D-12 (consumed by all 4 framework variants)
- [ ] `bench/scrub_artifacts.py` extension — verify per-fixture `.scrub_allow.txt` files are picked up (no Python source change expected per PATTERNS.md; if needed, add `DEFAULT_ALLOW` entries)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AJAX cart-add deterministically mutates DOM | FIXTURE-02 | Requires browser JS execution; not curl-testable | Open `http://127.0.0.1:8765/s09_ecommerce_pdp/` in Chrome, click "Add to cart", verify `localStorage.cart` updated AND cart-count badge increments |
| Post-mutation cart state extractable | FIXTURE-03 | Requires browser session continuity | After above, navigate to `verify-cart.html`, verify cart contents displayed |
| Login → cookie → dashboard flow | FIXTURE-09, FIXTURE-10 | Requires `document.cookie` write+read in browser | Open `login.html`, fill any non-empty creds, submit, verify `document.cookie` contains `session=fake-token-xyz` AND `dashboard.html` renders welcome banner |
| Complex form validation-error recovery | FIXTURE-12 | Requires interactive form fill | Open `s19_20_complex_form/`, submit empty form, verify inline validation errors; then fill required fields, verify error clears and submit succeeds |
| Read-only MCPs observably differ on SSR-with-hydration variant | FAIRNESS-09 | Cross-MCP comparison — measurement happens in Phase 8 | Defer to Phase 8 scoring run; Phase 6 documents the expected N/A surface in each prompt cell |
| Cross-platform parity (REPRO-13) | REPRO-13 | Linux x86_64 box not available this phase | Out of scope this phase — Phase 7 owns harness portability. Flag in PROVENANCE.md if any fixture has platform-specific gotchas (file-mode bits from wget, etc.) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (5 new test files / extensions)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (set when planner finalizes per-task IDs and confirms coverage)

**Approval:** pending
