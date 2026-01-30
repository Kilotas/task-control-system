from src.data.models import Batch
from src.domain.dto.report_dto import BatchReportDTO, ProductReportDTO


def _to_report_dto(batch: Batch) -> BatchReportDTO:
    return BatchReportDTO(
        batch_number=batch.batch_number,
        batch_date=str(batch.batch_date),
        is_closed=batch.is_closed,
        work_center_name=batch.work_center.name if batch.work_center else "-",
        shift=batch.shift,
        team=batch.team,
        nomenclature=batch.nomenclature,
        shift_start=batch.shift_start,
        shift_end=batch.shift_end,
        products=[
            ProductReportDTO(
                id=p.id,
                unique_code=p.unique_code,
                is_aggregated=p.is_aggregated,
                aggregated_at=p.aggregated_at,
            )
            for p in batch.products
        ],
    )
