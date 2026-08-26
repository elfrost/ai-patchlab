"""Tests for scanner-infrastructure (meta) findings and coverage reporting.

A meta finding describes the *state of the scan* (a tool was missing, crashed,
timed out, or only covered part of the tree) rather than a defect in the code.
These must never be filtered out by `--min-severity`: a report that silently
drops "semgrep crashed" reads exactly like a report that found nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from scanner.models import FINDING_FIELDS, Finding
from scanner.report import filter_by_min_severity, select_top_findings
from scanner.scanners.dependency_scan import scan_dependencies
from scanner.scanners.semgrep import scan_semgrep
from scanner.tools.pip_audit_runner import PipAuditInput, PipAuditResult
from scanner.tools.semgrep_runner import SemgrepResult


def _finding(**overrides: object) -> Finding:
    """Build a Finding with sensible defaults for the field under test."""
    base: dict[str, object] = {
        "id": "example",
        "tool": "semgrep",
        "severity": "info",
        "title": "Example",
        "description": "Example description.",
        "file": "app.py",
        "line": 1,
        "recommendation": "Do the thing.",
        "confidence": "medium",
    }
    base.update(overrides)
    return Finding(**base)  # type: ignore[arg-type]


class TestMetaFindingSchema:
    """`is_meta` is part of the normalized schema and defaults to False."""

    def test_is_meta_defaults_to_false(self) -> None:
        assert _finding().is_meta is False

    def test_is_meta_is_a_declared_field(self) -> None:
        assert "is_meta" in FINDING_FIELDS

    def test_is_meta_is_serialized(self) -> None:
        assert _finding(is_meta=True).to_dict()["is_meta"] is True


class TestMinSeverityExemption:
    """Meta findings survive `--min-severity`; ordinary findings do not."""

    def test_meta_finding_survives_the_strictest_floor(self) -> None:
        findings = [_finding(id="semgrep-scan-error", is_meta=True)]
        assert filter_by_min_severity(findings, "critical") == findings

    def test_ordinary_info_finding_is_still_dropped(self) -> None:
        findings = [_finding(id="ordinary-info", is_meta=False)]
        assert filter_by_min_severity(findings, "medium") == []

    def test_mixed_list_keeps_only_meta_and_severe_enough(self) -> None:
        meta = _finding(id="semgrep-scan-error", is_meta=True)
        noise = _finding(id="noise", severity="low")
        real = _finding(id="real", severity="high")
        kept = filter_by_min_severity([meta, noise, real], "high")
        assert kept == [meta, real]

    def test_meta_findings_are_never_promoted_into_top_findings(self) -> None:
        """Exempt from the severity floor, but still not a headline result."""
        meta = _finding(id="semgrep-scan-error", is_meta=True)
        real = _finding(id="real", severity="high")
        assert select_top_findings([meta, real]) == [real]


class TestSemgrepCoverageGap:
    """Semgrep's `errors` array is the only place partial coverage shows up.

    `paths.skipped` stays empty even when rules time out on a file, so a scan
    that never ran the rule that mattered reports as a clean scan.
    """

    def _run(self, tmp_path: Path, monkeypatch, payload: dict) -> list[Finding]:
        raw_dir = tmp_path / "reports" / "raw"
        raw_dir.mkdir(parents=True)
        (raw_dir / "semgrep.json").write_text(json.dumps(payload), encoding="utf-8")

        def fake_run_semgrep(repo_path: Path, raw_report_path: Path) -> SemgrepResult:
            return SemgrepResult(installed=True, raw_report_path=raw_report_path, returncode=0)

        monkeypatch.setattr("scanner.scanners.semgrep.run_semgrep", fake_run_semgrep)
        return scan_semgrep(repo_path=tmp_path, reports_dir=tmp_path / "reports")

    def test_timeout_errors_emit_a_coverage_finding(self, tmp_path: Path, monkeypatch) -> None:
        payload = {
            "results": [],
            "paths": {"skipped": []},
            "errors": [
                {
                    "type": "Timeout",
                    "rule_id": "python.lang.security.audit.subprocess-injection",
                    "path": "api/app.py",
                },
                {
                    "type": "Timeout",
                    "rule_id": "python.flask.security.subprocess-injection",
                    "path": "api/app.py",
                },
            ],
        }
        findings = self._run(tmp_path, monkeypatch, payload)
        coverage = [f for f in findings if f.id == "semgrep-partial-coverage"]
        assert len(coverage) == 1
        assert coverage[0].is_meta is True
        # The (rule, file) pair is the whole point - it names what was not checked.
        assert "api/app.py" in coverage[0].description
        assert "subprocess-injection" in coverage[0].description

    def test_coverage_finding_survives_the_severity_floor(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        payload = {
            "results": [],
            "errors": [{"type": "Timeout", "rule_id": "r", "path": "a.py"}],
        }
        findings = self._run(tmp_path, monkeypatch, payload)
        assert filter_by_min_severity(findings, "critical") != []

    def test_no_errors_means_no_coverage_finding(self, tmp_path: Path, monkeypatch) -> None:
        payload = {"results": [], "errors": [], "paths": {"skipped": []}}
        assert self._run(tmp_path, monkeypatch, payload) == []

    def test_non_timeout_errors_are_still_reported(self, tmp_path: Path, monkeypatch) -> None:
        payload = {
            "results": [],
            "errors": [{"type": "SyntaxError", "path": "broken.py", "message": "bad syntax"}],
        }
        findings = self._run(tmp_path, monkeypatch, payload)
        coverage = [f for f in findings if f.id == "semgrep-partial-coverage"]
        assert len(coverage) == 1
        assert "broken.py" in coverage[0].description

    def test_real_results_are_kept_alongside_the_coverage_finding(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        payload = {
            "results": [
                {
                    "check_id": "python.lang.security.audit.eval-detected",
                    "path": "app.py",
                    "start": {"line": 10},
                    "extra": {"severity": "ERROR", "message": "eval is dangerous"},
                }
            ],
            "errors": [{"type": "Timeout", "rule_id": "r", "path": "slow.py"}],
        }
        findings = self._run(tmp_path, monkeypatch, payload)
        assert {f.id for f in findings} >= {"semgrep-partial-coverage"}
        assert any(f.tool == "semgrep" and not f.is_meta for f in findings)


class TestDependencyInstallPathCoverage:
    """A repo shipping both a lockfile and open version floors has two install
    paths, and pip-audit only ever reads one of them. Reporting a single merged
    dependency verdict is wrong for at least one of the project's own users.
    """

    def _run(self, tmp_path: Path, monkeypatch) -> list[Finding]:
        raw_dir = tmp_path / "reports" / "raw"
        raw_dir.mkdir(parents=True)
        (raw_dir / "pip-audit.json").write_text("[]", encoding="utf-8")

        def fake_run_pip_audit(
            repo_path: Path, raw_report_path: Path, audit_input: PipAuditInput
        ) -> PipAuditResult:
            return PipAuditResult(
                installed=True,
                raw_report_path=raw_report_path,
                audit_input=audit_input,
                returncode=0,
            )

        monkeypatch.setattr(
            "scanner.scanners.dependency_scan.run_pip_audit",
            fake_run_pip_audit,
        )
        return scan_dependencies(repo_path=tmp_path, reports_dir=tmp_path / "reports")

    def test_unaudited_lockfile_emits_a_coverage_finding(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        (tmp_path / "uv.lock").write_text("# lock\n", encoding="utf-8")

        findings = self._run(tmp_path, monkeypatch)
        coverage = [f for f in findings if f.id == "dependency-scan-unaudited-lockfile"]
        assert len(coverage) == 1
        assert coverage[0].is_meta is True
        assert "uv.lock" in coverage[0].description

    def test_coverage_finding_survives_the_severity_floor(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        (tmp_path / "poetry.lock").write_text("# lock\n", encoding="utf-8")

        findings = self._run(tmp_path, monkeypatch)
        assert filter_by_min_severity(findings, "critical") != []

    def test_no_lockfile_means_no_coverage_finding(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        findings = self._run(tmp_path, monkeypatch)
        assert [f for f in findings if f.id == "dependency-scan-unaudited-lockfile"] == []

    def test_requirements_input_with_a_lockfile_still_warns(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """requirements.txt wins the input race, so uv.lock is still unread."""
        (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
        (tmp_path / "uv.lock").write_text("# lock\n", encoding="utf-8")

        findings = self._run(tmp_path, monkeypatch)
        coverage = [f for f in findings if f.id == "dependency-scan-unaudited-lockfile"]
        assert len(coverage) == 1

    def test_locked_project_input_does_not_warn_about_its_own_lock(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """pylock.*.toml IS the audited input - warning about it would be noise."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        (tmp_path / "pylock.main.toml").write_text("# lock\n", encoding="utf-8")

        findings = self._run(tmp_path, monkeypatch)
        assert [f for f in findings if f.id == "dependency-scan-unaudited-lockfile"] == []


