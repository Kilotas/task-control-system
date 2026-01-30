from pydantic import BaseModel, EmailStr
from typing import Literal

class BatchReportIn(BaseModel):
    format: Literal["excel", "pdf"] = "excel"
    email: EmailStr | None = None
