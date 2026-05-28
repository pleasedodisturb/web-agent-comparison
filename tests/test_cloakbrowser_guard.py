"""Tests for bench/cloakbrowser_guard."""

from __future__ import annotations

import unittest

from bench.cloakbrowser_guard import (
    ALLOWED_HOSTS,
    HostnameNotAllowedError,
    assert_local_only,
)


class CloakbrowserGuardTests(unittest.TestCase):
    def test_loopback_ipv4_accepted(self) -> None:
        # Should not raise.
        assert_local_only("http://127.0.0.1:8000/greenhouse/index.html")

    def test_localhost_accepted(self) -> None:
        assert_local_only("http://localhost:8000/")
        assert_local_only("https://localhost/")

    def test_loopback_ipv6_accepted(self) -> None:
        # IPv6 literal: brackets in URL are stripped by urlparse.hostname.
        assert_local_only("http://[::1]:8000/path")

    def test_greenhouse_rejected(self) -> None:
        with self.assertRaises(HostnameNotAllowedError) as ctx:
            assert_local_only("https://boards.greenhouse.io/anthropic")
        self.assertIn("boards.greenhouse.io", str(ctx.exception))

    def test_google_rejected(self) -> None:
        with self.assertRaises(HostnameNotAllowedError):
            assert_local_only("https://www.google.com/")

    def test_private_lan_address_rejected(self) -> None:
        """An RFC1918 address is NOT loopback and must be rejected."""
        with self.assertRaises(HostnameNotAllowedError):
            assert_local_only("http://192.168.1.10:8000/")
        with self.assertRaises(HostnameNotAllowedError):
            assert_local_only("http://10.0.0.5/")

    def test_loopback_lookalike_rejected(self) -> None:
        """A subdomain of localhost is NOT loopback (DNS-rebinding hazard)."""
        with self.assertRaises(HostnameNotAllowedError):
            assert_local_only("http://localhost.example.com/")

    def test_empty_url_rejected(self) -> None:
        with self.assertRaises(HostnameNotAllowedError):
            assert_local_only("")
        with self.assertRaises(HostnameNotAllowedError):
            assert_local_only("   ")

    def test_url_with_no_hostname_rejected(self) -> None:
        """`file://` URLs and bare paths must not be silently accepted."""
        with self.assertRaises(HostnameNotAllowedError):
            assert_local_only("file:///etc/passwd")
        with self.assertRaises(HostnameNotAllowedError):
            assert_local_only("/relative/path/only")

    def test_non_string_input_rejected(self) -> None:
        with self.assertRaises(HostnameNotAllowedError):
            assert_local_only(None)  # type: ignore[arg-type]

    def test_allowed_hosts_constant_shape(self) -> None:
        """Smoke test: contract documented in module docstring matches code."""
        self.assertIn("127.0.0.1", ALLOWED_HOSTS)
        self.assertIn("localhost", ALLOWED_HOSTS)
        self.assertIn("::1", ALLOWED_HOSTS)


if __name__ == "__main__":
    unittest.main()
