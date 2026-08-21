"""Tests for fingerprint data contracts and seed loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fingerprint.git_seeds import (
    SEEDS_DEFAULT_PATH,
    SeedEntry,
    SeedLoadError,
    load_seeds,
    slug_from_repo_url,
)
from fingerprint.models import (
    AssetFingerprint,
    HtmlSignature,
    MatchResult,
    MatchSignal,
    RepoFingerprint,
    band_for_score,
)

VALID_SHA = "a" * 64


def test_band_for_score_boundaries() -> None:
    assert band_for_score(0.0) == "weak"
    assert band_for_score(0.29) == "weak"
    assert band_for_score(0.3) == "plausible"
    assert band_for_score(0.59) == "plausible"
    assert band_for_score(0.6) == "strong"
    assert band_for_score(1.0) == "strong"


def test_band_for_score_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        band_for_score(-0.1)
    with pytest.raises(ValueError):
        band_for_score(1.1)


def test_asset_fingerprint_validates_sha256() -> None:
    AssetFingerprint(
        relative_path="public/favicon.ico",
        sha256=VALID_SHA,
        byte_size=100,
        kind="favicon",
    )
    with pytest.raises(ValueError):
        AssetFingerprint(
            relative_path="favicon.ico",
            sha256="not-a-sha",
            byte_size=10,
            kind="favicon",
        )


def test_asset_fingerprint_validates_kind() -> None:
    with pytest.raises(ValueError):
        AssetFingerprint(
            relative_path="favicon.ico",
            sha256=VALID_SHA,
            byte_size=10,
            kind="not-a-kind",
        )


def test_asset_fingerprint_rejects_empty_relative_path() -> None:
    with pytest.raises(ValueError):
        AssetFingerprint(
            relative_path="   ",
            sha256=VALID_SHA,
            byte_size=10,
            kind="favicon",
        )


def test_asset_fingerprint_rejects_negative_size() -> None:
    with pytest.raises(ValueError):
        AssetFingerprint(
            relative_path="favicon.ico",
            sha256=VALID_SHA,
            byte_size=-1,
            kind="favicon",
        )


def test_html_signature_validates_kind() -> None:
    HtmlSignature(kind="meta-generator", pattern="Next.js", weight="high")
    with pytest.raises(ValueError):
        HtmlSignature(kind="bogus", pattern="x", weight="high")


def test_html_signature_validates_weight() -> None:
    with pytest.raises(ValueError):
        HtmlSignature(kind="class", pattern="hero", weight="ultra")


def test_html_signature_rejects_empty_pattern() -> None:
    with pytest.raises(ValueError):
        HtmlSignature(kind="class", pattern="", weight="medium")


def test_repo_fingerprint_minimum_valid() -> None:
    fp = RepoFingerprint(
        slug="vercel-commerce",
        repo_url="https://github.com/vercel/commerce",
        indexed_at="2026-05-14T00:00:00Z",
    )
    assert fp.slug == "vercel-commerce"
    assert fp.assets == ()


def test_repo_fingerprint_rejects_bad_url() -> None:
    with pytest.raises(ValueError):
        RepoFingerprint(
            slug="x",
            repo_url="ftp://example.com/repo",
            indexed_at="2026-05-14T00:00:00Z",
        )


def test_repo_fingerprint_to_dict_round_trip() -> None:
    asset = AssetFingerprint(
        relative_path="favicon.ico",
        sha256=VALID_SHA,
        byte_size=42,
        kind="favicon",
    )
    sig = HtmlSignature(kind="meta-generator", pattern="Next.js", weight="high")
    fp = RepoFingerprint(
        slug="x",
        repo_url="https://github.com/x/y",
        indexed_at="2026-05-14T00:00:00Z",
        assets=(asset,),
        html_signatures=(sig,),
        notable_paths=("public/favicon.ico",),
    )
    data = fp.to_dict()
    assert data["slug"] == "x"
    assert data["assets"][0]["sha256"] == VALID_SHA
    assert data["html_signatures"][0]["pattern"] == "Next.js"
    assert data["notable_paths"] == ["public/favicon.ico"]


def test_match_signal_validates() -> None:
    MatchSignal(kind="favicon-hash", detail="favicon SHA-256 match", weight="high")
    with pytest.raises(ValueError):
        MatchSignal(kind="", detail="x", weight="high")
    with pytest.raises(ValueError):
        MatchSignal(kind="x", detail="x", weight="medium-rare")


def test_match_result_rejects_band_score_mismatch() -> None:
    with pytest.raises(ValueError):
        MatchResult(
            target_url="https://example.com",
            fetched_at="2026-05-14T00:00:00Z",
            repo_slug="x",
            score=0.5,
            band="strong",  # 0.5 is plausible, not strong
        )


def test_match_result_accepts_valid_band() -> None:
    result = MatchResult(
        target_url="https://example.com",
        fetched_at="2026-05-14T00:00:00Z",
        repo_slug="x",
        score=0.8,
        band="strong",
    )
    assert result.band == "strong"


def test_match_result_to_dict() -> None:
    signal = MatchSignal(kind="favicon-hash", detail="match", weight="high")
    result = MatchResult(
        target_url="https://example.com",
        fetched_at="2026-05-14T00:00:00Z",
        repo_slug="x",
        score=0.0,
        band="weak",
        signals=(signal,),
        notes="ok",
    )
    data = result.to_dict()
    assert data["repo_slug"] == "x"
    assert data["signals"][0]["weight"] == "high"


def test_seed_entry_validates_slug() -> None:
    with pytest.raises(SeedLoadError):
        SeedEntry(slug="Bad Slug", repo_url="https://github.com/x/y")


def test_seed_entry_rejects_non_https() -> None:
    with pytest.raises(SeedLoadError):
        SeedEntry(slug="x", repo_url="http://github.com/x/y")


def test_load_seeds_default_file() -> None:
    seeds = load_seeds()
    assert len(seeds) >= 3
    for seed in seeds:
        assert seed.repo_url.startswith("https://")
        assert seed.slug


def test_load_seeds_rejects_duplicate_slug(tmp_path: Path) -> None:
    path = tmp_path / "repos.json"
    path.write_text(
        json.dumps(
            [
                {"slug": "x", "repo_url": "https://github.com/a/b"},
                {"slug": "x", "repo_url": "https://github.com/c/d"},
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(SeedLoadError):
        load_seeds(path)


def test_load_seeds_rejects_non_list(tmp_path: Path) -> None:
    path = tmp_path / "repos.json"
    path.write_text('{"not": "a list"}', encoding="utf-8")
    with pytest.raises(SeedLoadError):
        load_seeds(path)


def test_load_seeds_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SeedLoadError):
        load_seeds(tmp_path / "missing.json")


def test_load_seeds_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "repos.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(SeedLoadError):
        load_seeds(path)


def test_load_seeds_rejects_non_https_entry(tmp_path: Path) -> None:
    path = tmp_path / "repos.json"
    path.write_text(
        json.dumps([{"slug": "x", "repo_url": "http://github.com/a/b"}]),
        encoding="utf-8",
    )
    with pytest.raises(SeedLoadError):
        load_seeds(path)


def test_load_seeds_notable_paths_must_be_list(tmp_path: Path) -> None:
    path = tmp_path / "repos.json"
    path.write_text(
        json.dumps(
            [
                {
                    "slug": "x",
                    "repo_url": "https://github.com/a/b",
                    "notable_paths": "favicon.ico",
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(SeedLoadError):
        load_seeds(path)


def test_default_seed_file_exists() -> None:
    assert SEEDS_DEFAULT_PATH.exists()


def test_slug_from_repo_url_github() -> None:
    assert slug_from_repo_url("https://github.com/vercel/commerce") == "vercel-commerce"
    assert slug_from_repo_url("https://github.com/vercel/commerce.git") == "vercel-commerce"
    assert slug_from_repo_url("https://github.com/jekyll/minima/") == "jekyll-minima"


def test_slug_from_repo_url_fallback() -> None:
    slug = slug_from_repo_url("https://example.com/my-repo")
    assert slug == "my-repo"
