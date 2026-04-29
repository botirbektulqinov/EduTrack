"""
EduTrack - Redis connection helpers.
Used for caching, token blacklisting, and worker integrations.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    aioredis = None


class NoOpRedisClient:
    """Fallback client that keeps the app importable when Redis is unavailable."""

    async def get(self, key: str) -> None:
        return None

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        return True

    async def delete(self, key: str) -> int:
        return 0

    async def incr(self, key: str) -> int:
        return 1

    async def expire(self, key: str, ttl: int) -> bool:
        return True

    async def ping(self) -> bool:
        return False

    async def close(self) -> None:
        return None


if aioredis is not None:
    redis_client: Any = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
else:
    logger.warning(
        "redis package is not installed; falling back to a no-op Redis client. "
        "Token blacklist persistence is disabled until redis is installed."
    )
    redis_client = NoOpRedisClient()


async def get_redis() -> Any:
    """FastAPI dependency returning the configured async Redis-compatible client."""
    return redis_client
