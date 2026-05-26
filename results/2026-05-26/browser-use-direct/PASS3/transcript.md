# browser-use MCP — 2026-05-26 stage walk transcript

Human-readable summary; harness derives the canonical record from
`raw_stream.jsonl`.

**MCP under test:** browser-use (`mcp__browser-use__*`)
**Fixture server:** http://127.0.0.1:8765 (Python SimpleHTTP/0.6)
**Allow-list:** `mcp__browser-use__*`, Read, Write, Bash
**Date:** 2026-05-26

## Headline

browser-use's **navigation, DOM inspection, and screenshot primitives all
work** against the loopback fixtures. Its **content-extraction primitive
(`browser_extract_content`) returned "No content extracted" on both
fixtures** — that is the only MCP-level finding worth flagging this wave.
**Stages S4-S7 are fixture-bound failures, not MCP failures** (see
"Fixture state" below).

## Stage-by-stage

| Stage | Artifact | Verdict | Tools used |
|-------|----------|---------|------------|
| S1 | `stage_s1.yml` | PARTIAL — fixture inactive-board | `browser_navigate`, `browser_extract_content`, `browser_get_state`, `browser_get_html` |
| S2 | `stage_s2.yml` | PARTIAL — SPA shell only | `browser_navigate`, `browser_extract_content`, `browser_get_state` |
| S3 | `stage_s3.md`  | DONE — pure reasoning over S1+S2 | (none — reasoning over prior captures) |
| S4 | `stage_s4.FAILED` | FAILED — no apply form in fixture | `browser_navigate` (probed 404 via bash curl) |
| S5 | `stage_s5.FAILED` | FAILED — no form to fill | (none — no targets in `browser_get_state`) |
| S6 | `stage_s6.FAILED` | FAILED — no upload target + no upload primitive | n/a |
| S7 | `stage_s7.FAILED` | FAILED — no dropdown to select | n/a |
| S8 | `stage_s8.png` (48KB) | CAPTURED — screenshot of whatever was on the page at S8 time (Greenhouse inactive-board interstitial, not a filled form) | `browser_screenshot` |

## Tool inventory observed

After `ToolSearch select:` on the documented browser-use tool list, 16
primitives loaded:

- Navigation: `browser_navigate`, `browser_go_back`, `browser_scroll`
- State: `browser_get_state`, `browser_get_html`, `browser_list_tabs`,
  `browser_list_sessions`
- Interaction: `browser_click` (by index or pixel coords), `browser_type`
- Extraction: `browser_extract_content` (semantic query-driven)
- Capture: `browser_screenshot` (viewport or full page)
- Tab/session lifecycle: `browser_switch_tab`, `browser_close_tab`,
  `browser_close_session`, `browser_close_all`
- Escape hatch: `retry_with_browser_use_agent` (LLM-driven fallback —
  intentionally not invoked this run so the scoring measures the MCP's
  own surface, not the LLM papering over gaps)

