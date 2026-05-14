"""Tests for the disabled-by-default AI security review adapter."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scanner.config import AiReviewConfig
from scanner.scanners import ai_review as ai_review_module
from scanner.scanners.ai_review import scan_ai_security_review
from scanner.tools import ai_review_runner as ai_review_runner_module
from scanner.tools.ai_review_runner import AiReviewResult, run_ai_review_command


@pytest.fixture(autouse=True)
def _clean_ai_review_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no developer .env values leak into AI review tests."""
    for var in (
        "AI_PATCHLAB_AI_REVIEW_ENABLED",
        "AI_PATCHLAB_AI_REVIEW_PROVIDER",
        "AI_PATCHLAB_AI_REVIEW_COMMAND",
        "AI_PATCHLAB_AI_REVIEW_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(var, raising=False)


def _disabled_config() -> AiReviewConfig:
    return AiReviewConfig(
        ai_review_enabled=False,
        ai_review_provider="disabled",
        ai_review_command="",
    )


def _local_command_config(command: str = r"C:\tools\ai-review-wrapper.cmd") -> AiReviewConfig:
    return AiReviewConfig(
        ai_review_enabled=True,
        ai_review_provider="local_command",
        ai_review_command=command,
        ai_review_timeout_seconds=30,
    )


def test_ai_review_config_defaults_are_disabled() -> None:
    config = AiReviewConfig()

    assert config.ai_review_enabled is False
    assert config.ai_review_provider == "disabled"
    assert config.ai_review_command == ""
    assert config.ai_review_timeout_seconds == 120
    assert config.is_local_command_ready is False


def test_ai_review_config_rejects_unsupported_provider() -> None:
    with pytest.raises(ValueError):
        AiReviewConfig(ai_review_provider="openai")


def test_ai_review_config_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError):
        AiReviewConfig(ai_review_timeout_seconds=0)


