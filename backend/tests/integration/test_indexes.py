"""ensure_indexes: TTL retention for audit logs and password reset tokens."""

import pytest

from app.core.config import settings
from app.db.indexes import ensure_indexes


async def _index_on(db, collection: str, field: str) -> dict:
    async for index in db[collection].list_indexes():
        if dict(index["key"]) == {field: 1}:
            return index
    raise AssertionError(f"no index on {collection}.{field}")


@pytest.mark.asyncio
async def test_creates_ttl_indexes(test_db):
    await ensure_indexes(test_db)

    audit = await _index_on(test_db, "audit_logs", "timestamp")
    assert audit["expireAfterSeconds"] == settings.AUDIT_LOG_RETENTION_DAYS * 24 * 3600
    assert (await _index_on(test_db, "password_resets", "expires_at"))["expireAfterSeconds"] == 0


@pytest.mark.asyncio
async def test_converts_existing_plain_index_and_is_idempotent(test_db, monkeypatch):
    # Databases seeded before retention existed have a plain timestamp index.
    await test_db["audit_logs"].create_index("timestamp")

    await ensure_indexes(test_db)
    await ensure_indexes(test_db)
    assert "expireAfterSeconds" in await _index_on(test_db, "audit_logs", "timestamp")

    monkeypatch.setattr(settings, "AUDIT_LOG_RETENTION_DAYS", 30)
    await ensure_indexes(test_db)
    assert (await _index_on(test_db, "audit_logs", "timestamp"))["expireAfterSeconds"] == 30 * 24 * 3600
