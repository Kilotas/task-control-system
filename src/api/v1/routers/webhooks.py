from fastapi import APIRouter, status

from src.api.v1.schemas.webhook import (
    WebhookSubscriptionCreateIn,
    WebhookSubscriptionOut,
    WebhookSubscriptionListOut,
    WebhookSubscriptionUpdateIn,
    WebhookDeliveryListOut,
)
from src.core.dependencies import WebhookServiceDep

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


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
    return sub


@router.get(
    "",
    response_model=WebhookSubscriptionListOut,
    status_code=status.HTTP_200_OK,
)
async def list_webhooks(service: WebhookServiceDep):
    items = await service.list_subscriptions()
    return WebhookSubscriptionListOut(items=items, total=len(items))


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
    return sub


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
    return WebhookDeliveryListOut(items=items, total=len(items))
