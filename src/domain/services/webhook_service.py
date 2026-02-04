from __future__ import annotations

import logging
from typing import Any

from src.application.uow.protocol import UnitOfWorkProtocol
from src.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, uow: UnitOfWorkProtocol):
        self.uow = uow

    async def create_subscription(self, data: dict[str, Any]):
        async with self.uow as uow:
            subscription = await uow.webhooks.create_subscription(data)
            return subscription

    async def list_subscriptions(self):
        async with self.uow as uow:
            items = await uow.webhooks.list_subscriptions()
            return items

    async def get_subscription(self, webhook_id: int):
        async with self.uow as uow:
            sub = await uow.webhooks.get_subscription_by_id(webhook_id)
            if sub is None:
                raise NotFoundException("WebhookSubscription", webhook_id)
            return sub

    async def update_subscription(self, webhook_id: int, data: dict[str, Any]):
        async with self.uow as uow:
            sub = await uow.webhooks.get_subscription_by_id(webhook_id)
            if sub is None:
                raise NotFoundException("WebhookSubscription", webhook_id)
            for key, value in data.items():
                setattr(sub, key, value)
            await uow.webhooks.update_subscription(sub)
            return sub

    async def delete_subscription(self, webhook_id: int):
        async with self.uow as uow:
            sub = await uow.webhooks.get_subscription_by_id(webhook_id)
            if sub is None:
                raise NotFoundException("WebhookSubscription", webhook_id)
            await uow.webhooks.delete_subscription(sub)

    async def list_deliveries(self, webhook_id: int):
        async with self.uow as uow:
            sub = await uow.webhooks.get_subscription_by_id(webhook_id)
            if sub is None:
                raise NotFoundException("WebhookSubscription", webhook_id)
            items = await uow.webhooks.list_deliveries_by_subscription(webhook_id)
            return items


def dispatch_webhook_event(event_type: str, data: dict[str, Any]) -> None:
    """
    Отправка webhook события всем подписчикам.

    Args:
        event_type: Тип события (batch_created, batch_updated, etc.)
        data: Данные события
    """
    from src.tasks.webhooks import deliver_webhook_event
    deliver_webhook_event.delay(event_type=event_type, data=data)
