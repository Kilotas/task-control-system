from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from typing import Optional

from src.core.constants import (
    BATCH_IS_CLOSED,
    BATCH_TASK_DESCRIPTION,
    BATCH_WORK_CENTER_NAME,
    BATCH_SHIFT,
    BATCH_TEAM,
    BATCH_NUMBER,
    BATCH_DATE,
    BATCH_NOMENCLATURE,
    BATCH_EKN_CODE,
    BATCH_WORK_CENTER_IDENTIFIER,
    BATCH_SHIFT_START,
    BATCH_SHIFT_END,
    DEFAULT_OFFSET,
    DEFAULT_LIMIT,
    MIN_LIMIT,
    MAX_LIMIT,
)


class BatchCreateIn(BaseModel):
    """
    Входной DTO. Наружу — русские поля, внутри — англ поля модели Batch.
    """
    model_config = ConfigDict(populate_by_name=True)

    is_closed: bool = Field(alias=BATCH_IS_CLOSED)
    task_description: str = Field(alias=BATCH_TASK_DESCRIPTION)

    work_center_name: str = Field(alias=BATCH_WORK_CENTER_NAME)
    shift: str = Field(alias=BATCH_SHIFT)
    team: str = Field(alias=BATCH_TEAM)

    batch_number: int = Field(alias=BATCH_NUMBER)
    batch_date: date = Field(alias=BATCH_DATE)

    nomenclature: str = Field(alias=BATCH_NOMENCLATURE)
    ekn_code: str = Field(alias=BATCH_EKN_CODE)

    work_center_identifier: str = Field(alias=BATCH_WORK_CENTER_IDENTIFIER)

    shift_start: datetime = Field(alias=BATCH_SHIFT_START)
    shift_end: datetime = Field(alias=BATCH_SHIFT_END)


    @field_validator("batch_number")
    @classmethod
    def validate_batch_number(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("НомерПартии должен быть > 0")
        return v


    @field_validator("shift_end")
    @classmethod
    def validate_shift_times(cls, v: datetime, info):
        start = info.data.get("shift_start")
        if start and v <= start:
            raise ValueError(
                "ДатаВремяОкончанияСмены должна быть позже начала смены"
            )
        return v


class BatchCreatedOut(BaseModel):
    """
    Ответ DTO.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: int
    is_closed: bool = Field(alias=BATCH_IS_CLOSED)
    batch_number: int = Field(alias=BATCH_NUMBER)
    batch_date: date = Field(alias=BATCH_DATE)
    work_center_identifier: str = Field(alias=BATCH_WORK_CENTER_IDENTIFIER)
    created_at: datetime


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unique_code: str
    is_aggregated: bool
    aggregated_at: datetime | None


class BatchDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_closed: bool
    batch_number: int
    batch_date: date
    products: list[ProductOut]


class BatchUpdateIn(BaseModel):
    """
    PATCH: обновляем только разрешённые поля.
    Сейчас — только is_closed.
    """
    model_config = ConfigDict(populate_by_name=True)

    is_closed: bool = Field(alias="СтатусЗакрытия")


class BatchListQuery(BaseModel):
    """Параметры запроса для списка партий"""

    is_closed: Optional[bool] = None
    batch_number: Optional[int] = None
    batch_date: Optional[date] = None
    work_center_id: Optional[str] = None
    shift: Optional[str] = None

    offset: int = Field(
        default=DEFAULT_OFFSET,
        ge=0,
        description="Смещение для пагинации"
    )

    limit: int = Field(
        default=DEFAULT_LIMIT,
        ge=MIN_LIMIT,
        le=MAX_LIMIT,
        description=f"Количество записей на странице (от {MIN_LIMIT} до {MAX_LIMIT})"
    )


class BatchAggregateOut(BaseModel):
    batch_id: int
    updated_count: int
    already_aggregated: int
    total_products: int
