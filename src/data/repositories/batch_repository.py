from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.batch import Batch
from src.data.models.product import Product
from src.data.models.work_center import WorkCenter


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


    async def get_by_id_with_products_and_wc(self, batch_id: int) -> Batch | None:
        stmt = (
            select(Batch)
            .where(Batch.id == batch_id)
            .options(
                selectinload(Batch.products),
                selectinload(Batch.work_center),
            )
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


    async def export_list(
            self,
            *,
            is_closed: bool | None = None,
            date_from: date | None = None,
            date_to: date | None = None,
            work_center_identifier: str | None = None,
            shift: str | None = None,
    ) -> list[Batch]:
        stmt = select(Batch).options(selectinload(Batch.work_center))

        if is_closed is not None:
            stmt = stmt.where(Batch.is_closed == is_closed)
        if date_from is not None:
            stmt = stmt.where(Batch.batch_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Batch.batch_date <= date_to)
        if work_center_identifier is not None:
            stmt = stmt.where(Batch.work_center.has(identifier=work_center_identifier))
        if shift is not None:
            stmt = stmt.where(Batch.shift == shift)

        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def close_expired(self, now: datetime) -> int:
        stmt = (
            update(Batch)
            .where(Batch.shift_end < now, Batch.is_closed.is_(False))
            .values(is_closed=True, closed_at=now)
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def count_statistics(self) -> dict:
        total = await self.session.scalar(select(func.count(Batch.id)))
        open_count = await self.session.scalar(
            select(func.count(Batch.id)).where(Batch.is_closed.is_(False))
        )
        closed_count = await self.session.scalar(
            select(func.count(Batch.id)).where(Batch.is_closed.is_(True))
        )
        product_count = await self.session.scalar(select(func.count(Product.id)))
        aggregated_count = await self.session.scalar(
            select(func.count(Product.id)).where(Product.is_aggregated.is_(True))
        )

        aggregation_rate = 0.0
        if product_count:
            aggregation_rate = round(aggregated_count / product_count * 100, 2)

        return {
            "total_batches": total or 0,
            "open_batches": open_count or 0,
            "closed_batches": closed_count or 0,
            "total_products": product_count or 0,
            "aggregated_products": aggregated_count or 0,
            "aggregation_rate": aggregation_rate,
        }

    async def count_today_statistics(self) -> dict:
        """Статистика за сегодня."""
        from datetime import date
        today = date.today()

        batches_created = await self.session.scalar(
            select(func.count(Batch.id)).where(Batch.batch_date == today)
        )
        batches_closed = await self.session.scalar(
            select(func.count(Batch.id)).where(
                Batch.batch_date == today,
                Batch.is_closed.is_(True),
            )
        )


        products_added = await self.session.scalar(
            select(func.count(Product.id))
            .join(Batch, Product.batch_id == Batch.id)
            .where(Batch.batch_date == today)
        )

        products_aggregated = await self.session.scalar(
            select(func.count(Product.id))
            .join(Batch, Product.batch_id == Batch.id)
            .where(
                Batch.batch_date == today,
                Product.is_aggregated.is_(True),
            )
        )

        return {
            "batches_created": batches_created or 0,
            "batches_closed": batches_closed or 0,
            "products_added": products_added or 0,
            "products_aggregated": products_aggregated or 0,
        }

    async def count_by_shift(self) -> dict:
        """Статистика по сменам."""
        stmt = (
            select(
                Batch.shift,
                func.count(Batch.id).label("batches"),
            )
            .group_by(Batch.shift)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        shift_stats = {}
        for row in rows:
            shift_name = f"Смена {row.shift}" if row.shift else "Не указано"
            shift_stats[shift_name] = {
                "batches": row.batches,
            }

        return shift_stats

    async def get_top_work_centers(self, limit: int = 5) -> list[dict]:
        """Топ рабочих центров по количеству партий."""
        stmt = (
            select(
                WorkCenter.id,
                WorkCenter.identifier,
                WorkCenter.name,
                func.count(Batch.id).label("batches_count"),
            )
            .join(Batch, Batch.work_center_id == WorkCenter.id)
            .group_by(WorkCenter.id, WorkCenter.identifier, WorkCenter.name)
            .order_by(func.count(Batch.id).desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "id": row.identifier,
                "name": row.name,
                "batches_count": row.batches_count,
            }
            for row in rows
        ]


