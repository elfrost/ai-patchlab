"""Tests for --from-git-url CLI handling."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

from scanner.git_source import GitCloneResult
from scanner.run_scan import main


def test_cli_requires_at_least_one_source(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main([])
    err = capsys.readouterr().err.lower()
    assert "required" in err or "one of the arguments" in err


def test_cli_rejects_both_repo_and_url(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "--repo",
                str(tmp_path),
                "--from-git-url",
                "https://github.com/owner/repo",
            ]
        )
    err = capsys.readouterr().err.lower()
    assert "not allowed with" in err or "argument --from-git-url" in err


def test_cli_runs_scan_from_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_clone = tmp_path / "cloned-repo"
    fake_clone.mkdir()
    reports_dir = tmp_path / "reports"

    @contextmanager
    def fake_cloned_repo(url: str, depth: int = 1):
        yield GitCloneResult(url=url, repo_path=fake_clone, head_sha="abc1234")

    monkeypatch.setattr("scanner.run_scan.cloned_repo", fake_cloned_repo)
    monkeypatch.setattr("scanner.run_scan.collect_findings", lambda repo, reports: [])

    exit_code = main(
        [
            "--from-git-url",
            "https://github.com/owner/repo",
            "--reports-dir",
            str(reports_dir),
        ]
    )
    assert exit_code == 0
    assert (reports_dir / "security_report.json").exists()


def test_cli_rejects_invalid_url(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    exit_code = main(
        [
            "--from-git-url",
            "not-a-valid-url",
            "--reports-dir",
            str(tmp_path / "reports"),
        ]
    )
    assert exit_code == 2
    err = capsys.readouterr().err
    assert "Not a recognized git URL" in err
