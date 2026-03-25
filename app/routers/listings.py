import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.listing import ListingQuery, ListingRead, PaginatedListings
from app.services import listing_service

router = APIRouter()

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=PaginatedListings)
async def list_listings(
    db: DB,
    brand: str | None = Query(None),
    model: str | None = Query(None),
    price_min: Decimal | None = Query(None),
    price_max: Decimal | None = Query(None),
    year_min: int | None = Query(None),
    year_max: int | None = Query(None),
    mileage_max: int | None = Query(None),
    fuel_type: str | None = Query(None),
    source_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = ListingQuery(
        brand=brand,
        model=model,
        price_min=price_min,
        price_max=price_max,
        year_min=year_min,
        year_max=year_max,
        mileage_max=mileage_max,
        fuel_type=fuel_type,
        source_id=source_id,
        limit=limit,
        offset=offset,
    )
    total, items = await listing_service.query_listings(db, query)
    return PaginatedListings(total=total, items=items)


@router.get("/{listing_id}", response_model=ListingRead)
async def get_listing(listing_id: uuid.UUID, db: DB):
    listing = await listing_service.get_listing_by_id(db, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing
