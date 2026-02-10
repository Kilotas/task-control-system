import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.repositories.batch_repository import BatchRepository
from src.data.repositories.work_center_repository import WorkCenterRepository
from src.data.repositories.product_repository import ProductRepository
from src.data.repositories.webhook_repository import WebhookRepository

logger = logging.getLogger(__name__)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self):
        self._session = self._session_factory()
        self.batches = BatchRepository(self._session)
        self.work_centers = WorkCenterRepository(self._session)
        self.products = ProductRepository(self._session)
        self.webhooks = WebhookRepository(self._session)

        logger.debug("UoW started, session=%s", id(self._session))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.warning("UoW rollback due to exception: %s", exc_type.__name__)
            await self.rollback()
        else:
            try:
                await self.commit()
            except Exception:
                await self.rollback()
                raise
        if self._session:
            await self._session.close()
            self._session = None

    async def flush(self) -> None:
        if self._session is None:
            raise RuntimeError("UoW session is not initialized")

        await self._session.flush()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("UoW session is not initialized")

        try:
            await self._session.commit()
            logger.debug("UoW committed successfully")
        except Exception:
            logger.exception("UoW commit failed")
            await self.rollback()
            raise

    async def rollback(self) -> None:
        if self._session:
            await self._session.rollback()
            logger.debug("UoW rolled back")