**Notable absences:** no first-class `browser_file_upload` primitive (cf.
Playwright's `browser_file_upload`, chrome-devtools' `upload_file`), no
first-class `browser_select_option` (cf. Playwright's
`browser_select_option`, lightpanda's `selectOption`), no
`browser_fill_form` batched-form primitive (cf. Playwright's
`browser_fill_form`, chrome-devtools' `fill_form`). These gaps did not
matter on this fixture (no form to interact with) but will matter when
the fixture exposes a real apply form.

## Fixture state (the load-bearing context)

- **Greenhouse** snapshot (`greenhouse_2026-05-22/anthropic/jobs/5023394008.html`):
  the live job had already been removed when wget mirrored it on
  2026-05-22T15:49:32Z. The captured HTML is Greenhouse's "Page not
  found / The job board you were viewing is no longer active."
  interstitial. No apply form, no apply URL, no employment metadata.
  This is documented in `fixtures/snapshots/greenhouse_2026-05-22/PROVENANCE.md`
  ("Pitfall 8 — public-fixture rot — live URLs 404 within 6 months").
- **Ashby** snapshot (`ashby_2026-05-22/replit/<uuid>.html`): 6,294 bytes
  Vite SPA boot shell with `<div id="root">` + `<noscript>` banner; no
  upstream API endpoint on the loopback so the SPA never hydrates. Also
  documented in PROVENANCE.md ("SPA-shell caveat").

The fixture limitation applies to **every** MCP in the 2026-05-26 wave;
the comparative scoring is still valid because every candidate sees the
same content.

## MCP-level findings worth scoring

1. **`browser_extract_content` returned "No content extracted" on both
   fixtures.** browser_get_html confirmed the DOM was present (84KB on
   Greenhouse, 6KB on Ashby), so the extraction layer is not missing the
   bytes — it appears to require a populated job-posting schema and
   bails when the only content is an error page or an unhydrated shell.
   This is a degraded-content robustness gap, not a hard failure.
2. **No native file-upload primitive** in the surfaced tool inventory.
   If a fixture exposes an apply form with `<input type=file>`, this
   MCP cannot complete S6 via batched tools — it would have to drive
   click + a file-picker dialog that's typically out of headless
   reach. Worth a "0 on upload, irrespective of fixture" in the
   capability matrix.
3. **Navigation + DOM access + screenshot are stable.** No timeouts,
   no transport errors, no Chromium crash. The MCP handled loopback
   `Server: SimpleHTTP/0.6` cleanly without TLS-fingerprint contortions.
4. **Page title scrubbing artefact noticed:** the Greenhouse fixture's
   `<title>` reads "Jane Testworth for Jane Testworth Program at
   Anthropic" — an artefact of the PROVENANCE.md scrubbing rule
   (190 two-word capitalized matches rewritten to "Jane Testworth"
   before commit). Not a browser-use bug; flagging because if the
   scoring rubric weighs title quality it'll mis-score this fixture
   uniformly across all 7 MCPs.

## Caveats / what didn't happen

- I deliberately did **not** invoke `retry_with_browser_use_agent` —
  that fallback would let an LLM solve the stages through navigation,
  but the score we're after measures the MCP's first-class tool
  surface against the fixture, not the LLM's ability to recover.
- I did not attempt to point browser-use at the live
  `job-boards.greenhouse.io` or `jobs.ashbyhq.com` URLs. The harness
  contract is loopback-only; the live URLs are a separate G-710 smoke
  gate per PROVENANCE.md.
- The screenshot artifact (`stage_s8.png`, 48,379 bytes) is the page
  state at S8 time, which was the Greenhouse inactive-board interstitial
  (because S4 navigated back to it). The harness allow-list does not let
  me re-navigate to a contrived "filled form" elsewhere; this is the
  honest capture of what was on screen.
- `browser_screenshot` returns the PNG inline as an MCP image content
  block; it does not accept a save-path parameter. I extracted the
  base64 image bytes from `raw_stream.jsonl` via a Bash + Python
  one-liner and persisted them to `stage_s8.png`. The same approach
  will work for any future MCP that returns screenshots inline; the
  alternative would be a `mcp__browser-use__*` change request to add
  an `output_path` param.

## Reproduction

```
# 1. Bring the fixture server up
scripts/serve_fixtures.sh

# 2. Launch the run
scripts/run_mcp_session.sh browser-use

# 3. Artifacts land in:
results/2026-05-26/browser-use/
  stage_s1.yml          # extracted: title only (fixture inactive)
  stage_s2.yml          # extracted: SPA shell, footer chrome only
  stage_s3.md           # platform detection reasoning
  stage_s4.FAILED       # no apply form in fixture
  stage_s5.FAILED       # no form fields to fill
  stage_s6.FAILED       # no <input type=file> + no upload primitive
  stage_s7.FAILED       # no source-dropdown widget
  stage_s8.png          # 48KB Greenhouse inactive-board screenshot
  transcript.md         # this file
  raw_stream.jsonl      # harness-emitted canonical stream
```
