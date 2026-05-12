"""Tests for the real Semgrep integration."""

import json
from pathlib import Path
from types import SimpleNamespace

from scanner.scanners.semgrep import scan_semgrep
from scanner.tools import semgrep_runner
from scanner.tools.semgrep_runner import SemgrepResult, find_semgrep_executable, run_semgrep


def test_semgrep_missing_returns_info_finding(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    monkeypatch.setattr(
        "scanner.scanners.semgrep.run_semgrep",
        lambda repo_path, raw_report_path: SemgrepResult(
            installed=False,
            raw_report_path=raw_report_path,
        ),
    )

    findings = scan_semgrep(repo_path, reports_dir)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "semgrep-not-installed"
    assert finding.tool == "semgrep"
    assert finding.severity == "info"
    assert finding.confidence == "high"


def test_semgrep_json_findings_map_to_normalized_schema(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    def fake_run_semgrep(repo_path: Path, raw_report_path: Path) -> SemgrepResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "check_id": "python.lang.security.audit.subprocess-shell-true",
                            "path": "src/app.py",
                            "start": {"line": 42, "col": 9},
                            "extra": {
                                "message": "Detected subprocess call with shell=True.",
                                "severity": "ERROR",
                                "metadata": {
                                    "remediation": "Avoid shell=True and pass arguments as a list."
                                },
                            },
                        },
                        {
                            "check_id": "python.lang.best-practice.requests",
                            "path": "src/client.py",
                            "start": {"line": 7, "col": 1},
                            "extra": {
                                "message": "Request without timeout.",
                                "severity": "WARNING",
                            },
                        },
                        {
                            "check_id": "python.lang.info.todo",
                            "path": "src/app.py",
                            "start": {"line": 3, "col": 1},
                            "extra": {
                                "message": "TODO comment.",
                                "severity": "INFO",
                            },
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        return SemgrepResult(
            installed=True,
            raw_report_path=raw_report_path,
            returncode=0,
        )

    monkeypatch.setattr("scanner.scanners.semgrep.run_semgrep", fake_run_semgrep)

    findings = scan_semgrep(repo_path, reports_dir)

    assert (reports_dir / "raw" / "semgrep.json").exists()
    assert [finding.severity for finding in findings] == ["high", "medium", "low"]
    assert findings[0].tool == "semgrep"
    assert findings[0].title == "python.lang.security.audit.subprocess-shell-true"
    assert findings[0].description == "Detected subprocess call with shell=True."
    assert findings[0].file == "src/app.py"
    assert findings[0].line == 42
    assert findings[0].recommendation == (
        "Avoid shell=True. Pass command arguments as a list and validate/allowlist "
        "user-controlled input."
    )
    assert findings[0].patch_before == 'subprocess.run(f"git log {branch}", shell=True)'
    assert findings[0].patch_after == 'subprocess.run(["git", "log", branch], check=True)'


def test_semgrep_runner_uses_json_report_command(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    raw_report_path = tmp_path / "reports" / "raw" / "semgrep.json"
    repo_path.mkdir()
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        raw_report_path.write_text('{"results": []}', encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        semgrep_runner, "find_semgrep_executable", lambda: "C:\\Python313\\Scripts\\semgrep.exe"
    )
    monkeypatch.setattr(semgrep_runner.subprocess, "run", fake_run)

    result = run_semgrep(repo_path=repo_path, raw_report_path=raw_report_path)

    assert result.installed is True
    assert result.returncode == 0
    assert captured["command"] == [
        "C:\\Python313\\Scripts\\semgrep.exe",
        "scan",
        "--config",
        "auto",
        "--json",
        "--output",
        str(raw_report_path),
        str(repo_path),
    ]
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "check": False,
    }


def test_semgrep_lookup_uses_python_scripts_fallback_when_path_lookup_fails(
    tmp_path: Path, monkeypatch
) -> None:
    fallback = tmp_path / "semgrep.exe"
    fallback.write_text("", encoding="utf-8")

    monkeypatch.setattr(semgrep_runner.shutil, "which", lambda name: None)
    monkeypatch.setattr(semgrep_runner, "PIP_USER_SEMGREP_PATH", fallback)

    assert find_semgrep_executable() == str(fallback)
