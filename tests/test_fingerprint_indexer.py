"""Tests for the fingerprint indexer."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest
from fingerprint.config import FingerprintConfig
from fingerprint.git_seeds import SeedEntry
from fingerprint.repo_index import (
    index_seed,
    load_fingerprints,
    write_fingerprint,
)
from fingerprint.run_index import main

from scanner.git_source import GitCloneError, GitCloneResult


def _populate_repo(repo_path: Path) -> None:
    """Populate a tiny fake template repo on disk."""
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / "public").mkdir(parents=True, exist_ok=True)
    (repo_path / "public" / "favicon.ico").write_bytes(b"icon")
    (repo_path / "public" / "app.css").write_bytes(b"body { color: red; }")
    (repo_path / "index.html").write_text(
        '<html><head><meta name="generator" content="Astro 4"></head>'
        '<body><div class="page-wrapper-main"></div></body></html>',
        encoding="utf-8",
    )
    (repo_path / "other.html").write_text(
        '<section class="page-wrapper-main"></section>',
        encoding="utf-8",
    )


def test_index_seed_runs_all_extractors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_repo = tmp_path / "fake-clone"
    _populate_repo(fake_repo)

    @contextmanager
    def fake_cloned_repo(url: str, depth: int = 1):
        yield GitCloneResult(url=url, repo_path=fake_repo, head_sha="abc1234")

    monkeypatch.setattr("fingerprint.repo_index.cloned_repo", fake_cloned_repo)

    seed = SeedEntry(
        slug="astro-x",
        repo_url="https://github.com/example/astro-x",
        notable_paths=("public/favicon.ico",),
    )
    config = FingerprintConfig()
    fp = index_seed(seed, config)
    assert fp.slug == "astro-x"
    assert fp.notes == ""
    asset_paths = {a.relative_path for a in fp.assets}
    assert "public/favicon.ico" in asset_paths
    assert any(s.pattern == "Astro 4" for s in fp.html_signatures)
    class_patterns = {s.pattern for s in fp.html_signatures if s.kind == "class"}
    assert "page-wrapper-main" in class_patterns


def test_index_seed_handles_clone_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def failing_cloned_repo(url: str, depth: int = 1):
        raise GitCloneError("simulated failure")
        yield  # pragma: no cover

    monkeypatch.setattr("fingerprint.repo_index.cloned_repo", failing_cloned_repo)

    seed = SeedEntry(slug="x", repo_url="https://github.com/a/b")
    config = FingerprintConfig()
    fp = index_seed(seed, config)
    assert fp.slug == "x"
    assert fp.assets == ()
    assert fp.html_signatures == ()
    assert "clone-failed" in fp.notes


def test_write_fingerprint_round_trips(tmp_path: Path) -> None:
    from fingerprint.models import AssetFingerprint, HtmlSignature, RepoFingerprint

    fingerprint = RepoFingerprint(
        slug="x",
        repo_url="https://github.com/a/b",
        indexed_at="2026-05-14T00:00:00Z",
        assets=(
            AssetFingerprint(
                relative_path="public/favicon.ico",
                sha256="b" * 64,
                byte_size=4,
                kind="favicon",
            ),
        ),
        html_signatures=(HtmlSignature(kind="meta-generator", pattern="Next.js", weight="high"),),
        notable_paths=("public/favicon.ico",),
    )

    db_dir = tmp_path / "db"
    path = write_fingerprint(fingerprint, db_dir)
    assert path.exists()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["slug"] == "x"

    loaded = load_fingerprints(db_dir)
    assert len(loaded) == 1
    assert loaded[0].slug == "x"
    assert loaded[0].assets[0].sha256 == "b" * 64


def test_load_fingerprints_skips_invalid_files(tmp_path: Path) -> None:
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    (db_dir / "broken.json").write_text("not json", encoding="utf-8")
    (db_dir / "bad-shape.json").write_text('{"slug": ""}', encoding="utf-8")
    assert load_fingerprints(db_dir) == ()


def test_load_fingerprints_missing_dir(tmp_path: Path) -> None:
    assert load_fingerprints(tmp_path / "does-not-exist") == ()


def test_run_index_rebuild(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_repo = tmp_path / "fake-clone"
    _populate_repo(fake_repo)

    @contextmanager
    def fake_cloned_repo(url: str, depth: int = 1):
        yield GitCloneResult(url=url, repo_path=fake_repo, head_sha="abc1234")

    monkeypatch.setattr("fingerprint.repo_index.cloned_repo", fake_cloned_repo)

    db_dir = tmp_path / "db"
    exit_code = main(["--rebuild", "--db-dir", str(db_dir)])
    assert exit_code == 0
    assert any(db_dir.glob("*.json"))


def test_run_index_single_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_repo = tmp_path / "fake-clone"
    _populate_repo(fake_repo)

    @contextmanager
    def fake_cloned_repo(url: str, depth: int = 1):
        yield GitCloneResult(url=url, repo_path=fake_repo, head_sha="abc1234")

    monkeypatch.setattr("fingerprint.repo_index.cloned_repo", fake_cloned_repo)

    db_dir = tmp_path / "db"
    exit_code = main(
        [
            "--repo-url",
            "https://github.com/example/x",
            "--db-dir",
            str(db_dir),
        ]
    )
    assert exit_code == 0
    written = list(db_dir.glob("*.json"))
    assert len(written) == 1
    assert "example-x" in written[0].name


def test_run_index_requires_source(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main([])
