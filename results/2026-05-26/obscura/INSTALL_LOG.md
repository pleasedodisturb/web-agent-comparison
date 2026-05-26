# obscura engine install attempt

- **date:** 2026-05-26T20:05:49Z
- **command:** `obscura-mcp install`
- **exit_code:** 0
- **wrapper_version:** 0.1.4-2 (installed via Homebrew/npm; research/STACK.md predicted 0.1.4-3 as latest on npm 2026-05-22 — host is one patch behind, acceptable for Phase-2 fairness since the engine binary is what does the work and is bundled)
- **engine_version:** 0.1.0 (per JSON-RPC handshake banner: `Headless Browser v0.1.0`; research/STACK.md `## 1` flags this as the known "binary self-identifies inconsistently" quirk — wrapper says 0.1.4-2, engine says 0.1.0; both logged here per the "wrapper version ≠ engine version" rule)
- **engine_binary_path:** `/opt/homebrew/lib/node_modules/obscura-mcp/bin/obscura`
- **engine_binary_sha256:** `1fe02307a10388b8319457b27055d7ba8e7e63f6036d865f14ec903b02ff9041`
- **engine_binary_size:** 59747760 bytes (~57 MB)
- **engine_binary_arch:** Mach-O 64-bit executable arm64 (native; matches CLAUDE.md macOS-arm64 host)
- **engine_worker_binary_path:** `/opt/homebrew/lib/node_modules/obscura-mcp/bin/obscura-worker`
- **cdp_endpoint:** `ws://127.0.0.1:9222/devtools/browser` (engine boots a CDP server on port 9222 — relevant to capability tag `stealth-specialist`; raw CDP, not Playwright-on-CDP, is the differentiator per research/SUMMARY.md)
- **stdout (.install.stdout):**
  ```
  Obscura binary ready at /opt/homebrew/lib/node_modules/obscura-mcp/bin/obscura
  ```
- **stderr (.install.stderr):** (empty)

## Outcome

**SUCCESS.** Engine binary is bundled with the npm package (no separate download step
performed by `obscura-mcp install`; the subcommand exists and exits 0, simply confirming
the pre-bundled binary is present). The known HANDOFF-GSD-AUTO STOP #3 "macOS arm64
install gap" did **not** materialize on this host — the npm wrapper at 0.1.4-2 already
ships the arm64 engine. Proceeding to the scored branch (3-pass median harness).

## Notes for Phase 4

- Wrapper version (0.1.4-2) ≠ engine version (0.1.0). Document both in the comparison
  matrix; do not collapse to a single version string.
- The engine's CDP-direct architecture (port 9222) is the architectural differentiator
  that motivates the `stealth-specialist` capability tag and the memory-footprint
  empirical claim falsification (see DEEP_ANALYSIS.md § "CDP-direct memory footprint").
- The `obscura-mcp install` subcommand is essentially a no-op when the engine is
  already bundled. If a future macOS arm64 host hits the HANDOFF STOP #3 install gap,
  the same SKIPPED branch documented in PLAN 02-04 § Task 1 step 3 applies; on this
  host it did not trip.
