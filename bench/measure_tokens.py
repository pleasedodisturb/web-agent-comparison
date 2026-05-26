"""measure_tokens — MEAS-02 3-scope token efficiency aggregator.

Plan 03-02 splits token efficiency into three scopes that the 2026-03 wave
conflated:

  * ``schema``  — tokens Claude pays just to know the MCP's ``tools/list``
                  surface, sourced from Anthropic SDK ``count_tokens()``
                  (free, no billing impact). Static per MCP.
  * ``payload`` — bytes of JSON-RPC ``tool_use.input`` +
                  ``tool_result.content`` payloads, parsed from Phase 2's
                  ``raw_stream.jsonl``. Byte count (proxy for token cost).
                  Per-stage, per-pass. **This is the Phase-4 headline column.**
  * ``turn``    — ``usage.{input_tokens,output_tokens,...}`` extracted from
                  the ``result``-typed stream-json envelope already captured
                  in Phase 1. Per-pass actual Claude billing cost.

For each MCP under ``<results_date>/<mcp>/`` the aggregator:

  1. Reads any existing Phase-1 ``tokens.json`` stub (it carries the captured
     ``turn`` block — we reuse it rather than re-extract).
  2. Walks ``PASS{1,2,3}/raw_stream.jsonl`` to compute payload bytes per
     stage (Write-marker attribution mirrors ``bench/aggregate_tool_calls``)
     and, if the stub's ``turn`` block is missing for a given pass, recovers
     it from the terminal ``result`` envelope.
  3. Calls ``count_tokens()`` once per MCP (baseline + with-tools) and
     attributes the delta to ``schema_tokens``. ``--skip-schema`` and a
     missing ``ANTHROPIC_API_KEY`` both fall through to ``schema_tokens=null``
     with a note recorded.
  4. Writes ``tokens.json`` overwriting any deferred stub. The ``deferred``
     key is removed on success.

CLI
---
    python -m bench.measure_tokens <results_date_dir> \\
        [--mcp <name>] [--model claude-opus-4-7] [--skip-schema]

Methodology disclosure
----------------------
``schema`` is **Anthropic-tokenizer-counted**; ``payload`` is **byte-counted**
(proxy for token cost); ``turn`` is **actual Claude billing**. The three units
are NOT directly comparable — Phase 4 synthesis must keep them separate.
This note is embedded in every ``tokens.json`` ``notes`` field per
03-CONTEXT.md decisions.

Anti-pattern guard
------------------
We do NOT call ``count_tokens()`` on raw_stream content. ``payload`` scope is
deliberately a byte count, not a token count, because tokenizing every
``tool_use.input`` and ``tool_result.content`` would (a) cost N API calls per
MCP, and (b) conflate two units in the published column.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

# Re-use the stage-marker regex from aggregate_tool_calls. The pattern accepts
# any non-zero-length suffix (yml/md/png/txt/FAILED/NA/diagnostic.yml) so
# failure-row stage markers also act as boundaries.
_STAGE_PATH_RE = re.compile(r"stage_s(\d+)\.[A-Za-z][A-Za-z0-9_.]*$")
PASS_NAMES = ("PASS1", "PASS2", "PASS3")

# The note string embedded in every tokens.json's `notes` array; documents
# the three-unit caveat the Phase-4 synthesis must respect.
METHODOLOGY_NOTE = (
    "schema = Anthropic-tokenizer-counted (count_tokens); "
    "payload = byte-count (proxy for tokens); "
    "turn = actual Claude billing — three units, do not conflate."
)


# ─── Pure helpers (test surface) ─────────────────────────────────────────


def _safe_jsonl_iter(jsonl_path: Path) -> Iterable[dict[str, Any]]:
    """Yield parsed JSON objects from a JSONL file, skipping malformed lines.

    Plan 03-02 stop_conditions say to skip individual parse errors and
    record a warning if >5 % of lines failed. The fraction tracking lives
    in the caller; this helper just yields whatever parsed cleanly.
    """
    if not jsonl_path.exists():
        return
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def extract_payload_bytes_per_pass(jsonl_path: Path) -> dict[str, int]:
    """Return ``{stage: bytes}`` for one raw_stream.jsonl.

    Walks the stream in order, tracking the "current stage" (last Write-marker
    target). For each ``assistant`` line iterate ``content[]``; for each
    ``tool_use`` add ``len(json.dumps(input).encode())``. For each ``user``
    line iterate ``content[]``; for each ``tool_result`` add
    ``len(json.dumps(content).encode())``.

    A ``Write`` whose ``input.file_path`` matches ``stage_s<N>.<ext>`` is a
    stage boundary; the Write's own input bytes attribute to that stage
    (matching the inclusive convention of ``aggregate_tool_calls``).
    Bytes seen before the first stage marker attribute to ``"unattributed"``.

    Returns a dict whose keys are ``"S1"``..``"S8"`` (and possibly
    ``"unattributed"``) and whose values are integer byte counts.
    """
    per_stage: dict[str, int] = {}
    current_stage: str | None = None
    # Buffer to attribute pending bytes that arrived BEFORE we saw any stage
    # marker. Once we see a marker, the buffer flushes to that stage (so the
    # tool_use that ARRIVED before the Write attributes to the same stage as
    # the Write — same inclusive convention as 03-01).
    pending: int = 0

    def _add(label: str, n: int) -> None:
        if n <= 0:
            return
        per_stage[label] = per_stage.get(label, 0) + n

    for obj in _safe_jsonl_iter(jsonl_path):
        t = obj.get("type")
        if t == "assistant":
            for block in (obj.get("message") or {}).get("content", []) or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                input_blob = block.get("input") or {}
                n_bytes = len(json.dumps(input_blob).encode("utf-8"))
                # Check if this is a stage-marker Write.
                stage_label = None
                if block.get("name") == "Write":
                    fp = (input_blob or {}).get("file_path", "")
                    if isinstance(fp, str):
                        m = _STAGE_PATH_RE.search(fp)
                        if m:
                            stage_label = f"S{int(m.group(1))}"
                if stage_label is not None:
                    # Flush pending into this stage, plus this Write's input.
                    _add(stage_label, pending + n_bytes)
                    pending = 0
                    current_stage = stage_label
                else:
                    if current_stage is None:
                        pending += n_bytes
                    else:
                        _add(current_stage, n_bytes)
        elif t == "user":
            for block in (obj.get("message") or {}).get("content", []) or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_result":
                    continue
                content = block.get("content")
                n_bytes = len(json.dumps(content).encode("utf-8"))
                if current_stage is None:
                    pending += n_bytes
                else:
                    _add(current_stage, n_bytes)

    # Any leftover bytes that never landed inside a stage.
    if pending > 0:
        _add("unattributed", pending)

    return per_stage


def extract_turn_usage_from_jsonl(jsonl_path: Path) -> dict[str, Any] | None:
    """Return the LAST ``{type:"result"}`` envelope's ``.usage`` dict.

    Mirrors the Phase-1 jq logic in ``scripts/run_mcp_session.sh`` step 13.
    Returns ``None`` if no result envelope was found or its usage is absent.
    """
    last_usage: dict[str, Any] | None = None
    for obj in _safe_jsonl_iter(jsonl_path):
        if obj.get("type") == "result":
            u = obj.get("usage")
            if isinstance(u, dict):
                last_usage = u
    return last_usage


def median_payload_bytes(passes: dict[str, dict[str, int]]) -> dict[str, int]:
    """Integer median per stage across passes; missing-stage = 0.

    Mirrors the 03-01 ``median_of_counts`` convention so the two
    aggregators stay aligned: a stage that's absent from one pass counts
    as 0 for the median calculation (rather than being dropped).
    """
    if not passes:
        return {}
    stage_set: set[str] = set()
    for p in passes.values():
        stage_set.update(p.keys())
    pass_keys = sorted(passes.keys())
    result: dict[str, int] = {}
    for stage in stage_set:
        samples = [passes[p].get(stage, 0) for p in pass_keys]
        result[stage] = int(round(statistics.median(samples)))
    return result


def build_anthropic_tools_schema(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a Phase-2 ``tools_inventory.json`` body to Anthropic's tools shape.

    Anthropic ``count_tokens(tools=[...])`` expects each tool as::

        {"name": "...", "description": "...", "input_schema": {
            "type": "object",
            "properties": {<key>: {} for key in input_schema_keys}
        }}

    The original ``input_schema`` per-property types are unknown to us (the
    Phase-1 probe only captured key NAMES, not value-types). Passing empty
    property dicts still tokenizes faithfully — count_tokens cares about the
    JSON-stringified schema, and an empty object is the smallest valid one.
    """
    schema: list[dict[str, Any]] = []
    for tool in inventory.get("tools", []) or []:
        name = tool.get("name") or "<unknown>"
        desc = tool.get("description_excerpt") or ""
        keys = tool.get("input_schema_keys") or []
        properties = {k: {} for k in keys}
        schema.append({
            "name": name,
            "description": desc,
            "input_schema": {
                "type": "object",
                "properties": properties,
            },
        })
    return schema


