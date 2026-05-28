# Lightpanda S1–S8 Stage Walk — 2026-05-26

MCP under test: **lightpanda** (against snapshot fixtures at
`http://127.0.0.1:8765`).

Tool surface restricted to `mcp__lightpanda__*`, `Read`, `Write`, `Bash`.
No WebFetch, no other MCP. Each stage's evidence file is the canonical
artifact; this transcript is the human view.

## Outcome at a glance

| Stage | Verdict | Artifact | Tool(s) used |
|-------|---------|----------|--------------|
| S1 — Greenhouse extract | ✅ PASS | `stage_s1.yml` | `goto`, `markdown`, `structuredData`, `links` |
| S2 — Ashby SPA extract | ❌ EXPECTED FAILURE | `stage_s2.yml` | `goto`, `markdown`, `structuredData`, `semantic_tree`, `evaluate` |
| S3 — Platform detection | ✅ PASS | `stage_s3.md` | (reasoning over S1/S2 outputs, no MCP calls) |
| S4 — Navigate apply form | ✅ PASS (same-page) | `stage_s4.yml` | `goto`, `detectForms`, `interactiveElements`, `nodeDetails` ×3 |
| S5 — Fill form | ✅ PARTIAL PASS | `stage_s5.yml` | `fill` ×4 + `evaluate` for verify |
| S6 — Upload resume | ⚪ NA | `stage_s6.NA` | (no upload primitive in MCP) |
| S7 — Source dropdown | ❌ FAILED | `stage_s7.md` | `selectOption` (rejected), `fill`, `press`, `evaluate` |
| S8 — Screenshot | ⚪ NA | `stage_s8.NA` | (no screenshot primitive in MCP) |

## Per-stage notes

### S1 — Greenhouse extract
Static Greenhouse HTML renders flawlessly. `markdown` returned the full job
post including title, location, salary band, requirements, apply link,
and inline form fields. `structuredData` recovered OpenGraph metadata.
Title: "Jane Testworth Program" (fixture is name-scrubbed; that's a snapshot
property, not an MCP property). Apply URL: `https://bit.ly/afpsafety`.

### S2 — Ashby SPA extract
Empty markdown, body-text length 55 chars, only `<head>` survived
(`title="Jobs"`, Ashby theme color `#483fad`). `#root` div present with 2
children but no descendants the agent can read. Lightpanda's Zig JS engine
does not execute React hydration. This IS the benchmark finding — Lightpanda
is unsuitable for client-rendered SPAs.

### S3 — Platform detection
URL pattern (numeric `gh_jid` vs Ashby UUID), Greenhouse footer
(`Powered by greenhouse.com`), Ashby theme color + cdn.ashbyprd.com favicon,
inline server-rendered form vs. empty SSR shell — four independent signals,
all pointing the same way. High confidence.

### S4 — Navigate apply form
No navigation needed: the Greenhouse fixture renders its apply form INLINE
on the job page. Mapped backendNodeIds for: first_name (7), last_name (8),
email (9), country combobox (10), phone (11), resume file input (12),
source/Constellation combobox (13), required-state mirror (14).

**Fixture vs. spec drift:** the stage walk lists linkedin & github in S5;
this Anthropic Fellows snapshot has no such inputs. Documented as fixture
property, not Lightpanda failure.

### S5 — Fill form
`fill` succeeded on all 4 plain text/tel inputs in 4 sequential tool calls.
Lightpanda has no batch fill primitive (Playwright's `browser_fill_form`
equivalent is absent). Verified via JS read-back:
```
first_name = "Jane"
last_name  = "Testworth"
email      = "jane.testworth@example.com"
phone      = "+1 555 867 5309"
```
linkedin/github skipped because the fields do not exist in this fixture.

### S6 — Upload resume → NA
No `upload_file` / `setInputFiles` primitive in lightpanda tool surface.
JS workaround attempted (`document.getElementById('resume').value = ...`)
was correctly blocked by browser security: `InvalidStateError`.

### S7 — Source dropdown → FAILED
React Select v5 widget. Three techniques attempted:
1. `selectOption` → rejected at MCP layer (not a native `<select>`).
2. `fill("Job board")` + `press("Enter")` → input string set, but
   `aria-expanded=false`, placeholder still "Select...", `data-value=""`,
   no `.select__menu` ever mounted.
3. DOM probe for any pre-rendered option list → empty. The static snapshot
   was frozen pre-interaction; even in a real browser the options array
   only materializes after `.select__control` is clicked. Lightpanda's
   engine cannot execute the click handler that mounts the menu.

Skipped a fake `input.value =` JS workaround that would set the visible text
without committing react-select state — that would produce a false-positive
green check.

### S8 — Screenshot → NA
Lightpanda's tool surface has 19 tools, zero of which can produce a
screenshot. Its browsercore engine has no paint buffer to capture from.

## Caveats / honesty notes

- Anthropic Fellows fixture is name-scrubbed (every name → "Jane Testworth"),
  which doesn't affect benchmarking but does make the extracted job
  description read oddly.
- The Greenhouse fixture lacks linkedin/github fields — stage walk spec
  assumes a richer form than this snapshot provides. S5 score should be
  read as "4/4 fields the fixture exposes," not "4/6 spec fields."
- Lightpanda's identity / version mismatch (mentioned in PROJECT.md
  intel: header reports 0.3.0, MCP handshake reports 0.1.0) was not
  re-verified during this run; not relevant to the stage outcomes.

## Tools NOT used

Did not reach for: WebFetch, any other MCP (`mcp__playwright__*`,
`mcp__chrome-devtools__*`, etc.), or any non-allow-listed tool. Fairness
contract preserved.

## Summary

Lightpanda is a competent **static-HTML / SSR** browser MCP and a clean
failure on **JS-rendered SPAs** and **interactive React widgets**. Of the
8 stages: 3 clean passes (S1, S3, S4), 1 partial pass (S5), 1 expected SPA
failure (S2), 1 react-select failure (S7), 2 NA on missing tool primitives
(S6 upload, S8 screenshot). This matches the rubric's prediction for the
engine class — Zig-based DOM-only browser tooling.
