"""
Small fixed-window rate limiter for high-risk endpoints.

Uses Redis when available and falls back to process-local memory for development.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.redis import redis_client


@dataclass
class RateLimit:
    name: str
    limit: int
    window_seconds: int


class FixedWindowRateLimiter:
    def __init__(self) -> None:
        self._memory_counts: dict[str, tuple[int, float]] = {}

    async def check(self, *, key: str, limit: int, window_seconds: int) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        if limit <= 0 or window_seconds <= 0:
            return

        now = time.time()
        window = int(now // window_seconds)
        bucket_key = f"rate-limit:{key}:{window}"
        count = await self._increment(bucket_key, window_seconds, now)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please try again later.",
                },
            )

    async def _increment(self, key: str, window_seconds: int, now: float) -> int:
        try:
            count = int(await redis_client.incr(key))
            if count == 1:
                await redis_client.expire(key, window_seconds)
            return count
        except Exception:
            return self._increment_memory(key, window_seconds, now)

    def _increment_memory(self, key: str, window_seconds: int, now: float) -> int:
        count, expires_at = self._memory_counts.get(key, (0, now + window_seconds))
        if now >= expires_at:
            count = 0
            expires_at = now + window_seconds
        count += 1
        self._memory_counts[key] = (count, expires_at)
        self._cleanup_memory(now)
        return count

    def _cleanup_memory(self, now: float) -> None:
        stale_keys = [
            key
            for key, (_, expires_at) in self._memory_counts.items()
            if expires_at < now
        ]
        for key in stale_keys:
            self._memory_counts.pop(key, None)

    def reset_memory(self) -> None:
        self._memory_counts.clear()


rate_limiter = FixedWindowRateLimiter()


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_ip_rate_limit(request: Request, rate: RateLimit) -> None:
    await rate_limiter.check(
        key=f"{rate.name}:ip:{client_ip(request)}",
        limit=rate.limit,
        window_seconds=rate.window_seconds,
    )


async def check_user_rate_limit(user_id: object, rate: RateLimit) -> None:
    await rate_limiter.check(
        key=f"{rate.name}:user:{user_id}",
        limit=rate.limit,
        window_seconds=rate.window_seconds,
    )
