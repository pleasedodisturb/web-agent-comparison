# Phase 6: Fixture authoring (S9-S26) - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning
**Mode:** Smart discuss — gray areas resolved through 4 question turns (source strategy, auth-walled mechanism, framework-variant content, i18n scope). Decisions captured below; planner can act without re-asking.

<domain>
## Phase Boundary

All 18 new v1.1 stages (S9-S26) exist as byte-for-byte loopback snapshots in `fixtures/snapshots/`, scrubbed + PROVENANCE-tagged, served by the existing 127.0.0.1 fixture server, and the harness's stage-walk prompt (`prompts/stage_walk.md`) can render every new stage end-to-end without harness modification — turning v1.1's design proposal into a frozen, reproducible asset set.

**Stop condition:** every stage S9-S26 has (1) a fixture directory under `fixtures/snapshots/`, (2) a PROVENANCE.md entry, (3) a prompt cell in the v1.1 stage_walk.md extension, (4) `du -sh fixtures/snapshots/` ≤ 50 MB, (5) `bench/scrub_artifacts.py` exits 0 on the full set, (6) sacrosanct triad byte-for-byte vs v1.0 close (2026-05-28).

**What this phase does NOT do:**
- Does NOT score any MCP against the new fixtures — that's Phase 8.
- Does NOT modify the rubric — FAIRNESS-08..12 are asserted via fixture-set composition, not new rubric dimensions.
- Does NOT add new candidates — BrowserMCP decision is Phase 9.
- Does NOT introduce a Linux-specific harness path — Phase 7 owns harness portability.

</domain>

<decisions>
## Implementation Decisions

### Source-selection per category (D-01..D-08)

Adopted the synthetic/captured split shown in the discussion table — 4 synthetic + 4 captured = 50/50, honors DESIGN-01 read-vs-drive parity.

- **D-01 (S9-11, e-commerce PDP + cart + cart-verify): synthetic.** Author a fake "OSS Project Store" PDP from scratch. Includes price, SKU, availability, AJAX cart-add button. Full control over cart-state JS means we can deterministically test S10's AJAX mutation and S11's post-mutation extraction. License-clean by construction. No real Shopify snapshot — too much version drift + PII risk in reviews.
- **D-02 (S12, SERP): captured DuckDuckGo HTML SERP + captured Brave SERP, same generic informational query.** Pinned query: `q=python+web+scraping+best+practices` (stable across captures, no PII, mix of organic + occasional sponsored result). Both DDG and Brave snapshots so MCPs can be compared on SERP-shape variance. DDG's `/?q=` returns plain HTML (no JS required) — ideal for read-only MCPs (lightpanda, firecrawl) to be measured fairly.
- **D-03 (S13-15, long-form Wikipedia): captured.** Wikipedia "Comparison of X" article family (e.g., "Comparison of programming languages (syntax)"). Single article serves all three stages: S13 body extraction, S14 table-in-article + infobox, S15 footnote/reference harvest. Maximizes dimensions stressed per fixture-byte. CC BY-SA license. (Tentatively: `Comparison_of_programming_languages_(syntax)` — planner confirms specific URL during snapshot.)
- **D-04 (S16, pagination): captured Hacker News front page across 5 pages.** Stable layout, plain HTML, ~30 items per page, public-domain-ish content (titles + links). HN's `/?p=N` is canonical pagination — no infinite-scroll JS. Tests "click next, dedup, aggregate" without backend variance.
- **D-05 (S17-18, auth-walled): synthetic.** No real auth ever. See § Auth-walled mechanism below.
- **D-06 (S19-20, complex form): synthetic.** Author a multi-section form covering: multi-select with search filter, date range picker, dependent fields (country → state), file upload, and inline client-side validation errors. S19 = full fill; S20 = trigger validation error and recover. Domain: visa-application-style (broad cross-cultural relevance, not biased toward any v1.0 MCP).
- **D-07 (S21-22, sortable table): captured Wikipedia comparison table — same fixture family as D-03 (double-duty).** Reuse the S13-15 Wikipedia article's sortable comparison table for S21 (extract as records) + S22 (sort-by-column then re-extract). Saves snapshot budget; ensures table-extraction and long-form-extraction are measured on a single CC-clean asset.
- **D-08 (S23-26, JS framework variants): synthetic — product list rendered 4 ways.** All four variants render the SAME product list (10 items, structured fields: name, price, short description, image alt text). Parallels D-01 (FIXTURE-01 e-commerce PDP) so the same MCP can be cross-checked on "extract from real-style PDP" vs "extract from product list rendered as Next.js / SvelteKit / Vue 3 / vanilla static." Cleanest possible A/B for the JS Rendering dimension.

