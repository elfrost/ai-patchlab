"""Fingerprint module configuration with safe defaults.

All defaults are local-first: short timeouts, hard bytes cap per asset, hard
cap on assets fetched per target, and a stable user agent. No remote service
besides the user-supplied target URL and the seeded git remotes is contacted.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_USER_AGENT = "ai-patchlab-fingerprint/0.1"
DEFAULT_MAX_BYTES_PER_ASSET = 512 * 1024
DEFAULT_MAX_ASSETS_PER_TARGET = 16
DEFAULT_FETCH_READ_TIMEOUT_SECONDS = 10.0
DEFAULT_FETCH_TOTAL_TIMEOUT_SECONDS = 5.0


class FingerprintConfig(BaseSettings):
    """Settings for the fingerprint indexer and matcher."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AI_PATCHLAB_FINGERPRINT_",
        extra="ignore",
    )

    fetch_read_timeout_seconds: float = DEFAULT_FETCH_READ_TIMEOUT_SECONDS
    fetch_total_timeout_seconds: float = DEFAULT_FETCH_TOTAL_TIMEOUT_SECONDS
    max_bytes_per_asset: int = DEFAULT_MAX_BYTES_PER_ASSET
    max_assets_per_target: int = DEFAULT_MAX_ASSETS_PER_TARGET
    user_agent: str = DEFAULT_USER_AGENT
    db_dir: Path = Path("fingerprint/db")
    report_dir: Path = Path("reports/fingerprint")

    @field_validator("fetch_read_timeout_seconds", "fetch_total_timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: float) -> float:
        """Keep timeouts positive and finite."""
        if value <= 0:
            raise ValueError("timeout values must be positive")
        return value

    @field_validator("max_bytes_per_asset", "max_assets_per_target")
    @classmethod
    def validate_positive(cls, value: int) -> int:
        """Keep caps positive."""
        if value <= 0:
            raise ValueError("cap values must be positive")
        return value

    @field_validator("user_agent")
    @classmethod
    def validate_user_agent(cls, value: str) -> str:
        """Reject empty user agents."""
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("user_agent must not be empty")
        return cleaned


def get_fingerprint_config() -> FingerprintConfig:
    """Build a fresh FingerprintConfig from the current environment."""
    return FingerprintConfig()
