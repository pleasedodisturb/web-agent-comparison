"""cloakbrowser_guard — SAFETY-04 contract enforcement.

The cloakbrowser MCP is a closed-source binary that touches cookies on
launch. Per `~/.claude/CLAUDE.md` browser-tools policy and the project-level
CONSTRAINTS in CLAUDE.md ("Sandbox-only MCPs: `cloakbrowser` is closed-source
binary touching cookies — never point at authenticated host pages"), it must
only ever be pointed at loopback hosts (the self-hosted snapshot fixtures
under `fixtures/snapshots/`).

This module exposes one function — `assert_local_only(url)` — that the
session driver (`scripts/run_mcp_session.sh`, landing in plan 01-04) MUST
call before spawning cloakbrowser. Any non-loopback hostname raises
`HostnameNotAllowedError` and aborts the spawn.

The guard is intentionally strict: only the literal allow-list passes. IPv6
loopback variants are accepted via both bracketed (`[::1]`) and bare (`::1`)
forms, since `urllib.parse.urlparse` strips brackets from `hostname` for
IPv6 literals.
"""

from __future__ import annotations

from urllib.parse import urlparse


class HostnameNotAllowedError(RuntimeError):
    """Raised when a non-loopback hostname is passed to a cloakbrowser-bound flow."""


# Hostnames that may be targeted by cloakbrowser. Anything else aborts.
# - `127.0.0.1`, `localhost`, `::1`: standard loopback identities.
# - `[::1]`: the literal bracketed form, in case a caller pre-parses brackets.
ALLOWED_HOSTS: frozenset[str] = frozenset({
    "127.0.0.1",
    "localhost",
    "::1",
    "[::1]",
})


def assert_local_only(url: str) -> None:
    """Raise `HostnameNotAllowedError` unless `url`'s hostname is loopback.

    Parameters
    ----------
    url
        Full URL string, e.g. `http://127.0.0.1:8000/greenhouse/index.html`.

    Raises
    ------
    HostnameNotAllowedError
        If `url` cannot be parsed, has no hostname, or has a hostname not in
        `ALLOWED_HOSTS`.
    """
    if not isinstance(url, str) or not url.strip():
        raise HostnameNotAllowedError(
            f"cloakbrowser refused: invalid URL {url!r}"
        )

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise HostnameNotAllowedError(
            f"cloakbrowser refused: could not parse URL {url!r} ({exc})"
        ) from exc

    host = parsed.hostname
    if host is None:
        raise HostnameNotAllowedError(
            f"cloakbrowser refused: URL {url!r} has no hostname"
        )

    # urlparse lowercases the hostname; allow-list matching is exact.
    if host not in ALLOWED_HOSTS:
        raise HostnameNotAllowedError(
            f"cloakbrowser refused: hostname {host!r} not in {sorted(ALLOWED_HOSTS)}"
        )
