from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from cachetools import TTLCache

logger = logging.getLogger(__name__)

PREFIX = "prod_control:"


class CacheBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> str | None: ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int: ...

    @abstractmethod
    async def clear(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


class InMemoryCache(CacheBackend):
    def __init__(self, default_ttl: int = 300):
        self._store: TTLCache = TTLCache(maxsize=4096, ttl=default_ttl)
        self._default_ttl = default_ttl

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def delete_pattern(self, pattern: str) -> int:
        import fnmatch
        keys_to_delete = [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]
        for key in keys_to_delete:
            self._store.pop(key, None)
        return len(keys_to_delete)

    async def clear(self) -> None:
        self._store.clear()

    async def close(self) -> None:
        self._store.clear()


class RedisCache(CacheBackend):
    def __init__(self, redis_url: str, default_ttl: int = 300):
        import redis.asyncio as aioredis

        pool = aioredis.ConnectionPool.from_url(redis_url, decode_responses=True)
        self._redis = aioredis.Redis(connection_pool=pool)
        self._default_ttl = default_ttl

    async def get(self, key: str) -> str | None:
        try:
            return await self._redis.get(PREFIX + key)
        except Exception:
            logger.exception("RedisCache.get failed for key=%s", key)
            return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        try:
            await self._redis.set(PREFIX + key, value, ex=ttl or self._default_ttl)
        except Exception:
            logger.exception("RedisCache.set failed for key=%s", key)

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(PREFIX + key)
        except Exception:
            logger.exception("RedisCache.delete failed for key=%s", key)

    async def delete_pattern(self, pattern: str) -> int:
        try:
            keys = []
            async for key in self._redis.scan_iter(match=PREFIX + pattern):
                keys.append(key)
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.debug("Cache invalidated by pattern: %s, count=%d", pattern, deleted)
                return deleted
            return 0
        except Exception:
            logger.exception("RedisCache.delete_pattern failed for pattern=%s", pattern)
            return 0

    async def clear(self) -> None:
        """Очистить все ключи с нашим префиксом"""
        try:
            keys = await self._redis.keys(PREFIX + "*")
            if keys:
                await self._redis.delete(*keys)
        except Exception:
            logger.exception("RedisCache.clear failed")

    async def close(self) -> None:
        try:
            await self._redis.aclose()
        except Exception:
            logger.exception("RedisCache.close failed")


class CacheService:
    def __init__(self, backend: CacheBackend):
        self._backend = backend

    async def get(self, key: str) -> Any | None:
        raw = await self._backend.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        raw = json.dumps(value, default=str)
        await self._backend.set(key, raw, ttl)

    async def delete(self, key: str) -> None:
        await self._backend.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        return await self._backend.delete_pattern(pattern)

    async def get_or_set(self, key: str, factory, ttl: int | None = None) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        await self.set(key, value, ttl)
        return value

    async def clear(self) -> None:
        await self._backend.clear()

    async def close(self) -> None:
        await self._backend.close()


_cache_service: CacheService | None = None


async def init_cache() -> CacheService:
    global _cache_service
    from src.core.config import get_settings

    settings = get_settings()

    if settings.cache_backend == "redis":
        backend = RedisCache(settings.redis_url, default_ttl=settings.cache_ttl)
    else:
        backend = InMemoryCache(default_ttl=settings.cache_ttl)

    _cache_service = CacheService(backend)
    logger.info("Cache initialized: backend=%s", settings.cache_backend)
    return _cache_service


def get_cache_service() -> CacheService:
    if _cache_service is None:
        raise RuntimeError("Cache not initialized. Call init_cache() first.")
    return _cache_service
