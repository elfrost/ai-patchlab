"""Tests for the initial scanner foundation."""

import json
from pathlib import Path

from scanner.models import FINDING_FIELDS, SEVERITIES
from scanner.run_scan import main, run_scan
from scanner.tools.gitleaks_runner import GitleaksResult
from scanner.tools.semgrep_runner import SemgrepResult
from scanner.tools.trivy_runner import TrivyResult


def test_run_scan_creates_json_and_markdown_reports(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "target-repo"
    repo_path.mkdir()
    reports_dir = tmp_path / "reports"

    for var in (
        "AI_PATCHLAB_AI_REVIEW_ENABLED",
        "AI_PATCHLAB_AI_REVIEW_PROVIDER",
        "AI_PATCHLAB_AI_REVIEW_COMMAND",
        "AI_PATCHLAB_AI_REVIEW_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(var, raising=False)

    monkeypatch.setattr(
        "scanner.scanners.gitleaks.run_gitleaks",
        lambda repo_path, raw_report_path: GitleaksResult(
            installed=False,
            raw_report_path=raw_report_path,
        ),
    )
    monkeypatch.setattr(
        "scanner.scanners.semgrep.run_semgrep",
        lambda repo_path, raw_report_path: SemgrepResult(
            installed=False,
            raw_report_path=raw_report_path,
        ),
    )
    monkeypatch.setattr(
        "scanner.scanners.trivy.run_trivy",
        lambda repo_path, raw_report_path: TrivyResult(
            installed=False,
            raw_report_path=raw_report_path,
        ),
    )

    def _fail_subprocess(*args, **kwargs):
        raise AssertionError("AI review must not invoke subprocess when disabled.")

    monkeypatch.setattr(
        "scanner.tools.ai_review_runner.subprocess.run",
        _fail_subprocess,
    )

    report_paths = run_scan(repo_path=repo_path, reports_dir=reports_dir)

    assert report_paths["json"] == reports_dir / "security_report.json"
    assert report_paths["markdown"] == reports_dir / "security_report.md"
    assert report_paths["json"].exists()
    assert report_paths["markdown"].exists()

    report = json.loads(report_paths["json"].read_text(encoding="utf-8"))
    assert set(report["findings_by_severity"]) == set(SEVERITIES)
    assert report["summary"]["info"] == 5

    findings = report["findings_by_severity"]["info"]
    assert {finding["tool"] for finding in findings} == {
        "semgrep",
        "gitleaks",
        "trivy",
        "dependency-scan",
        "ai-security-review",
    }
    ai_review_findings = [
        finding for finding in findings if finding["tool"] == "ai-security-review"
    ]
    assert len(ai_review_findings) == 1
    assert ai_review_findings[0]["id"] == "ai-review-disabled"
    for finding in findings:
        assert set(FINDING_FIELDS).issubset(finding)
        assert "patch_before" in finding
        assert "patch_after" in finding
        assert "remediation_explanation" in finding

    markdown = report_paths["markdown"].read_text(encoding="utf-8")
    assert "# AI PatchLab Security Report" in markdown
    assert "Semgrep is not installed" in markdown


def test_cli_returns_error_for_missing_repo(tmp_path: Path) -> None:
    missing_repo = tmp_path / "missing"

    exit_code = main(["--repo", str(missing_repo), "--reports-dir", str(tmp_path / "reports")])

    assert exit_code == 2
