# Phase 6: Fixture authoring (S9-S26) - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 18 new fixture directories + 1 shared data file + 11+ PROVENANCE.md files + 4 modify-targets
**Analogs found:** All new files have direct v1.0 analogs; 4 modify-targets are extensions in place

This phase has the cleanest possible analog landscape: every file Phase 6 creates is a structural twin of `fixtures/snapshots/greenhouse_2026-05-22/` or `fixtures/snapshots/ashby_2026-05-22/`, and every file it modifies is an in-place extension of an existing v1.0 artifact. Phase 6 does not invent new patterns — it duplicates the v1.0 snapshot pattern 18 times with category-specific source-acquisition variations (synthetic vs. wget-captured).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `fixtures/snapshots/s09_ecommerce_pdp/` (dir) | fixture (synthetic) | file-I/O | `fixtures/snapshots/greenhouse_2026-05-22/` | structural twin (dir layout) — synthetic content, not captured |
| `fixtures/snapshots/s09_ecommerce_pdp/index.html` | fixture asset (synthetic HTML) | file-I/O | `fixtures/snapshots/greenhouse_2026-05-22/anthropic/jobs/5023394008.html` | role-match (HTML served from snapshot tree); synthetic so no wget provenance |
| `fixtures/snapshots/s09_ecommerce_pdp/cart.html` | fixture asset (synthetic HTML) | file-I/O | same as above | role-match |
| `fixtures/snapshots/s09_ecommerce_pdp/verify-cart.html` | fixture asset (synthetic HTML) | file-I/O | same as above | role-match |
| `fixtures/snapshots/s12_serp_ddg/` | fixture (captured) | file-I/O | `fixtures/snapshots/greenhouse_2026-05-22/` | exact (captured via wget, same dir + provenance pattern) |
| `fixtures/snapshots/s12_serp_brave/` | fixture (captured) | file-I/O | `fixtures/snapshots/greenhouse_2026-05-22/` | exact |
| `fixtures/snapshots/s13_15_21_22_wikipedia/` | fixture (captured, multi-stage shared) | file-I/O | `fixtures/snapshots/greenhouse_2026-05-22/` | exact |
| `fixtures/snapshots/s16_hn_pagination/` | fixture (captured, 5 pages) | file-I/O | `fixtures/snapshots/greenhouse_2026-05-22/` | exact (multi-page extension — see Pattern Assignment 4) |
| `fixtures/snapshots/s17_18_auth_walled/` | fixture (synthetic, multi-page + cookies) | file-I/O + state | `fixtures/snapshots/greenhouse_2026-05-22/` | structural twin; novel cookie behavior not in v1.0 |
| `fixtures/snapshots/s19_20_complex_form/` | fixture (synthetic, interactive HTML+JS) | file-I/O + client-side state | `fixtures/snapshots/greenhouse_2026-05-22/` | structural twin |
| `fixtures/snapshots/s23_framework_variant_nextjs/` | fixture (synthetic, framework build artifact) | file-I/O | `fixtures/snapshots/greenhouse_2026-05-22/` | structural twin |
| `fixtures/snapshots/s24_framework_variant_sveltekit/` | fixture (synthetic, framework build artifact) | file-I/O | same | structural twin |
| `fixtures/snapshots/s25_framework_variant_vue/` | fixture (synthetic, framework build artifact) | file-I/O | same | structural twin |
| `fixtures/snapshots/s26_framework_variant_vanilla/` | fixture (synthetic, hand-authored static) | file-I/O | same | structural twin |
| `fixtures/framework-variants/data.json` | shared data source | file-I/O (read-only by builders) | `fixtures/mock_data.json` | exact (JSON data fixture committed at repo scope, consumed by multiple downstream artifacts) |
| `fixtures/snapshots/*/PROVENANCE.md` (×10+) | fixture metadata | doc | `fixtures/snapshots/greenhouse_2026-05-22/PROVENANCE.md` | exact for captured; extended schema for synthetic (see Shared Pattern 1) |
| `fixtures/snapshots/*/.sha256` (×10+) | integrity manifest | file-I/O | `fixtures/snapshots/greenhouse_2026-05-22/.sha256` | exact |
| `bench/scrub_artifacts.py` (MODIFY) | utility / safety gate | batch transform | itself (extend allow-list / TEXT_EXTS only) | self-extension |
| `prompts/stage_walk.md` (MODIFY) | harness prompt template | doc / config | itself (S1-S8 cells locked; append S9-S26 below) | self-extension |
| `scripts/serve_fixtures.sh` (MODIFY, optional) | orchestration | request-response | itself (parameter tweaks only if subdir depth requires) | self-extension |
| `.planning/REQUIREMENTS.md` (MODIFY) | requirements doc | doc | itself (mark FAIRNESS-11 deferred) | self-extension |

