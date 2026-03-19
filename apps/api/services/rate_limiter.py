"""Redis-based sliding window rate limiter for screening runs.

Enforces 3 screening runs per user per 24-hour window (D058).
When Redis is unavailable, degrades gracefully — all requests are allowed.
"""

import logging
import time

from fastapi import HTTPException, Request

logger = logging.getLogger("rate_limiter")

# Free-tier limits
MAX_REQUESTS = 3
WINDOW_SECONDS = 86400  # 24 hours


class RateLimiter:
    """Sliding window rate limiter backed by Redis sorted sets.

    Each user's requests are tracked in a sorted set keyed by
    ``rate_limit:{user_id}``.  Scores are Unix timestamps.
    On every check we prune entries older than the window, count
    remaining entries, and either allow (ZADD) or reject (429).

    When ``redis`` is None (no REDIS_URL configured), all checks
    pass without enforcement so the app still works in dev.
    """

    def __init__(self, redis=None):
        self.redis = redis

    async def check_rate_limit(self, user_id: str) -> int:
        """Check and record a rate-limited action for *user_id*.

        Returns the number of remaining requests in the window.
        Raises ``HTTPException(429)`` when the limit is exceeded.
        """
        if self.redis is None:
            logger.warning(
                "Redis unavailable — rate limiting disabled (user_id=%s)", user_id
            )
            return MAX_REQUESTS

        now = time.time()
        window_start = now - WINDOW_SECONDS
        key = f"rate_limit:{user_id}"

        # Atomic pipeline: prune expired → count → conditionally add
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        results = await pipe.execute()
        current_count = results[1]

        if current_count >= MAX_REQUESTS:
            # Find when the oldest entry expires so caller knows when to retry
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            retry_after = int(oldest[0][1] + WINDOW_SECONDS - now) if oldest else WINDOW_SECONDS

            logger.warning(
                "Rate limit exceeded for user_id=%s (count=%d, retry_after=%ds)",
                user_id, current_count, retry_after,
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Rate limit exceeded. Free tier allows 3 screening runs per 24 hours.",
                    "remaining": 0,
                    "retry_after": retry_after,
                },
            )

        # Record this request
        await self.redis.zadd(key, {str(now): now})
        # Set TTL so keys don't linger forever
        await self.redis.expire(key, WINDOW_SECONDS)

        remaining = MAX_REQUESTS - current_count - 1
        logger.info(
            "Rate limit check passed for user_id=%s (remaining=%d)", user_id, remaining
        )
        return remaining


def get_rate_limiter(request: Request) -> RateLimiter:
    """FastAPI dependency — retrieves the RateLimiter from app state."""
    return request.app.state.rate_limiter
