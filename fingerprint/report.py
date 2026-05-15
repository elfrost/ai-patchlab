"""JSON + Markdown report writers for fingerprint match results."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fingerprint.models import BANDS, MatchResult

DISCLAIMER = (
    "Probable template match — manual verification required. "
    "This report is a probabilistic signal, not an attribution."
)

BAND_HEADINGS: dict[str, str] = {
    "strong": "Strong matches (score ≥ 0.6)",
    "plausible": "Plausible matches (0.3 ≤ score < 0.6)",
    "weak": "Weak matches (score < 0.3)",
}


def build_match_payload(
    target_url: str,
    fetched_at: str,
    results: tuple[MatchResult, ...],
    notes: str,
) -> dict[str, Any]:
    """Build the JSON payload for a match report."""
    return {
        "target": target_url,
        "fetched_at": fetched_at,
        "disclaimer": DISCLAIMER,
        "notes": notes,
        "results": [result.to_dict() for result in results],
    }


def write_json_report(payload: dict[str, Any], path: Path) -> None:
    """Write the JSON match report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown_report(
    payload: dict[str, Any],
    path: Path,
    min_score: float = 0.0,
) -> None:
    """Write a human-readable Markdown match report.

    The disclaimer is emitted at the top, even for empty result sets. Results
    below ``min_score`` are dropped from the Markdown (but remain in JSON).
    """
    target = payload["target"]
    fetched_at = payload["fetched_at"]
    notes = payload.get("notes", "")

    lines = [
        "# Fingerprint match report",
        "",
        f"**Target:** {target}",
        f"**Fetched:** {fetched_at}",
        f"**Disclaimer:** {DISCLAIMER}",
        "",
    ]

    grouped: dict[str, list[dict[str, Any]]] = {band: [] for band in BANDS}
    for result in payload.get("results", []):
        if result.get("score", 0.0) < min_score:
            continue
        grouped.setdefault(result["band"], []).append(result)

    for band in ("strong", "plausible", "weak"):
        results = grouped.get(band, [])
        lines.extend([f"## {BAND_HEADINGS[band]}", ""])
        if not results:
            lines.extend(["_No matches in this band._", ""])
            continue
        results.sort(key=lambda r: (-float(r.get("score", 0.0)), r.get("repo_slug", "")))
        for result in results:
            lines.extend(
                [
                    f"### {result['repo_slug']} — score {result['score']:.2f}",
                    "",
                ]
            )
            signals = result.get("signals", [])
            if not signals:
                lines.append("- (no individual signals — see notes)")
            else:
                for signal in signals:
                    lines.append(f"- {signal['detail']} (weight: {signal['weight']})")
            result_notes = result.get("notes", "")
            if result_notes:
                lines.append(f"- notes: {result_notes}")
            lines.append("")

    lines.extend(["## Notes", "", f"- {notes or 'ok'}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def report_paths(
    target_url: str,
    report_dir: Path,
    when: datetime | None = None,
) -> dict[str, Path]:
    """Return JSON and Markdown report paths for ``target_url``.

    File names follow ``match_<host>_<UTC-YYYYMMDD-HHMMSS>.{json,md}``. Host
    is sanitized to ``[a-z0-9-]+`` to keep paths safe.
    """
    import re
    from urllib.parse import urlparse

    parsed = urlparse(target_url)
    host = (parsed.netloc or "unknown-host").lower()
    safe_host = re.sub(r"[^a-z0-9-]+", "-", host).strip("-") or "unknown-host"

    timestamp = (when or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    stem = f"match_{safe_host}_{timestamp}"
    return {
        "json": report_dir / f"{stem}.json",
        "markdown": report_dir / f"{stem}.md",
    }
