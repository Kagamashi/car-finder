import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Filter(Base):
    __tablename__ = "filters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Filter criteria — NULL means "any"
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    year_min: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    year_max: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    mileage_max_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuel_types: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    sources: Mapped[list[int] | None] = mapped_column(ARRAY(SmallInteger), nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="filters")  # type: ignore[name-defined]  # noqa: F821
    notification_logs: Mapped[list["NotificationLog"]] = relationship(back_populates="filter", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_filters_user_id", "user_id"),
        Index("ix_filters_active", "is_active", postgresql_where="is_active = TRUE"),
    )
