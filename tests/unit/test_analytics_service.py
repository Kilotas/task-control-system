import pytest
from unittest.mock import AsyncMock, patch

from src.domain.services.analytics_service import AnalyticsService
from src.core.exceptions import NotFoundException


@pytest.mark.asyncio
class TestAnalyticsService:

    async def test_get_dashboard_statistics(self, test_uow, sample_batch, sample_products):
        service = AnalyticsService(test_uow)

        with patch("src.domain.services.analytics_service.get_cache_service") as mock_cache:
            mock_cache.side_effect = RuntimeError("No cache")

            result = await service.get_dashboard_statistics()

        assert "summary" in result
        assert "today" in result
        assert "by_shift" in result
        assert "top_work_centers" in result
        assert "cached_at" in result

        assert result["summary"]["total_batches"] >= 1
        assert result["summary"]["total_products"] >= 1

    async def test_get_dashboard_statistics_from_cache(self, test_uow, test_cache):
        service = AnalyticsService(test_uow)

        cached_data = {
            "summary": {"total_batches": 100},
            "today": {},
            "by_shift": {},
            "top_work_centers": [],
            "cached_at": "2026-02-05T10:00:00",
        }
        test_cache.get.return_value = cached_data

        with patch("src.domain.services.analytics_service.get_cache_service", return_value=test_cache):
            result = await service.get_dashboard_statistics()

        assert result == cached_data
        test_cache.get.assert_called_once_with("dashboard_stats")

    async def test_get_batch_statistics_success(self, test_uow, sample_batch, sample_products):
        service = AnalyticsService(test_uow)

        with patch("src.domain.services.analytics_service.get_cache_service") as mock_cache:
            mock_cache.side_effect = RuntimeError("No cache")

            result = await service.get_batch_statistics(sample_batch.id)

        assert "batch_info" in result
        assert "production_stats" in result
        assert "timeline" in result
        assert "team_performance" in result

        assert result["batch_info"]["id"] == sample_batch.id
        assert result["production_stats"]["total_products"] == 10
        assert result["production_stats"]["aggregated"] == 5

    async def test_get_batch_statistics_not_found(self, test_uow):
        service = AnalyticsService(test_uow)

        with patch("src.domain.services.analytics_service.get_cache_service") as mock_cache:
            mock_cache.side_effect = RuntimeError("No cache")

            with pytest.raises(NotFoundException):
                await service.get_batch_statistics(99999)

    async def test_compare_batches(self, test_uow, sample_batch, sample_products):
        service = AnalyticsService(test_uow)

        result = await service.compare_batches([sample_batch.id])

        assert "comparison" in result
        assert "average" in result
        assert len(result["comparison"]) == 1
        assert result["comparison"][0]["batch_id"] == sample_batch.id

    async def test_compare_batches_empty(self, test_uow):
        service = AnalyticsService(test_uow)

        result = await service.compare_batches([])

        assert result == {"comparison": [], "average": {}}

    async def test_compare_batches_max_limit(self, test_uow):
        service = AnalyticsService(test_uow)

        batch_ids = list(range(1, 20))
        result = await service.compare_batches(batch_ids)

        assert len(result["comparison"]) <= 10
