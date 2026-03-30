"""Celery tasks for sending notifications."""
import asyncio
import uuid

from app.tasks.celery_app import celery_app
from app.utils.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.notify_matching_filters",
    max_retries=5,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def notify_matching_filters(self, listing_id_str: str) -> dict:
    """For a newly inserted listing, find all matching filters and send email notifications.

    Idempotent: notification_log UNIQUE(filter_id, listing_id) prevents duplicate sends
    even if this task is retried or executed concurrently.
    """
    return asyncio.run(_notify_matching_filters_async(listing_id_str))


async def _notify_matching_filters_async(listing_id_str: str) -> dict:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.config import settings
    from app.models.listing import Listing
    from app.services import filter_service, notification_service
    from sqlalchemy import select

    session_factory = async_sessionmaker(
        create_async_engine(settings.DATABASE_URL, poolclass=NullPool),
        expire_on_commit=False,
    )

    listing_id = uuid.UUID(listing_id_str)
    sent_count = 0
    skipped_count = 0

    async with session_factory() as db:
        result = await db.execute(select(Listing).where(Listing.id == listing_id))
        listing = result.scalar_one_or_none()

        if listing is None:
            logger.warning("notify_listing_not_found", listing_id=listing_id_str)
            return {"sent": 0, "skipped": 0, "error": "listing_not_found"}

        matching_filters = await filter_service.get_matching_filters(db, listing)

        for filter_obj in matching_filters:
            try:
                was_sent = await notification_service.send_listing_notification(
                    db, filter_obj, listing
                )
                if was_sent:
                    sent_count += 1
                else:
                    skipped_count += 1
            except Exception as exc:
                logger.error(
                    "notify_filter_error",
                    filter_id=str(filter_obj.id),
                    listing_id=listing_id_str,
                    error=str(exc),
                )

        await db.commit()

    logger.info(
        "notify_complete",
        listing_id=listing_id_str,
        sent=sent_count,
        skipped=skipped_count,
    )
    return {"sent": sent_count, "skipped": skipped_count}
