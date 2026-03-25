"""Unit tests for the scraper normalizer and OtomotoScraper.normalize_item."""
from unittest.mock import MagicMock, patch

import pytest

from app.scrapers.normalizer import normalize_fuel_type
from app.scrapers.otomoto import OtomotoScraper


# ── Fuel type normalization ────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("benzyna", "petrol"),
    ("Diesel", "diesel"),
    ("elektryczny", "electric"),
    ("hybryda", "hybrid"),
    ("LPG", "lpg"),
    ("unknown_fuel", "unknown_fuel"),  # pass-through unknown values
    (None, None),
])
def test_normalize_fuel_type(raw, expected):
    assert normalize_fuel_type(raw) == expected


# ── OtomotoScraper.normalize_item ─────────────────────────────────────────────

OTOMOTO_SAMPLE_NODE = {
    "title": "Toyota Corolla 1.8 HSD",
    "url": "https://www.otomoto.pl/osobowe/oferta/toyota-corolla-ID6abc.html",
    "price": {
        "amount": {"units": 75000},
        "currency": {"code": "PLN"},
    },
    "parameters": [
        {"key": "mileage", "displayValue": "120 000 km"},
        {"key": "year", "displayValue": "2021", "value": {"key": "2021"}},
        {"key": "fuel_type", "displayValue": "Hybryda", "value": {"key": "hybryda"}},
        {"key": "make", "displayValue": "Toyota", "value": {"key": "toyota"}},
        {"key": "model", "displayValue": "Corolla", "value": {"key": "corolla"}},
    ],
    "location": {
        "city": {"name": "Warszawa"},
        "region": {"name": "Mazowieckie"},
    },
    "categoryPath": [
        {"name": "Osobowe"},
        {"name": "Toyota"},
        {"name": "Corolla"},
    ],
}


@pytest.fixture
def scraper():
    mock_session = MagicMock()
    return OtomotoScraper(mock_session)


def test_normalize_item_basic_fields(scraper):
    result = scraper.normalize_item(OTOMOTO_SAMPLE_NODE)
    assert result.title == "Toyota Corolla 1.8 HSD"
    assert result.url == "https://www.otomoto.pl/osobowe/oferta/toyota-corolla-ID6abc.html"
    assert result.source_slug == "otomoto"


def test_normalize_item_price(scraper):
    result = scraper.normalize_item(OTOMOTO_SAMPLE_NODE)
    from decimal import Decimal
    assert result.price == Decimal("75000")
    assert result.currency == "PLN"


def test_normalize_item_mileage(scraper):
    result = scraper.normalize_item(OTOMOTO_SAMPLE_NODE)
    assert result.mileage_km == 120000


def test_normalize_item_year(scraper):
    result = scraper.normalize_item(OTOMOTO_SAMPLE_NODE)
    assert result.year == 2021


def test_normalize_item_fuel_type_normalized(scraper):
    result = scraper.normalize_item(OTOMOTO_SAMPLE_NODE)
    assert result.fuel_type == "hybrid"


def test_normalize_item_location(scraper):
    result = scraper.normalize_item(OTOMOTO_SAMPLE_NODE)
    assert result.location == "Warszawa"


def test_normalize_item_brand_model_from_category_path(scraper):
    result = scraper.normalize_item(OTOMOTO_SAMPLE_NODE)
    assert result.brand == "Toyota"
    assert result.model == "Corolla"


def test_normalize_item_content_hash_set(scraper):
    result = scraper.normalize_item(OTOMOTO_SAMPLE_NODE)
    assert len(result.content_hash) == 64


def test_normalize_item_missing_price(scraper):
    node = {**OTOMOTO_SAMPLE_NODE, "price": None}
    result = scraper.normalize_item(node)
    assert result.price is None


def test_normalize_item_missing_mileage(scraper):
    node = {
        **OTOMOTO_SAMPLE_NODE,
        "parameters": [p for p in OTOMOTO_SAMPLE_NODE["parameters"] if p["key"] != "mileage"],
    }
    result = scraper.normalize_item(node)
    assert result.mileage_km is None
