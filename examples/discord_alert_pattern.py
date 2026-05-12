"""
Discord Alert Pattern — Référence pour toutes les alertes Discord.
Utiliser ce pattern pour TOUT envoi de message Discord dans le projet.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel


class AlertType(Enum):
    """Couleurs d'embed par type d'alerte."""

    SUCCESS = 0x00FF00  # Vert
    WARNING = 0xFFAA00  # Jaune/Orange
    ERROR = 0xFF0000  # Rouge
    INFO = 0x0099FF  # Bleu
    EDGE = 0x9B59B6  # Violet — pour les +EV alerts


class AlertField(BaseModel):
    """Un champ dans l'embed Discord."""

    name: str
    value: str
    inline: bool = True


class DiscordAlert:
    """Envoi d'alertes Discord via webhook."""

    def __init__(self, webhook_url: str, rate_limit_seconds: float = 1.0):
        self.webhook_url = webhook_url
        self.rate_limit = rate_limit_seconds
        self._last_sent: float = 0

    async def send(
        self,
        title: str,
        description: str,
        alert_type: AlertType = AlertType.INFO,
        fields: list[AlertField] | None = None,
        footer: str | None = None,
    ) -> bool:
        """Envoie une alerte Discord avec embed."""

        # Rate limiting
        now = asyncio.get_event_loop().time()
        wait = self.rate_limit - (now - self._last_sent)
        if wait > 0:
            await asyncio.sleep(wait)

        embed: dict[str, Any] = {
            "title": title,
            "description": description,
            "color": alert_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if fields:
            embed["fields"] = [f.model_dump() for f in fields]

        if footer:
            embed["footer"] = {"text": footer}

        payload = {"embeds": [embed]}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.webhook_url, json=payload, timeout=10)
                resp.raise_for_status()
                self._last_sent = asyncio.get_event_loop().time()
                logger.debug(f"Discord alert sent: {title}")
                return True
        except httpx.HTTPError as e:
            logger.error(f"Discord alert failed: {e}")
            return False


# --- Usage Examples ---

async def send_edge_alert(alert: DiscordAlert):
    """Exemple: alerte +EV edge trouvé."""
    await alert.send(
        title="🎯 +EV Edge Detected",
        description="NFL — Alternate Spread",
        alert_type=AlertType.EDGE,
        fields=[
            AlertField(name="Book", value="Bet365"),
            AlertField(name="Market", value="KC Chiefs -7.5"),
            AlertField(name="Book Odds", value="+155"),
            AlertField(name="Fair Odds", value="+130"),
            AlertField(name="Edge", value="4.2%"),
            AlertField(name="Bet Size", value="$5.00 (2.5%)"),
        ],
        footer="SharpEdge • Bankroll: $200 CAD",
    )


async def send_error_alert(alert: DiscordAlert):
    """Exemple: alerte d'erreur."""
    await alert.send(
        title="❌ Scraper Error",
        description="Bet365 scraper failed — possible rate limit",
        alert_type=AlertType.ERROR,
        fields=[
            AlertField(name="Error", value="TimeoutError after 30s", inline=False),
            AlertField(name="Retry", value="Will retry in 5 min"),
        ],
    )


async def main():
    # Charger le webhook depuis .env en production
    webhook_url = "https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE"
    alert = DiscordAlert(webhook_url)

    await send_edge_alert(alert)
    await send_error_alert(alert)


if __name__ == "__main__":
    asyncio.run(main())
