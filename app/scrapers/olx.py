"""OLX scraper stub — to be implemented in a future iteration."""
import httpx

from app.scrapers.base import BaseScraper
from app.schemas.listing import ListingCreate


class OlxScraper(BaseScraper):
    source_slug = "olx"
    BASE_URL = "https://www.olx.pl/motoryzacja/samochody"

    def __init__(self, session: httpx.AsyncClient) -> None:
        super().__init__(session)

    async def fetch_page(self, page: int) -> bytes:
        raise NotImplementedError("OLX scraper not yet implemented")

    def parse_page(self, raw: bytes) -> list[dict]:
        raise NotImplementedError("OLX scraper not yet implemented")

    def has_next_page(self, raw: bytes, page: int) -> bool:
        raise NotImplementedError("OLX scraper not yet implemented")

    def normalize_item(self, raw_item: dict) -> ListingCreate:
        raise NotImplementedError("OLX scraper not yet implemented")
