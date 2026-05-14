"""Normalized data contracts for web template fingerprinting."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

ASSET_KINDS = ("favicon", "css", "js", "image", "other")
SIGNATURE_KINDS = ("meta-generator", "class", "id", "data-attr", "comment")
WEIGHTS = ("high", "medium", "low")
BANDS = ("weak", "plausible", "strong")

_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def band_for_score(score: float) -> str:
    """Return the band label for a given match score.

    Single source of truth used by both writer and validator.
    """
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"score must be in [0.0, 1.0]; got {score}")
    if score < 0.3:
        return "weak"
    if score < 0.6:
        return "plausible"
    return "strong"


@dataclass(frozen=True)
class AssetFingerprint:
    """Hash and metadata for one distinctive repo asset."""

    relative_path: str
    sha256: str
    byte_size: int
    kind: str

    def __post_init__(self) -> None:
        """Validate fingerprint shape."""
        if not self.relative_path.strip():
            raise ValueError("relative_path must not be empty")
        if not _SHA256_PATTERN.match(self.sha256):
            raise ValueError(f"sha256 must be 64 lowercase hex chars; got {self.sha256!r}")
        if self.byte_size < 0:
            raise ValueError(f"byte_size must be >= 0; got {self.byte_size}")
        if self.kind not in ASSET_KINDS:
            raise ValueError(f"kind must be one of {ASSET_KINDS}; got {self.kind!r}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict."""
        return asdict(self)


@dataclass(frozen=True)
class HtmlSignature:
    """One HTML-level marker extracted from a template repo."""

    kind: str
    pattern: str
    weight: str

    def __post_init__(self) -> None:
        """Validate signature shape."""
        if self.kind not in SIGNATURE_KINDS:
            raise ValueError(f"kind must be one of {SIGNATURE_KINDS}; got {self.kind!r}")
        if not self.pattern.strip():
            raise ValueError("pattern must not be empty")
        if self.weight not in WEIGHTS:
            raise ValueError(f"weight must be one of {WEIGHTS}; got {self.weight!r}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict."""
        return asdict(self)


@dataclass(frozen=True)
class RepoFingerprint:
    """Deterministic fingerprint of a seeded template repository."""

    slug: str
    repo_url: str
    indexed_at: str
    assets: tuple[AssetFingerprint, ...] = ()
    html_signatures: tuple[HtmlSignature, ...] = ()
    notable_paths: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate fingerprint shape."""
        if not self.slug.strip():
            raise ValueError("slug must not be empty")
        if not self.repo_url.startswith(("https://", "http://")):
            raise ValueError(f"repo_url must start with https:// or http://; got {self.repo_url!r}")
        if not self.indexed_at.strip():
            raise ValueError("indexed_at must not be empty")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict."""
        return {
            "slug": self.slug,
            "repo_url": self.repo_url,
            "indexed_at": self.indexed_at,
            "assets": [asset.to_dict() for asset in self.assets],
            "html_signatures": [sig.to_dict() for sig in self.html_signatures],
            "notable_paths": list(self.notable_paths),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class MatchSignal:
    """One concrete signal that the target matches a repo fingerprint."""

    kind: str
    detail: str
    weight: str

    def __post_init__(self) -> None:
        """Validate signal shape."""
        if not self.kind.strip():
            raise ValueError("kind must not be empty")
        if not self.detail.strip():
            raise ValueError("detail must not be empty")
        if self.weight not in WEIGHTS:
            raise ValueError(f"weight must be one of {WEIGHTS}; got {self.weight!r}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict."""
        return asdict(self)


@dataclass(frozen=True)
class MatchResult:
    """Ranked result for one repo fingerprint applied to a target snapshot."""

    target_url: str
    fetched_at: str
    repo_slug: str
    score: float
    band: str
    signals: tuple[MatchSignal, ...] = field(default_factory=tuple)
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate match shape."""
        if not self.target_url.startswith(("https://", "http://")):
            raise ValueError(
                f"target_url must start with https:// or http://; got {self.target_url!r}"
            )
        if not self.fetched_at.strip():
            raise ValueError("fetched_at must not be empty")
        if not self.repo_slug.strip():
            raise ValueError("repo_slug must not be empty")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0.0, 1.0]; got {self.score}")
        if self.band not in BANDS:
            raise ValueError(f"band must be one of {BANDS}; got {self.band!r}")
        expected_band = band_for_score(self.score)
        if self.band != expected_band:
            raise ValueError(
                f"band {self.band!r} does not match score {self.score} (expected {expected_band!r})"
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict."""
        return {
            "target_url": self.target_url,
            "fetched_at": self.fetched_at,
            "repo_slug": self.repo_slug,
            "score": self.score,
            "band": self.band,
            "signals": [signal.to_dict() for signal in self.signals],
            "notes": self.notes,
        }
