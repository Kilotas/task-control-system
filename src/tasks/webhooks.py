import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx

from src.celery_app import celery_app
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.database import celery_session_maker
from src.data.models.webhook_delivery import WebhookDelivery

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1, name="deliver_webhook_event")
def deliver_webhook_event(self, event_type: str, payload: dict):
    uow = SqlAlchemyUnitOfWork(celery_session_maker)

    async def _run():
        async with uow:
            subscriptions = await uow.webhooks.get_active_subscriptions_for_event(event_type)

            for sub in subscriptions:
                delivery = WebhookDelivery(
                    subscription_id=sub.id,
                    event_type=event_type,
                    payload=payload,
                    status="pending",
                    attempts=0,
                )
                await uow.webhooks.create_delivery(delivery)

            await uow.flush()

            deliveries = await uow.webhooks.get_pending_deliveries_for_event(event_type)

            async with httpx.AsyncClient() as client:
                for delivery in deliveries:
                    sub = delivery.subscription
                    body = json.dumps(delivery.payload, default=str)
                    signature = hmac.new(
                        sub.secret_key.encode(), body.encode(), hashlib.sha256
                    ).hexdigest()

                    delivery.attempts += 1
                    try:
                        resp = await client.post(
                            sub.url,
                            content=body,
                            headers={
                                "Content-Type": "application/json",
                                "X-Webhook-Signature": signature,
                            },
                            timeout=sub.timeout,
                        )
                        delivery.response_status = resp.status_code
                        delivery.response_body = resp.text[:1024]
                        if 200 <= resp.status_code < 300:
                            delivery.status = "success"
                            delivery.delivered_at = datetime.now(timezone.utc)
                        else:
                            delivery.status = "failed"
                    except Exception as exc:
                        delivery.status = "failed"
                        delivery.error_message = str(exc)[:512]

                    await uow.webhooks.update_delivery(delivery)

        logger.info("deliver_webhook_event: event=%s dispatched", event_type)

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("deliver_webhook_event failed: event=%s", event_type)
        raise self.retry(exc=exc, countdown=10)
