from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.data.models.base import Base
from src.core.constants import SHORT_STR_LEN


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("webhook_subscriptions.id"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(String(SHORT_STR_LEN), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False)  # pending/success/failed
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subscription: Mapped["WebhookSubscription"] = relationship(back_populates="deliveries")
