from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import redis.asyncio as aioredis

from app.core.config import settings

# ---------------------------------------------------------------------------
# MongoDB (motor async driver)
# ---------------------------------------------------------------------------

_mongo_client: AsyncIOMotorClient | None = None


async def connect_mongo() -> None:
    global _mongo_client
    _mongo_client = AsyncIOMotorClient(settings.MONGO_URI)
    # Force a connection check
    await _mongo_client.admin.command("ping")


async def close_mongo() -> None:
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None


def get_database() -> AsyncIOMotorDatabase:
    if _mongo_client is None:
        raise RuntimeError("MongoDB client is not initialised. Call connect_mongo() first.")
    return _mongo_client[settings.MONGO_DB_NAME]


# ---------------------------------------------------------------------------
# Redis (async)
# ---------------------------------------------------------------------------

_redis_client: aioredis.Redis | None = None


async def connect_redis() -> None:
    global _redis_client
    _redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    await _redis_client.ping()


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def get_redis() -> aioredis.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis client is not initialised. Call connect_redis() first.")
    return _redis_client
