from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.api.v1.schemas.webhook import (
        WebhookSubscriptionOut,
        WebhookSubscriptionListOut,
        WebhookDeliveryOut,
        WebhookDeliveryListOut,
    )


def to_subscription_out(subscription) -> "WebhookSubscriptionOut":
    from src.api.v1.schemas.webhook import WebhookSubscriptionOut
    return WebhookSubscriptionOut(
        id=subscription.id,
        url=subscription.url,
        events=subscription.events,
        is_active=subscription.is_active,
        created_at=subscription.created_at,
    )


def to_subscription_list_out(subscriptions: list) -> "WebhookSubscriptionListOut":
    from src.api.v1.schemas.webhook import WebhookSubscriptionListOut
    items = [to_subscription_out(sub) for sub in subscriptions]
    return WebhookSubscriptionListOut(items=items, total=len(items))


def to_delivery_out(delivery) -> "WebhookDeliveryOut":
    from src.api.v1.schemas.webhook import WebhookDeliveryOut
    return WebhookDeliveryOut(
        id=delivery.id,
        event_type=delivery.event_type,
        status=delivery.status,
        attempts=delivery.attempts,
        response_status=delivery.response_status,
        error_message=delivery.error_message,
        created_at=delivery.created_at,
        delivered_at=delivery.delivered_at,
    )


def to_delivery_list_out(deliveries: list) -> "WebhookDeliveryListOut":
    from src.api.v1.schemas.webhook import WebhookDeliveryListOut
    items = [to_delivery_out(d) for d in deliveries]
    return WebhookDeliveryListOut(items=items, total=len(items))
