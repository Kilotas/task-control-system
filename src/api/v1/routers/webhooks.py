from fastapi import APIRouter, status

from src.api.v1.schemas.webhook import (
    WebhookSubscriptionCreateIn,
    WebhookSubscriptionOut,
    WebhookSubscriptionListOut,
    WebhookSubscriptionUpdateIn,
    WebhookDeliveryListOut,
)
from src.core.dependencies import WebhookServiceDep
from src.core.circuit_breaker import webhook_circuit_breaker
from src.domain.mappers.webhook_mapper import (
    to_subscription_out,
    to_subscription_list_out,
    to_delivery_list_out,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.get("/circuit-breaker/status")
async def get_circuit_breaker_status():
    return webhook_circuit_breaker.get_state()


@router.post(
    "",
    response_model=WebhookSubscriptionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_webhook(
    payload: WebhookSubscriptionCreateIn,
    service: WebhookServiceDep,
):
    data = payload.model_dump()
    data["url"] = str(data["url"])
    sub = await service.create_subscription(data)
    return to_subscription_out(sub)


@router.get(
    "",
    response_model=WebhookSubscriptionListOut,
    status_code=status.HTTP_200_OK,
)
async def list_webhooks(service: WebhookServiceDep):
    items = await service.list_subscriptions()
    return to_subscription_list_out(items)


@router.patch(
    "/{webhook_id}",
    response_model=WebhookSubscriptionOut,
    status_code=status.HTTP_200_OK,
)
async def update_webhook(
    webhook_id: int,
    payload: WebhookSubscriptionUpdateIn,
    service: WebhookServiceDep,
):
    data = payload.model_dump(exclude_unset=True)
    if "url" in data and data["url"] is not None:
        data["url"] = str(data["url"])
    sub = await service.update_subscription(webhook_id, data)
    return to_subscription_out(sub)


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_webhook(
    webhook_id: int,
    service: WebhookServiceDep,
):
    await service.delete_subscription(webhook_id)


@router.get(
    "/{webhook_id}/deliveries",
    response_model=WebhookDeliveryListOut,
    status_code=status.HTTP_200_OK,
)
async def list_deliveries(
    webhook_id: int,
    service: WebhookServiceDep,
):
    items = await service.list_deliveries(webhook_id)
    return to_delivery_list_out(items)
