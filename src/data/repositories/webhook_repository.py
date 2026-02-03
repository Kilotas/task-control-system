from __future__ import annotations

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models.webhook_delivery import WebhookDelivery
from src.data.models.webhook_subscription import WebhookSubscription


class WebhookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_subscription(self, data: dict) -> WebhookSubscription:
        sub = WebhookSubscription(**data)
        self.session.add(sub)
        await self.session.flush()
        return sub

    async def get_subscription_by_id(self, sub_id: int) -> WebhookSubscription | None:
        stmt = select(WebhookSubscription).where(WebhookSubscription.id == sub_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_subscriptions(self) -> list[WebhookSubscription]:
        stmt = select(WebhookSubscription).order_by(WebhookSubscription.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_subscription(self, sub: WebhookSubscription) -> WebhookSubscription:
        await self.session.flush()
        return sub

    async def delete_subscription(self, sub: WebhookSubscription) -> None:
        await self.session.delete(sub)
        await self.session.flush()

    async def get_active_subscriptions_for_event(
        self, event_type: str
    ) -> list[WebhookSubscription]:
        stmt = (
            select(WebhookSubscription)
            .where(
                WebhookSubscription.is_active.is_(True),
                WebhookSubscription.events.any(event_type),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())



    async def create_delivery(self, delivery: WebhookDelivery) -> WebhookDelivery:
        self.session.add(delivery)
        await self.session.flush()
        return delivery

    async def update_delivery(self, delivery: WebhookDelivery) -> WebhookDelivery:
        await self.session.flush()
        return delivery

    async def list_deliveries_by_subscription(
        self, subscription_id: int
    ) -> list[WebhookDelivery]:
        stmt = (
            select(WebhookDelivery)
            .where(WebhookDelivery.subscription_id == subscription_id)
            .order_by(WebhookDelivery.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_failed_deliveries(self, limit: int = 50) -> list[WebhookDelivery]:
        stmt = (
            select(WebhookDelivery)
            .options(selectinload(WebhookDelivery.subscription))
            .join(WebhookSubscription)
            .where(
                WebhookDelivery.status.in_(["failed", "pending"]),
                WebhookSubscription.is_active.is_(True),
                WebhookDelivery.attempts < WebhookSubscription.retry_count,
            )
            .order_by(WebhookDelivery.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_deliveries_for_event(
        self, event_type: str
    ) -> list[WebhookDelivery]:
        stmt = (
            select(WebhookDelivery)
            .options(selectinload(WebhookDelivery.subscription))
            .where(
                WebhookDelivery.event_type == event_type,
                WebhookDelivery.status == "pending",
                WebhookDelivery.attempts == 0,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
