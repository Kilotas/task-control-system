from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.product import Product


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exists_by_unique_code(self, unique_code: str) -> bool:
        stmt = select(Product.id).where(Product.unique_code == unique_code)
        return (await self.session.scalar(stmt)) is not None

    async def create(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.flush()
        return product

    async def count_by_batch(self, batch_id: int) -> int:
        stmt = select(func.count(Product.id)).where(Product.batch_id == batch_id)
        return int(await self.session.scalar(stmt) or 0)

    async def count_aggregated_by_batch(self, batch_id: int) -> int:
        stmt = select(func.count(Product.id)).where(
            Product.batch_id == batch_id,
            Product.is_aggregated.is_(True),
        )
        return int(await self.session.scalar(stmt) or 0)

    async def aggregate_by_batch(self, batch_id: int) -> int:
        stmt = (
            update(Product)
            .where(Product.batch_id == batch_id, Product.is_aggregated.is_(False))
            .values(is_aggregated=True, aggregated_at=func.now())
        )
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)

    async def fetch_statuses_by_codes(
            self,
            batch_id: int,
            codes: list[str],
    ) -> list[tuple[str, bool]]:
        """
        Вернёт список (unique_code, is_aggregated) для найденных продуктов партии.
        """
        stmt = select(Product.unique_code, Product.is_aggregated).where(
            Product.batch_id == batch_id,
            Product.unique_code.in_(codes),
        )
        res = await self.session.execute(stmt)
        return list(res.all())

    async def aggregate_by_codes(
            self,
            batch_id: int,
            codes_to_aggregate: list[str],
    ) -> int:
        """
        Массово выставляет aggregated для выбранных кодов (только тех, кто ещё не aggregated).
        Возвращает количество обновлённых строк.
        """
        if not codes_to_aggregate:
            return 0

        stmt = (
            update(Product)
            .where(
                Product.batch_id == batch_id,
                Product.unique_code.in_(codes_to_aggregate),
                Product.is_aggregated.is_(False),
            )
            .values(is_aggregated=True, aggregated_at=func.now())
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
