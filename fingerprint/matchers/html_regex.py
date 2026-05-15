"""Match HTML signatures from a fingerprint against the target homepage."""

from __future__ import annotations

import re

from fingerprint.models import HtmlSignature, MatchSignal, RepoFingerprint
from fingerprint.web_probe import TargetSnapshot

# Reject patterns that look unbounded or pathological. v0.1 only matches
# plain substrings — the "regex" tag in the PRP refers to a future direction.
_NESTED_QUANTIFIER = re.compile(r"[*+?]\s*[*+?]")


def _is_safe_pattern(pattern: str) -> bool:
    """Return True when the pattern is safe to use as a plain substring."""
    if not pattern.strip():
        return False
    if _NESTED_QUANTIFIER.search(pattern):
        return False
    return True


def _build_detail(signature: HtmlSignature) -> str:
    """Build a human-readable detail line for a matched signature."""
    if signature.kind == "meta-generator":
        return f"meta-generator: {signature.pattern}"
    if signature.kind == "class":
        return f"class `{signature.pattern}` present"
    if signature.kind == "id":
        return f"id `{signature.pattern}` present"
    if signature.kind == "data-attr":
        return f"data attribute {signature.pattern} present"
    if signature.kind == "comment":
        return f"comment marker `{signature.pattern}` present"
    return f"{signature.kind}: {signature.pattern}"


def match_html_signatures(
    repo: RepoFingerprint,
    snapshot: TargetSnapshot,
) -> list[MatchSignal]:
    """Return one signal per HTML signature found in the homepage bytes.

    Uses plain substring matching against the decoded homepage HTML. Patterns
    with nested quantifiers are rejected to keep matching cheap and bounded.
    """
    if not repo.html_signatures or not snapshot.homepage_html:
        return []

    html_text = snapshot.homepage_html.decode("utf-8", errors="replace")
    signals: list[MatchSignal] = []
    for signature in repo.html_signatures:
        if not _is_safe_pattern(signature.pattern):
            continue
        if signature.pattern not in html_text:
            continue
        signals.append(
            MatchSignal(
                kind=f"html-{signature.kind}",
                detail=_build_detail(signature),
                weight=signature.weight,
            )
        )
    return signals
