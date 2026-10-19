"""Without SMTP, email bodies (which can hold reset links) are logged only in DEBUG."""

import logging

import pytest

from app.core.config import settings
from app.services.email_service import send_email


@pytest.mark.asyncio
async def test_body_not_logged_outside_debug(monkeypatch, caplog):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "DEBUG", False)
    with caplog.at_level(logging.INFO):
        sent = await send_email("user@example.com", "Reset", "secret-link-123")
    assert sent is False
    assert "secret-link-123" not in caplog.text
    assert "user@example.com" not in caplog.text
    assert "SMTP not configured" in caplog.text


@pytest.mark.asyncio
async def test_body_logged_in_debug(monkeypatch, caplog):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "DEBUG", True)
    with caplog.at_level(logging.INFO):
        await send_email("user@example.com", "Reset", "secret-link-123")
    assert "secret-link-123" in caplog.text
