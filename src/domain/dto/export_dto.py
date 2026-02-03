from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class BatchExportRowDTO:
    id: int
    batch_number: int
    batch_date: date
    is_closed: bool
    closed_at: datetime | None
    work_center_identifier: str | None
    work_center_name: str | None
    shift: str | None
    team: str | None
    nomenclature: str | None
    ekn_code: str | None
    shift_start: datetime | None
    shift_end: datetime | None


@dataclass(frozen=True)
class ExportResult:
    success: bool
    file_url: str | None = None
    file_name: str | None = None
    total_batches: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.success:
            return {
                "success": True,
                "file_url": self.file_url,
                "file_name": self.file_name,
                "total_batches": self.total_batches,
            }
        return {"success": False, "error": self.error}
