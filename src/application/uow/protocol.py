from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.data.repositories.protocols import (
    BatchRepositoryProtocol,
    WorkCenterRepositoryProtocol,
    ProductRepositoryProtocol,
)
from src.data.repositories.webhook_repository import WebhookRepository


@runtime_checkable
class UnitOfWorkProtocol(Protocol):
    batches: BatchRepositoryProtocol
    work_centers: WorkCenterRepositoryProtocol
    products: ProductRepositoryProtocol
    webhooks: WebhookRepository

    async def flush(self) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...

    async def __aenter__(self) -> "UnitOfWorkProtocol": ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
