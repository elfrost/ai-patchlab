"""
Playwright Scraper Pattern — Référence pour tous les scrapers.
Utiliser ce pattern pour TOUT scraping avec Playwright dans le projet.
"""

import asyncio
import random
from typing import Any

from loguru import logger
from playwright.async_api import async_playwright, Browser, Page


class ScraperConfig:
    """Configuration du scraper."""

    # Rate limiting
    MIN_DELAY: float = 3.0  # secondes minimum entre requêtes
    MAX_DELAY: float = 7.0  # secondes maximum entre requêtes
    PAGE_TIMEOUT: int = 30_000  # ms timeout pour les pages

    # Retry
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: float = 2.0  # multiplicateur de backoff

    # Browser
    HEADLESS: bool = True
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


class BaseScraper:
    """Base scraper avec gestion du browser, rate limiting, et retry."""

    def __init__(self, config: ScraperConfig | None = None):
        self.config = config or ScraperConfig()
        self._browser: Browser | None = None
        self._playwright = None

    async def start(self) -> None:
        """Lance le browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.HEADLESS,
        )
        logger.info("Browser started")

    async def stop(self) -> None:
        """Ferme le browser proprement."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser stopped")

    async def _new_page(self) -> Page:
        """Crée une nouvelle page avec les settings de base."""
        assert self._browser, "Browser not started. Call start() first."
        context = await self._browser.new_context(
            user_agent=self.config.USER_AGENT,
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        page.set_default_timeout(self.config.PAGE_TIMEOUT)
        return page

    async def _rate_limit(self) -> None:
        """Attend un délai aléatoire entre les requêtes."""
        delay = random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY)
        logger.debug(f"Rate limit: waiting {delay:.1f}s")
        await asyncio.sleep(delay)

    async def _retry(self, func, *args, **kwargs) -> Any:
        """Exécute une fonction avec retry et backoff exponentiel."""
        last_error = None
        for attempt in range(self.config.MAX_RETRIES):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                wait = self.config.RETRY_BACKOFF ** attempt
                logger.warning(
                    f"Attempt {attempt + 1}/{self.config.MAX_RETRIES} failed: {e}. "
                    f"Retrying in {wait:.1f}s..."
                )
                await asyncio.sleep(wait)

        logger.error(f"All {self.config.MAX_RETRIES} attempts failed")
        raise last_error


# --- Exemple concret: Scraper de cotes ---

class OddsScraper(BaseScraper):
    """Exemple de scraper qui extrait des cotes d'un site de paris."""

    async def scrape_odds(self, url: str) -> list[dict[str, Any]]:
        """Scrape les cotes d'une page."""
        return await self._retry(self._do_scrape, url)

    async def _do_scrape(self, url: str) -> list[dict[str, Any]]:
        """Logique de scraping (appelée par _retry)."""
        page = await self._new_page()
        odds_data = []

        try:
            await page.goto(url, wait_until="networkidle")
            await self._rate_limit()

            # Attendre que les éléments soient chargés
            await page.wait_for_selector(".odds-container", timeout=10_000)

            # Extraire les données
            items = await page.query_selector_all(".odds-item")
            for item in items:
                market = await item.query_selector(".market-name")
                line = await item.query_selector(".line-value")
                price = await item.query_selector(".price-value")

                if market and line and price:
                    odds_data.append({
                        "market": await market.inner_text(),
                        "line": await line.inner_text(),
                        "price": await price.inner_text(),
                    })

            logger.info(f"Scraped {len(odds_data)} odds from {url}")
            return odds_data

        except Exception as e:
            logger.error(f"Scrape failed for {url}: {e}")
            raise
        finally:
            await page.close()


# --- Usage ---
async def main():
    scraper = OddsScraper()
    await scraper.start()

    try:
        odds = await scraper.scrape_odds("https://example.com/odds")
        for odd in odds:
            logger.info(f"Market: {odd['market']}, Line: {odd['line']}, Price: {odd['price']}")
    finally:
        await scraper.stop()


if __name__ == "__main__":
    asyncio.run(main())
