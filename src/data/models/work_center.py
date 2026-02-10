from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import NAME_LEN, SHORT_STR_LEN
from src.data.models.base import Base, TimestampMixin


class WorkCenter(Base, TimestampMixin):
    __tablename__ = "work_centers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(
        String(SHORT_STR_LEN), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(NAME_LEN), nullable=False)

    batches: Mapped[list["Batch"]] = relationship(back_populates="work_center")
