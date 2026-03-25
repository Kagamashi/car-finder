import hashlib
from decimal import Decimal


def compute_content_hash(title: str, price: Decimal | None, mileage_km: int | None) -> str:
    """Compute a deterministic SHA-256 hash from listing's key identity fields.

    Used as a secondary deduplication key (URL is primary).
    Catches the same car reposted with a new URL or appearing on multiple sources.
    """
    raw = f"{(title or '').strip().lower()}|{price or ''}|{mileage_km or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()