## Pattern Assignments

### 1. `fixtures/snapshots/s12_serp_ddg/`, `s12_serp_brave/`, `s13_15_21_22_wikipedia/`, `s16_hn_pagination/` (captured fixtures)

**Analog:** `fixtures/snapshots/greenhouse_2026-05-22/` + `scripts/snapshot_fixtures.sh`

**On-disk layout pattern** (verified via `find`):
```
fixtures/snapshots/greenhouse_2026-05-22/
├── .sha256                         # SHA256 over served-content tree
├── PROVENANCE.md                   # metadata (source, date, scrub log)
└── anthropic/jobs/5023394008.html  # the actual captured page (wget mirrors source path structure)
```

**Capture command pattern** (from `scripts/snapshot_fixtures.sh` per `01-03-snapshot-fixtures-PLAN.md` Task 1):
```bash
wget --mirror \
     --convert-links \
     --adjust-extension \
     --page-requisites \
     --no-parent \
     --execute robots=off \
     --user-agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36' \
     --directory-prefix="${OUTDIR}" \
     "${URL}"
```

**PII scrub pattern** (sed post-pass — `01-03-snapshot-fixtures-PLAN.md` Task 1):
```bash
find "${OUTDIR}" -type f \( -name '*.html' -o -name '*.htm' -o -name '*.js' -o -name '*.json' \) -print0 \
  | xargs -0 sed -i.bak -E -e 's/[A-Z][a-z]+ [A-Z][a-z]+/Jane Testworth/g'
find "${OUTDIR}" -name '*.bak' -delete
```

**SHA256 directory hash** (`.sha256` file content from `greenhouse_2026-05-22/.sha256`):
```
450ad57fa370c5f1d847855e294503c27b9446dcf9d83cb9d8d133e6b6a616e1  greenhouse_2026-05-22
```
Computed via `tar -cf - --sort=name "${OUTDIR}" | shasum -a 256 | awk '{print $1}' > "${OUTDIR}/.sha256"` (Task 1.5 in 01-03 PLAN).

**Apply to:** All four captured fixtures. The Wikipedia + HN dirs will be multi-page (HN: 5 pages at `?p=1..5`, Wikipedia: one article + assets), but the layout convention is identical — wget mirrors the URL path under the snapshot root, so HN will produce e.g. `s16_hn_pagination/news.ycombinator.com/index.html`, `s16_hn_pagination/news.ycombinator.com/index.html?p=2`, etc., or a flattened `page-1.html`..`page-5.html` if the planner post-processes for readability. Either is acceptable; document the choice in PROVENANCE.

---

### 2. `fixtures/snapshots/s09_ecommerce_pdp/`, `s17_18_auth_walled/`, `s19_20_complex_form/`, `s23-s26_framework_variants/` (synthetic fixtures)

**Analog:** `fixtures/snapshots/greenhouse_2026-05-22/` (same directory layout) BUT no `scripts/snapshot_fixtures.sh` invocation — content is hand-authored or build-tool-produced.

**Directory layout pattern** (inherits from greenhouse_2026-05-22):
```
fixtures/snapshots/s09_ecommerce_pdp/
├── .sha256                   # computed after content is final
├── PROVENANCE.md             # metadata, BUT with "Capture tool: hand-authored" or "Capture tool: next build && next export (v15.x)"
├── index.html                # the PDP
├── cart.html                 # the cart state after AJAX add
├── verify-cart.html          # the post-mutation extraction target
└── assets/                   # if any CSS/JS/images (size-budget conscious)
    └── ...
```

