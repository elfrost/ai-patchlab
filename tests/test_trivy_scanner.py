"""Tests for the real Trivy integration."""

import json
from pathlib import Path
from types import SimpleNamespace

from scanner.scanners.trivy import scan_trivy
from scanner.tools import trivy_runner
from scanner.tools.trivy_runner import TrivyResult, find_trivy_executable, run_trivy


def test_trivy_missing_returns_info_finding(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    monkeypatch.setattr(
        "scanner.scanners.trivy.run_trivy",
        lambda repo_path, raw_report_path: TrivyResult(
            installed=False,
            raw_report_path=raw_report_path,
        ),
    )

    findings = scan_trivy(repo_path, reports_dir)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "trivy-not-installed"
    assert finding.tool == "trivy"
    assert finding.severity == "info"
    assert finding.confidence == "high"


def test_trivy_runner_uses_filesystem_json_report_command(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    raw_report_path = tmp_path / "reports" / "raw" / "trivy.json"
    repo_path.mkdir()
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        raw_report_path.write_text('{"Results": []}', encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(trivy_runner, "find_trivy_executable", lambda: "C:\\tools\\trivy.exe")
    monkeypatch.setattr(trivy_runner.subprocess, "run", fake_run)

    result = run_trivy(repo_path=repo_path, raw_report_path=raw_report_path)

    assert result.installed is True
    assert result.returncode == 0
    assert captured["command"] == [
        "C:\\tools\\trivy.exe",
        "fs",
        "--format",
        "json",
        "--output",
        str(raw_report_path),
        "--scanners",
        "vuln,misconfig",
        "--no-progress",
        "--skip-version-check",
        str(repo_path),
    ]
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "check": False,
    }


def test_trivy_runner_writes_empty_report_when_process_fails(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    raw_report_path = tmp_path / "reports" / "raw" / "trivy.json"
    repo_path.mkdir()

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        raise OSError("trivy failed to start")

    monkeypatch.setattr(trivy_runner, "find_trivy_executable", lambda: "trivy")
    monkeypatch.setattr(trivy_runner.subprocess, "run", fake_run)

    result = run_trivy(repo_path=repo_path, raw_report_path=raw_report_path)

    assert result.installed is True
    assert result.returncode == 127
    assert "trivy failed to start" in result.stderr
    assert json.loads(raw_report_path.read_text(encoding="utf-8")) == {"Results": []}


def test_trivy_runner_writes_empty_report_when_output_missing(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    raw_report_path = tmp_path / "reports" / "raw" / "trivy.json"
    repo_path.mkdir()

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(trivy_runner, "find_trivy_executable", lambda: "trivy")
    monkeypatch.setattr(trivy_runner.subprocess, "run", fake_run)

    result = run_trivy(repo_path=repo_path, raw_report_path=raw_report_path)

    assert result.installed is True
    assert raw_report_path.exists()
    assert json.loads(raw_report_path.read_text(encoding="utf-8")) == {"Results": []}


def test_trivy_lookup_uses_path_only(monkeypatch) -> None:
    monkeypatch.setattr(trivy_runner.shutil, "which", lambda name: "C:\\tools\\trivy.exe")

    assert find_trivy_executable() == "C:\\tools\\trivy.exe"


def test_trivy_invalid_json_returns_parse_error_finding(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    def fake_run_trivy(repo_path: Path, raw_report_path: Path) -> TrivyResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text("{invalid", encoding="utf-8")
        return TrivyResult(installed=True, raw_report_path=raw_report_path, returncode=0)

    monkeypatch.setattr("scanner.scanners.trivy.run_trivy", fake_run_trivy)

    findings = scan_trivy(repo_path, reports_dir)

    assert len(findings) == 1
    assert findings[0].id == "trivy-json-parse-error"
    assert findings[0].severity == "info"


def test_trivy_nonzero_without_findings_returns_scan_error(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    def fake_run_trivy(repo_path: Path, raw_report_path: Path) -> TrivyResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text('{"Results": []}', encoding="utf-8")
        return TrivyResult(
            installed=True,
            raw_report_path=raw_report_path,
            returncode=2,
            stderr="database error",
        )

    monkeypatch.setattr("scanner.scanners.trivy.run_trivy", fake_run_trivy)

    findings = scan_trivy(repo_path, reports_dir)

    assert len(findings) == 1
    assert findings[0].id == "trivy-scan-error"
    assert findings[0].description == "database error"


def test_trivy_vulnerability_maps_to_normalized_schema(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    def fake_run_trivy(repo_path: Path, raw_report_path: Path) -> TrivyResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text(
            json.dumps(
                {
                    "Results": [
                        {
                            "Target": "requirements.txt",
                            "Class": "lang-pkgs",
                            "Type": "pip",
                            "Vulnerabilities": [
                                {
                                    "VulnerabilityID": "CVE-2024-12345",
                                    "PkgName": "urllib3",
                                    "InstalledVersion": "1.26.0",
                                    "FixedVersion": "1.26.19",
                                    "Severity": "HIGH",
                                    "Title": "urllib3 request smuggling vulnerability",
                                    "Description": "urllib3 is affected by request smuggling.",
                                    "PrimaryURL": "https://avd.aquasec.com/nvd/cve-2024-12345",
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return TrivyResult(installed=True, raw_report_path=raw_report_path, returncode=0)

    monkeypatch.setattr("scanner.scanners.trivy.run_trivy", fake_run_trivy)

    findings = scan_trivy(repo_path, reports_dir)

    assert (reports_dir / "raw" / "trivy.json").exists()
    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "trivy-vuln-CVE-2024-12345-urllib3-requirements.txt-1.26.0"
    assert finding.tool == "trivy"
    assert finding.severity == "high"
    assert finding.title == "urllib3 request smuggling vulnerability"
    assert finding.file == "requirements.txt"
    assert finding.line is None
    assert "Package: urllib3" in finding.description
    assert "Upgrade urllib3 to fixed version 1.26.19." in finding.recommendation
    assert "https://avd.aquasec.com/nvd/cve-2024-12345" in finding.recommendation
    assert finding.confidence == "high"


def test_trivy_nonzero_with_vulnerability_still_returns_finding(
    tmp_path: Path, monkeypatch
) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    def fake_run_trivy(repo_path: Path, raw_report_path: Path) -> TrivyResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text(
            json.dumps(
                {
                    "Results": [
                        {
                            "Target": "package-lock.json",
                            "Vulnerabilities": [
                                {
                                    "VulnerabilityID": "GHSA-example",
                                    "PkgName": "demo",
                                    "Severity": "MEDIUM",
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return TrivyResult(installed=True, raw_report_path=raw_report_path, returncode=2)

    monkeypatch.setattr("scanner.scanners.trivy.run_trivy", fake_run_trivy)

    findings = scan_trivy(repo_path, reports_dir)

    assert len(findings) == 1
    assert findings[0].severity == "medium"
    assert findings[0].confidence == "medium"


def test_trivy_misconfiguration_maps_to_normalized_schema(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    def fake_run_trivy(repo_path: Path, raw_report_path: Path) -> TrivyResult:
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text(
            json.dumps(
                {
                    "Results": [
                        {
                            "Target": "Dockerfile",
                            "Class": "config",
                            "Type": "dockerfile",
                            "Misconfigurations": [
                                {
                                    "ID": "DS002",
                                    "AVDID": "AVD-DS-0002",
                                    "Severity": "CRITICAL",
                                    "Title": "Root user configured",
                                    "Description": "The container runs as root.",
                                    "Message": "Specify a non-root USER.",
                                    "Resolution": "Add a USER instruction with a non-root user.",
                                    "CauseMetadata": {
                                        "Resource": "Dockerfile",
                                        "StartLine": 12,
                                        "EndLine": 13,
                                    },
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return TrivyResult(installed=True, raw_report_path=raw_report_path, returncode=0)

    monkeypatch.setattr("scanner.scanners.trivy.run_trivy", fake_run_trivy)

    findings = scan_trivy(repo_path, reports_dir)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "trivy-misconfig-DS002-Dockerfile-12"
    assert finding.tool == "trivy"
    assert finding.severity == "critical"
    assert finding.title == "Root user configured"
    assert finding.description == "The container runs as root."
    assert finding.file == "Dockerfile"
    assert finding.line == 12
    assert finding.recommendation == "Add a USER instruction with a non-root user."
    assert finding.confidence == "medium"
