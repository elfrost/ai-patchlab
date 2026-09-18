"""Tests for scan coverage reporting.

A report that says "3 findings" while two of five scanners never ran is true
and misleading at the same time. These tests pin the property that makes the
difference visible: every configured scanner gets a row, and a tool that did
not examine what it was pointed at cannot be silently absent.
"""

from __future__ import annotations

import json
from pathlib import Path

from scanner.coverage import (
    COVERAGE_STATUSES,
    EXPECTED_TOOLS,
    ToolCoverage,
    build_coverage,
    coverage_payload,
    incomplete_tools,
    is_complete,
    status_for_meta_finding,
)
from scanner.ignore import apply_ignore
from scanner.models import Finding
from scanner.report import build_report, write_reports
from scanner.scanners import SCANNERS
from scanner.tools.gitleaks_runner import GitleaksResult
from scanner.tools.semgrep_runner import SemgrepResult
from scanner.tools.trivy_runner import TrivyResult

AI_REVIEW_ENV_VARS = (
    "AI_PATCHLAB_AI_REVIEW_ENABLED",
    "AI_PATCHLAB_AI_REVIEW_PROVIDER",
    "AI_PATCHLAB_AI_REVIEW_COMMAND",
    "AI_PATCHLAB_AI_REVIEW_TIMEOUT_SECONDS",
)


def _meta(finding_id: str, tool: str, title: str = "Example state", **overrides: object) -> Finding:
    """Build a meta finding with defaults for the field under test."""
    base: dict[str, object] = {
        "id": finding_id,
        "tool": tool,
        "severity": "info",
        "title": title,
        "description": "Example description.",
        "file": "app.py",
        "line": None,
        "recommendation": "Install the tool.",
        "confidence": "high",
        "is_meta": True,
    }
    base.update(overrides)
    return Finding(**base)  # type: ignore[arg-type]


def _stub_external_tools(monkeypatch) -> None:
    """Report every external scanner as not installed, without touching PATH."""
    for var in AI_REVIEW_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(
        "scanner.scanners.gitleaks.run_gitleaks",
        lambda repo_path, raw_report_path: GitleaksResult(
            installed=False, raw_report_path=raw_report_path
        ),
    )
    monkeypatch.setattr(
        "scanner.scanners.semgrep.run_semgrep",
        lambda repo_path, raw_report_path: SemgrepResult(
            installed=False, raw_report_path=raw_report_path
        ),
    )
    monkeypatch.setattr(
        "scanner.scanners.trivy.run_trivy",
        lambda repo_path, raw_report_path: TrivyResult(
            installed=False, raw_report_path=raw_report_path
        ),
    )


class TestStatusDerivation:
    """Each meta finding id maps to exactly one coverage state."""

    def test_not_installed_means_not_run(self) -> None:
        assert status_for_meta_finding("semgrep-not-installed") == "not_run"

    def test_disabled_means_not_run(self) -> None:
        assert status_for_meta_finding("ai-review-disabled") == "not_run"

    def test_scan_error_means_error(self) -> None:
        assert status_for_meta_finding("semgrep-scan-error") == "error"

    def test_json_parse_error_means_error(self) -> None:
        assert status_for_meta_finding("trivy-json-parse-error") == "error"

    def test_command_error_means_error(self) -> None:
        assert status_for_meta_finding("ai-review-command-error") == "error"

    def test_partial_coverage_means_partial(self) -> None:
        assert status_for_meta_finding("semgrep-partial-coverage") == "partial"

    def test_no_supported_manifest_means_partial(self) -> None:
        assert status_for_meta_finding("dependency-scan-no-supported-manifest") == "partial"

    def test_unknown_meta_finding_defaults_to_partial(self) -> None:
        """An unmodelled scan-state signal must not read as full coverage."""
        assert status_for_meta_finding("semgrep-something-new") == "partial"

    def test_every_status_is_declared(self) -> None:
        derived = {
            status_for_meta_finding(finding_id)
            for finding_id in (
                "x-not-installed",
                "x-scan-error",
                "x-partial-coverage",
                "x-unknown",
            )
        }
        assert derived.issubset(set(COVERAGE_STATUSES))


class TestBuildCoverage:
    """Every configured scanner gets exactly one row, in registry order."""

    def test_every_expected_tool_gets_a_row(self) -> None:
        coverage = build_coverage([])
        assert tuple(row.tool for row in coverage) == EXPECTED_TOOLS

    def test_a_tool_that_reported_nothing_ran(self) -> None:
        """This is the whole point: silence means success, and must be stated."""
        coverage = build_coverage([])
        assert all(row.status == "ran" for row in coverage)

    def test_meta_finding_sets_the_status_and_detail(self) -> None:
        findings = [_meta("semgrep-not-installed", "semgrep", title="Semgrep is not installed")]
        row = build_coverage(findings)[0]
        assert row.tool == "semgrep"
        assert row.status == "not_run"
        assert row.detail == "Semgrep is not installed"
        assert row.meta_finding_ids == ("semgrep-not-installed",)

    def test_worst_status_wins(self) -> None:
        findings = [
            _meta("semgrep-partial-coverage", "semgrep"),
            _meta("semgrep-not-installed", "semgrep"),
        ]
        row = build_coverage(findings)[0]
        assert row.status == "not_run"
        assert len(row.meta_finding_ids) == 2

    def test_ordinary_findings_do_not_affect_coverage(self) -> None:
        findings = [
            _meta("sql-injection", "semgrep", severity="high", is_meta=False, confidence="medium")
        ]
        assert build_coverage(findings)[0].status == "ran"

    def test_unknown_tool_is_ignored(self) -> None:
        findings = [_meta("mystery-not-installed", "mystery-tool")]
        coverage = build_coverage(findings)
        assert tuple(row.tool for row in coverage) == EXPECTED_TOOLS

    def test_rejects_an_unsupported_status(self) -> None:
        try:
            ToolCoverage(tool="semgrep", status="maybe", detail="")
        except ValueError as exc:
            assert "maybe" in str(exc)
        else:  # pragma: no cover - guard
            raise AssertionError("ToolCoverage accepted an undeclared status")


