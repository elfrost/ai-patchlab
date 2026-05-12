"""
MySQL Async Pattern — Référence pour tous les accès base de données.
Utiliser ce pattern pour TOUTE interaction avec MySQL dans le projet.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import aiomysql
from loguru import logger
from pydantic_settings import BaseSettings


class DBConfig(BaseSettings):
    """Configuration DB chargée depuis .env"""

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = ""

    class Config:
        env_file = ".env"


class Database:
    """Async MySQL connection pool manager."""

    def __init__(self, config: DBConfig | None = None):
        self.config = config or DBConfig()
        self._pool: aiomysql.Pool | None = None

    async def connect(self) -> None:
        """Initialize connection pool."""
        self._pool = await aiomysql.create_pool(
            host=self.config.mysql_host,
            port=self.config.mysql_port,
            user=self.config.mysql_user,
            password=self.config.mysql_password,
            db=self.config.mysql_database,
            autocommit=True,
            minsize=1,
            maxsize=5,
        )
        logger.info(f"Connected to MySQL: {self.config.mysql_database}")

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            logger.info("MySQL connection pool closed")

    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions with auto-rollback on error."""
        assert self._pool, "Database not connected. Call connect() first."
        async with self._pool.acquire() as conn:
            await conn.begin()
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    async def execute(self, query: str, params: tuple = ()) -> int:
        """Execute a write query. Returns affected row count."""
        assert self._pool, "Database not connected."
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return cur.rowcount

    async def fetch_one(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        """Fetch a single row as dict."""
        assert self._pool, "Database not connected."
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params)
                return await cur.fetchone()

    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Fetch all rows as list of dicts."""
        assert self._pool, "Database not connected."
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params)
                return await cur.fetchall()


# --- Usage Example ---
async def main():
    db = Database()
    await db.connect()

    try:
        # Insert — ALWAYS use parameterized queries
        await db.execute(
            "INSERT INTO odds (book, market, line, price) VALUES (%s, %s, %s, %s)",
            ("bet365", "NFL_spread", -3.5, -110),
        )

        # Select
        row = await db.fetch_one(
            "SELECT * FROM odds WHERE book = %s AND market = %s",
            ("bet365", "NFL_spread"),
        )
        logger.info(f"Found: {row}")

        # Transaction
        async with db.transaction() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE odds SET price = %s WHERE id = %s", (-105, 1))
                await cur.execute("INSERT INTO logs (action) VALUES (%s)", ("price_update",))

    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
