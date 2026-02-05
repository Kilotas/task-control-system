from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.api.v1.schemas.analytics import (
        DashboardOut,
        BatchStatisticsOut,
        CompareBatchesOut,
    )


def to_dashboard_out(data: dict) -> "DashboardOut":
    from src.api.v1.schemas.analytics import (
        DashboardOut,
        SummaryStats,
        TodayStats,
        ShiftStats,
        TopWorkCenter,
    )
    return DashboardOut(
        summary=SummaryStats(**data["summary"]),
        today=TodayStats(**data["today"]),
        by_shift={k: ShiftStats(**v) for k, v in data["by_shift"].items()},
        top_work_centers=[TopWorkCenter(**wc) for wc in data["top_work_centers"]],
        cached_at=data["cached_at"],
    )


def to_batch_statistics_out(data: dict) -> "BatchStatisticsOut":
    from src.api.v1.schemas.analytics import (
        BatchStatisticsOut,
        BatchInfo,
        ProductionStats,
        Timeline,
        TeamPerformance,
    )
    return BatchStatisticsOut(
        batch_info=BatchInfo(**data["batch_info"]),
        production_stats=ProductionStats(**data["production_stats"]),
        timeline=Timeline(**data["timeline"]) if data["timeline"] else Timeline(),
        team_performance=TeamPerformance(**data["team_performance"]),
        cached_at=data["cached_at"],
    )


def to_compare_batches_out(data: dict) -> "CompareBatchesOut":
    from src.api.v1.schemas.analytics import (
        CompareBatchesOut,
        BatchComparison,
        CompareAverage,
    )
    return CompareBatchesOut(
        comparison=[BatchComparison(**item) for item in data["comparison"]],
        average=CompareAverage(**data["average"]) if data["average"] else CompareAverage(aggregation_rate=0, products_per_hour=0),
    )
