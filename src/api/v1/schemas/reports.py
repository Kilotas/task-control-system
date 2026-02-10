from dataclasses import Field
from datetime import datetime, date

from pydantic import BaseModel, EmailStr
from typing import Literal

class BatchReportIn(BaseModel):
    """Запрос на генерацию отчета (УЖЕ ЕСТЬ У ВАС)"""
    format: Literal["excel", "pdf"] = "excel"
    email: EmailStr | None = None


