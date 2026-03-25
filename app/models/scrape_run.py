import uuid
from datetime import datetime

from sqlalchemy import Index, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    listings_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    listings_new: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["Source"] = relationship(back_populates="scrape_runs")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_scrape_runs_source_id", "source_id"),
        Index("ix_scrape_runs_started", "started_at"),
    )
