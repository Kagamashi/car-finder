import json
from decimal import Decimal, InvalidOperation

import httpx
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScraperError
from app.scrapers.normalizer import normalize_fuel_type
from app.schemas.listing import ListingCreate
from app.utils.hashing import compute_content_hash
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OtomotoScraper(BaseScraper):
    """Scraper for otomoto.pl.

    OTOMOTO uses Next.js with urql (GraphQL client). Listing data is embedded in
    __NEXT_DATA__ → props.pageProps.urqlState → the entry containing 'advertSearch'
    → inner JSON string → advertSearch.edges[*].node.

    Pagination: page query param, stop when currentOffset + pageSize >= totalCount.
    """

    source_slug = "otomoto"
    BASE_URL = "https://www.otomoto.pl/osobowe"
    MAX_PAGES = 50

    def __init__(self, session: httpx.AsyncClient, query_params: dict | None = None) -> None:
        super().__init__(session)
        self._query_params = query_params or {}
        self._total_count: int = 0
        self._page_size: int = 32
        self._current_offset: int = 0

    async def fetch_page(self, page: int) -> bytes:
        params = {"page": page, **self._query_params}
        try:
            response = await self._session.get(
                self.BASE_URL,
                params=params,
                headers=self.HEADERS,
                timeout=self.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as exc:
            raise ScraperError(f"HTTP {exc.response.status_code} on page {page}") from exc
        except httpx.RequestError as exc:
            raise ScraperError(f"Request failed on page {page}: {exc}") from exc

    def _extract_advert_search(self, raw: bytes) -> dict:
        """Extract the advertSearch GraphQL cache entry from __NEXT_DATA__."""
        soup = BeautifulSoup(raw, "lxml")
        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script_tag or not script_tag.string:
            raise ScraperError("__NEXT_DATA__ script tag not found or empty")

        try:
            page_data = json.loads(script_tag.string)
        except json.JSONDecodeError as exc:
            raise ScraperError(f"Failed to parse __NEXT_DATA__ JSON: {exc}") from exc

        urql_state = (
            page_data.get("props", {})
            .get("pageProps", {})
            .get("urqlState", {})
        )

        for entry in urql_state.values():
            try:
                inner = json.loads(entry.get("data", "{}"))
            except (json.JSONDecodeError, AttributeError):
                continue
            if "advertSearch" in inner:
                return inner["advertSearch"]

        raise ScraperError("advertSearch not found in urqlState")

    def parse_page(self, raw: bytes) -> list[dict]:
        advert_search = self._extract_advert_search(raw)

        page_info = advert_search.get("pageInfo", {})
        self._total_count = advert_search.get("totalCount", 0)
        self._page_size = page_info.get("pageSize", 32)
        self._current_offset = page_info.get("currentOffset", 0)

        edges = advert_search.get("edges", [])
        return [edge["node"] for edge in edges if "node" in edge]

    def has_next_page(self, raw: bytes, page: int) -> bool:
        next_offset = self._current_offset + self._page_size
        return next_offset < self._total_count and page < self.MAX_PAGES

    def normalize_item(self, raw_item: dict) -> ListingCreate:
        # Parameters lookup: {key: value} — value is already normalized (e.g. "electric", "2023")
        params = {p["key"]: p for p in raw_item.get("parameters", []) if p.get("key")}

        def param_val(key: str) -> str | None:
            return params[key]["value"] if key in params else None

        def param_display(key: str) -> str | None:
            return params[key]["displayValue"] if key in params else None

        # Price
        price_data = (raw_item.get("price") or {}).get("amount") or {}
        price_raw = price_data.get("units")
        try:
            price = Decimal(str(price_raw)) if price_raw is not None else None
        except InvalidOperation:
            price = None
        currency = price_data.get("currencyCode", "PLN") or "PLN"

        # Mileage — value is a plain number string e.g. "18000"
        mileage_raw = param_val("mileage")
        try:
            mileage_km = int(mileage_raw) if mileage_raw else None
        except (ValueError, TypeError):
            mileage_km = None

        # Year
        year_raw = param_val("year")
        try:
            year = int(year_raw) if year_raw else None
        except (ValueError, TypeError):
            year = None

        # Location
        location_data = raw_item.get("location") or {}
        city = (location_data.get("city") or {}).get("name")
        region = (location_data.get("region") or {}).get("name")
        location = city or region

        # Brand / model from parameters
        brand = param_display("make")
        model = param_display("model")

        # Fuel type — value is already English e.g. "electric", "diesel"
        fuel_type = normalize_fuel_type(param_val("fuel_type"))

        title = raw_item.get("title", "")
        url = raw_item.get("url", "")
        content_hash = compute_content_hash(title, price, mileage_km)

        return ListingCreate(
            source_slug=self.source_slug,
            url=url,
            title=title,
            content_hash=content_hash,
            price=price,
            currency=currency,
            location=location,
            mileage_km=mileage_km,
            year=year,
            fuel_type=fuel_type,
            brand=brand,
            model=model,
            raw_data=raw_item,
        )
