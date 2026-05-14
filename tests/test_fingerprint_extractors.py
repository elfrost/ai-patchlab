"""Tests for fingerprint extractors."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fingerprint.config import FingerprintConfig
from fingerprint.extractors.favicon import extract_favicon
from fingerprint.extractors.html_signatures import extract_html_signatures
from fingerprint.extractors.static_assets import extract_static_assets


def _write(path: Path, content: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def test_extract_favicon_finds_public_ico(tmp_path: Path) -> None:
    data = b"\x00favicon-bytes"
    _write(tmp_path / "public" / "favicon.ico", data)
    fp = extract_favicon(tmp_path)
    assert fp is not None
    assert fp.relative_path == "public/favicon.ico"
    assert fp.sha256 == hashlib.sha256(data).hexdigest()
    assert fp.byte_size == len(data)
    assert fp.kind == "favicon"


def test_extract_favicon_returns_none_when_missing(tmp_path: Path) -> None:
    assert extract_favicon(tmp_path) is None


def test_extract_favicon_preserves_ordering(tmp_path: Path) -> None:
    _write(tmp_path / "favicon.ico", b"root")
    _write(tmp_path / "public" / "favicon.ico", b"public")
    fp = extract_favicon(tmp_path)
    assert fp is not None
    # public/favicon.ico comes before favicon.ico in the candidate list
    assert fp.relative_path == "public/favicon.ico"


def test_extract_static_assets_walks_known_folders(tmp_path: Path) -> None:
    _write(tmp_path / "public" / "app.css", b"body{}")
    _write(tmp_path / "public" / "app.js", b"console.log('x')")
    _write(tmp_path / "static" / "icon.svg", b"<svg></svg>")
    _write(tmp_path / "README.md", b"# ignored")

    config = FingerprintConfig()
    assets = extract_static_assets(tmp_path, config)
    paths = {asset.relative_path for asset in assets}
    assert "public/app.css" in paths
    assert "public/app.js" in paths
    assert "static/icon.svg" in paths


def test_extract_static_assets_skips_oversize(tmp_path: Path) -> None:
    small = tmp_path / "public" / "small.css"
    large = tmp_path / "public" / "large.css"
    _write(small, b"small")
    _write(large, b"x" * 2000)

    config = FingerprintConfig(max_bytes_per_asset=100)
    assets = extract_static_assets(tmp_path, config)
    paths = {asset.relative_path for asset in assets}
    assert "public/small.css" in paths
    assert "public/large.css" not in paths


def test_extract_static_assets_deterministic(tmp_path: Path) -> None:
    for name in ("b.css", "a.css", "c.css"):
        _write(tmp_path / "public" / name, name.encode())

    config = FingerprintConfig()
    first = extract_static_assets(tmp_path, config)
    second = extract_static_assets(tmp_path, config)
    assert first == second


def test_extract_static_assets_dedups_identical_hashes(tmp_path: Path) -> None:
    _write(tmp_path / "public" / "a.css", b"same")
    _write(tmp_path / "public" / "b.css", b"same")
    config = FingerprintConfig()
    assets = extract_static_assets(tmp_path, config)
    assert len(assets) == 1


def test_extract_html_signatures_meta_generator(tmp_path: Path) -> None:
    _write(
        tmp_path / "index.html",
        '<html><head><meta name="generator" content="Next.js"></head></html>',
    )
    sigs = extract_html_signatures(tmp_path)
    assert any(s.kind == "meta-generator" and s.pattern == "Next.js" for s in sigs)


def test_extract_html_signatures_class_must_repeat(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.html",
        '<div class="hero-section-primary"></div>',
    )
    _write(
        tmp_path / "b.html",
        '<section class="hero-section-primary"></section>',
    )
    _write(
        tmp_path / "c.html",
        '<span class="unique-once-only"></span>',
    )
    sigs = extract_html_signatures(tmp_path)
    class_patterns = {s.pattern for s in sigs if s.kind == "class"}
    assert "hero-section-primary" in class_patterns
    assert "unique-once-only" not in class_patterns


def test_extract_html_signatures_data_attr(tmp_path: Path) -> None:
    _write(
        tmp_path / "index.html",
        '<div data-template-id="nextjs-saas"></div>',
    )
    sigs = extract_html_signatures(tmp_path)
    patterns = {s.pattern for s in sigs if s.kind == "data-attr"}
    assert 'data-template-id="nextjs-saas"' in patterns


def test_extract_html_signatures_skips_node_modules(tmp_path: Path) -> None:
    _write(
        tmp_path / "node_modules" / "vendor" / "vendor.html",
        '<meta name="generator" content="VendorThing">',
    )
    _write(
        tmp_path / "index.html",
        "<html><body></body></html>",
    )
    sigs = extract_html_signatures(tmp_path)
    assert not any(s.kind == "meta-generator" and s.pattern == "VendorThing" for s in sigs)


def test_extract_html_signatures_deterministic(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.html",
        '<meta name="generator" content="Astro 4.0"><div class="page-wrapper-main"></div>',
    )
    _write(
        tmp_path / "b.html",
        '<div class="page-wrapper-main"></div>',
    )
    first = extract_html_signatures(tmp_path)
    second = extract_html_signatures(tmp_path)
    assert first == second


def test_extract_html_signatures_comment_marker(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.html",
        "<!-- BuiltWith Astro -->",
    )
    _write(
        tmp_path / "b.html",
        "<!-- BuiltWith Astro -->",
    )
    sigs = extract_html_signatures(tmp_path)
    patterns = {s.pattern for s in sigs if s.kind == "comment"}
    assert "BuiltWith" in patterns
