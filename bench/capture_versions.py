"""capture_versions — write a reproducibility manifest for the live env.

Produces TWO files in `<results-root>/<date>/`:

  * `versions.json` — machine-readable. The full live-env state at
    capture time, suitable for diffing across machines / dates / waves.

  * `versions.lock.md` — human-readable companion. Same data, rendered
    as a Markdown table a reader can `cat` to see "which versions ran
    here". Generated from the same dict so the two files cannot drift.

What's captured
---------------
- **Host**: OS name, version, arch (`uname -srm` + `sw_vers` on macOS).
- **Tooling**: Claude Code, Node, npm, Python, uv versions.
- **MCPs**: for each key in `.mcp.json`:
    - the resolved binary path (`command -v <cmd>`),
    - the binary SHA256 (`shasum -a 256 <path>`),
    - the package version (`npm view <pkg> version` for npm MCPs,
      `<binary> --version` for binary MCPs).
- **Lightpanda binary-vs-handshake mismatch** — the handshake-reported
  version is whatever the latest `tools_inventory.json` recorded under
  `version_handshake`; we record both numbers and flag the mismatch in
  the lock file when they differ, per RESEARCH §1 finding.

Privacy
-------
CLAUDE.md mandates no PII or machine-identifying data in committed
artifacts. We deliberately AVOID:
  - `hostname`, `whoami`, `$USER` — would leak the contributor's identity.
  - Absolute home-directory paths in the binary_path field — collapsed
    to `~/...` when the path starts with the current $HOME.
  - `ifconfig`/`ip` output, MAC addresses, hardware UUIDs.

The OS string (`Darwin 25.5.0 arm64`) is generic enough to be safe —
hundreds of thousands of macs report identically.

CLI
---
    python -m bench.capture_versions [--date YYYY-MM-DD]
                                     [--results-root results/]

If `--date` is omitted, today's UTC date is used.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MCP_JSON = _REPO_ROOT / ".mcp.json"

# Map MCP key in `.mcp.json` → npm package name we can `npm view`. Built-
# from-binary MCPs (lightpanda, browser-use, cloakbrowser) are left out;
# their version comes from `<binary> --version` instead.
NPM_PACKAGE_MAP = {
    "playwright": "@playwright/mcp",
    "chrome-devtools": "chrome-devtools-mcp",
    "obscura": "obscura-mcp",
    "firecrawl": "firecrawl-mcp",
}

# Map MCP key → the argv used to print its version. None of the three
# binary-distributed MCPs accept `--version`:
#   * lightpanda: subcommand-style — `lightpanda version`
#   * browser-use: argparse rejects --version; queried via `uv tool list`
#   * cloakbrowser: argparse rejects --version; queried via `uv tool list`
# `None` here means "skip the binary probe; rely on UV_TOOL_LIST_NAMES".
BINARY_VERSION_ARGV: dict[str, Optional[list[str]]] = {
    "lightpanda": ["version"],
    "browser-use": None,
    "cloakbrowser": None,
}

# Map MCP key → the name uv tool list uses for the package. browser-use
# and cloakbrowsermcp are both installed via `uv tool install` and their
# version is reported as `<name> v<X.Y.Z>` in `uv tool list` output.
UV_TOOL_LIST_NAMES = {
    "browser-use": "browser-use",
    "cloakbrowser": "cloakbrowsermcp",
}


def _uv_tool_version(tool_name: str) -> Optional[str]:
    """Parse `uv tool list` output to find the version of `tool_name`.

    `uv tool list` prints lines like:
        browser-use v0.12.7
        - browser
        - browser-use
        ...

    Returns the bare version number (`0.12.7`) for the matching line, or
    None if not present.
    """
    out = _run_capture(["uv", "tool", "list"], timeout_s=5.0)
    if not out:
        return None
    for line in out.splitlines():
        # Tool line format: "<name> v<version>"; sub-package lines start
        # with "- " and should be ignored.
        if line.startswith("- "):
            continue
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] == tool_name and parts[1].startswith("v"):
            return parts[1].lstrip("v")
    return None


# ─── Subprocess helpers ──────────────────────────────────────────────────


def _run_capture(cmd: list[str], timeout_s: float = 5.0) -> Optional[str]:
    """Run `cmd`, return stripped stdout, or None on failure/timeout.

    Never raises. Designed for "best-effort capture" — a missing binary
    or a timeout simply leaves the field unpopulated in the manifest, not
    a stack trace in the user's face.
    """
    try:
        out = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    # Some tools print version to stderr (e.g. `node` doesn't, but some
    # MCPs do). Concatenate both so we don't miss it.
    text = (out.stdout or "") + (out.stderr or "")
    return text.strip() or None


def _which(cmd: str) -> Optional[str]:
    """`shutil.which` wrapper that also collapses $HOME → ~/."""
    path = shutil.which(cmd)
    if not path:
        return None
    home = os.environ.get("HOME", "")
    if home and path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


def _sha256_file(path: str) -> Optional[str]:
    """Return the SHA256 hex digest of `path`, or None if unreadable.

    Uses `shasum -a 256` (POSIX, on macOS by default per PROJECT.md)
    with a hashlib fallback. We prefer the shell tool because that's
    what a human-reproducer will use to verify, and consistent tool
    choice means consistent edge-case behavior (symlink following,
    permission errors).
    """
    # If `path` was collapsed to ~/foo for the manifest, expand it back
    # before hashing.
    real_path = os.path.expanduser(path)
    if not Path(real_path).exists():
        return None

    out = _run_capture(["shasum", "-a", "256", real_path], timeout_s=10.0)
    if out:
        # `shasum` output: "<hexdigest>  <filename>"
        parts = out.split()
        if parts and len(parts[0]) == 64:
            return parts[0].lower()

    # Fallback: read the file in chunks. 8 MB chunks — most MCP binaries
    # are under 100 MB so this completes in a fraction of a second.
    try:
        h = hashlib.sha256()
        with open(real_path, "rb") as f:
            for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


# ─── Section captors ─────────────────────────────────────────────────────


def capture_host() -> dict[str, str]:
    """OS name, kernel version, arch. macOS gets `sw_vers` for the
    product version on top of the Darwin kernel version."""
    info: dict[str, str] = {
        "os": platform.system(),               # "Darwin" / "Linux"
        "kernel_version": platform.release(),  # e.g. "25.5.0"
        "arch": platform.machine(),            # "arm64" / "x86_64"
    }
    if info["os"] == "Darwin":
        # `sw_vers -productVersion` returns macOS marketing version
        # ("15.5" etc). Generic, no PII.
        pv = _run_capture(["sw_vers", "-productVersion"])
        if pv:
            info["macos_version"] = pv
    return info


def capture_tooling() -> dict[str, Optional[str]]:
    """Versions of the toolchain the harness depends on.

    Each value is the FIRST LINE of the tool's version output, stripped.
    None if the tool isn't on PATH.
    """
    def first_line(s: Optional[str]) -> Optional[str]:
        return s.splitlines()[0].strip() if s else None

    return {
        "claude_code": first_line(_run_capture(["claude", "--version"])),
        "node": first_line(_run_capture(["node", "--version"])),
        "npm": first_line(_run_capture(["npm", "--version"])),
        "python": first_line(_run_capture(["python3", "--version"])),
        "uv": first_line(_run_capture(["uv", "--version"])),
    }


def _capture_mcp(name: str, command: str,
                 handshake_versions: dict[str, str]) -> dict[str, Any]:
    """Capture binary path, SHA256, and version string for one MCP.

    `handshake_versions` is a dict {mcp_name: version_string} taken from
    any tools_inventory.json files in the current results directory, so
    we can record the binary-vs-handshake mismatch (lightpanda case).
    """
    info: dict[str, Any] = {
        "command": command,
        "binary_path": _which(command),
    }

    # SHA256 of the resolved binary.
    if info["binary_path"]:
        info["sha256"] = _sha256_file(info["binary_path"])
    else:
        info["sha256"] = None

    # Package version. Strategy depends on MCP type.
    if name in NPM_PACKAGE_MAP:
        pkg = NPM_PACKAGE_MAP[name]
        v = _run_capture(["npm", "view", pkg, "version"], timeout_s=10.0)
        info["package_name"] = pkg
        info["package_version"] = v
    elif name in BINARY_VERSION_ARGV:
        argv = BINARY_VERSION_ARGV[name]
        v: Optional[str] = None
        if argv is not None:
            # Binary supports a version subcommand or flag.
            raw = _run_capture([command] + argv, timeout_s=5.0)
            # Only the first line — some tools print a banner.
            v = raw.splitlines()[0].strip() if raw else None
        if not v and name in UV_TOOL_LIST_NAMES:
            # Fallback: `uv tool list` (covers browser-use, cloakbrowser).
            v = _uv_tool_version(UV_TOOL_LIST_NAMES[name])
        info["binary_self_report"] = v
    else:
        # Unknown MCP-type — try --version as a generic probe.
        v = _run_capture([command, "--version"], timeout_s=5.0)
        info["binary_self_report"] = v.splitlines()[0].strip() if v else None

    # Handshake version from tools_inventory.json, if present.
    if name in handshake_versions:
        info["handshake_protocol_version"] = handshake_versions[name]
        # Flag the lightpanda-style mismatch.
        binary_str = (info.get("binary_self_report")
                      or info.get("package_version") or "")
        handshake_str = handshake_versions[name] or ""
        if (binary_str and handshake_str
                and binary_str not in handshake_str
                and handshake_str not in binary_str):
            info["version_mismatch"] = True

    return info


def _collect_handshake_versions(results_date_dir: Path) -> dict[str, str]:
    """Scan `results/<date>/<mcp>/tools_inventory.json` files and pull
    out the handshake version for each MCP. Returns {} if nothing's been
    inventoried yet (e.g. on a fresh harness run before any MCP runs)."""
    versions: dict[str, str] = {}
    if not results_date_dir.exists():
        return versions
    for entry in results_date_dir.iterdir():
        if not entry.is_dir():
            continue
        inv_path = entry / "tools_inventory.json"
        if not inv_path.exists():
            continue
        try:
            data = json.loads(inv_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        v = data.get("version_handshake")
        if v:
            versions[entry.name] = str(v)
    return versions


def capture_mcps(mcp_json_path: Path,
                 results_date_dir: Path) -> dict[str, dict[str, Any]]:
    """Iterate `.mcp.json` keys; capture per-MCP version info for each."""
    if not mcp_json_path.exists():
        return {}
    config = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    servers = config.get("mcpServers", {})

    handshake = _collect_handshake_versions(results_date_dir)

    out: dict[str, dict[str, Any]] = {}
    for name, spec in servers.items():
        out[name] = _capture_mcp(
            name=name,
            command=spec["command"],
            handshake_versions=handshake,
        )
    return out


# ─── Top-level capture ───────────────────────────────────────────────────


def _now_iso_utc() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def capture(date: str, results_root: Path,
            mcp_json_path: Path = DEFAULT_MCP_JSON) -> dict[str, Any]:
    """Run all section captors and return the combined manifest dict."""
    results_date_dir = results_root / date
    return {
        "captured_at": _now_iso_utc(),
        "date": date,
        "host": capture_host(),
        "tooling": capture_tooling(),
        "mcps": capture_mcps(mcp_json_path, results_date_dir),
    }


# ─── Markdown rendering ──────────────────────────────────────────────────


def render_markdown(manifest: dict[str, Any]) -> str:
    """Render `manifest` as a `versions.lock.md` human-readable companion.

    Mirrors the structure of the JSON 1:1 so a reader can flip between
    the two. Uses pipe-tables (GitHub-flavored) so the README renders
    cleanly when surfaced.
    """
    host = manifest.get("host", {})
    tooling = manifest.get("tooling", {})
    mcps = manifest.get("mcps", {})

    lines: list[str] = []
    lines.append(f"# Reproducibility Manifest — {manifest.get('date', '?')}")
    lines.append("")
    lines.append(f"*Captured at:* `{manifest.get('captured_at', '?')}` (UTC)")
    lines.append("")

    # Host section.
    lines.append("## Host")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for k in ("os", "macos_version", "kernel_version", "arch"):
        if k in host:
            lines.append(f"| {k} | `{host[k]}` |")
    lines.append("")

    # Tooling section.
    lines.append("## Tooling")
    lines.append("")
    lines.append("| Tool | Version |")
    lines.append("|---|---|")
    for k in ("claude_code", "node", "npm", "python", "uv"):
        v = tooling.get(k)
        lines.append(f"| {k} | `{v if v else '(not on PATH)'}` |")
    lines.append("")

    # MCPs section.
    lines.append("## MCPs")
    lines.append("")
    lines.append("| MCP | Version | SHA256 (first 16) | Binary path | Notes |")
    lines.append("|---|---|---|---|---|")
    for name in sorted(mcps.keys()):
        info = mcps[name]
        version = (
            info.get("package_version")
            or info.get("binary_self_report")
            or "?"
        )
        sha = info.get("sha256") or "?"
        sha_short = sha[:16] if sha and sha != "?" else "?"
        path = info.get("binary_path") or "(not on PATH)"
        notes_parts: list[str] = []
        handshake = info.get("handshake_protocol_version")
        if handshake:
            notes_parts.append(f"handshake={handshake}")
        if info.get("version_mismatch"):
            notes_parts.append("**MISMATCH**")
        notes = "; ".join(notes_parts) if notes_parts else ""
        lines.append(
            f"| `{name}` | `{version}` | `{sha_short}` | `{path}` | {notes} |"
        )
    lines.append("")

    # Mismatch annotation block.
    mismatches = [n for n, info in mcps.items() if info.get("version_mismatch")]
    if mismatches:
        lines.append("## Version mismatches")
        lines.append("")
        lines.append(
            "The following MCPs reported one version via their binary's "
            "self-report and a different version via the JSON-RPC `initialize` "
            "handshake. Lightpanda is the documented case (RESEARCH §1) — "
            "binary header says `0.3.0`, handshake says `0.1.0`. Both numbers "
            "are recorded above; do not pick one."
        )
        lines.append("")
        for name in mismatches:
            info = mcps[name]
            lines.append(
                f"- **{name}**: binary `{info.get('binary_self_report', '?')}` "
                f"vs handshake `{info.get('handshake_protocol_version', '?')}`"
            )
        lines.append("")

    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bench.capture_versions",
        description=(
            "Write a reproducibility manifest (versions.json + "
            "versions.lock.md) describing the live environment."
        ),
    )
    parser.add_argument(
        "--date",
        type=str,
        default=dt.datetime.now(tz=dt.timezone.utc).date().isoformat(),
        help="Date subdirectory under --results-root (default: UTC today)",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("results"),
        help="Root results directory (default: results/)",
    )
    parser.add_argument(
        "--mcp-json",
        type=Path,
        default=DEFAULT_MCP_JSON,
        help="Path to .mcp.json (default: project-scope .mcp.json)",
    )
    args = parser.parse_args(argv)

    manifest = capture(
        date=args.date,
        results_root=args.results_root,
        mcp_json_path=args.mcp_json,
    )

    out_dir = args.results_root / args.date
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "versions.json"
    md_path = out_dir / "versions.lock.md"

    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(manifest) + "\n", encoding="utf-8")

    print(f"capture_versions: wrote {json_path}", file=sys.stderr)
    print(f"capture_versions: wrote {md_path}", file=sys.stderr)

    # Count how many MCPs we successfully captured a SHA for. If zero,
    # something is fundamentally broken — exit non-zero so CI / the
    # harness wrapper notices.
    captured = sum(
        1 for v in manifest.get("mcps", {}).values()
        if v.get("sha256")
    )
    total = len(manifest.get("mcps", {}))
    print(
        f"capture_versions: SHA256 captured for {captured}/{total} MCPs",
        file=sys.stderr,
    )
    return 0 if captured > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
