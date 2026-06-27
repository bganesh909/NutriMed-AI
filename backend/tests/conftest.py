"""
Shared pytest fixtures for NutriMed AI backend tests.

Provides:
- Async MongoDB test client (uses a dedicated test database)
- Redis test client (uses a separate DB index)
- FastAPI async test client via httpx
- Pre-created test user and auth-token helpers
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# Override settings BEFORE importing the app so the test database is used.
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "nutrimed_ai_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests")
os.environ.setdefault("AES_KEY", "test-aes-key-32-bytes-long-value")

from app.core.config import settings  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# MongoDB fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def mongo_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Session-scoped MongoDB client."""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    yield client
    client.close()


@pytest_asyncio.fixture()
async def test_db(mongo_client: AsyncIOMotorClient) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    Per-test MongoDB database.  Drops the test database after each test
    to guarantee isolation.
    """
    db = mongo_client[settings.MONGO_DB_NAME]
    yield db
    await mongo_client.drop_database(settings.MONGO_DB_NAME)


# ---------------------------------------------------------------------------
# Redis fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def test_redis():
    """
    Per-test Redis client.  Flushes the test DB after each test.
    Falls back to a no-op stub if Redis is not available.
    """
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        yield client
        await client.flushdb()
        await client.aclose()
    except Exception:
        # Redis not available -- yield a dummy so tests that don't need it still pass.
        yield None


# ---------------------------------------------------------------------------
# Test user helpers
# ---------------------------------------------------------------------------

TEST_USER_DATA = {
    "name": "Test User",
    "email": "testuser@nutrimed.ai",
    "password": "Test@1234",
    "age": 30,
    "gender": "male",
    "weight": 75.0,
    "height": 175.0,
    "activity_level": "moderately_active",
    "goals": ["maintenance"],
    "role": "user",
}


@pytest_asyncio.fixture()
async def test_user(test_db: AsyncIOMotorDatabase) -> dict:
    """Insert a test user into the DB and return the document (with 'id' field)."""
    user_doc = {
        "name": TEST_USER_DATA["name"],
        "email": TEST_USER_DATA["email"],
        "hashed_password": hash_password(TEST_USER_DATA["password"]),
        "age": TEST_USER_DATA["age"],
        "gender": TEST_USER_DATA["gender"],
        "weight": TEST_USER_DATA["weight"],
        "height": TEST_USER_DATA["height"],
        "activity_level": TEST_USER_DATA["activity_level"],
        "goals": TEST_USER_DATA["goals"],
        "role": TEST_USER_DATA["role"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await test_db["users"].insert_one(user_doc)
    user_doc["id"] = str(result.inserted_id)
    user_doc.pop("_id", None)
    return user_doc


@pytest.fixture()
def auth_token(test_user: dict) -> str:
    """Return a valid JWT access token for the test user."""
    return create_access_token(
        subject=test_user["id"],
        role=test_user.get("role", "user"),
    )


@pytest.fixture()
def auth_headers(auth_token: str) -> dict[str, str]:
    """Return Authorization headers ready for httpx requests."""
    return {"Authorization": f"Bearer {auth_token}"}


# ---------------------------------------------------------------------------
# FastAPI async test client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def client(test_db: AsyncIOMotorDatabase) -> AsyncGenerator[AsyncClient, None]:
    """
    httpx AsyncClient wired to the FastAPI app.

    Patches the database dependency so all requests hit the test database.
    """
    from app.core.dependencies import get_db  # noqa: E402
    from app.main import app  # noqa: E402

    async def _override_get_db():
        return test_db

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
