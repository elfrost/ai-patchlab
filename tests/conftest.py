"""
Fixtures pytest partagées — Disponibles automatiquement dans tous les tests.
Ajouter ici les fixtures communes (DB mock, config test, etc.)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

# --- Event Loop ---


@pytest.fixture(scope="session")
def event_loop():
    """Crée un event loop partagé pour tous les tests async."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# --- Database Mock ---


@pytest.fixture
def mock_db():
    """Mock de la classe Database pour éviter les vrais appels MySQL."""
    db = AsyncMock()
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()
    db.execute = AsyncMock(return_value=1)
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_all = AsyncMock(return_value=[])
    return db


# --- HTTP Client Mock ---


@pytest.fixture
def mock_http_client():
    """Mock httpx.AsyncClient pour les appels API externes."""
    client = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {}
    response.raise_for_status = MagicMock()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    return client


# --- Discord Mock ---


@pytest.fixture
def mock_discord():
    """Mock pour DiscordAlert — évite les vrais envois webhook."""
    discord = AsyncMock()
    discord.send = AsyncMock(return_value=True)
    return discord


# --- Config Test ---


@pytest.fixture
def test_config():
    """Configuration de test avec des valeurs par défaut sûres."""
    return {
        "mysql_host": "localhost",
        "mysql_port": 3306,
        "mysql_user": "test",
        "mysql_password": "test",
        "mysql_database": "test_db",
        "discord_webhook_url": "https://discord.com/api/webhooks/test/test",
        "log_level": "DEBUG",
        "env": "test",
    }
