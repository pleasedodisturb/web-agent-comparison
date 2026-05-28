# Lightpanda — Stage Walk Transcript (2026-05-26)

**MCP under test:** `lightpanda`
**Snapshot server:** `http://127.0.0.1:8765`
**Mock identity:** Jane Testworth (`fixtures/mock_data.json`)
**Run mode:** 8-stage locked script per `scoring/rubric.md`

## Tool inventory used
- `mcp__lightpanda__goto` — primary navigation
- `mcp__lightpanda__links` — directory-listing drill-down
- `mcp__lightpanda__markdown` — primary content read
- `mcp__lightpanda__structuredData` — JSON-LD/OG/meta extraction
- `mcp__lightpanda__semantic_tree` — DOM tree probe (Ashby diagnostic)
- `Read` (mock_data.json) and `Write` (artifacts)

No non-allowlisted tool was reached for. No WebFetch. Allow-list contract preserved.

## Per-stage result

| Stage | Outcome | Artifact | Notes |
|---|---|---|---|
| S1 | PASS | `stage_s1.yml` | Greenhouse SSR HTML extracted cleanly — title, locations, comp band, full apply-form schema, OG/meta tags. |
| S2 | FAIL (expected) | `stage_s2.FAILED` + `stage_s2.diagnostic.yml` | Ashby React SPA. Lightpanda's Zig JS engine does not execute the React bundle; `<title>Jobs</title>` is the entire reachable content. This IS the load-bearing finding for lightpanda. |
| S3 | PASS | `stage_s3.md` | Platform identification unambiguous from URL pattern (numeric vs UUID), asset CDN (`*.greenhouse.io` vs `cdn.ashbyprd.com`), and SSR-vs-CSR posture. |
| S4 | N/A | `stage_s4.NA` | Read-only treatment per prompt rule. Lightpanda has fill/click/selectOption tools but no screenshot/upload — and the prompt explicitly classifies it read-only, so the sentinel cascade applies. |
| S5 | N/A | `stage_s5.NA` | Cascades from S4 NA. No batch form-fill primitive. |
| S6 | N/A | `stage_s6.NA` | No file_upload primitive. Resume PDF upload not achievable. |
| S7 | N/A | `stage_s7.NA` | React Select combobox; selectOption would not bind even if attempted. |
| S8 | N/A | `stage_s8.NA` | No screenshot primitive. |

## Failure modes & caveats

1. **JS rendering gap is the headline finding.** Lightpanda is a Zig-based read-only browser with no React execution. Ashby (and any other SPA-rendered ATS such as Workday-Cloud) returns an empty shell. Greenhouse, Lever-SSR, and any ATS that ships server-rendered HTML are fine.
2. **Tool-surface ceiling.** Lightpanda exposes interaction primitives (`fill`, `click`, `selectOption`, `setChecked`, `press`, `hover`, `eval`) but no `screenshot` and no `file_upload`. S6 and S8 are physically impossible on this MCP. The prompt-locked read-only classification rolls up the cascade for S4-S7 as well.
3. **Fixture data note.** Greenhouse snapshot has been scrubbed: mentor names and program codename replaced with the literal `"Jane Testworth"` placeholder. This is fixture state, not lightpanda output — it propagates verbatim into the OG/meta block lightpanda extracts.
4. **Cold-start / latency:** not measured this pass (the harness records timing externally via stream-json). Subjectively all `goto` calls returned promptly (<1s observed); no timeouts.
5. **Stability:** identical S1/S2/S3 verdicts across PASS1, PASS2, and this run — three consecutive runs converging on the same outcome.

## Compliance
- Allow-list: `mcp__lightpanda__*`, `Read`, `Write`, `Bash` — only these were called. ✅
- No `WebFetch` fallback attempted. ✅
- One artifact per stage. ✅
- Failure mode documented, not masked. ✅
