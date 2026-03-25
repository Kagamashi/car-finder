import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing
from app.models.source import Source
from app.schemas.listing import ListingCreate, ListingQuery
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def get_source_id(db: AsyncSession, slug: str) -> int:
    result = await db.execute(select(Source.id).where(Source.slug == slug))
    source_id = result.scalar_one_or_none()
    if source_id is None:
        raise ValueError(f"Unknown source slug: {slug!r}")
    return source_id


async def upsert_listing(
    db: AsyncSession, listing_create: ListingCreate
) -> tuple[Listing, bool]:
    """Insert a new listing or update an existing one.

    Returns (listing, is_new) where is_new=True means this listing was just inserted.

    Deduplication logic:
    1. Check by URL (primary key): if found, update last_seen_at and return is_new=False.
    2. Check by content_hash (secondary): if found but different URL, log collision and still insert.
    3. Insert new row.
    """
    # Step 1: URL check
    result = await db.execute(select(Listing).where(Listing.url == listing_create.url))
    existing = result.scalar_one_or_none()

    if existing is not None:
        existing.last_seen_at = datetime.now(tz=timezone.utc)
        existing.is_active = True
        if existing.content_hash != listing_create.content_hash:
            # Price or mileage changed on the same listing URL
            existing.content_hash = listing_create.content_hash
            existing.price = listing_create.price
            existing.mileage_km = listing_create.mileage_km
            logger.info(
                "listing_updated",
                url=listing_create.url,
                new_hash=listing_create.content_hash,
            )
        await db.flush()
        return existing, False

    # Step 2: Content hash check (cross-source/repost detection)
    result = await db.execute(
        select(Listing).where(Listing.content_hash == listing_create.content_hash)
    )
    collision = result.scalar_one_or_none()
    if collision is not None:
        logger.info(
            "listing_hash_collision",
            new_url=listing_create.url,
            existing_url=collision.url,
            content_hash=listing_create.content_hash,
        )
        # Still insert — different URL is a distinct listing entry

    # Step 3: Insert new
    source_id = await get_source_id(db, listing_create.source_slug)
    new_listing = Listing(
        id=uuid.uuid4(),
        source_id=source_id,
        url=listing_create.url,
        content_hash=listing_create.content_hash,
        title=listing_create.title,
        price=listing_create.price,
        currency=listing_create.currency,
        location=listing_create.location,
        mileage_km=listing_create.mileage_km,
        year=listing_create.year,
        fuel_type=listing_create.fuel_type,
        brand=listing_create.brand,
        model=listing_create.model,
        raw_data=listing_create.raw_data,
    )
    db.add(new_listing)
    await db.flush()
    logger.info("listing_inserted", url=listing_create.url, listing_id=str(new_listing.id))
    return new_listing, True


async def query_listings(db: AsyncSession, query: ListingQuery) -> tuple[int, list[Listing]]:
    """Return (total_count, page_items) matching the given query params."""
    stmt = select(Listing).where(Listing.is_active == True)  # noqa: E712

    if query.brand:
        stmt = stmt.where(func.lower(Listing.brand) == query.brand.lower())
    if query.model:
        stmt = stmt.where(func.lower(Listing.model) == query.model.lower())
    if query.price_min is not None:
        stmt = stmt.where(Listing.price >= query.price_min)
    if query.price_max is not None:
        stmt = stmt.where(Listing.price <= query.price_max)
    if query.year_min is not None:
        stmt = stmt.where(Listing.year >= query.year_min)
    if query.year_max is not None:
        stmt = stmt.where(Listing.year <= query.year_max)
    if query.mileage_max is not None:
        stmt = stmt.where(Listing.mileage_km <= query.mileage_max)
    if query.fuel_type:
        stmt = stmt.where(Listing.fuel_type == query.fuel_type)
    if query.source_id is not None:
        stmt = stmt.where(Listing.source_id == query.source_id)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar_one()

    items_result = await db.execute(
        stmt.order_by(Listing.first_seen_at.desc())
        .limit(min(query.limit, 200))
        .offset(query.offset)
    )
    items = list(items_result.scalars().all())
    return total, items


async def get_listing_by_id(db: AsyncSession, listing_id: uuid.UUID) -> Listing | None:
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    return result.scalar_one_or_none()
