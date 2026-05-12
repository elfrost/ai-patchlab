"""
Scheduler Pattern — Référence pour les tâches planifiées.
Utiliser ce pattern pour TOUTE logique de scheduling dans le projet.

Deux approches:
1. Asyncio loop interne (pour des intervalles simples)
2. Déclenchement externe (cron / n8n qui appelle le script)
"""

import asyncio
import signal
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from loguru import logger


# =============================================================================
# Approche 1: Scheduler asyncio interne
# Pour des tâches qui tournent en boucle avec un intervalle
# =============================================================================


class AsyncScheduler:
    """Scheduler async léger pour des tâches périodiques."""

    def __init__(self):
        self._tasks: list[dict[str, Any]] = []
        self._running: bool = False

    def register(
        self,
        name: str,
        func: Callable[[], Coroutine],
        interval_seconds: int,
        run_on_start: bool = True,
    ) -> None:
        """Enregistre une tâche périodique."""
        self._tasks.append({
            "name": name,
            "func": func,
            "interval": interval_seconds,
            "run_on_start": run_on_start,
        })
        logger.info(f"Registered task: {name} (every {interval_seconds}s)")

    async def start(self) -> None:
        """Démarre toutes les tâches enregistrées."""
        self._running = True
        logger.info(f"Scheduler starting with {len(self._tasks)} tasks")

        workers = [self._run_task(task) for task in self._tasks]
        await asyncio.gather(*workers)

    async def stop(self) -> None:
        """Arrête proprement le scheduler."""
        self._running = False
        logger.info("Scheduler stopping...")

    async def _run_task(self, task: dict[str, Any]) -> None:
        """Boucle d'exécution pour une tâche."""
        name = task["name"]
        func = task["func"]
        interval = task["interval"]

        # Premier run immédiat si demandé
        if task["run_on_start"]:
            await self._execute(name, func)

        while self._running:
            await asyncio.sleep(interval)
            if not self._running:
                break
            await self._execute(name, func)

    async def _execute(self, name: str, func: Callable) -> None:
        """Exécute une tâche avec logging et error handling."""
        start = datetime.now(timezone.utc)
        logger.info(f"[{name}] Starting...")

        try:
            await func()
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            logger.info(f"[{name}] Completed in {elapsed:.1f}s")
        except Exception as e:
            logger.error(f"[{name}] Failed: {e}")
            # Ne pas crash le scheduler — les autres tâches continuent


# =============================================================================
# Approche 2: Script one-shot (pour cron / n8n)
# Le script fait son job puis exit. L'ordonnancement est externe.
# =============================================================================


async def run_once(job_name: str, func: Callable[[], Coroutine]) -> bool:
    """
    Exécute une tâche une seule fois (pour déclenchement cron/n8n).

    Returns:
        True si succès, False si erreur
    """
    start = datetime.now(timezone.utc)
    logger.info(f"[{job_name}] Starting one-shot execution...")

    try:
        await func()
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.info(f"[{job_name}] Completed in {elapsed:.1f}s")
        return True
    except Exception as e:
        logger.error(f"[{job_name}] Failed: {e}")
        return False


# =============================================================================
# Usage Examples
# =============================================================================


async def scrape_odds():
    """Exemple: tâche de scraping périodique."""
    logger.info("Scraping odds from Bet365...")
    await asyncio.sleep(2)  # Simule le travail
    logger.info("Scraped 42 odds")


async def check_edges():
    """Exemple: tâche de calcul d'edge."""
    logger.info("Checking for +EV edges...")
    await asyncio.sleep(1)  # Simule le travail
    logger.info("Found 3 edges above threshold")


async def cleanup_old_data():
    """Exemple: nettoyage périodique."""
    logger.info("Cleaning up data older than 24h...")
    await asyncio.sleep(0.5)
    logger.info("Cleaned 150 old records")


# --- Exemple 1: Scheduler interne ---


async def main_scheduler():
    """Run en mode scheduler (boucle continue)."""
    scheduler = AsyncScheduler()

    scheduler.register("scrape_odds", scrape_odds, interval_seconds=300)  # 5 min
    scheduler.register("check_edges", check_edges, interval_seconds=60)  # 1 min
    scheduler.register("cleanup", cleanup_old_data, interval_seconds=3600, run_on_start=False)  # 1h

    # Graceful shutdown sur SIGINT/SIGTERM
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(scheduler.stop()))

    await scheduler.start()


# --- Exemple 2: One-shot pour cron/n8n ---


async def main_oneshot():
    """Run en mode one-shot (cron/n8n trigger)."""
    success = await run_once("scrape_and_check", scrape_odds)
    if success:
        await run_once("check_edges", check_edges)


if __name__ == "__main__":
    import sys

    if "--once" in sys.argv:
        asyncio.run(main_oneshot())
    else:
        asyncio.run(main_scheduler())