### Auth-walled fixture mechanism (D-09..D-11)

- **D-09: Cookie-based fake session.** The synthetic login form's submit handler sets a session cookie (`session=fake-token-xyz`) via inline JavaScript; the dashboard's snapshot reads `document.cookie` to determine logged-in state. **This is the dimension S1-S8 does not exercise** — state persistence across requests, real cookie handling. Each MCP's cookie-persistence behavior becomes a measurement axis without modifying the rubric (folded into Interaction Depth + Data Quality).
- **D-10: Generic SaaS dashboard layout.** Welcome banner + notifications widget + "recent activity" list + settings link. Mirrors Stripe/Linear/Notion-style layouts. **Deliberately NOT job-board / not GitHub-like** — keeps the public benchmark from biasing toward Vitalik's downstream Kestrel/Eyas use case. Reusable across audiences.
- **D-11: Submit-button mechanics.** Login form accepts any non-empty username + non-empty password (no dummy-credential check). Submit handler: (1) sets cookie, (2) navigates to `dashboard.html`. Failure case (empty input) shows inline validation error message. Tests form-fill + cookie set + navigate + post-auth read in one S17→S18 flow.

### JS framework variants content + authoring (D-12..D-14)

- **D-12: Content = 10-product list with structured fields.** Each product has `name`, `price`, `short_description`, `image_alt_text` (no real images — alt-text only, keeps fixture size small). Same JSON data file (`fixtures/framework-variants/data.json`) feeds all 4 framework renderers. Verification: extracting from any of the 4 variants must yield the same 10 records.
- **D-13: Authoring approach.** Use each framework's canonical scaffold (`npx create-next-app`, `npm create svelte@latest`, `npm create vite@latest -- --template vue`, and a hand-authored vanilla index.html). Strip each to a minimal product-list page that imports the shared `data.json`. Build (`next build && next export` / equivalents) and snapshot the produced HTML + assets. **The build artifacts are the fixture; we do NOT ship the framework scaffolds in the repo** (would blow the size budget).
- **D-14: Snapshot location.** `fixtures/snapshots/framework_variant_nextjs/`, `framework_variant_sveltekit/`, `framework_variant_vue/`, `framework_variant_vanilla/`. Each contains the built HTML + minimal accompanying CSS/JS. Vanilla static fixture (S26) is the baseline reference — agents that extract from it correctly but fail on the SPA variants reveal their JS-rendering capability gap.

### i18n scope (D-15)

- **D-15: FAIRNESS-11 deferred to v1.2.** Update `REQUIREMENTS.md` to mark FAIRNESS-11 as deferred. Rationale: v1.1 already adds 18 stages; the 2 additional fixtures (Japanese Wikipedia + Arabic news) add ~1.5× authoring effort on encoding verification + RTL layout review. The methodological gap gets an explicit "not measured — see v1.2" callout in the v1.1 published report. The deferred line in REQUIREMENTS.md serves as the v1.2 anchor.

### Decisions inherited from v1.0 (not re-asked)

- **Loopback-only**: every fixture served from `127.0.0.1` via existing fixture server (REPRO-09; v1.0 Phase 1 D-13).
- **PROVENANCE.md per fixture dir**: source URL, capture date, license, agent-task tag (DESIGN-03), rendering archetype (FAIRNESS-08). Format mirrors v1.0 Phase 1 PROVENANCE.md pattern.
- **`bench/scrub_artifacts.py`**: extended for new fixture surface per REPRO-10; scrub-allow-list pattern for synthetic mock data (e.g., "Jane Testworth" mock applicant carries forward).
- **`bench/wave_close_check.py`**: continues asserting sacrosanct triad (scoring/score.py, scoring/rubric.md, .mcp.json) byte-for-byte vs v1.0 close (2026-05-28). Phase 6 does not modify any of these.
- **Snapshot capture toolchain**: `wget --mirror --no-clobber --convert-links --page-requisites` for captured sources (v1.0 precedent). Synthetic fixtures hand-authored or LLM-drafted then hand-reviewed.

