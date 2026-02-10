from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import NAME_LEN, SHORT_STR_LEN
from src.data.models.base import Base, TimestampMixin


class Batch(Base, TimestampMixin):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task_description: Mapped[str] = mapped_column(String(NAME_LEN), nullable=False)
    work_center_id: Mapped[int] = mapped_column(ForeignKey("work_centers.id"), nullable=False)

    shift: Mapped[str] = mapped_column(String(SHORT_STR_LEN), nullable=False)
    team: Mapped[str] = mapped_column(String(SHORT_STR_LEN), nullable=False)

    batch_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)


    batch_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    nomenclature: Mapped[str] = mapped_column(String(NAME_LEN), nullable=False)
    ekn_code: Mapped[str] = mapped_column(String(SHORT_STR_LEN), nullable=False)


    shift_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    shift_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    work_center: Mapped["WorkCenter"] = relationship(back_populates="batches")

    __table_args__ = (
        UniqueConstraint("batch_number", "batch_date", name="uq_batch_number_date"),
        Index("idx_batch_closed", "is_closed"),
        Index("idx_batch_shift_times", "shift_start", "shift_end"),
    )
