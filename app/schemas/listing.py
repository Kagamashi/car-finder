import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ListingCreate(BaseModel):
    source_slug: str
    url: str
    title: str
    content_hash: str = ""
    price: Decimal | None = None
    currency: str = "PLN"
    location: str | None = None
    mileage_km: int | None = None
    year: int | None = None
    fuel_type: str | None = None
    brand: str | None = None
    model: str | None = None
    raw_data: dict | None = None


class ListingRead(BaseModel):
    id: uuid.UUID
    source_id: int
    url: str
    title: str
    price: Decimal | None
    currency: str
    location: str | None
    mileage_km: int | None
    year: int | None
    fuel_type: str | None
    brand: str | None
    model: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class ListingQuery(BaseModel):
    brand: str | None = None
    model: str | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    year_min: int | None = None
    year_max: int | None = None
    mileage_max: int | None = None
    fuel_type: str | None = None
    source_id: int | None = None
    limit: int = 50
    offset: int = 0


class PaginatedListings(BaseModel):
    total: int
    items: list[ListingRead]
