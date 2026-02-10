from pydantic import BaseModel
from datetime import datetime


class ProductCreate(BaseModel):
    unique_code: str
    batch_id: int


class ProductOut(BaseModel):
    id: int
    unique_code: str
    batch_id: int
    is_aggregated: bool
    aggregated_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
