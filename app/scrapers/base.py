import abc
import asyncio
from collections.abc import AsyncIterator

import httpx

from app.schemas.listing import ListingCreate
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ScraperError(Exception):
    pass


class BaseScraper(abc.ABC):
    """Abstract base for all marketplace scrapers.

    Subclasses must implement `fetch_page`, `parse_page`, and `has_next_page`.
    The `scrape_all` driver handles retry, pagination, and normalization.
    """

    source_slug: str  # must be set by subclass

    REQUEST_TIMEOUT: int = 15
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: list[int] = [2, 5, 10]
    MAX_PAGES: int = 100
    PAGE_DELAY_SECONDS: float = 0.5  # polite rate limiting between pages

    HEADERS: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, session: httpx.AsyncClient) -> None:
        self._session = session

    @abc.abstractmethod
    async def fetch_page(self, page: int) -> bytes:
        """Fetch raw HTML/JSON for a results page. Should raise httpx.HTTPError on failure."""
        ...

    @abc.abstractmethod
    def parse_page(self, raw: bytes) -> list[dict]:
        """Parse raw bytes into a list of raw listing dicts. Side-effects allowed (e.g. store pagination state)."""
        ...

    @abc.abstractmethod
    def has_next_page(self, raw: bytes, page: int) -> bool:
        """Return True if there is at least one more page of results."""
        ...

    @abc.abstractmethod
    def normalize_item(self, raw_item: dict) -> ListingCreate:
        """Convert a source-specific raw dict into a unified ListingCreate."""
        ...

    async def scrape_all(self) -> AsyncIterator[ListingCreate]:
        """Main pagination driver with per-page retry and backoff.

        Yields normalized ListingCreate instances. Stops when has_next_page returns
        False, MAX_PAGES is reached, or 3 consecutive page failures occur.
        """
        page = 1
        consecutive_failures = 0

        while page <= self.MAX_PAGES:
            raw: bytes | None = None

            for attempt in range(self.MAX_RETRIES):
                try:
                    raw = await self.fetch_page(page)
                    break
                except Exception as exc:
                    wait = self.RETRY_BACKOFF[min(attempt, len(self.RETRY_BACKOFF) - 1)]
                    logger.warning(
                        "scraper_page_fetch_failed",
                        source=self.source_slug,
                        page=page,
                        attempt=attempt + 1,
                        error=str(exc),
                        retry_in=wait,
                    )
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(wait)

            if raw is None:
                consecutive_failures += 1
                logger.error(
                    "scraper_page_exhausted_retries",
                    source=self.source_slug,
                    page=page,
                    consecutive_failures=consecutive_failures,
                )
                if consecutive_failures >= 3:
                    logger.error(
                        "scraper_aborting",
                        source=self.source_slug,
                        reason="too_many_consecutive_failures",
                    )
                    break
                page += 1
                continue

            consecutive_failures = 0

            try:
                raw_items = self.parse_page(raw)
            except Exception as exc:
                logger.error(
                    "scraper_parse_failed",
                    source=self.source_slug,
                    page=page,
                    error=str(exc),
                )
                page += 1
                continue

            logger.info(
                "scraper_page_scraped",
                source=self.source_slug,
                page=page,
                items=len(raw_items),
            )

            for raw_item in raw_items:
                try:
                    yield self.normalize_item(raw_item)
                except Exception as exc:
                    logger.warning(
                        "scraper_normalize_failed",
                        source=self.source_slug,
                        error=str(exc),
                    )

            if not self.has_next_page(raw, page):
                break

            page += 1
            await asyncio.sleep(self.PAGE_DELAY_SECONDS)
