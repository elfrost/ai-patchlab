"""Fingerprint module: index curated repos and match a live target."""

from fingerprint.models import (
    AssetFingerprint,
    HtmlSignature,
    MatchResult,
    MatchSignal,
    RepoFingerprint,
)

__all__ = (
    "AssetFingerprint",
    "HtmlSignature",
    "MatchResult",
    "MatchSignal",
    "RepoFingerprint",
)