# ─── Per-MCP aggregation ─────────────────────────────────────────────────


def _read_existing_stub(mcp_dir: Path) -> dict[str, Any] | None:
    p = mcp_dir / "tokens.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _read_first_nonblank_line(p: Path) -> str:
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
        text = p.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip():
                return line.strip()
    except OSError:
        pass
    return ""


def _call_count_tokens_with_retry(
    fn: Callable[..., Any],
    *,
    model: str,
    tools: list[dict[str, Any]] | None,
    max_attempts: int = 3,
) -> int | None:
    """Invoke ``count_tokens()`` with bounded backoff.

    Per Plan 03-02 stop_conditions: 3 attempts with 2/4/8s backoff. Returns
    the integer ``input_tokens`` count, or ``None`` if all attempts failed.
    """
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
    }
    if tools is not None:
        body["tools"] = tools

    sleep_secs = [0, 2, 4, 8]
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        if sleep_secs[attempt]:
            time.sleep(sleep_secs[attempt])
        try:
            resp = fn(**body)
            # Accept both real Anthropic objects (.input_tokens) and dicts.
            if hasattr(resp, "input_tokens"):
                return int(resp.input_tokens)
            if isinstance(resp, dict) and "input_tokens" in resp:
                return int(resp["input_tokens"])
            raise RuntimeError(
                f"count_tokens returned unexpected shape: {type(resp).__name__}"
            )
        except Exception as exc:  # noqa: BLE001 — retry-on-anything per stop_conditions
            last_exc = exc
            continue
    if last_exc is not None:
        print(
            f"measure_tokens: WARN count_tokens failed after {max_attempts} "
            f"attempts ({type(last_exc).__name__}: {last_exc})",
            file=sys.stderr,
        )
    return None


