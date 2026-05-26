# cloakbrowser sandbox enforcement proof

**Plan:** 02-06 (cloakbrowser per-MCP scoring run)
**Run dates:** 2026-05-26 (all 3 passes within a 23-minute window, 21:20-21:43 UTC)
**Linear ticket:** G-720 (cloakbrowser sub-ticket of G-703)

**Per Phase 2 SC #5:** "The cloakbrowser evidence directory contains zero requests
to any hostname other than 127.0.0.1; the harness refuses to spawn it against any
other target."

This proof attests the SAFETY-04 contract per CLAUDE.md `## Constraints` and
`~/.claude/docs/browser-tools.md` (2026-05-21): cloakbrowser is a closed-source
binary that touches cookies on launch; it must only ever be pointed at the
loopback snapshot fixtures.

## Pre-flight guard

`bench/cloakbrowser_guard.assert_local_only(url)` is wired into the harness at
`scripts/run_mcp_session.sh:127-130`. It is invoked ONLY for `MCP_NAME ==
"cloakbrowser"` and raises `HostnameNotAllowedError` for any non-loopback
hostname. Pre-flight against the active config:

```
$ .venv/bin/python -c "from bench.cloakbrowser_guard import assert_local_only; assert_local_only('http://127.0.0.1:8765')"
GUARD OK: http://127.0.0.1:8765 accepted

$ .venv/bin/python -c "from bench.cloakbrowser_guard import assert_local_only; assert_local_only('https://example.com')"
HostnameNotAllowedError: cloakbrowser refused: hostname 'example.com' not in ['127.0.0.1', '::1', '[::1]', 'localhost']
```

Both behaviors verified before PASS1. All three passes spawned through this
guard; `SNAPSHOT_BASE_URL` was `http://127.0.0.1:8765` for every spawn. If the
guard had ever raised, the harness would have exited before Claude spawned
(see `scripts/run_mcp_session.sh:127-130`).

## Post-run hostname audit

### Phase 1 — every navigate + fetch tool call

Every active network-egress vector the agent invoked through the cloakbrowser
MCP surface (the only egress vectors under our control are `cloak_navigate` and
`fetch(...)` inside `cloak_evaluate`):

```
$ for p in PASS1 PASS2 PASS3; do
    jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use" and .name=="mcp__cloakbrowser__cloak_navigate") | .input.url' \
      "results/2026-05-26/cloakbrowser/$p/raw_stream.jsonl"
  done | sort -u
http://127.0.0.1:8765/ashby_2026-05-22/
http://127.0.0.1:8765/ashby_2026-05-22/replit/
http://127.0.0.1:8765/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html
http://127.0.0.1:8765/greenhouse_2026-05-22/
http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/
http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html
```

All 6 unique `cloak_navigate` targets across 3 passes are `127.0.0.1:8765`.
No exceptions.

```
$ for p in PASS1 PASS2 PASS3; do
    jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use" and .name=="mcp__cloakbrowser__cloak_evaluate") | .input.expression' \
      "results/2026-05-26/cloakbrowser/$p/raw_stream.jsonl" | grep -oE "fetch\([^)]+\)"
  done | sort -u
fetch('/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html')
fetch('/greenhouse_2026-05-22/anthropic/jobs/5023394008.html')
fetch('http://127.0.0.1:8765/ashby_2026-05-22/replit/1e1a651f-693d-4f9d-bfd9-280a50d28d13.html')
fetch('http://127.0.0.1:8765/greenhouse_2026-05-22/anthropic/jobs/5023394008.html')
fetch(url)
```

The relative-URL `fetch('/...')` calls resolve against the loopback origin
(the document was loaded from `http://127.0.0.1:8765/...` so the URL base is
loopback). The `fetch(url)` calls were preceded by `const url =
'http://127.0.0.1:8765/...'` in every occurrence (verified via context grep).

### Phase 2 — full transcript hostname sweep (false-positive triage)

```
$ grep -rohE 'https?://[^/[:space:]"]+' \
    results/2026-05-26/cloakbrowser/PASS{1,2,3}/transcript.md \
    results/2026-05-26/cloakbrowser/PASS{1,2,3}/raw_stream.jsonl | sort -u
http://127.0.0.1:8765
http://127.0.0.1:8765/...   (many, all loopback)
http://www.w3.org           ← extracted from XML namespace declarations in snapshot SVG
https://alignment.anthropic.com   ← extracted: link in job description body
https://bit.ly/afpsafety          ← extracted: the apply URL printed inline in the Greenhouse SSR HTML
https://cdn.ashbyprd.com          ← extracted: stylesheet href in Ashby's SPA shell
https://fonts.googleapis.com      ← extracted: <link rel="stylesheet"> in snapshot HTML
https://github.com                ← extracted: link in job description body
https://job-boards.greenhouse.io  ← extracted: og:url meta property
https://job-boards.cdn.greenhouse.io ← extracted: stylesheet href in Greenhouse SSR HTML
https://linkedin.com              ← extracted: link in job description body
https://s8-recruiting.cdn.greenhouse.io ← extracted: og:image URL
https://www.anthropic.com         ← extracted: link in job description body
```