class TestCompleteness:
    """`complete` is the flag a reader trusts, so its edges matter."""

    def test_all_ran_is_complete(self) -> None:
        assert is_complete(build_coverage([])) is True

    def test_a_missing_tool_is_incomplete(self) -> None:
        coverage = build_coverage([_meta("semgrep-not-installed", "semgrep")])
        assert is_complete(coverage) is False
        assert [row.tool for row in incomplete_tools(coverage)] == ["semgrep"]

    def test_disabled_ai_review_alone_stays_complete(self) -> None:
        """AI review is off by default (ADR-010) - a banner that always fires is ignored."""
        coverage = build_coverage([_meta("ai-review-disabled", "ai-security-review")])
        assert is_complete(coverage) is True

    def test_disabled_ai_review_does_not_mask_a_real_gap(self) -> None:
        coverage = build_coverage(
            [
                _meta("ai-review-disabled", "ai-security-review"),
                _meta("semgrep-not-installed", "semgrep"),
            ]
        )
        assert is_complete(coverage) is False

    def test_ai_review_command_error_is_a_real_gap(self) -> None:
        coverage = build_coverage([_meta("ai-review-command-error", "ai-security-review")])
        assert is_complete(coverage) is False

    def test_payload_counts_match_the_rows(self) -> None:
        payload = coverage_payload(build_coverage([_meta("trivy-scan-error", "trivy")]))
        assert payload["complete"] is False
        assert payload["incomplete_tool_count"] == 1
        assert payload["tool_count"] == len(EXPECTED_TOOLS)
        assert len(payload["tools"]) == len(EXPECTED_TOOLS)


class TestIgnoreImmunity:
    """`--ignore-file` must not be able to hide the fact that a tool never ran."""

    def test_coverage_survives_a_pattern_that_suppresses_the_meta_finding(self) -> None:
        findings = [_meta("semgrep-not-installed", "semgrep", file="app.py")]
        coverage = build_coverage(findings)

        surviving = apply_ignore(findings, ["*.py"])

        assert surviving == [], "precondition: the pattern must suppress the finding"
        assert coverage[0].status == "not_run"


class TestRegistryDrift:
    """Adding a scanner without adding it to coverage must fail here."""

    def test_expected_tools_matches_the_scanner_registry(self, tmp_path: Path, monkeypatch) -> None:
        _stub_external_tools(monkeypatch)
        repo_path = tmp_path / "empty-repo"
        repo_path.mkdir()
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()

        tools = {
            finding.tool
            for scanner in SCANNERS
            for finding in scanner(repo_path, reports_dir)
            if finding.is_meta
        }

        assert tools == set(EXPECTED_TOOLS)


class TestReportRendering:
    """The banner is the part a reader cannot miss, so it is pinned."""

    def test_no_coverage_key_when_not_supplied(self, tmp_path: Path) -> None:
        report = build_report(repo_path=tmp_path, findings=[])
        assert "coverage" not in report

    def test_banner_is_rendered_when_incomplete(self, tmp_path: Path) -> None:
        coverage = build_coverage([_meta("semgrep-not-installed", "semgrep")])
        paths = write_reports(
            repo_path=tmp_path,
            findings=[],
            reports_dir=tmp_path / "reports",
            coverage=coverage,
        )
        markdown = paths["markdown"].read_text(encoding="utf-8")
        assert "**Incomplete scan.**" in markdown
        assert "1 of 5 tools" in markdown
        assert "## Scan Coverage" in markdown
        assert "`not_run`" in markdown

    def test_no_banner_when_complete(self, tmp_path: Path) -> None:
        paths = write_reports(
            repo_path=tmp_path,
            findings=[],
            reports_dir=tmp_path / "reports",
            coverage=build_coverage([]),
        )
        markdown = paths["markdown"].read_text(encoding="utf-8")
        assert "Incomplete scan" not in markdown
        assert "## Scan Coverage" in markdown

    def test_coverage_json_is_written(self, tmp_path: Path) -> None:
        paths = write_reports(
            repo_path=tmp_path,
            findings=[],
            reports_dir=tmp_path / "reports",
            coverage=build_coverage([_meta("trivy-not-installed", "trivy")]),
        )
        assert paths["coverage"].name == "coverage.json"
        payload = json.loads(paths["coverage"].read_text(encoding="utf-8"))
        assert payload["complete"] is False
        assert payload["repository"]
        assert payload["generated_at"]
        assert {row["tool"] for row in payload["tools"]} == set(EXPECTED_TOOLS)

    def test_no_coverage_file_when_not_supplied(self, tmp_path: Path) -> None:
        reports_dir = tmp_path / "reports"
        paths = write_reports(repo_path=tmp_path, findings=[], reports_dir=reports_dir)
        assert "coverage" not in paths
        assert not (reports_dir / "coverage.json").exists()