def test_ai_review_disabled_returns_normalized_info_finding(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    def _fail_subprocess(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called when AI review is disabled.")

    monkeypatch.setattr(subprocess, "run", _fail_subprocess)
    monkeypatch.setattr(ai_review_runner_module.subprocess, "run", _fail_subprocess)

    findings = scan_ai_security_review(repo_path, reports_dir, config=_disabled_config())

    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "ai-review-disabled"
    assert finding.tool == "ai-security-review"
    assert finding.severity == "info"
    assert finding.confidence == "high"
    assert finding.file == str(repo_path)
    assert "disabled by default" in finding.description.lower()


def test_ai_review_enabled_but_missing_command_returns_not_configured(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    config = AiReviewConfig(
        ai_review_enabled=True,
        ai_review_provider="local_command",
        ai_review_command="   ",
    )

    findings = scan_ai_security_review(repo_path, reports_dir, config=config)

    assert len(findings) == 1
    assert findings[0].id == "ai-review-not-configured"
    assert findings[0].severity == "info"


def test_ai_review_runner_skips_subprocess_when_not_configured(tmp_path: Path, monkeypatch) -> None:
    def _fail_subprocess(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called when AI review is not configured.")

    monkeypatch.setattr(ai_review_runner_module.subprocess, "run", _fail_subprocess)

    result = run_ai_review_command(
        repo_path=tmp_path / "repo",
        reports_dir=tmp_path / "reports",
        config=_disabled_config(),
    )

    assert result.configured is False
    assert result.completed is False
    assert result.command == ()
    assert result.returncode is None


def test_ai_review_runner_builds_expected_command(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        (reports_dir / "raw" / "ai-review.json").write_text("[]", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(ai_review_runner_module.subprocess, "run", fake_run)

    config = _local_command_config()
    result = run_ai_review_command(
        repo_path=repo_path,
        reports_dir=reports_dir,
        config=config,
    )

    expected_output = reports_dir / "raw" / "ai-review.json"
    assert captured["command"] == [
        config.ai_review_command,
        "--repo",
        str(repo_path),
        "--output",
        str(expected_output),
    ]
    kwargs = captured["kwargs"]
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False
    assert kwargs["timeout"] == config.ai_review_timeout_seconds
    assert "shell" not in kwargs
    assert result.configured is True
    assert result.completed is True
    assert result.returncode == 0


def test_ai_review_runner_writes_stdout_when_output_missing(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    payload = '[{"title": "Example", "description": "Example finding"}]'

    def fake_run(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout=payload, stderr="")

    monkeypatch.setattr(ai_review_runner_module.subprocess, "run", fake_run)

    result = run_ai_review_command(
        repo_path=repo_path,
        reports_dir=reports_dir,
        config=_local_command_config(),
    )

    raw_report = reports_dir / "raw" / "ai-review.json"
    assert raw_report.exists()
    assert raw_report.read_text(encoding="utf-8") == payload
    assert result.completed is True


def test_ai_review_runner_handles_timeout(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs.get("timeout", 0))

    monkeypatch.setattr(ai_review_runner_module.subprocess, "run", fake_run)

    result = run_ai_review_command(
        repo_path=repo_path,
        reports_dir=reports_dir,
        config=_local_command_config(),
    )

    raw_report = reports_dir / "raw" / "ai-review.json"
    assert raw_report.exists()
    assert result.returncode == 124
    assert "timed out" in result.stderr.lower()


def test_ai_review_runner_handles_os_error(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()

    def fake_run(command, **kwargs):
        raise OSError("ai review wrapper not found")

    monkeypatch.setattr(ai_review_runner_module.subprocess, "run", fake_run)

    result = run_ai_review_command(
        repo_path=repo_path,
        reports_dir=reports_dir,
        config=_local_command_config(),
    )

    assert result.returncode == 127
    assert "not found" in result.stderr
    assert (reports_dir / "raw" / "ai-review.json").read_text(encoding="utf-8") == "[]"


def test_ai_review_configured_local_command_maps_findings_to_schema(
    tmp_path: Path, monkeypatch
) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    config = _local_command_config()

    def fake_runner(repo_path, reports_dir, cfg):
        raw_report_path = reports_dir / "raw" / "ai-review.json"
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text(
            json.dumps(
                [
                    {
                        "id": "ai-review-example",
                        "severity": "Medium",
                        "title": "Potential unsafe dynamic execution",
                        "description": "Risky execution pattern detected.",
                        "file": "src/example.py",
                        "line": 42,
                        "recommendation": "Replace with an allowlisted dispatcher.",
                        "confidence": "MEDIUM",
                    }
                ]
            ),
            encoding="utf-8",
        )
        return AiReviewResult(
            configured=True,
            raw_report_path=raw_report_path,
            returncode=0,
        )

    monkeypatch.setattr(ai_review_module, "run_ai_review_command", fake_runner)

    findings = scan_ai_security_review(repo_path, reports_dir, config=config)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.tool == "ai-security-review"
    assert finding.severity == "medium"
    assert finding.confidence == "medium"
    assert finding.title == "Potential unsafe dynamic execution"
    assert finding.file == "src/example.py"
    assert finding.line == 42
    assert finding.id.startswith("ai-review-")
    assert finding.patch_before == ""
    assert finding.patch_after == ""
    assert finding.remediation_explanation == ""


def test_ai_review_accepts_findings_wrapper_shape(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    config = _local_command_config()

    def fake_runner(repo_path, reports_dir, cfg):
        raw_report_path = reports_dir / "raw" / "ai-review.json"
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text(
            json.dumps(
                {
                    "findings": [
                        {
                            "title": "Wrapped finding",
                            "description": "Wrapped description",
                            "severity": "low",
                            "confidence": "low",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return AiReviewResult(
            configured=True,
            raw_report_path=raw_report_path,
            returncode=0,
        )

    monkeypatch.setattr(ai_review_module, "run_ai_review_command", fake_runner)

    findings = scan_ai_security_review(repo_path, reports_dir, config=config)

    assert len(findings) == 1
    assert findings[0].title == "Wrapped finding"
    assert findings[0].severity == "low"
    assert findings[0].confidence == "low"


def test_ai_review_fallback_on_invalid_json(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    config = _local_command_config()

    def fake_runner(repo_path, reports_dir, cfg):
        raw_report_path = reports_dir / "raw" / "ai-review.json"
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text("{not valid json", encoding="utf-8")
        return AiReviewResult(
            configured=True,
            raw_report_path=raw_report_path,
            returncode=0,
        )

    monkeypatch.setattr(ai_review_module, "run_ai_review_command", fake_runner)

    findings = scan_ai_security_review(repo_path, reports_dir, config=config)

    assert len(findings) == 1
    assert findings[0].id == "ai-review-json-parse-error"
    assert findings[0].severity == "info"


def test_ai_review_fallback_on_command_error(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    config = _local_command_config()

    def fake_runner(repo_path, reports_dir, cfg):
        raw_report_path = reports_dir / "raw" / "ai-review.json"
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text("[]", encoding="utf-8")
        return AiReviewResult(
            configured=True,
            raw_report_path=raw_report_path,
            returncode=2,
            stderr="wrapper crashed",
        )

    monkeypatch.setattr(ai_review_module, "run_ai_review_command", fake_runner)

    findings = scan_ai_security_review(repo_path, reports_dir, config=config)

    assert len(findings) == 1
    assert findings[0].id == "ai-review-command-error"
    assert findings[0].description == "wrapper crashed"


def test_ai_review_drops_invalid_records(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "repo"
    reports_dir = tmp_path / "reports"
    repo_path.mkdir()
    config = _local_command_config()

    def fake_runner(repo_path, reports_dir, cfg):
        raw_report_path = reports_dir / "raw" / "ai-review.json"
        raw_report_path.parent.mkdir(parents=True, exist_ok=True)
        raw_report_path.write_text(
            json.dumps(
                [
                    {},
                    {"title": "", "description": ""},
                    "not-a-dict",
                ]
            ),
            encoding="utf-8",
        )
        return AiReviewResult(
            configured=True,
            raw_report_path=raw_report_path,
            returncode=0,
        )

    monkeypatch.setattr(ai_review_module, "run_ai_review_command", fake_runner)

    findings = scan_ai_security_review(repo_path, reports_dir, config=config)

    assert len(findings) == 1
    assert findings[0].id == "ai-review-no-findings"
    assert findings[0].severity == "info"
