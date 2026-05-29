# Phase 6: Fixture authoring (S9-S26) - Research

**Researched:** 2026-05-29
**Domain:** Web fixture authoring (snapshot capture + synthetic HTML/JS authoring) for benchmark reproducibility
**Confidence:** HIGH on synthetic-fixture path and tooling; MEDIUM on captured-source legal posture; HIGH on extension surfaces in existing code.

## Summary

Phase 6 is a pure asset-production phase: 18 new stage fixtures, half captured-from-live (wget --mirror), half hand-authored synthetic HTML+CSS+JS. All served from 127.0.0.1 via the existing `serve_fixtures.sh`. No harness code changes — only fixture files, three PROVENANCE.md per fixture-dir, a `bench/scrub_artifacts.py` extension for the new allow-list surface, and an append-only extension to `prompts/stage_walk.md` adding 18 prompt cells below the locked S1-S8 set.

The research uncovered three operational gotchas the planner MUST address explicitly:

1. **DDG `/html/?q=` and Brave `/search?q=` both `Disallow: /` in robots.txt** [VERIFIED: WebFetch of html.duckduckgo.com/robots.txt + search.brave.com/robots.txt]. The CONTEXT.md D-02 decision to use both as captured SERP fixtures collides with this — needs an explicit "we override robots.txt via `--execute robots=off` for archival-research purpose, captured once, never re-crawled, single search query" posture in the PROVENANCE.md plus consideration of whether a synthetic SERP page is the safer ship.
2. **The framework-variant build pipeline (D-08) is the only "build something then snapshot the build artifact" path in the project** — every other fixture is either captured (wget) or hand-authored (text editor). The scaffolds (`create-next-app`, etc.) are NOT committed; only the `out/` / `build/` / `dist/` directories are. The Plans must include a temp-scratch-dir scaffolding step that produces the artifact, copies it into `fixtures/snapshots/framework_variant_<name>/`, then discards the scaffold. This is a meaningfully different work-shape from the captured-fixtures path and warrants its own wave.
3. **Per-fixture size budget is tight on the framework variants.** A minimal `next export` site lands in the 80-200KB range on disk for HTML + JS chunks (verified rough order from Next.js static export docs); SvelteKit minimal is ~30-80KB; Vite/Vue is ~30-100KB; vanilla is ~5-20KB. Total for 4 variants is plausibly ≤ 1MB combined, leaving ample headroom under the 50MB total. But Next.js with `_next/static/chunks/` directories has many small files — disk-usage measurement is needed at the end of each framework wave.

**Primary recommendation:** Organize Phase 6 as **one prep wave + seven parallel fixture-group waves + one finalize wave** (9 waves total, ~22-26 tasks). Treat the framework-variant wave as the riskiest and gate it behind a prep checkpoint that confirms the chosen scaffold scripts succeed on the Mac Mini.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Source-selection per category (D-01..D-08):**
- **D-01 (S9-11 e-commerce):** synthetic. Author "OSS Project Store" PDP with price, SKU, availability, AJAX cart-add button. Deterministic AJAX cart-state JS; no real Shopify markup.
- **D-02 (S12 SERP):** captured DuckDuckGo HTML SERP + captured Brave SERP, same generic query `q=python+web+scraping+best+practices`. DDG = `html.duckduckgo.com/html/?q=...`; Brave = `search.brave.com/search?q=...`.
- **D-03 (S13-15 long-form):** captured Wikipedia "Comparison of programming languages (syntax)" — same article serves S13 body, S14 table+infobox, S15 footnotes.
- **D-04 (S16 pagination):** captured Hacker News front page across 5 pages `/?p=1` through `/?p=5`.
- **D-05 (S17-18 auth-walled):** synthetic. Cookie-based fake session (`session=fake-token-xyz`). No real auth.
- **D-06 (S19-20 complex form):** synthetic. Visa-application-style: multi-select+search, date range, dependent country→state, file upload, inline validation. S19 = fill; S20 = recover from validation error.
- **D-07 (S21-22 sortable table):** **same fixture as D-03 Wikipedia** (double-duty). S21 = extract records; S22 = sort-by-column then re-extract.
- **D-08 (S23-26 JS framework variants):** synthetic. 10-product list rendered 4 ways (Next.js / SvelteKit / Vue 3 / vanilla) from a single shared `data.json`. Each variant snapshotted as built artifact, not source scaffold.

**Auth-walled mechanism (D-09..D-11):**
- D-09: Cookie-based fake session, `document.cookie` read on dashboard.
- D-10: Generic SaaS dashboard layout (welcome banner + notifications widget + recent activity + settings link). NOT job-board / NOT GitHub-like.
- D-11: Login form accepts any non-empty username + non-empty password. Submit sets cookie + navigates to `dashboard.html`. Empty input shows inline validation.

**JS framework variants (D-12..D-14):**
- D-12: Content = 10-product list. Each product: `name`, `price`, `short_description`, `image_alt_text`. Shared `fixtures/framework-variants/data.json`. Extraction parity verification.
- D-13: Authoring via canonical scaffolds (create-next-app, sveltekit init, vite + vue template, hand-authored vanilla). Build, then snapshot the produced HTML + assets. Framework scaffolds NOT committed; build artifacts ARE.
- D-14: Locations:
  - `fixtures/snapshots/framework_variant_nextjs/`
  - `fixtures/snapshots/framework_variant_sveltekit/`
  - `fixtures/snapshots/framework_variant_vue/`
  - `fixtures/snapshots/framework_variant_vanilla/`

**i18n scope (D-15):** FAIRNESS-11 deferred to v1.2. REQUIREMENTS.md already updated to reflect this.

**Inherited from v1.0 (not re-asked):**
- Loopback-only serving from 127.0.0.1 via `scripts/serve_fixtures.sh`
- PROVENANCE.md per fixture dir with source URL, capture date, license, agent-task tag (DESIGN-03), rendering archetype (FAIRNESS-08)
- `bench/scrub_artifacts.py` extended for new fixture surface
- `bench/wave_close_check.py` sacrosanct triad audit unchanged
- `wget --mirror --no-clobber --convert-links --page-requisites` for captured sources; hand-author or LLM-draft + review for synthetic

### Claude's Discretion

- Specific Wikipedia article URL for D-03/D-07 — default candidate confirmed live + structurally suitable: `https://en.wikipedia.org/wiki/Comparison_of_programming_languages_(syntax)` (has sortable table, ~24 footnotes, comparable to ~400-500KB body HTML).
- DDG SERP capture mechanics — wget direct + post-processing (DDG /html/?q= serves plain HTML, no JS).
- Synthetic fixture HTML structure — semantic HTML5 + ARIA per FAIRNESS-12.
- Filename slug pattern — recommend `fixtures/snapshots/s09_ecommerce_pdp/`, `s12_serp_ddg/`, etc., for human readability.

### Deferred Ideas (OUT OF SCOPE)