**PROVENANCE.md template for synthetic** (extends the captured template — see Shared Pattern 1):
- `Source URL:` replaced with `Source: hand-authored synthetic fixture` or `Source: scaffolded via "npx create-next-app@15 --typescript --tailwind --no-src-dir" then stripped`
- `Capture tool:` replaced with `Authoring tool: hand-authored` or `Authoring tool: next@15.2.1 + next build && next export`
- New field `Rendering archetype:` per FAIRNESS-08 (e.g., `static-HTML`, `SPA-Next.js-static-export`, `SPA-SvelteKit-static-export`, `SPA-Vue3-Vite-build`, `static-hand-authored`)
- New field `Agent task tag:` per DESIGN-03 (e.g., `read-only-extract`, `interact-mutate-verify`, `auth-walled-read`)
- `License:` field — all synthetic fixtures are `License: project license (this repo)`. Captured Wikipedia is `License: CC BY-SA 4.0`. HN is `License: public-domain-ish (titles + links only; no comment bodies captured)`. DDG/Brave SERP captures get `License: SERP page metadata; queries are non-PII generic-informational`.

**SHA256 computation** is identical to captured fixtures (`tar -cf - --sort=name "${OUTDIR}" | shasum -a 256`).

**Auth-walled cookie mechanism** (D-09; no v1.0 analog for the JS pattern itself — author inline):
```html
<!-- s17_18_auth_walled/login.html submit handler — must be self-contained inline JS, no external deps -->
<script>
document.querySelector('form').addEventListener('submit', function(e) {
  e.preventDefault();
  var u = document.querySelector('input[name=username]').value.trim();
  var p = document.querySelector('input[name=password]').value.trim();
  if (!u || !p) {
    document.querySelector('.error').textContent = 'Username and password are required.';
    return;
  }
  document.cookie = 'session=fake-token-xyz; path=/';
  window.location.href = './dashboard.html';
});
</script>
```
The dashboard.html reads `document.cookie`, expects `session=fake-token-xyz`, and if absent redirects to login (so the auth gate is testable end-to-end without a real server).

---

### 3. `fixtures/framework-variants/data.json`

**Analog:** `fixtures/mock_data.json` (committed at `fixtures/mock_data.json`, ~322 bytes, used by S5 form-fill via `Read fixtures/mock_data.json`).

