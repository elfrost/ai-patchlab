"""Tests for keeping local and editable requirements away from pip."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from scanner.coverage import build_coverage, status_for_meta_finding
from scanner.scanners.dependency_scan import scan_dependencies
from scanner.tools import pip_audit_runner
from scanner.tools.pip_audit_runner import PipAuditResult, find_pip_audit_input, run_pip_audit
from scanner.tools.requirements_sanitizer import sanitize_requirements

PYPROJECT_WITH_EXTRA = """
[project]
name = "demo"
dependencies = ["flask>=2.0", "requests"]

[project.optional-dependencies]
app = ["gunicorn==21.2.0"]
"""

DYNAMIC_PYPROJECT = """
[project]
name = "demo"
dynamic = ["dependencies"]

[tool.setuptools.dynamic]
dependencies = { file = ["deps.in"] }
"""


def _repo(tmp_path: Path, requirements: str, pyproject: str | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text(requirements, encoding="utf-8")
    if pyproject is not None:
        (repo / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return repo


def _clean_pip_audit(repo_path: Path, raw_report_path: Path, audit_input) -> PipAuditResult:
    return PipAuditResult(
        installed=True, raw_report_path=raw_report_path, audit_input=audit_input, returncode=0
    )


def _run_with_fake_pip_audit(monkeypatch, repo: Path, raw_report: Path) -> dict:
    """Run the runner with a fake subprocess and return what it was given."""
    captured: dict = {}

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        captured["command"] = command
        captured["cwd"] = kwargs.get("cwd")
        requirement = command[command.index("--requirement") + 1]
        captured["requirement_path"] = requirement
        captured["requirements"] = Path(requirement).read_text(encoding="utf-8")
        raw_report.write_text("[]", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(pip_audit_runner, "find_pip_audit_command", lambda: ["pip-audit"])
    monkeypatch.setattr(pip_audit_runner.subprocess, "run", fake_run)
    audit_input = find_pip_audit_input(repo)
    assert audit_input is not None
    run_pip_audit(repo_path=repo, raw_report_path=raw_report, audit_input=audit_input)
    return captured


class TestEditableOnlyRequirements:
    """The shape seen in the field: `requirements.txt` is only `-e .[app]`."""

    def test_pyproject_dependencies_replace_the_editable_line(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        repo = _repo(tmp_path, "-e .[app]\n", PYPROJECT_WITH_EXTRA)
        raw_report = tmp_path / "reports" / "raw" / "pip-audit.json"

        captured = _run_with_fake_pip_audit(monkeypatch, repo, raw_report)

        assert captured["requirements"].split() == ["flask>=2.0", "requests", "gunicorn==21.2.0"]
        assert captured["requirement_path"] != str(repo / "requirements.txt")

    def test_pip_never_runs_from_the_repo_or_the_scanner_cwd(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        repo = _repo(tmp_path, "-e .\n", PYPROJECT_WITH_EXTRA)
        raw_report = tmp_path / "reports" / "raw" / "pip-audit.json"

        captured = _run_with_fake_pip_audit(monkeypatch, repo, raw_report)

        cwd = Path(captured["cwd"])
        assert cwd not in {repo, Path.cwd()}
        assert repo not in cwd.parents
        assert Path.cwd() not in cwd.parents

    def test_recovered_dependencies_leave_coverage_complete(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        repo = _repo(tmp_path, "--editable .[app]\n", PYPROJECT_WITH_EXTRA)
        monkeypatch.setattr("scanner.scanners.dependency_scan.run_pip_audit", _clean_pip_audit)

        findings = scan_dependencies(repo, tmp_path / "reports")

        assert findings == []

    def test_dynamic_pyproject_is_partial_and_pip_audit_is_not_run(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        repo = _repo(tmp_path, "-e .[app]\n", DYNAMIC_PYPROJECT)

        def explode(*args, **kwargs):
            raise AssertionError("pip-audit must not run with nothing auditable")

        monkeypatch.setattr("scanner.scanners.dependency_scan.run_pip_audit", explode)

        findings = scan_dependencies(repo, tmp_path / "reports")

        assert [f.id for f in findings] == ["dependency-scan-partial"]
        assert findings[0].is_meta is True
        assert "-e .[app]" in findings[0].description
        coverage = {row.tool: row for row in build_coverage(findings)}
        assert coverage["dependency-scan"].status == "partial"

    def test_editable_only_without_any_pyproject_is_partial(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, "-e .\n")

        findings = scan_dependencies(repo, tmp_path / "reports")

        assert [f.id for f in findings] == ["dependency-scan-partial"]

    def test_extra_the_project_does_not_define_is_not_guessed(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, "-e .[missing]\n", PYPROJECT_WITH_EXTRA)

        sanitized = sanitize_requirements(repo, (repo / "requirements.txt",))

        assert sanitized.lines == ()
        assert [item.resolved for item in sanitized.skipped] == [False]


class TestMixedRequirements:
    def test_pinned_lines_are_kept_and_editable_line_is_dropped(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, "flask==0.5\n-e .\nrequests==2.0.0\n", DYNAMIC_PYPROJECT)

        sanitized = sanitize_requirements(repo, (repo / "requirements.txt",))

        assert sanitized.lines == ("flask==0.5", "requests==2.0.0")
        assert sanitized.rewritten is True
        assert [(item.line, item.reason, item.resolved) for item in sanitized.skipped] == [
            (2, "editable", False)
        ]

    def test_mixed_file_with_declared_dependencies_merges_without_duplicates(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, "flask>=2.0\n-e .\n", PYPROJECT_WITH_EXTRA)

        sanitized = sanitize_requirements(repo, (repo / "requirements.txt",))

        assert sanitized.lines == ("flask>=2.0", "requests")
        assert sanitized.unresolved == ()

    def test_unresolved_editable_line_adds_a_partial_finding_after_the_audit(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        repo = _repo(tmp_path, "flask==0.5\n-e .\n", DYNAMIC_PYPROJECT)
        monkeypatch.setattr("scanner.scanners.dependency_scan.run_pip_audit", _clean_pip_audit)

        findings = scan_dependencies(repo, tmp_path / "reports")

        assert [f.id for f in findings] == ["dependency-scan-partial"]

    def test_clean_requirements_are_audited_in_place(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, "flask==0.5\n# comment\nrequests>=2 ; python_version>'3'\n")

        audit_input = find_pip_audit_input(repo)

        assert audit_input is not None
        assert audit_input.requirement_lines is None
        assert audit_input.skipped == ()


class TestLocalPathLines:
    @pytest.mark.parametrize(
        "line",
        [
            "./libs/foo",
            "../sibling",
            "libs/foo",
            "libs\\foo",
            "/abs/path/pkg",
            "~/pkg",
            "C:\\pkgs\\foo",
            "file:///tmp/foo.whl",
            "file:./foo",
            "foo @ file:///tmp/foo.whl",
            "foo @ ./foo",
            "-e ./libs/foo[extra]",
            "--editable=./libs/foo",
            "-e.",
            ".[dev]",
            ".",
        ],
    )
    def test_local_lines_never_reach_pip(self, tmp_path: Path, line: str) -> None:
        repo = _repo(tmp_path, f"flask==0.5\n{line}\n", DYNAMIC_PYPROJECT)

        sanitized = sanitize_requirements(repo, (repo / "requirements.txt",))

        assert sanitized.lines == ("flask==0.5",)
        assert len(sanitized.skipped) == 1
        assert sanitized.skipped[0].resolved is False

    @pytest.mark.parametrize(
        "line",
        [
            "flask==0.5",
            "Flask[async]>=2 ; python_version >= '3.9'",
            "foo @ https://example.com/foo-1.0.tar.gz",
            "foo==1.0 --hash=sha256:abc",
            "--index-url https://pypi.example/simple",
            "--no-binary :all:",
        ],
    )
    def test_ordinary_lines_are_kept(self, tmp_path: Path, line: str) -> None:
        repo = _repo(tmp_path, f"{line}\n")

        sanitized = sanitize_requirements(repo, (repo / "requirements.txt",))

        assert sanitized.lines == (line,)
        assert sanitized.skipped == ()
        assert sanitized.rewritten is False

    def test_continuation_and_comment_handling(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, "foo==1.0 \\\n    --hash=sha256:abc  # pinned\n-e \\\n  ./pkg\n")

        sanitized = sanitize_requirements(repo, (repo / "requirements.txt",))

        assert len(sanitized.lines) == 1
        assert sanitized.lines[0].split() == ["foo==1.0", "--hash=sha256:abc"]
        assert [(item.line, item.reason) for item in sanitized.skipped] == [(3, "editable")]


class TestIncludes:
    def test_editable_line_inside_an_included_file_is_dropped(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, "-r requirements/base.txt\n")
        (repo / "requirements").mkdir()
        (repo / "requirements" / "base.txt").write_text("flask==0.5\n-e .\n", encoding="utf-8")

        sanitized = sanitize_requirements(repo, (repo / "requirements.txt",))

        assert sanitized.lines == ("flask==0.5",)
        assert [item.file for item in sanitized.skipped] == ["requirements/base.txt"]

    def test_include_outside_the_repository_is_not_followed(self, tmp_path: Path) -> None:
        (tmp_path / "outside.txt").write_text("evil==1.0\n", encoding="utf-8")
        repo = _repo(tmp_path, "-r ../outside.txt\nflask==0.5\n")

        sanitized = sanitize_requirements(repo, (repo / "requirements.txt",))

        assert sanitized.lines == ("flask==0.5",)
        assert [item.reason for item in sanitized.skipped] == ["unusable-include"]

    def test_include_cycle_terminates(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, "-r requirements.txt\nflask==0.5\n")

        sanitized = sanitize_requirements(repo, (repo / "requirements.txt",))

        assert sanitized.lines == ("flask==0.5",)

    def test_constraint_file_is_made_absolute_so_the_cwd_does_not_matter(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, "-c constraints.txt\nflask\n")
        (repo / "constraints.txt").write_text("flask<3\n", encoding="utf-8")

        sanitized = sanitize_requirements(repo, (repo / "requirements.txt",))

        assert sanitized.lines == (f"-c {(repo / 'constraints.txt').resolve()}", "flask")


class TestFallsBackToPylock:
    def test_editable_only_requirements_use_the_pylock_file(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, "-e .\n", DYNAMIC_PYPROJECT)
        (repo / "pylock.demo.toml").write_text("lock-version = '1.0'\n", encoding="utf-8")

        audit_input = find_pip_audit_input(repo)

        assert audit_input is not None
        assert audit_input.kind == "locked-project"
        assert [item.text for item in audit_input.skipped] == ["-e ."]


def test_partial_meta_finding_id_maps_to_partial_coverage() -> None:
    assert status_for_meta_finding("dependency-scan-partial") == "partial"
