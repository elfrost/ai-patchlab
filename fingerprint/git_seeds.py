"""Curated seed list loader and validator."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

SEEDS_DEFAULT_PATH = Path(__file__).resolve().parent / "seeds" / "repos.json"

_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class SeedLoadError(ValueError):
    """Raised when the seed list cannot be loaded or validated."""


@dataclass(frozen=True)
class SeedEntry:
    """One entry in the curated seed list."""

    slug: str
    repo_url: str
    notable_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the seed entry shape."""
        if not _SLUG_PATTERN.match(self.slug):
            raise SeedLoadError(f"slug must match {_SLUG_PATTERN.pattern}; got {self.slug!r}")
        if not self.repo_url.startswith("https://"):
            raise SeedLoadError(f"repo_url must use https://; got {self.repo_url!r}")


def load_seeds(path: Path | None = None) -> tuple[SeedEntry, ...]:
    """Load and validate the seed list from JSON."""
    seed_path = path or SEEDS_DEFAULT_PATH
    if not seed_path.exists():
        raise SeedLoadError(f"Seed file not found: {seed_path}")

    raw = seed_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SeedLoadError(f"Seed file is not valid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise SeedLoadError("Seed file must contain a JSON list at the root")

    entries: list[SeedEntry] = []
    seen_slugs: set[str] = set()
    for index, raw_entry in enumerate(data):
        if not isinstance(raw_entry, dict):
            raise SeedLoadError(f"Seed entry #{index} is not an object")
        slug = str(raw_entry.get("slug", "")).strip()
        repo_url = str(raw_entry.get("repo_url", "")).strip()
        notable_raw = raw_entry.get("notable_paths") or []
        if not isinstance(notable_raw, list):
            raise SeedLoadError(f"Seed entry {slug!r}: notable_paths must be a list")
        notable = tuple(str(item).strip() for item in notable_raw if str(item).strip())
        entry = SeedEntry(slug=slug, repo_url=repo_url, notable_paths=notable)
        if entry.slug in seen_slugs:
            raise SeedLoadError(f"Duplicate seed slug: {entry.slug!r}")
        seen_slugs.add(entry.slug)
        entries.append(entry)

    return tuple(entries)


def slug_from_repo_url(url: str) -> str:
    """Derive a deterministic kebab-case slug from a git URL."""
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    tail = cleaned.rsplit("/", 1)[-1]
    if "/" in cleaned and "github.com" in cleaned:
        parts = cleaned.split("/")
        if len(parts) >= 2:
            tail = f"{parts[-2]}-{parts[-1]}"
    slug = re.sub(r"[^a-zA-Z0-9-]+", "-", tail).strip("-").lower()
    if not slug:
        slug = "repo"
    if not _SLUG_PATTERN.match(slug):
        slug = re.sub(r"^[^a-z0-9]+", "", slug) or "repo"
    return slug[:64]
