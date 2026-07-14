import json
import hashlib
import logging
from typing import Optional, Any
from datetime import timedelta

import redis.asyncio as aioredis

from backend.config import settings

logger = logging.getLogger("gigacorp.cache.redis")


class RedisCache:
    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url or settings.redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def initialize(self):
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=settings.redis_socket_timeout,
            )
            logger.info("Redis cache connected at %s", self._redis_url)

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis cache closed")

    @property
    def client(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("Redis cache not initialized")
        return self._redis

    def _make_key(self, prefix: str, *parts: str) -> str:
        raw = "|".join(str(p) for p in parts)
        return f"{prefix}:{hashlib.sha256(raw.encode()).hexdigest()}"

    async def get(self, key: str) -> Optional[Any]:
        try:
            val = await self.client.get(key)
            if val is not None:
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return val
            return None
        except Exception as e:
            logger.warning("Redis get failed for key %s: %s", key, e)
            return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        try:
            serialized = json.dumps(value, default=str)
            ttl = ttl_seconds or settings.cache_default_ttl_seconds
            await self.client.setex(key, timedelta(seconds=ttl), serialized)
        except Exception as e:
            logger.warning("Redis set failed for key %s: %s", key, e)

    async def delete(self, key: str) -> None:
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.warning("Redis delete failed for key %s: %s", key, e)

    async def delete_pattern(self, pattern: str) -> None:
        try:
            cursor = 0
            while True:
                cursor, keys = await self.client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await self.client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning("Redis delete_pattern failed for %s: %s", pattern, e)

    async def clear_all(self) -> None:
        try:
            await self.client.flushdb()
            logger.info("Redis cache cleared")
        except Exception as e:
            logger.warning("Redis clear_all failed: %s", e)

    async def exists(self, key: str) -> bool:
        try:
            return await self.client.exists(key) > 0
        except Exception:
            return False

    async def increment(self, key: str, amount: int = 1, ttl_seconds: Optional[int] = None) -> int:
        try:
            val = await self.client.incrby(key, amount)
            if ttl_seconds:
                await self.client.expire(key, ttl_seconds)
            return val
        except Exception as e:
            logger.warning("Redis increment failed for key %s: %s", key, e)
            return 0

    async def ttl(self, key: str) -> int:
        try:
            return await self.client.ttl(key)
        except Exception:
            return -2


_cache_instance: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
        await _cache_instance.initialize()
    return _cache_instance
