"""
Config Pattern — Référence pour la configuration des projets.
Utiliser ce pattern pour TOUTE gestion de configuration dans le projet.

Charge les variables depuis .env avec validation Pydantic.
"""

from pathlib import Path

from loguru import logger
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Configuration principale de l'application, chargée depuis .env"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    env: str = "development"
    log_level: str = "DEBUG"
    project_name: str = "my-project"

    # --- Database ---
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = ""

    # --- Discord ---
    discord_webhook_url: str = ""

    # --- API Keys (optionnelles) ---
    openrouter_api_key: str = ""
    cno_api_key: str = ""

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Valide que le log level est supporté par loguru."""
        allowed = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        """Vérifie si on est en production."""
        return self.env.lower() == "production"

    @property
    def database_url(self) -> str:
        """Construit l'URL de connexion MySQL."""
        return (
            f"mysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


# --- Singleton pattern pour accès global ---

_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Retourne la config singleton. Charge depuis .env au premier appel."""
    global _config
    if _config is None:
        _config = AppConfig()
        logger.info(f"Config loaded: env={_config.env}, db={_config.mysql_database}")
    return _config


def get_project_root() -> Path:
    """Retourne le chemin racine du projet (où se trouve .env)."""
    return Path(__file__).parent.parent


# --- Usage Example ---


def main():
    config = get_config()

    logger.info(f"Environment: {config.env}")
    logger.info(f"Database: {config.database_url}")
    logger.info(f"Production: {config.is_production}")
    logger.info(f"Log level: {config.log_level}")

    if not config.discord_webhook_url:
        logger.warning("Discord webhook not configured")

    if not config.mysql_password:
        logger.warning("Database password is empty")


if __name__ == "__main__":
    main()
