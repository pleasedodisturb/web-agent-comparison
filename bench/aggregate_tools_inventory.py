"""aggregate_tools_inventory — MEAS-09 rollup of per-MCP tools_inventory.json.

For each direct child directory under `results/<date>/`:

  1. Read `tools_inventory.json` if present; capture status, tool_count,
     categories (the six-bucket scheme from bench/tools_inventory.py).
  2. If missing, mark the row `status=MISSING` so the rendered doc
     surfaces the gap explicitly.

The aggregator emits a single Markdown file (default
`results/<date>/TOOLS_INVENTORY_SUMMARY.md`) with:

  - A side-by-side category table (one row per MCP, columns for the six
    categories + tool_count + status).
  - A "Gaps" section listing every row whose status is not OK (MISSING,
    INITIALIZE_TIMEOUT, SPAWN_OR_RPC_ERROR, ...).
  - A methodology footer citing the first-match-wins category keyword
    table from `bench/tools_inventory.py`.

Stdlib-only. The companion `bench/tools_inventory.py` is responsible for
producing the per-MCP JSON; this module only consumes it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

# Match the canonical CATEGORY_NAMES from bench/tools_inventory.py, in
# their canonical render order. Keeping it duplicated avoids importing
# the heavyweight `bench.tools_inventory` (which pulls in the `mcp` SDK)
# just to render Markdown — the aggregator stays import-light so it can
# run anywhere.
CATEGORY_RENDER_ORDER = (
    "navigation",
    "interaction",
    "capture",
    "diagnostics",
    "inspection",
    "other",
)


# ─── Collection ──────────────────────────────────────────────────────────


def collect_inventories(results_date_dir: Path) -> list[dict[str, Any]]:
    """Return one row per per-MCP subdirectory under results_date_dir.

    Each row dict carries: ``mcp``, ``status`` (OK / MISSING / probe-error
    code), ``tool_count``, ``categories`` (dict with all 6 keys zero-
    filled), and the optional ``inventory_path`` for cross-reference.
    """
    rows: list[dict[str, Any]] = []
    for child in sorted(results_date_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        inventory_path = child / "tools_inventory.json"
        row: dict[str, Any] = {
            "mcp": child.name,
            "inventory_path": str(inventory_path.relative_to(results_date_dir.parent)),
        }
        if not inventory_path.exists():
            row.update(
                status="MISSING",
                tool_count=0,
                categories={k: 0 for k in CATEGORY_RENDER_ORDER},
            )
            rows.append(row)
            continue

        try:
            inv = json.loads(inventory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            row.update(
                status="PARSE_ERROR",
                tool_count=0,
                categories={k: 0 for k in CATEGORY_RENDER_ORDER},
                parse_error=f"{type(exc).__name__}: {exc}",
            )
            rows.append(row)
            continue

        cats = inv.get("categories") or {}
        # Normalize: ensure every render-order key is present (zero-fill).
        normalized = {k: int(cats.get(k, 0)) for k in CATEGORY_RENDER_ORDER}
        row.update(
            status=inv.get("status", "UNKNOWN"),
            tool_count=int(inv.get("tool_count", 0) or 0),
            categories=normalized,
            version_handshake=inv.get("version_handshake"),
        )
        rows.append(row)
    return rows


def find_gaps(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the subset of rows whose status is not OK."""
    return [r for r in rows if r.get("status") != "OK"]


# ─── Rendering ───────────────────────────────────────────────────────────


