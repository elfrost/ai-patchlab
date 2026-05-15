"""Tests for the web probe.

All tests use `httpx.MockTransport` — the test suite never opens a real
socket. Each test installs a `handler(request) -> httpx.Response` that fully
controls the responses for a given target.
"""

from __future__ import annotations

import httpx
import pytest
from fingerprint.config import FingerprintConfig
from fingerprint.web_probe import fetch_target


def _make_transport(routes: dict[str, httpx.Response]) -> httpx.MockTransport:
    """Build a MockTransport that maps absolute URLs to responses."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url in routes:
            return routes[url]
        return httpx.Response(404, text="not found")

    return httpx.MockTransport(handler)


def test_fetch_target_rejects_non_http_scheme() -> None:
    config = FingerprintConfig()
    with pytest.raises(ValueError):
        fetch_target("file:///etc/passwd", config, ())


def test_fetch_target_rejects_gopher_scheme() -> None:
    config = FingerprintConfig()
    with pytest.raises(ValueError):
        fetch_target("gopher://example.com", config, ())


def test_fetch_target_rejects_missing_host() -> None:
    config = FingerprintConfig()
    with pytest.raises(ValueError):
        fetch_target("https://", config, ())


def test_fetch_target_happy_path() -> None:
    routes = {
        "https://example.com/robots.txt": httpx.Response(404, text="not found"),
        "https://example.com/": httpx.Response(200, text="<html>hello</html>"),
        "https://example.com/public/favicon.ico": httpx.Response(200, content=b"\x00FAVICON"),
    }
    transport = _make_transport(routes)
    snapshot = fetch_target(
        "https://example.com/",
        FingerprintConfig(),
        ("public/favicon.ico",),
        transport=transport,
    )
    assert snapshot.notes == "ok"
    assert snapshot.homepage_html == b"<html>hello</html>"
    assert len(snapshot.fetched_assets) == 1
    asset = snapshot.fetched_assets[0]
    assert asset.url == "https://example.com/public/favicon.ico"
    assert asset.byte_size == len(b"\x00FAVICON")
    assert asset.truncated is False
    assert asset.status == 200


def test_fetch_target_respects_robots_disallow() -> None:
    # urllib.robotparser splits the runtime UA on "/" before matching;
    # `ai-patchlab-fingerprint/0.1` becomes `ai-patchlab-fingerprint`. A
    # robots.txt block targeting just the name (no version) disallows us.
    routes = {
        "https://example.com/robots.txt": httpx.Response(
            200,
            text="User-agent: ai-patchlab-fingerprint\nDisallow: /\n",
        ),
        "https://example.com/": httpx.Response(200, text="should not be reached"),
    }
    transport = _make_transport(routes)
    snapshot = fetch_target(
        "https://example.com/",
        FingerprintConfig(),
        (),
        transport=transport,
    )
    assert snapshot.notes == "robots-disallowed"
    assert snapshot.homepage_html == b""
    assert snapshot.fetched_assets == ()


def test_fetch_target_robots_allows_when_unreachable() -> None:
    routes = {
        "https://example.com/": httpx.Response(200, text="<html>x</html>"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            raise httpx.ConnectError("robots unreachable")
        if url in routes:
            return routes[url]
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    snapshot = fetch_target(
        "https://example.com/",
        FingerprintConfig(),
        (),
        transport=transport,
    )
    assert snapshot.homepage_html == b"<html>x</html>"
    assert snapshot.notes == "ok"


def test_fetch_target_truncates_oversize_homepage() -> None:
    big = b"x" * 5000
    routes = {
        "https://example.com/robots.txt": httpx.Response(404),
        "https://example.com/": httpx.Response(200, content=big),
    }
    transport = _make_transport(routes)
    config = FingerprintConfig(max_bytes_per_asset=100)
    snapshot = fetch_target(
        "https://example.com/",
        config,
        (),
        transport=transport,
    )
    assert len(snapshot.homepage_html) == 100
    assert "homepage-truncated" in snapshot.notes


def test_fetch_target_marks_oversize_asset() -> None:
    big = b"y" * 5000
    routes = {
        "https://example.com/robots.txt": httpx.Response(404),
        "https://example.com/": httpx.Response(200, text="<html></html>"),
        "https://example.com/public/big.css": httpx.Response(200, content=big),
    }
    transport = _make_transport(routes)
    config = FingerprintConfig(max_bytes_per_asset=100)
    snapshot = fetch_target(
        "https://example.com/",
        config,
        ("public/big.css",),
        transport=transport,
    )
    assert len(snapshot.fetched_assets) == 1
    asset = snapshot.fetched_assets[0]
    assert asset.truncated is True
    assert asset.byte_size == 100


def test_fetch_target_redirect_chain() -> None:
    routes = {
        "https://example.com/robots.txt": httpx.Response(404),
        "https://example.com/": httpx.Response(301, headers={"Location": "https://example.com/a"}),
        "https://example.com/a": httpx.Response(302, headers={"Location": "https://example.com/b"}),
        "https://example.com/b": httpx.Response(200, text="<html>final</html>"),
    }
    transport = _make_transport(routes)
    snapshot = fetch_target(
        "https://example.com/",
        FingerprintConfig(),
        (),
        transport=transport,
    )
    assert snapshot.homepage_html == b"<html>final</html>"


def test_fetch_target_404_homepage_still_records_notes() -> None:
    routes = {
        "https://example.com/robots.txt": httpx.Response(404),
        "https://example.com/": httpx.Response(404, text="missing"),
    }
    transport = _make_transport(routes)
    snapshot = fetch_target(
        "https://example.com/",
        FingerprintConfig(),
        (),
        transport=transport,
    )
    assert snapshot.homepage_html == b""
    assert "homepage-status-404" in snapshot.notes


def test_fetch_target_caps_total_assets() -> None:
    routes = {
        "https://example.com/robots.txt": httpx.Response(404),
        "https://example.com/": httpx.Response(200, text="<html></html>"),
    }
    for i in range(20):
        routes[f"https://example.com/asset-{i}.css"] = httpx.Response(
            200, content=f"a-{i}".encode()
        )
    transport = _make_transport(routes)
    config = FingerprintConfig(max_assets_per_target=5)
    paths = tuple(f"asset-{i}.css" for i in range(20))
    snapshot = fetch_target(
        "https://example.com/",
        config,
        paths,
        transport=transport,
    )
    # 1 homepage + max 4 assets => 4 in fetched_assets
    assert len(snapshot.fetched_assets) == 4


def test_fetch_target_deduplicates_candidate_paths() -> None:
    routes = {
        "https://example.com/robots.txt": httpx.Response(404),
        "https://example.com/": httpx.Response(200, text="<html></html>"),
        "https://example.com/favicon.ico": httpx.Response(200, content=b"\x00"),
    }
    transport = _make_transport(routes)
    snapshot = fetch_target(
        "https://example.com/",
        FingerprintConfig(),
        ("favicon.ico", "favicon.ico", " favicon.ico "),
        transport=transport,
    )
    assert len(snapshot.fetched_assets) == 1


def test_fetch_target_skips_failed_asset_silently() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(404)
        if url == "https://example.com/":
            return httpx.Response(200, text="<html></html>")
        if url.endswith("/broken.css"):
            raise httpx.ConnectError("boom")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    snapshot = fetch_target(
        "https://example.com/",
        FingerprintConfig(),
        ("broken.css",),
        transport=transport,
    )
    assert snapshot.fetched_assets == ()
    assert snapshot.notes == "ok"
