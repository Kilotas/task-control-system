from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import (
    NAME_LEN,
    WEBHOOK_DEFAULT_RETRY_COUNT,
    WEBHOOK_DEFAULT_TIMEOUT,
)
from src.data.models.base import Base, TimestampMixin


class WebhookSubscription(Base, TimestampMixin):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(NAME_LEN), nullable=False)
    events: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    secret_key: Mapped[str] = mapped_column(String(NAME_LEN), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=WEBHOOK_DEFAULT_RETRY_COUNT)
    timeout: Mapped[int] = mapped_column(Integer, default=WEBHOOK_DEFAULT_TIMEOUT)

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(back_populates="subscription")
