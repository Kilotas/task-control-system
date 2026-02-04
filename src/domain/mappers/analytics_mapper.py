from __future__ import annotations

from src.api.v1.schemas.analytics import (
    DashboardOut,
    SummaryStats,
    TodayStats,
    ShiftStats,
    TopWorkCenter,
    BatchStatisticsOut,
    BatchInfo,
    ProductionStats,
    Timeline,
    TeamPerformance,
    CompareBatchesOut,
    BatchComparison,
    CompareAverage,
)


def to_dashboard_out(data: dict) -> DashboardOut:
    return DashboardOut(
        summary=SummaryStats(**data["summary"]),
        today=TodayStats(**data["today"]),
        by_shift={k: ShiftStats(**v) for k, v in data["by_shift"].items()},
        top_work_centers=[TopWorkCenter(**wc) for wc in data["top_work_centers"]],
        cached_at=data["cached_at"],
    )


def to_batch_statistics_out(data: dict) -> BatchStatisticsOut:
    return BatchStatisticsOut(
        batch_info=BatchInfo(**data["batch_info"]),
        production_stats=ProductionStats(**data["production_stats"]),
        timeline=Timeline(**data["timeline"]) if data["timeline"] else Timeline(),
        team_performance=TeamPerformance(**data["team_performance"]),
        cached_at=data["cached_at"],
    )


def to_compare_batches_out(data: dict) -> CompareBatchesOut:
    return CompareBatchesOut(
        comparison=[BatchComparison(**item) for item in data["comparison"]],
        average=CompareAverage(**data["average"]) if data["average"] else CompareAverage(aggregation_rate=0, products_per_hour=0),
    )
