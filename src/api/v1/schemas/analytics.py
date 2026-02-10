from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SummaryStats(BaseModel):
    total_batches: int
    active_batches: int
    closed_batches: int
    total_products: int
    aggregated_products: int
    aggregation_rate: float


class TodayStats(BaseModel):
    batches_created: int
    batches_closed: int
    products_added: int
    products_aggregated: int


class ShiftStats(BaseModel):
    batches: int


class TopWorkCenter(BaseModel):
    id: str
    name: str
    batches_count: int


class DashboardOut(BaseModel):
    summary: SummaryStats
    today: TodayStats
    by_shift: dict[str, ShiftStats]
    top_work_centers: list[TopWorkCenter]
    cached_at: str


class BatchInfo(BaseModel):
    id: int
    batch_number: int
    batch_date: str
    is_closed: bool
    work_center: str | None


class ProductionStats(BaseModel):
    total_products: int
    aggregated: int
    remaining: int
    aggregation_rate: float


class Timeline(BaseModel):
    shift_duration_hours: float | None = None
    elapsed_hours: float | None = None
    products_per_hour: float | None = None
    estimated_completion: str | None = None


class TeamPerformance(BaseModel):
    team: str | None
    shift: str | None


class BatchStatisticsOut(BaseModel):
    batch_info: BatchInfo
    production_stats: ProductionStats
    timeline: Timeline
    team_performance: TeamPerformance
    cached_at: str


class BatchComparison(BaseModel):
    batch_id: int
    batch_number: int
    batch_date: str
    work_center: str | None
    total_products: int
    aggregated: int
    aggregation_rate: float
    duration_hours: float
    products_per_hour: float


class CompareAverage(BaseModel):
    aggregation_rate: float
    products_per_hour: float


class CompareBatchesOut(BaseModel):
    comparison: list[BatchComparison]
    average: CompareAverage


class CompareBatchesIn(BaseModel):
    batch_ids: list[int]
