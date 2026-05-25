"""tools_inventory — spawn an MCP, call tools/list, categorize, persist.

This is the only **real** measurement that lands in plan 01-06 (the other
three Phase-1-deferred files are stubs via `bench.stub_writers`). For each
MCP under test we:

  1. Read `.mcp.json` to recover the `command` + `args`.
  2. Spawn the server via `mcp.client.stdio.stdio_client` (Python SDK 1.16).
  3. Run `initialize` (handshake), capture the server's reported version
     string (when present).
  4. Run `tools/list`, capture every tool name + description.
  5. Categorize each tool into one of 6 buckets following the scheme used
     by `chrome-devtools-mcp` (navigation / inspection / interaction /
     capture / diagnostics / other).
  6. Write `tools_inventory.json` to the MCP's evidence directory.

If the server fails to initialize within 30 s, we write
`{"status": "INITIALIZE_TIMEOUT", "error": "..."}` and EXIT NONZERO so
the harness can flag the row as `tool-bug` per FAIRNESS-06. **We do not
crash** — initialize timeouts are exactly the failure mode the benchmark
needs to surface (browser-use v0.12.7 had a documented one as of
2026-05-21; the wave needs to confirm or refute that on the current
version).

Version-string gotcha
---------------------
Some MCPs (lightpanda specifically, per browser-tools.md 2026-05-21
verification) report inconsistent version strings: the binary header
self-identifies as `0.3.0` while the JSON-RPC handshake says `0.1.0`.
This module captures BOTH where possible:

  - `version_handshake` — what `initialize.serverInfo.version` returns.
  - `version_binary`    — the basename version surfaced by `--version`
                          (recorded by `bench.capture_versions`, not here;
                          this module only knows the handshake side).

Don't pick one. Record both. The eventual reproducibility audit reads
both fields.

CLI
---
    python -m bench.tools_inventory <MCP_NAME> --out <PATH>

Where `<MCP_NAME>` is a key in `.mcp.json` and `<PATH>` is where the JSON
should be written (typically `<OUT_DIR>/tools_inventory.json`).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# The MCP Python SDK provides an async stdio client that handles the
# JSON-RPC framing for us. We use the high-level `ClientSession` for
# `initialize` + `tools/list` because the low-level RPC types churn faster
# than the high-level API. SDK pinned to 1.16.x in pyproject.toml.
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# Hard timeout for the initialize+tools/list round-trip. The plan
# (01-06 task 3) specifies 30 s; browser-use v0.12.7's known initialize
# timeout was the motivating case. Anything above 30 s indicates the MCP
# is wedged, not slow.
INITIALIZE_TIMEOUT_S = 30.0

# Repo-relative path to the project-scope MCP config file. The harness
# always reads from this file (per CONTEXT.md "Project-scope `.mcp.json`
# not user-scope per G-688 lesson").
DEFAULT_MCP_JSON = Path(__file__).resolve().parent.parent / ".mcp.json"


# ─── Categorization ──────────────────────────────────────────────────────
#
# Six categories chosen to mirror `chrome-devtools-mcp`'s scheme, which is
# the most rigorously-categorized of the 7 candidates and aligns with
# `scoring/rubric.md`'s dimension names. The keyword lists are case-
# insensitive substring matches; the FIRST category that matches wins, so
# order matters. `other` is the catch-all when nothing matches — the JSON
# output flags any uncategorized tools so a human can spot-check.

# Each tuple is (category_name, list_of_keywords_or_substrings). Matching
# is case-insensitive. A tool name like "browser_navigate" matches the
# "navigation" bucket via the "navigate" keyword.
CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    # Navigation: goto/back/forward/reload (and the "navigate" verb).
    ("navigation", ["navigate", "goto", "go_to", "back", "forward", "reload",
                    "open_url", "visit"]),
    # Interaction: clicks, typing, form interaction, drag/hover, file
    # upload/drop. Checked BEFORE inspection so "click_and_capture"-style
    # names land here.
    ("interaction", ["click", "type", "fill", "press", "select", "drag",
                     "drop", "hover", "submit", "scroll", "tap", "input",
                     "focus", "blur", "wait_for", "upload", "run_code"]),
    # Capture: screenshots, PDFs, recordings.
    ("capture", ["screenshot", "screen_shot", "pdf", "record", "video",
                 "capture_image"]),
    # Diagnostics: dev-tools-style introspection (console, network, perf,
    # traces). Note `evaluate` lands here because it's commonly used for
    # JS-runtime inspection — Playwright's `evaluate` is also borderline-
    # interaction but the rubric tradition (chrome-devtools-mcp) puts it
    # under diagnostics.
    ("diagnostics", ["console", "network", "trace", "performance",
                     "evaluate", "lighthouse", "metrics", "log",
                     "request", "response", "har"]),
    # Inspection: read-only state probes. Checked LAST among non-other
    # buckets so "screenshot_and_snapshot" lands in capture, not here.
    ("inspection", ["snapshot", "read", "extract", "get_state", "scrape",
                    "markdown", "html", "content", "list", "describe",
                    "inspect", "query", "find", "search"]),
]

CATEGORY_NAMES = [name for name, _ in CATEGORY_KEYWORDS] + ["other"]


def categorize_tool(tool_name: str) -> str:
    """Classify a tool name into one of CATEGORY_NAMES.

    First-match-wins on the CATEGORY_KEYWORDS table. Returns ``"other"``
    if nothing matches. The match is case-insensitive substring on the
    tool name (NOT on the description — descriptions are too noisy and
    a single-line keyword like "click" in a description would force
    everything into the interaction bucket).
    """
    lower = tool_name.lower()
    for category, keywords in CATEGORY_KEYWORDS:
        for keyword in keywords:
            if keyword in lower:
                return category
    return "other"


# ─── .mcp.json loader ────────────────────────────────────────────────────


@dataclass
class McpSpec:
    """Resolved spawn parameters for an MCP server from .mcp.json."""

    name: str
    command: str
    args: list[str]
    env: dict[str, str]


def load_mcp_spec(mcp_name: str, mcp_json_path: Path = DEFAULT_MCP_JSON) -> McpSpec:
    """Read .mcp.json and return spawn parameters for `mcp_name`.

    Raises
    ------
    KeyError
        If `mcp_name` is not a key under `mcpServers`.
    FileNotFoundError
        If `mcp_json_path` doesn't exist.
    """
    if not mcp_json_path.exists():
        raise FileNotFoundError(f"MCP config not found: {mcp_json_path}")

    config = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    servers = config.get("mcpServers", {})
    if mcp_name not in servers:
        raise KeyError(
            f"{mcp_name!r} not in .mcp.json; available: "
            f"{sorted(servers.keys())}"
        )
    spec = servers[mcp_name]
    return McpSpec(
        name=mcp_name,
        command=spec["command"],
        args=list(spec.get("args", [])),
        # Pass through current env plus any per-MCP `env` overrides. We
        # filter to str:str for the SDK's StdioServerParameters type
        # contract.
        env={**os.environ, **{k: str(v) for k, v in spec.get("env", {}).items()}},
    )


# ─── tools/list probe ────────────────────────────────────────────────────


async def _probe_tools(spec: McpSpec, timeout_s: float) -> dict[str, Any]:
    """Spawn the MCP, run initialize + tools/list, return raw probe data.

    Returns a dict with:
      - `version_handshake`: serverInfo.version from initialize (or None)
      - `tools`: list of {name, description, input_schema_keys} dicts
      - `protocol_version`: the protocolVersion returned by the server

    Raises any exception the underlying SDK raises; the caller wraps
    them into the JSON error shape. This separation keeps the async
    boundary clean.

    Implementation note: the `stdio_client` context manager spawns the
    server as a child process. The Python SDK uses `anyio.open_process`
    which on POSIX defaults to a new process group when run under our
    asyncio loop — that matches `bench.process_group.spawn_setsid`'s
    contract closely enough for Phase 1, and avoids re-implementing the
    spawn dance. The context-manager teardown SIGTERMs the child; we
    don't need explicit `kill_group` here.
    """
    server_params = StdioServerParameters(
        command=spec.command,
        args=spec.args,
        env=spec.env,
    )

    # All three calls (stdio spawn, initialize, tools/list) live under a
    # single asyncio.wait_for so the 30 s budget is total, not per-call.
    # A wedged initialize that never returns is the failure mode we want
    # to catch — per-call budgets would let it sit for 90 s before tripping.
    async def _do_probe() -> dict[str, Any]:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                init_result = await session.initialize()
                tools_result = await session.list_tools()

                # `init_result.serverInfo.version` is the canonical
                # handshake-reported version. Lightpanda is the known
                # culprit for binary-vs-handshake mismatch; we capture
                # whatever the server gives us and leave reconciliation
                # to capture_versions.py + the human report.
                server_info = getattr(init_result, "serverInfo", None)
                version_handshake = (
                    getattr(server_info, "version", None) if server_info else None
                )
                protocol_version = getattr(init_result, "protocolVersion", None)

                tools_dump: list[dict[str, Any]] = []
                for tool in tools_result.tools:
                    # `description` is optional in the spec. Truncate to 200
                    # chars so the JSON file is grep-friendly and not
                    # dominated by long help text.
                    desc = (tool.description or "").strip()
                    if len(desc) > 200:
                        desc = desc[:197] + "..."
                    # The input schema can be huge; we only record the
                    # top-level property keys (a useful "tool surface
                    # area" signal without dumping the whole schema).
                    schema = tool.inputSchema or {}
                    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
                    schema_keys = sorted(properties.keys()) if isinstance(properties, dict) else []

                    tools_dump.append(
                        {
                            "name": tool.name,
                            "description_excerpt": desc,
                            "input_schema_keys": schema_keys,
                            "category": categorize_tool(tool.name),
                        }
                    )

                return {
                    "version_handshake": version_handshake,
                    "protocol_version": protocol_version,
                    "tools": tools_dump,
                }

    return await asyncio.wait_for(_do_probe(), timeout=timeout_s)


# ─── Top-level API ───────────────────────────────────────────────────────


def _now_iso_utc() -> str:
    """ISO-8601 UTC stamp, no microseconds, trailing Z."""
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def inventory_mcp(mcp_name: str, mcp_json_path: Path = DEFAULT_MCP_JSON,
                  timeout_s: float = INITIALIZE_TIMEOUT_S) -> dict[str, Any]:
    """Run the probe and return a `tools_inventory.json`-shaped dict.

    Never raises. On success: returns the full categorized inventory.
    On failure (missing MCP key, spawn error, initialize timeout): returns
    a dict with `status` set to a machine-readable error code. The caller
    (CLI) translates the `status` field into an exit code.
    """
    captured_at = _now_iso_utc()
    base: dict[str, Any] = {
        "mcp": mcp_name,
        "captured_at": captured_at,
    }

    try:
        spec = load_mcp_spec(mcp_name, mcp_json_path)
    except (FileNotFoundError, KeyError) as exc:
        return {
            **base,
            "status": "MCP_CONFIG_ERROR",
            "error": str(exc),
            "tool_count": 0,
            "categories": _empty_categories(),
            "tools": [],
        }

    try:
        probe = asyncio.run(_probe_tools(spec, timeout_s))
    except asyncio.TimeoutError:
        return {
            **base,
            "status": "INITIALIZE_TIMEOUT",
            "error": (
                f"Server did not complete initialize+tools/list within "
                f"{timeout_s:.0f}s — see browser-tools.md 2026-05-21 for "
                "the documented browser-use v0.12.7 timeout case."
            ),
            "command": spec.command,
            "args": spec.args,
            "tool_count": 0,
            "categories": _empty_categories(),
            "tools": [],
        }
    except Exception as exc:  # noqa: BLE001 — we want to surface anything
        return {
            **base,
            "status": "SPAWN_OR_RPC_ERROR",
            "error": f"{type(exc).__name__}: {exc}",
            "command": spec.command,
            "args": spec.args,
            "tool_count": 0,
            "categories": _empty_categories(),
            "tools": [],
        }

    # Success path.
    tools = probe["tools"]
    categories = _empty_categories()
    for tool in tools:
        categories[tool["category"]] = categories.get(tool["category"], 0) + 1

    return {
        **base,
        "status": "OK",
        "command": spec.command,
        "args": spec.args,
        "version_handshake": probe["version_handshake"],
        "protocol_version": probe["protocol_version"],
        "tool_count": len(tools),
        "categories": categories,
        "tools": tools,
    }


def _empty_categories() -> dict[str, int]:
    """Initialize the per-category counter to zero for every bucket.

    Even when probing fails (status != "OK") we emit the zero-filled
    structure so downstream readers can sum across MCPs without checking
    for missing keys.
    """
    return {name: 0 for name in CATEGORY_NAMES}


# ─── CLI ─────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.tools_inventory",
        description=(
            "Spawn an MCP via mcp.client.stdio, call tools/list, "
            "categorize each tool, and write tools_inventory.json. "
            "Exits non-zero on failure modes (INITIALIZE_TIMEOUT, "
            "SPAWN_OR_RPC_ERROR, MCP_CONFIG_ERROR) so the harness can "
            "attribute the row as tool-bug per FAIRNESS-06."
        ),
    )
    parser.add_argument(
        "mcp_name",
        type=str,
        help="MCP key in .mcp.json (e.g. playwright, lightpanda, ...)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output path for tools_inventory.json",
    )
    parser.add_argument(
        "--mcp-json",
        type=Path,
        default=DEFAULT_MCP_JSON,
        help="Path to .mcp.json (default: project-scope .mcp.json)",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=INITIALIZE_TIMEOUT_S,
        help=f"Initialize+tools/list timeout (default: {INITIALIZE_TIMEOUT_S}s)",
    )
    args = parser.parse_args(argv)

    inventory = inventory_mcp(
        args.mcp_name,
        mcp_json_path=args.mcp_json,
        timeout_s=args.timeout_s,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    status = inventory.get("status")
    print(
        f"tools_inventory: {args.mcp_name} -> {args.out} "
        f"(status={status}, tool_count={inventory.get('tool_count', 0)})",
        file=sys.stderr,
    )

    # Exit codes:
    #   0  — OK
    #   1  — INITIALIZE_TIMEOUT (the documented v0.12.7 case)
    #   2  — SPAWN_OR_RPC_ERROR (binary missing, crash, RPC error)
    #   3  — MCP_CONFIG_ERROR   (mcp_name not in .mcp.json)
    return {
        "OK": 0,
        "INITIALIZE_TIMEOUT": 1,
        "SPAWN_OR_RPC_ERROR": 2,
        "MCP_CONFIG_ERROR": 3,
    }.get(status or "", 4)


if __name__ == "__main__":
    sys.exit(main())
