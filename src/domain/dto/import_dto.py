from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ImportErrorItem:
    row: int
    error: str

@dataclass(frozen=True)
class ImportResult:
    success: bool
    total_rows: int
    created: int
    skipped: int
    errors: list[ImportErrorItem]

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "total_rows": self.total_rows,
            "created": self.created,
            "skipped": self.skipped,
            "errors": [{"row": e.row, "error": e.error} for e in self.errors],
        }
