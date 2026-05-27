# Reproducing the 2026-05-27 MCP Comparison

This document is the third-party recipe for re-running the
[2026-05-27 MCP comparison wave](../results/2026-05-27-mcp-comparison.md) on
your own machine. The scored matrix and the
[Stage 2 graduation recommendations](../results/recommendations.md) are only as
trustworthy as their reproducibility — this is how you verify the numbers
yourself with only the public repo.

The recipe is deliberately honest about what's verified, what's untested, and
what may legitimately fail on your hardware. The wave was run on a Mac Mini
(Apple Silicon, macOS arm64); MacBook + Linux parity is **not** validated this
wave and is deferred to [G-710](https://linear.app/abandoned-yachts/issue/G-710).

## Prerequisites

| | Required | Verified this wave |
|---|---|---|
| OS / arch | macOS arm64 OR Linux arm64/x86_64 | macOS arm64 (Mac Mini) only |
| Node | 22 LTS | 22.x (see `versions.lock.md`) |
| Python | 3.12+ (the harness `.venv` uses 3.14.5; 3.12 works) | 3.14.5 |
| `uv` | ≥ 0.7.x | pinned via `uv.lock` |
| Claude Code CLI | on `PATH`, recent stable | 2.1.142 |
| `jq` | any 1.7+ | yes |
| `make` | GNU Make 3.81 (Apple system) or 4.x | 3.81 |

The exact pinned versions used for the published wave live in
[`results/2026-05-27/versions.lock.md`](../results/2026-05-27/versions.lock.md)
(and its machine-readable companion `versions.json`). That file is the canonical
exact-version snapshot — regenerate yours with `make versions` after install and
diff against ours to confirm you're on equivalent toolchain.

`results/2026-05-27/MACHINE.md` records the run host (model, CPU, RAM, OS
build, NTP-synced timestamp, network info) — cite when reporting reproduction
deltas.

## Installing the 7 MCPs

The project-scope [`.mcp.json`](../.mcp.json) is the **single source of truth**
for which MCPs are in the wave and how Claude Code spawns each one. Install
each binary so its `command` resolves on your `PATH`:

| MCP key (in `.mcp.json`) | Install command |
|---|---|
| `playwright` | `npm install -g @playwright/mcp` (then `npx playwright install chromium` on first run) |
| `browser-use` | `uv tool install browser-use[cli]` |
| `chrome-devtools` | `npm install -g chrome-devtools-mcp` |
| `lightpanda` | Download the nightly binary from [lightpanda-io/browser releases](https://github.com/lightpanda-io/browser/releases) and place it on `PATH` |
| `obscura` | `npm install -g obscura-mcp` then `obscura-mcp install` to fetch the Rust+V8 engine |
| `firecrawl` | `npm install -g firecrawl-mcp` (cloud — also needs `FIRECRAWL_API_KEY`, see below) |
| `cloakbrowser` | `uv tool install cloakbrowsermcp` — **see sandbox-only constraint below** |

After install, run the prereq gate:

```bash
scripts/check_prereqs.sh
```

It exits non-zero with a remediation message if any of the 7 binaries are
missing from `PATH`.

## API keys

`FIRECRAWL_API_KEY` is the **only** paid-key requirement in this wave. The
firecrawl MCP is a thin client over the firecrawl.dev cloud and won't return
anything useful without it.

Sign up at <https://firecrawl.dev> and export the key:

```bash
export FIRECRAWL_API_KEY=fc-...   # in your shell, OR
echo 'FIRECRAWL_API_KEY=fc-...' >> .env          # in a gitignored .env, OR
echo 'export FIRECRAWL_API_KEY=fc-...' >> .envrc # via direnv (recommended)
```

`.env` and `.envrc` are gitignored. **Never commit a literal key into
`.mcp.json`** — the SAFETY-01 pre-commit hook blocks inline secrets and the
env-var-reference form (`${FIRECRAWL_API_KEY}`) is the only accepted shape.

If the key is absent, the harness runs **6/7** of the candidate set: the
firecrawl row in the published matrix is rendered as `SKIPPED` with the
`LLM_KEY_ABSENT` / `API_KEY_ABSENT` failure-attribution tag rather than a
silent zero. Per project policy, **partial 6/7 scoring is acceptable** — the
report still ships and the composite denominator is honest about what was
measured. No other paid keys are needed.

## Running the comparison

The single command is:

```bash
make bench
```

`make bench` is wired in the [Makefile](../Makefile) as:

1. `scripts/check_prereqs.sh` — gate (HARNESS-06).
2. `make bench-<mcp>` for each of the 7 MCPs sequentially (orphan-process
   clashes if parallel).
3. `make score` — aggregates `results/$(DATE)/scores.json` through
   `scoring/score.py` (the locked, sacrosanct rubric).

The fixture server (`scripts/serve_fixtures.sh`) auto-starts on
`127.0.0.1:8765` so every MCP sees the same loopback snapshot of the
Greenhouse + Ashby fixtures. **No live URL hits during scored runs** — see
`fixtures/snapshots/*/PROVENANCE.md` for snapshot dates and SHA256s.

Useful additional targets:

```bash
make versions       # regenerate results/<DATE>/versions.{json,lock.md}
make cold-start     # 3-segment cold + warm sweep (MEAS-01)
make stability      # selective_top3_60min_rest_30min stability soak (MEAS-07)
make bench-<mcp>    # one MCP only — e.g. make bench-playwright
make help           # full target listing
```

### Why no Docker / devcontainer?

Containerised reproducibility was explicitly rejected for this wave. Docker
adds an indirection layer that contaminates cold-start latency, and any TLS
fingerprint captured inside a container is the container's, not the host's —
useless for the bot-detection follow-up in G-710. See
`.planning/RESEARCH.md §4` for the full rationale.

## cloakbrowser: sandbox-only

> **Sandbox only — do not point at authenticated sessions.**

`cloakbrowser` (`cloakbrowsermcp` on PyPI) is a **closed-source binary that
touches cookies on launch**. Per global browser-tools policy and the wave's
SAFETY-04 requirement, it is tested **only** against the public Greenhouse +
Ashby loopback snapshot fixtures. The harness rejects any attempt to point
`cloakbrowser` at a non-`127.0.0.1` host (see `bench/cloakbrowser_guard.py`).

Linux availability is **uncertain**: only the macOS arm64 binary was verified
in this wave. The upstream vendor (`overtimepog/CloakMCP`) ships a Linux build,
but it has not been A/B'd against the macOS arm64 baseline. If `cloakbrowser`
fails to install or run on your platform, the harness emits a clearly-labeled
`INSTALL_FAILED` row in the matrix with the reason captured — partial scoring
(6/7) is acceptable, exactly the same policy as the firecrawl-API-key-absent
case.

Every mention of `cloakbrowser` in the public report (`results/recommendations.md`
and `results/2026-05-27-mcp-comparison.md`) carries the same **Sandbox only —
do not point at authenticated sessions** callout. That convention exists
because the closed binary's cookie-touch behaviour is a real
credential-exfiltration risk on real host pages.

## Cross-machine parity disclosure

The 2026-05-27 wave was run end-to-end on **one machine**: a Mac Mini (Apple
Silicon, macOS arm64). Per PROJECT.md: _"Mac Mini has all 7 binaries installed;
MacBook parity not yet verified."_

Specifically **not** validated this wave:

- **MacBook (Apple Silicon)** — same arch as the Mac Mini, but the harness has
  not been re-run on it. Scores may drift due to thermal-throttling-driven
  latency differences during the cold-start dimension.
- **Linux arm64** — untested. The 7 MCPs nominally support it, but the
  `cloakbrowser` macOS binary is the only one verified, and Lightpanda's
  Linux-arm64 nightly may not match the macOS build feature-for-feature.
- **Linux x86_64** — untested. Same caveats; additionally
  `Sec-CH-UA-Platform-*` client-hint behaviour for `obscura` differs from
  macOS and may shift the SAFETY-03 stealth-leak verdict (see
  `~/.claude/docs/browser-tools.md`).

Cross-machine reproducibility — including the bot-detection /
TLS-fingerprint / residential-IP cuts that were also deferred — moves to
follow-up wave [G-710](https://linear.app/abandoned-yachts/issue/G-710).
G-710 reuses this wave's harness once it ships and adds the anti-captcha.com
integration plus MacBook + Linux re-runs.

## What to expect

A successful `make bench` produces, per MCP:

```
results/<DATE>/<mcp>/
  cold_start.json
  tokens.json
  stability_metadata.json
  tool_call_counts.json
  tools_inventory.json
  PASS1/  PASS2/  PASS3/   ← median-of-3 per FAIRNESS-01
  DEEP_ANALYSIS.md          ← per-MCP strengths/weaknesses
```

Plus the aggregated artifacts:

```
results/<DATE>/
  scores.json
  CROSS_CUT_SUMMARY.md
  CAPABILITY_MATRIX.md
  MACHINE.md
  versions.lock.md  versions.json
```

Your composite scores should land within **±0.5** of the published
`results/2026-05-27-mcp-comparison.md` composites — that's the same tolerance
the Phase 1 harness calibration gate uses against the 2026-03 baseline
(see [`results/2026-05-25/PHASE1_CALIBRATION.md`](../results/2026-05-25/PHASE1_CALIBRATION.md)
which logged Playwright at 7.93 inside the [7.83, 8.83] accept band). If your
composite falls outside that window, capture your `MACHINE.md` + your
`versions.lock.md` + the affected `PASS*/` directories and file the delta.

## Troubleshooting

Three most-likely failure modes, with the expected response:

1. **An MCP binary is missing from `PATH`.** `scripts/check_prereqs.sh` (run
   automatically as the first step of `make bench`) flags it with a
   remediation message. Re-run the install command from the table above; if
   you skipped one deliberately, the corresponding `bench-<mcp>` target will
   exit early and the matrix row will be tagged `INSTALL_FAILED` rather than
   silently zeroed.
2. **`FIRECRAWL_API_KEY` absent → 6/7 partial run.** This is the documented
   acceptable mode. The firecrawl row appears as `SKIPPED` with the
   `API_KEY_ABSENT` tag; the composite denominator drops accordingly so the
   averaged result is still honest.
3. **`cloakbrowser` unavailable on Linux (or any non-macOS-arm64 platform).**
   Expected per the sandbox-only + Linux-uncertainty disclosure above. The
   `cloakbrowser` row renders as `INSTALL_FAILED` with the platform reason.
   The rest of the matrix is unaffected and the wave still ships.

Anything outside these three modes is a real failure worth reporting upstream.
G-703 is the umbrella ticket and `.planning/REQUIREMENTS.md` lists the
per-requirement IDs (HARNESS-01..09, FAIRNESS-01..07, MEAS-01..09,
REPRO-01..06, REPORT-01..12, SAFETY-01..05) you can cite when filing.
