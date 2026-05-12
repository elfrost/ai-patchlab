"""
ai-patchlab â€” Point d'entrÃ©e principal.
Usage: python -m src.main
"""

import asyncio
import sys

from loguru import logger

# --- Logging Setup ---
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | <cyan>{name}</cyan> â€” <level>{message}</level>",
    level="DEBUG",
)
logger.add(
    "logs/{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
)


async def main() -> None:
    """Point d'entrÃ©e async principal."""
    logger.info("Starting ai-patchlab...")

    # TODO: Initialiser les services ici
    # db = Database()
    # await db.connect()

    try:
        # TODO: Logique principale ici
        logger.info("Running main logic...")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        # TODO: Cleanup ici
        # await db.disconnect()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
