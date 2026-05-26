"""aggregate_tool_calls — MEAS-08 walker over Phase-2 raw_stream.jsonl evidence.

For each MCP under `results/<date>/<mcp>/`:

  1. If `SKIPPED.md` is present and no `PASS*` directories exist, emit a
     `tool_call_counts.json` with `status: SKIPPED` and the first SKIPPED.md
     line as the reason. (browser-use-agent path.)
  2. Otherwise, for each `PASS1`, `PASS2`, `PASS3` directory present, parse
     `raw_stream.jsonl` line-by-line. Count `tool_use` events appearing
     inside `type==assistant` lines' `message.content[]` blocks. The
     stream_event line that the SDK emits with a duplicate `tool_use`
     content_block_start is NOT counted (would double-count by 2x).
  3. With `--stage-attribution=marker`, attribute each tool_use to S1-S8
     using `Write` events whose `input.file_path` ends in
     `stage_s<N>.<ext>` (where ext is yml/md/png/txt/FAILED/NA/diagnostic.yml).
     Tool uses BEFORE and INCLUDING the Write attribute to that stage.
     With `--stage-attribution=none` (default), counts are flat per pass.
  4. Compute the integer median per stage and per tool across the passes;
     missing tools in a pass count as 0 for the median.
  5. Write `tool_call_counts.json` to `<mcp_dir>/tool_call_counts.json`.

CLI
---
    python -m bench.aggregate_tool_calls <RESULTS_DATE_DIR> \\
        [--mcp <name>] [--stage-attribution {none,marker}]

The aggregator is stdlib-only (no third-party deps) so it can run in any
checkout without `uv sync`.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

# Stage-marker pattern. Matches:
#   stage_s1.yml, stage_s2.md, stage_s8.png, stage_s4.FAILED,
#   stage_s5.NA, stage_s2.diagnostic.yml
# The numeric stage index is captured in group 1.
_STAGE_PATH_RE = re.compile(r"stage_s(\d+)\.[A-Za-z][A-Za-z0-9_.]*$")

# Names of passes we look for. Phase-2 wave uses 3 passes per MCP.
PASS_NAMES = ("PASS1", "PASS2", "PASS3")


# ─── Pure helpers (the surface tests target) ─────────────────────────────


def _iter_assistant_tool_uses(jsonl_path: Path) -> Iterable[dict[str, Any]]:
    """Yield each tool_use content block from `assistant`-typed lines.

    The Claude Code stream emits each tool call twice: once as a
    `stream_event` line (content_block_start) and once inside an
    `assistant` line's `message.content[]` array. Both carry the same
    `id`. We yield from the `assistant` line only — that's the canonical
    block with the full `input` payload. Filtering on assistant also
    naturally excludes built-in stream envelopes (`system`, `user`,
    `result`).

    Malformed lines (non-JSON) are skipped silently per Plan 03-01
    stop_conditions — they're rare and a single bad line should not
    abort the whole aggregation.
    """
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # Plan 03-01 stop_conditions:
                # "raw_stream.jsonl parse error on any pass — log the
                # offending line number, skip that line, continue."
                # Logging happens at the count_tool_uses_in_jsonl boundary
                # so the per-line iteration here stays silent.
                continue
            if obj.get("type") != "assistant":
                continue
            message = obj.get("message") or {}
            for block in message.get("content", []) or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                yield block


def count_tool_uses_in_jsonl(jsonl_path: Path) -> dict[str, int]:
    """Return {tool_name: count} for the entire raw_stream.jsonl.

    No stage attribution. The aggregator entry point uses this when the
    `--stage-attribution=none` flag is set (the default).
    """
    counts: dict[str, int] = {}
    for block in _iter_assistant_tool_uses(jsonl_path):
        name = block.get("name", "<unknown>")
        counts[name] = counts.get(name, 0) + 1
    return counts


def attribute_stages(tool_uses: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Partition a sequence of tool_use blocks into per-stage counters.

    A `Write` tool_use whose `input.file_path` matches `stage_s<N>.<ext>`
    is a STAGE BOUNDARY. Every tool_use seen since the previous boundary,
    including the boundary Write itself, attributes to that stage.

    Tool uses that appear AFTER the last boundary (no further Write to
    `stage_sM`) attribute to the sentinel bucket ``"unattributed"``.
    Tool uses that appear when no boundary has yet been seen (no Write
    at all in the pass) also land in ``"unattributed"``.

    Returns a dict shaped like:
        {"S1": {"navigate": 2, "Write": 1}, "S2": {...}, "unattributed": {...}}
    Empty buckets are omitted.
    """
    per_stage: dict[str, dict[str, int]] = {}
    buffer: list[dict[str, Any]] = []

    def _flush(stage_label: str) -> None:
        bucket = per_stage.setdefault(stage_label, {})
        for blk in buffer:
            n = blk.get("name", "<unknown>")
            bucket[n] = bucket.get(n, 0) + 1
        buffer.clear()

    for block in tool_uses:
        buffer.append(block)
        if block.get("name") != "Write":
            continue
        input_blob = block.get("input") or {}
        file_path = input_blob.get("file_path", "")
        if not isinstance(file_path, str):
            continue
        m = _STAGE_PATH_RE.search(file_path)
        if not m:
            continue
        # Stage boundary — flush the buffer into Sn.
        stage_label = f"S{int(m.group(1))}"
        _flush(stage_label)

    # Any leftover tool uses (no further Write boundary) land in unattributed.
    if buffer:
        _flush("unattributed")

    return per_stage


