"""Async Redis client — module-level singleton, initialised in app lifespan."""
from __future__ import annotations

import redis.asyncio as aioredis
from app.config import settings


_redis_client: aioredis.Redis | None = None


async def init_redis() -> aioredis.Redis:
    """Create the Redis connection pool. Called once at startup."""
    global _redis_client
    _redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
    )
    # Verify connectivity
    await _redis_client.ping()
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


def get_redis() -> aioredis.Redis | None:
    """Return the singleton client (None if Redis is unavailable — predictions still work uncached)."""
    return _redis_client
