"""
API Client Pattern — Référence pour consommer des APIs REST externes.
Utiliser ce pattern pour TOUT appel API externe dans le projet.

Inclut: authentification, rate limiting, retry, pagination.
"""

import asyncio
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel


class APIConfig(BaseModel):
    """Configuration du client API."""

    base_url: str
    api_key: str = ""
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 2.0
    rate_limit_seconds: float = 1.0


class BaseAPIClient:
    """Client API async avec retry, rate limiting, et auth."""

    def __init__(self, config: APIConfig):
        self.config = config
        self._last_request: float = 0
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Context manager: ouvre le client HTTP."""
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            headers=self._default_headers(),
        )
        return self

    async def __aexit__(self, *args):
        """Context manager: ferme le client HTTP."""
        if self._client:
            await self._client.aclose()

    def _default_headers(self) -> dict[str, str]:
        """Headers par défaut. Override dans les sous-classes pour auth custom."""
        headers = {"Accept": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    async def _rate_limit(self) -> None:
        """Respecte le rate limit entre les requêtes."""
        now = asyncio.get_event_loop().time()
        wait = self.config.rate_limit_seconds - (now - self._last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request = asyncio.get_event_loop().time()

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Requête HTTP avec retry et rate limiting."""
        assert self._client, "Client not initialized. Use 'async with' context manager."

        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                await self._rate_limit()

                response = await self._client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )
                response.raise_for_status()

                logger.debug(f"{method} {path} -> {response.status_code}")
                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code

                # Ne pas retry les erreurs client (sauf 429 rate limit)
                if 400 <= status < 500 and status != 429:
                    logger.error(f"Client error {status}: {e.response.text}")
                    raise

                wait = self.config.retry_backoff ** attempt
                logger.warning(
                    f"Attempt {attempt + 1}/{self.config.max_retries} failed "
                    f"(HTTP {status}). Retrying in {wait:.1f}s..."
                )
                await asyncio.sleep(wait)

            except httpx.RequestError as e:
                last_error = e
                wait = self.config.retry_backoff ** attempt
                logger.warning(
                    f"Attempt {attempt + 1}/{self.config.max_retries} failed: {e}. "
                    f"Retrying in {wait:.1f}s..."
                )
                await asyncio.sleep(wait)

        logger.error(f"All {self.config.max_retries} attempts failed for {method} {path}")
        raise last_error

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET request."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST request."""
        return await self._request("POST", path, json=json)

    async def get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        page_key: str = "page",
        results_key: str = "data",
        max_pages: int = 100,
    ) -> list[dict[str, Any]]:
        """GET avec pagination automatique. Accumule tous les résultats."""
        all_results = []
        params = params or {}
        page = 1

        while page <= max_pages:
            params[page_key] = page
            data = await self.get(path, params=params)

            results = data.get(results_key, [])
            if not results:
                break

            all_results.extend(results)
            logger.debug(f"Page {page}: {len(results)} results (total: {len(all_results)})")
            page += 1

        return all_results


# --- Exemple concret: Client pour une API de cotes ---


class OddsAPIClient(BaseAPIClient):
    """Client pour une API de cotes sportives."""

    async def get_events(self, sport: str) -> list[dict[str, Any]]:
        """Récupère les événements pour un sport."""
        data = await self.get(f"/v1/events", params={"sport": sport})
        return data.get("events", [])

    async def get_odds(self, event_id: str) -> dict[str, Any]:
        """Récupère les cotes pour un événement."""
        return await self.get(f"/v1/events/{event_id}/odds")


# --- Usage ---


async def main():
    config = APIConfig(
        base_url="https://api.example.com",
        api_key="your-api-key-here",
        rate_limit_seconds=0.5,
    )

    async with OddsAPIClient(config) as client:
        try:
            events = await client.get_events("NFL")
            for event in events:
                logger.info(f"Event: {event}")

                odds = await client.get_odds(event["id"])
                logger.info(f"Odds: {odds}")

        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} — {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Network error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
