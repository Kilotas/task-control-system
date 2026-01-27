from enum import StrEnum


class WebhookDeliveryStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class WebhookEvent(StrEnum):
    BATCH_CREATED = "batch_created"
    BATCH_CLOSED = "batch_closed"
