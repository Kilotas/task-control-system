from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class ProductReportDTO:
    id: int
    unique_code: str
    is_aggregated: bool
    aggregated_at: datetime | None


@dataclass(frozen=True)
class BatchReportDTO:
    batch_number: int
    batch_date: str
    is_closed: bool
    work_center_name: str
    shift: str
    team: str
    nomenclature: str
    shift_start: datetime
    shift_end: datetime
    products: List[ProductReportDTO]