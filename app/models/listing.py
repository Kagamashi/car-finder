import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Index, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="PLN", nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    mileage_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    source: Mapped["Source"] = relationship(back_populates="listings")  # type: ignore[name-defined]  # noqa: F821
    notification_logs: Mapped[list["NotificationLog"]] = relationship(back_populates="listing", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_listings_source_id", "source_id"),
        Index("ix_listings_content_hash", "content_hash"),
        Index("ix_listings_brand_model", "brand", "model"),
        Index("ix_listings_price", "price"),
        Index("ix_listings_year", "year"),
        Index("ix_listings_fuel_type", "fuel_type"),
        Index("ix_listings_first_seen", "first_seen_at"),
    )