def _now_iso_utc() -> str:
    return (
        dt.datetime.now(tz=dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def render_markdown(
    rows: list[dict[str, Any]],
    *,
    generated_at: str | None = None,
) -> str:
    """Render the full rollup Markdown document."""
    generated_at = generated_at or _now_iso_utc()

    # Header: title, generation stamp, MCP count.
    out: list[str] = [
        "# Tools-Surface Inventory — Side-by-Side Rollup",
        "",
        f"_Generated:_ `{generated_at}`",
        "",
        f"_Sources:_ `results/<date>/<mcp>/tools_inventory.json` for each "
        f"of the **{len(rows)} MCP rows** below.",
        "",
        "Per-MCP probe runs the standard MCP lifecycle "
        "(`initialize` → `tools/list`) via `mcp.client.stdio` "
        "(Python SDK 1.16) with a 30 s budget. Each tool name is then "
        "classified into one of six categories using a first-match-wins "
        "keyword table (see `bench/tools_inventory.py::CATEGORY_KEYWORDS`).",
        "",
    ]

    # Detect consistency mismatches up-front so the table footer can flag them.
    inconsistent: list[str] = []
    for r in rows:
        if r.get("status") != "OK":
            continue
        if sum(r["categories"].values()) != r["tool_count"]:
            inconsistent.append(r["mcp"])

    # Render the main table.
    header_cols = ["MCP", "Status", "Tool count"] + list(CATEGORY_RENDER_ORDER)
    out.append("| " + " | ".join(header_cols) + " |")
    out.append("|" + "|".join(["---"] * len(header_cols)) + "|")
    for r in rows:
        cells = [
            f"`{r['mcp']}`",
            r.get("status", "?"),
            str(r.get("tool_count", 0)),
        ]
        for cat in CATEGORY_RENDER_ORDER:
            cells.append(str(r["categories"].get(cat, 0)))
        out.append("| " + " | ".join(cells) + " |")
    out.append("")

    if inconsistent:
        out.append(
            "> ⚠ **Inconsistent rows** (sum of categories ≠ tool_count): "
            + ", ".join(f"`{n}`" for n in inconsistent)
            + ". Likely an outdated `tools_inventory.json` — "
              "re-run `python -m bench.tools_inventory <name>` to refresh."
        )
        out.append("")

    # Gaps section — always present even if empty so readers learn the contract.
    gaps = find_gaps(rows)
    out.append("## Gaps")
    out.append("")
    if not gaps:
        out.append("None — every MCP under this run produced a healthy "
                   "`tools_inventory.json` with `status: OK`.")
    else:
        out.append(
            "The following MCPs did not produce a `status: OK` "
            "tools_inventory.json. Each row's `inventory_path` is "
            "preserved so the diagnostic JSON remains as evidence:"
        )
        out.append("")
        out.append("| MCP | Status | Evidence path |")
        out.append("|---|---|---|")
        for g in gaps:
            out.append(
                f"| `{g['mcp']}` | {g.get('status', '?')} | "
                f"`{g.get('inventory_path', '(missing)')}` |"
            )
    out.append("")

    # Methodology footer.
    out.append("## Methodology — six-category scheme")
    out.append("")
    out.append(
        "The categorization is rigorously aligned with "
        "[chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)'s "
        "naming and applies a **first-match-wins** keyword table from "
        "`bench/tools_inventory.py`. The matching is case-insensitive "
        "substring on the **tool name only** (not the description). The "
        "order of the table is the resolution order — `interaction` is "
        "checked before `diagnostics` and `inspection`, for instance, "
        "so a tool like `click_and_capture` lands in `capture` (via the "
        "`capture` bucket's `screenshot|pdf|...` keywords) only if no "
        "earlier bucket claims it. The full ordered keyword sets are "
        "captured in `CATEGORY_KEYWORDS` and reproduced inside each "
        "per-MCP `tools_inventory.json` so this rollup is reconstructible "
        "from disk alone."
    )
    out.append("")
    out.append(
        "Tool counts that disagree with the sum of their categories "
        "indicate either a stale `tools_inventory.json` (re-run the probe) "
        "or a tool whose name doesn't match any keyword and landed in "
        "`other` — inspect the per-MCP file's `tools[].category` field for "
        "details."
    )
    out.append("")

    return "\n".join(out) + "\n"


# ─── CLI ─────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.aggregate_tools_inventory",
        description=(
            "Read tools_inventory.json from every per-MCP subdir of "
            "results/<date>/ and emit a side-by-side TOOLS_INVENTORY_SUMMARY.md."
        ),
    )
    parser.add_argument(
        "results_date_dir",
        type=Path,
        help="e.g. results/2026-05-26",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Output Markdown path "
            "(default: <results_date_dir>/TOOLS_INVENTORY_SUMMARY.md)."
        ),
    )
    args = parser.parse_args(argv)

    if not args.results_date_dir.is_dir():
        print(
            f"aggregate_tools_inventory: ERROR "
            f"{args.results_date_dir} is not a directory",
            file=sys.stderr,
        )
        return 2

    rows = collect_inventories(args.results_date_dir)
    out_path = args.out or (args.results_date_dir / "TOOLS_INVENTORY_SUMMARY.md")
    out_path.write_text(render_markdown(rows), encoding="utf-8")

    gaps = find_gaps(rows)
    print(
        f"aggregate_tools_inventory: wrote {out_path} "
        f"({len(rows)} rows, {len(gaps)} non-OK).",
        file=sys.stderr,
    )
    for g in gaps:
        print(
            f"  - gap: {g['mcp']} status={g.get('status')} "
            f"path={g.get('inventory_path')}",
            file=sys.stderr,
        )

    # Exit 0 even with gaps — the doc itself is the surfacing mechanism.
    return 0


if __name__ == "__main__":
    sys.exit(main())
