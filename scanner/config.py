"""AI PatchLab scanner configuration with safe defaults.

AI review is disabled by default. No paid API, hosted model, or remote endpoint
is contacted unless the user explicitly enables a supported local provider via
environment variables.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SUPPORTED_AI_REVIEW_PROVIDERS = ("disabled", "local_command")


class AiReviewConfig(BaseSettings):
    """Disabled-by-default settings for AI security review."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AI_PATCHLAB_",
        extra="ignore",
    )

    ai_review_enabled: bool = False
    ai_review_provider: str = "disabled"
    ai_review_command: str = ""
    ai_review_timeout_seconds: int = 120

    @field_validator("ai_review_provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        """Reject unsupported provider names early."""
        normalized = (value or "").strip().lower()
        if normalized not in SUPPORTED_AI_REVIEW_PROVIDERS:
            raise ValueError(
                "ai_review_provider must be one of "
                f"{', '.join(SUPPORTED_AI_REVIEW_PROVIDERS)}; got {value!r}."
            )
        return normalized

    @field_validator("ai_review_timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: int) -> int:
        """Keep the timeout positive and finite."""
        if value <= 0:
            raise ValueError("ai_review_timeout_seconds must be a positive integer.")
        return value

    @property
    def is_local_command_ready(self) -> bool:
        """Return True only when local_command is fully configured."""
        return (
            self.ai_review_enabled
            and self.ai_review_provider == "local_command"
            and bool(self.ai_review_command.strip())
        )


def get_ai_review_config() -> AiReviewConfig:
    """Build a fresh AiReviewConfig from the current environment."""
    return AiReviewConfig()
