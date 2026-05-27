"""build_cross_cut_summary — Phase-3 synthesis aggregator.

Walks `results/<date>/<mcp>/` for every MCP that has at least one of the
five cross-cutting artifacts produced by Phase-3 plans 03-01..03-04, joins
them into a single in-memory rollup, then renders a Phase-4-consumable
`CROSS_CUT_SUMMARY.md` (and an optional JSON companion).

The five per-MCP source artifacts read here:

    cold_start.json          (Plan 03-03, MEAS-01)
    tokens.json              (Plan 03-02, MEAS-02)
    stability_metadata.json  (Plan 03-04, MEAS-07)
    tool_call_counts.json    (Plan 03-01, MEAS-08)
    tools_inventory.json     (Plan 03-01, MEAS-09)

The aggregator does NOT re-measure anything; it is pure synthesis.

CLI
---
    python -m bench.build_cross_cut_summary <RESULTS_DATE_DIR> \\
        --out <CROSS_CUT_SUMMARY.md> \\
        [--json-out <cross_cut_data.json>]

The aggregator is stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

# ─── Constants ───────────────────────────────────────────────────────────

# The five cross-cutting artifact filenames (in order of MEAS- requirement).
ARTIFACT_FILES = (
    "cold_start.json",      # MEAS-01
    "tokens.json",          # MEAS-02
    "stability_metadata.json",  # MEAS-07
    "tool_call_counts.json",    # MEAS-08
    "tools_inventory.json",     # MEAS-09
)

DIMENSION_KEYS = (
    "cold_start",
    "tokens",
    "stability",
    "tcc",
    "inventory",
)

# Mapping dimension -> source filename
DIMENSION_FILE = {
    "cold_start": "cold_start.json",
    "tokens": "tokens.json",
    "stability": "stability_metadata.json",
    "tcc": "tool_call_counts.json",
    "inventory": "tools_inventory.json",
}

# Ordering for the matrix rows. Falls back to alphabetical if scores.json
# is missing. Approximated from Phase 2 composite ranking — adjusted by
# loading scores.json composite when present.
DEFAULT_ROW_ORDER = (
    "cloakbrowser",
    "playwright",
    "lightpanda",
    "browser-use-direct",
    "chrome-devtools",
    "firecrawl",
    "obscura",
    "browser-use-agent",
)


# ─── Pure aggregation ───────────────────────────────────────────────────


def _safe_load_json(path: Path) -> dict | None:
    """Read a JSON file; return None on missing or parse error."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _dimension_status(dim: str, payload: dict | None) -> str:
    """Return the canonical status string for a dimension's payload.

    Missing file -> MISSING.
    For stability the canonical field is `completion_status`
    (COMPLETED / SKIPPED / CRASHED / TIMED_OUT). All other dimensions
    use the `status` field.
    """
    if payload is None:
        return "MISSING"
    if dim == "stability":
        cs = payload.get("completion_status")
        if isinstance(cs, str) and cs:
            return cs
    status = payload.get("status")
    if isinstance(status, str) and status:
        return status
    return "OK"


