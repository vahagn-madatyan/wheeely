"""FastAPI application entry point.

Start with:
    cd /path/to/wheeely && PYTHONPATH=. uvicorn apps.api.main:app --reload
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.services.task_store import TaskStore, periodic_cleanup
from apps.api.services.rate_limiter import RateLimiter
from apps.api.routers import keys, screen, positions

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: start TTL cleanup task, init Redis, cancel on shutdown."""
    store = TaskStore()
    app.state.task_store = store

    # Redis for rate limiting (optional — degrades to no-op when unset)
    redis_url = os.environ.get("REDIS_URL")
    redis_client = None
    if redis_url:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        logger.info("Redis connected for rate limiting")
    else:
        logger.info("REDIS_URL not set — rate limiting disabled")

    app.state.redis_client = redis_client
    app.state.rate_limiter = RateLimiter(redis_client)

    cleanup_task = asyncio.create_task(periodic_cleanup(store, interval=300))

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    if redis_client is not None:
        await redis_client.aclose()
        logger.info("Redis connection closed")


app = FastAPI(
    title="Wheeely Screening API",
    description="HTTP wrapper around the options wheel screener engine",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for dev; S07 will tighten this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(screen.router)
app.include_router(positions.router)
app.include_router(keys.router)