def aggregate_mcp(
    mcp_dir: Path,
    *,
    count_tokens_fn: Callable[..., Any] | None,
    model: str = "claude-opus-4-7",
) -> dict[str, Any]:
    """Aggregate one MCP's 3-scope token efficiency record.

    Parameters
    ----------
    mcp_dir
        Per-MCP directory under ``results/<date>/``.
    count_tokens_fn
        Callable used to count schema tokens. The CLI wires this to
        ``anthropic.Anthropic().messages.count_tokens``; tests inject a
        mock. ``None`` means skip schema scope (``--skip-schema`` or
        missing ``ANTHROPIC_API_KEY``).
    model
        Model name string passed to ``count_tokens``. Recorded in the
        output as ``schema_model``.
    """
    mcp_name = mcp_dir.name
    notes: list[str] = [METHODOLOGY_NOTE]

    skipped_md = mcp_dir / "SKIPPED.md"
    pass_dirs = [mcp_dir / p for p in PASS_NAMES if (mcp_dir / p).is_dir()]
    existing_stub = _read_existing_stub(mcp_dir)
    inventory_path = mcp_dir / "tools_inventory.json"

    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── SKIPPED path: only SKIPPED.md, no PASS dirs.
    if not pass_dirs and skipped_md.exists():
        reason = _read_first_nonblank_line(skipped_md) or "SKIPPED (no reason captured)"
        out: dict[str, Any] = {
            "mcp": mcp_name,
            "captured_at": captured_at,
            "status": "SKIPPED",
            "reason": reason,
            "scope": "skipped",
            "schema_tokens": None,
            "payload_bytes_per_stage": {},
            "median_payload_bytes_per_stage": {},
            "median_total_payload_bytes": None,
            "turn_tokens_per_pass": {},
            "median_turn_input_tokens": None,
            "median_turn_output_tokens": None,
            "headline_payload_bytes": None,
            "notes": notes,
        }
        return out

    # ── NO_EVIDENCE path: no PASS dirs, no SKIPPED.md.
    if not pass_dirs:
        # Playwright lives at results/2026-05-25/ — surface the gap cleanly.
        notes.append(
            "No PASS{1,2,3} directories under "
            f"{mcp_dir}/ — payload + turn scopes pending re-scoring. "
            "If this MCP was scored in a sibling date dir, the aggregator "
            "must be pointed there explicitly via --mcp + a different "
            "results_date_dir argument."
        )
        return {
            "mcp": mcp_name,
            "captured_at": captured_at,
            "status": "NO_EVIDENCE",
            "scope": "no-evidence",
            "schema_tokens": None,
            "payload_bytes_per_stage": {},
            "median_payload_bytes_per_stage": {},
            "median_total_payload_bytes": None,
            "turn_tokens_per_pass": {},
            "median_turn_input_tokens": None,
            "median_turn_output_tokens": None,
            "headline_payload_bytes": None,
            "notes": notes,
        }

    # ── Payload bytes per pass.
    payload_bytes_per_pass: dict[str, dict[str, int]] = {}
    turn_per_pass: dict[str, dict[str, Any] | None] = {}

    for pass_dir in pass_dirs:
        pass_name = pass_dir.name
        jsonl = pass_dir / "raw_stream.jsonl"

        if jsonl.exists() and jsonl.stat().st_size > 0:
            payload_bytes_per_pass[pass_name] = extract_payload_bytes_per_pass(jsonl)
            turn_per_pass[pass_name] = extract_turn_usage_from_jsonl(jsonl)
        else:
            payload_bytes_per_pass[pass_name] = {}
            turn_per_pass[pass_name] = None

    # ── Turn-block fallback: if a pass's raw_stream lacks a result envelope
    #    but the existing Phase-1 stub captured one, reuse it. This is the
    #    "stub overwrite reuses turn block" contract from Test 6.
    if existing_stub and isinstance(existing_stub.get("turn"), dict):
        stub_turn = existing_stub["turn"]
        for pass_name in PASS_NAMES:
            if pass_name in turn_per_pass and turn_per_pass[pass_name] is None:
                turn_per_pass[pass_name] = stub_turn

    # ── Median payload bytes per stage.
    median_per_stage = median_payload_bytes(payload_bytes_per_pass)
    # Drop "unattributed" from the headline so payload-bytes published
    # totals don't get polluted by early-crash leakage (a known-noisy bucket
    # per 03-01 SUMMARY). It's still visible in payload_bytes_per_stage.
    median_for_headline = {
        k: v for k, v in median_per_stage.items() if k != "unattributed"
    }
    median_total_payload = sum(median_for_headline.values())

    # ── Per-pass turn medians.
    pass_turns_with_data = [
        v for v in turn_per_pass.values() if isinstance(v, dict)
    ]
    median_turn_input = None
    median_turn_output = None
    if pass_turns_with_data:
        inputs = [int(t.get("input_tokens") or 0) for t in pass_turns_with_data]
        outputs = [int(t.get("output_tokens") or 0) for t in pass_turns_with_data]
        if inputs:
            median_turn_input = int(round(statistics.median(inputs)))
        if outputs:
            median_turn_output = int(round(statistics.median(outputs)))

    # ── Schema scope.
    schema_tokens: int | None = None
    schema_source: str | None = None
    schema_baseline: int | None = None
    schema_with_tools: int | None = None

    if count_tokens_fn is not None and inventory_path.exists():
        try:
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            notes.append(f"tools_inventory.json unreadable: {exc}")
            inventory = None

        if inventory is not None:
            inv_status = inventory.get("status")
            if inv_status and inv_status != "OK":
                notes.append(
                    f"tools_inventory.json status={inv_status!r}; "
                    "schema scope unavailable (no tool list captured)"
                )
            else:
                tools_schema = build_anthropic_tools_schema(inventory)
                baseline = _call_count_tokens_with_retry(
                    count_tokens_fn, model=model, tools=None
                )
                with_tools = _call_count_tokens_with_retry(
                    count_tokens_fn, model=model, tools=tools_schema
                )
                if baseline is not None and with_tools is not None:
                    schema_tokens = with_tools - baseline
                    schema_baseline = baseline
                    schema_with_tools = with_tools
                    schema_source = "anthropic.count_tokens"
                else:
                    notes.append(
                        "count_tokens failed for one or both calls; "
                        "schema scope unavailable"
                    )
    elif count_tokens_fn is None:
        notes.append("schema scope unavailable: --skip-schema or ANTHROPIC_API_KEY absent")
    elif not inventory_path.exists():
        notes.append(
            f"tools_inventory.json missing under {mcp_dir} — schema scope unavailable"
        )

    # ── Compose output.
    out: dict[str, Any] = {
        "mcp": mcp_name,
        "captured_at": captured_at,
        "status": "OK",
        "scope": "schema+payload+turn",
        "schema_tokens": schema_tokens,
        "schema_source": schema_source,
        "schema_model": model if schema_tokens is not None else None,
        "schema_baseline_tokens": schema_baseline,
        "schema_with_tools_tokens": schema_with_tools,
        "payload_bytes_per_stage": payload_bytes_per_pass,
        "median_payload_bytes_per_stage": median_for_headline,
        "median_total_payload_bytes": median_total_payload,
        "turn_tokens_per_pass": {
            k: (v if isinstance(v, dict) else None) for k, v in turn_per_pass.items()
        },
        "median_turn_input_tokens": median_turn_input,
        "median_turn_output_tokens": median_turn_output,
        "headline_payload_bytes": median_total_payload,
        "notes": notes,
    }
    return out


