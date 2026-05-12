"""
Service Pattern — Référence pour la business logic.
Utiliser ce pattern pour TOUTE logique métier dans le projet.

Un service orchestre : données (DB/API) → calcul → action (alerte/stockage).
"""

import asyncio
from dataclasses import dataclass
from typing import Any

from loguru import logger


# --- Domain Models ---


@dataclass
class OddsData:
    """Données de cotes extraites d'une source."""

    book: str
    market: str
    line: float
    price: int  # American odds format: +150, -110
    event_name: str = ""


@dataclass
class EdgeResult:
    """Résultat d'un calcul d'edge."""

    book_odds: OddsData
    fair_odds: OddsData
    edge_pct: float
    is_positive: bool
    recommended_bet: float = 0.0


# --- Service Class ---


class EdgeCalculatorService:
    """
    Service de calcul d'edge entre deux sources de cotes.

    Responsabilités:
    - Récupérer les cotes de deux sources
    - Calculer les edges
    - Filtrer les opportunités positives
    - Déclencher les alertes

    Ne fait PAS:
    - D'accès direct à la DB (utilise un repository)
    - De scraping (reçoit les données)
    - D'envoi direct de webhooks (utilise un alerter)
    """

    def __init__(
        self,
        db: Any,
        alerter: Any,
        min_edge_pct: float = 3.0,
        bankroll: float = 200.0,
        kelly_fraction: float = 0.25,
    ):
        self.db = db
        self.alerter = alerter
        self.min_edge_pct = min_edge_pct
        self.bankroll = bankroll
        self.kelly_fraction = kelly_fraction

    async def process_odds(
        self,
        book_odds: list[OddsData],
        sharp_odds: list[OddsData],
    ) -> list[EdgeResult]:
        """
        Compare les cotes de deux sources et retourne les edges positifs.

        Args:
            book_odds: Cotes du book (ex: Bet365)
            sharp_odds: Cotes sharp (ex: Pinnacle)

        Returns:
            Liste des edges positifs trouvés
        """
        edges: list[EdgeResult] = []

        # Matcher les marchés par (market, line)
        sharp_lookup = {(o.market, o.line): o for o in sharp_odds}

        for book in book_odds:
            key = (book.market, book.line)
            sharp = sharp_lookup.get(key)

            if not sharp:
                continue

            edge = self._calculate_edge(book.price, sharp.price)

            if edge > 0:
                bet_size = self._kelly_bet(edge, book.price)
                result = EdgeResult(
                    book_odds=book,
                    fair_odds=sharp,
                    edge_pct=edge,
                    is_positive=edge >= self.min_edge_pct,
                    recommended_bet=bet_size,
                )
                edges.append(result)

                if result.is_positive:
                    logger.info(
                        f"+EV Found: {book.market} {book.line} @ {book.price} "
                        f"(edge: {edge:.1f}%, bet: ${bet_size:.2f})"
                    )

        # Persister et alerter
        await self._save_edges(edges)
        await self._alert_positive_edges(edges)

        return edges

    def _calculate_edge(self, book_price: int, sharp_price: int) -> float:
        """Calcule l'edge entre le book price et le sharp price."""
        book_prob = self._american_to_prob(book_price)
        sharp_prob = self._american_to_prob(sharp_price)

        if sharp_prob <= 0:
            return 0.0

        # Edge = (fair_prob / book_implied_prob - 1) * 100
        # Inversé: le book donne plus que la fair value
        edge = ((1 / book_prob) / (1 / sharp_prob) - 1) * 100
        return round(edge, 2)

    @staticmethod
    def _american_to_prob(odds: int) -> float:
        """Convertit les cotes américaines en probabilité implicite."""
        if odds > 0:
            return 100 / (odds + 100)
        elif odds < 0:
            return abs(odds) / (abs(odds) + 100)
        return 0.0

    def _kelly_bet(self, edge_pct: float, odds: int) -> float:
        """Calcule la mise Kelly fractionnelle."""
        prob = self._american_to_prob(odds)
        if prob <= 0 or prob >= 1:
            return 0.0

        decimal_odds = self._american_to_decimal(odds)
        b = decimal_odds - 1  # profit net si gagné
        q = 1 - prob

        kelly_full = (b * prob - q) / b
        if kelly_full <= 0:
            return 0.0

        bet = self.bankroll * kelly_full * self.kelly_fraction
        return round(min(bet, self.bankroll * 0.05), 2)  # Cap à 5% du bankroll

    @staticmethod
    def _american_to_decimal(odds: int) -> float:
        """Convertit les cotes américaines en décimales."""
        if odds > 0:
            return (odds / 100) + 1
        elif odds < 0:
            return (100 / abs(odds)) + 1
        return 1.0

    async def _save_edges(self, edges: list[EdgeResult]) -> None:
        """Persiste les edges trouvés en DB."""
        for edge in edges:
            try:
                await self.db.execute(
                    "INSERT INTO edges (book, market, line, book_price, fair_price, edge_pct, bet_size) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        edge.book_odds.book,
                        edge.book_odds.market,
                        edge.book_odds.line,
                        edge.book_odds.price,
                        edge.fair_odds.price,
                        edge.edge_pct,
                        edge.recommended_bet,
                    ),
                )
            except Exception as e:
                logger.error(f"Failed to save edge: {e}")

    async def _alert_positive_edges(self, edges: list[EdgeResult]) -> None:
        """Envoie des alertes Discord pour les edges positifs."""
        positive = [e for e in edges if e.is_positive]

        for edge in positive:
            try:
                await self.alerter.send(
                    title=f"+EV: {edge.book_odds.market} {edge.book_odds.line}",
                    description=(
                        f"Book: {edge.book_odds.book} @ {edge.book_odds.price}\n"
                        f"Edge: {edge.edge_pct:.1f}%\n"
                        f"Bet: ${edge.recommended_bet:.2f}"
                    ),
                )
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")


# --- Usage ---


async def main():
    """Exemple d'utilisation du service."""
    from unittest.mock import AsyncMock

    # Mock des dépendances (en production, utiliser les vraies classes)
    mock_db = AsyncMock()
    mock_alerter = AsyncMock()

    service = EdgeCalculatorService(
        db=mock_db,
        alerter=mock_alerter,
        min_edge_pct=3.0,
        bankroll=200.0,
    )

    # Données simulées
    book_odds = [
        OddsData(book="bet365", market="NFL_spread", line=-3.5, price=155),
        OddsData(book="bet365", market="NFL_spread", line=-7.5, price=250),
    ]
    sharp_odds = [
        OddsData(book="pinnacle", market="NFL_spread", line=-3.5, price=130),
        OddsData(book="pinnacle", market="NFL_spread", line=-7.5, price=200),
    ]

    edges = await service.process_odds(book_odds, sharp_odds)
    for edge in edges:
        logger.info(
            f"Edge: {edge.edge_pct:.1f}% | "
            f"Positive: {edge.is_positive} | "
            f"Bet: ${edge.recommended_bet:.2f}"
        )


if __name__ == "__main__":
    asyncio.run(main())
