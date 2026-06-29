"""
Redis cache client and helper utilities.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as aioredis

from backend.config import settings

# Lazy singleton
_redis: Optional[Any] = None


class MockRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key: str) -> Optional[str]:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self.store


async def get_redis() -> Any:
    global _redis
    if _redis is None:
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            # Try a quick ping to see if server is up
            await client.ping()
            _redis = client
        except Exception:
            _redis = MockRedis()
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    """Get a JSON-serialised value from Redis. Returns None on miss."""
    r = await get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    """Serialise value to JSON and store in Redis with TTL (seconds)."""
    r = await get_redis()
    await r.set(key, json.dumps(value, default=str), ex=ttl)


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def cache_exists(key: str) -> bool:
    r = await get_redis()
    return bool(await r.exists(key))


def feature_key(player_id: str, match_type: str, window: int) -> str:
    return f"features:{player_id}:{match_type}:{window}"


def prediction_key(match_id: str, mode: str) -> str:
    return f"prediction:{match_id}:{mode}"


def explanation_key(match_id: str, player_id: str) -> str:
    return f"explain:{match_id}:{player_id}"


def revoked_token_key(jti: str) -> str:
    return f"revoked:jti:{jti}"