def median_of_counts(
    passes: dict[str, dict[str, dict[str, int]]],
) -> dict[str, dict[str, int]]:
    """Integer median per stage per tool across passes.

    Args
    ----
    passes
        ``{"PASS1": {"S1": {"tool_x": 2}, ...}, "PASS2": {...}, ...}``

    Returns
    -------
    ``{"S1": {"tool_x": <median>}, ...}``  — missing entries in a pass
    are treated as zero before taking the median, so a tool that appears
    in 2 of 3 passes still contributes a sensible median (rather than
    being dropped or skewed by absence-vs-zero ambiguity).
    """
    # Collect the union of stage labels and per-stage tool names.
    stage_tools: dict[str, set[str]] = {}
    for pass_counts in passes.values():
        for stage, tool_counts in pass_counts.items():
            stage_tools.setdefault(stage, set()).update(tool_counts.keys())

    result: dict[str, dict[str, int]] = {}
    pass_keys = sorted(passes.keys())
    for stage, tools in stage_tools.items():
        result[stage] = {}
        for tool in tools:
            samples = [
                passes[p].get(stage, {}).get(tool, 0) for p in pass_keys
            ]
            # statistics.median returns a float for even-length lists;
            # we round to nearest int for stable JSON output. With three
            # passes the median is always one of the samples (no rounding
            # ambiguity), but we round anyway to keep the JSON tidy.
            result[stage][tool] = int(round(statistics.median(samples)))
    return result


# ─── Per-MCP aggregation ─────────────────────────────────────────────────


def _read_first_nonblank_line(p: Path) -> str:
    """Return the first non-blank, non-comment line of a small markdown file."""
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
        # Fallback: very first line (even if it was a heading).
        text = p.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip():
                return line.strip()
    except OSError:
        pass
    return ""