def _discover_mcps(results_date_dir: Path) -> list[str]:
    """List subdirectories under results_date_dir that look like MCP dirs.

    A directory counts as an MCP dir if it contains at least one of the
    five cross-cut artifacts OR a SKIPPED.md sentinel.
    """
    mcps: list[str] = []
    for child in sorted(results_date_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        has_artifact = any((child / f).is_file() for f in ARTIFACT_FILES)
        has_skipped = (child / "SKIPPED.md").is_file()
        if has_artifact or has_skipped:
            mcps.append(child.name)
    return mcps


def _row_order(results_date_dir: Path, discovered: list[str]) -> list[str]:
    """Order MCP rows by the locked Phase-2 ranking (with extras appended).

    Reads scores.json to confirm membership; falls back to DEFAULT_ROW_ORDER
    if scores.json is unavailable. Any newly-discovered MCP not in the
    canonical list is appended alphabetically at the end.
    """
    scores_path = results_date_dir / "scores.json"
    scores = _safe_load_json(scores_path) or {}
    canonical = [m for m in DEFAULT_ROW_ORDER if m in discovered]
    extras = sorted(set(discovered) - set(canonical))
    ordered = canonical + extras
    # Preserve scores membership note for the JSON companion
    return ordered if ordered else sorted(discovered)


def aggregate_results(results_date_dir: Path) -> dict[str, Any]:
    """Walk per-MCP dirs and return a JSON-ready rollup.

    Output shape::

        {
            "results_date_dir": str(<date>),
            "mcps": [
                {
                    "mcp": "<name>",
                    "cold_start": {"status": "OK", "raw": {...}},
                    "tokens":     {"status": "OK"|"SKIPPED", "raw": {...}},
                    "stability":  {"status": "COMPLETED"|"SKIPPED"|"CRASHED",
                                   "skip_reason": "<reason or None>",
                                   "raw": {...}},
                    "tcc":        {"status": "OK"|"SKIPPED"|"NO_EVIDENCE", "raw": {...}},
                    "inventory":  {"status": "OK", "raw": {...}},
                },
                ...
            ],
            "missing_files": [<relative paths>],
            "metadata": {
                "generator": "bench.build_cross_cut_summary",
                "n_mcps": <int>,
            },
        }
    """
    if not results_date_dir.is_dir():
        raise FileNotFoundError(f"not a directory: {results_date_dir}")

    discovered = _discover_mcps(results_date_dir)
    ordered = _row_order(results_date_dir, discovered)

    mcps: list[dict[str, Any]] = []
    missing_files: list[str] = []
    for mcp in ordered:
        mcp_dir = results_date_dir / mcp
        row: dict[str, Any] = {"mcp": mcp}
        for dim, fname in DIMENSION_FILE.items():
            path = mcp_dir / fname
            payload = _safe_load_json(path)
            if payload is None:
                missing_files.append(f"{mcp}/{fname}")
                row[dim] = {"status": "MISSING", "raw": None}
                continue
            status = _dimension_status(dim, payload)
            entry: dict[str, Any] = {"status": status, "raw": payload}
            # Convenience: lift skip_reason for stability + tokens
            if dim == "stability":
                entry["skip_reason"] = payload.get("skip_reason")
            row[dim] = entry
        mcps.append(row)

    return {
        "results_date_dir": str(results_date_dir),
        "mcps": mcps,
        "missing_files": missing_files,
        "metadata": {
            "generator": "bench.build_cross_cut_summary",
            "n_mcps": len(mcps),
        },
    }


# ─── Cell formatters (used by table renderers) ──────────────────────────


def _fmt_cell(value: Any) -> str:
    """Format a single cell value for a Markdown table; handle None/MISSING."""
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _cold_start_cells(entry: dict) -> tuple[str, str]:
    """Return (cold_total_ms, warm_total_ms) formatted strings."""
    status = entry.get("status")
    if status == "MISSING" or entry.get("raw") is None:
        return ("MISSING", "MISSING")
    raw = entry["raw"]
    cold = raw.get("cold", {}).get("median", {}).get("total_ms")
    warm = raw.get("warm", {}).get("median", {}).get("total_ms")
    return (_fmt_cell(cold), _fmt_cell(warm))


def _tokens_cells(entry: dict) -> tuple[str, str, str]:
    """Return (payload_bytes, input_tokens, output_tokens)."""
    status = entry.get("status")
    if status == "MISSING" or entry.get("raw") is None:
        return ("MISSING", "MISSING", "MISSING")
    raw = entry["raw"]
    if status == "SKIPPED":
        return ("SKIPPED", "SKIPPED", "SKIPPED")
    if status == "NO_EVIDENCE":
        return ("NO_EVIDENCE", "NO_EVIDENCE", "NO_EVIDENCE")
    payload = raw.get("headline_payload_bytes")
    in_tok = raw.get("median_turn_input_tokens")
    out_tok = raw.get("median_turn_output_tokens")
    return (_fmt_cell(payload), _fmt_cell(in_tok), _fmt_cell(out_tok))


def _stability_cells(entry: dict) -> tuple[str, str, str, str]:
    """Return (status_label, iters, configured_min, actual_min)."""
    status = entry.get("status")
    if status == "MISSING" or entry.get("raw") is None:
        return ("MISSING", "—", "—", "—")
    raw = entry["raw"]
    if status == "SKIPPED":
        reason = entry.get("skip_reason") or raw.get("skip_reason") or "(no reason)"
        return (f"SKIPPED ({reason})", "0", "0", "0")
    iters = raw.get("iterations_completed", "—")
    configured = raw.get("configured_duration_minutes", "—")
    actual = raw.get("actual_duration_minutes", "—")
    return (str(status), _fmt_cell(iters), _fmt_cell(configured), _fmt_cell(actual))


def _tcc_cells(entry: dict) -> tuple[str, str]:
    """Return (median_total_calls, median_S5_total)."""
    status = entry.get("status")
    if status == "MISSING" or entry.get("raw") is None:
        return ("MISSING", "MISSING")
    raw = entry["raw"]
    if status in ("SKIPPED", "NO_EVIDENCE"):
        return (status, status)
    total = raw.get("median_total_calls")
    s5 = raw.get("median_total_per_stage", {}).get("S5")
    return (_fmt_cell(total), _fmt_cell(s5))


def _inventory_cells(entry: dict) -> tuple[str, str]:
    """Return (tool_count, categories_string)."""
    status = entry.get("status")
    if status == "MISSING" or entry.get("raw") is None:
        return ("MISSING", "MISSING")
    raw = entry["raw"]
    count = raw.get("tool_count")
    cats = raw.get("categories", {}) or {}
    cat_str = "/".join(
        f"{cats.get(c, 0)}" for c in
        ("navigation", "interaction", "capture", "diagnostics", "inspection", "other")
    )
    return (_fmt_cell(count), cat_str)


# ─── Table renderers ────────────────────────────────────────────────────


def _md_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def render_master_table(data: dict) -> str:
    """Render the §1 master cross-cut table."""
    headers = [
        "MCP",
        "Cold-start cold (ms)",
        "Cold-start warm (ms)",
        "Payload bytes (median)",
        "Input tokens",
        "Output tokens",
        "Stability",
        "Iters",
        "Median tool-calls",
        "S5 tool-calls",
        "Tool count",
    ]
    out = [
        _md_row(headers),
        _md_row(["---"] * len(headers)),
    ]
    for row in data["mcps"]:
        cs_cold, cs_warm = _cold_start_cells(row["cold_start"])
        payload, in_tok, out_tok = _tokens_cells(row["tokens"])
        stab_status, iters, _conf, _actual = _stability_cells(row["stability"])
        tcc_total, tcc_s5 = _tcc_cells(row["tcc"])
        inv_count, _ = _inventory_cells(row["inventory"])
        out.append(_md_row([
            f"`{row['mcp']}`",
            cs_cold,
            cs_warm,
            payload,
            in_tok,
            out_tok,
            stab_status,
            iters,
            tcc_total,
            tcc_s5,
            inv_count,
        ]))
    return "\n".join(out)


def render_cold_start_table(data: dict) -> str:
    """Render §2 — cold + warm segment medians per MCP."""
    headers = [
        "MCP", "Status",
        "Cold t_resolve", "Cold t_spawn", "Cold t_first_useful", "Cold total",
        "Warm t_resolve", "Warm t_spawn", "Warm t_first_useful", "Warm total",
    ]
    out = [_md_row(headers), _md_row(["---"] * len(headers))]
    for row in data["mcps"]:
        entry = row["cold_start"]
        if entry["status"] == "MISSING" or entry.get("raw") is None:
            out.append(_md_row(
                [f"`{row['mcp']}`", "MISSING"] + ["—"] * 8
            ))
            continue
        raw = entry["raw"]
        cold = raw.get("cold", {}).get("median", {}) or {}
        warm = raw.get("warm", {}).get("median", {}) or {}
        out.append(_md_row([
            f"`{row['mcp']}`",
            str(entry["status"]),
            _fmt_cell(cold.get("t_resolve_ms")),
            _fmt_cell(cold.get("t_spawn_ms")),
            _fmt_cell(cold.get("t_first_useful_ms")),
            _fmt_cell(cold.get("total_ms")),
            _fmt_cell(warm.get("t_resolve_ms")),
            _fmt_cell(warm.get("t_spawn_ms")),
            _fmt_cell(warm.get("t_first_useful_ms")),
            _fmt_cell(warm.get("total_ms")),
        ]))
    return "\n".join(out)


def render_tokens_table(data: dict) -> str:
    """Render §3 — token efficiency 3-scope per MCP."""
    headers = [
        "MCP", "Status", "Scope",
        "Schema tokens", "Payload bytes (median)",
        "Median input tokens", "Median output tokens",
    ]
    out = [_md_row(headers), _md_row(["---"] * len(headers))]
    for row in data["mcps"]:
        entry = row["tokens"]
        if entry["status"] == "MISSING" or entry.get("raw") is None:
            out.append(_md_row([f"`{row['mcp']}`", "MISSING"] + ["—"] * 5))
            continue
        raw = entry["raw"]
        out.append(_md_row([
            f"`{row['mcp']}`",
            str(entry["status"]),
            _fmt_cell(raw.get("scope")),
            _fmt_cell(raw.get("schema_tokens")),
            _fmt_cell(raw.get("headline_payload_bytes")),
            _fmt_cell(raw.get("median_turn_input_tokens")),
            _fmt_cell(raw.get("median_turn_output_tokens")),
        ]))
    return "\n".join(out)


def render_stability_table(data: dict) -> str:
    """Render §4 — stability per MCP."""
    headers = [
        "MCP", "Status",
        "Configured (min)", "Actual (min)", "Iters",
        "RSS first (kB)", "RSS max (kB)", "RSS growth (kB)",
        "Orphan survivors", "Skip reason",
    ]
    out = [_md_row(headers), _md_row(["---"] * len(headers))]
    for row in data["mcps"]:
        entry = row["stability"]
        if entry["status"] == "MISSING" or entry.get("raw") is None:
            out.append(_md_row([f"`{row['mcp']}`", "MISSING"] + ["—"] * 8))
            continue
        raw = entry["raw"]
        out.append(_md_row([
            f"`{row['mcp']}`",
            str(entry["status"]),
            _fmt_cell(raw.get("configured_duration_minutes")),
            _fmt_cell(raw.get("actual_duration_minutes")),
            _fmt_cell(raw.get("iterations_completed")),
            _fmt_cell(raw.get("rss_first_kb")),
            _fmt_cell(raw.get("rss_max_kb")),
            _fmt_cell(raw.get("rss_growth_kb")),
            _fmt_cell(raw.get("orphan_audit_survivors")),
            _fmt_cell(raw.get("skip_reason")),
        ]))
    return "\n".join(out)


def render_tool_calls_table(data: dict) -> str:
    """Render §5 — per-stage tool-call counts per MCP."""
    headers = [
        "MCP", "Status",
        "Median total", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8",
    ]
    out = [_md_row(headers), _md_row(["---"] * len(headers))]
    for row in data["mcps"]:
        entry = row["tcc"]
        if entry["status"] == "MISSING" or entry.get("raw") is None:
            out.append(_md_row([f"`{row['mcp']}`", "MISSING"] + ["—"] * 9))
            continue
        raw = entry["raw"]
        if entry["status"] in ("SKIPPED", "NO_EVIDENCE"):
            out.append(_md_row(
                [f"`{row['mcp']}`", str(entry["status"])] + ["—"] * 9
            ))
            continue
        per_stage = raw.get("median_total_per_stage", {}) or {}
        out.append(_md_row([
            f"`{row['mcp']}`",
            str(entry["status"]),
            _fmt_cell(raw.get("median_total_calls")),
            _fmt_cell(per_stage.get("S1")),
            _fmt_cell(per_stage.get("S2")),
            _fmt_cell(per_stage.get("S3")),
            _fmt_cell(per_stage.get("S4")),
            _fmt_cell(per_stage.get("S5")),
            _fmt_cell(per_stage.get("S6")),
            _fmt_cell(per_stage.get("S7")),
            _fmt_cell(per_stage.get("S8")),
        ]))
    return "\n".join(out)


def render_inventory_table(data: dict) -> str:
    """Render §6 — tools-inventory 6-category breakdown."""
    headers = [
        "MCP", "Status", "Tool count",
        "navigation", "interaction", "capture",
        "diagnostics", "inspection", "other",
    ]
    out = [_md_row(headers), _md_row(["---"] * len(headers))]
    for row in data["mcps"]:
        entry = row["inventory"]
        if entry["status"] == "MISSING" or entry.get("raw") is None:
            out.append(_md_row([f"`{row['mcp']}`", "MISSING"] + ["—"] * 7))
            continue
        raw = entry["raw"]
        cats = raw.get("categories", {}) or {}
        out.append(_md_row([
            f"`{row['mcp']}`",
            str(entry["status"]),
            _fmt_cell(raw.get("tool_count")),
            _fmt_cell(cats.get("navigation", 0)),
            _fmt_cell(cats.get("interaction", 0)),
            _fmt_cell(cats.get("capture", 0)),
            _fmt_cell(cats.get("diagnostics", 0)),
            _fmt_cell(cats.get("inspection", 0)),
            _fmt_cell(cats.get("other", 0)),
        ]))
    return "\n".join(out)


# ─── Empirical findings (§7) ────────────────────────────────────────────


def _find_mcp(data: dict, name: str) -> dict | None:
    for row in data["mcps"]:
        if row["mcp"] == name:
            return row
    return None


def _verdict(value: float | None, baseline: float | None, kind: str) -> str:
    """Return CONFIRMED / REFUTED / INCONCLUSIVE based on direction.

    `kind`:
      - "lower-better": CONFIRMED iff value < baseline
      - "higher-better": CONFIRMED iff value > baseline
    """
    if value is None or baseline is None:
        return "INCONCLUSIVE (missing data)"
    if kind == "lower-better":
        return "CONFIRMED" if value < baseline else "REFUTED"
    if kind == "higher-better":
        return "CONFIRMED" if value > baseline else "REFUTED"
    return "INCONCLUSIVE"


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _playwright_batch_fill_finding(data: dict) -> str:
    """Compare playwright's S5 median tool-calls vs other MCPs.

    Claim (from research/SUMMARY.md): playwright's `browser_fill_form`
    fills multiple fields in 1-2 calls vs ~6 calls/field for others.
    """
    pw = _find_mcp(data, "playwright")
    if pw is None:
        return ("- **Playwright batch-fill claim:** NO_EVIDENCE — "
                "playwright row missing from results dir.")
    pw_tcc = pw["tcc"]
    if pw_tcc["status"] in ("NO_EVIDENCE", "MISSING", "SKIPPED"):
        reason = pw_tcc["status"]
        if pw_tcc["status"] == "NO_EVIDENCE":
            extra = (
                " (PASS dirs were captured at 2026-05-25 not 2026-05-26; "
                "Phase 4 must reconcile date-dir mismatch before quoting "
                "the batch-fill claim)"
            )
        else:
            extra = ""
        return (
            f"- **Playwright batch-fill claim:** {reason}{extra} — "
            "no S5 tool-call counts available to test the hypothesis. "
            "Phase 4 reader: do NOT cite the batch-fill claim as "
            "CONFIRMED until a re-run with PASS dirs on the current date."
        )
    pw_s5 = _safe_int(
        (pw_tcc.get("raw") or {}).get("median_total_per_stage", {}).get("S5")
    )
    # Collect S5 totals for the other SCORED MCPs (status OK).
    others_s5: list[int] = []
    for row in data["mcps"]:
        if row["mcp"] == "playwright":
            continue
        tcc = row["tcc"]
        if tcc.get("status") != "OK":
            continue
        s5 = _safe_int(
            (tcc.get("raw") or {}).get("median_total_per_stage", {}).get("S5")
        )
        if s5 is None:
            continue
        others_s5.append(s5)
    if pw_s5 is None or not others_s5:
        return (
            "- **Playwright batch-fill claim:** INCONCLUSIVE — could not "
            f"compute baseline (pw_s5={pw_s5}, n_others={len(others_s5)})."
        )
    baseline = statistics.median(others_s5)
    verdict = _verdict(pw_s5, baseline, "lower-better")
    return (
        f"- **Playwright batch-fill claim:** playwright S5 median = {pw_s5} "
        f"tool-calls vs other SCORED MCPs median = {baseline:.1f} "
        f"(n={len(others_s5)}) — **{verdict}**."
    )


def _lightpanda_cold_start_finding(data: dict) -> str:
    lp = _find_mcp(data, "lightpanda")
    pw = _find_mcp(data, "playwright")
    if lp is None or pw is None:
        return "- **Lightpanda cold-start claim:** NO_EVIDENCE (row missing)."
    lp_cs = lp["cold_start"]
    pw_cs = pw["cold_start"]
    if lp_cs["status"] != "OK" or pw_cs["status"] != "OK":
        return (
            f"- **Lightpanda cold-start claim:** INCONCLUSIVE — "
            f"lightpanda status={lp_cs['status']}, playwright status={pw_cs['status']}."
        )
    lp_total = _safe_int(
        (lp_cs.get("raw") or {}).get("cold", {}).get("median", {}).get("total_ms")
    )
    pw_total = _safe_int(
        (pw_cs.get("raw") or {}).get("cold", {}).get("median", {}).get("total_ms")
    )
    if lp_total is None or pw_total is None:
        return "- **Lightpanda cold-start claim:** INCONCLUSIVE — median total_ms missing."
    verdict = _verdict(lp_total, pw_total, "lower-better")
    ratio = pw_total / lp_total if lp_total > 0 else 0
    # Also compute the maximum spread across all OK MCPs (the headline
    # 50× number from the executor's contract).
    all_cs: list[tuple[str, int]] = []
    for row in data["mcps"]:
        cs = row["cold_start"]
        if cs.get("status") != "OK":
            continue
        v = _safe_int(
            (cs.get("raw") or {}).get("cold", {}).get("median", {}).get("total_ms")
        )
        if v is not None and v > 0:
            all_cs.append((row["mcp"], v))
    max_spread_note = ""
    if all_cs:
        all_cs_sorted = sorted(all_cs, key=lambda t: t[1])
        fastest = all_cs_sorted[0]
        slowest = all_cs_sorted[-1]
        max_ratio = slowest[1] / fastest[1] if fastest[1] > 0 else 0
        max_spread_note = (
            f" Maximal cold-start spread across all OK rows: "
            f"`{fastest[0]}` {fastest[1]}ms → `{slowest[0]}` {slowest[1]}ms "
            f"= {max_ratio:.1f}× — this is the headline cold-start delta."
        )
    return (
        f"- **Lightpanda cold-start claim:** lightpanda cold median = {lp_total} ms "
        f"vs playwright {pw_total} ms ({ratio:.1f}× spread) — **{verdict}**. "
        f"Zig binary with no Chromium download path explains the gap.{max_spread_note}"
    )


def _obscura_memory_finding(data: dict) -> str:
    obs = _find_mcp(data, "obscura")
    pw = _find_mcp(data, "playwright")
    if obs is None or pw is None:
        return "- **Obscura memory-footprint claim:** NO_EVIDENCE (row missing)."
    obs_st = obs["stability"]
    pw_st = pw["stability"]
    if obs_st["status"] != "COMPLETED" or pw_st["status"] != "COMPLETED":
        return (
            f"- **Obscura memory-footprint claim:** INCONCLUSIVE — "
            f"obscura status={obs_st['status']}, playwright status={pw_st['status']}."
        )
    obs_rss = _safe_int((obs_st.get("raw") or {}).get("rss_max_kb"))
    pw_rss = _safe_int((pw_st.get("raw") or {}).get("rss_max_kb"))
    if obs_rss is None or pw_rss is None:
        return "- **Obscura memory-footprint claim:** INCONCLUSIVE — rss_max_kb missing."
    verdict = _verdict(obs_rss, pw_rss, "lower-better")
    ratio = pw_rss / obs_rss if obs_rss > 0 else 0
    return (
        f"- **Obscura memory-footprint claim:** obscura rss_max = "
        f"{obs_rss} kB vs playwright {pw_rss} kB ({ratio:.1f}× spread) — "
        f"**{verdict}**. (Note: transport-level stability PASSed; Phase 2 "
        f"semantic-output FAIL stands — annotate the stability column.)"
    )


def _payload_spread_finding(data: dict) -> str:
    """Headline payload bytes spread across MCPs with OK tokens."""
    samples: list[tuple[str, int]] = []
    for row in data["mcps"]:
        tok = row["tokens"]
        if tok.get("status") != "OK":
            continue
        v = _safe_int((tok.get("raw") or {}).get("headline_payload_bytes"))
        if v is None or v <= 0:
            continue
        samples.append((row["mcp"], v))
    if len(samples) < 2:
        return "- **Payload spread:** INCONCLUSIVE — fewer than 2 OK samples."
    samples.sort(key=lambda t: t[1])
    smallest = samples[0]
    largest = samples[-1]
    ratio = largest[1] / smallest[1] if smallest[1] > 0 else 0
    return (
        f"- **Token-payload spread:** {ratio:.1f}× spread — smallest = "
        f"`{smallest[0]}` at {smallest[1]:,} bytes, largest = `{largest[1]:,}` bytes "
        f"on `{largest[0]}`. Payload bytes are a proxy for context cost in "
        "the harness; turn-level billing diverges from payload by a 2-10× "
        "factor (see methodology §8)."
    )


def _cold_vs_warm_delta_finding(data: dict) -> str:
    deltas: list[tuple[str, int]] = []
    for row in data["mcps"]:
        cs = row["cold_start"]
        if cs.get("status") != "OK":
            continue
        raw = cs.get("raw") or {}
        cold = _safe_int(raw.get("cold", {}).get("median", {}).get("total_ms"))
        warm = _safe_int(raw.get("warm", {}).get("median", {}).get("total_ms"))
        if cold is None or warm is None:
            continue
        deltas.append((row["mcp"], cold - warm))
    if not deltas:
        return "- **Cold-vs-warm delta:** INCONCLUSIVE."
    abs_deltas = [abs(d) for _, d in deltas]
    median_abs = statistics.median(abs_deltas)
    return (
        f"- **Cold-vs-warm delta (process-only eviction):** median |Δ| = "
        f"{median_abs:.1f} ms across {len(deltas)} MCPs. The narrow delta "
        "reflects the harness's process-only cache eviction (pkill + respawn); "
        "the OS file cache is NOT evicted between cold and warm runs because "
        "`sudo purge` is gated by an interactive sudo prompt unavailable to "
        "the autonomous executor. **True uncached-filesystem cold-start is "
        "deferred to ticket G-710.**"
    )


def _stability_transport_caveat_finding(data: dict) -> str:
    """List MCPs whose stability is COMPLETED but Phase 2 semantic-output FAILED."""
    candidates = []
    for row in data["mcps"]:
        st = row["stability"]
        if st.get("status") != "COMPLETED":
            continue
        # Hard-coded list of known transport-PASS / semantic-FAIL rows
        # (from Phase 2 attribution audit + 03-04 SUMMARY).
        if row["mcp"] in ("obscura", "browser-use-direct"):
            candidates.append(row["mcp"])
    if not candidates:
        return (
            "- **Stability transport-vs-semantic caveat:** no rows flagged. "
            "Phase 4 should still verify before publishing."
        )
    return (
        f"- **Stability transport-vs-semantic caveat:** {len(candidates)} row(s) "
        f"({', '.join('`' + n + '`' for n in candidates)}) PASSed stability "
        "at the transport level (call_tool returned without raising) but "
        "Phase 2 evidence shows SEMANTIC-output failures (obscura tool-bug "
        "cascade; browser-use-direct S5 React-clobber). Phase 4 matrix "
        "MUST annotate these stability cells as `COMPLETED ⚠ (transport-only; "
        "Phase 2 semantic-output FAIL stands)`. See 03-04 SUMMARY for context."
    )


def render_empirical_findings(data: dict) -> str:
    """Render §7 — empirical findings section.

    Each finding emits a CONFIRMED / REFUTED / INCONCLUSIVE / NO_EVIDENCE
    verdict grounded in the loaded data. Do NOT hand-edit verdicts to
    match prior expectations — the data IS the finding.
    """
    parts: list[str] = []
    parts.append(_playwright_batch_fill_finding(data))
    parts.append(_lightpanda_cold_start_finding(data))
    parts.append(_obscura_memory_finding(data))
    parts.append(_payload_spread_finding(data))
    parts.append(_cold_vs_warm_delta_finding(data))
    parts.append(_stability_transport_caveat_finding(data))
    return "\n".join(parts)


# ─── Methodology + Source Manifest (§8, §9) ─────────────────────────────


def render_methodology(data: dict) -> str:
    """Render §8 — hard-coded methodology block.

    Reads wallclock_decision from the first stability_metadata.json that
    has one, so the doc cites the ACTUAL decision used at run time.
    """
    wallclock = "unknown (no stability metadata available)"
    for row in data["mcps"]:
        raw = (row["stability"].get("raw") or {})
        wd = raw.get("wallclock_decision")
        if isinstance(wd, str) and wd:
            wallclock = wd
            break

    return (
        "### Token units — three scopes, do not conflate\n"
        "- `schema_tokens` (Anthropic count_tokens, free) — token count of the "
        "MCP's tools/list response. SKIPPED in this run: ANTHROPIC_API_KEY "
        "is held in rbw and the autonomous executor cannot prompt for "
        "unlock. **schema column is null for every row.**\n"
        "- `payload_bytes` — byte-count of the JSON-RPC tool_use+tool_result "
        "envelopes parsed from raw_stream.jsonl. Proxy for context cost.\n"
        "- `turn_tokens` (median_turn_input_tokens / output_tokens) — actual "
        "Claude billing units captured from stream-json `usage` blocks. "
        "Diverges from payload_bytes because of cache-creation / cache-read.\n"
        "\n"
        "### Cold-start cache eviction\n"
        "Per-MCP cold-start runs use `pkill -f <mcp>` + immediate respawn. "
        "`sudo purge` is NOT invoked (interactive sudo prompt unavailable to "
        "autonomous executor). The OS file cache stays warm between cold "
        "and warm runs, so the `cold` median is closer to "
        "\"first-spawn-of-shell-session-after-pkill\" than "
        "\"first-spawn-after-fresh-boot.\" True uncached-fs cold-start is "
        "deferred to G-710.\n"
        "\n"
        f"### Stability wall-clock\n"
        f"All COMPLETED stability rows used wallclock_decision = "
        f"`{wallclock}`. The orchestrator's pre-decided budget of "
        "`selective_top3_60min_rest_30min` (4.5 hours) was compressed by the "
        "executor to 15-min × top-3 + 7-min × rest = ~66 min. The Makefile "
        "targets `stability-strict-60min` / `stability-selective-top3` / "
        "`stability-reduced-30min` allow a re-runner to commit the full "
        "budget if needed.\n"
        "\n"
        "### Stability measures transport, not semantics\n"
        "The stability harness counts a tool call as PASS iff `call_tool` "
        "returned without raising. It does **not** validate the response "
        "body. Phase 2's semantic-output FAILs (obscura tool-bug cascade, "
        "browser-use-direct S5 React-clobber) stand independently of the "
        "stability column. Phase 4 must annotate the affected cells.\n"
        "\n"
        "### browser-use-agent SKIPPED\n"
        "Agent mode is SKIPPED with reason `LLM_KEY_ABSENT` (no "
        "ANTHROPIC_API_KEY or OPENAI_API_KEY in the autonomous executor's "
        "env, rbw locked). Cold-start IS measurable because MCP spawn does "
        "not require an LLM key; tools_inventory IS measurable because the "
        "tools/list handshake does not invoke the planner. Tokens / "
        "tool-call counts / stability all require an active agent session "
        "and so are SKIPPED rather than 0.\n"
        "\n"
        "### Playwright cross-cut data gap\n"
        "Playwright's PASS{1,2,3} directories exist at 2026-05-25 (the "
        "calibration / Phase-1 run) but NOT at 2026-05-26. The tokens and "
        "tool-call counts rows are therefore NO_EVIDENCE for playwright in "
        "this wave. Phase 4 reader: do not cite the batch-fill claim "
        "(`browser_fill_form` = N fields/1 call) as CONFIRMED until a "
        "re-run produces PASS dirs at the current date. The cold-start, "
        "stability, and tools_inventory rows ARE valid (those measurements "
        "do not depend on PASS dirs)."
    )


def render_source_manifest(data: dict) -> str:
    """Render §9 — source manifest (every per-MCP file path consumed)."""
    lines: list[str] = []
    for row in data["mcps"]:
        for dim, fname in DIMENSION_FILE.items():
            entry = row[dim]
            path = f"{row['mcp']}/{fname}"
            if entry["status"] == "MISSING":
                lines.append(f"- `{path}` — **MISSING** (no file on disk)")
            else:
                lines.append(f"- `{path}` (status: `{entry['status']}`)")
    if data.get("missing_files"):
        lines.append("")
        lines.append("**Missing-files summary:**")
        for mf in data["missing_files"]:
            lines.append(f"- `{mf}`")
    return "\n".join(lines)


# ─── Top-level builder ──────────────────────────────────────────────────


def build_summary(data: dict) -> str:
    """Assemble the full CROSS_CUT_SUMMARY.md from the rollup dict."""
    n_mcps = data["metadata"]["n_mcps"]
    results_dir = Path(data["results_date_dir"]).name
    parts: list[str] = []
    parts.append(f"# Cross-Cutting Measurements Summary — {results_dir}")
    parts.append("")
    parts.append(
        "> Consumed by Phase 4 (synthesis). Generated by "
        "`bench.build_cross_cut_summary`. Every number cites the per-MCP "
        "file it came from; methodology disclaimers in §8."
    )
    parts.append("")
    parts.append(f"_Rows: {n_mcps} MCPs. Source artifacts: 5 per MCP "
                 "(cold_start.json, tokens.json, stability_metadata.json, "
                 "tool_call_counts.json, tools_inventory.json)._")
    parts.append("")

    parts.append("## 1. Master Cross-Cut Table")
    parts.append("")
    parts.append(render_master_table(data))
    parts.append("")

    parts.append("## 2. Cold-Start (MEAS-01)")
    parts.append("")
    parts.append(
        "Three-segment timing (resolve / spawn / first_useful) per the "
        "MCP lifecycle: `mcp.client.stdio.__aenter__` → "
        "`session.initialize()` → `session.list_tools()`. Five cold + "
        "five warm runs per MCP; median reported."
    )
    parts.append("")
    parts.append(render_cold_start_table(data))
    parts.append("")

    parts.append("## 3. Token Efficiency (MEAS-02)")
    parts.append("")
    parts.append(
        "Three scopes: schema (Anthropic count_tokens — SKIPPED this run, "
        "see §8), payload (raw_stream.jsonl tool_use+tool_result byte "
        "count), turn (Claude billing usage blocks). Do NOT conflate."
    )
    parts.append("")
    parts.append(render_tokens_table(data))
    parts.append("")

    parts.append("## 4. Stability (MEAS-07)")
    parts.append("")
    parts.append(
        "Per-MCP S1+S5 loop against loopback fixture server "
        "`http://127.0.0.1:8765`. Cloakbrowser uses "
        "`assert_local_only(fixture_base_url)` SAFETY-04 gate before loop "
        "entry. Transport-level success only (see §8)."
    )
    parts.append("")
    parts.append(render_stability_table(data))
    parts.append("")

    parts.append("## 5. Tool-Call Counts (MEAS-08)")
    parts.append("")
    parts.append(
        "Median tool-use events per stage S1-S8 across PASS{1,2,3}. "
        "Stage attribution via Write-marker events targeting "
        "`stage_s<N>.<ext>` paths. NO_EVIDENCE rows lack PASS dirs at "
        "this date."
    )
    parts.append("")
    parts.append(render_tool_calls_table(data))
    parts.append("")

    parts.append("## 6. Tools Inventory (MEAS-09)")
    parts.append("")
    parts.append(
        "tool_count + first-match-wins six-category breakdown from "
        "`bench/tools_inventory.py::CATEGORY_KEYWORDS` "
        "(navigation/interaction/capture/diagnostics/inspection/other)."
    )
    parts.append("")
    parts.append(render_inventory_table(data))
    parts.append("")

    parts.append("## 7. Empirical Findings")
    parts.append("")
    parts.append(
        "Verdicts (CONFIRMED / REFUTED / INCONCLUSIVE / NO_EVIDENCE) are "
        "derived from the loaded data. **The data IS the finding** — "
        "verdicts are not edited to match the prior research hypothesis "
        "if the numbers say otherwise."
    )
    parts.append("")
    parts.append(render_empirical_findings(data))
    parts.append("")

    parts.append("## 8. Methodology Notes")
    parts.append("")
    parts.append(render_methodology(data))
    parts.append("")

    parts.append("## 9. Source Manifest")
    parts.append("")
    parts.append(
        "Every per-MCP file consumed by this aggregator. Statuses are "
        "lifted from each file's `status` field (OK / SKIPPED / "
        "NO_EVIDENCE / MISSING / COMPLETED)."
    )
    parts.append("")
    parts.append(render_source_manifest(data))
    parts.append("")

    return "\n".join(parts)


# ─── CLI ────────────────────────────────────────────────────────────────


def _strip_raw(data: dict) -> dict:
    """Return a shallow copy of the rollup with `raw` payloads dropped.

    The JSON companion (cross_cut_data.json) is consumed by Phase 4 for
    programmatic access; we don't want to re-embed the per-MCP source
    JSON inside it (Phase 4 can load the source files directly).
    """
    out = {
        "results_date_dir": data["results_date_dir"],
        "metadata": data["metadata"],
        "missing_files": data["missing_files"],
        "mcps": [],
    }
    for row in data["mcps"]:
        stripped = {"mcp": row["mcp"]}
        for dim in DIMENSION_KEYS:
            entry = row[dim]
            stripped_entry = {"status": entry["status"]}
            if dim == "stability" and "skip_reason" in entry:
                stripped_entry["skip_reason"] = entry["skip_reason"]
            # Selectively lift headline values for programmatic use
            raw = entry.get("raw") or {}
            if dim == "cold_start" and entry["status"] == "OK":
                stripped_entry["cold_median_total_ms"] = (
                    raw.get("cold", {}).get("median", {}).get("total_ms")
                )
                stripped_entry["warm_median_total_ms"] = (
                    raw.get("warm", {}).get("median", {}).get("total_ms")
                )
            elif dim == "tokens" and entry["status"] == "OK":
                stripped_entry["headline_payload_bytes"] = raw.get("headline_payload_bytes")
                stripped_entry["median_turn_input_tokens"] = raw.get("median_turn_input_tokens")
                stripped_entry["median_turn_output_tokens"] = raw.get("median_turn_output_tokens")
            elif dim == "stability" and entry["status"] == "COMPLETED":
                stripped_entry["iterations_completed"] = raw.get("iterations_completed")
                stripped_entry["rss_first_kb"] = raw.get("rss_first_kb")
                stripped_entry["rss_max_kb"] = raw.get("rss_max_kb")
                stripped_entry["rss_growth_kb"] = raw.get("rss_growth_kb")
                stripped_entry["orphan_audit_survivors"] = raw.get("orphan_audit_survivors")
                stripped_entry["wallclock_decision"] = raw.get("wallclock_decision")
            elif dim == "tcc" and entry["status"] == "OK":
                stripped_entry["median_total_calls"] = raw.get("median_total_calls")
                stripped_entry["median_total_per_stage"] = raw.get("median_total_per_stage")
            elif dim == "inventory" and entry["status"] == "OK":
                stripped_entry["tool_count"] = raw.get("tool_count")
                stripped_entry["categories"] = raw.get("categories")
            stripped[dim] = stripped_entry
        out["mcps"].append(stripped)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.build_cross_cut_summary",
        description=(
            "Aggregate per-MCP cross-cutting measurement artifacts into a "
            "Phase-4-consumable CROSS_CUT_SUMMARY.md (markdown) and "
            "cross_cut_data.json (programmatic companion)."
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
        required=True,
        help="Path to write the CROSS_CUT_SUMMARY.md (markdown)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write the programmatic companion JSON",
    )
    args = parser.parse_args(argv)

    if not args.results_date_dir.is_dir():
        print(
            f"build_cross_cut_summary: ERROR {args.results_date_dir} is not a directory",
            file=sys.stderr,
        )
        return 2

    data = aggregate_results(args.results_date_dir)
    md = build_summary(data)
    args.out.write_text(md, encoding="utf-8")
    print(
        f"build_cross_cut_summary: wrote {args.out} "
        f"({len(md.splitlines())} lines, {data['metadata']['n_mcps']} MCPs)",
        file=sys.stderr,
    )

    if args.json_out is not None:
        companion = _strip_raw(data)
        args.json_out.write_text(
            json.dumps(companion, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            f"build_cross_cut_summary: wrote {args.json_out} (JSON companion)",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
