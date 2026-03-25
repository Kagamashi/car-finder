from app.scrapers.base import BaseScraper
from app.scrapers.otomoto import OtomotoScraper

__all__ = ["BaseScraper", "OtomotoScraper"]

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "otomoto": OtomotoScraper,
}
