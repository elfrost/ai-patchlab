"""Validation and aggregation for the dismissal corpus.

Split from `scanner.verdicts`, which owns the record and its producers; this
module owns reading a corpus back and proving it is trustworthy.

The curation half of `verdicts.json` is written as JSON by hand during `/daily`
Phase 4, so nothing constructs a `VerdictRecord` and nothing enforces the closed
vocabularies. A closed vocabulary is only closed if something closes it: on its
first production run, scan #109 wrote six curation rows with an empty `rule` and
free prose in `verdict`. Both are exactly what makes a corpus uncountable later
(ADR-017).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scanner.verdicts import (
    REASON_CODES,
    VERDICT_SOURCES,
    VERDICTS,
    VerdictRecord,
    count_by_reason,
    load_records,
    total_dismissed,
)


def validate_payload(payload: dict[str, Any]) -> list[str]:
    """Return every problem in a `verdicts.json` payload, as readable sentences.

    `load_records` raises on the first bad row, which is right for a library and
    useless for a check run: the curation half of the corpus is written as JSON
    by hand, so nothing constructs a `VerdictRecord` and nothing enforces the
    closed vocabularies. This collects all problems at once so one run shows the
    whole repair list.

    Returns:
        An empty list when the payload is valid.
    """
    problems: list[str] = []
    rows = payload.get("records")
    if not isinstance(rows, list):
        return ["`records` is missing or is not a list."]

    for index, row in enumerate(rows):
        where = f"record {index}"
        if not isinstance(row, dict):
            problems.append(f"{where}: not an object.")
            continue

        label = f"{where} ({row.get('reason_code', '?')}/{row.get('rule') or 'no rule'})"
        # Each field is checked on its own rather than through `VerdictRecord`,
        # which raises on the first failure. A repair list that reveals one
        # problem per run costs as many runs as there are problems.
        if row.get("source") not in VERDICT_SOURCES:
            problems.append(
                f"{label}: source {row.get('source')!r} is not one of {VERDICT_SOURCES}."
            )
        if row.get("reason_code") not in REASON_CODES:
            problems.append(
                f"{label}: reason_code {row.get('reason_code')!r} is not in the vocabulary."
            )
        if not str(row.get("rule", "")).strip():
            problems.append(
                f"{label}: rule is empty - name the rule family so the row is actionable."
            )
        if not str(row.get("tool", "")).strip():
            problems.append(f"{label}: tool is empty.")
        verdict = str(row.get("verdict", ""))
        if verdict and verdict not in VERDICTS:
            problems.append(
                f"{label}: verdict {verdict!r} is not one of {VERDICTS} - "
                "the sentence belongs in `detail`."
            )
        try:
            if int(row.get("count", 0)) < 1:
                problems.append(f"{label}: count must be at least 1.")
        except (TypeError, ValueError):
            problems.append(f"{label}: count {row.get('count')!r} is not a number.")

    if not problems:
        records = load_records(payload)
        declared = payload.get("total_dismissed")
        actual = total_dismissed(records)
        if declared is not None and declared != actual:
            problems.append(f"`total_dismissed` says {declared} but the rows count {actual}.")
        declared_reasons = payload.get("by_reason")
        actual_reasons = count_by_reason(records)
        if declared_reasons is not None and declared_reasons != actual_reasons:
            problems.append(
                f"`by_reason` says {declared_reasons} but the rows give {actual_reasons}."
            )

    return problems


def load_corpus(directory: Path) -> tuple[VerdictRecord, ...]:
    """Load every archived verdict file under `directory`, sorted by name.

    This is the accumulating corpus: one file per scan, committed, so the
    measurement that justified ADR-014 becomes a `sum()` rather than an
    archaeology project over whatever happens to still be on one machine.
    """
    records: list[VerdictRecord] = []
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.extend(load_records(payload))
    return tuple(records)
