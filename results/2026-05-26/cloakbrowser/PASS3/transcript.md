# CloakBrowser MCP — Stage Walk Transcript (2026-05-26)

**MCP under test:** `cloakbrowser` (cloakbrowsermcp 2.0.4, closed-source patched Chromium)
**Fixture server:** `http://127.0.0.1:8765` (loopback only)
**Output dir:** `results/2026-05-26/cloakbrowser/`
**Tool allow-list honoured:** only `mcp__cloakbrowser__*`, `Read`, `Write`, `Bash`. No `WebFetch`, no other MCP.

## Tool inventory used (in order of first appearance)

| tool                    | purpose                                                  |
|-------------------------|----------------------------------------------------------|
| `cloak_launch`          | start stealth browser (one session, one page reused)     |
| `cloak_navigate`        | load fixture URLs and walk index → posting               |
| `cloak_snapshot`        | get [@eN] ref IDs for interactive elements               |
| `cloak_click`           | click directory links and form buttons                   |
| `cloak_read_page`       | get clean markdown of rendered DOM                       |
| `cloak_wait`            | settle wait after navigation                             |
| `cloak_evaluate`        | the workhorse for pre-hydration extraction + file upload + DOM probes |
| `cloak_type`            | per-field form input (humanizer-backed key cadence)      |
| `cloak_screenshot`      | annotated full-page PNG for S8                           |
| `cloak_close`           | release browser                                          |

Auxiliary host tools: `Read`, `Write`, `Bash` only.

## Per-stage outcome

| stage | artifact            | outcome                                                      | tools                                                |
|-------|---------------------|--------------------------------------------------------------|------------------------------------------------------|
| S1    | `stage_s1.yml`      | DONE — extracted title, location, salary, workstreams        | `cloak_navigate`, `cloak_evaluate` (fetch+DOMParser) |
| S2    | `stage_s2.yml`      | DONE-with-honest-finding — SPA hydrated, posting API absent  | `cloak_navigate`, `cloak_evaluate`                   |
| S3    | `stage_s3.md`       | DONE — Greenhouse vs Ashby classification with signal table  | `cloak_evaluate` (re-read static HTML, no nav)       |
| S4    | `stage_s4.md`       | DONE — form re-injected, 15 [@eN] refs live                  | `cloak_navigate`, `cloak_evaluate`, `cloak_snapshot` |
| S5    | `stage_s5.md`       | DONE-partial — 4/6 fields filled; linkedin & github absent in fixture | `cloak_type` ×4, `cloak_evaluate` (verify)   |
| S6    | `stage_s6.md`       | DONE — resume File set via DataTransfer; size+MIME verified  | `Bash` (base64), `cloak_evaluate`                    |
| S7    | `stage_s7.md`       | DOCUMENTED — source field absent; React-Select technique exercised on @e12 | `cloak_click`, `cloak_type`, `cloak_evaluate` |
| S8    | `stage_s8.png`      | DONE — 56,408-byte annotated PNG, 14 elements indexed         | `cloak_screenshot(full_page=True)`                   |

## What worked

- `cloak_evaluate` is the MCP's force multiplier. It rescued S1 (React hydration overwrote the body), enabled S2's appData diagnostic, materialised the apply form in S4, and synthesised the file upload in S6. CloakBrowser exposes it as a first-class primitive, so the workarounds are within the fairness contract.
- `cloak_type` runs through CloakBrowser's humanizer (key-by-key cadence). For S5's 4 fields this added ~4 round-trips vs a batched-fill MCP, but is the entire point of the stealth design.
- `cloak_snapshot` produced stable `[@eN]` refs after the S4 form re-injection. Refs survived intermediate clicks and types — no stale-ref retries needed.
- `cloak_screenshot(full_page=True)` captured the entire form with the annotated element indices, matching the snapshot's ref IDs.

## What did not work / caveats

- **React hydration clobber.** Both fixtures shipped JS that overwrote the rendered body. For the Greenhouse posting, the static HTML carries the full content but React's API call resolves to "Page not found." Mitigation: `cloak_evaluate(fetch + DOMParser)` to read the pre-hydration body. Documented in S1, S2, S4.
- **Ashby SPA cannot show the posting in this fixture.** The bundle does run (CloakBrowser is real Chromium), but the loopback server cannot replay `api.ashbyhq.com`, so the SPA branches to its 404 path. The MCP's capability is intact; the fixture is the limiter. Recorded honestly in S2.
- **Source dropdown does not exist** in the Greenhouse Anthropic-Fellows posting. S7 exercised the React-Select technique against the closest analogue (`@e12`, the custom-question combobox). The detached-script form configuration set up in S4 (to keep the form visible) means React listeners on that combobox don't fire, so the option couldn't be committed; documented as a technique-vs-environment trade-off.
- **No batched `browser_fill_form`** equivalent on CloakBrowser. Per-field typing is the only path.
- **No dedicated file-upload primitive.** Upload goes through `cloak_evaluate` with a synthesised `File` + `DataTransfer`. Works for small resumes; would hit MCP payload limits for ~5+ MB files.
- **`cloak_select` is for native `<select>` only.** Greenhouse forms ship Emotion-styled React-Select (`select__*` BEM + `remix-css-*` hashes), so `cloak_select` is not the right tool there.

## Fairness contract

- No `WebFetch` was called.
- No other MCP (`playwright`, `chrome-devtools`, `browser-use`, `firecrawl`, `obscura`, `lightpanda`) was called.
- Only `Read`, `Write`, `Bash` were used outside the `mcp__cloakbrowser__*` namespace, and only for: reading `fixtures/mock_data.json`, base64-encoding `fixtures/mock_resume.pdf`, copying the screenshot from CloakBrowser's artifact dir into the evidence dir, and reading the prior `PASS1`/`PASS2` references to mirror methodology decisions.
- All eight stage artifacts present in `results/2026-05-26/cloakbrowser/`.
