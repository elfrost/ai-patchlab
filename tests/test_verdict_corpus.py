"""Tests for dismissal-corpus validation and aggregation.

The curation half of `verdicts.json` is hand-written JSON, so the dataclass
never runs and the closed vocabularies enforce nothing on their own. Scan #109
proved it on the first production run: six rows with an empty `rule` and free
prose in `verdict`. These tests pin the enforcement that closes that gap, and
the property that made it expensive - a checker that reveals one problem per
run costs as many runs as there are problems (ADR-017).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scanner.verdict_corpus import load_corpus, validate_payload
from scanner.verdicts import (
    CURATION_REASON_CODES,
    VerdictRecord,
    verdicts_payload,
)


def _row(**overrides: object) -> dict[str, object]:
    """Build a valid raw verdict row, then break exactly one field."""
    row: dict[str, object] = {
        "source": "curation",
        "reason_code": "by-design",
        "tool": "semgrep",
        "rule": "github-actions-mutable-action-tag",
        "count": 16,
        "verdict": "by-design",
        "detail": "SHA-pin hardening nudge on CI action refs.",
    }
    row.update(overrides)
    return row


def _payload(*rows: dict[str, object]) -> dict[str, object]:
    """Wrap raw rows without recomputing the derived totals."""
    return {"records": list(rows)}


class TestVocabularyAddition:
    """`confirmed-real` is first-party only; version drift has its own code."""

    def test_dependency_currency_is_a_reason_code(self) -> None:
        assert "dependency-currency" in CURATION_REASON_CODES

    def test_confirmed_real_still_exists(self) -> None:
        assert "confirmed-real" in CURATION_REASON_CODES

    def test_the_two_are_distinct_codes(self) -> None:
        rows = (
            VerdictRecord("curation", "confirmed-real", "semgrep", "a", 1),
            VerdictRecord("curation", "dependency-currency", "trivy", "b", 13),
        )
        assert verdicts_payload(rows)["by_reason"] == {
            "dependency-currency": 13,
            "confirmed-real": 1,
        }


class TestRuleIsRequired:
    """A row without a rule family can be counted but never acted on."""

    def test_record_rejects_an_empty_rule(self) -> None:
        with pytest.raises(ValueError, match="names a rule family"):
            VerdictRecord("curation", "by-design", "semgrep", "", 1)

    def test_record_rejects_a_whitespace_rule(self) -> None:
        with pytest.raises(ValueError, match="names a rule family"):
            VerdictRecord("curation", "by-design", "semgrep", "   ", 1)

    def test_validator_flags_an_empty_rule(self) -> None:
        problems = validate_payload(_payload(_row(rule="")))
        assert any("rule is empty" in problem for problem in problems)


class TestValidatePayload:
    """One run must show the whole repair list, not the first item of it."""

    def test_a_good_payload_has_no_problems(self) -> None:
        assert validate_payload(_payload(_row())) == []

    def test_a_generated_payload_round_trips_clean(self) -> None:
        rows = (VerdictRecord("scanner", "ignore-pattern", "semgrep", "rule-a", 3),)
        assert validate_payload(verdicts_payload(rows)) == []

    def test_missing_records_key(self) -> None:
        assert validate_payload({}) == ["`records` is missing or is not a list."]

    def test_flags_an_unknown_reason_code(self) -> None:
        problems = validate_payload(_payload(_row(reason_code="vibes")))
        assert any("not in the vocabulary" in problem for problem in problems)

    def test_flags_an_unknown_source(self) -> None:
        problems = validate_payload(_payload(_row(source="intern")))
        assert any("source" in problem for problem in problems)

    def test_flags_free_prose_in_verdict(self) -> None:
        problems = validate_payload(_payload(_row(verdict="FP - parameterized")))
        assert any("belongs in `detail`" in problem for problem in problems)

    def test_an_empty_verdict_is_allowed(self) -> None:
        assert validate_payload(_payload(_row(verdict=""))) == []

    def test_flags_a_zero_count(self) -> None:
        problems = validate_payload(_payload(_row(count=0)))
        assert any("at least 1" in problem for problem in problems)

    def test_flags_a_non_numeric_count(self) -> None:
        problems = validate_payload(_payload(_row(count="many")))
        assert any("not a number" in problem for problem in problems)

    def test_flags_an_empty_tool(self) -> None:
        problems = validate_payload(_payload(_row(tool="")))
        assert any("tool is empty" in problem for problem in problems)

    def test_reports_every_problem_in_one_row_at_once(self) -> None:
        """The regression: scan #109 needed two runs to reveal two defects."""
        problems = validate_payload(_payload(_row(rule="", verdict="FP - parameterized")))
        assert len(problems) == 2
        assert any("rule is empty" in problem for problem in problems)
        assert any("belongs in `detail`" in problem for problem in problems)

    def test_reports_problems_across_several_rows(self) -> None:
        problems = validate_payload(_payload(_row(rule=""), _row(count=0)))
        assert len(problems) == 2

    def test_flags_a_total_that_disagrees_with_the_rows(self) -> None:
        payload = verdicts_payload((VerdictRecord("curation", "by-design", "t", "r", 5),))
        payload["total_dismissed"] = 99
        problems = validate_payload(payload)
        assert any("total_dismissed" in problem for problem in problems)

    def test_flags_by_reason_that_disagrees_with_the_rows(self) -> None:
        payload = verdicts_payload((VerdictRecord("curation", "by-design", "t", "r", 5),))
        payload["by_reason"] = {"by-design": 4}
        problems = validate_payload(payload)
        assert any("by_reason" in problem for problem in problems)

    def test_a_row_that_is_not_an_object(self) -> None:
        assert validate_payload({"records": ["nope"]}) == ["record 0: not an object."]


class TestLoadCorpus:
    """The corpus is the point: many scans, one countable total."""

    def test_an_empty_directory_yields_no_records(self, tmp_path: Path) -> None:
        assert load_corpus(tmp_path) == ()

    def test_records_accumulate_across_files(self, tmp_path: Path) -> None:
        for index, count in enumerate((3, 7)):
            rows = (VerdictRecord("curation", "sql-identifier-fp", "semgrep", "rule", count),)
            (tmp_path / f"scan-{index}.json").write_text(
                json.dumps(verdicts_payload(rows)), encoding="utf-8"
            )

        records = load_corpus(tmp_path)

        assert len(records) == 2
        assert sum(record.count for record in records) == 10

    def test_files_are_read_in_name_order(self, tmp_path: Path) -> None:
        for name, rule in (("b.json", "second"), ("a.json", "first")):
            rows = (VerdictRecord("curation", "by-design", "t", rule, 1),)
            (tmp_path / name).write_text(json.dumps(verdicts_payload(rows)), encoding="utf-8")

        assert [record.rule for record in load_corpus(tmp_path)] == ["first", "second"]

    def test_a_corrupt_file_fails_loudly(self, tmp_path: Path) -> None:
        """A corpus that skips what it cannot parse under-reports its own total."""
        (tmp_path / "bad.json").write_text(
            json.dumps({"records": [_row(reason_code="vibes")]}), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="reason code"):
            load_corpus(tmp_path)

    def test_non_json_files_are_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("not a corpus file", encoding="utf-8")
        assert load_corpus(tmp_path) == ()
