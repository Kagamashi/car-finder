"""Integration tests for the /listings FastAPI endpoints."""
import uuid
from decimal import Decimal

import pytest

from app.schemas.listing import ListingCreate
from app.services import listing_service
from app.utils.hashing import compute_content_hash


async def insert_listing(db, **kwargs) -> None:
    title = kwargs.get("title", "Test Car")
    price = kwargs.get("price", Decimal("50000"))
    mileage_km = kwargs.get("mileage_km", 100000)
    lc = ListingCreate(
        source_slug="otomoto",
        url=kwargs.get("url", f"https://www.otomoto.pl/oferta/{uuid.uuid4()}.html"),
        title=title,
        content_hash=compute_content_hash(title, price, mileage_km),
        price=price,
        mileage_km=mileage_km,
        year=kwargs.get("year", 2021),
        fuel_type=kwargs.get("fuel_type", "petrol"),
        brand=kwargs.get("brand", "Volkswagen"),
        model=kwargs.get("model", "Golf"),
    )
    await listing_service.upsert_listing(db, lc)


@pytest.mark.asyncio
async def test_list_listings_returns_200(client, db, seed_source):
    await insert_listing(db)
    response = await client.get("/listings")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_listings_brand_filter(client, db, seed_source):
    await insert_listing(db, brand="Mercedes", model="C-Class")
    response = await client.get("/listings", params={"brand": "Mercedes"})
    assert response.status_code == 200
    data = response.json()
    assert all(item["brand"] == "Mercedes" for item in data["items"])


@pytest.mark.asyncio
async def test_list_listings_pagination(client, db, seed_source):
    for i in range(5):
        await insert_listing(db, url=f"https://www.otomoto.pl/oferta/page-test-{uuid.uuid4()}.html")

    response = await client.get("/listings", params={"limit": 2, "offset": 0})
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_get_listing_by_id(client, db, seed_source):
    url = f"https://www.otomoto.pl/oferta/{uuid.uuid4()}.html"
    await insert_listing(db, url=url, brand="Audi", model="A4")

    # First get from listing list to retrieve the ID
    response = await client.get("/listings", params={"brand": "Audi", "model": "A4"})
    items = response.json()["items"]
    listing_id = next(item["id"] for item in items if item["brand"] == "Audi")

    detail_response = await client.get(f"/listings/{listing_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["brand"] == "Audi"


@pytest.mark.asyncio
async def test_get_listing_not_found(client, db, seed_source):
    response = await client.get(f"/listings/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_listings_limit_max_200(client, db, seed_source):
    response = await client.get("/listings", params={"limit": 500})
    assert response.status_code == 422  # FastAPI validation error for limit > 200


@pytest.mark.asyncio
async def test_create_user_and_filter(client, db, seed_source):
    # Create user
    response = await client.post("/users", json={"email": f"test-{uuid.uuid4()}@example.com"})
    assert response.status_code == 201
    user_id = response.json()["id"]

    # Create filter for user
    filter_payload = {
        "name": "My Toyota Filter",
        "brand": "Toyota",
        "price_max": 80000,
        "year_min": 2018,
        "fuel_types": ["hybrid", "petrol"],
    }
    response = await client.post(f"/users/{user_id}/filters", json=filter_payload)
    assert response.status_code == 201
    filter_data = response.json()
    assert filter_data["brand"] == "Toyota"
    assert filter_data["fuel_types"] == ["hybrid", "petrol"]

    # List filters
    response = await client.get(f"/users/{user_id}/filters")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_health_endpoint(client, db, seed_source):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "db" in data
    assert "redis" in data
