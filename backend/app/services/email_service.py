"""
Outgoing email.

Sends through SMTP when ``SMTP_HOST`` is configured. Without it, in DEBUG mode
(local development) the message is written to the application log instead, so
flows such as password reset stay usable without a mail server. Outside DEBUG
the body is never logged: a reset link is a credential, and logs travel far.
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_sync(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email. Returns False (and logs) on failure rather than raising."""
    if not settings.SMTP_HOST:
        if settings.DEBUG:
            logger.warning("SMTP not configured -- email to %s not sent.\nSubject: %s\n\n%s", to, subject, body)
        else:
            logger.error("SMTP not configured -- email %r was not sent. Set SMTP_HOST to deliver email.", subject)
        return False
    try:
        await asyncio.to_thread(_send_sync, to, subject, body)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False
