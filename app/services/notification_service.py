import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.filter import Filter
from app.models.listing import Listing
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.utils.email import send_email
from app.utils.logging import get_logger

logger = get_logger(__name__)

_template_dir = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_template_dir)), autoescape=True)


async def send_listing_notification(
    db: AsyncSession, filter_obj: Filter, listing: Listing
) -> bool:
    """Send an email notification for a new matching listing.

    Returns True if the notification was sent, False if it was skipped (already sent).
    Uses the notification_log UNIQUE(filter_id, listing_id) constraint as idempotency guard.
    """
    # Check for existing notification (fast path before SMTP attempt)
    existing = await db.execute(
        select(NotificationLog).where(
            NotificationLog.filter_id == filter_obj.id,
            NotificationLog.listing_id == listing.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.info(
            "notification_skipped_duplicate",
            filter_id=str(filter_obj.id),
            listing_id=str(listing.id),
        )
        return False

    # Load user email
    user_result = await db.execute(select(User).where(User.id == filter_obj.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        logger.warning("notification_skipped_no_user", filter_id=str(filter_obj.id))
        return False

    # Render email
    template = _jinja_env.get_template("notification_email.html")
    html_body = template.render(listing=listing, filter_name=filter_obj.name)
    subject = f"Nowe ogłoszenie: {listing.title}"
    if listing.price:
        subject += f" – {int(listing.price)} {listing.currency}"

    # Attempt to send
    status = "sent"
    error_msg = None
    try:
        await send_email(user.email, subject, html_body)
        logger.info(
            "notification_sent",
            to=user.email,
            listing_id=str(listing.id),
            filter_id=str(filter_obj.id),
        )
    except Exception as exc:
        status = "failed"
        error_msg = str(exc)
        logger.error(
            "notification_send_failed",
            to=user.email,
            listing_id=str(listing.id),
            error=error_msg,
        )

    # Record the attempt (success or failure)
    log_entry = NotificationLog(
        id=uuid.uuid4(),
        filter_id=filter_obj.id,
        listing_id=listing.id,
        status=status,
        error_msg=error_msg,
    )
    db.add(log_entry)
    try:
        await db.flush()
    except IntegrityError:
        # Race condition: another task beat us to it — safe to ignore
        await db.rollback()
        logger.info(
            "notification_log_conflict_ignored",
            filter_id=str(filter_obj.id),
            listing_id=str(listing.id),
        )
        return False

    return status == "sent"


async def get_notification_log(
    db: AsyncSession,
    filter_id: uuid.UUID | None = None,
    listing_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[NotificationLog]:
    stmt = select(NotificationLog).order_by(NotificationLog.sent_at.desc())
    if filter_id:
        stmt = stmt.where(NotificationLog.filter_id == filter_id)
    if listing_id:
        stmt = stmt.where(NotificationLog.listing_id == listing_id)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())