- FAIRNESS-11 i18n fixtures — v1.2.
- FIXTURE-19 media-heavy / lazy-loaded — v1.2+.
- FIXTURE-20 iframe-embedded — v1.2+.
- FIXTURE-21 PDF rendering — v1.2+.
- Real-Chrome fixture archive for time-travel reproducibility — v2.0 stretch.
- Synthetic-fixture LLM-generation provenance (LLM + prompt in PROVENANCE.md) — v1.2.
- `bench/diff_fixtures.py` snapshot diffing — v1.2.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIXTURE-01 | S9 e-commerce PDP synthetic | Hand-authored HTML+CSS+inline JS — see §Synthetic Fixture Authoring Pattern |
| FIXTURE-02 | S10 e-commerce cart-add AJAX | Inline JS cart-state mutation, no backend — see §Cart AJAX Pattern |
| FIXTURE-03 | S11 cart post-mutation extraction | Re-read cart-state DOM after S10 — see §Cart Verification Pattern |
| FIXTURE-04 | S12 SERP DDG + Brave | **Robots.txt BLOCKED on both** [VERIFIED: WebFetch] — see §SERP Capture Risk + Mitigation |
| FIXTURE-05 | S13 Wikipedia body | wget --mirror with asset pruning — see §Wikipedia Capture |
| FIXTURE-06 | S14 Wikipedia table+infobox | Same fixture as S13; verify infobox absent OR adjust article choice — see §Wikipedia Capture |
| FIXTURE-07 | S15 Wikipedia footnotes | Same fixture as S13; ~24 numbered refs confirmed — see §Wikipedia Capture |
| FIXTURE-08 | S16 pagination (HN ×5) | wget per-page capture; robots.txt allows + 30s crawl-delay — see §HN Pagination Capture |
| FIXTURE-09 | S17 synthetic auth login | Synthetic HTML form, cookie set on submit, JS-driven redirect — see §Synthetic Auth Pattern |
| FIXTURE-10 | S18 synthetic dashboard | Generic SaaS layout, reads `document.cookie` — see §Synthetic Auth Pattern |
| FIXTURE-11 | S19 complex form fill | Visa-app shape: vanilla JS dependent-field + validation — see §Complex Form Pattern |
| FIXTURE-12 | S20 form validation recovery | Same fixture; inline validation error path — see §Complex Form Pattern |
| FIXTURE-13 | S21 sortable table extract | Reuse Wikipedia D-03 fixture — see §Wikipedia Capture |
| FIXTURE-14 | S22 sort-by-column re-extract | Same Wikipedia fixture; Wikipedia tables use jQuery+`mw-sortable` — verify the sort JS captures into the static mirror |
| FIXTURE-15 | S23 Next.js variant | `output: 'export'` config + `next build` — see §Framework Variant Build Pipeline |
| FIXTURE-16 | S24 SvelteKit variant | `@sveltejs/adapter-static` + `prerender = true` + `npm run build` — see §Framework Variant Build Pipeline |
| FIXTURE-17 | S25 Vue 3 variant | `vite build --base=/framework_variant_vue/` — see §Framework Variant Build Pipeline |
| FIXTURE-18 | S26 vanilla baseline | Hand-authored single `index.html` reading `data.json` — see §Framework Variant Build Pipeline |
| DESIGN-01 | Read-vs-drive 50/50 | Tag each S9-S26 in prompt cell — see §Read-vs-Drive Tagging |
| DESIGN-02 | Multi-page state (≥3 pages) | S16 HN pagination prompt cell explicit requirement — see §HN Pagination Capture |
| DESIGN-03 | Per-fixture use-case tag | One-sentence tag in PROVENANCE.md — see §PROVENANCE.md v1.1 Format |
| FAIRNESS-08 | Rendering archetype coverage | Set composition: classic server-HTML (Wikipedia+HN), React-SSR (Next.js), SvelteKit, Vue 3 SPA, vanilla static |
| FAIRNESS-09 | Workload coverage | Each stage stresses ≥1 rubric dim S1-S8 didn't (cart AJAX, table sort, dependent fields, post-auth read, etc.) |
| FAIRNESS-10 | No MCP-specific bias | Verified set composition — see §Bias-Check |
| FAIRNESS-11 | i18n | DEFERRED to v1.2 per D-15 — REQUIREMENTS.md update task |
| FAIRNESS-12 | Semantic vs div-soup | Synthetic e-commerce = semantic HTML5+ARIA; framework-variant SPAs = expected div-soup; document per fixture |
| REPRO-09 | Loopback-only | Existing `scripts/serve_fixtures.sh` unchanged |
| REPRO-10 | PII-scrubbed | Extend `bench/scrub_artifacts.py` allow-list — see §Scrub Extension Surface |
| REPRO-11 | ≤ 5MB/fixture; ≤ 50MB total | Audit budget — see §Size Budget |
| REPRO-12 | License-clean | Per-source verdict — see §License Posture |
| REPRO-13 | Cross-platform parity | Static HTML/JS is portable; only wget output filemodes differ — see §Cross-Platform Audit |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fixture asset storage | Filesystem (`fixtures/snapshots/`) | — | Static files committed to repo |
| Loopback serving | Python http.server (existing) | — | `scripts/serve_fixtures.sh` unchanged |
| Captured-source acquisition | Shell + wget | Python (scrub script) | `scripts/snapshot_fixtures.sh` pattern |
| Synthetic fixture authoring | Hand-authored HTML/CSS/JS | LLM-assisted draft + human review | Per CONTEXT.md "hand-authored or LLM-drafted then hand-reviewed" |
| Framework variant build | Node toolchain (npx/npm) on host | — | Build in temp scratch dir, copy `out/build/dist/` into repo, discard scaffold |
| PII scrubbing audit | Python (`bench/scrub_artifacts.py`) | — | Existing tool, extend allow-list only |
| Prompt cell extension | Markdown (`prompts/stage_walk.md`) | — | Append-only; locked S1-S8 untouched |
| Provenance metadata | Markdown (per-fixture PROVENANCE.md) | — | Mirrors v1.0 format with two new fields |
| Invariants audit | Python (`bench/wave_close_check.py`) | — | Unchanged; verifies triad byte-identity |

## Standard Stack

### Core (existing — DO NOT modify)
| Tool | Version | Purpose | Source |
|------|---------|---------|--------|
| Python 3.12 | from `.venv/` | scrub_artifacts.py, wave_close_check.py, http.server | [VERIFIED: project venv per `.python-version`] |
| wget | 1.25.0 | captured-source mirroring | [VERIFIED: existing PROVENANCE.md "GNU Wget 1.25.0 built on darwin25.2.0"] |
| Bash 5+ | system | orchestration | [VERIFIED: existing scripts/] |

### New (Phase 6 only — Node toolchain for framework variants)
| Tool | Version (recommended) | Purpose | Source |
|------|----------------------|---------|--------|
| Node.js | 22 LTS | Build host for framework scaffolds | [CITED: nodejs.org LTS schedule; matches CLAUDE.md project standard] |
| npm | bundled with Node 22 | Package install + scaffold scripts | [VERIFIED: standard] |
| `create-next-app` | latest (run via `npx create-next-app@latest`) | Next.js scaffold | [CITED: nextjs.org docs — `output: 'export'` config snippet] |
| `@sveltejs/adapter-static` | latest | SvelteKit static export | [CITED: svelte.dev/docs/kit/adapter-static — install + config snippet verified] |
| Vite | 5.x+ (bundled with `create-vite`) | Vue 3 scaffold + build | [CITED: vite.dev/guide/build — `base` option for subdirectory hosting verified] |

**Important:** These tools run ONLY during fixture authoring on the Mac Mini. They are NOT runtime dependencies of the harness or scoring engine. The committed artifacts are pure static HTML/CSS/JS.

### Existing infrastructure to extend
| File | Modification | Purpose |
|------|--------------|---------|
| `bench/scrub_artifacts.py` | Add allow-list entries (no logic changes) | New synthetic-fixture proper nouns (e.g., "Open Source", "Mechanical Keyboard"); auth-walled mock user `Jane Testworth` already allowlisted |
| `prompts/stage_walk.md` | Append S9-S26 prompt cells below locked S1-S8 | Per CONTEXT.md: "do NOT modify S1-S8 cells" |
| `scripts/serve_fixtures.sh` | None expected | `python3 -m http.server --directory fixtures/snapshots/` walks nested dirs natively |
| `tests/test_snapshot_serves.sh` | Extend with curl checks for new fixture roots | Pattern: HTTP 200 + body length > N |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| wget --mirror for DDG/Brave SERP | Playwright `page.content()` save-as-HTML | wget is simpler, DDG /html/ serves no-JS; Playwright would add a node-toolchain dep for one capture |
| `create-next-app` scaffold | hand-authored Next.js manually | Scaffold gives canonical SSR-with-hydration output that the JS Rendering rubric dimension intends to measure |
| Vue 3 via Vite | Nuxt 3 static export | Vite is the official Vue 3 starter; Nuxt would add an opinionated SSR/hydration layer that confounds the comparison with Next.js |
| Capture HN with 1-day spacing | Single-day sequential capture | Single-day is fine — HN content shifts hourly but the fixture is a frozen snapshot, not a time series |
| Synthetic SERP fixture (avoids robots.txt) | Captured DDG+Brave per D-02 | CONTEXT.md locks captured. If legal posture is unacceptable, revisit in discuss-phase reopener |

**Installation (Phase 6 author-time only, NOT runtime):**
```bash
# On the Mac Mini, in a temp scratch dir outside the repo:
npx create-next-app@latest framework-variant-nextjs --typescript --no-tailwind --no-eslint --app
npm create vite@latest framework-variant-vue -- --template vue
npx sv create framework-variant-sveltekit --template minimal --types ts --no-add-ons
```

**Version verification (run before authoring framework variants):**
```bash
node --version          # expect v22.x
npm view next version   # expect 14.x+ (output: 'export' stable since 13.4)
npm view @sveltejs/adapter-static version
npm view vite version
```

## Package Legitimacy Audit

> No external packages are committed to the runtime. The Node packages above are used ONLY during fixture authoring on the developer's workstation. The committed artifacts are inert static HTML/CSS/JS, so the typical npm supply-chain risk (postinstall scripts running on install) applies only to the author-time machine, not to downstream readers reproducing the benchmark.

| Package | Registry | Age | Downloads | Source Repo | Disposition |
|---------|----------|-----|-----------|-------------|-------------|
| `next` | npm | 9+ yrs | 8M+/wk | github.com/vercel/next.js | Approved — author-time only [CITED: nextjs.org official docs] |
| `react` / `react-dom` | npm | 11+ yrs | 25M+/wk | github.com/facebook/react | Approved — author-time only |
| `@sveltejs/adapter-static` | npm | 5+ yrs | 200K+/wk | github.com/sveltejs/kit | Approved — author-time only [CITED: svelte.dev docs] |
| `vite` | npm | 5+ yrs | 30M+/wk | github.com/vitejs/vite | Approved — author-time only [CITED: vite.dev docs] |
| `vue` | npm | 11+ yrs | 5M+/wk | github.com/vuejs/core | Approved — author-time only |
| `create-next-app` | npm | 8+ yrs | 200K+/wk | github.com/vercel/next.js | Approved — author-time only |
| `create-vite` | npm | 4+ yrs | 1M+/wk | github.com/vitejs/vite | Approved — author-time only |

*slopcheck was not available in this research session; all packages above are well-established household-name frameworks discovered from official documentation. Risk profile is low even unverified. Per the package-legitimacy protocol the planner should add a `checkpoint:human-verify` task before the framework-variant wave begins to confirm published versions on npm.*

## Architecture Patterns

### System Architecture Diagram