# ─── CLI ─────────────────────────────────────────────────────────────────


def _iter_mcp_dirs(results_date_dir: Path, mcp_filter: str | None) -> list[Path]:
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


def _build_live_count_tokens(model: str) -> Callable[..., Any] | None:
    """Return a callable that hits the real Anthropic count_tokens endpoint.

    If ``ANTHROPIC_API_KEY`` is unset, returns ``None`` so the aggregator
    falls through to ``schema_tokens=null`` with a note.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic  # noqa: PLC0415 — lazy import keeps tests anthropic-free
    except ImportError:
        print(
            "measure_tokens: WARN anthropic SDK not installed — schema scope unavailable",
            file=sys.stderr,
        )
        return None
    client = anthropic.Anthropic()

    def _fn(**kwargs: Any) -> Any:
        return client.messages.count_tokens(**kwargs)

    return _fn


# browser-use deduplication: schema_tokens for browser-use-direct and
# browser-use-agent are the same number (same tools surface). We compute
# direct first; when agent runs, we COPY schema_tokens over.
def _share_browser_use_schema(results: dict[str, dict[str, Any]]) -> None:
    direct = results.get("browser-use-direct")
    agent = results.get("browser-use-agent")
    if not direct or not agent:
        return
    if direct.get("schema_tokens") is not None and agent.get("schema_tokens") is None:
        agent["schema_tokens"] = direct["schema_tokens"]
        agent["schema_source"] = direct.get("schema_source")
        agent["schema_model"] = direct.get("schema_model")
        agent["schema_baseline_tokens"] = direct.get("schema_baseline_tokens")
        agent["schema_with_tools_tokens"] = direct.get("schema_with_tools_tokens")
        notes = agent.setdefault("notes", [])
        notes.append(
            "schema_tokens copied from browser-use-direct (same tools surface; "
            "browser-use-agent mode diverges at session runtime, not at handshake)"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.measure_tokens",
        description=(
            "MEAS-02 3-scope token-efficiency aggregator. Reads Phase-2 "
            "raw_stream.jsonl + tools_inventory.json + Phase-1 tokens.json "
            "stubs; writes per-MCP tokens.json carrying schema, payload, "
            "and turn scopes."
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
        help="Restrict to a single MCP subdir name.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-opus-4-7",
        help="Model name passed to count_tokens (default: claude-opus-4-7).",
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip the schema scope (no count_tokens calls). Use when "
             "ANTHROPIC_API_KEY is absent or for offline runs.",
    )
    args = parser.parse_args(argv)

    if not args.results_date_dir.is_dir():
        print(
            f"measure_tokens: ERROR {args.results_date_dir} is not a directory",
            file=sys.stderr,
        )
        return 2

    count_tokens_fn: Callable[..., Any] | None
    if args.skip_schema:
        count_tokens_fn = None
        print("measure_tokens: --skip-schema set; schema scope disabled", file=sys.stderr)
    else:
        count_tokens_fn = _build_live_count_tokens(args.model)
        if count_tokens_fn is None:
            print(
                "measure_tokens: ANTHROPIC_API_KEY absent or SDK missing; "
                "schema scope will be null. Re-run with the key set to "
                "populate schema_tokens.",
                file=sys.stderr,
            )

    mcp_dirs = _iter_mcp_dirs(args.results_date_dir, args.mcp)
    results_by_name: dict[str, dict[str, Any]] = {}
    failures: list[str] = []

    for mcp_dir in mcp_dirs:
        try:
            record = aggregate_mcp(
                mcp_dir,
                count_tokens_fn=count_tokens_fn,
                model=args.model,
            )
        except Exception as exc:  # noqa: BLE001 — keep aggregation going
            failures.append(f"{mcp_dir.name}: {type(exc).__name__}: {exc}")
            print(
                f"measure_tokens: ERROR {mcp_dir.name}: {exc}",
                file=sys.stderr,
            )
            continue
        results_by_name[mcp_dir.name] = record

    # browser-use schema sharing.
    _share_browser_use_schema(results_by_name)

    for mcp_name, record in results_by_name.items():
        out_path = args.results_date_dir / mcp_name / "tokens.json"
        out_path.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        headline = record.get("headline_payload_bytes")
        schema = record.get("schema_tokens")
        status = record.get("status")
        print(
            f"measure_tokens: {mcp_name} -> {out_path} "
            f"(status={status} payload={headline} schema={schema})",
            file=sys.stderr,
        )

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
