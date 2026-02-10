from __future__ import annotations

import logging
from datetime import datetime, timezone, date

from src.application.uow.protocol import UnitOfWorkProtocol
from src.domain.services.cache_service import get_cache_service
from src.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Сервис расширенной аналитики с кэшированием."""

    def __init__(self, uow: UnitOfWorkProtocol):
        self._uow = uow

    async def get_dashboard_statistics(self) -> dict:
        """
        Расширенная статистика дашборда (TTL: 5 минут).
        """
        cache = None
        cache_key = "dashboard_stats"

        try:
            cache = get_cache_service()
            cached_data = await cache.get(cache_key)
            if cached_data:
                logger.debug("Dashboard stats from cache")
                return cached_data
        except RuntimeError:
            pass

        async with self._uow as uow:
            stats = await uow.batches.count_statistics()
            today_stats = await uow.batches.count_today_statistics()
            shift_stats = await uow.batches.count_by_shift()
            top_wc = await uow.batches.get_top_work_centers(limit=5)

        result = {
            "summary": {
                "total_batches": stats["total_batches"],
                "active_batches": stats["open_batches"],
                "closed_batches": stats["closed_batches"],
                "total_products": stats["total_products"],
                "aggregated_products": stats["aggregated_products"],
                "aggregation_rate": stats["aggregation_rate"],
            },
            "today": today_stats,
            "by_shift": shift_stats,
            "top_work_centers": top_wc,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }

        if cache:
            await cache.set(cache_key, result, ttl=300)
            logger.debug("Dashboard stats cached")

        return result

    async def get_batch_statistics(self, batch_id: int) -> dict:
        """
        Расширенная статистика партии (TTL: 5 минут).
        """
        cache = None
        cache_key = f"batch_statistics:{batch_id}"

        try:
            cache = get_cache_service()
            cached_data = await cache.get(cache_key)
            if cached_data:
                return cached_data
        except RuntimeError:
            pass

        async with self._uow as uow:
            batch = await uow.batches.get_by_id_with_wc(batch_id)
            if not batch:
                raise NotFoundException("Batch", batch_id)

            total = await uow.products.count_by_batch(batch_id)
            aggregated = await uow.products.count_aggregated_by_batch(batch_id)

        remaining = total - aggregated
        rate = round(aggregated / total * 100, 2) if total > 0 else 0.0
        timeline = self._calculate_timeline(batch, total, aggregated)

        result = {
            "batch_info": {
                "id": batch.id,
                "batch_number": batch.batch_number,
                "batch_date": str(batch.batch_date),
                "is_closed": batch.is_closed,
                "work_center": batch.work_center.name if batch.work_center else None,
            },
            "production_stats": {
                "total_products": total,
                "aggregated": aggregated,
                "remaining": remaining,
                "aggregation_rate": rate,
            },
            "timeline": timeline,
            "team_performance": {
                "team": batch.team,
                "shift": batch.shift,
            },
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }

        if cache:
            await cache.set(cache_key, result, ttl=300)

        return result

    async def compare_batches(self, batch_ids: list[int]) -> dict:
        """
        Сравнение нескольких партий.
        """
        if not batch_ids:
            return {"comparison": [], "average": {}}

        if len(batch_ids) > 10:
            batch_ids = batch_ids[:10]

        comparison = []
        total_rate = 0.0
        total_pph = 0.0

        async with self._uow as uow:
            for batch_id in batch_ids:
                batch = await uow.batches.get_by_id_with_wc(batch_id)
                if not batch:
                    continue

                total = await uow.products.count_by_batch(batch_id)
                aggregated = await uow.products.count_aggregated_by_batch(batch_id)

                rate = round(aggregated / total * 100, 2) if total > 0 else 0.0
                duration_hours = self._get_duration_hours(batch)
                pph = round(aggregated / duration_hours, 2) if duration_hours > 0 else 0.0

                comparison.append({
                    "batch_id": batch.id,
                    "batch_number": batch.batch_number,
                    "batch_date": str(batch.batch_date),
                    "work_center": batch.work_center.name if batch.work_center else None,
                    "total_products": total,
                    "aggregated": aggregated,
                    "aggregation_rate": rate,
                    "duration_hours": duration_hours,
                    "products_per_hour": pph,
                })

                total_rate += rate
                total_pph += pph

        count = len(comparison)
        avg_rate = round(total_rate / count, 2) if count > 0 else 0.0
        avg_pph = round(total_pph / count, 2) if count > 0 else 0.0

        return {
            "comparison": comparison,
            "average": {
                "aggregation_rate": avg_rate,
                "products_per_hour": avg_pph,
            },
        }

    def _calculate_timeline(self, batch, total: int, aggregated: int) -> dict:
        """Расчёт timeline для партии."""
        if not batch.shift_start or not batch.shift_end:
            return {}

        shift_start = batch.shift_start
        shift_end = batch.shift_end

        if isinstance(shift_start, str):
            shift_start = datetime.fromisoformat(shift_start)
        if isinstance(shift_end, str):
            shift_end = datetime.fromisoformat(shift_end)

        duration = (shift_end - shift_start).total_seconds() / 3600
        now = datetime.now(timezone.utc)

        if shift_start.tzinfo is None:
            shift_start = shift_start.replace(tzinfo=timezone.utc)

        elapsed = (now - shift_start).total_seconds() / 3600
        elapsed = max(0, min(elapsed, duration))

        pph = round(aggregated / elapsed, 2) if elapsed > 0 else 0.0
        remaining = total - aggregated

        if pph > 0 and remaining > 0:
            hours_to_complete = remaining / pph
            estimated = now + __import__('datetime').timedelta(hours=hours_to_complete)
        else:
            estimated = None

        return {
            "shift_duration_hours": round(duration, 2),
            "elapsed_hours": round(elapsed, 2),
            "products_per_hour": pph,
            "estimated_completion": estimated.isoformat() if estimated else None,
        }

    def _get_duration_hours(self, batch) -> float:
        """Получить длительность смены в часах."""
        if not batch.shift_start or not batch.shift_end:
            return 12.0

        shift_start = batch.shift_start
        shift_end = batch.shift_end

        if isinstance(shift_start, str):
            shift_start = datetime.fromisoformat(shift_start)
        if isinstance(shift_end, str):
            shift_end = datetime.fromisoformat(shift_end)

        return (shift_end - shift_start).total_seconds() / 3600
