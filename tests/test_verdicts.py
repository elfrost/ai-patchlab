"""Tests for dismissal records.

A report that suppresses 400 findings and says nothing is editing its own
numbers. These tests pin the two properties that stop that: every suppression
step accounts for what it removed, and the reason vocabulary stays closed so
the corpus can still be counted years later (ADR-016).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scanner.models import Finding
from scanner.report import write_reports
from scanner.run_scan import run_scan
from scanner.verdicts import (
    CURATION_REASON_CODES,
    REASON_CODES,
    SCANNER_REASON_CODES,
    VerdictRecord,
    count_by_reason,
    load_records,
    summarize_removed,
    total_dismissed,
    verdicts_payload,
)


def _finding(tool: str = "semgrep", title: str = "rule-a", **overrides: object) -> Finding:
    """Build a finding with defaults for the field under test."""
    base: dict[str, object] = {
        "id": f"{title}:app.py:1",
        "tool": tool,
        "severity": "low",
        "title": title,
        "description": "Example description.",
        "file": "app.py",
        "line": 1,
        "recommendation": "Fix it.",
        "confidence": "medium",
    }
    base.update(overrides)
    return Finding(**base)  # type: ignore[arg-type]


class TestVocabulary:
    """The reason codes are closed on purpose - an open set counts to one."""

    def test_scanner_and_curation_codes_are_disjoint(self) -> None:
        assert not set(SCANNER_REASON_CODES) & set(CURATION_REASON_CODES)

    def test_reason_codes_is_the_union(self) -> None:
        assert set(REASON_CODES) == set(SCANNER_REASON_CODES) | set(CURATION_REASON_CODES)

    def test_rejects_an_unknown_reason_code(self) -> None:
        with pytest.raises(ValueError, match="reason code"):
            VerdictRecord(source="curation", reason_code="vibes", tool="t", rule="r", count=1)

    def test_rejects_an_unknown_source(self) -> None:
        with pytest.raises(ValueError, match="source"):
            VerdictRecord(source="intern", reason_code="by-design", tool="t", rule="r", count=1)

    def test_rejects_an_unknown_verdict(self) -> None:
        with pytest.raises(ValueError, match="verdict"):
            VerdictRecord(
                source="curation",
                reason_code="by-design",
                tool="t",
                rule="r",
                count=1,
                verdict="probably-fine",
            )

    def test_rejects_a_zero_count(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            VerdictRecord(source="curation", reason_code="by-design", tool="t", rule="r", count=0)

    def test_a_curation_code_is_not_a_scanner_code(self) -> None:
        with pytest.raises(ValueError, match="scanner reason code"):
            summarize_removed([_finding()], [], "by-design")


class TestSummarizeRemoved:
    """Rows are rule families with counts, never one row per finding."""

    def test_nothing_removed_yields_no_rows(self) -> None:
        findings = [_finding(), _finding()]
        assert summarize_removed(findings, findings, "ignore-pattern") == ()

    def test_counts_are_grouped_by_rule_family(self) -> None:
        before = [_finding(title="rule-a") for _ in range(3)] + [_finding(title="rule-b")]
        rows = summarize_removed(before, [], "ignore-pattern")
        assert len(rows) == 2
        assert (rows[0].rule, rows[0].count) == ("rule-a", 3)
        assert (rows[1].rule, rows[1].count) == ("rule-b", 1)

    def test_partial_removal_counts_only_the_difference(self) -> None:
        before = [_finding(title="rule-a") for _ in range(5)]
        after = before[:2]
        rows = summarize_removed(before, after, "ignore-pattern")
        assert rows[0].count == 3

    def test_same_rule_from_two_tools_stays_separate(self) -> None:
        before = [_finding(tool="semgrep", title="x"), _finding(tool="gitleaks", title="x")]
        rows = summarize_removed(before, [], "below-min-severity")
        assert {row.tool for row in rows} == {"gitleaks", "semgrep"}

    def test_rows_are_sorted_by_descending_count(self) -> None:
        before = [_finding(title="small")] + [_finding(title="big") for _ in range(4)]
        rows = summarize_removed(before, [], "ignore-pattern")
        assert [row.rule for row in rows] == ["big", "small"]

    def test_an_untitled_finding_still_gets_a_family(self) -> None:
        rows = summarize_removed([_finding(title="")], [], "ignore-pattern")
        assert rows[0].rule == "(unlabelled)"

    def test_records_carry_the_reason_and_detail(self) -> None:
        rows = summarize_removed([_finding()], [], "ignore-pattern", detail="Because.")
        assert rows[0].source == "scanner"
        assert rows[0].reason_code == "ignore-pattern"
        assert rows[0].detail == "Because."


class TestCounting:
    """The counter is the measurement ADR-014 had to do by hand."""

    def test_total_sums_the_counts_not_the_rows(self) -> None:
        rows = summarize_removed([_finding() for _ in range(7)], [], "ignore-pattern")
        assert len(rows) == 1
        assert total_dismissed(rows) == 7

    def test_count_by_reason_aggregates_across_sources(self) -> None:
        rows = (
            VerdictRecord("scanner", "ignore-pattern", "semgrep", "a", 3),
            VerdictRecord("curation", "sql-identifier-fp", "semgrep", "b", 10),
            VerdictRecord("curation", "sql-identifier-fp", "semgrep", "c", 5),
        )
        assert count_by_reason(rows) == {"sql-identifier-fp": 15, "ignore-pattern": 3}

    def test_count_by_reason_is_ordered_highest_first(self) -> None:
        rows = (
            VerdictRecord("curation", "by-design", "t", "a", 1),
            VerdictRecord("curation", "not-reachable", "t", "b", 9),
        )
        assert list(count_by_reason(rows)) == ["not-reachable", "by-design"]

    def test_payload_round_trips_through_load_records(self) -> None:
        rows = (
            VerdictRecord("curation", "confirmed-real", "semgrep", "a", 1, verdict="real"),
            VerdictRecord("scanner", "ignore-pattern", "trivy", "b", 4),
        )
        assert load_records(verdicts_payload(rows)) == rows

    def test_load_rejects_a_corrupt_row_instead_of_skipping_it(self) -> None:
        """A corpus that silently drops what it cannot parse under-reports."""
        with pytest.raises(ValueError, match="reason code"):
            load_records(
                {
                    "records": [
                        {
                            "source": "curation",
                            "reason_code": "nope",
                            "tool": "t",
                            "rule": "r",
                            "count": 1,
                        }
                    ]
                }
            )


class TestReportRendering:
    """Suppressed findings appear in the report or the report is lying."""

    def test_no_dismissed_section_without_records(self, tmp_path: Path) -> None:
        paths = write_reports(repo_path=tmp_path, findings=[], reports_dir=tmp_path / "r")
        assert "verdicts" not in paths
        assert "## Dismissed" not in paths["markdown"].read_text(encoding="utf-8")

    def test_dismissed_section_lists_families_and_totals(self, tmp_path: Path) -> None:
        rows = summarize_removed(
            [_finding(title="noisy-rule") for _ in range(6)], [], "ignore-pattern"
        )
        paths = write_reports(
            repo_path=tmp_path, findings=[], reports_dir=tmp_path / "r", verdicts=rows
        )
        markdown = paths["markdown"].read_text(encoding="utf-8")
        assert "## Dismissed" in markdown
        assert "6 findings were removed" in markdown
        assert "ignore-pattern (6)" in markdown
        assert "noisy-rule" in markdown

    def test_verdicts_json_is_written(self, tmp_path: Path) -> None:
        rows = summarize_removed([_finding()], [], "below-min-severity")
        paths = write_reports(
            repo_path=tmp_path, findings=[], reports_dir=tmp_path / "r", verdicts=rows
        )
        payload = json.loads(paths["verdicts"].read_text(encoding="utf-8"))
        assert payload["total_dismissed"] == 1
        assert payload["by_reason"] == {"below-min-severity": 1}
        assert load_records(payload) == rows


class TestScanPipeline:
    """End to end: a suppressed finding is accounted for, not vanished.

    `collect_findings` is stubbed rather than the individual runners: the
    behaviour under test is the before/after diffing wired around each
    suppression step in `run_scan`, not how any one adapter produces findings.
    """

    @staticmethod
    def _run(tmp_path: Path, monkeypatch, findings: list[Finding], **kwargs) -> dict[str, Path]:
        monkeypatch.setattr(
            "scanner.run_scan.collect_findings",
            lambda repo_path, reports_dir: list(findings),
        )
        repo_path = tmp_path / "repo"
        repo_path.mkdir(exist_ok=True)
        return run_scan(repo_path=repo_path, reports_dir=tmp_path / "reports", **kwargs)

    def test_min_severity_suppression_is_recorded(self, tmp_path: Path, monkeypatch) -> None:
        paths = self._run(
            tmp_path,
            monkeypatch,
            [_finding(title="noisy", severity="low") for _ in range(4)],
            min_severity="critical",
        )
        payload = json.loads(paths["verdicts"].read_text(encoding="utf-8"))
        assert payload["by_reason"] == {"below-min-severity": 4}
        assert payload["records"][0]["rule"] == "noisy"

    def test_ignore_pattern_suppression_is_recorded(self, tmp_path: Path, monkeypatch) -> None:
        ignore_file = tmp_path / ".patchlabignore"
        ignore_file.write_text("*.py\n", encoding="utf-8")
        paths = self._run(
            tmp_path,
            monkeypatch,
            [_finding(title="hidden", severity="high")],
            ignore_file=ignore_file,
        )
        payload = json.loads(paths["verdicts"].read_text(encoding="utf-8"))
        assert payload["by_reason"] == {"ignore-pattern": 1}

    def test_the_two_steps_are_recorded_separately(self, tmp_path: Path, monkeypatch) -> None:
        ignore_file = tmp_path / ".patchlabignore"
        ignore_file.write_text("ignored.py\n", encoding="utf-8")
        findings = [
            _finding(title="by-path", severity="high", file="ignored.py"),
            _finding(title="by-floor", severity="low", file="kept.py"),
        ]
        paths = self._run(
            tmp_path, monkeypatch, findings, ignore_file=ignore_file, min_severity="critical"
        )
        payload = json.loads(paths["verdicts"].read_text(encoding="utf-8"))
        assert payload["by_reason"] == {"below-min-severity": 1, "ignore-pattern": 1}

    def test_nothing_suppressed_writes_no_verdicts_file(self, tmp_path: Path, monkeypatch) -> None:
        paths = self._run(tmp_path, monkeypatch, [_finding(severity="critical")])
        assert "verdicts" not in paths
        assert not (tmp_path / "reports" / "verdicts.json").exists()

    def test_meta_findings_are_never_counted_as_dismissed(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Meta findings survive `--min-severity`, so they cannot appear here."""
        findings = [
            _finding(title="Semgrep is not installed", severity="info", is_meta=True),
            _finding(title="real-rule", severity="low"),
        ]
        paths = self._run(tmp_path, monkeypatch, findings, min_severity="critical")
        payload = json.loads(paths["verdicts"].read_text(encoding="utf-8"))
        assert {row["rule"] for row in payload["records"]} == {"real-rule"}
