"""Tests for fingerprint match report writers and CLI."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fingerprint.config import FingerprintConfig
from fingerprint.models import MatchResult, MatchSignal
from fingerprint.report import (
    DISCLAIMER,
    build_match_payload,
    report_paths,
    write_json_report,
    write_markdown_report,
)
from fingerprint.run_match import main as match_main
from fingerprint.run_match import run_match


def _result(score: float, slug: str = "x", signals: tuple[MatchSignal, ...] = ()) -> MatchResult:
    from fingerprint.models import band_for_score

    return MatchResult(
        target_url="https://example.com/",
        fetched_at="2026-05-14T00:00:00Z",
        repo_slug=slug,
        score=score,
        band=band_for_score(score),
        signals=signals,
        notes="ok",
    )


def test_disclaimer_present_with_empty_results(tmp_path: Path) -> None:
    payload = build_match_payload(
        target_url="https://example.com/",
        fetched_at="2026-05-14T00:00:00Z",
        results=(),
        notes="ok",
    )
    md = tmp_path / "report.md"
    write_markdown_report(payload, md)
    text = md.read_text(encoding="utf-8")
    assert DISCLAIMER in text
    assert "Probable template match" in text
    assert "manual verification required" in text


def test_markdown_groups_by_band(tmp_path: Path) -> None:
    strong = _result(0.8, "strong-match")
    plausible = _result(0.4, "plausible-match")
    weak = _result(0.1, "weak-match")
    payload = build_match_payload(
        target_url="https://example.com/",
        fetched_at="2026-05-14T00:00:00Z",
        results=(weak, plausible, strong),
        notes="ok",
    )
    md = tmp_path / "report.md"
    write_markdown_report(payload, md)
    text = md.read_text(encoding="utf-8")

    strong_idx = text.find("Strong matches")
    plausible_idx = text.find("Plausible matches")
    weak_idx = text.find("Weak matches")
    assert strong_idx < plausible_idx < weak_idx
    assert text.find("strong-match") < text.find("plausible-match") < text.find("weak-match")


def test_markdown_disclaimer_never_uses_attribution_words(tmp_path: Path) -> None:
    payload = build_match_payload(
        target_url="https://example.com/",
        fetched_at="2026-05-14T00:00:00Z",
        results=(_result(0.9, "x"),),
        notes="ok",
    )
    md = tmp_path / "report.md"
    write_markdown_report(payload, md)
    text = md.read_text(encoding="utf-8").lower()
    for forbidden in ("confirmed", "proven", "stolen", "copied"):
        assert forbidden not in text, f"forbidden attribution word in report: {forbidden}"


def test_markdown_min_score_drops_low_results(tmp_path: Path) -> None:
    payload = build_match_payload(
        target_url="https://example.com/",
        fetched_at="2026-05-14T00:00:00Z",
        results=(_result(0.8, "high-score"), _result(0.05, "low-score")),
        notes="ok",
    )
    md = tmp_path / "report.md"
    write_markdown_report(payload, md, min_score=0.3)
    text = md.read_text(encoding="utf-8")
    assert "high-score" in text
    assert "low-score" not in text


def test_json_includes_all_results_regardless_of_min_score(tmp_path: Path) -> None:
    payload = build_match_payload(
        target_url="https://example.com/",
        fetched_at="2026-05-14T00:00:00Z",
        results=(_result(0.8, "high"), _result(0.05, "low")),
        notes="ok",
    )
    j = tmp_path / "report.json"
    write_json_report(payload, j)
    data = json.loads(j.read_text(encoding="utf-8"))
    assert data["disclaimer"] == DISCLAIMER
    slugs = {r["repo_slug"] for r in data["results"]}
    assert slugs == {"high", "low"}


def test_report_paths_sanitize_host() -> None:
    when = datetime(2026, 5, 14, 12, 34, 56, tzinfo=UTC)
    paths = report_paths(
        "https://Sub.Example.COM:8080/path",
        Path("reports/fingerprint"),
        when=when,
    )
    assert paths["json"].name == "match_sub-example-com-8080_20260514-123456.json"
    assert paths["markdown"].name == "match_sub-example-com-8080_20260514-123456.md"


def _populate_db(db_dir: Path) -> None:
    db_dir.mkdir(parents=True, exist_ok=True)
    fp = {
        "slug": "vercel-commerce",
        "repo_url": "https://github.com/vercel/commerce",
        "indexed_at": "2026-05-14T00:00:00Z",
        "assets": [
            {
                "relative_path": "public/favicon.ico",
                "sha256": "a" * 64,
                "byte_size": 4,
                "kind": "favicon",
            }
        ],
        "html_signatures": [{"kind": "meta-generator", "pattern": "Next.js", "weight": "high"}],
        "notable_paths": ["public/favicon.ico"],
        "notes": "",
    }
    (db_dir / "vercel-commerce.json").write_text(json.dumps(fp), encoding="utf-8")


def test_run_match_empty_db_still_writes_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    routes = {
        "https://example.com/robots.txt": httpx.Response(404),
        "https://example.com/": httpx.Response(200, text="<html></html>"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return routes.get(str(request.url), httpx.Response(404))

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "fingerprint.run_match.fetch_target",
        lambda url, cfg, paths: __import__(
            "fingerprint.web_probe", fromlist=["fetch_target"]
        ).fetch_target(url, cfg, paths, transport=transport),
    )

    config = FingerprintConfig(
        db_dir=tmp_path / "empty-db",
        report_dir=tmp_path / "reports",
    )
    paths = run_match("https://example.com/", config)
    assert paths["json"].exists()
    assert paths["markdown"].exists()
    data = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert "no-fingerprints-in-db" in data["notes"]


def test_run_match_with_db_produces_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db_dir = tmp_path / "db"
    _populate_db(db_dir)

    routes = {
        "https://example.com/robots.txt": httpx.Response(404),
        "https://example.com/": httpx.Response(
            200, text='<meta name="generator" content="Next.js">'
        ),
        # SHA-256 of 4 "a" bytes is computed at runtime; use favicon.ico path
        "https://example.com/public/favicon.ico": httpx.Response(200, content=b"\xaa\xaa\xaa\xaa"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return routes.get(str(request.url), httpx.Response(404))

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "fingerprint.run_match.fetch_target",
        lambda url, cfg, paths: __import__(
            "fingerprint.web_probe", fromlist=["fetch_target"]
        ).fetch_target(url, cfg, paths, transport=transport),
    )

    config = FingerprintConfig(db_dir=db_dir, report_dir=tmp_path / "reports")
    paths = run_match("https://example.com/", config)
    data = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert len(data["results"]) == 1
    result = data["results"][0]
    # The meta-generator html signal must have fired.
    signal_details = [s["detail"] for s in result["signals"]]
    assert any("Next.js" in detail for detail in signal_details)


def test_run_match_bad_scheme_writes_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = FingerprintConfig(db_dir=tmp_path / "db", report_dir=tmp_path / "reports")
    paths = run_match("file:///etc/passwd", config)
    assert paths["json"].exists()
    data = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert "bad-scheme" in data["notes"]


def test_match_cli_returns_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    routes = {
        "https://example.com/robots.txt": httpx.Response(404),
        "https://example.com/": httpx.Response(200, text="<html></html>"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return routes.get(str(request.url), httpx.Response(404))

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "fingerprint.run_match.fetch_target",
        lambda url, cfg, paths: __import__(
            "fingerprint.web_probe", fromlist=["fetch_target"]
        ).fetch_target(url, cfg, paths, transport=transport),
    )

    exit_code = match_main(
        [
            "--target",
            "https://example.com/",
            "--db-dir",
            str(tmp_path / "db"),
            "--report-dir",
            str(tmp_path / "reports"),
        ]
    )
    assert exit_code == 0
