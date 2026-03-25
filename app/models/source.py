from sqlalchemy import Boolean, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    listings: Mapped[list["Listing"]] = relationship(back_populates="source")  # type: ignore[name-defined]  # noqa: F821
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(back_populates="source")  # type: ignore[name-defined]  # noqa: F821