```
                     [PHASE 6 ASSET PRODUCTION]
                                │
   ┌────────────────────────────┼────────────────────────────────┐
   │ CAPTURED PATH              │ SYNTHETIC PATH                 │
   │ (D-02, D-03, D-04, D-07)   │ (D-01, D-05, D-06, D-08)       │
   │                            │                                │
   │ live URL                   │ design intent                  │
   │   │                        │   │                            │
   │   ▼                        │   ▼                            │
   │ wget --mirror              │ hand-author HTML/CSS/JS        │
   │   --no-host-directories    │ (or LLM-draft + human review)  │
   │   --execute robots=off     │   │                            │
   │   │                        │   │                            │
   │   ▼                        │   ▼                            │
   │ raw mirror tree            │ raw author tree                │
   │   │                        │   │                            │
   │   ▼                        │   ▼                            │
   │ asset-prune (Wikipedia)    │ for framework variants only:   │
   │   strip non-essential CSS  │   build via canonical scaffold │
   │   strip tracking pixels    │   (npx create-next-app, etc.)  │
   │   │                        │   → temp scratch dir           │
   │   ▼                        │   → copy out/build/dist/       │
   │ PII scrub (Python regex)   │   into fixtures/snapshots/     │
   │   iterate to convergence   │   → discard scaffold           │
   │   │                        │   │                            │
   └───┴────────────┬───────────┴───┴──────┬─────────────────────┘
                    │                      │
                    ▼                      ▼
        fixtures/snapshots/<slug>/ + PROVENANCE.md per fixture
                              │
                              ▼
        bench/scrub_artifacts.py (extended allow-list) → exit 0
                              │
                              ▼
        du -sh fixtures/snapshots/ → ≤ 50 MB
                              │
                              ▼
        scripts/serve_fixtures.sh start → curl http://127.0.0.1:8765/<slug>/ → 200
                              │
                              ▼
        prompts/stage_walk.md (append S9-S26 cells below S1-S8)
                              │
                              ▼
        bench/wave_close_check.py → all_pass=True (sacrosanct triad byte-identical)
                              │
                              ▼
                [PHASE 6 STOP CONDITION SATISFIED]
```

### Recommended Project Structure

```
fixtures/
├── mock_data.json                          # existing — Jane Testworth profile
├── mock_resume.pdf                         # existing
├── framework-variants/                     # NEW — shared data for D-12
│   └── data.json                           # 10-product list
└── snapshots/                              # existing — extended
    ├── .gitkeep                            # existing
    ├── greenhouse_2026-05-22/              # existing — UNCHANGED
    ├── ashby_2026-05-22/                   # existing — UNCHANGED
    ├── s09_ecommerce_pdp/                  # NEW (D-01)
    │   ├── index.html                      # PDP markup
    │   ├── product.js                      # AJAX cart-add inline JS
    │   ├── styles.css
    │   └── PROVENANCE.md
    ├── s12_serp_ddg/                       # NEW (D-02 first half)
    │   ├── index.html                      # wget output of DDG /html/?q=...
    │   ├── PROVENANCE.md
    │   └── .sha256
    ├── s12_serp_brave/                     # NEW (D-02 second half)
    │   ├── index.html                      # wget output of Brave /search?q=...
    │   ├── PROVENANCE.md
    │   └── .sha256
    ├── s13_15_21_22_wikipedia/             # NEW (D-03, D-07; serves 4 stages)
    │   ├── article.html                    # wget output
    │   ├── (minimal CSS/JS for table sort)
    │   ├── PROVENANCE.md
    │   └── .sha256
    ├── s16_hn_pagination/                  # NEW (D-04)
    │   ├── p1.html ... p5.html             # 5 separate captured pages
    │   ├── PROVENANCE.md
    │   └── .sha256
    ├── s17_18_auth_walled/                 # NEW (D-05)
    │   ├── login.html                      # form + cookie-set JS
    │   ├── dashboard.html                  # reads document.cookie
    │   ├── styles.css
    │   └── PROVENANCE.md
    ├── s19_20_complex_form/                # NEW (D-06)
    │   ├── index.html                      # visa-app form
    │   ├── form.js                         # dependent fields + validation
    │   ├── styles.css
    │   └── PROVENANCE.md
    ├── framework_variant_nextjs/           # NEW (D-08 / S23) — built artifact
    │   ├── index.html
    │   ├── _next/static/chunks/*.js
    │   ├── data.json                       # copy of fixtures/framework-variants/data.json
    │   └── PROVENANCE.md
    ├── framework_variant_sveltekit/        # NEW (D-08 / S24)
    │   ├── index.html
    │   ├── _app/immutable/*.js
    │   ├── data.json
    │   └── PROVENANCE.md
    ├── framework_variant_vue/              # NEW (D-08 / S25)
    │   ├── index.html
    │   ├── assets/*.js
    │   ├── data.json
    │   └── PROVENANCE.md
    └── framework_variant_vanilla/          # NEW (D-08 / S26)
        ├── index.html                      # plain HTML reading data.json
        ├── data.json
        └── PROVENANCE.md
```

### Pattern 1: Synthetic Fixture Authoring (PDP, auth-walled, complex-form)

**What:** Hand-author HTML+CSS+vanilla JS (no framework) for fixtures that need full control over behaviour. The HTML structure is semantic HTML5 with ARIA labels (per FAIRNESS-12) to give accessibility-tree-leaning MCPs an honest target.

**When to use:** D-01, D-05, D-06.

**Example (cart AJAX pattern from D-01 / S10):**

```html
<!-- index.html (S9 PDP, S10 cart-add) -->
<article aria-labelledby="product-title">
  <h1 id="product-title">Mechanical Keyboard Y50</h1>
  <dl>
    <dt>SKU</dt><dd id="product-sku">KEY-Y50-OSS</dd>
    <dt>Price</dt><dd id="product-price">$129.00</dd>
    <dt>Availability</dt><dd id="product-availability">In stock</dd>
  </dl>
  <button type="button" id="add-to-cart" aria-label="Add to cart">Add to cart</button>
  <section aria-live="polite" aria-label="Cart summary">
    <p>Items in cart: <span id="cart-count">0</span></p>
    <p>Cart total: <span id="cart-total">$0.00</span></p>
  </section>

  <script>
    // Deterministic AJAX cart-state mutation (no backend).
    // S10 verification: cart-count becomes 1, cart-total becomes "$129.00".
    document.getElementById('add-to-cart').addEventListener('click', () => {
      const countEl = document.getElementById('cart-count');
      const totalEl = document.getElementById('cart-total');
      const newCount = parseInt(countEl.textContent, 10) + 1;
      countEl.textContent = String(newCount);
      totalEl.textContent = `$${(129.00 * newCount).toFixed(2)}`;
      // Surface a tiny "added" toast so screenshot MCPs can verify visually.
      const toast = document.createElement('div');
      toast.setAttribute('role', 'status');
      toast.textContent = 'Added to cart';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 1500);
    });
  </script>
</article>
```

**Source:** Hand-authored against rubric per CONTEXT.md "synthetic fixture HTML structure — planner authors against the rubric (semantic HTML + ARIA per FAIRNESS-12)."

### Pattern 2: Captured Source (wget --mirror)

**What:** Existing `scripts/snapshot_fixtures.sh` pattern, generalized beyond `greenhouse|ashby` to accept any source URL. CONTEXT.md decision is to reuse the wget --mirror toolchain.

**When to use:** D-02 (SERP), D-03/D-07 (Wikipedia), D-04 (HN).

**Generalization strategy:** Rather than special-casing each new captured fixture in the existing script (which currently has a hardcoded `case "$PLATFORM" in greenhouse|ashby` block), **add a `--slug <name>` flag** that accepts any output slug, and replace the platform whitelist with a regex-validated slug. This preserves the original `greenhouse`/`ashby` callsites but unlocks the new captures.

**Example (HN pagination capture per D-04):**

```bash
# Capture 5 sequential HN pages into one fixture dir.
# Sequence the 5 URLs with --wait 30 to honor HN's robots.txt 30s crawl-delay.
SLUG="s16_hn_pagination"
OUTDIR="fixtures/snapshots/$SLUG"
mkdir -p "$OUTDIR"

for P in 1 2 3 4 5; do
  wget \
    --no-clobber \
    --convert-links \
    --adjust-extension \
    --page-requisites \
    --no-host-directories \
    --execute robots=off \
    --user-agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36' \
    --wait=30 \
    --tries=2 \
    --timeout=30 \
    --output-document="$OUTDIR/p${P}.html" \
    "https://news.ycombinator.com/?p=${P}"
done
```

**Note on `--convert-links`:** When capturing 5 separate pages, wget rewrites links within each page to point to the downloaded resources. The "next page" link inside `p1.html` will point at `p2.html` after rewriting — verify this is the case post-capture (manual check: `grep '?p=2' p1.html` should be replaced with a relative `p2.html` link). If wget doesn't link-rewrite across separate `--output-document` invocations, the planner should add a `sed` pass to convert `?p=N` references to `pN.html` so the MCPs can navigate "next page" within the snapshot.

### Pattern 3: Framework Variant Build (Next.js / SvelteKit / Vue / Vanilla)

**What:** Scaffold each framework in a temp directory OUTSIDE the repo, build the static export, copy the built artifact into `fixtures/snapshots/framework_variant_<name>/`, discard the scaffold.

**When to use:** D-08 (S23-S26).

**Why temp dir, not in-repo:** A committed scaffold would blow the 50MB budget (`node_modules` alone is 200+MB for Next.js) AND introduce a non-static dependency. CONTEXT.md is explicit: "the build artifacts are the fixture; we do NOT ship the framework scaffolds in the repo."

**Next.js variant (S23):**

```bash
# Author-time only. Mac Mini. Outside repo.
SCRATCH=$(mktemp -d)
cd "$SCRATCH"
npx create-next-app@latest fv-nextjs --typescript --no-tailwind --no-eslint --app --use-npm
cd fv-nextjs

# Configure for static export + subdir hosting.
cat > next.config.js <<'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath: '/framework_variant_nextjs',
  trailingSlash: true,
  images: { unoptimized: true },  // critical for static export with no remote loader
};
module.exports = nextConfig;
EOF

# Wire up app/page.tsx to render the 10-product list from data.json.
# Use a Server Component so the HTML ships pre-rendered (the SSR-with-hydration story).
cp /path/to/fixtures/framework-variants/data.json public/data.json
# ... edit app/page.tsx to fetch /data.json + render product list ...

npm run build
# Output is in ./out/

# Copy into repo:
cp -R out/. "$REPO/fixtures/snapshots/framework_variant_nextjs/"

# Discard scaffold.
cd / && rm -rf "$SCRATCH"
```

