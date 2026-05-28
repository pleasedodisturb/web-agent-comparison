# chrome-devtools MCP — 2026-05-26 stage walk transcript

**MCP under test:** `chrome-devtools` (chrome-devtools-mcp v1.0.1, GA'd 2026-05-18)
**Driver:** Claude Code, Opus 4.7 (1M context)
**Fixture server:** `http://127.0.0.1:8765` (loopback)
**Output dir:** `results/2026-05-26/chrome-devtools/`
**Allow-list honored:** `mcp__chrome-devtools__*`, `Read`, `Write`, `Bash` only. No `WebFetch`, no other MCPs.

## Tool inventory used

| Tool | Stages | Notes |
|---|---|---|
| `mcp__chrome-devtools__new_page` | S1 | Opened the Greenhouse directory listing |
| `mcp__chrome-devtools__navigate_page` | S1, S2, S8 | URL navigation |
| `mcp__chrome-devtools__take_snapshot` | S1, S2 | A11y-tree snapshot with uid refs |
| `mcp__chrome-devtools__evaluate_script` | S1, S2 | Critical — used to bypass SPA hydration and read SSR HTML via fetch + DOMParser |
| `mcp__chrome-devtools__take_screenshot` | S8 (diagnostic) | Full-page PNG |

Tools available but unused (would have been used had stages reached form-fill): `click`, `fill`, `fill_form`, `upload_file`, `press_key`, `type_text`, `select_page`, `wait_for`.

## Stage-by-stage outcome

| Stage | Verdict | Artifact | One-line summary |
|---|---|---|---|
| S1 | PASS | `stage_s1.yml` | Extracted full Greenhouse posting (title, company, location, salary band, workstreams, requirements) via fetch + DOMParser fallback after SPA hydrated to "Page not found". |
| S2 | PASS-with-caveat | `stage_s2.yml` | Ashby SPA rendered to its own empty-state ("Page not found / The page you requested was not found"); `window.__appData.posting === null` confirms the snapshot lacks the runtime API payload. This IS the expected SPA-rendering surface per `ashby_2026-05-22/PROVENANCE.md`. |
| S3 | PASS | `stage_s3.md` | Discriminated Greenhouse (integer job ID, ~85KB SSR HTML) from Ashby (UUID job ID, ~6KB shell + `__appData` bootstrap). |
| S4 | FAILED | `stage_s4.FAILED` | Apply form not in the snapshot fixture (only the job-posting page was captured), and the SSR Apply button was destroyed when the SPA hydrated to "Page not found". Environment-gated, not MCP-gated. |
| S5 | FAILED | `stage_s5.FAILED` | Cascaded from S4 — no form to fill. `fill_form` was the intended batch tool. |
| S6 | FAILED | `stage_s6.FAILED` | Cascaded from S4 — no file input. `upload_file` was the intended tool. |
| S7 | FAILED | `stage_s7.FAILED` | Cascaded from S4 — no React-Select source dropdown to interact with. |
| S8 | FAILED | `stage_s8.FAILED` + `stage_s8_greenhouse_post_hydration.png` | No filled form to screenshot; instead captured a diagnostic full-page PNG of the actual post-hydration "Page not found" state. |

## Key MCP-specific findings

1. **`evaluate_script` is load-bearing.** chrome-devtools' a11y-tree snapshot reflects the post-hydration DOM, which on this Greenhouse fixture is just the SPA's "Page not found" fallback. Recovering the SSR job data required `evaluate_script` running `fetch(location.href)` + `DOMParser` inside the same page context. An MCP without a JS-eval primitive could not have recovered S1's data from this fixture.
2. **The a11y-snapshot uid pipeline (`take_snapshot` → `click`/`fill` by uid) never got exercised** because the form stages were environment-blocked. This is the headline interaction primitive of chrome-devtools-mcp v1.0; the bench did not get to score it on this run.
3. **No console / network instrumentation was used**, though available (`list_console_messages`, `list_network_requests`). Those would have been informative on S2 (would have shown the failed Ashby API fetch) but were not strictly required for stage completion.
4. **GA-version warning:** chrome-devtools-mcp 0.26 → 1.0.0 → 1.0.1 shipped four days before this run (2026-05-18). Re-snapshotting the tool inventory before scoring (per the v1.0 GA caveat in PROJECT.md §1) was not done in-flight; the inventory present here matches what was loaded via ToolSearch and what 1.0.1 advertises. No schema drift observed.

## Fairness contract

- No tool outside `mcp__chrome-devtools__*` / `Read` / `Write` / `Bash` was invoked.
- `Bash` was used only for fixture inspection (`curl` against loopback, `ls`/`find` against the local fixtures dir, `mkdir` for the output dir) — never to bypass the MCP's browser surface.
- Mock identity (`fixtures/mock_data.json`) was loaded but never used downstream because S5+ were blocked.
- Mock resume (`fixtures/mock_resume.pdf`) was not opened.

## Caveats for downstream scoring

- S4-S8 are FAILED, not NA. chrome-devtools is interaction-capable; the failure is purely environmental (snapshot scope did not include an apply form). Scoring should distinguish "MCP lacks the primitive" (NA) from "snapshot lacked the surface" (FAILED) when this run is composed with read-only MCPs (lightpanda, firecrawl) whose S4 will be NA for a different reason.
- S2's "Page not found" result is the **correct** rendered output for a JS-capable MCP against this Ashby snapshot — it should NOT be scored equivalently to lightpanda's expected un-hydrated-shell output, even though the user-facing content length is similar.
