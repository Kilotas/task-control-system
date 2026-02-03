from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class WebhookSubscriptionCreateIn(BaseModel):
    url: HttpUrl
    events: list[str]
    secret_key: str
    retry_count: int = 3
    timeout: int = 10


class WebhookSubscriptionOut(BaseModel):
    id: int
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookSubscriptionListOut(BaseModel):
    items: list[WebhookSubscriptionOut]
    total: int


class WebhookSubscriptionUpdateIn(BaseModel):
    url: HttpUrl | None = None
    events: list[str] | None = None
    secret_key: str | None = None
    is_active: bool | None = None
    retry_count: int | None = None
    timeout: int | None = None


class WebhookDeliveryOut(BaseModel):
    id: int
    event_type: str
    status: str
    attempts: int
    response_status: int | None = None
    error_message: str | None = None
    created_at: datetime
    delivered_at: datetime | None = None

    model_config = {"from_attributes": True}


class WebhookDeliveryListOut(BaseModel):
    items: list[WebhookDeliveryOut]
    total: int
