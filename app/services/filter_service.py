import uuid

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.filter import Filter
from app.models.listing import Listing
from app.schemas.filter import FilterCreate, FilterUpdate
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def create_filter(db: AsyncSession, user_id: uuid.UUID, data: FilterCreate) -> Filter:
    f = Filter(
        id=uuid.uuid4(),
        user_id=user_id,
        name=data.name,
        brand=data.brand,
        model=data.model,
        price_min=data.price_min,
        price_max=data.price_max,
        year_min=data.year_min,
        year_max=data.year_max,
        mileage_max_km=data.mileage_max_km,
        fuel_types=data.fuel_types,
        sources=data.sources,
    )
    db.add(f)
    await db.flush()
    return f


async def get_filters_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Filter]:
    result = await db.execute(select(Filter).where(Filter.user_id == user_id))
    return list(result.scalars().all())


async def get_filter(db: AsyncSession, filter_id: uuid.UUID) -> Filter | None:
    result = await db.execute(select(Filter).where(Filter.id == filter_id))
    return result.scalar_one_or_none()


async def update_filter(db: AsyncSession, f: Filter, data: FilterUpdate) -> Filter:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(f, field, value)
    await db.flush()
    return f


async def delete_filter(db: AsyncSession, f: Filter) -> None:
    f.is_active = False
    await db.flush()


async def get_matching_filters(db: AsyncSession, listing: Listing) -> list[Filter]:
    """Return all active filters that match the given listing.

    All conditions use OR(field IS NULL, match_condition) so that NULL means "any".
    Runs entirely in PostgreSQL — no Python-side filtering needed.
    """
    stmt = select(Filter).where(Filter.is_active == True)  # noqa: E712

    # Brand matching (case-insensitive)
    if listing.brand:
        stmt = stmt.where(
            or_(Filter.brand == None, Filter.brand.ilike(listing.brand))  # noqa: E711
        )
    else:
        stmt = stmt.where(Filter.brand == None)  # noqa: E711

    # Model matching (case-insensitive)
    if listing.model:
        stmt = stmt.where(
            or_(Filter.model == None, Filter.model.ilike(listing.model))  # noqa: E711
        )
    else:
        stmt = stmt.where(Filter.model == None)  # noqa: E711

    # Price range
    if listing.price is not None:
        stmt = stmt.where(
            or_(Filter.price_min == None, Filter.price_min <= listing.price)  # noqa: E711
        )
        stmt = stmt.where(
            or_(Filter.price_max == None, Filter.price_max >= listing.price)  # noqa: E711
        )

    # Year range
    if listing.year is not None:
        stmt = stmt.where(
            or_(Filter.year_min == None, Filter.year_min <= listing.year)  # noqa: E711
        )
        stmt = stmt.where(
            or_(Filter.year_max == None, Filter.year_max >= listing.year)  # noqa: E711
        )

    # Mileage max
    if listing.mileage_km is not None:
        stmt = stmt.where(
            or_(Filter.mileage_max_km == None, Filter.mileage_max_km >= listing.mileage_km)  # noqa: E711
        )

    # Fuel type array overlap: filter.fuel_types && ARRAY[listing.fuel_type]
    if listing.fuel_type:
        stmt = stmt.where(
            or_(
                Filter.fuel_types == None,  # noqa: E711
                Filter.fuel_types.overlap(array([listing.fuel_type])),
            )
        )

    # Source filter: filter.sources && ARRAY[listing.source_id]
    stmt = stmt.where(
        or_(
            Filter.sources == None,  # noqa: E711
            Filter.sources.overlap(array([listing.source_id])),
        )
    )

    result = await db.execute(stmt)
    matched = list(result.scalars().all())
    logger.info(
        "filter_match",
        listing_id=str(listing.id),
        matched_filters=len(matched),
    )
    return matched