### Claude's Discretion

- **Specific Wikipedia article URL** for D-03/D-07 — planner picks during snapshot from the "Comparison of programming languages" family; criterion: rich sortable table + ≥3 footnotes + an infobox + size within budget. Default candidate: `Comparison_of_programming_languages_(syntax)`.
- **Exact DDG SERP capture mechanics** — planner picks between `wget` direct + post-processing vs Playwright save-page (DDG's HTML SERP doesn't need JS, so wget is simpler).
- **Synthetic fixture HTML structure** — planner authors against the rubric (semantic HTML + ARIA per FAIRNESS-12) without re-asking unless a specific design tradeoff surfaces.
- **Specific filename slug pattern** — recommended `fixtures/snapshots/s09_ecommerce_pdp/`, etc., but planner can adjust if a different convention is more readable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.1 milestone scope
- `.planning/PROJECT.md` § Current Milestone v1.1 — goal + 8 target features + key context (loopback-only, byte-for-byte rubric lock, etc.)
- `.planning/REQUIREMENTS.md` — 65 v1.1 REQ-IDs; Phase 6 owns 31: FIXTURE-01..18, DESIGN-01..03, FAIRNESS-08..12, REPRO-09..13
- `.planning/ROADMAP.md` § Phase 6 — Goal + Success Criteria + Depends-on
- `~/Projects/web-agent-comparison-launch-drafts/05-v1.1-general-fixtures-proposal.md` — the v1.1 design proposal that drove these requirements; deeper rationale for each fixture category

### v1.0 patterns to inherit (not invent fresh)
- `.planning/milestones/v1.0-phases/01-harness-foundation/01-CONTEXT.md` — style template + many decisions Phase 6 inherits (loopback, scrub pipeline, PROVENANCE schema, snapshot-serving model)
- `.planning/milestones/v1.0-phases/01-harness-foundation/01-03-snapshot-fixtures-PLAN.md` — original snapshot-fixtures plan; the wget --mirror invocation + PROVENANCE.md format is the v1.1 baseline to extend
- `fixtures/snapshots/greenhouse_2026-05-22/PROVENANCE.md` — concrete v1.0 PROVENANCE example to mirror format for new fixtures
- `fixtures/snapshots/ashby_2026-05-22/PROVENANCE.md` — second concrete example

### Existing code Phase 6 must extend (not rewrite)
- `bench/scrub_artifacts.py` — extend for new fixture surface (synthetic auth-walled fixture, multi-page HN snapshot, framework-variant builds). Must continue exiting 0 on every committed fixture.
- `prompts/stage_walk.md` — v1.0 S1-S8 prompt is locked; v1.1 extends with S9-S26 prompt cells appended. Do NOT modify S1-S8 cells.
- `scripts/serve_fixtures.sh` — Python http.server invocation; may need tweaks to handle new fixture-dir tree depth (e.g., multi-page HN snapshot subdirs).
- `fixtures/mock_data.json` + `fixtures/mock_resume.pdf` — v1.0 mock applicant Jane Testworth survives the scrub; synthetic fixtures may reference her if a "user profile" is needed (auth-walled dashboard could show "Welcome, Jane Testworth").

### Sacrosanct invariants (must NOT change in Phase 6)
- `scoring/score.py` byte-for-byte from v1.0 close (2026-05-28)
- `scoring/rubric.md` byte-for-byte from v1.0 close
- `.mcp.json` byte-for-byte from v1.0 close (BrowserMCP decision is Phase 9, not Phase 6)
- `bench/wave_close_check.py` audit must continue reporting `all_pass=True` at every plan boundary

### Tracking
- GitHub repo: pleasedodisturb/web-agent-comparison
- Linear team: G (Vitalik)
- Phase 6 has no upstream issues; all work is local

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Python http.server fixture-serving pattern** (v1.0 Phase 1 D-13): `python3 -m http.server` bound to `127.0.0.1:8765`, root at `fixtures/snapshots/`. Continues unchanged.
- **wget --mirror snapshot toolchain** (v1.0 Phase 1): `wget --mirror --no-clobber --convert-links --page-requisites` is the captured-fixture acquisition pattern. Reuses for D-02 (DDG SERP), D-03 (Wikipedia), D-04 (HN pagination), D-07 (Wikipedia table — same artifact as D-03).
- **PROVENANCE.md per-fixture-dir format** (v1.0 fixtures/snapshots/greenhouse_2026-05-22/PROVENANCE.md): captures source URL + capture date + license + scrubbed-fields list. v1.1 extends with agent-task tag (DESIGN-03) + rendering archetype (FAIRNESS-08).
- **`bench/scrub_artifacts.py` allow-list pattern** (v1.0): `.scrub_allow.txt` per fixture dir lists pre-approved survivors (e.g., mock applicant name). v1.1 extends for synthetic fixtures (the auth-walled dashboard's mock user, the synthetic e-commerce store's product names).
- **`bench/wave_close_check.py` invariants framework** (v1.0): runs at every plan boundary; v1.1 reuses unchanged.