def aggregate_mcp(
    mcp_dir: Path,
    *,
    stage_attribution: str = "none",
) -> dict[str, Any]:
    """Aggregate one MCP's tool-call counts; return the JSON-ready dict.

    `mcp_dir` is the per-MCP directory under `results/<date>/`.
    The function does NOT write to disk — the CLI layer does that, so
    tests can introspect the dict directly.
    """
    mcp_name = mcp_dir.name
    skipped_md = mcp_dir / "SKIPPED.md"
    pass_dirs = [mcp_dir / p for p in PASS_NAMES if (mcp_dir / p).is_dir()]

    if not pass_dirs and skipped_md.exists():
        reason = _read_first_nonblank_line(skipped_md) or "SKIPPED (no reason captured)"
        return {
            "mcp": mcp_name,
            "status": "SKIPPED",
            "reason": reason,
            "stage_attribution_mode": stage_attribution,
        }

    if not pass_dirs:
        # No PASS* and no SKIPPED.md — surface a NO_EVIDENCE row so the
        # downstream consumer can flag it.
        return {
            "mcp": mcp_name,
            "status": "NO_EVIDENCE",
            "reason": (
                "No PASS{1,2,3} directories and no SKIPPED.md found in "
                f"{mcp_dir.name}."
            ),
            "stage_attribution_mode": stage_attribution,
        }

    passes: dict[str, dict[str, dict[str, int]]] = {}
    total_calls_per_pass: dict[str, int] = {}
    parse_errors: dict[str, int] = {}

    for pass_dir in pass_dirs:
        jsonl = pass_dir / "raw_stream.jsonl"
        pass_name = pass_dir.name
        if not jsonl.exists():
            # The pass dir exists but no raw_stream.jsonl — record as empty.
            passes[pass_name] = {}
            total_calls_per_pass[pass_name] = 0
            continue

        # Collect all assistant tool_use blocks, tally any parse errors.
        tool_uses: list[dict[str, Any]] = []
        line_errors = 0
        with jsonl.open("r", encoding="utf-8") as f:
            for ln_no, raw in enumerate(f, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    line_errors += 1
                    print(
                        f"aggregate_tool_calls: WARN parse error "
                        f"{jsonl}:{ln_no} (skipped)",
                        file=sys.stderr,
                    )
                    continue
                if obj.get("type") != "assistant":
                    continue
                for block in (obj.get("message") or {}).get("content", []) or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_uses.append(block)
        if line_errors:
            parse_errors[pass_name] = line_errors

        if stage_attribution == "marker":
            passes[pass_name] = attribute_stages(tool_uses)
        else:
            # Flat: single "unattributed" bucket holds the whole pass.
            flat: dict[str, int] = {}
            for block in tool_uses:
                n = block.get("name", "<unknown>")
                flat[n] = flat.get(n, 0) + 1
            passes[pass_name] = {"unattributed": flat}

        total_calls_per_pass[pass_name] = len(tool_uses)

    median_per_stage = median_of_counts(passes)
    # Convenience: per-stage totals (sum of all tool counts in the median).
    median_total_per_stage = {
        stage: sum(tool_counts.values())
        for stage, tool_counts in median_per_stage.items()
    }
    median_total = int(round(statistics.median(
        sorted(total_calls_per_pass.values()) or [0]
    )))

    out: dict[str, Any] = {
        "mcp": mcp_name,
        "status": "OK",
        "stage_attribution_mode": stage_attribution,
        "passes": passes,
        "median_per_stage": median_per_stage,
        "median_total_per_stage": median_total_per_stage,
        "total_calls_per_pass": total_calls_per_pass,
        "median_total_calls": median_total,
        "interesting": {
            # Populated by plan 03-05 synthesis using stage_s5.* artifacts
            # (count of fields filled). Kept here so the schema is stable.
            "s5_calls_per_field_filled": None,
        },
    }
    if parse_errors:
        out["parse_errors_per_pass"] = parse_errors
    return out


# ─── CLI ─────────────────────────────────────────────────────────────────


def _iter_mcp_dirs(results_date_dir: Path, mcp_filter: str | None) -> list[Path]:
    """Return the per-MCP subdirectories under `results_date_dir`.

    Filters out files (CAPABILITY_MATRIX.md, scores.json, etc.). If
    `mcp_filter` is set, return ONLY that subdir (must exist).
    """
    if mcp_filter:
        candidate = results_date_dir / mcp_filter
        if not candidate.is_dir():
            raise FileNotFoundError(
                f"--mcp filter {mcp_filter!r} does not match any dir under "
                f"{results_date_dir}"
            )
        return [candidate]
    return sorted(
        child for child in results_date_dir.iterdir()
        if child.is_dir() and not child.name.startswith(".")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.aggregate_tool_calls",
        description=(
            "Walk results/<date>/<mcp>/PASS{1,2,3}/raw_stream.jsonl, count "
            "tool_use events per stage S1-S8 (via Write-marker attribution), "
            "and write per-MCP tool_call_counts.json."
        ),
    )
    parser.add_argument(
        "results_date_dir",
        type=Path,
        help="e.g. results/2026-05-26",
    )
    parser.add_argument(
        "--mcp",
        type=str,
        default=None,
        help="Restrict to a single MCP (subdir name) under results_date_dir.",
    )
    parser.add_argument(
        "--stage-attribution",
        choices=("none", "marker"),
        default="marker",
        help=(
            "Attribute tool_use events to S1-S8 stages using Write-marker "
            "events (default: marker). Use 'none' for flat counts."
        ),
    )
    args = parser.parse_args(argv)

    if not args.results_date_dir.is_dir():
        print(
            f"aggregate_tool_calls: ERROR {args.results_date_dir} is not a directory",
            file=sys.stderr,
        )
        return 2

    mcp_dirs = _iter_mcp_dirs(args.results_date_dir, args.mcp)
    failures: list[str] = []
    for mcp_dir in mcp_dirs:
        try:
            result = aggregate_mcp(
                mcp_dir,
                stage_attribution=args.stage_attribution,
            )
        except Exception as exc:  # noqa: BLE001 — keep aggregation going
            failures.append(f"{mcp_dir.name}: {type(exc).__name__}: {exc}")
            print(
                f"aggregate_tool_calls: ERROR {mcp_dir.name}: {exc}",
                file=sys.stderr,
            )
            continue

        out_path = mcp_dir / "tool_call_counts.json"
        out_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            f"aggregate_tool_calls: {mcp_dir.name} -> {out_path} "
            f"(status={result.get('status')}, "
            f"median_total_calls={result.get('median_total_calls', 'n/a')})",
            file=sys.stderr,
        )

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
