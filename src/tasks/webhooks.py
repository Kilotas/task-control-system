import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone

import httpx

from src.celery_app import celery_app
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.database import celery_session_maker
from src.data.models.webhook_delivery import WebhookDelivery
from src.domain.exceptions import (
    WebhookDeliveryNotFound,
    WebhookSubscriptionInactive,
    WebhookDeliveryFailed,
    WebhookTimeoutError,
    WebhookConnectionError,
    WebhookHttpError,
)

logger = logging.getLogger(__name__)

RETRY_DELAYS = [10, 60, 300]


def generate_signature(secret_key: str, payload: str, timestamp: str) -> str:
    """Генерация HMAC-SHA256 подписи. Формат: t={timestamp},v1={signature}"""
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def build_payload(event_type: str, data: dict) -> dict:
    """Формирование стандартного payload для webhook."""
    return {
        "event": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_headers(signature: str, event_type: str, delivery_id: int, timestamp: str) -> dict:
    """Формирование заголовков для webhook запроса."""
    return {
        "Content-Type": "application/json; charset=utf-8",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": event_type,
        "X-Webhook-Delivery-Id": str(delivery_id),
        "X-Webhook-Timestamp": timestamp,
    }


async def execute_http_request(url: str, body: str, headers: dict, timeout: float) -> httpx.Response:
    """Выполнение HTTP POST запроса."""
    async with httpx.AsyncClient() as client:
        return await client.post(
            url,
            content=body,
            headers=headers,
            timeout=httpx.Timeout(timeout),
        )


def handle_response(delivery: WebhookDelivery, response: httpx.Response) -> None:
    """Обработка HTTP ответа. Выбрасывает исключение при ошибке."""
    delivery.response_status = response.status_code
    delivery.response_body = response.text[:2048] if response.text else None

    if 200 <= response.status_code < 300:
        delivery.status = "success"
        delivery.delivered_at = datetime.now(timezone.utc)
        logger.info("Webhook delivered: id=%s, status=%s", delivery.id, response.status_code)
    else:
        delivery.status = "failed"
        delivery.error_message = f"HTTP {response.status_code}"
        logger.warning("Webhook failed: id=%s, status=%s", delivery.id, response.status_code)
        raise WebhookHttpError(delivery.id, response.status_code, delivery.response_body)


def handle_request_error(delivery: WebhookDelivery, exc: Exception, url: str, timeout: float) -> None:
    """Обработка ошибки запроса. Всегда выбрасывает исключение."""
    delivery.status = "failed"

    if isinstance(exc, httpx.TimeoutException):
        delivery.error_message = f"Timeout: {str(exc)[:256]}"
        logger.warning("Webhook timeout: id=%s", delivery.id)
        raise WebhookTimeoutError(delivery.id, url, timeout)

    if isinstance(exc, httpx.RequestError):
        delivery.error_message = f"Connection error: {str(exc)[:256]}"
        logger.warning("Webhook connection error: id=%s, error=%s", delivery.id, exc)
        raise WebhookConnectionError(delivery.id, url, str(exc)[:256])

    delivery.error_message = f"Unexpected error: {str(exc)[:256]}"
    logger.exception("Webhook unexpected error: id=%s", delivery.id)
    raise WebhookDeliveryFailed(delivery.id, str(exc)[:256])


@celery_app.task(bind=True, max_retries=3, name="send_webhook_delivery")
def send_webhook_delivery(self, delivery_id: int):
    """Отправка webhook с retry логикой."""

    async def _send():
        uow = SqlAlchemyUnitOfWork(celery_session_maker)
        async with uow:
            delivery = await uow.webhooks.get_delivery_by_id(delivery_id)
            if not delivery:
                raise WebhookDeliveryNotFound(delivery_id)

            if delivery.status == "success":
                logger.info("Delivery already succeeded: id=%s", delivery_id)
                return

            subscription = await uow.webhooks.get_subscription_by_id(delivery.subscription_id)
            if not subscription or not subscription.is_active:
                await _cancel_delivery(uow, delivery)
                return

            await _attempt_delivery(uow, delivery, subscription)

    async def _cancel_delivery(uow, delivery):
        delivery.status = "cancelled"
        delivery.error_message = "Subscription inactive or not found"
        await uow.webhooks.update_delivery(delivery)
        await uow.commit()
        raise WebhookSubscriptionInactive(delivery.subscription_id)

    async def _attempt_delivery(uow, delivery, subscription):
        body = json.dumps(delivery.payload, default=str, ensure_ascii=False)
        timestamp = str(int(time.time()))
        signature = generate_signature(subscription.secret_key, body, timestamp)
        headers = build_headers(signature, delivery.event_type, delivery.id, timestamp)
        timeout = subscription.timeout or 30.0

        delivery.attempts += 1
        delivery.last_attempt_at = datetime.now(timezone.utc)

        try:
            response = await execute_http_request(subscription.url, body, headers, timeout)
            handle_response(delivery, response)
        except (WebhookHttpError, WebhookTimeoutError, WebhookConnectionError, WebhookDeliveryFailed):
            raise
        except Exception as exc:
            handle_request_error(delivery, exc, subscription.url, timeout)
        finally:
            await uow.webhooks.update_delivery(delivery)
            await uow.commit()

    try:
        asyncio.run(_send())
    except WebhookDeliveryNotFound:
        logger.error("Delivery not found: id=%s", delivery_id)
    except WebhookSubscriptionInactive:
        logger.warning("Subscription inactive: delivery_id=%s", delivery_id)
    except (WebhookHttpError, WebhookTimeoutError, WebhookConnectionError, WebhookDeliveryFailed) as exc:
        _handle_retry(self, delivery_id, exc)


def _handle_retry(task, delivery_id: int, exc: Exception) -> None:
    """Обработка retry логики."""
    retry_count = task.request.retries
    if retry_count < task.max_retries:
        countdown = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]
        logger.info("Retrying: delivery_id=%s, attempt=%s, countdown=%ss", delivery_id, retry_count + 1, countdown)
        raise task.retry(exc=exc, countdown=countdown)
    else:
        logger.error("Exhausted retries: delivery_id=%s, attempts=%s", delivery_id, retry_count + 1)


@celery_app.task(bind=True, max_retries=1, name="deliver_webhook_event")
def deliver_webhook_event(self, event_type: str, data: dict):
    """Создание WebhookDelivery записей и постановка задач на отправку."""

    async def _create_deliveries() -> list[int]:
        uow = SqlAlchemyUnitOfWork(celery_session_maker)
        async with uow:
            subscriptions = await uow.webhooks.get_active_subscriptions_for_event(event_type)
            if not subscriptions:
                logger.debug("No subscriptions for event: %s", event_type)
                return []

            payload = build_payload(event_type, data)
            delivery_ids = []

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
                delivery_ids.append(delivery.id)

            await uow.commit()
            logger.info("Created %d deliveries for event: %s", len(delivery_ids), event_type)
            return delivery_ids

    try:
        delivery_ids = asyncio.run(_create_deliveries())
        for delivery_id in delivery_ids:
            send_webhook_delivery.delay(delivery_id)
        return {"event_type": event_type, "deliveries_created": len(delivery_ids)}
    except Exception as exc:
        logger.exception("Failed to create deliveries: event=%s", event_type)
        raise self.retry(exc=exc, countdown=10)
