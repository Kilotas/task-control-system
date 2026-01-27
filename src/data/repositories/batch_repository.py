from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.batch import Batch


class BatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session


    async def exists_by_number_and_date(self, batch_number: int, batch_date: date) -> bool:
        stmt = select(Batch.id).where(
            Batch.batch_number == batch_number,
            Batch.batch_date == batch_date,
        )
        return (await self.session.scalar(stmt)) is not None


    async def bulk_create(self, items: list[dict]) -> list[Batch]:
        batches = [Batch(**item) for item in items]
        self.session.add_all(batches)
        await self.session.flush()
        return batches


    async def get_by_id_with_products(self, batch_id: int) -> Batch | None:
        stmt = (
            select(Batch)
            .where(Batch.id == batch_id)
            .options(selectinload(Batch.products))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


    async def get_by_id(self, batch_id: int) -> Batch | None:
        stmt = select(Batch).where(Batch.id == batch_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


    async def update(self, batch: Batch) -> Batch:
        await self.session.flush()
        return batch


    async def get_by_id_with_wc(self, batch_id: int):
        stmt = (
            select(Batch)
            .options(selectinload(Batch.work_center))
            .where(Batch.id == batch_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


    async def list(
        self,
        *,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        work_center_id: str | None = None,
        shift: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        stmt = select(Batch).options(selectinload(Batch.work_center))

        if is_closed is not None:
            stmt = stmt.where(Batch.is_closed == is_closed)
        if batch_number is not None:
            stmt = stmt.where(Batch.batch_number == batch_number)
        if batch_date is not None:
            stmt = stmt.where(Batch.batch_date == batch_date)
        if work_center_id is not None:
            stmt = stmt.where(Batch.work_center.has(identifier=work_center_id))
        if shift is not None:
            stmt = stmt.where(Batch.shift == shift)

        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        batches = result.scalars().all()


        return [
            {
                "batch": b,
                "work_center_identifier": b.work_center.identifier if b.work_center else None
            }
            for b in batches
        ]
