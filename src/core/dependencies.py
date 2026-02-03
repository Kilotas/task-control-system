from typing import Annotated

from fastapi import Depends

from src.application.uow.protocol import UnitOfWorkProtocol
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.database import async_session_maker
from src.domain.services.batch_service import BatchService
from src.domain.services.product_service import ProductService
from src.domain.services.webhook_service import WebhookService


def get_uow() -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(async_session_maker)


async def get_batch_service(
    uow: Annotated[UnitOfWorkProtocol, Depends(get_uow)],
) -> BatchService:
    return BatchService(uow=uow)


async def get_product_service(
    uow: Annotated[UnitOfWorkProtocol, Depends(get_uow)],
) -> ProductService:
    return ProductService(uow=uow)


async def get_webhook_service(
    uow: Annotated[UnitOfWorkProtocol, Depends(get_uow)],
) -> WebhookService:
    return WebhookService(uow=uow)


BatchServiceDep = Annotated[BatchService, Depends(get_batch_service)]

ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]

WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]
