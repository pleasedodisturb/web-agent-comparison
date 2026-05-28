# browser-use MCP — stage walk transcript (2026-05-26)

**MCP under test:** `browser-use` (PyPI `browser-use`, target version 0.12.7 per intel)
**Snapshot server:** `http://127.0.0.1:8765`
**Evidence dir:** `results/2026-05-26/browser-use/`
**Allow-list:** `mcp__browser-use__*`, `Read`, `Write`, `Bash`. No off-allow-list tools used (no WebFetch, no other MCP).

## Tools available (loaded via ToolSearch)

`browser_navigate`, `browser_extract_content`, `browser_get_state`, `browser_get_html`,
`browser_click`, `browser_type`, `browser_screenshot`, `browser_scroll`, `browser_go_back`,
`browser_list_sessions`, `browser_list_tabs`, `browser_switch_tab`, `browser_close_session`,
`browser_close_tab`, `browser_close_all`, `retry_with_browser_use_agent`.

Surface notes:
- **No JS-eval / run_code / evaluate_script primitive.** This is the load-bearing gap
  for this fixture set.
- **No file-upload primitive.** No equivalent of Playwright's `browser_file_upload` or
  chrome-devtools' `upload_file`.
- **No batch form-fill primitive.** Each field requires one `browser_type` call (Playwright's
  `browser_fill_form` style is unavailable here).
- `retry_with_browser_use_agent` is an LLM-driven escape hatch; NOT used in this run so
  the scoring reflects primitive-surface capability only.

## Stage outcomes

| Stage | Outcome | Artifact | Tools used |
|---|---|---|---|
| S1 — Greenhouse JD extract | FAILED (capability-correct) | `stage_s1.md` | `browser_navigate`, `browser_click`, `browser_extract_content`, `browser_get_state`, `browser_get_html` |
| S2 — Ashby JD extract | FAILED (capability-correct) | `stage_s2.md` | same set as S1 |
| S3 — Platform detection | DONE (works from chrome alone) | `stage_s3.md` | reasoning over S1+S2 outputs, no MCP tools |
| S4 — Navigate to apply form | FAILED | `stage_s4.FAILED` | `browser_navigate`, `browser_get_state` |
| S5 — Fill form | N/A | `stage_s5.NA` | — |
| S6 — Upload resume | N/A | `stage_s6.NA` | — |
| S7 — Source dropdown | N/A | `stage_s7.NA` | — |
| S8 — Screenshot | N/A | `stage_s8.NA` | — |

## What failed and why

Both fixture pages (Greenhouse + Ashby) are static captures of React SPA shells. When
browser-use loads them, the React bundle hydrates and, finding no live backend, replaces
the entire body with the in-app "Page not found" / "job board is no longer active"
fallback. The fully-rendered DOM contains only header chrome (logo SVG) + the 404
message.

Post-hydration:
- `browser_extract_content` returns "No content extracted" on both fixtures.
- `browser_get_state.interactive_elements` collapses to 2 (Greenhouse: span+svg) or
  ~8 (Ashby: footer policy links + "Powered by Ashby").
- The apply button, form inputs, and resume upload control all live in the SSR'd HTML
  body but are unreachable through the live DOM after React mount.

chrome-devtools (in `../chrome-devtools/`) bypassed this by fetching the raw HTML via
`evaluate_script`, stripping `<script>` tags, then `document.write()`-ing the cleaned HTML
back so the SSR'd form rendered without the React 404 override. **browser-use cannot do
this** — its tool surface has no JS-eval primitive. lightpanda also failed for the
opposite reason (no JS rendering at all, but at least it can read the SSR'd HTML).

## What worked

- S1 + S2 fully exercised browser-use's exploration loop (navigate → state → click →
  state → click → state → extract). Page metadata (`<title>` tag) survived hydration and
  was reachable via `browser_get_state`. The extraction-failure-mode itself is a clear,
  documented finding.
- S3's platform-detection task is answerable from chrome alone (URL shape, CSS class
  conventions, footer attribution) — no primitive limit hit.
- Token usage on this run is the read-only navigation cost only; no LLM-driven retries.

## Capability score implications (for the rubric)

| Rubric dimension | browser-use result on this fixture |
|---|---|
| Greenhouse SPA extraction | structural fail — shared with all JS-rendering MCPs against this offline snapshot, but exposes browser-use specifically because it has no eval escape hatch |
| Ashby SPA extraction | same |
| Platform identification | full |
| Form navigation | fail — no JS-eval primitive to bypass hydration |
| Form fill batch | fail — no batch primitive; would have required N type calls per field even on a working form |
| File upload | fail — no primitive exposed |
| React-Select source dropdown | N/A — fixture has no source field anyway |
| Screenshot of filled form | primitive exists (full-page supported) but precondition unmet |

## Caveats

- This run did NOT attempt `retry_with_browser_use_agent`. That fallback would consume
  external LLM credits and run a non-deterministic agent loop — and the structural
  hydration-to-404 issue is fixture-side, so an LLM agent would face the same wall.
  Documenting the gap is more useful than spending tokens proving it.
- Network: every navigation was loopback to 127.0.0.1:8765. No external traffic.
- No file artifacts written outside `results/2026-05-26/browser-use/`.
