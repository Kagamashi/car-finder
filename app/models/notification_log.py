import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("filters.id", ondelete="CASCADE"), nullable=False
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="sent", nullable=False)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)

    filter: Mapped["Filter"] = relationship(back_populates="notification_logs")  # type: ignore[name-defined]  # noqa: F821
    listing: Mapped["Listing"] = relationship(back_populates="notification_logs")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        UniqueConstraint("filter_id", "listing_id", name="uq_notification_log_filter_listing"),
        Index("ix_notification_log_filter_id", "filter_id"),
        Index("ix_notification_log_listing_id", "listing_id"),
    )