class TestPipAuditTimeout:
    """pip-audit has no internal time bound and has hung whole scans."""

    def test_timeout_produces_a_scan_error_instead_of_hanging(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        import subprocess

        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

        def fake_run(*args: object, **kwargs: object):
            raise subprocess.TimeoutExpired(cmd="pip-audit", timeout=300)

        monkeypatch.setattr(
            "scanner.tools.pip_audit_runner.find_pip_audit_command",
            lambda: ["pip-audit"],
        )
        monkeypatch.setattr("scanner.tools.pip_audit_runner.subprocess.run", fake_run)

        findings = scan_dependencies(repo_path=tmp_path, reports_dir=tmp_path / "reports")
        errors = [f for f in findings if f.id == "pip-audit-scan-error"]
        assert len(errors) == 1
        assert errors[0].is_meta is True
        assert "timed out" in errors[0].description

    def test_timeout_writes_an_empty_raw_report(self, tmp_path: Path, monkeypatch) -> None:
        """The raw artifact must exist so downstream parsing never sees a 0-byte file."""
        import subprocess

        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

        def fake_run(*args: object, **kwargs: object):
            raise subprocess.TimeoutExpired(cmd="pip-audit", timeout=300)

        monkeypatch.setattr(
            "scanner.tools.pip_audit_runner.find_pip_audit_command",
            lambda: ["pip-audit"],
        )
        monkeypatch.setattr("scanner.tools.pip_audit_runner.subprocess.run", fake_run)

        scan_dependencies(repo_path=tmp_path, reports_dir=tmp_path / "reports")
        raw = tmp_path / "reports" / "raw" / "pip-audit.json"
        assert raw.read_text(encoding="utf-8") == "[]"

    def test_the_timeout_is_actually_passed_to_subprocess(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Guard against the timeout kwarg being dropped in a future refactor."""
        from scanner.tools.pip_audit_runner import DEFAULT_TIMEOUT_SECONDS

        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        captured: dict[str, object] = {}

        class _Completed:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(command: object, **kwargs: object):
            captured.update(kwargs)
            return _Completed()

        monkeypatch.setattr(
            "scanner.tools.pip_audit_runner.find_pip_audit_command",
            lambda: ["pip-audit"],
        )
        monkeypatch.setattr("scanner.tools.pip_audit_runner.subprocess.run", fake_run)

        scan_dependencies(repo_path=tmp_path, reports_dir=tmp_path / "reports")
        assert captured["timeout"] == DEFAULT_TIMEOUT_SECONDS
        assert captured["check"] is False


class TestCoverageFindingLeaksNoLocalPaths:
    """The coverage description is published. It must never carry the
    operator's filesystem layout, which Semgrep reports as absolute paths and
    which, on a `--from-git-url` scan, embed the local temp clone directory.
    """

    def _run(self, tmp_path: Path, monkeypatch, errors: list[dict]) -> list[Finding]:
        raw_dir = tmp_path / "reports" / "raw"
        raw_dir.mkdir(parents=True)
        (raw_dir / "semgrep.json").write_text(
            json.dumps({"results": [], "errors": errors}), encoding="utf-8"
        )

        def fake_run_semgrep(repo_path: Path, raw_report_path: Path) -> SemgrepResult:
            return SemgrepResult(installed=True, raw_report_path=raw_report_path, returncode=0)

        monkeypatch.setattr("scanner.scanners.semgrep.run_semgrep", fake_run_semgrep)
        return scan_semgrep(repo_path=tmp_path, reports_dir=tmp_path / "reports")

    def test_absolute_paths_are_rebased_to_repo_relative(self, tmp_path: Path, monkeypatch) -> None:
        target = tmp_path / "custom_components" / "openrag" / "multimodal.py"
        target.parent.mkdir(parents=True)
        target.write_text("x = 1\n", encoding="utf-8")

        findings = self._run(
            tmp_path,
            monkeypatch,
            [{"type": "Timeout", "rule_id": "r.request-with-http", "path": str(target)}],
        )
        description = next(f for f in findings if f.id == "semgrep-partial-coverage").description

        assert "custom_components/openrag/multimodal.py" in description
        assert str(tmp_path) not in description

    def test_no_windows_drive_or_temp_dir_survives(self, tmp_path: Path, monkeypatch) -> None:
        target = tmp_path / "app.py"
        target.write_text("x = 1\n", encoding="utf-8")

        findings = self._run(
            tmp_path,
            monkeypatch,
            [{"type": "Timeout", "rule_id": "r", "path": str(target)}],
        )
        description = next(f for f in findings if f.id == "semgrep-partial-coverage").description

        for leak in ("AppData", "ai-patchlab-clone", r"C:\Users", "/tmp/"):
            assert leak not in description, f"leaked {leak!r}"

    def test_a_path_outside_the_repo_is_still_reported(self, tmp_path: Path, monkeypatch) -> None:
        """Rebasing must not silently drop an error it cannot make relative."""
        findings = self._run(
            tmp_path,
            monkeypatch,
            [{"type": "SyntaxError", "path": "<unknown>", "message": "bad"}],
        )
        description = next(f for f in findings if f.id == "semgrep-partial-coverage").description
        assert "<unknown>" in description


class TestSemgrepNonStringErrorTypes:
    """Semgrep does not always report `type` as a plain string.

    `PartialParsing` arrives as `["PartialParsing", [{"path": ...}, ...]]`.
    Stringifying the whole value put absolute paths in a published description
    even after the per-path rebasing was added, because the path rode in on the
    *label* rather than the path field.
    """

    def _run(self, tmp_path: Path, monkeypatch, errors: list[dict]) -> list[Finding]:
        raw_dir = tmp_path / "reports" / "raw"
        raw_dir.mkdir(parents=True)
        (raw_dir / "semgrep.json").write_text(
            json.dumps({"results": [], "errors": errors}), encoding="utf-8"
        )

        def fake_run_semgrep(repo_path: Path, raw_report_path: Path) -> SemgrepResult:
            return SemgrepResult(installed=True, raw_report_path=raw_report_path, returncode=0)

        monkeypatch.setattr("scanner.scanners.semgrep.run_semgrep", fake_run_semgrep)
        return scan_semgrep(repo_path=tmp_path, reports_dir=tmp_path / "reports")

    def _description(self, findings: list[Finding]) -> str:
        return next(f for f in findings if f.id == "semgrep-partial-coverage").description

    def test_partial_parsing_label_is_just_the_name(self, tmp_path: Path, monkeypatch) -> None:
        workflow = tmp_path / ".github" / "workflows" / "deploy.yaml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("on: push\n", encoding="utf-8")

        description = self._description(
            self._run(
                tmp_path,
                monkeypatch,
                [
                    {
                        "type": ["PartialParsing", [{"path": str(workflow), "start": 1}]],
                        "path": str(workflow),
                    }
                ],
            )
        )
        assert "PartialParsing -> .github/workflows/deploy.yaml" in description
        assert "'start'" not in description
        assert str(tmp_path) not in description

    def test_nested_list_type_is_flattened(self, tmp_path: Path, monkeypatch) -> None:
        target = tmp_path / "a.py"
        target.write_text("x = 1\n", encoding="utf-8")
        description = self._description(
            self._run(tmp_path, monkeypatch, [{"type": [["Deep", 1], 2], "path": str(target)}])
        )
        assert "Deep -> a.py" in description

    def test_scan_root_is_scrubbed_from_any_surviving_text(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Belt and braces: an unknown Semgrep shape must not leak either."""
        description = self._description(
            self._run(
                tmp_path,
                monkeypatch,
                [{"type": "weird " + str(tmp_path) + " trailing", "path": "<unknown>"}],
            )
        )
        assert str(tmp_path) not in description
        assert "AppData" not in description
