"""Unit tests for the content hash utility."""
from decimal import Decimal

from app.utils.hashing import compute_content_hash


def test_hash_is_deterministic():
    h1 = compute_content_hash("Toyota Corolla 2020", Decimal("45000"), 120000)
    h2 = compute_content_hash("Toyota Corolla 2020", Decimal("45000"), 120000)
    assert h1 == h2


def test_hash_is_64_chars():
    h = compute_content_hash("Test", Decimal("1000"), 50000)
    assert len(h) == 64


def test_different_price_yields_different_hash():
    h1 = compute_content_hash("Toyota Corolla", Decimal("45000"), 100000)
    h2 = compute_content_hash("Toyota Corolla", Decimal("46000"), 100000)
    assert h1 != h2


def test_different_mileage_yields_different_hash():
    h1 = compute_content_hash("Toyota Corolla", Decimal("45000"), 100000)
    h2 = compute_content_hash("Toyota Corolla", Decimal("45000"), 100001)
    assert h1 != h2


def test_title_case_insensitive():
    h1 = compute_content_hash("Toyota Corolla", Decimal("45000"), 100000)
    h2 = compute_content_hash("TOYOTA COROLLA", Decimal("45000"), 100000)
    assert h1 == h2


def test_none_values_handled():
    h = compute_content_hash("Test listing", None, None)
    assert isinstance(h, str)
    assert len(h) == 64


def test_title_whitespace_stripped():
    h1 = compute_content_hash("  Toyota  ", Decimal("10000"), 50000)
    h2 = compute_content_hash("Toyota", Decimal("10000"), 50000)
    assert h1 == h2
