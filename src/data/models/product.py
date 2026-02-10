from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.data.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    unique_code: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False, index=True)

    is_aggregated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    aggregated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    batch: Mapped["Batch"] = relationship(back_populates="products")

    __table_args__ = (
        Index("idx_product_batch_aggregated", "batch_id", "is_aggregated"),
    )
