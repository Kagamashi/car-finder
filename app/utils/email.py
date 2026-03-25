import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _send_email_sync(to_address: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_address
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if settings.SMTP_USE_TLS:
        smtp_cls = smtplib.SMTP
        smtp = smtp_cls(settings.SMTP_HOST, settings.SMTP_PORT)
        smtp.starttls()
    else:
        smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

    try:
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.sendmail(settings.SMTP_FROM, [to_address], msg.as_string())
        logger.info("Email sent", to=to_address, subject=subject)
    finally:
        smtp.quit()


async def send_email(to_address: str, subject: str, html_body: str) -> None:
    """Send email asynchronously by running the sync SMTP client in a thread pool."""
    await asyncio.to_thread(_send_email_sync, to_address, subject, html_body)
