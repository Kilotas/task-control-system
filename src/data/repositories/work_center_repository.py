import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.work_center import WorkCenter

logger = logging.getLogger(__name__)


class WorkCenterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_identifier(self, identifier: str) -> WorkCenter | None:
        stmt = select(WorkCenter).where(WorkCenter.identifier == identifier)
        return await self.session.scalar(stmt)

    async def create(self, *, identifier: str, name: str) -> WorkCenter:
        wc = WorkCenter(identifier=identifier, name=name)
        self.session.add(wc)
        await self.session.flush()

        logger.info(
            "WorkCenter created: id=%s identifier=%s",
            wc.id,
            wc.identifier,
        )
        return wc
