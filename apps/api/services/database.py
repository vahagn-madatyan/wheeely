"""Async database connection pool for Supabase-managed Postgres via asyncpg."""

from __future__ import annotations

import os
from typing import AsyncGenerator, Optional

import asyncpg

_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """Return the cached asyncpg connection pool, creating it on first call.

    Reads ``DATABASE_URL`` from the environment.  Raises ``ValueError`` if the
    variable is not set.
    """
    global _pool
    if _pool is None:
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise ValueError("DATABASE_URL environment variable is not set")
        _pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
    return _pool


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency that yields a connection from the pool.

    Usage::

        @router.get("/example")
        async def example(conn: asyncpg.Connection = Depends(get_db)):
            rows = await conn.fetch("SELECT 1")
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        yield conn


async def close_db_pool() -> None:
    """Close the cached connection pool.  Safe to call if no pool exists."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
