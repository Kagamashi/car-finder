"""Celery tasks for scraping marketplaces."""
import asyncio
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.scrape_run import ScrapeRun
from app.models.source import Source
from app.scrapers import SCRAPER_REGISTRY
from app.services import listing_service
from app.tasks.celery_app import celery_app
from app.utils.logging import get_logger


def _make_session():
    """Create a fresh engine+session per task using NullPool.

    Required for Celery prefork workers: asyncpg connections are bound to a
    specific event loop. NullPool ensures no connections are shared across
    forked processes.
    """
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    return async_sessionmaker(engine, expire_on_commit=False)

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.scrape_tasks.dispatch_all_sources",
    max_retries=1,
)
def dispatch_all_sources(self):
    """Beat entry-point: dispatch one scrape_source task per active source."""
    asyncio.run(_dispatch_all_sources_async())


async def _dispatch_all_sources_async() -> None:
    from sqlalchemy import select

    async with _make_session()() as db:
        result = await db.execute(select(Source).where(Source.is_active == True))  # noqa: E712
        sources = list(result.scalars().all())

    for source in sources:
        logger.info("dispatching_scrape", source=source.slug)
        scrape_source.delay(source.slug)


@celery_app.task(
    bind=True,
    name="app.tasks.scrape_tasks.scrape_source",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(httpx.HTTPError,),
    retry_backoff=True,
)
def scrape_source(self, source_slug: str) -> dict:
    """Scrape a single source and persist new listings.

    For each new listing found, chains a notify_matching_filters task.
    Updates scrape_run with final status and counts.
    """
    return asyncio.run(_scrape_source_async(source_slug))


async def _scrape_source_async(source_slug: str) -> dict:
    from app.tasks.notification_tasks import notify_matching_filters

    scraper_cls = SCRAPER_REGISTRY.get(source_slug)
    if scraper_cls is None:
        logger.error("unknown_source_slug", source=source_slug)
        return {"status": "failed", "error": f"Unknown source: {source_slug}"}

    # Create scrape run record
    scrape_run_id = uuid.uuid4()
    async with _make_session()() as db:
        from sqlalchemy import select

        source_result = await db.execute(
            select(Source.id).where(Source.slug == source_slug)
        )
        source_id = source_result.scalar_one()

        run = ScrapeRun(
            id=scrape_run_id,
            source_id=source_id,
            status="running",
        )
        db.add(run)
        await db.commit()

    listings_found = 0
    listings_new = 0
    status = "success"
    error_msg = None

    try:
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            scraper = scraper_cls(http_client)

            async with _make_session()() as db:
                async for listing_create in scraper.scrape_all():
                    listings_found += 1
                    try:
                        listing, is_new = await listing_service.upsert_listing(db, listing_create)
                        if is_new:
                            listings_new += 1
                            # Commit first so the notification task can find the listing in DB
                            await db.commit()
                            notify_matching_filters.delay(str(listing.id))
                    except Exception as exc:
                        logger.error(
                            "listing_upsert_failed",
                            source=source_slug,
                            url=listing_create.url,
                            error=str(exc),
                        )
                        await db.rollback()

                await db.commit()

    except Exception as exc:
        status = "partial" if listings_found > 0 else "failed"
        error_msg = str(exc)
        logger.error(
            "scrape_run_error",
            source=source_slug,
            error=error_msg,
            listings_found=listings_found,
        )

    # Update scrape run record
    async with _make_session()() as db:
        from sqlalchemy import select, update

        await db.execute(
            update(ScrapeRun)
            .where(ScrapeRun.id == scrape_run_id)
            .values(
                finished_at=datetime.now(tz=timezone.utc),
                status=status,
                listings_found=listings_found,
                listings_new=listings_new,
                error_msg=error_msg,
            )
        )
        await db.commit()

    logger.info(
        "scrape_run_complete",
        source=source_slug,
        status=status,
        found=listings_found,
        new=listings_new,
    )
    return {
        "source": source_slug,
        "status": status,
        "listings_found": listings_found,
        "listings_new": listings_new,
    }
