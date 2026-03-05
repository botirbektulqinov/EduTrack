"""
EduTrack — Redis Connection
Used for caching, session blacklist, and Celery broker.
"""

import redis.asyncio as aioredis

from app.core.config import settings

redis_client = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency — returns the async Redis client."""
    return redis_client
