import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class FilterCreate(BaseModel):
    name: str
    brand: str | None = None
    model: str | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    year_min: int | None = None
    year_max: int | None = None
    mileage_max_km: int | None = None
    fuel_types: list[str] | None = None
    sources: list[int] | None = None


class FilterUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    brand: str | None = None
    model: str | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    year_min: int | None = None
    year_max: int | None = None
    mileage_max_km: int | None = None
    fuel_types: list[str] | None = None
    sources: list[int] | None = None


class FilterRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    is_active: bool
    brand: str | None
    model: str | None
    price_min: Decimal | None
    price_max: Decimal | None
    year_min: int | None
    year_max: int | None
    mileage_max_km: int | None
    fuel_types: list[str] | None
    sources: list[int] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
