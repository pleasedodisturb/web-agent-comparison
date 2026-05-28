# Tools-Surface Inventory — Side-by-Side Rollup

_Generated:_ `2026-05-26T22:32:44Z`

_Sources:_ `results/<date>/<mcp>/tools_inventory.json` for each of the **8 MCP rows** below.

Per-MCP probe runs the standard MCP lifecycle (`initialize` → `tools/list`) via `mcp.client.stdio` (Python SDK 1.16) with a 30 s budget. Each tool name is then classified into one of six categories using a first-match-wins keyword table (see `bench/tools_inventory.py::CATEGORY_KEYWORDS`).

| MCP | Status | Tool count | navigation | interaction | capture | diagnostics | inspection | other |
|---|---|---|---|---|---|---|---|---|
| `browser-use-agent` | OK | 16 | 2 | 3 | 1 | 0 | 5 | 5 |
| `browser-use-direct` | OK | 16 | 2 | 3 | 1 | 0 | 5 | 5 |
| `chrome-devtools` | OK | 29 | 1 | 10 | 1 | 10 | 3 | 4 |
| `cloakbrowser` | OK | 20 | 3 | 6 | 1 | 1 | 3 | 6 |
| `firecrawl` | OK | 24 | 1 | 0 | 0 | 0 | 5 | 18 |
| `lightpanda` | OK | 20 | 2 | 7 | 0 | 1 | 2 | 8 |
| `obscura` | OK | 4 | 0 | 0 | 0 | 0 | 1 | 3 |
| `playwright` | OK | 23 | 2 | 11 | 1 | 5 | 1 | 3 |

## Gaps

None — every MCP under this run produced a healthy `tools_inventory.json` with `status: OK`.

## Methodology — six-category scheme

The categorization is rigorously aligned with [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)'s naming and applies a **first-match-wins** keyword table from `bench/tools_inventory.py`. The matching is case-insensitive substring on the **tool name only** (not the description). The order of the table is the resolution order — `interaction` is checked before `diagnostics` and `inspection`, for instance, so a tool like `click_and_capture` lands in `capture` (via the `capture` bucket's `screenshot|pdf|...` keywords) only if no earlier bucket claims it. The full ordered keyword sets are captured in `CATEGORY_KEYWORDS` and reproduced inside each per-MCP `tools_inventory.json` so this rollup is reconstructible from disk alone.

Tool counts that disagree with the sum of their categories indicate either a stale `tools_inventory.json` (re-run the probe) or a tool whose name doesn't match any keyword and landed in `other` — inspect the per-MCP file's `tools[].category` field for details.

