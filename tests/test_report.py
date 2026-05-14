"""Tests for severity filtering and top-finding selection in reports."""

from __future__ import annotations

from pathlib import Path

import pytest

from scanner.models import Finding
from scanner.report import (
    build_report,
    filter_by_min_severity,
    select_top_findings,
    write_markdown_report,
)


def _finding(
    *,
    severity: str = "high",
    confidence: str = "medium",
    tool: str = "semgrep",
    title: str = "title",
    finding_id: str = "id",
) -> Finding:
    return Finding(
        id=finding_id,
        tool=tool,
        severity=severity,
        title=title,
        description="d",
        file="src/x.py",
        line=1,
        recommendation="r",
        confidence=confidence,
    )


class TestFilterByMinSeverity:
    def test_info_keeps_everything(self) -> None:
        findings = [
            _finding(severity="critical", finding_id="c"),
            _finding(severity="info", finding_id="i"),
        ]
        kept = filter_by_min_severity(findings, "info")
        assert len(kept) == 2

    def test_high_keeps_critical_and_high(self) -> None:
        findings = [
            _finding(severity="critical", finding_id="c"),
            _finding(severity="high", finding_id="h"),
            _finding(severity="medium", finding_id="m"),
            _finding(severity="low", finding_id="l"),
            _finding(severity="info", finding_id="i"),
        ]
        kept = filter_by_min_severity(findings, "high")
        assert {f.id for f in kept} == {"c", "h"}

    def test_critical_keeps_only_critical(self) -> None:
        findings = [
            _finding(severity="critical", finding_id="c"),
            _finding(severity="high", finding_id="h"),
        ]
        kept = filter_by_min_severity(findings, "critical")
        assert [f.id for f in kept] == ["c"]

    def test_invalid_severity_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported severity"):
            filter_by_min_severity([], "totally-unknown")

    def test_preserves_order(self) -> None:
        findings = [
            _finding(severity="medium", finding_id="m1"),
            _finding(severity="high", finding_id="h1"),
            _finding(severity="medium", finding_id="m2"),
            _finding(severity="high", finding_id="h2"),
        ]
        kept = filter_by_min_severity(findings, "medium")
        assert [f.id for f in kept] == ["m1", "h1", "m2", "h2"]


class TestSelectTopFindings:
    def test_orders_by_severity_then_confidence(self) -> None:
        findings = [
            _finding(severity="medium", confidence="high", finding_id="m-h"),
            _finding(severity="high", confidence="low", finding_id="h-l"),
            _finding(severity="critical", confidence="medium", finding_id="c-m"),
            _finding(severity="high", confidence="high", finding_id="h-h"),
        ]
        top = select_top_findings(findings, limit=4)
        # critical first, then high (sorted by confidence high→low), then medium
        assert [f.id for f in top] == ["c-m", "h-h", "h-l", "m-h"]

    def test_respects_limit(self) -> None:
        findings = [_finding(severity="high", finding_id=f"f{i}") for i in range(10)]
        top = select_top_findings(findings, limit=3)
        assert len(top) == 3

    def test_returns_empty_for_no_findings(self) -> None:
        assert select_top_findings([], limit=5) == []

    def test_default_limit_is_five(self) -> None:
        findings = [_finding(severity="high", finding_id=f"f{i}") for i in range(20)]
        top = select_top_findings(findings)
        assert len(top) == 5

    def test_excludes_info_findings(self) -> None:
        findings = [
            _finding(severity="info", finding_id="i1"),
            _finding(severity="high", finding_id="h1"),
            _finding(severity="info", finding_id="i2"),
        ]
        top = select_top_findings(findings, limit=5)
        assert [f.id for f in top] == ["h1"]


class TestBuildReportIncludesTopFindings:
    def test_top_findings_in_payload(self) -> None:
        findings = [
            _finding(severity="critical", finding_id="c1"),
            _finding(severity="high", finding_id="h1"),
            _finding(severity="info", finding_id="i1"),
        ]
        report = build_report(Path("/tmp/repo"), findings)
        assert "top_findings" in report
        assert [f["id"] for f in report["top_findings"]] == ["c1", "h1"]


class TestMarkdownReportRendersTopFindings:
    def test_top_findings_section_appears_between_summary_and_findings(
        self, tmp_path: Path
    ) -> None:
        findings = [_finding(severity="high", finding_id="hello", title="My Issue")]
        report = build_report(tmp_path, findings)
        md_path = tmp_path / "out.md"
        write_markdown_report(report, md_path)

        text = md_path.read_text(encoding="utf-8")
        summary_idx = text.index("## Summary")
        top_idx = text.index("## Top Findings")
        findings_idx = text.index("## Findings")
        assert summary_idx < top_idx < findings_idx
        assert "My Issue" in text

    def test_empty_findings_renders_no_top_findings(self, tmp_path: Path) -> None:
        report = build_report(tmp_path, [])
        md_path = tmp_path / "out.md"
        write_markdown_report(report, md_path)

        text = md_path.read_text(encoding="utf-8")
        assert "## Top Findings" in text
        assert "No findings of interest" in text or "No top findings" in text