**SvelteKit variant (S24):**

```bash
SCRATCH=$(mktemp -d)
cd "$SCRATCH"
npx sv create fv-sveltekit --template minimal --types ts --no-add-ons --install npm
cd fv-sveltekit
npm i -D @sveltejs/adapter-static

# Configure svelte.config.js for static adapter + subdir.
cat > svelte.config.js <<'EOF'
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
export default {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({ pages: 'build', assets: 'build', fallback: undefined, precompress: false, strict: true }),
    paths: { base: '/framework_variant_sveltekit' },
  },
};
EOF

# Mark root layout prerenderable.
mkdir -p src/routes
cat > src/routes/+layout.ts <<'EOF'
export const prerender = true;
EOF

# ... edit src/routes/+page.svelte to fetch data.json + render list ...
cp /path/to/fixtures/framework-variants/data.json static/data.json

npm run build
# Output is in ./build/

cp -R build/. "$REPO/fixtures/snapshots/framework_variant_sveltekit/"
cd / && rm -rf "$SCRATCH"
```

**Vue 3 + Vite variant (S25):**

```bash
SCRATCH=$(mktemp -d)
cd "$SCRATCH"
npm create vite@latest fv-vue -- --template vue-ts
cd fv-vue
npm install

# Configure vite.config.ts for subdir.
cat > vite.config.ts <<'EOF'
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
export default defineConfig({
  plugins: [vue()],
  base: '/framework_variant_vue/',
});
EOF

# ... edit src/App.vue to fetch /framework_variant_vue/data.json + render list ...
cp /path/to/fixtures/framework-variants/data.json public/data.json

npm run build
# Output is in ./dist/

cp -R dist/. "$REPO/fixtures/snapshots/framework_variant_vue/"
cd / && rm -rf "$SCRATCH"
```

**Vanilla variant (S26):**

```bash
# Hand-author one file. No scaffold, no build.
cat > "$REPO/fixtures/snapshots/framework_variant_vanilla/index.html" <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Open Source Outpost — Products</title></head>
<body>
  <h1>Products</h1>
  <ul id="products"></ul>
  <script>
    fetch('data.json')
      .then(r => r.json())
      .then(items => {
        const ul = document.getElementById('products');
        for (const p of items) {
          const li = document.createElement('li');
          li.innerHTML = `<strong>${p.name}</strong> — ${p.price} — <em>${p.short_description}</em>`;
          ul.appendChild(li);
        }
      });
  </script>
</body>
</html>
EOF
cp "$REPO/fixtures/framework-variants/data.json" "$REPO/fixtures/snapshots/framework_variant_vanilla/data.json"
```

**Critical:** All four variants render the SAME 10 products. A verification task at the end of the framework-variant wave does: `for variant in nextjs sveltekit vue vanilla; do extract_products "$variant"; done` and asserts identical output.

### Pattern 4: PROVENANCE.md v1.1 Format

Existing v1.0 format + two new fields (DESIGN-03 agent-task tag, FAIRNESS-08 rendering archetype):

```markdown
# Snapshot provenance — <slug>

- **Source URL:** <url OR "synthetic — hand-authored">
- **Capture date:** YYYY-MM-DD (UTC)
- **Capture timestamp:** YYYY-MM-DDTHH:MM:SSZ
- **Capture tool:** <"GNU Wget 1.25.0..." OR "hand-authored" OR "Next.js 16.x static export, npx create-next-app@latest scaffold">
- **License:** <"CC BY-SA 4.0 (Wikipedia)" / "public-domain-ish (HN titles+links)" / "DuckDuckGo SERP — see Legal note below" / "synthetic — license-clean by construction">
- **Agent-task tag (DESIGN-03):** <one sentence: "Proxies extracting a product detail page for a price-comparison agent.">
- **Rendering archetype (FAIRNESS-08):** <"classic server-rendered HTML" / "React 18 / Next.js SSR-with-hydration" / "SvelteKit" / "Vue 3 SPA" / "vanilla static" / "synthetic semantic HTML+ARIA">
- **Scrubbing applied:**
  - NAME_REGEX iterated to convergence
  - Count of pre-scrub non-allow-listed matches: <N>
  - Allow-list deltas: <list, or "none">
- **Directory SHA256:** <sha>
- **Files captured:** <N>
- **Total bytes (served content):** <N>
- **Primary HTML:** `<path>` (<N> bytes)
- **Reason for capture:** <"frozen reproducibility surface" / "synthetic to give MCPs a deterministic AJAX cart">
- **Stages served:** <"S13, S14, S15, S21, S22" for the Wikipedia fixture; "S9, S10, S11" for the e-commerce fixture>
```

### Anti-Patterns to Avoid

- **Pulling in framework `node_modules/` directories.** Blows the size budget; introduces a non-static dependency.
- **Capturing live SERPs at run-time during scoring.** The whole point of the fixture-set is byte-for-byte reproducibility — re-capturing would mean every score-run sees a different SERP.
- **Authoring the synthetic auth-walled fixture with real-looking PII.** Use Jane Testworth ONLY; any other "realistic" looking name would trip the scrub.
- **Using a CDN-hosted React/Vue/Svelte runtime in the vanilla variant.** Defeats the point — vanilla MUST be zero-framework.
- **Storing the `data.json` only at `fixtures/framework-variants/data.json` without copying into each variant.** Each variant must be self-contained for loopback serving from its own subdir.
- **Capturing Wikipedia with `--page-requisites` and pulling all CSS/images.** Will exceed 5MB per fixture trivially. Use `--reject 'jpg,jpeg,png,gif,svg,webp,ico'` to drop images; keep only the structural HTML + minimal Wikipedia CSS for table-sort.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Static HTML mirroring | Custom curl loop | `wget --mirror` (existing pattern) | Handles link rewriting, page-requisites, idempotent re-runs |
| PII scrubbing | New regex pipeline | Existing `bench/scrub_artifacts.py` | Already tested with `tests/test_scrub_artifacts.py`; allow-list extension is the only change needed |
| Loopback HTTP server | Bespoke daemon | Existing `scripts/serve_fixtures.sh` (Python http.server) | Already tested with `tests/test_snapshot_serves.sh`; nested dir tree walking is native |
| Next.js / SvelteKit / Vue static export | Hand-roll a bundler | Each framework's canonical `output: 'export'` / `adapter-static` / `vite build` | Reproducible, version-pinnable, matches what real apps ship |
| Invariants audit | New diff script | Existing `bench/wave_close_check.py` | Already locked at v1.0 close (2026-05-28); unchanged through v1.1 except for CANDIDATE-03 |
| Per-fixture size enforcement | Manual `du` per-fixture | Single audit step at end of finalize wave | `du -sh fixtures/snapshots/*/ | awk '$1 > 5MB {exit 1}'` is one-liner |

**Key insight:** Phase 6 is ASSET production. Every piece of mechanism the harness needs already exists. The only "new" tooling is the Node toolchain for the framework-variant authoring path, and even there the canonical scaffolds carry the build pipeline as a managed product.

## Runtime State Inventory

> Phase 6 is a fixture-authoring phase (asset creation). It does NOT rename anything, refactor existing code, or migrate stored data. Runtime State Inventory does not apply.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified by inspection. No databases, no stored state. | None |
| Live service config | None — verified by inspection. Fixture server is stateless Python http.server. | None |
| OS-registered state | None — verified by inspection. No background services. | None |
| Secrets/env vars | None new. `FIRECRAWL_API_KEY` is unaffected (Firecrawl is a Phase 8 re-scoring concern, not Phase 6). | None |
| Build artifacts | The framework-variant builds produce `out/build/dist/` — these are the fixture contents themselves, and the scaffolds are discarded. No drift surface. | None |

## Common Pitfalls

### Pitfall 1: DDG + Brave SERP Robots.txt Block

**What goes wrong:** wget without `--execute robots=off` will refuse to mirror `html.duckduckgo.com/html/?q=...` and `search.brave.com/search?q=...`. Even with the override, there's a legal posture question — both robots.txt say `Disallow: /` (DDG) and `Disallow: /search` (Brave).

**Why it happens:** [VERIFIED: WebFetch of both robots.txt files on 2026-05-29.]

**How to avoid:**
1. The existing `scripts/snapshot_fixtures.sh` already passes `--execute robots=off` — technical capture works.
2. Document the override + the legal posture in each SERP fixture's PROVENANCE.md:
   - Single capture for archival benchmarking research
   - One-time, frozen snapshot (no re-crawl, no commercial use)
   - The captured SERP page itself, not the indexed third-party content
3. Consider escalating to a discuss-phase reopener if the legal posture is a hard block — the alternative is **synthetic SERP fixtures** (compose a fake SERP with realistic shape and 10 fake organic results) which fully satisfies FAIRNESS-09 / FAIRNESS-10 with zero legal exposure.

**Warning signs:** wget log shows `User-agent: * Disallow: /` and exits without mirroring; or the captured HTML is a 0-byte redirect to the robots-block page.

### Pitfall 2: Wikipedia Capture Size Blowout

**What goes wrong:** `wget --mirror --page-requisites` against a Wikipedia article pulls every image, every Wikipedia chrome CSS file, every footnote-icon — easily 10-30MB per article. The 5MB-per-fixture budget is busted.

**Why it happens:** Wikipedia articles reference dozens of small assets (favicons, math-render images, Commons photos).