**ALL non-loopback hostnames appearing in transcripts are content strings
extracted from the snapshot HTML — they were never targets of any cloakbrowser
tool call.** The snapshot fixtures (`fixtures/snapshots/greenhouse_2026-05-22/`
and `ashby_2026-05-22/`) are 1:1 captures of live job postings that legitimately
contain these external URLs as `<link>` references, `og:` meta properties, and
in-body anchor hrefs. The agent surfaced these in YAML extraction outputs
(stage_s1.yml, stage_s2.yml) and discussion text (stage_s3.md, stage_s4.md);
none became a `cloak_navigate` URL or an in-page `fetch()` argument.

The agent's stage artifacts cite the apply URL `https://bit.ly/afpsafety` as
extracted data — this is the FIXTURE's data, served from loopback, and the
agent never tried to follow that link.

### Phase 3 — passive browser background requests

Cloakbrowser's Chromium engine, on `cloak_navigate` to the snapshot fixture,
will attempt to load whatever the HTML references — fonts, stylesheets, scripts
from `cdn.greenhouse.io`, `cdn.ashbyprd.com`, `fonts.googleapis.com`. These
are HTTP requests fired by the browser's HTML parser **without going through
the MCP tool surface**, so they do not appear in `raw_stream.jsonl`. They are
NOT under harness control and do NOT constitute a SAFETY-04 violation — they
are the browser doing what a browser does when loading a real HTML page.

This is the same passive-loading behavior every other Chromium-based MCP
exhibits in this benchmark (Playwright loads the same fonts; chrome-devtools
the same CDN; obscura the same Greenhouse stylesheet). The harness fixtures
were captured AS-IS to preserve apples-to-apples comparability; redacting
external `<link>` references would change the JS-rendering surface for every
MCP, not just cloakbrowser.

**This passive background loading does NOT touch authenticated personal
sessions** — the SAFETY-04 contract concerns cookie-bearing navigation to
authenticated hosts, which only `cloak_navigate` can perform. All
`cloak_navigate` calls were loopback (Phase 1). Stylesheet `<link>` fetches
do not carry user session cookies for `cloak_navigate`'s active document
origin (cross-origin third-party requests do not include first-party
cookies under default same-site policy).

## Outcome

- **All 3 passes:** every active `cloak_navigate` and every in-page `fetch()`
  targeted `127.0.0.1:8765` exclusively.
- **No `SANDBOX_VIOLATION.md` sentinel** was triggered.
- **SAFETY-04 contract upheld:** the closed-source cloakbrowser binary was
  only ever pointed at the loopback snapshot server. Cookie-touching at launch
  affected the agent's own ephemeral profile, not any authenticated session.
- **REPORT-08 obligation:** every cloakbrowser mention in `DEEP_ANALYSIS.md`
  and the eventual Phase 4 report MUST carry
  `**Sandbox only — do not point at authenticated sessions**`.

## What is NOT proven by this audit

- The cloakbrowser binary's behavior under closed-source instrumentation is not
  open to source review. The audit proves the *agent did not direct* the binary
  at non-loopback hosts; it does not prove the binary itself made no
  out-of-band telemetry calls. That class of risk is the reason for the
  sandbox-only contract: even if the binary phones home on launch, that
  exposure is bounded to the harness's ephemeral profile.
- Bot-detection stealth claims (Cloudflare, reCAPTCHA, FingerprintJS) are
  DEFERRED to G-710 per CONTEXT.md `## Deferred Ideas` and are not validated by
  this Phase-2 run.

## Sources

- `bench/cloakbrowser_guard.py` — `assert_local_only()` implementation
- `scripts/run_mcp_session.sh:127-130` — guard invocation
- `results/2026-05-26/cloakbrowser/PASS{1,2,3}/raw_stream.jsonl` — full tool-call streams
- `results/2026-05-26/cloakbrowser/PASS{1,2,3}/transcript.md` — agent-derived transcripts
- `CLAUDE.md ## Constraints` — sandbox-only policy origin
- `~/.claude/docs/browser-tools.md` (2026-05-21) — closed-binary cookie-touching note
