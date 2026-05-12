"""Tests for the real Gitleaks integration."""

import json
from pathlib import Path
from types import SimpleNamespace

from scanner.scanners.gitleaks import scan_gitleaks
from scanner.tools import gitleaks_runner
from scanner.tools.gitleaks_runner import GitleaksResult, find_gitleaks_executable, run_gitleaks


def test_gitleaks_missing_returns_info_finding(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    monkeypatch.setattr(
        "scanner.scanners.gitleaks.run_gitleaks",
        lambda repo_path, raw_report_path: GitleaksResult(
            installed=False,
            raw_report_path=raw_report_path,
        ),
    )

    findings = scan_gitleaks(repo_path, reports_dir)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "gitleaks-not-installed"
    assert finding.tool == "gitleaks"
    assert finding.severity == "info"
    assert finding.confidence == "high"


def test_gitleaks_json_findings_map_to_normalized_schema(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    def fake_run_gitleaks(repo_path: Path, raw_report_path: Path) -> GitleaksResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text(
            json.dumps(
                [
                    {
                        "RuleID": "generic-api-key",
                        "Description": "Detected a generic API key.",
                        "File": "src/settings.py",
                        "StartLine": 12,
                        "Fingerprint": "repo:src/settings.py:generic-api-key:12",
                    }
                ]
            ),
            encoding="utf-8",
        )
        return GitleaksResult(
            installed=True,
            raw_report_path=raw_report_path,
            returncode=1,
        )

    monkeypatch.setattr("scanner.scanners.gitleaks.run_gitleaks", fake_run_gitleaks)

    findings = scan_gitleaks(repo_path, reports_dir)

    assert (reports_dir / "raw" / "gitleaks.json").exists()
    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "repo:src/settings.py:generic-api-key:12"
    assert finding.tool == "gitleaks"
    assert finding.severity == "high"
    assert finding.title == "Potential secret detected: generic-api-key"
    assert finding.description == "Detected a generic API key."
    assert finding.file == "src/settings.py"
    assert finding.line == 12
    assert finding.recommendation == (
        "Rotate the exposed secret, remove it from source code, move it to environment variables, "
        "and rewrite git history if committed."
    )
    assert finding.patch_before == 'STRIPE_API_KEY = "sk_live_redacted"'
    assert finding.patch_after == 'STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]'
    assert finding.confidence == "high"


def test_gitleaks_runner_uses_json_report_command(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    raw_report_path = tmp_path / "reports" / "raw" / "gitleaks.json"
    repo_path.mkdir()
    captured: dict[str, list[str]] = {}

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        raw_report_path.write_text("[]", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        gitleaks_runner, "find_gitleaks_executable", lambda: "C:\\tools\\gitleaks.exe"
    )
    monkeypatch.setattr(gitleaks_runner.subprocess, "run", fake_run)

    result = run_gitleaks(repo_path=repo_path, raw_report_path=raw_report_path)

    assert result.installed is True
    assert result.returncode == 0
    assert captured["command"] == [
        "C:\\tools\\gitleaks.exe",
        "detect",
        "--source",
        str(repo_path),
        "--report-format",
        "json",
        "--report-path",
        str(raw_report_path),
        "--no-git",
    ]
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "check": False,
    }


def test_gitleaks_lookup_uses_winget_fallback_when_path_lookup_fails(
    tmp_path: Path, monkeypatch
) -> None:
    fallback = tmp_path / "gitleaks.exe"
    fallback.write_text("", encoding="utf-8")

    monkeypatch.setattr(gitleaks_runner.shutil, "which", lambda name: None)
    monkeypatch.setattr(gitleaks_runner, "WINGET_GITLEAKS_PATH", fallback)

    assert find_gitleaks_executable() == str(fallback)
