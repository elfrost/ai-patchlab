"""Tests for path-based finding suppression via .gitignore-style patterns."""

from __future__ import annotations

from pathlib import Path

import pytest

from scanner.ignore import (
    DEFAULT_SAMPLE_IGNORE_PATTERNS,
    apply_ignore,
    load_ignore_patterns,
    parse_ignore_patterns,
)
from scanner.models import Finding


def _finding(file: str, finding_id: str = "x") -> Finding:
    return Finding(
        id=finding_id,
        tool="semgrep",
        severity="high",
        title="t",
        description="d",
        file=file,
        line=1,
        recommendation="r",
        confidence="medium",
    )


class TestDefaultSampleIgnore:
    @pytest.mark.parametrize(
        "path",
        [
            "examples/foo.py",
            "docs/sample-apps/x/main.py",
            "pkg/examples/deep/a.py",
            "src/demo/app.py",
            "frontend/samples/index.js",
        ],
    )
    def test_suppresses_sample_subtrees(self, path: str) -> None:
        kept = apply_ignore([_finding(path)], list(DEFAULT_SAMPLE_IGNORE_PATTERNS))
        assert kept == []

    @pytest.mark.parametrize(
        "path",
        [
            "src/core/example.py",
            "src/myexamples/a.py",
            "examples.py",
            "pixeltable/share/packager.py",
        ],
    )
    def test_keeps_non_sample_paths(self, path: str) -> None:
        kept = apply_ignore([_finding(path)], list(DEFAULT_SAMPLE_IGNORE_PATTERNS))
        assert len(kept) == 1


class TestParseIgnorePatterns:
    def test_strips_comments_and_blank_lines(self) -> None:
        raw = "\n# top comment\ntests/**\n\n  # indented comment\n**/cassettes/**\n"
        patterns = parse_ignore_patterns(raw)
        assert patterns == ["tests/**", "**/cassettes/**"]

    def test_keeps_negation_lines(self) -> None:
        raw = "tests/**\n!tests/test_critical.py\n"
        patterns = parse_ignore_patterns(raw)
        assert patterns == ["tests/**", "!tests/test_critical.py"]


class TestLoadIgnorePatterns:
    def test_returns_empty_for_none_path(self) -> None:
        assert load_ignore_patterns(None) == []

    def test_reads_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "ignore.txt"
        path.write_text("tests/**\n# comment\n**/cassettes/**\n", encoding="utf-8")
        assert load_ignore_patterns(path) == ["tests/**", "**/cassettes/**"]

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_ignore_patterns(tmp_path / "nope.txt")


class TestApplyIgnore:
    def test_empty_patterns_returns_input_unchanged(self) -> None:
        findings = [_finding("src/a.py", "1"), _finding("tests/b.py", "2")]
        assert apply_ignore(findings, []) == findings

    def test_drops_findings_matching_pattern(self) -> None:
        findings = [
            _finding("src/a.py", "src"),
            _finding("tests/b.py", "tst"),
        ]
        result = apply_ignore(findings, ["tests/**"])
        assert [f.id for f in result] == ["src"]

    def test_double_star_matches_any_depth(self) -> None:
        findings = [
            _finding("packages/x/tests/cassettes/foo.yaml", "deep"),
            _finding("tests/cassettes/bar.yaml", "shallow"),
            _finding("src/foo.py", "keep"),
        ]
        result = apply_ignore(findings, ["**/cassettes/**"])
        assert [f.id for f in result] == ["keep"]

    def test_negation_re_includes_specific_file(self) -> None:
        findings = [
            _finding("tests/test_a.py", "a"),
            _finding("tests/test_critical.py", "critical"),
        ]
        result = apply_ignore(findings, ["tests/**", "!tests/test_critical.py"])
        assert [f.id for f in result] == ["critical"]

    def test_preserves_order(self) -> None:
        findings = [
            _finding("src/a.py", "a"),
            _finding("tests/b.py", "b"),
            _finding("src/c.py", "c"),
        ]
        result = apply_ignore(findings, ["tests/**"])
        assert [f.id for f in result] == ["a", "c"]

    def test_empty_file_field_is_never_suppressed(self) -> None:
        # A finding with empty file (e.g. dependency-scan info) should
        # not be silently dropped by a `**` pattern.
        findings = [_finding("", "empty"), _finding("tests/b.py", "tst")]
        result = apply_ignore(findings, ["tests/**", "**"])
        assert "empty" in [f.id for f in result]
