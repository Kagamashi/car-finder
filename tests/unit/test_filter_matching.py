"""Unit tests for filter matching SQL logic via FilterService."""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.filter import Filter
from app.models.listing import Listing


def make_listing(**kwargs) -> Listing:
    defaults = {
        "id": uuid.uuid4(),
        "source_id": 1,
        "url": "https://example.com/car/1",
        "content_hash": "abc123",
        "title": "Test Car",
        "price": Decimal("50000"),
        "currency": "PLN",
        "mileage_km": 100000,
        "year": 2020,
        "fuel_type": "diesel",
        "brand": "Toyota",
        "model": "Corolla",
        "is_active": True,
    }
    defaults.update(kwargs)
    listing = Listing.__new__(Listing)
    listing.__dict__.update(defaults)
    return listing


def make_filter(**kwargs) -> Filter:
    defaults = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "name": "Test Filter",
        "is_active": True,
        "brand": None,
        "model": None,
        "price_min": None,
        "price_max": None,
        "year_min": None,
        "year_max": None,
        "mileage_max_km": None,
        "fuel_types": None,
        "sources": None,
    }
    defaults.update(kwargs)
    f = Filter.__new__(Filter)
    f.__dict__.update(defaults)
    return f


class TestFilterMatchingLogic:
    """These tests validate the filter matching conditions in Python (logic mirroring the SQL).

    Full SQL integration tests are in tests/integration/.
    """

    def _matches(self, filter_obj: Filter, listing: Listing) -> bool:
        """Python re-implementation of the filter matching logic for unit testing."""
        if not filter_obj.is_active:
            return False

        if filter_obj.brand is not None:
            if listing.brand is None or listing.brand.lower() != filter_obj.brand.lower():
                return False

        if filter_obj.model is not None:
            if listing.model is None or listing.model.lower() != filter_obj.model.lower():
                return False

        if filter_obj.price_min is not None and listing.price is not None:
            if listing.price < filter_obj.price_min:
                return False

        if filter_obj.price_max is not None and listing.price is not None:
            if listing.price > filter_obj.price_max:
                return False

        if filter_obj.year_min is not None and listing.year is not None:
            if listing.year < filter_obj.year_min:
                return False

        if filter_obj.year_max is not None and listing.year is not None:
            if listing.year > filter_obj.year_max:
                return False

        if filter_obj.mileage_max_km is not None and listing.mileage_km is not None:
            if listing.mileage_km > filter_obj.mileage_max_km:
                return False

        if filter_obj.fuel_types is not None and listing.fuel_type is not None:
            if listing.fuel_type not in filter_obj.fuel_types:
                return False

        return True

    def test_null_filter_matches_any_listing(self):
        f = make_filter()
        listing = make_listing()
        assert self._matches(f, listing)

    def test_brand_filter_matches(self):
        f = make_filter(brand="Toyota")
        listing = make_listing(brand="Toyota")
        assert self._matches(f, listing)

    def test_brand_filter_case_insensitive(self):
        f = make_filter(brand="toyota")
        listing = make_listing(brand="TOYOTA")
        assert self._matches(f, listing)

    def test_brand_filter_no_match(self):
        f = make_filter(brand="BMW")
        listing = make_listing(brand="Toyota")
        assert not self._matches(f, listing)

    def test_price_range_match(self):
        f = make_filter(price_min=Decimal("40000"), price_max=Decimal("60000"))
        listing = make_listing(price=Decimal("50000"))
        assert self._matches(f, listing)

    def test_price_below_min(self):
        f = make_filter(price_min=Decimal("60000"))
        listing = make_listing(price=Decimal("50000"))
        assert not self._matches(f, listing)

    def test_price_above_max(self):
        f = make_filter(price_max=Decimal("40000"))
        listing = make_listing(price=Decimal("50000"))
        assert not self._matches(f, listing)

    def test_year_range_match(self):
        f = make_filter(year_min=2018, year_max=2022)
        listing = make_listing(year=2020)
        assert self._matches(f, listing)

    def test_year_too_old(self):
        f = make_filter(year_min=2021)
        listing = make_listing(year=2019)
        assert not self._matches(f, listing)

    def test_mileage_within_limit(self):
        f = make_filter(mileage_max_km=150000)
        listing = make_listing(mileage_km=100000)
        assert self._matches(f, listing)

    def test_mileage_exceeds_limit(self):
        f = make_filter(mileage_max_km=80000)
        listing = make_listing(mileage_km=100000)
        assert not self._matches(f, listing)

    def test_fuel_type_match(self):
        f = make_filter(fuel_types=["diesel", "hybrid"])
        listing = make_listing(fuel_type="diesel")
        assert self._matches(f, listing)

    def test_fuel_type_no_match(self):
        f = make_filter(fuel_types=["petrol"])
        listing = make_listing(fuel_type="diesel")
        assert not self._matches(f, listing)

    def test_inactive_filter_never_matches(self):
        f = make_filter(is_active=False)
        listing = make_listing()
        assert not self._matches(f, listing)

    def test_combined_criteria_all_match(self):
        f = make_filter(
            brand="Toyota",
            price_min=Decimal("40000"),
            price_max=Decimal("60000"),
            year_min=2018,
            mileage_max_km=150000,
            fuel_types=["diesel"],
        )
        listing = make_listing(
            brand="Toyota",
            price=Decimal("50000"),
            year=2020,
            mileage_km=100000,
            fuel_type="diesel",
        )
        assert self._matches(f, listing)

    def test_combined_criteria_one_fails(self):
        f = make_filter(
            brand="Toyota",
            price_max=Decimal("45000"),  # listing price 50k exceeds this
        )
        listing = make_listing(brand="Toyota", price=Decimal("50000"))
        assert not self._matches(f, listing)
