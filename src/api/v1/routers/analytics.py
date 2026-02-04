from fastapi import APIRouter, Depends

from src.api.v1.schemas.analytics import (
    DashboardOut,
    BatchStatisticsOut,
    CompareBatchesOut,
    CompareBatchesIn,
)
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.dependencies import get_uow
from src.domain.services.analytics_service import AnalyticsService
from src.domain.mappers.analytics_mapper import (
    to_dashboard_out,
    to_batch_statistics_out,
    to_compare_batches_out,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard_statistics(uow: SqlAlchemyUnitOfWork = Depends(get_uow)):
    service = AnalyticsService(uow)
    data = await service.get_dashboard_statistics()
    return to_dashboard_out(data)


@router.get("/batches/{batch_id}/statistics", response_model=BatchStatisticsOut)
async def get_batch_statistics(
    batch_id: int,
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
):
    service = AnalyticsService(uow)
    data = await service.get_batch_statistics(batch_id)
    return to_batch_statistics_out(data)


@router.post("/compare-batches", response_model=CompareBatchesOut)
async def compare_batches(
    request: CompareBatchesIn,
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
):
    service = AnalyticsService(uow)
    data = await service.compare_batches(request.batch_ids)
    return to_compare_batches_out(data)
