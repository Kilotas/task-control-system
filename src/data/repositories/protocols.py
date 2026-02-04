"""
Repository Protocols (DIP).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.batch import Batch
from ..models.product import Product
from ..models.work_center import WorkCenter


@runtime_checkable
class WorkCenterRepositoryProtocol(Protocol):
    session: AsyncSession

    async def get_by_identifier(self, identifier: str) -> WorkCenter | None: ...
    async def create(self, *, identifier: str, name: str) -> WorkCenter: ...


@runtime_checkable
class BatchRepositoryProtocol(Protocol):
    session: AsyncSession

    async def bulk_create(self, items: list[dict]) -> list[Batch]: ...
    async def exists_by_number_and_date(self, batch_number: int, batch_date: date) -> bool: ...
    async def get_by_id(self, batch_id: int) -> Batch | None: ...
    async def get_by_id_with_wc(self, batch_id: int) -> Batch | None: ...
    async def get_by_id_with_products(self, batch_id: int) -> Batch | None: ...
    async def update(self, batch: Batch) -> Batch: ...
    async def list(
        self,
        *,
        is_closed: bool | None,
        batch_number: int | None,
        batch_date: date | None,
        work_center_id: str | None,
        shift: str | None,
        offset: int,
        limit: int,
    ) -> list[Batch]: ...
    async def count_statistics(self) -> dict: ...
    async def count_today_statistics(self) -> dict: ...
    async def count_by_shift(self) -> dict: ...
    async def get_top_work_centers(self, limit: int = 5) -> list[dict]: ...


@runtime_checkable
class ProductRepositoryProtocol(Protocol):
    session: AsyncSession

    async def exists_by_unique_code(self, unique_code: str) -> bool: ...
    async def create(self, product: Product) -> Product: ...
    async def get_by_id(self, product_id: int) -> Product | None: ...
    async def count_by_batch(self, batch_id: int) -> int: ...
    async def count_aggregated_by_batch(self, batch_id: int) -> int: ...
    async def aggregate_by_batch(self, batch_id: int) -> int: ...



