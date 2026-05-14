"""Tests for finding-path rebasing."""

from __future__ import annotations

from pathlib import Path

from scanner.models import Finding
from scanner.paths import rebase_finding_path, rebase_finding_paths


def _finding(file: str, finding_id: str = "x", tool: str = "semgrep") -> Finding:
    return Finding(
        id=finding_id,
        tool=tool,
        severity="high",
        title="t",
        description="d",
        file=file,
        line=1,
        recommendation="r",
        confidence="medium",
    )


class TestRebaseFindingPath:
    def test_relative_to_repo_returns_posix_path(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        nested = repo / "src" / "db"
        nested.mkdir(parents=True)
        file_path = nested / "usage.py"
        file_path.touch()

        assert rebase_finding_path(str(file_path), repo) == "src/db/usage.py"

    def test_path_outside_repo_is_returned_unchanged(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        other = tmp_path / "other_dir"
        repo.mkdir()
        other.mkdir()
        outsider = other / "leak.py"
        outsider.touch()

        assert rebase_finding_path(str(outsider), repo) == str(outsider)

    def test_empty_file_stays_empty(self, tmp_path: Path) -> None:
        assert rebase_finding_path("", tmp_path) == ""

    def test_repo_root_itself_becomes_dot(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        assert rebase_finding_path(str(repo), repo) == "."

    def test_handles_unresolvable_paths_gracefully(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        # A bogus path that doesn't exist should still be rebased if it
        # textually starts with repo_root (or returned as-is otherwise).
        assert rebase_finding_path("<unknown>", repo) == "<unknown>"


class TestRebaseFindingPaths:
    def test_rebases_each_finding_independently(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "a.py").touch()
        (repo / "src" / "b.py").touch()

        findings = [
            _finding(str(repo / "src" / "a.py"), "f1"),
            _finding(str(repo / "src" / "b.py"), "f2"),
        ]

        rebased = rebase_finding_paths(findings, repo)
        assert [f.file for f in rebased] == ["src/a.py", "src/b.py"]

    def test_preserves_finding_identity_when_no_change(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        other = tmp_path / "other_file.py"
        other.touch()
        finding = _finding(str(other), "f1")

        rebased = rebase_finding_paths([finding], repo)
        # Outside-the-repo paths return the same Finding object (no copy).
        assert rebased[0] is finding

    def test_returns_new_findings_only_when_path_changed(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "a.py").touch()
        inside = _finding(str(repo / "src" / "a.py"), "f-inside")
        outside = _finding("/totally/outside.py", "f-outside")

        rebased = rebase_finding_paths([inside, outside], repo)

        assert rebased[0] is not inside
        assert rebased[0].file == "src/a.py"
        assert rebased[1] is outside

    def test_id_containing_original_path_is_also_rebased(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / "src" / "db").mkdir(parents=True)
        target = repo / "src" / "db" / "usage.py"
        target.touch()

        finding = _finding(
            file=str(target),
            finding_id=f"semgrep-rule-{target}-167",
        )

        rebased = rebase_finding_paths([finding], repo)
        assert rebased[0].file == "src/db/usage.py"
        # The original absolute path must not survive in the id.
        assert str(target) not in rebased[0].id
        assert "src/db/usage.py" in rebased[0].id