**How to avoid:**
1. Use `--reject 'jpg,jpeg,png,gif,svg,webp,ico'` to drop all image formats.
2. After mirroring, audit: `find fixtures/snapshots/s13_15_21_22_wikipedia/ -type f -name '*.css' -size +500k -delete` to drop oversized Wikipedia CSS bundles. The static HTML + a single minimal CSS for table sort is enough.
3. **Verify the sortable table still sorts after pruning.** Wikipedia's `mw-sortable` tables require jQuery + `sortable.js` — the inline JS reference must remain in the HTML, but the actual `sortable.js` file may need to be captured from `upload.wikimedia.org` (whose mirror by default goes outside `--no-parent` scope).

**Warning signs:** `du -sh fixtures/snapshots/s13_15_21_22_wikipedia/` > 5MB on first capture; or S22 prompt (sort-by-column) fails because table sort JS is missing.

### Pitfall 3: HN robots.txt 30s Crawl-Delay

**What goes wrong:** Capturing 5 sequential HN pages without `--wait=30` violates HN's robots.txt politeness requirement [VERIFIED: WebFetch of news.ycombinator.com/robots.txt] and could trigger a temporary IP block.

**How to avoid:** Add `--wait=30` to the wget invocations. Total capture wall-clock: 5 × 30s = 150s. Document the wait time in PROVENANCE.md.

### Pitfall 4: Framework Variant `basePath` / `base` Mismatch

**What goes wrong:** If the Next.js `basePath` or Vite `base` doesn't match the served subdirectory exactly, all JS/CSS asset paths in the produced HTML will 404 when served from `http://127.0.0.1:8765/framework_variant_nextjs/`.

**How to avoid:**
- Next.js: `basePath: '/framework_variant_nextjs'` (NO trailing slash in basePath; `trailingSlash: true` is for URL handling).
- SvelteKit: `kit.paths.base: '/framework_variant_sveltekit'`.
- Vite/Vue: `base: '/framework_variant_vue/'` (trailing slash REQUIRED per Vite docs).

**Verification step (REQUIRED):** After each variant is committed, start the fixture server and curl the entry point:
```bash
scripts/serve_fixtures.sh start
curl -sf http://127.0.0.1:8765/framework_variant_nextjs/ > /dev/null   # exits 0
# Then check a referenced asset:
curl -sf http://127.0.0.1:8765/framework_variant_nextjs/_next/static/chunks/main.js > /dev/null
scripts/serve_fixtures.sh stop
```

### Pitfall 5: Synthetic Fixture Triggers NAME_REGEX False Positives

**What goes wrong:** Hand-authoring an e-commerce PDP with realistic product names like "Mechanical Keyboard" or "USB Hub Pro" matches `\b[A-Z][a-z]+ [A-Z][a-z]+\b` — `bench/scrub_artifacts.py` flags them as PII.

**Why it happens:** The regex is intentionally over-zealous to avoid false negatives on real PII. v1.0 dealt with this by allowlisting `Jane Testworth` only.

**How to avoid:** Extend the allow-list. Two options:
1. **Per-fixture `.scrub_allow.txt`** alongside each synthetic fixture — extend `scrub_artifacts.py` to auto-discover these files. (More work, more maintainable.)
2. **Single global allow-list extension** in `bench/scrub_artifacts.py` `DEFAULT_ALLOW` — add the synthetic product names + "Open Source" + "Mechanical Keyboard" etc. (Simpler, slight risk of allowlisting a real-PII collision.)

**Recommendation:** Option 1 (per-fixture `.scrub_allow.txt` files). Existing CLI already supports `--allow <file>` flag (line 192-197 of `bench/scrub_artifacts.py`). The change is one method that walks `fixtures/snapshots/*/` for `.scrub_allow.txt` files and unions them, OR have the test harness pass `--allow` per fixture.

**Warning signs:** `bench/scrub_artifacts.py` exits 1 with `FLAG: fixtures/snapshots/s09_ecommerce_pdp/index.html:42: Mechanical Keyboard`.

### Pitfall 6: HN Pagination Link-Rewrite Failure

**What goes wrong:** `wget --output-document=p1.html` captures page 1, but the "next" link inside `p1.html` still points at `https://news.ycombinator.com/?p=2`, not the relative `p2.html`. When a multi-page MCP follows the link, it goes to the live HN site, contaminating the test.

**How to avoid:** Post-capture `sed` pass:
```bash
for P in 1 2 3 4 5; do
  N=$((P+1))
  sed -i.bak -e "s|https://news.ycombinator.com/\\?p=${N}|p${N}.html|g" \
             -e "s|news.ycombinator.com/news\\?p=${N}|p${N}.html|g" \
             "$OUTDIR/p${P}.html"
done
find "$OUTDIR" -name '*.bak' -delete
```

**Warning signs:** S16 prompt cell tells the MCP to "navigate to page 2", and the MCP loads a live HN response (visible from a non-localhost URL in tool logs).

### Pitfall 7: Build Output Includes Hashed Filenames That Differ Per Build

**What goes wrong:** Vite produces files like `assets/index-Bx7kL9aP.js` where the hash changes between builds. The SHA256 of the fixture dir is NOT stable across re-captures — defeats the v1.0 PROVENANCE pattern.

**Why it happens:** Hashed filenames are a build-cache mechanism; they're content-addressed BUT shift with build tooling versions.

**How to avoid:**
- The SHA256 documented in PROVENANCE.md is a single-build snapshot, NOT a reproducibility contract for re-builds (which the framework variants aren't expected to support — they're frozen artifacts).
- Document explicitly in the framework-variant PROVENANCE.md: "build artifacts are committed as-frozen; re-running the build will produce different content-addressed filenames."

### Pitfall 8: Sacrosanct Triad Audit False Positive

**What goes wrong:** `bench/wave_close_check.py` audits `scoring/score.py`, `scoring/rubric.md`, and `.mcp.json`. If any contributor accidentally edits these (a typo fix in rubric.md, etc.), the audit fails and the phase is blocked.

**Why it happens:** Easy slip during Phase 6 work — the auditor is paranoid by design.

**How to avoid:** Add `bench/wave_close_check.py` audit as the LAST step in EVERY plan in Phase 6 (cheap to run, fails fast). Pre-commit hook integration is also a v1.0 carry-forward.

## Code Examples

### Cart-add AJAX (verified vanilla JS pattern, hand-authored)
See Pattern 1 above.

### wget --mirror with image rejection for Wikipedia capture
```bash
wget \
  --mirror \
  --convert-links \
  --adjust-extension \
  --page-requisites \
  --no-parent \
  --no-host-directories \
  --execute robots=off \
  --reject 'jpg,jpeg,png,gif,svg,webp,ico' \
  --reject-regex '.*(upload\.wikimedia|wikimedia\.org/api).*' \
  --user-agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36' \
  --tries=2 \
  --timeout=30 \
  --directory-prefix=fixtures/snapshots/s13_15_21_22_wikipedia/ \
  'https://en.wikipedia.org/wiki/Comparison_of_programming_languages_(syntax)'
```

### Next.js static export config (verified — Next.js 16.2.6 official docs)
```js
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath: '/framework_variant_nextjs',
  trailingSlash: true,
  images: { unoptimized: true },
};
module.exports = nextConfig;
```
**Source:** [CITED: nextjs.org/docs/app/guides/static-exports — verified 2026-05-29]

### SvelteKit static adapter config (verified — svelte.dev docs)
```js
// svelte.config.js
import adapter from '@sveltejs/adapter-static';
export default {
  kit: {
    adapter: adapter(),
    paths: { base: '/framework_variant_sveltekit' },
  },
};
```
**Source:** [CITED: svelte.dev/docs/kit/adapter-static — verified 2026-05-29]

### Vite/Vue base config (verified — vite.dev docs)
```js
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
export default defineConfig({
  plugins: [vue()],
  base: '/framework_variant_vue/',
});
```
**Source:** [CITED: vite.dev/guide/build — verified 2026-05-29]

### scrub_artifacts.py allow-list extension (NO LOGIC CHANGE)
The existing CLI already accepts `--allow <file>` flag. The Phase 6 work is to either:
(a) Create `fixtures/snapshots/<slug>/.scrub_allow.txt` per synthetic fixture and document the harness contract that the runner unions them, OR
(b) Add to `bench/scrub_artifacts.py` `DEFAULT_ALLOW`:
```python
DEFAULT_ALLOW: frozenset[str] = frozenset({
    "Jane Testworth",
    # v1.1 synthetic fixture proper-noun allow-list (Phase 6 extension):
    "Open Source",          # store name
    "Mechanical Keyboard",  # product (S9-11)
    "Project Store",        # store name
    "USB Hub",              # product
    # ...add more as fixtures are authored
})
```

## State of the Art

