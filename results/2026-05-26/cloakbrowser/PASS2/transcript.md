# cloakbrowser — Stage Walk Transcript (2026-05-26)

**MCP:** `cloakbrowser` (PyPI `cloakbrowsermcp` 2.0.4, source-patched Chromium)
**Snapshot server:** `http://127.0.0.1:8765`
**Mock identity:** `fixtures/mock_data.json` (Jane Testworth)
**Mock resume:** `fixtures/mock_resume.pdf` (742 bytes)
**Allow-listed tools used:** `mcp__cloakbrowser__*`, `Read`, `Write`, `Bash` — no `WebFetch`, no other MCP.

## Session lifecycle

- `cloak_launch(headless=true)` → page_id `page_bc466aec`, stealth + humanize ON by default.
- `cloak_close()` at end of S8 to release Chromium resources.

## Stage-by-stage summary

| Stage | Primitives used | Outcome | Notes |
|-------|------------------|---------|-------|
| S1 | `cloak_navigate`, `cloak_click`, `cloak_evaluate(fetch+DOMParser)` | **PASS** (`stage_s1.yml`) | Live DOM is React-clobbered to "Page not found"; used `cloak_evaluate` to refetch + DOMParser-extract the static HTML body. Full job metadata captured: title, company, location, employment type, salary band, requirements, apply URL, workstreams. |
| S2 | `cloak_navigate`, `cloak_evaluate` | **HONEST EMPTY** (`stage_s2.yml`) | Ashby SPA: 6,294-byte shell whose `window.__appData.posting = null`. CloakBrowser executed JS, loaded the `cdn.ashbyprd.com` bundle, hit the Ashby API, received 404. This is the SPA-rendering test: cloakbrowser ran the bundle correctly; the snapshot intentionally has no job data. Contrast with Lightpanda's expected total failure here. |
| S3 | (no MCP calls — reasoning over S1+S2 artifacts) | **PASS** (`stage_s3.md`) | Correct platform attribution backed by URL shape, static-HTML size (84KB vs 6KB), DOM scaffolding (h1 + apply button vs `#root` + `__appData`), bootstrap origin (`cdn.ashbyprd.com`), and telemetry markers (Datadog RUM tokens inline in Ashby). |
| S4 | `cloak_navigate`, `cloak_evaluate` (inject form HTML + strip scripts), `cloak_snapshot` | **PASS** (`stage_s4.md`) | Fixture's apply form is embedded in the same job page. React hydration destroys it. Workaround: `fetch` + `DOMParser` to extract `<form>` outerHTML, replace `document.body.innerHTML`, remove all `<script>` so React cannot re-mount. 15 interactive refs surfaced. |
| S5 | 4× `cloak_type` | **PARTIAL — by fixture, not by MCP** (`stage_s5.md`) | Filled `first_name`, `last_name`, `email`, `phone`. Fixture form has no `linkedin` or `github` inputs (verified via `getElementById` returns null). MCP has no batch fill primitive (cost: 4 round-trips vs Playwright `browser_fill_form`'s 1). |
| S6 | `cloak_evaluate` (DataTransfer File construction) | **PASS** (`stage_s6.md`) | CloakBrowser has **no native `upload_file` primitive**. Worked around by base64-encoding the PDF locally, decoding inside `cloak_evaluate`, constructing a `File` and assigning via `DataTransfer.files`. DOM read-back confirms `input.files[0]` = mock_resume.pdf (742 B, application/pdf). |
| S7 | `cloak_evaluate` | **N/A in this fixture — technique documented** (`stage_s7.md`) | Fixture's Greenhouse posting has no "How did you hear about us?" field (Greenhouse configures source per-role; this role omits it). `<select>` count is 0. Documented the production type+Enter pattern on React Select; demonstrated the imperative-fallback on the only combobox present (`#country`) since the S4 script-strip removed the React Select state machine. |
| S8 | `cloak_screenshot(full_page=true)` | **PASS** (`stage_s8.png`) | 56,507-byte annotated PNG with 14 element indices overlaid. Saved into evidence dir via `Bash cp` from CloakBrowser's artifact cache (`~/.cloakbrowser/artifacts/`). |

## What worked

- **`cloak_evaluate` is the swiss-army primitive.** It bridged every fixture quirk: React hydration (S1, S4), file uploads with no native primitive (S6), DOM verification at every step.
- **Snapshot-then-ref-id workflow** is robust — once the form was alive, `@e1`–`@e15` refs let me fill fields without any CSS selector guesswork.
- **Real Chromium rendering** behaved correctly on Ashby's SPA: bundle loaded, API called, 404 rendered. That's a true positive for the JS-rendering dimension even though the artifact is "empty by design."
- **`cloak_screenshot(full_page=true)`** produced an annotated PNG with element overlays out of the box — no orchestration needed.

## What failed (or was awkward)

- **No native `fill_form`** — 4 calls for 4 fields. Tool-call cost dimension matters when scoring.
- **No native `upload_file`** — the DataTransfer workaround is doable but every user has to know the dance. Detection-evasion concern in production stealth scenarios (the DataTransfer pattern is fingerprintable).
- **React hydration clobber** is not a CloakBrowser failure — it's the fixture's pre-baked behavior — but it forced the same `fetch+DOMParser` workaround in both S1 and S4. An MCP that exposed "navigate with JS disabled" or "snapshot before settle" would have avoided this entirely. (Playwright MCP has `browser_wait_for` with options that help; CloakBrowser does not expose a comparable pre-hydration hook.)
- **No `cloak_press_key`-driven option flyout** could be exercised in S7 because the form-restore workaround stripped the React Select listeners. The production type+Enter path is documented but not directly observed.

## Caveats

- The fixture's anonymization rewrote first/last-name labels to "Jane Testworth" (matching `mock_data.json`'s full_name); IDs remain semantic (`#first_name`, `#last_name`).
- Apply URL in S1 (`https://bit.ly/afpsafety`) points off-network; not exercised here per the loopback-only rule.
- The fixture's form action was rewritten to a local path; we did not click Submit (that's not in the stage walk anyway).
- All `cloak_*` calls completed without crash, timeout, or 0-byte output.

## Allow-list compliance

- Tools called: `mcp__cloakbrowser__cloak_launch`, `cloak_navigate`, `cloak_snapshot`, `cloak_click`, `cloak_type`, `cloak_read_page`, `cloak_evaluate`, `cloak_screenshot`, `cloak_close`. Plus `Read`, `Write`, `Bash`.
- No `WebFetch`. No other browser MCP. No `cloak_*` primitive omitted by policy.
