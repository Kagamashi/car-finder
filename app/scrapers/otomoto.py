import json
import re
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
    """Scraper for otomoto.pl (Next.js, data in __NEXT_DATA__ script tag).

    OTOMOTO renders listing data server-side via Next.js. The full JSON state
    is embedded in a <script id="__NEXT_DATA__"> tag on every search results page.

    Data path: props.pageProps.data.advertSearch.edges[*].node
    Pagination: props.pageProps.data.advertSearch.pageInfo.hasNextPage
    """

    source_slug = "otomoto"
    BASE_URL = "https://www.otomoto.pl/osobowe"
    MAX_PAGES = 50  # OTOMOTO typically has 32 items/page; 50 pages = ~1600 listings

    def __init__(self, session: httpx.AsyncClient, query_params: dict | None = None) -> None:
        super().__init__(session)
        self._query_params = query_params or {}
        self._last_page_info: dict = {}

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

    def parse_page(self, raw: bytes) -> list[dict]:
        soup = BeautifulSoup(raw, "lxml")
        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script_tag or not script_tag.string:
            raise ScraperError("__NEXT_DATA__ script tag not found or empty")

        try:
            data = json.loads(script_tag.string)
        except json.JSONDecodeError as exc:
            raise ScraperError(f"Failed to parse __NEXT_DATA__ JSON: {exc}") from exc

        advert_search = (
            data.get("props", {})
            .get("pageProps", {})
            .get("data", {})
            .get("advertSearch", {})
        )
        self._last_page_info = advert_search.get("pageInfo", {})
        edges = advert_search.get("edges", [])
        return [edge["node"] for edge in edges if "node" in edge]

    def has_next_page(self, raw: bytes, page: int) -> bool:
        return bool(self._last_page_info.get("hasNextPage", False)) and page < self.MAX_PAGES

    def normalize_item(self, raw_item: dict) -> ListingCreate:
        # Build parameters lookup: {key: value}
        params = {
            p.get("key", ""): p.get("value", {}).get("key") or p.get("displayValue", "")
            for p in raw_item.get("parameters", [])
            if p.get("key")
        }

        # Price
        price_data = raw_item.get("price", {}) or {}
        price_amount = price_data.get("amount", {}) or {}
        price_raw = price_amount.get("units")
        try:
            price = Decimal(str(price_raw)) if price_raw is not None else None
        except InvalidOperation:
            price = None

        currency = (
            (price_data.get("currency", {}) or {}).get("code", "PLN") or "PLN"
        )

        # Mileage — "150 000 km" → 150000
        mileage_raw = params.get("mileage") or raw_item.get("mileage")
        mileage_km: int | None = None
        if mileage_raw:
            digits = re.sub(r"[^\d]", "", str(mileage_raw))
            mileage_km = int(digits) if digits else None

        # Year
        year_raw = params.get("year") or raw_item.get("year")
        try:
            year = int(year_raw) if year_raw else None
        except (ValueError, TypeError):
            year = None

        # Location
        location_data = raw_item.get("location", {}) or {}
        city = (location_data.get("city", {}) or {}).get("name")
        region = (location_data.get("region", {}) or {}).get("name")
        location = city or region

        # Brand / model from category path or title
        category = raw_item.get("category", {}) or {}
        brand: str | None = None
        model: str | None = None

        # OTOMOTO nests category: {id, name, ...} — the breadcrumb is in the path
        # Try to extract from the normalized URL or category name
        category_path = raw_item.get("categoryPath", []) or []
        if len(category_path) >= 2:
            brand = category_path[1].get("name") if len(category_path) > 1 else category.get("name")
            model = category_path[2].get("name") if len(category_path) > 2 else None
        else:
            brand = params.get("make") or category.get("name")
            model = params.get("model")

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
            fuel_type=normalize_fuel_type(params.get("fuel_type")),
            brand=brand,
            model=model,
            raw_data=raw_item,
        )
