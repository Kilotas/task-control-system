import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

from src.domain.services.batch_service import BatchService
from src.core.exceptions import NotFoundException


@pytest.mark.asyncio
class TestBatchService:

    async def test_create_batches_success(self, test_uow, sample_work_center):
        service = BatchService(test_uow)

        items = [
            {
                "batch_number": 2001,
                "batch_date": date.today(),
                "work_center_identifier": sample_work_center.identifier,
                "work_center_name": sample_work_center.name,
                "shift": "1",
                "team": "B",
                "task_description": "Test task",
                "nomenclature": "Test nomenclature",
                "ekn_code": "EKN002",
                "shift_start": datetime.now(),
                "shift_end": datetime.now() + timedelta(hours=8),
                "is_closed": False,
            }
        ]

        result = await service.create_batches(items)

        assert len(result) == 1
        assert result[0].batch_number == 2001
        assert result[0].shift == "1"

    async def test_create_batches_new_work_center(self, test_uow):
        service = BatchService(test_uow)

        items = [
            {
                "batch_number": 3001,
                "batch_date": date.today(),
                "work_center_identifier": "NEW-WC",
                "work_center_name": "New Work Center",
                "shift": "2",
                "team": "C",
                "task_description": "New WC task",
                "nomenclature": "Test nomenclature",
                "ekn_code": "EKN003",
                "shift_start": datetime.now(),
                "shift_end": datetime.now() + timedelta(hours=8),
                "is_closed": False,
            }
        ]

        result = await service.create_batches(items)

        assert len(result) == 1
        assert result[0].batch_number == 3001

    async def test_get_batch_by_id_success(self, test_uow, sample_batch):
        service = BatchService(test_uow)

        result = await service.get_batch_by_id(sample_batch.id)

        assert result is not None
        assert result.id == sample_batch.id
        assert result.batch_number == sample_batch.batch_number

    async def test_get_batch_by_id_not_found(self, test_uow):
        service = BatchService(test_uow)

        with pytest.raises(NotFoundException):
            await service.get_batch_by_id(99999)

    async def test_list_batches(self, test_uow, sample_batch):
        service = BatchService(test_uow)

        query = AsyncMock()
        query.is_closed = None
        query.batch_number = None
        query.batch_date = None
        query.work_center_id = None
        query.shift = None
        query.offset = 0
        query.limit = 20

        result = await service.list_batches(query)

        assert len(result) >= 1

    async def test_aggregate_batch_products(self, test_uow, sample_batch, sample_products):
        service = BatchService(test_uow)

        result = await service.aggregate_batch_products(sample_batch.id)

        assert "batch_id" in result
        assert "updated_count" in result

    async def test_aggregate_batch_not_found(self, test_uow):
        service = BatchService(test_uow)

        with pytest.raises(NotFoundException):
            await service.aggregate_batch_products(99999)