### Established Patterns
- **Stage-walk prompt extension**: append S9-S26 prompt cells to `prompts/stage_walk.md` below the locked S1-S8 cells; do not interleave. v1.0 stage_walk.md is the format reference.
- **Per-MCP allowlisting via `--allowedTools "mcp__${MCP}__*,Read,Write,Bash"`** (v1.0 harness model): Phase 6 doesn't touch this; just provides new fixtures for the existing harness to walk.
- **N/A vs FAIL distinction** (v1.0 Phase 2 P02 lightpanda finding): fixture authoring must respect that some MCPs will be categorically N/A on JS-requiring stages (e.g., lightpanda + Firecrawl on S23-S25 SPA variants). Document the expected N/A surface per stage in the prompt cells.

### Integration Points
- **`prompts/stage_walk.md` v1.1 extension** — appends S9-S26 cells; consumed by Phase 8 harness re-validation runs.
- **`fixtures/snapshots/*/PROVENANCE.md` files** — consumed by `docs/REPRODUCIBILITY.md` updates in Phase 11 (REPORT-17).
- **`bench/scrub_artifacts.py` extended ruleset** — must pass at every commit; integrated with the pre-commit-hook framework v1.0 established.

</code_context>

<specifics>
## Specific Ideas

- **Pinned DDG SERP query for D-02**: `q=python+web+scraping+best+practices` — stable, no PII, mix of organic + occasional sponsored, no controversial topics. Capture from both DDG (`html.duckduckgo.com/html/?q=...`) and Brave (`search.brave.com/search?q=...`).
- **Wikipedia article candidate for D-03/D-07**: `Comparison_of_programming_languages_(syntax)` — has sortable comparison table (S21-22), rich infobox, ~10+ footnotes, body prose (S13), within size budget.
- **HN pagination for D-04**: 5 sequential snapshots of `news.ycombinator.com/?p=1` through `?p=5`. Title + URL + comments-link per item. Plain HTML, no JS required.
- **Synthetic e-commerce store name for D-01**: "Open Source Outpost" or similar fictional store name (clear it's not a real brand). Products are themed around dev tools (e.g., "Mechanical Keyboard Y50", "USB-C Hub Pro", etc.) — broad enough to not bias the benchmark.
- **Synthetic auth-walled mock user for D-10**: "Jane Testworth" — the v1.0 mock applicant. Reuses the existing scrub allow-list; preserves continuity across milestones.

</specifics>

<deferred>
## Deferred Ideas

- **FAIRNESS-11 (i18n: non-English + non-ASCII fixtures)** — deferred to v1.2 per D-15. Mark in REQUIREMENTS.md.
- **FIXTURE-19 (S27 media-heavy / lazy-loaded)** — already deferred per REQUIREMENTS.md Future section. Stays there.
- **FIXTURE-20 (S28-29 iframe-embedded)** — already deferred. Stays.
- **FIXTURE-21 (S32 PDF rendering)** — already deferred. Stays.
- **Real-Chrome fixture archive for time-travel reproducibility** — would let third parties replay v1.0 vs v1.1 numbers from the same Chrome version. Out of scope for v1.1; tracked as a v2.0 stretch.
- **Synthetic-fixture LLM-generation provenance** — for synthetic fixtures authored with LLM assistance, PROVENANCE.md should note the LLM + prompt used. v1.0 PROVENANCE didn't have this concept. Defer adding to v1.2.
- **Snapshot diffing tooling** — `bench/diff_fixtures.py` would help catch drift if v1.1 ever re-captures. Useful but not needed for the initial v1.1 ship.

</deferred>

---

*Phase: 06-Fixture authoring (S9-S26)*
*Context gathered: 2026-05-29*
