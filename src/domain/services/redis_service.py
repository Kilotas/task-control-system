from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

from src.domain.services.cache_service import get_cache_service, CacheService

logger = logging.getLogger(__name__)


def cached(ttl: int, key_prefix: str):
    """
    Декоратор для кэширования результатов функции.

    Args:
        ttl: Время жизни кэша в секундах
        key_prefix: Префикс ключа кэша

    Usage:
        @cached(ttl=300, key_prefix="dashboard_stats")
        async def get_dashboard_statistics():
            ...

        @cached(ttl=60, key_prefix="batch_detail")
        async def get_batch_detail(batch_id: int):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                cache = get_cache_service()
            except RuntimeError:
                return await func(*args, **kwargs)

            key_parts = [key_prefix]
            for arg in args:
                if not hasattr(arg, '__class__') or arg.__class__.__name__ not in ('UnitOfWork', 'SqlAlchemyUnitOfWork'):
                    key_parts.append(str(arg))
            for k, v in sorted(kwargs.items()):
                if v is not None and k not in ('self', 'uow'):
                    key_parts.append(f"{k}={v}")
            cache_key = ":".join(key_parts)

            cached_data = await cache.get(cache_key)
            if cached_data is not None:
                logger.debug("Cache HIT: %s", cache_key)
                return cached_data


            logger.debug("Cache MISS: %s", cache_key)
            result = await func(*args, **kwargs)

            if isinstance(result, dict) and "cached_at" not in result:
                result["cached_at"] = datetime.now(timezone.utc).isoformat()

            await cache.set(cache_key, result, ttl=ttl)

            return result
        return wrapper
    return decorator


class CacheInvalidator:
    """Хелпер для инвалидации кэша."""

    def __init__(self, cache_service: CacheService | None = None):
        self._cache = cache_service

    def _get_cache(self) -> CacheService:
        if self._cache:
            return self._cache
        try:
            return get_cache_service()
        except RuntimeError:
            return None

    async def on_batch_created(self) -> None:
        """Инвалидация при создании партии."""
        cache = self._get_cache()
        if not cache:
            return
        await cache.delete("dashboard_stats")
        await cache.delete_pattern("batches_list:*")

    async def on_batch_updated(self, batch_id: int) -> None:
        """Инвалидация при обновлении партии."""
        cache = self._get_cache()
        if not cache:
            return
        await cache.delete(f"batch_detail:{batch_id}")
        await cache.delete(f"batch_statistics:{batch_id}")
        await cache.delete("dashboard_stats")
        await cache.delete_pattern("batches_list:*")

    async def on_product_aggregated(self, batch_id: int) -> None:
        """Инвалидация при агрегации продукта."""
        cache = self._get_cache()
        if not cache:
            return
        await cache.delete(f"batch_detail:{batch_id}")
        await cache.delete(f"batch_statistics:{batch_id}")
        await cache.delete("dashboard_stats")

    async def invalidate_all(self) -> None:
        """Полная инвалидация кэша."""
        cache = self._get_cache()
        if not cache:
            return
        await cache.delete_pattern("dashboard_stats*")
        await cache.delete_pattern("batches_list:*")
        await cache.delete_pattern("batch_detail:*")
        await cache.delete_pattern("batch_statistics:*")
