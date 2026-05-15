"""Fingerprint matcher registry.

Each matcher takes a `(RepoFingerprint, TargetSnapshot)` pair and returns a
list of `MatchSignal`. Matchers never mutate inputs and never raise on a
mismatch — an absence of signal is the empty list.
"""

from collections.abc import Callable

from fingerprint.matchers.asset_hash import match_asset_hashes
from fingerprint.matchers.html_regex import match_html_signatures
from fingerprint.models import MatchSignal, RepoFingerprint
from fingerprint.web_probe import TargetSnapshot

Matcher = Callable[[RepoFingerprint, TargetSnapshot], list[MatchSignal]]

MATCHERS: tuple[Matcher, ...] = (
    match_asset_hashes,
    match_html_signatures,
)

__all__ = (
    "MATCHERS",
    "Matcher",
    "match_asset_hashes",
    "match_html_signatures",
)