| Old Approach (Phase 1, v1.0) | Current Approach (Phase 6, v1.1) | When Changed | Impact |
|------------------------------|----------------------------------|--------------|--------|
| Two captured snapshots (Greenhouse, Ashby) | 12+ fixture directories spanning capture + synthetic + framework-builds | Phase 6 | Forces the snapshot toolchain to generalize beyond `greenhouse\|ashby` whitelist |
| PROVENANCE.md = source-URL + scrub + SHA | + agent-task tag (DESIGN-03) + rendering archetype (FAIRNESS-08) | Phase 6 | Two new fields per PROVENANCE.md; planner template update |
| Stage prompts S1-S8 (locked) | Stage prompts S1-S26 (S1-S8 locked, S9-S26 appended) | Phase 6 | `prompts/stage_walk.md` append-only edit |
| No framework-variant builds | 4 framework-variant builds with shared `data.json` | Phase 6 | Node toolchain becomes an author-time dependency |
| Robots.txt-permissive sources (Greenhouse, Ashby) | Two robots.txt-blocked sources (DDG, Brave) | Phase 6 (D-02) | Documented override; planner must surface this risk |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Wikipedia article "Comparison of programming languages (syntax)" has an infobox | Phase Requirements / FIXTURE-06 | LOW — WebFetch said no traditional infobox. Article still has sortable tables + footnotes, so S14 prompt may need adjustment ("extract any prominent floating-info block" instead of literal `<aside class="infobox">`). Or planner picks a different Wikipedia article with an infobox. |
| A2 | Wikipedia's `mw-sortable` table sort JS captures into a static mirror | Pattern 2 + Pitfall 2 | MEDIUM — mw-sortable requires jQuery + a Wikipedia-specific sortable.js. wget may not capture cross-domain JS. The fix is either (a) confirm post-capture that sort still works, or (b) author a small inline JS that re-implements column-sort on the captured table. S22 prompt cell would then test the synthetic sort, not the Wikipedia-native one. |
| A3 | `npx create-next-app@latest` succeeds on Mac Mini with Node 22 | Pattern 3 framework variant build | LOW — Standard scaffold path. If it fails, the planner reverts that variant to a hand-authored "Next.js-style" SSR-with-hydration page. The fixture wouldn't be a "real" Next.js build but would still serve the rubric purpose. |
| A4 | `sv create` (SvelteKit CLI) command syntax | Pattern 3 | LOW — Current SvelteKit init command is `npx sv create`; older `npm create svelte@latest` is the deprecated path. Confirm against svelte.dev on author-day. |
| A5 | Hand-authored `data.json` with 10 products fits well under the 5MB-per-fixture budget | Size Budget | HIGH confidence the budget is fine — 10 product records as JSON is < 5KB. |
| A6 | DDG SERP and Brave SERP captures pass legal review for "research-archival" use | Pitfall 1 | MEDIUM — Both robots.txt say Disallow. The legal posture is "single capture, archival benchmarking, no commercial use" — defensible but not explicit fair-use. Discuss-phase locked this decision; planner should add a discuss-phase reopener task IF the author has any qualms during capture. |
| A7 | The Mac Mini has Node 22 LTS + npx + npm in the path | Stack | LOW — CLAUDE.md project standard is Node 22 LTS; confirm with `node --version` at the start of the framework-variant wave. |
| A8 | Wikipedia article is ~400-500KB body HTML | WebFetch estimate | LOW — within 5MB budget by 10× margin. |

## Open Questions

1. **Wikipedia infobox presence in `Comparison_of_programming_languages_(syntax)`?**
   - What we know: WebFetch suggests no traditional infobox; uses "navigation templates and content boxes."
   - What's unclear: Whether S14 prompt cell ("extract table-in-article + infobox") needs the article changed OR the prompt loosened to "infobox-or-equivalent floating-info block".
   - Recommendation: Planner checks the live page during snapshot. If infobox absent, either (a) pick a different "Comparison of X" article with a confirmed infobox (e.g., a less-comparison-table-y article would also serve), or (b) adjust the S14 prompt cell wording. Both are fast resolutions.

2. **Sortable-table JS capture for S22?**
   - What we know: Wikipedia tables marked `class="wikitable sortable"` use `mw-sortable` JS for in-page sort.
   - What's unclear: Whether `wget --mirror` captures the sort JS (loaded from `https://en.wikipedia.org/w/load.php?...`) into the snapshot.
   - Recommendation: Planner does a smoke test after capture: serve the fixture, open in browser, click a sortable column header. If it sorts → snapshot is complete. If not → write a 30-line inline `<script>` that adds click handlers + sorts. This is an in-the-wave acceptance step.

3. **Per-fixture `.scrub_allow.txt` vs global `DEFAULT_ALLOW` extension?**
   - What we know: Existing CLI already supports `--allow <file>`. Test harness pattern is `subprocess.run([..., "-m", "bench.scrub_artifacts", str(target)])`.
   - What's unclear: Which is the lower-friction extension — per-fixture file (more files, tighter scope) or global extension (fewer files, broader allowance).
   - Recommendation: **Per-fixture `.scrub_allow.txt`** with a small `bench/scrub_artifacts.py` enhancement to auto-discover `.scrub_allow.txt` siblings to the scanned root. Confines allow-list scope to the fixture that needs it; no global allow-list growth across milestones.

4. **Should DDG/Brave captures be replaced with synthetic SERP fixtures?**
   - What we know: Both robots.txt say `Disallow: /`. CONTEXT.md D-02 locks captured.
   - What's unclear: Whether the legal posture is comfortable enough to ship a public benchmark with these captures.
   - Recommendation: Planner proceeds with captured per CONTEXT.md, but Phase 6 finalize wave includes a "human-verify" checkpoint where the author reviews the captured SERP HTML + the legal-posture note in PROVENANCE.md before commit. If unease, the planner inserts a discuss-phase reopener task.

5. **Does Next.js 16.2.6 SSR-with-hydration ship a noticeable JS-rendering surface, or is `output: 'export'` effectively just a static SPA?**
   - What we know: Next.js docs say Server Components run at build time → HTML is pre-rendered. Client Components hydrate after.
   - What's unclear: Whether a read-only MCP like Firecrawl sees the pre-rendered HTML directly (which would make Next.js indistinguishable from vanilla for that MCP), or if there's a meaningful difference.
   - Recommendation: Author the Next.js variant with a Client Component that does at least one post-mount DOM mutation (e.g., a "Loading..." → "Loaded N products" transition driven by `useEffect`) so the SSR-vs-hydration distinction is observable. This is what FAIRNESS-08 is asking the fixture to test.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `wget` | Captured-fixture path (D-02, D-03, D-04, D-07) | ✓ (assumed Homebrew) | 1.25.0+ | None — required |
| `python3` (.venv 3.12) | scrub_artifacts.py, serve_fixtures.sh, sed-replacement Python in snapshot_fixtures.sh | ✓ (verified in existing PROVENANCE) | 3.12 | None — required |
| `node` | Framework-variant scaffolds (D-08) | Unknown — verify before wave | 22 LTS expected | Hand-author "Next.js-style" SPA pages if scaffold fails |
| `npm` / `npx` | Framework-variant scaffolds | Bundled with Node | — | Same as above |
| `sed`, `find`, `awk`, `shasum` | Snapshot script | ✓ (BSD on macOS) | — | None — required |
| `curl` | tests/test_snapshot_serves.sh + verification | ✓ | — | None — required |
| `git` | wave_close_check.py audit | ✓ | — | None — required |

**Missing dependencies with no fallback:** None expected on Mac Mini. Confirm `node --version` at wave start.

**Missing dependencies with fallback:** Framework scaffold tools — if Node 22 isn't available, drop to hand-authored "framework-style" HTML for the affected variant and document in PROVENANCE.md.

## Validation Architecture

