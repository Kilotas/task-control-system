from pydantic import BaseModel
from typing import Any, Literal

class BatchExportIn(BaseModel):
    format: Literal["excel", "csv"] = "excel"
    filters: dict[str, Any] = {}
