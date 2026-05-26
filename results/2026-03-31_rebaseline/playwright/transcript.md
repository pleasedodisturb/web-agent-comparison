# Playwright MCP — 2026-03-31 Re-Baseline Transcript

Reconstructed from the published narrative in `results/2026-03-31_run.md`
(Section: "1. Playwright MCP — 9.07/10 (Winner)"). The 2026-03 wave did not
capture a raw transcript; this is the text the published report used to
describe the run.

## Per-stage summary

| Stage | Outcome | Tools used | Artifact |
|---|---|---|---|
| S1 | PASS (33KB snapshot, all fields present) | `browser_navigate`, `browser_snapshot` | `stage_s1.yml` |
| S2 | PASS (Ashby React SPA rendered fully, 10.8KB snapshot) | `browser_navigate`, `browser_snapshot` | `stage_s2.yml` |
| S3 | PASS (platform identifiable from snapshot — Greenhouse branding, URL structure) | analysis only | `stage_s3.md` |
| S4 | PASS (clicked Apply via ref, form appeared) | `browser_click` | `stage_s4.yml` |
| S5 | PASS (browser_fill_form filled 6 fields in ONE tool call) | `browser_fill_form` | `stage_s5.md` |
| S6 | PASS (file chooser triggered, mock_resume.pdf uploaded) | `browser_file_upload` | `stage_s6.md` |
| S7 | PARTIAL (React Select combobox not native, needed browser_run_code fallback) | `browser_run_code` | `stage_s7.md` |
| S8 | PASS (full-page screenshot captured, 1.5MB PNG) | `browser_take_screenshot` | `stage_s8.png` |

## Key strengths

- `browser_fill_form` is a game-changer — fills multiple fields in ONE tool
  call (6 fields at once vs 4+ commands for others).
- Richest tool surface: evaluate, network intercept, drag, file upload,
  console messages.
- Warm browser means fast navigation (~2-3s per page).
- Accessibility snapshots are structured and token-efficient.
- Full JS/React rendering — Ashby SPA rendered perfectly.

## Key weaknesses

- React Select comboboxes (common in Greenhouse) aren't native `<select>`
  elements — `browser_select_option` fails, requiring `browser_run_code`
  fallback.
- No auth/cookies — can't access gated content (LinkedIn profiles, internal
  tools).
- Chromium process memory overhead (~200-400MB).

## Verdict

The clear winner for application automation. `browser_fill_form` alone
justifies using it over alternatives. Only use something else when you need
auth (BrowserMCP) or just need to read a page (WebFetch).

(Source: `results/2026-03-31_run.md`, lines 78-94.)
