"""Integration tests for ListingService deduplication and upsert logic.

Requires a live PostgreSQL test database (see conftest.py).
"""
import uuid
from decimal import Decimal

import pytest

from app.schemas.listing import ListingCreate
from app.services import listing_service
from app.utils.hashing import compute_content_hash


def make_listing_create(**kwargs) -> ListingCreate:
    title = kwargs.pop("title", "Toyota Corolla 2020 1.8 HSD")
    price = kwargs.pop("price", Decimal("55000"))
    mileage_km = kwargs.pop("mileage_km", 80000)
    return ListingCreate(
        source_slug=kwargs.pop("source_slug", "otomoto"),
        url=kwargs.pop("url", f"https://www.otomoto.pl/oferta/{uuid.uuid4()}.html"),
        title=title,
        content_hash=compute_content_hash(title, price, mileage_km),
        price=price,
        mileage_km=mileage_km,
        year=kwargs.pop("year", 2020),
        fuel_type=kwargs.pop("fuel_type", "hybrid"),
        brand=kwargs.pop("brand", "Toyota"),
        model=kwargs.pop("model", "Corolla"),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_upsert_new_listing(db, seed_source):
    lc = make_listing_create()
    listing, is_new = await listing_service.upsert_listing(db, lc)
    assert is_new is True
    assert listing.url == lc.url
    assert listing.price == Decimal("55000")


@pytest.mark.asyncio
async def test_upsert_same_url_is_not_new(db, seed_source):
    lc = make_listing_create()
    listing1, is_new1 = await listing_service.upsert_listing(db, lc)
    listing2, is_new2 = await listing_service.upsert_listing(db, lc)
    assert is_new1 is True
    assert is_new2 is False
    assert listing1.id == listing2.id


@pytest.mark.asyncio
async def test_upsert_same_url_updates_price(db, seed_source):
    lc = make_listing_create(price=Decimal("55000"))
    listing, _ = await listing_service.upsert_listing(db, lc)

    lc_updated = make_listing_create(
        url=lc.url,
        price=Decimal("50000"),
        mileage_km=lc.mileage_km,
        title=lc.title,
    )
    lc_updated.content_hash = compute_content_hash(lc_updated.title, lc_updated.price, lc_updated.mileage_km)
    updated, is_new = await listing_service.upsert_listing(db, lc_updated)
    assert is_new is False
    assert updated.price == Decimal("50000")
    assert updated.id == listing.id


@pytest.mark.asyncio
async def test_different_urls_same_hash_both_inserted(db, seed_source):
    title = "BMW 3 Series 2019"
    price = Decimal("80000")
    mileage_km = 60000
    content_hash = compute_content_hash(title, price, mileage_km)

    lc1 = make_listing_create(
        url="https://www.otomoto.pl/oferta/bmw-3-a.html",
        title=title,
        price=price,
        mileage_km=mileage_km,
    )
    lc1.content_hash = content_hash

    lc2 = make_listing_create(
        url="https://www.otomoto.pl/oferta/bmw-3-b.html",
        title=title,
        price=price,
        mileage_km=mileage_km,
    )
    lc2.content_hash = content_hash

    _, is_new1 = await listing_service.upsert_listing(db, lc1)
    _, is_new2 = await listing_service.upsert_listing(db, lc2)
    assert is_new1 is True
    assert is_new2 is True  # different URL = distinct listing


@pytest.mark.asyncio
async def test_query_listings_by_brand(db, seed_source):
    lc = make_listing_create(brand="BMW", model="5 Series")
    await listing_service.upsert_listing(db, lc)

    from app.schemas.listing import ListingQuery
    q = ListingQuery(brand="BMW")
    total, items = await listing_service.query_listings(db, q)
    assert total >= 1
    assert all(item.brand == "BMW" for item in items)


@pytest.mark.asyncio
async def test_query_listings_price_filter(db, seed_source):
    lc_cheap = make_listing_create(
        url=f"https://www.otomoto.pl/oferta/cheap-{uuid.uuid4()}.html",
        price=Decimal("20000"),
        brand="Fiat",
    )
    lc_expensive = make_listing_create(
        url=f"https://www.otomoto.pl/oferta/expensive-{uuid.uuid4()}.html",
        price=Decimal("200000"),
        brand="Porsche",
    )
    await listing_service.upsert_listing(db, lc_cheap)
    await listing_service.upsert_listing(db, lc_expensive)

    from app.schemas.listing import ListingQuery
    q = ListingQuery(price_max=Decimal("50000"))
    _, items = await listing_service.query_listings(db, q)
    assert all(item.price <= Decimal("50000") for item in items if item.price)