> Nyquist validation is enabled (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (Python stdlib) + bash test scripts |
| Config file | none — tests are direct subprocess invocations |
| Quick run command | `uv run python -m unittest tests.test_scrub_artifacts -v` (≤ 10s) |
| Full suite command | `uv run python -m unittest discover -s tests` + `bash tests/test_snapshot_serves.sh` |
| Phase gate | `bench/wave_close_check.py all_pass=True` + `bench/scrub_artifacts.py fixtures/snapshots/` exit 0 + full unittest suite green |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIXTURE-01 | S9 fixture HTTP 200, body > 1KB | smoke | `curl -fs http://127.0.0.1:8765/s09_ecommerce_pdp/ \| wc -c` ≥ 1024 | ❌ Wave 0 — extend `tests/test_snapshot_serves.sh` |
| FIXTURE-02 | S10 cart-add JS deterministically mutates DOM | unit (browser-based) | Manual or harness-driven | Skip automated — manual verify in finalize wave |
| FIXTURE-03 | S11 cart-state extractable post-mutation | unit (browser-based) | Manual or harness-driven | Skip automated — manual verify |
| FIXTURE-04 | S12 DDG + Brave SERP HTTP 200 | smoke | curl per fixture | ❌ Wave 0 — extend test_snapshot_serves.sh |
| FIXTURE-05..07 | S13-15 Wikipedia HTTP 200 + body > 50KB | smoke | curl + wc -c | ❌ Wave 0 |
| FIXTURE-08 | S16 HN p1..p5 all HTTP 200; link-rewrite verified | smoke + grep | `for P in 1 2 3 4 5; do curl -fs ".../p${P}.html"; done`; `grep -q "p2.html" p1.html` | ❌ Wave 0 |
| FIXTURE-09..10 | S17/S18 login+dashboard serve | smoke | curl | ❌ Wave 0 |
| FIXTURE-11..12 | S19/S20 complex form serves | smoke | curl | ❌ Wave 0 |
| FIXTURE-13..14 | S21/S22 table extract — same fixture as Wikipedia | (covered by FIXTURE-05..07) | — | — |
| FIXTURE-15..18 | S23-S26 framework variants serve; entry + main JS chunk 200 | smoke | `curl -fs <variant>/ && curl -fs <variant>/_next/static/chunks/main.js` (path varies per framework) | ❌ Wave 0 |
| DESIGN-01 | Read-vs-drive 50/50 in S9-S26 prompt cells | grep | `grep -c "^**Type:**.*read$" prompts/stage_walk.md` ≈ `grep -c "^**Type:**.*drive$"` | ❌ Wave 0 — add a `tests/test_stage_walk_balance.py` |
| DESIGN-02 | S16 prompt requires ≥3 pages | grep | `grep -A 20 '^## S16' prompts/stage_walk.md \| grep -q "across all 5 pages\|pages 1.*5"` | ❌ Wave 0 — fold into balance test |
| DESIGN-03 | Every PROVENANCE.md has agent-task tag | grep | `for f in fixtures/snapshots/*/PROVENANCE.md; do grep -q "Agent-task tag" "$f" \|\| exit 1; done` | ❌ Wave 0 — new `tests/test_provenance_complete.sh` |
| FAIRNESS-08 | Every PROVENANCE.md has rendering-archetype field | grep | same shape as above | ❌ Wave 0 — fold into provenance test |
| FAIRNESS-09 | Each new stage stresses ≥1 dimension S1-S8 doesn't | manual audit | — | Manual review in finalize wave |
| FAIRNESS-10 | No MCP-specific bias | manual audit | — | Manual review |
| FAIRNESS-12 | Semantic+ARIA fixture(s) present + div-soup fixture(s) present | grep | `grep -rq 'aria-label' fixtures/snapshots/s09_ecommerce_pdp/` ; `grep -rq 'role=' fixtures/snapshots/s17_18_auth_walled/` | ❌ Wave 0 — extend test_snapshot_serves.sh |
| REPRO-09 | Loopback only | covered by tests/test_snapshot_serves.sh (existing) | already exists | ✅ |
| REPRO-10 | scrub_artifacts.py exits 0 | unit | `uv run python -m bench.scrub_artifacts fixtures/snapshots/` | ✅ existing — extend per-fixture allow-lists |
| REPRO-11 | ≤ 5MB/fixture; ≤ 50MB total | unit | `bash tests/test_size_budget.sh` | ❌ Wave 0 — new test |
| REPRO-12 | License-clean per fixture | grep | `for f in fixtures/snapshots/*/PROVENANCE.md; do grep -q "License:" "$f" \|\| exit 1; done` | ❌ Wave 0 |
| REPRO-13 | Cross-platform parity | manual — Phase 7 territory | — | Out of scope this phase; flag in PROVENANCE.md if any fixture has platform-specific gotchas |
| Sacrosanct triad invariant | `wave_close_check.py all_pass=True` | unit | `uv run python -m bench.wave_close_check` | ✅ existing |

### Sampling Rate
- **Per task commit:** `bash tests/test_snapshot_serves.sh` (boot server, curl each new fixture root, stop server) + `uv run python -m bench.scrub_artifacts fixtures/snapshots/<new-slug>/` + `uv run python -m bench.wave_close_check`. Wall-clock: ~5-10s.
- **Per wave merge:** Full unittest suite + all snapshot serve tests + scrub of entire `fixtures/snapshots/` tree + size-budget audit. Wall-clock: ~20-30s.
- **Phase gate:** Full suite green + `du -sh fixtures/snapshots/` ≤ 50 MB + every PROVENANCE.md has all required fields (DESIGN-03 + FAIRNESS-08).

### Wave 0 Gaps
- [ ] `tests/test_snapshot_serves.sh` — extend the `expected_dirs=()` list with the 12 new fixture roots (S9-S26 share 12 distinct dirs after merging same-fixture stages)
- [ ] `tests/test_provenance_complete.sh` — verify every PROVENANCE.md has source URL, license, agent-task tag, rendering archetype, scrub log
- [ ] `tests/test_size_budget.sh` — assert `du -sh fixtures/snapshots/` ≤ 50MB AND every direct child ≤ 5MB
- [ ] `tests/test_stage_walk_balance.py` — verify S9-S26 prompt cells contain a `**Type:** read|drive` tag, the count is 9:9 ±1 (DESIGN-01), and S16's prompt requires ≥3 pages (DESIGN-02)
- [ ] `tests/fixtures/` may need golden-file fixtures for the synthetic-fixture cart-AJAX test if we automate that, but recommend manual verification in finalize wave for now

*(All existing tests under `tests/` remain unchanged; only additive test files needed.)*

## Security Domain

> The `security_enforcement` key is absent from `.planning/config.json` → treated as enabled per the workflow contract. Phase 6 is a fixture-authoring phase serving only loopback-bound static files, so the ASVS surface is narrow.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | partial | Synthetic auth-walled fixture uses a **fake** cookie — no real auth. Document explicitly in PROVENANCE.md that the cookie is non-credential. |
| V3 Session Management | partial | Same — `session=fake-token-xyz` is intentionally not a credential. Auth contract is "any non-empty input passes" (D-11). |
| V4 Access Control | no | No real access boundaries; loopback-only. |
| V5 Input Validation | yes | Complex form fixture (D-06) MUST implement client-side validation per FIXTURE-12; that IS the test. Use HTML5 `pattern=`, `required`, plus inline JS `<input>` event handlers. |
| V6 Cryptography | no | No cryptographic operations in any fixture. |
| V7 Error Handling | partial | Complex form (S20) error recovery is the test. Inline error messages with `role="alert"` for accessibility. |
| V8 Data Protection | yes | NO PII in fixtures — Jane Testworth mock + scrub_artifacts.py enforcement is the v1.0 inherited contract. |
| V14 Configuration | yes | Loopback-bind enforced by `serve_fixtures.sh` (`--bind 127.0.0.1`) — explicit at server-spawn time. |

### Known Threat Patterns for fixture-authoring stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PII leaks in committed fixtures | Information Disclosure | `bench/scrub_artifacts.py` (existing) + Jane Testworth allow-list + per-fixture `.scrub_allow.txt` |
| Captured SERP contains tracker URLs / cookies | Information Disclosure | wget output retains source HTML as-is; manual scan post-capture: `grep -i "set-cookie\|google-analytics\|doubleclick" fixtures/snapshots/s12_serp_*/index.html` |
| Synthetic cookie misinterpreted as credential | Confusion / Repudiation | PROVENANCE.md explicit "fake cookie, no auth surface"; cookie value `fake-token-xyz` is self-evidently non-secret |
| Fixture server bound to non-loopback | Information Disclosure | Existing `--bind 127.0.0.1` hardcoded; covered by v1.0 invariant |
| External resource references in captured HTML (CSS/JS/fonts) | Network Tampering during scoring | wget `--convert-links` rewrites paths; manually verify NO `http://`-prefixed sources remain after capture; if any do, `sed` them out or document in PROVENANCE |
| Framework-variant build pulls remote assets | Supply chain | Build-time only; the committed artifact has no remote refs after build. Audit: `grep -r "http[s]\?://" fixtures/snapshots/framework_variant_*/` should show only standalone-doctype references (or nothing) |

## Project Constraints (from CLAUDE.md)

- **Tech stack:** Python 3 + Markdown + shell. No framework for harness/scoring. Phase 6 introduces Node 22 LTS toolchain as AUTHOR-TIME ONLY for framework variants — committed artifacts are static.
- **Reproducibility:** Methodology must be runnable by a third party. Snapshot capture commands documented; framework-variant builds documented but artifacts are pre-built and committed.
- **Sandbox-only MCPs:** Cloakbrowser tested only on public Greenhouse/Ashby fixtures. Phase 6 does NOT alter this; Phase 8 owns the re-scoring decision.
- **Public repo:** `.mcp.json` byte-identical to v1.0. Phase 6 does NOT modify `.mcp.json`.
- **No tests deferred:** "EVERY piece of code MUST have unit tests" per CLAUDE.md — applies to any new test files; the fixtures themselves are HTML/data assets and are covered by smoke tests (curl + size + scrub).
- **Linear traceability:** Phase 6 has no existing umbrella ticket (per CONTEXT.md "Phase 6 has no upstream issues; all work is local"). Planner may consider a per-wave Linear ticket per project convention but this is at the planner's discretion.
- **Cross-machine:** Mac Mini is the primary; MacBook parity not verified for v1.1 either. REPRO-13 (cross-platform parity) is mostly Phase 7's concern.
- **Git workflow:** All changes via branches + PRs. Phase 6 will produce multiple commits across multiple branches per the standard GSD flow.
- **No bypass of GSD:** Project CLAUDE.md mandates that file edits route through GSD commands. Phase 6 is a planned phase — fully compliant.

## Wave Organization Recommendation

Given the 7 logical fixture groups + cross-cutting prep + finalize, the planner should organize Phase 6 as:

**Wave 0 (prep — sequential, blocks all other waves):**
- Plan 06-00-prep: Extend `bench/scrub_artifacts.py` if going the per-fixture-allow-list route (one method addition); extend `tests/test_snapshot_serves.sh` expected_dirs list; create `tests/test_provenance_complete.sh`, `tests/test_size_budget.sh`, `tests/test_stage_walk_balance.py`; generalize `scripts/snapshot_fixtures.sh` to accept `--slug` flag; add `fixtures/framework-variants/data.json` (the shared 10-product source).

**Wave 1 (captured fixtures — can run in parallel; independent files):**
- Plan 06-01-wikipedia (D-03, D-07): Capture Wikipedia article; verify table sort + footnotes intact; PROVENANCE.md.
- Plan 06-02-hn-pagination (D-04): Capture 5 HN pages with 30s wait; link-rewrite; PROVENANCE.md.
- Plan 06-03-serp-ddg-brave (D-02): Capture both SERPs (robots.txt override documented); PROVENANCE.md.

**Wave 2 (synthetic fixtures — can run in parallel; independent files):**
- Plan 06-04-ecommerce (D-01, S9-S11): Author PDP + cart AJAX + cart verification; PROVENANCE.md.
- Plan 06-05-auth-walled (D-05, S17-S18): Author login + dashboard with cookie-based fake session; PROVENANCE.md.
- Plan 06-06-complex-form (D-06, S19-S20): Author visa-application form with multi-select / date range / dependent fields / validation; PROVENANCE.md.

**Wave 3 (framework variants — sequential within wave; depends on data.json from Wave 0):**
- Plan 06-07-framework-vanilla (D-08, S26): Hand-author vanilla baseline. Quickest, lowest risk; do first.
- Plan 06-08-framework-vue (D-08, S25): Vite + Vue 3 scaffold + build.
- Plan 06-09-framework-sveltekit (D-08, S24): SvelteKit + adapter-static + build.
- Plan 06-10-framework-nextjs (D-08, S23): Next.js + `output: 'export'` + build. Highest complexity; do last.
- Plan 06-11-framework-variant-parity-check: Run extraction across all 4 variants; assert identical product list.

**Wave 4 (finalize — sequential, depends on all earlier waves):**
- Plan 06-12-stage-walk-extension: Append S9-S26 prompt cells to `prompts/stage_walk.md`; verify DESIGN-01 (read/drive 50/50) and DESIGN-02 (S16 multi-page).
- Plan 06-13-final-audit: Run all tests; `du -sh`; `wave_close_check.py all_pass=True`; mark FAIRNESS-11 as deferred in REQUIREMENTS.md per D-15; close out.

**Rationale:** Wave 0 must precede everything (data.json + scrub extension + test infrastructure). Waves 1-3 are largely parallelizable internally (each plan touches a different fixture dir). Wave 4 depends on all fixtures existing. Total estimated work: ~12-14 plans, ~16-22 hours depending on framework variant smooth-execution.

## Bias-Check (FAIRNESS-10)

Confirming the fixture set does not favor any single v1.0 MCP:

- **Playwright:** real Chrome, all rubric dims surfaceable → no fixture specifically advantages it.
- **Browser-use (direct):** Chromium + LLM-driven → frameworks-variants will exercise it equally with Playwright.
- **Chrome-devtools-mcp:** real Chrome via CDP → equivalent to Playwright on JS-heavy fixtures.
- **Lightpanda:** Zig JS engine, no React → categorical N/A on S23-S25 framework variants; SERP and Wikipedia are plain HTML so it does fine there.
- **Obscura:** Rust+V8 → can render the framework variants; capture-fixtures fine.
- **Firecrawl:** cloud SSR — **cannot reach loopback fixtures at all in v1.0; documented as N/A on the entire v1.1 fixture set.** This is a v1.0-inherited constraint, NOT a Phase 6 bias.
- **Cloakbrowser:** sandbox-only on Greenhouse/Ashby per global policy → **N/A on entire v1.1 fixture set per SAFETY-04 carryover.**

**Net:** Lightpanda has known categorical N/A on framework variants (which is intentional — that's what JS Rendering measures). Firecrawl + Cloakbrowser have systemic constraints inherited from v1.0. No fixture choice in Phase 6 was made to advantage any of the four real-Chrome MCPs over another.

## Size Budget

Per-fixture-dir budget audit (REPRO-11):

| Fixture | Expected size | Notes |
|---------|--------------|-------|
| s09_ecommerce_pdp (S9-S11) | ~10-50KB | Hand-authored HTML+CSS+inline JS |
| s12_serp_ddg | ~50-200KB | DDG /html/?q= returns plain HTML |
| s12_serp_brave | ~100-500KB | Brave SERP may include more chrome |
| s13_15_21_22_wikipedia | ~400-600KB | After image rejection; HTML body + minimal CSS |
| s16_hn_pagination | ~50KB × 5 = ~250KB | HN pages are tiny plain HTML |
| s17_18_auth_walled | ~10-30KB | 2 hand-authored HTML pages |
| s19_20_complex_form | ~20-50KB | More JS for dependent fields |
| framework_variant_vanilla | ~5-15KB | Single index.html + data.json |
| framework_variant_vue | ~50-150KB | Vite build with Vue runtime |
| framework_variant_sveltekit | ~50-200KB | Svelte runtime + adapter-static output |
| framework_variant_nextjs | ~200-500KB | React + Next.js chunks (largest single fixture) |
| **TOTAL estimated** | **~1.2 - 2.5 MB** | **Comfortable under 50MB budget (20× headroom)** |

The 5MB-per-fixture budget is the operative ceiling; Wikipedia and Next.js are the candidates worth watching. Both are well within tolerance based on standard expectations.

## License Posture

| Source | License | Citation | Disposition |
|--------|---------|----------|-------------|
| Wikipedia article body | CC BY-SA 4.0 | [VERIFIED: wikipedia.org/wiki/Wikipedia:Reusing_Wikipedia_content] | Attribution in PROVENANCE.md ("Source: Wikipedia, CC BY-SA 4.0"); compatible with public benchmark repo. |
| Hacker News pages | YC content (TOS); titles+links are factual | [VERIFIED: news.ycombinator.com/robots.txt allows non-interactive crawling with 30s delay] | Fair use for non-commercial archival benchmarking; minimal expressive content reproduced. |
| DuckDuckGo SERP (/html/) | Disallow per robots.txt | [VERIFIED: html.duckduckgo.com/robots.txt 2026-05-29] | **AT-RISK** — documented "single-capture archival research benchmark" posture in PROVENANCE.md; planner should consider checkpoint:human-verify before commit. |
| Brave SERP (/search) | Disallow per robots.txt | [VERIFIED: search.brave.com/robots.txt 2026-05-29] | Same as DDG. |
| Synthetic fixtures (D-01, D-05, D-06, D-08) | License-clean by construction | — | No external content. |

The **DDG + Brave robots.txt block** is the only legal-posture flag. Two mitigation paths:
1. Proceed as locked in CONTEXT.md (single capture, frozen archive, documented purpose), with a discuss-phase reopener option if the author has qualms.
2. Substitute synthetic SERP fixtures (would require re-opening CONTEXT.md D-02).

Recommendation: Path 1, with a checkpoint:human-verify task in the SERP plan.

## Cross-Platform Audit (REPRO-13)

Most fixtures are pure HTML/CSS/JS/JSON — fully cross-platform. The known platform-sensitivity surface is narrow:

- **wget output file modes** differ between macOS (rwx) and Linux (rw-) defaults. Committed files inherit the snapshot machine's umask. Audit step at the end of Wave 1: `git ls-files --stage fixtures/snapshots/ | awk '{print $1}' | sort -u` — should show only 100644 entries.
- **Framework-variant builds:** deterministic outputs across macOS/Linux assuming same Node/npm versions. Hashed asset filenames change between builds regardless of OS, but committed artifact is frozen.
- **Newline handling:** Wikipedia + HN captures may have CRLF line endings if any are passed through; `.gitattributes` should enforce LF for `*.html *.js *.css *.json` to avoid Windows-checkout drift.

REPRO-13's substantive verification happens in Phase 7 (harness Linux baseline). Phase 6 just produces the artifacts.

## Sources

### Primary (HIGH confidence)
- `.planning/phases/06-fixture-authoring-s9-s26/06-CONTEXT.md` — locked decisions D-01..D-15
- `.planning/REQUIREMENTS.md` — 31 phase-6 REQ-IDs
- `.planning/ROADMAP.md` Phase 6 — goal + success criteria
- `.planning/milestones/v1.0-phases/01-harness-foundation/01-CONTEXT.md` — v1.0 patterns inherited
- `.planning/milestones/v1.0-phases/01-harness-foundation/01-03-snapshot-fixtures-PLAN.md` — wget --mirror baseline pattern
- `fixtures/snapshots/greenhouse_2026-05-22/PROVENANCE.md` and `fixtures/snapshots/ashby_2026-05-22/PROVENANCE.md` — concrete format
- `bench/scrub_artifacts.py` — full source read; existing `--allow` flag verified
- `bench/wave_close_check.py` — full source read; verified the audit covers `.mcp.json`, `scoring/rubric.md`, `scoring/score.py`
- `scripts/serve_fixtures.sh` and `scripts/snapshot_fixtures.sh` — full source read
- `prompts/stage_walk.md` — full source read; S1-S8 lock confirmed
- `.planning/config.json` — verified `nyquist_validation: true`, `commit_docs: true`
- Next.js static export docs — [CITED: nextjs.org/docs/app/guides/static-exports, 2026-05-28] — `output: 'export'`, `basePath`, `unoptimized: true`
- SvelteKit adapter-static docs — [CITED: svelte.dev/docs/kit/adapter-static, 2026-05-29]
- Vite build + base config — [CITED: vite.dev/guide/build, 2026-05-29]
- HN robots.txt — [VERIFIED: news.ycombinator.com/robots.txt — 30s crawl-delay, no global Disallow]
- Wikipedia article verified to exist — [VERIFIED: WebFetch en.wikipedia.org/wiki/Comparison_of_programming_languages_(syntax)]

### Secondary (MEDIUM confidence)
- DDG robots.txt analysis — [VERIFIED: WebFetch html.duckduckgo.com/robots.txt — `Disallow: /`]
- Brave robots.txt analysis — [VERIFIED: WebFetch search.brave.com/robots.txt — `Disallow: /search`]
- Wikipedia HTML body size estimate (~400-500KB) — WebFetch best-effort estimate, within budget by 10×

### Tertiary (LOW confidence — flagged for in-wave verification)
- Wikipedia article has infobox claim — WebFetch suggested no traditional infobox; planner verifies during capture
- Wikipedia table sort JS captures into static mirror — needs in-wave smoke test
- Mac Mini Node 22 availability — needs runtime check at start of framework-variant wave
- `npx sv create` exact SvelteKit init syntax — confirm against svelte.dev on author-day (current command at time of research)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tooling is well-established; Context7 + official docs verified for each framework
- Architecture: HIGH — patterns are existing v1.0 carry-forward; one new wave-shape (framework-variant build pipeline) documented
- Pitfalls: HIGH on technical pitfalls; MEDIUM on legal-posture pitfall (DDG/Brave robots.txt)
- Synthetic fixture authoring: HIGH — vanilla JS patterns are well-known, no novel tech
- Framework-variant builds: MEDIUM — depends on canonical scaffold scripts succeeding on Mac Mini; fallback documented
- Size budget: HIGH — comfortable headroom on every fixture category

**Research date:** 2026-05-29
**Valid until:** 2026-06-29 (30 days — framework versions evolve rapidly, especially Next.js)
