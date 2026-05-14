"""AI security review adapter.

The first AI review implementation is disabled by default. When the user
explicitly enables a local command provider, AI PatchLab invokes the
configured executable, parses its JSON output, and normalizes results into the
shared `Finding` schema. No paid API, hosted model, or remote endpoint is
contacted by default. Failures are surfaced as `info` findings so the full
security report still completes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scanner.config import AiReviewConfig, get_ai_review_config
from scanner.models import CONFIDENCES, SEVERITIES, Finding
from scanner.recommendations import enrich_findings
from scanner.remediation import apply_patch_suggestions
from scanner.tools.ai_review_runner import AiReviewResult, run_ai_review_command

AI_REVIEW_TOOL = "ai-security-review"


def scan_ai_security_review(
    repo_path: Path,
    reports_dir: Path,
    config: AiReviewConfig | None = None,
) -> list[Finding]:
    """Run AI review only when the user explicitly opts in, else return info findings."""
    config = config or get_ai_review_config()

    if not config.ai_review_enabled:
        return [_disabled_finding(repo_path)]

    if not config.is_local_command_ready:
        return [_not_configured_finding(repo_path)]

    result = run_ai_review_command(repo_path, reports_dir, config)

    try:
        records = _read_ai_review_records(result.raw_report_path)
    except json.JSONDecodeError:
        return [_json_parse_error_finding(repo_path, result.raw_report_path)]

    findings = _map_ai_review_records(records, repo_path)

    if result.returncode not in {0, None} and not findings:
        return [_command_error_finding(repo_path, result)]

    if not findings:
        return [_empty_result_finding(repo_path, result)]

    return apply_patch_suggestions(enrich_findings(findings))


def _read_ai_review_records(raw_report_path: Path) -> list[dict[str, Any]]:
    """Read AI review records from disk, accepting list or `{findings: [...]}` shape."""
    if not raw_report_path.exists():
        return []

    raw_text = raw_report_path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw_text:
        return []

    data = json.loads(raw_text)
    if isinstance(data, list):
        return [record for record in data if isinstance(record, dict)]

    if isinstance(data, dict):
        records = data.get("findings")
        if isinstance(records, list):
            return [record for record in records if isinstance(record, dict)]

    return []


def _map_ai_review_records(
    records: list[dict[str, Any]],
    repo_path: Path,
) -> list[Finding]:
    """Map untrusted AI review records into normalized findings."""
    findings: list[Finding] = []
    for record in records:
        finding = _map_ai_review_record(record, repo_path)
        if finding is not None:
            findings.append(finding)
    return findings


def _map_ai_review_record(
    record: dict[str, Any],
    repo_path: Path,
) -> Finding | None:
    """Map one untrusted AI review record into a `Finding`, dropping invalid entries."""
    title = _get_string(record, "title", default="").strip()
    description = _get_string(record, "description", default="").strip()
    if not title and not description:
        return None

    severity = _validate_choice(record.get("severity"), SEVERITIES, default="info")
    confidence = _validate_choice(record.get("confidence"), CONFIDENCES, default="medium")
    raw_id = _get_string(record, "id", default="").strip()
    finding_id = _stable_id("ai-review", raw_id or title or "finding")
    file_value = _get_string(record, "file", default="").strip()
    line_value = _coerce_line(record.get("line"))
    recommendation = _get_string(
        record,
        "recommendation",
        default="Review the AI security review finding and confirm whether action is required.",
    ).strip()

    return Finding(
        id=finding_id,
        tool=AI_REVIEW_TOOL,
        severity=severity,
        title=title or f"AI security review finding {finding_id}",
        description=description or title,
        file=file_value or str(repo_path),
        line=line_value,
        recommendation=recommendation,
        confidence=confidence,
        patch_before=_get_string(record, "patch_before", default=""),
        patch_after=_get_string(record, "patch_after", default=""),
        remediation_explanation=_get_string(record, "remediation_explanation", default=""),
    )


def _disabled_finding(repo_path: Path) -> Finding:
    return Finding(
        id="ai-review-disabled",
        tool=AI_REVIEW_TOOL,
        severity="info",
        title="AI security review is disabled",
        description=(
            "AI security review is disabled by default. No AI provider was contacted and no "
            "paid API was called for this scan."
        ),
        file=str(repo_path),
        line=None,
        recommendation=(
            "To enable AI review, set AI_PATCHLAB_AI_REVIEW_ENABLED=true, choose a supported "
            "local provider, and configure AI_PATCHLAB_AI_REVIEW_COMMAND. See README for the "
            "local command JSON contract."
        ),
        confidence="high",
    )


def _not_configured_finding(repo_path: Path) -> Finding:
    return Finding(
        id="ai-review-not-configured",
        tool=AI_REVIEW_TOOL,
        severity="info",
        title="AI security review is not fully configured",
        description=(
            "AI review is enabled but the configured provider or local command is incomplete, "
            "so no AI review ran and no paid API was called."
        ),
        file=str(repo_path),
        line=None,
        recommendation=(
            "Set AI_PATCHLAB_AI_REVIEW_PROVIDER=local_command and AI_PATCHLAB_AI_REVIEW_COMMAND "
            "to the absolute path of your local AI review executable."
        ),
        confidence="high",
    )


def _command_error_finding(repo_path: Path, result: AiReviewResult) -> Finding:
    return Finding(
        id="ai-review-command-error",
        tool=AI_REVIEW_TOOL,
        severity="info",
        title="AI security review command did not complete successfully",
        description=_format_scan_error(result.stderr or result.stdout),
        file=str(repo_path),
        line=None,
        recommendation=(
            "Inspect the local AI review command output, fix the wrapper script, and re-run "
            "the scan from PowerShell."
        ),
        confidence="medium",
    )


def _empty_result_finding(repo_path: Path, result: AiReviewResult) -> Finding:
    description = (
        "The local AI review command completed without reporting any findings. "
        f"Raw report: {result.raw_report_path}."
    )
    return Finding(
        id="ai-review-no-findings",
        tool=AI_REVIEW_TOOL,
        severity="info",
        title="AI security review reported no findings",
        description=description,
        file=str(repo_path),
        line=None,
        recommendation=(
            "If you expected findings, verify the AI review wrapper outputs the documented "
            "JSON contract to the configured output path or stdout."
        ),
        confidence="high",
    )


def _json_parse_error_finding(repo_path: Path, raw_report_path: Path) -> Finding:
    return Finding(
        id="ai-review-json-parse-error",
        tool=AI_REVIEW_TOOL,
        severity="info",
        title="AI security review JSON output could not be parsed",
        description=(
            f"The raw AI review report at {raw_report_path} is not valid JSON. The wrapper "
            "must emit either a JSON list of findings or an object with a `findings` array."
        ),
        file=str(repo_path),
        line=None,
        recommendation=(
            "Re-run the AI review wrapper and inspect the raw JSON output for truncation or "
            "invalid formatting."
        ),
        confidence="medium",
    )


def _format_scan_error(output: str) -> str:
    """Keep the captured scanner error short enough for the report."""
    output = (output or "").strip()
    if not output:
        return "AI review command returned an error without additional output."
    return output[:500]


def _stable_id(*parts: str) -> str:
    """Build a stable finding ID from non-empty values."""
    safe_parts = [re.sub(r"[^A-Za-z0-9_.:-]+", "-", part.strip()) for part in parts if part.strip()]
    return "-".join(safe_parts)


def _validate_choice(value: Any, allowed: tuple[str, ...], *, default: str) -> str:
    """Return the lowercased value when in `allowed`, else fall back to `default`."""
    if not isinstance(value, str):
        return default
    normalized = value.strip().lower()
    if normalized in allowed:
        return normalized
    return default


def _coerce_line(value: Any) -> int | None:
    """Return a positive integer line number or None for invalid values."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        line = int(value.strip())
        return line if line > 0 else None
    return None


def _get_string(record: dict[str, Any], key: str, *, default: str) -> str:
    """Return a non-empty string value from `record[key]`, else `default`."""
    value = record.get(key)
    if value is None:
        return default
    text = str(value)
    if not text.strip():
        return default
    return text
