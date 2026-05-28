# External browser-tools research notes — 2026-05-21 snapshot

> **Status:** Summary of findings from an internal browser-automation tooling
> review conducted 2026-05-21. The original notes (`~/.claude/docs/browser-tools.md`)
> are a private working document on the maintainer's machine; this file extracts
> the publicly-citable findings that the Phase 4 report and recommendations rely on,
> so third-party readers can verify claims using only the public repo.
> Per CLAUDE.md: "Reproducibility — methodology must be runnable by a third party
> with only the public repo."

This file is the public-repo home of the externally-sourced findings that
`bench/build_report.py` and `bench/build_recommendations.py` cite. The findings
themselves were measured against the live tools; the citations here let a reader
verify what claim each artifact line is grounded in.

## SAFETY-03 — macOS `--stealth` flag leaks `Sec-CH-UA-Platform-*`

**Finding (verified 2026-05-21 across multiple stealth-capable browser MCPs).**
Enabling `--stealth` mode on macOS host machines does NOT actually hide the OS
identity from sites that consult HTTP client hints. The `Sec-CH-UA-Platform`,
`Sec-CH-UA-Platform-Version`, and `Sec-CH-UA-Arch` headers are sourced from
the underlying network stack (Chrome's platform integration), not from
JavaScript. A JS-level User-Agent shim cannot rewrite these — they ship with
every TLS handshake.

**Impact on this benchmark.** Obscura's `--stealth` flag was DISABLED on macOS
for the 2026-05-26 wave. The macOS-host stealth claim cannot be honestly
validated without a Linux host where `Sec-CH-UA-Platform-*` is honest about
the OS. The Linux A/B is the G-710 follow-up (REPRO-07 scope).

**Detection mechanism (background).** Cloudflare's bot-management layer
cross-checks the JS-visible navigator.userAgent against `Sec-CH-UA-Platform-*`
on every request. A mismatch (e.g. JS UA says Linux, client hints say macOS)
elevates the request's bot-likelihood score, frequently triggering challenges.

**Affected MCPs:** Obscura (`obscura-mcp`), and any other browser MCP that
exposes a `stealth` flag while running on Chromium-on-macOS. CloakBrowser is a
separate case — its closed-binary sandbox-only model is governed by SAFETY-04,
not SAFETY-03.

## Cookie-touch on launch (CloakBrowser observation)

**Finding (verified 2026-05-21).** CloakBrowser's launcher binary touches the
host's existing browser cookie stores on first invocation as part of its
profile setup. This is a closed-source binary; the exact files touched are
not auditable from the user's side.

**Impact on this benchmark.** CloakBrowser is sandbox-only — pointed only at
the public Greenhouse + Ashby snapshot fixtures, never at authenticated host
sessions. The Phase 4 recommendations file gates this with a per-mention
"Sandbox only — do not point at authenticated sessions" callout.

## TLS fingerprint dominance for 2025–2026 bot detection

**Finding (general industry observation, 2025–2026).** JA3 and JA4 TLS
fingerprints have become the dominant first-pass bot-detection signal at the
major edges (Cloudflare, Akamai, DataDome). User-Agent strings and headless
flags are downstream signals; a clean JA4 fingerprint (matched against real
Chrome's TLS handshake) is what most often determines whether a request gets
challenged.

**Impact on this benchmark.** This benchmark's Phase 2 walk uses loopback
snapshot fixtures (REPRO-04), which do NOT TLS-fingerprint. The dominance
claim is therefore deferred to G-710's bot-detection adversary set, not
exercised in this wave.

## Per-MCP testbench scores (2026-05-21 snapshot)

The 2026-05-21 testbench produced an early-signal score sheet that this
report's Wave 2 measurements supersede with more rigorous evidence. Where
the Wave 2 report cites the 2026-05-21 testbench (`browser-use 0.12.x`
`initialize` timeout regression specifically), it is for the historical
context only — Wave 2's v0.12.7 measurements stand independently and
confirm the regression was fixed.

---

_Generated 2026-05-28 from the 2026-05-21 internal browser-tools review.
Original working notes are not in the public repo; this file extracts the
publicly-citable findings the Phase 4 report depends on._
