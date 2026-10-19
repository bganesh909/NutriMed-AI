"""
Indexes the API depends on for correctness and data retention, ensured
idempotently at startup. The seed script (seeds/seed_data.py) creates the
general query indexes.
"""

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _ensure_ttl(db: AsyncIOMotorDatabase, collection: str, field: str, seconds: int) -> None:
    """Create a TTL index on ``field``, or convert/update an existing single-field index in place."""
    async for index in db[collection].list_indexes():
        if dict(index["key"]) == {field: 1}:
            if index.get("expireAfterSeconds") != seconds:
                await db.command("collMod", collection, index={"keyPattern": {field: 1}, "expireAfterSeconds": seconds})
                logger.info("Set %s.%s to expire after %ss", collection, field, seconds)
            return
    await db[collection].create_index(field, expireAfterSeconds=seconds)


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db["password_resets"].create_index("token_hash", unique=True)
    await db["password_resets"].create_index("user_id")
    # Reset tokens disappear once they expire.
    await _ensure_ttl(db, "password_resets", "expires_at", 0)

    await db["notifications"].create_index([("user_id", 1), ("created_at", -1)])

    # Audit logs are kept for a limited period (stated in the privacy notice).
    await _ensure_ttl(db, "audit_logs", "timestamp", settings.AUDIT_LOG_RETENTION_DAYS * 24 * 3600)
