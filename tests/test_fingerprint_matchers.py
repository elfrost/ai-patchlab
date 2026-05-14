"""Tests for fingerprint matchers."""

from __future__ import annotations

from fingerprint.matchers.asset_hash import match_asset_hashes
from fingerprint.matchers.html_regex import match_html_signatures
from fingerprint.models import (
    AssetFingerprint,
    HtmlSignature,
    RepoFingerprint,
)
from fingerprint.web_probe import FetchedAsset, TargetSnapshot


def _repo(
    *,
    assets: tuple[AssetFingerprint, ...] = (),
    signatures: tuple[HtmlSignature, ...] = (),
) -> RepoFingerprint:
    return RepoFingerprint(
        slug="x",
        repo_url="https://github.com/a/b",
        indexed_at="2026-05-14T00:00:00Z",
        assets=assets,
        html_signatures=signatures,
    )


def _snapshot(
    *,
    html: bytes = b"",
    fetched: tuple[FetchedAsset, ...] = (),
    notes: str = "ok",
) -> TargetSnapshot:
    return TargetSnapshot(
        target_url="https://example.com/",
        fetched_at="2026-05-14T00:00:00Z",
        homepage_html=html,
        fetched_assets=fetched,
        notes=notes,
    )


def test_match_asset_hash_favicon_high_weight() -> None:
    sha = "a" * 64
    repo = _repo(
        assets=(
            AssetFingerprint(
                relative_path="public/favicon.ico",
                sha256=sha,
                byte_size=10,
                kind="favicon",
            ),
        )
    )
    snap = _snapshot(
        fetched=(
            FetchedAsset(
                url="https://example.com/favicon.ico",
                sha256=sha,
                byte_size=10,
                truncated=False,
                status=200,
            ),
        ),
    )
    signals = match_asset_hashes(repo, snap)
    assert len(signals) == 1
    assert signals[0].weight == "high"


def test_match_asset_hash_other_kind_medium_weight() -> None:
    sha = "b" * 64
    repo = _repo(
        assets=(
            AssetFingerprint(
                relative_path="public/app.css",
                sha256=sha,
                byte_size=10,
                kind="css",
            ),
        )
    )
    snap = _snapshot(
        fetched=(
            FetchedAsset(
                url="https://example.com/app.css",
                sha256=sha,
                byte_size=10,
                truncated=False,
                status=200,
            ),
        ),
    )
    signals = match_asset_hashes(repo, snap)
    assert len(signals) == 1
    assert signals[0].weight == "medium"


def test_match_asset_hash_no_match() -> None:
    repo = _repo(
        assets=(
            AssetFingerprint(
                relative_path="public/favicon.ico",
                sha256="a" * 64,
                byte_size=10,
                kind="favicon",
            ),
        )
    )
    snap = _snapshot(
        fetched=(
            FetchedAsset(
                url="https://example.com/favicon.ico",
                sha256="c" * 64,
                byte_size=10,
                truncated=False,
                status=200,
            ),
        ),
    )
    assert match_asset_hashes(repo, snap) == []


def test_match_asset_hash_partial_match() -> None:
    fav_sha = "a" * 64
    css_sha = "b" * 64
    other_sha = "c" * 64
    repo = _repo(
        assets=(
            AssetFingerprint(
                relative_path="public/favicon.ico",
                sha256=fav_sha,
                byte_size=10,
                kind="favicon",
            ),
            AssetFingerprint(
                relative_path="public/app.css",
                sha256=css_sha,
                byte_size=10,
                kind="css",
            ),
        )
    )
    snap = _snapshot(
        fetched=(
            FetchedAsset(
                url="https://example.com/favicon.ico",
                sha256=fav_sha,
                byte_size=10,
                truncated=False,
                status=200,
            ),
            FetchedAsset(
                url="https://example.com/app.css",
                sha256=other_sha,
                byte_size=10,
                truncated=False,
                status=200,
            ),
        ),
    )
    signals = match_asset_hashes(repo, snap)
    assert len(signals) == 1
    assert "favicon" in signals[0].detail


def test_match_asset_hash_skips_truncated_fetched() -> None:
    sha = "d" * 64
    repo = _repo(
        assets=(
            AssetFingerprint(
                relative_path="public/favicon.ico",
                sha256=sha,
                byte_size=10,
                kind="favicon",
            ),
        )
    )
    snap = _snapshot(
        fetched=(
            FetchedAsset(
                url="https://example.com/favicon.ico",
                sha256=sha,
                byte_size=10,
                truncated=True,
                status=200,
            ),
        ),
    )
    assert match_asset_hashes(repo, snap) == []


def test_match_asset_hash_empty_inputs() -> None:
    repo = _repo()
    snap = _snapshot()
    assert match_asset_hashes(repo, snap) == []


def test_match_html_signature_meta_generator() -> None:
    repo = _repo(
        signatures=(HtmlSignature(kind="meta-generator", pattern="Next.js", weight="high"),)
    )
    snap = _snapshot(html=b'<meta name="generator" content="Next.js">')
    signals = match_html_signatures(repo, snap)
    assert len(signals) == 1
    assert signals[0].weight == "high"
    assert "meta-generator" in signals[0].detail or "Next.js" in signals[0].detail


def test_match_html_signature_class() -> None:
    repo = _repo(signatures=(HtmlSignature(kind="class", pattern="hero-section", weight="medium"),))
    snap = _snapshot(html=b'<div class="hero-section is-primary">')
    signals = match_html_signatures(repo, snap)
    assert len(signals) == 1
    assert signals[0].weight == "medium"


def test_match_html_signature_no_match() -> None:
    repo = _repo(signatures=(HtmlSignature(kind="meta-generator", pattern="Astro", weight="high"),))
    snap = _snapshot(html=b"<html>no match here</html>")
    assert match_html_signatures(repo, snap) == []


def test_match_html_signature_empty_html() -> None:
    repo = _repo(signatures=(HtmlSignature(kind="meta-generator", pattern="Astro", weight="high"),))
    snap = _snapshot(html=b"")
    assert match_html_signatures(repo, snap) == []


def test_match_html_signature_rejects_nested_quantifiers() -> None:
    # The HtmlSignature ctor doesn't validate regex shape; matcher must
    # silently skip dangerous patterns rather than executing them.
    repo = _repo(signatures=(HtmlSignature(kind="class", pattern="a*+b", weight="medium"),))
    snap = _snapshot(html=b"a*+b is right here in the html")
    # Pattern is dropped because it has a nested quantifier.
    assert match_html_signatures(repo, snap) == []


def test_match_html_signature_data_attr() -> None:
    repo = _repo(
        signatures=(
            HtmlSignature(
                kind="data-attr",
                pattern='data-template="saas"',
                weight="medium",
            ),
        )
    )
    snap = _snapshot(html=b'<body data-template="saas">')
    signals = match_html_signatures(repo, snap)
    assert len(signals) == 1