**Pattern from `fixtures/mock_data.json`** (existing 322-byte JSON, mock applicant identity for S5):
- Lives at `fixtures/` root (NOT under `fixtures/snapshots/` — it's a harness asset, not a per-fixture asset)
- Read by harness/stage-prompt via `Read fixtures/mock_data.json` (see `prompts/stage_walk.md` line 35: "Mock identity: read `fixtures/mock_data.json`")
- Survives the scrub via the default allow-list ("Jane Testworth" only — no PII)

**Apply to `data.json`:**
- Place at `fixtures/framework-variants/data.json` (NOT under `fixtures/snapshots/` — it's a build-time input, not a served fixture)
- Schema per D-12: array of 10 product objects with `name`, `price`, `short_description`, `image_alt_text`
- Each of the 4 framework builds (S23-S26) reads it at build time and bakes the 10 records into the static HTML output
- Product names should be deliberately fictional (no real brands) per D-01 ("Open Source Outpost", "Mechanical Keyboard Y50", etc.) so the scrub doesn't false-positive — two-word capitalized fictional product names will trip `NAME_REGEX` and need to be added to the scrub allow-list (see Pattern Assignment 5)

---

### 4. Multi-page snapshot for `s16_hn_pagination/` (5 pages)

**Analog:** `fixtures/snapshots/greenhouse_2026-05-22/anthropic/jobs/5023394008.html` (single-page case) — multi-page is a v1.0 extension, not a re-pattern.

**Capture approach** — two viable structures, planner picks:

**Option A: Mirror URL paths** (most faithful to wget output, what `--mirror` produces by default):
```
fixtures/snapshots/s16_hn_pagination/
├── PROVENANCE.md
├── .sha256
└── news.ycombinator.com/
    ├── index.html              # ?p=1 (or default)
    ├── index.html?p=2          # wget --adjust-extension may rename to news.ycombinator.com@p=2.html
    ├── ...
    └── (linked CSS/images via --page-requisites)
```

**Option B: Flatten + rewrite** (better for loopback serving — `?p=N` querystrings may not be cleanly servable by `http.server`):
```
fixtures/snapshots/s16_hn_pagination/
├── PROVENANCE.md
├── .sha256
├── page-1.html  # post-processed: "next" link rewritten to "./page-2.html"
├── page-2.html
├── page-3.html
├── page-4.html
└── page-5.html
```

**Recommendation:** Option B (flatten + rewrite). `python3 -m http.server` does not strip querystrings before file lookup, so `?p=2` would 404. Document the post-processing in PROVENANCE.md ("links rewritten from `?p=N` to `./page-N.html` for loopback serving — original querystring pagination preserved as comments in source HTML").

**Apply to:** s16 only. The 5-page HN capture is the only multi-page captured fixture in Phase 6; Wikipedia is single-article (one captured page); SERPs are single-query (one page each).

---

### 5. `bench/scrub_artifacts.py` (MODIFY — extend allow-list per REPRO-10)

**Analog:** itself — this is a pure additive extension, no structural change.

**Pattern to preserve** (from `bench/scrub_artifacts.py` lines 48-58):
```python
# Default allow-list. The mock applicant for all Phase 1 fixtures.
DEFAULT_ALLOW: frozenset[str] = frozenset({"Jane Testworth"})

# File extensions scanned as plain text.
TEXT_EXTS: frozenset[str] = frozenset({
    ".md", ".txt", ".yml", ".yaml", ".jsonl", ".json", ".log",
    ".csv", ".html", ".htm", ".xml",
})
```

**Existing extension mechanism** (lines 191-198, 200-205) — `--allow <file>` already accepts additional allow-list files at runtime:
```python
parser.add_argument(
    "--allow",
    type=Path,
    action="append",
    default=[],
    help="Extra allow-list file (one name per line). May be passed multiple times.",
)
# ...
allow: set[str] = set(DEFAULT_ALLOW)
for extra_path in args.allow:
    if not extra_path.exists():
        print(f"ERROR: allow-list file not found: {extra_path}", file=sys.stderr)
        return 1
    allow.update(_load_allow_extension(extra_path))
```

**Allow-list file format** (loader at lines 130-138):
```python
def _load_allow_extension(path: Path) -> set[str]:
    """Load an allow-list extension file (one name per line, # comments)."""
    extra: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        extra.add(line)
    return extra
```

**Two viable extension paths for Phase 6:**

1. **Preferred: per-fixture `.scrub_allow.txt` files.** Add a small `.scrub_allow.txt` next to each fixture's `PROVENANCE.md` listing fictional two-word product names that legitimately need to survive (e.g., `Mechanical Keyboard`, `Outpost Mug`). Invoke the scrub with `--allow fixtures/snapshots/s09_ecommerce_pdp/.scrub_allow.txt` (the harness already supports `action="append"` for repeated `--allow`). No code change to `scrub_artifacts.py`, just call-site change.

2. **If invocation expansion isn't workable: extend `DEFAULT_ALLOW`.** Append synthetic-fixture survivors (product names, the SaaS dashboard's UI strings like "Recent Activity", "Welcome Back") directly to `DEFAULT_ALLOW`. Less granular but simpler. The CONTEXT.md `code_context` section explicitly describes this as "`bench/scrub_artifacts.py` allow-list pattern (v1.0): `.scrub_allow.txt` per fixture dir lists pre-approved survivors" — so v1.0's intended pattern was per-dir allow files even though the v1.0 fixtures didn't need any beyond "Jane Testworth".

**Apply to:** Option 1 (per-fixture `.scrub_allow.txt`) is the v1.0-intended pattern per CONTEXT.md and requires no `scrub_artifacts.py` source change. Pick this unless a downstream call-site complication forces Option 2.

**Possible TEXT_EXTS extension:** if synthetic framework-variant builds produce `.css`, `.svg`, `.mjs` artifacts the planner wants scanned, extend `TEXT_EXTS` accordingly. Default v1.0 set already covers `.html`, `.json`, `.js` (note: `.js` is NOT in v1.0 `TEXT_EXTS` — it's listed in the snapshot script's sed pass at line 81 of `01-03-snapshot-fixtures-PLAN.md` but not in the Python scanner). If framework builds emit JS bundles with potentially-leaky strings, add `.js`, `.mjs`, `.cjs` to `TEXT_EXTS`.

---

### 6. `prompts/stage_walk.md` (MODIFY — append S9-S26 cells per CONTEXT.md "stage-walk prompt extension")

**Analog:** itself — Phase 6 explicitly may NOT touch S1-S8 cells (sacrosanct).

**Locked S1-S8 cell pattern to extend** (from `prompts/stage_walk.md`):

**Header pattern** (lines 26-36 — keep unchanged, treat as the "preamble" everything below inherits):
```markdown
# Web-Agent MCP Stage Walk — `${MCP}`

You are driving the **${MCP}** MCP against snapshot fixtures of Greenhouse +
Ashby job postings. Your job is to execute stages S1 through S8 using ONLY
the tools `mcp__${MCP}__*`, `Read`, `Write`, and `Bash`. Save evidence to
`${OUT_DIR}/`.

**Snapshot server (loopback only):** `${SNAPSHOT_BASE_URL}`
**Output directory:** `${OUT_DIR}`
**Mock identity:** read `fixtures/mock_data.json` (Jane Testworth).
**Mock resume:** `fixtures/mock_resume.pdf`.
```

Phase 6 must NOT alter this header. v1.1 will need to update "stages S1 through S8" to "stages S1 through S26" — that is the ONE permitted edit to the locked region (CONTEXT.md says "do not modify S1-S8 cells", and that header is the preamble, not a cell; planner should clarify but the safe read is "edit the range bound only, do not change any cell body").

**Hard-rules block** (lines 38-55 — keep unchanged; it applies equally to S9-S26):
```markdown
**Hard rules:**

- Use ONLY `mcp__${MCP}__*`, `Read`, `Write`, `Bash`. Never reach for
  `WebFetch` or a different MCP — the harness allow-list will refuse, and
  the run will be scored `tool-bug`.
- One artifact per stage, written to `${OUT_DIR}/stage_sN.<ext>` where
  `<ext>` is whatever the MCP natively produces (`.yml`, `.md`, `.txt`,
  `.json`, or `.png` for screenshots). The harness accepts any of those.
- If a stage CANNOT be completed with this MCP's surface (e.g. a read-only
  MCP cannot fill a form), write `${OUT_DIR}/stage_sN.NA` (one line stating
  why) and CONTINUE to the next applicable stage.
- If a stage was attempted and failed (crashed, timed out, returned 0
  bytes), write `${OUT_DIR}/stage_sN.FAILED` (one line stating the failure
  mode) and CONTINUE.
- At the end, write `${OUT_DIR}/transcript.md` summarising the tools you
  used per stage and any failure modes you hit. The harness will also
  derive a transcript from the stream-json; yours is the human view.
```

**Per-stage cell pattern** (S1 from lines 58-68, S2 from lines 70-80, etc. — append S9..S26 in this same shape):
```markdown
## SN — [Stage description]

**Target:** `${SNAPSHOT_BASE_URL}/[fixture-dir]/`

[1-3 sentences describing what to extract / interact / verify]

Write [output description] to `${OUT_DIR}/stage_sN.yml` (or `.md` / `.txt`
/ `.json` — pick the format the MCP natively returns).

[If applicable: "N/A surface" callout — which MCPs are expected to be N/A
on this stage and why, per CONTEXT.md code_context note about lightpanda +
Firecrawl on S23-S25 SPA variants.]
```

**STOP block** (lines 148-154 — keep at the absolute bottom; move it after the new S26 cell when appending):
```markdown
**STOP.** Write `${OUT_DIR}/transcript.md` summarising which tools you
used per stage, what worked, what failed, and any caveats. Do NOT call any
non-`mcp__${MCP}__` tools except `Read`, `Write`, `Bash`. Do NOT reach for
`WebFetch`. If a stage cannot be completed with the MCP under test, write
`${OUT_DIR}/stage_sN.FAILED` with a one-line reason and move on.
```

**Apply to:** Append 18 new `## SN` cells between the existing S8 cell (ending around line 146) and the STOP block (lines 148-154). New cells use the exact pattern of S1-S8 cells (target URL → instruction → output spec → optional N/A callout). Per CONTEXT.md "Document the expected N/A surface per stage in the prompt cells" — for S23-S25 SPA variants, explicitly list `lightpanda`, `firecrawl` as expected N/A; for the auth-walled cookie-based S17-S18, document expected N/A for read-only MCPs that can't set cookies.

---

### 7. `scripts/serve_fixtures.sh` (MODIFY — only if subdir depth requires)

**Analog:** itself — the v1.0 server already mounts `fixtures/snapshots/` as the root via `--directory "$ROOT"` (line 106 of `serve_fixtures.sh`). New fixture dirs land under that root automatically. **No source change should be needed** unless one of the synthetic fixtures uses absolute paths (`/assets/style.css` instead of `./assets/style.css`) or expects a deeper mount point.

**Pattern to preserve** (lines 104-107):
```bash
nohup "$venv_python" -m http.server "$PORT" \
    --bind "$BIND" \
    --directory "$ROOT" \
    > "$LOGFILE" 2>&1 &
```

`$ROOT` resolves to `$REPO_ROOT/fixtures/snapshots` (line 37). All new s09..s26 dirs land under it.

**Apply to:** No edit unless a synthetic fixture's HTML uses absolute (root-relative) asset paths. If it does, the cleaner fix is to make the fixture use relative paths (`./assets/...` or `assets/...`) rather than reconfigure the server — this preserves the loopback-server pattern intact. The CONTEXT.md `code_context` says "may need tweaks to handle new fixture-dir tree depth (e.g., multi-page HN snapshot subdirs)" but on review `http.server --directory <root>` already handles arbitrary depth; the only realistic tweak is if the planner wants per-fixture subroute behavior (e.g., a `/login` redirect helper) which `http.server` does NOT support — in which case the right answer is fixture-side relative links, not server-side rewriting.

---

### 8. `.planning/REQUIREMENTS.md` (MODIFY — mark FAIRNESS-11 deferred per D-15)

**Analog:** Existing `## Deferred (out of scope for v1.1)` section pattern in REQUIREMENTS.md (the planner can grep for the existing "Deferred" or "Future" section header to find the established convention). Phase 6 only adds one bullet under that section.

**Apply to:** Single one-line edit. Per CONTEXT.md `decisions` D-15: "The deferred line in REQUIREMENTS.md serves as the v1.2 anchor."

Suggested text (planner adjusts to match the file's existing bullet style):
```markdown
- **FAIRNESS-11 (i18n: non-English + non-ASCII fixtures)** — deferred to v1.2.
  Rationale: v1.1 already adds 18 stages; 2 additional i18n fixtures (Japanese
  Wikipedia + Arabic news) add ~1.5× authoring effort on encoding verification
  + RTL layout review. The v1.1 published report includes an explicit
  "not measured — see v1.2" callout. (Phase 6 D-15.)
```

## Shared Patterns

### Shared Pattern 1: PROVENANCE.md schema (extended for v1.1)

**Source:** `fixtures/snapshots/greenhouse_2026-05-22/PROVENANCE.md` + `fixtures/snapshots/ashby_2026-05-22/PROVENANCE.md`
**Apply to:** EVERY new fixture directory under `fixtures/snapshots/s09_*..s26_*/`.

**v1.0 base schema** (verbatim from `greenhouse_2026-05-22/PROVENANCE.md`):
```markdown
# Snapshot provenance — greenhouse_2026-05-22

- **Source URL:** https://job-boards.greenhouse.io/anthropic/jobs/5023394008
- **Capture date:** 2026-05-22 (UTC)
- **Capture timestamp:** 2026-05-22T15:49:32Z
- **Capture tool:** GNU Wget 1.25.0 built on darwin25.2.0.
- **Captured by:** scripts/snapshot_fixtures.sh
- **Scrubbing applied:**
  - Two-word capitalized strings replaced with `Jane Testworth` using the
    same `NAME_REGEX` as `bench/scrub_artifacts.py`, iterated to convergence.
  - Count of pre-scrub non-allow-listed matches: 190
  - Allow-list deltas: none
- **Directory SHA256:** 450ad57fa370c5f1d847855e294503c27b9446dcf9d83cb9d8d133e6b6a616e1  greenhouse_2026-05-22
- **Files captured:** 1
- **Total bytes (served content):** 84609
- **Primary HTML:** `anthropic/jobs/5023394008.html` (84609 bytes)
- **Reason for capture:** Pitfall 8 (public-fixture rot) — live URLs 404 within 6 months. This snapshot is the test target; live-URL drift is a separate daily-smoke gate (deferred to G-710).
- **Drift detection:** ONE live-URL smoke test per platform — `make smoke-live` (diagnostic only, not part of the scored bench flow).
```

**SPA-shell caveat extension** (from `ashby_2026-05-22/PROVENANCE.md` lines 20-22) — pattern for when wget produces a degraded snapshot:
```markdown
## SPA-shell caveat

**SPA-shell detected:** primary HTML contains a `<div id="root">` mount point and a `<noscript>You need to enable JavaScript</noscript>` banner, indicating no server-rendered listing content. wget --mirror cannot capture the runtime-fetched API responses that hydrate this SPA; the harness will see the shell (and the loading-spinner CSS) only.
```

**v1.1 schema extensions** (Phase 6 adds, per CONTEXT.md `code_context` "v1.1 extends with agent-task tag (DESIGN-03) + rendering archetype (FAIRNESS-08)"):
```markdown
- **Rendering archetype:** [static-HTML | SPA-Next.js-static-export | SPA-SvelteKit-static-export | SPA-Vue3-Vite-build | static-hand-authored | captured-SERP-static | captured-Wikipedia-static | captured-HN-static | SPA-shell-only]   ← FAIRNESS-08
- **Agent task tag:** [read-only-extract | read-only-multi-page | interact-mutate-verify | auth-walled-read | form-fill-validate | sort-then-extract | framework-variant-A/B]   ← DESIGN-03
- **License:** [project license (this repo) | CC BY-SA 4.0 | public-domain-ish (titles + links only) | SERP-page-metadata-non-PII]
- **Stages served:** [list of S9..S26 stages this fixture is the target for, e.g. "S13, S14, S15, S21, S22" for the shared Wikipedia capture]
```

**For SYNTHETIC fixtures, also change:**
- `Source URL:` → `Source: hand-authored synthetic fixture for ${STAGE-RANGE}` or `Source: scaffolded via ${SCAFFOLD_CMD}, stripped to product-list page, built via ${BUILD_CMD}`
- `Capture tool:` → `Authoring tool: hand-authored` or `Authoring tool: next@15.x + next build && next export`
- `Captured by:` → `Authored by:` (omit if not script-driven)
- `Scrubbing applied:` block is still required even for synthetic — scrub_artifacts.py still runs, and any product-name false-positives are documented under `Allow-list deltas:` (cross-reference to `.scrub_allow.txt`)
- `SPA-shell caveat` section is REPLACED by `## JS-rendering archetype` (for S23-S26 framework variants) documenting which framework, which build command, which bundle artifacts were produced

### Shared Pattern 2: Scrub-runs-clean invariant

**Source:** `bench/scrub_artifacts.py` exit code 0 contract (lines 142-215, especially 211-215).
**Apply to:** Every new fixture dir before commit. Per CONTEXT.md Stop condition #5: "`bench/scrub_artifacts.py` exits 0 on the full set."

Invocation pattern (from `01-03-snapshot-fixtures-PLAN.md` Task 4):
```bash
uv run python -m bench.scrub_artifacts fixtures/snapshots/
```
Or per-fixture with allow-list extension:
```bash
uv run python -m bench.scrub_artifacts fixtures/snapshots/s09_ecommerce_pdp/ \
    --allow fixtures/snapshots/s09_ecommerce_pdp/.scrub_allow.txt
```

### Shared Pattern 3: Sacrosanct triad untouched

**Source:** `bench/wave_close_check.py` (lines 50-60, `WAVE2_BASELINE` constant, and the `audit_*` functions).
**Apply to:** Phase 6 must NOT modify any of:
- `scoring/score.py`
- `scoring/rubric.md`
- `.mcp.json`

At every plan boundary Phase 6 runs `python3 -m bench.wave_close_check` and confirms `all_pass=True`. If the audit reports `terminal_craft_commits > 0`, `candidate_count != 7`, `rubric_columns != 8`, or `no_new_mcps == False`, Phase 6 has accidentally drifted scope and must roll back.

CONTEXT.md `canonical_refs` § Sacrosanct invariants states this explicitly; the audit is the enforcement mechanism. Wave-close-check usage (from its CLI block at lines 432-496):
```bash
python3 -m bench.wave_close_check \
    --mcp-json .mcp.json \
    --rubric scoring/rubric.md \
    --out .planning/phases/06-fixture-authoring-s9-s26/PRE_PLAN_AUDIT.md
```
(or however the planner wants to name boundary-audit evidence files; the audit is read-only and idempotent).

### Shared Pattern 4: Size-budget discipline

**Source:** CONTEXT.md Stop condition #4: "`du -sh fixtures/snapshots/` ≤ 50 MB".
**Apply to:** Every fixture dir contributes to the 50 MB cap. v1.0 footprint is tiny (greenhouse_2026-05-22 = 84,609 bytes; ashby_2026-05-22 = 6,294 bytes — both verifiable from their PROVENANCE.md `Total bytes` lines). Phase 6 has ~50 MB headroom but the framework-variant builds (S23-S25) are the realistic budget risk because `next build` / Vite output can easily exceed 1 MB per variant when unstripped. Stripping must happen post-build:
- Remove source-maps (`*.map`).
- Remove framework runtime polyfills not required for a single static product-list page.
- Inline minimal CSS; remove framework-default CSS resets if not used.

Hard rule: every fixture dir's `du -sh` is documented in its PROVENANCE.md under `Total bytes (served content)` (mirrors v1.0).

### Shared Pattern 5: Loopback-only addressing in prompt cells

**Source:** `prompts/stage_walk.md` lines 33-34 + each S1/S2 cell's `**Target:**` line.
**Apply to:** Every new S9-S26 cell uses `${SNAPSHOT_BASE_URL}/<fixture-dir>/` as its target — never a live URL, never `localhost` (use the literal placeholder `${SNAPSHOT_BASE_URL}` which `scripts/run_mcp_session.sh` expands to `http://127.0.0.1:8765`). Per CONTEXT.md `code_context` "Reusable Assets" #1: "Python http.server fixture-serving pattern (v1.0 Phase 1 D-13): `python3 -m http.server` bound to `127.0.0.1:8765`, root at `fixtures/snapshots/`. Continues unchanged."

## No Analog Found

All Phase 6 work has direct v1.0 analogs because Phase 6 is explicitly a duplication-and-extension phase, not an invention phase. Two micro-patterns lack a v1.0 analog but are local-novel (handle inline in the planner, no codebase reference needed):

| Sub-pattern | Stage(s) | Reason no analog | Mitigation |
|---|---|---|---|
| Cookie-based fake auth flow (login.html sets `document.cookie`; dashboard.html reads it) | S17-S18 (D-09) | v1.0 fixtures are pure read targets; no stateful interaction beyond Greenhouse form fill. | Author inline JS per the snippet in Pattern Assignment 2. Document in PROVENANCE under `Agent task tag: auth-walled-read`. |
| Multi-framework build artifact set (Next.js/SvelteKit/Vue/vanilla rendering the same `data.json`) | S23-S26 (D-13) | v1.0 has no SPA build-tooling pipeline; the Ashby SPA is captured-not-built. | Build externally (scaffold + strip + `next build && next export` etc.), commit only the build artifacts. PROVENANCE field `Source: scaffolded via ${SCAFFOLD_CMD}, built via ${BUILD_CMD}` documents the recipe so a third party can reproduce without us shipping the scaffolds. |

## Metadata

**Analog search scope:** `fixtures/snapshots/`, `bench/`, `scripts/`, `prompts/`, `.planning/milestones/v1.0-phases/01-harness-foundation/`
**Files scanned:** 9 (CONTEXT.md ×2, the v1.0 snapshot-fixtures PLAN, both v1.0 PROVENANCE.md files, scrub_artifacts.py, stage_walk.md, serve_fixtures.sh, wave_close_check.py) + 3 ls/find passes for directory layout verification.
**Pattern extraction date:** 2026-05-29
