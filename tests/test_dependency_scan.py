"""Tests for the real dependency scanner integration."""

import json
from pathlib import Path
from types import SimpleNamespace

from scanner.scanners.dependency_scan import scan_dependencies
from scanner.tools import pip_audit_runner
from scanner.tools.pip_audit_runner import (
    PipAuditInput,
    PipAuditResult,
    find_pip_audit_input,
    run_pip_audit,
)


def test_dependency_scan_without_supported_manifest_returns_info(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    findings = scan_dependencies(repo_path, reports_dir)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "dependency-scan-no-supported-manifest"
    assert finding.tool == "dependency-scan"
    assert finding.severity == "info"
    assert finding.confidence == "high"


def test_dependency_scan_missing_pip_audit_returns_info(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    requirements_path = repo_path / "requirements.txt"
    requirements_path.write_text("flask==0.5\n", encoding="utf-8")

    monkeypatch.setattr(
        "scanner.scanners.dependency_scan.run_pip_audit",
        lambda repo_path, raw_report_path, audit_input: PipAuditResult(
            installed=False,
            raw_report_path=raw_report_path,
            audit_input=audit_input,
        ),
    )

    findings = scan_dependencies(repo_path, reports_dir)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "pip-audit-not-installed"
    assert finding.file == str(requirements_path)
    assert finding.severity == "info"


def test_pip_audit_runner_uses_requirements_json_report_command(
    tmp_path: Path, monkeypatch
) -> None:
    repo_path = tmp_path / "repo"
    raw_report_path = tmp_path / "reports" / "raw" / "pip-audit.json"
    repo_path.mkdir()
    requirements_path = repo_path / "requirements.txt"
    requirements_path.write_text("flask==0.5\n", encoding="utf-8")
    audit_input = PipAuditInput(kind="requirements", paths=(requirements_path,))
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        raw_report_path.write_text("[]", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        pip_audit_runner,
        "find_pip_audit_command",
        lambda: ["C:\\tools\\pip-audit.exe"],
    )
    monkeypatch.setattr(pip_audit_runner.subprocess, "run", fake_run)

    result = run_pip_audit(
        repo_path=repo_path,
        raw_report_path=raw_report_path,
        audit_input=audit_input,
    )

    assert result.installed is True
    assert result.returncode == 0
    assert captured["command"] == [
        "C:\\tools\\pip-audit.exe",
        "--format",
        "json",
        "--output",
        str(raw_report_path),
        "--progress-spinner",
        "off",
        "--requirement",
        str(requirements_path),
    ]
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "check": False,
        # pip-audit has no internal time bound and has hung entire scans.
        "timeout": pip_audit_runner.DEFAULT_TIMEOUT_SECONDS,
    }


def test_pip_audit_runner_uses_project_command_for_pyproject(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    raw_report_path = tmp_path / "reports" / "raw" / "pip-audit.json"
    repo_path.mkdir()
    (repo_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    audit_input = PipAuditInput(kind="project", paths=(repo_path,))
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        captured["command"] = command
        raw_report_path.write_text("[]", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(pip_audit_runner, "find_pip_audit_command", lambda: ["pip-audit"])
    monkeypatch.setattr(pip_audit_runner.subprocess, "run", fake_run)

    run_pip_audit(
        repo_path=repo_path,
        raw_report_path=raw_report_path,
        audit_input=audit_input,
    )

    assert captured["command"] == [
        "pip-audit",
        "--format",
        "json",
        "--output",
        str(raw_report_path),
        "--progress-spinner",
        "off",
        str(repo_path),
    ]


def test_pip_audit_runner_writes_empty_report_when_process_fails(
    tmp_path: Path, monkeypatch
) -> None:
    repo_path = tmp_path / "repo"
    raw_report_path = tmp_path / "reports" / "raw" / "pip-audit.json"
    repo_path.mkdir()
    requirements_path = repo_path / "requirements.txt"
    requirements_path.write_text("flask==0.5\n", encoding="utf-8")
    audit_input = PipAuditInput(kind="requirements", paths=(requirements_path,))

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        raise OSError("pip-audit failed to start")

    monkeypatch.setattr(pip_audit_runner, "find_pip_audit_command", lambda: ["pip-audit"])
    monkeypatch.setattr(pip_audit_runner.subprocess, "run", fake_run)

    result = run_pip_audit(
        repo_path=repo_path,
        raw_report_path=raw_report_path,
        audit_input=audit_input,
    )

    assert result.installed is True
    assert result.returncode == 127
    assert "pip-audit failed to start" in result.stderr
    assert json.loads(raw_report_path.read_text(encoding="utf-8")) == []


def test_find_pip_audit_input_prefers_requirements(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    requirements_path = repo_path / "requirements.txt"
    requirements_path.write_text("flask==0.5\n", encoding="utf-8")
    (repo_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    audit_input = find_pip_audit_input(repo_path)

    assert audit_input == PipAuditInput(kind="requirements", paths=(requirements_path,))


def test_dependency_scan_invalid_json_returns_parse_error(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    requirements_path = repo_path / "requirements.txt"
    requirements_path.write_text("flask==0.5\n", encoding="utf-8")

    def fake_run_pip_audit(
        repo_path: Path,
        raw_report_path: Path,
        audit_input: PipAuditInput,
    ) -> PipAuditResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text("{invalid", encoding="utf-8")
        return PipAuditResult(
            installed=True,
            raw_report_path=raw_report_path,
            audit_input=audit_input,
            returncode=0,
        )

    monkeypatch.setattr("scanner.scanners.dependency_scan.run_pip_audit", fake_run_pip_audit)

    findings = scan_dependencies(repo_path, reports_dir)

    assert len(findings) == 1
    assert findings[0].id == "pip-audit-json-parse-error"
    assert findings[0].severity == "info"


def test_dependency_scan_error_without_findings_returns_scan_error(
    tmp_path: Path, monkeypatch
) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    requirements_path = repo_path / "requirements.txt"
    requirements_path.write_text("flask==0.5\n", encoding="utf-8")

    def fake_run_pip_audit(
        repo_path: Path,
        raw_report_path: Path,
        audit_input: PipAuditInput,
    ) -> PipAuditResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text("[]", encoding="utf-8")
        return PipAuditResult(
            installed=True,
            raw_report_path=raw_report_path,
            audit_input=audit_input,
            returncode=2,
            stderr="resolution failed",
        )

    monkeypatch.setattr("scanner.scanners.dependency_scan.run_pip_audit", fake_run_pip_audit)

    findings = scan_dependencies(repo_path, reports_dir)

    assert len(findings) == 1
    assert findings[0].id == "pip-audit-scan-error"
    assert findings[0].description == "resolution failed"


def test_dependency_vulnerability_maps_to_normalized_schema(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    requirements_path = repo_path / "requirements.txt"
    requirements_path.write_text("flask==0.5\n", encoding="utf-8")

    def fake_run_pip_audit(
        repo_path: Path,
        raw_report_path: Path,
        audit_input: PipAuditInput,
    ) -> PipAuditResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text(
            json.dumps(
                [
                    {
                        "name": "flask",
                        "version": "0.5",
                        "vulns": [
                            {
                                "id": "PYSEC-2019-179",
                                "fix_versions": ["1.0"],
                                "aliases": ["CVE-2019-1010083", "GHSA-5wv5-4vpf-pj6m"],
                                "description": "Flask before 1.0 is affected by denial of service.",
                            }
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )
        return PipAuditResult(
            installed=True,
            raw_report_path=raw_report_path,
            audit_input=audit_input,
            returncode=1,
        )

    monkeypatch.setattr("scanner.scanners.dependency_scan.run_pip_audit", fake_run_pip_audit)

    findings = scan_dependencies(repo_path, reports_dir)

    assert (reports_dir / "raw" / "pip-audit.json").exists()
    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "dependency-scan-flask-0.5-PYSEC-2019-179"
    assert finding.tool == "dependency-scan"
    assert finding.severity == "high"
    assert finding.title == "Vulnerable dependency: flask PYSEC-2019-179"
    assert finding.file == str(requirements_path)
    assert finding.line is None
    assert "Package: flask" in finding.description
    assert "CVE-2019-1010083" in finding.description
    assert "Upgrade flask to a fixed version: 1.0." in finding.recommendation
    assert finding.confidence == "high"


def test_dependency_scan_supports_current_dependencies_json_shape(
    tmp_path: Path, monkeypatch
) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    requirements_path = repo_path / "requirements.txt"
    requirements_path.write_text("django==1.2\n", encoding="utf-8")

    def fake_run_pip_audit(
        repo_path: Path,
        raw_report_path: Path,
        audit_input: PipAuditInput,
    ) -> PipAuditResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text(
            json.dumps(
                {
                    "dependencies": [
                        {
                            "name": "django",
                            "version": "1.2",
                            "vulns": [
                                {
                                    "id": "GHSA-example",
                                    "fix_versions": [],
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return PipAuditResult(
            installed=True,
            raw_report_path=raw_report_path,
            audit_input=audit_input,
            returncode=1,
        )

    monkeypatch.setattr("scanner.scanners.dependency_scan.run_pip_audit", fake_run_pip_audit)

    findings = scan_dependencies(repo_path, reports_dir)

    assert len(findings) == 1
    assert findings[0].severity == "medium"
    assert "Review advisory GHSA-example" in findings[0].recommendation
