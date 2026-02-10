from typing import Annotated, Any

from fastapi import Depends

from src.application.uow.protocol import UnitOfWorkProtocol
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.database import async_session_maker


def get_uow() -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(async_session_maker)


async def get_batch_service(
    uow: Annotated[UnitOfWorkProtocol, Depends(get_uow)],
) -> Any:
    from src.domain.services.batch_service import BatchService
    return BatchService(uow=uow)


async def get_product_service(
    uow: Annotated[UnitOfWorkProtocol, Depends(get_uow)],
) -> Any:
    from src.domain.services.product_service import ProductService
    return ProductService(uow=uow)


async def get_webhook_service(
    uow: Annotated[UnitOfWorkProtocol, Depends(get_uow)],
) -> Any:
    from src.domain.services.webhook_service import WebhookService
    return WebhookService(uow=uow)


BatchServiceDep = Annotated[Any, Depends(get_batch_service)]
ProductServiceDep = Annotated[Any, Depends(get_product_service)]
WebhookServiceDep = Annotated[Any, Depends(get_webhook_service)]
