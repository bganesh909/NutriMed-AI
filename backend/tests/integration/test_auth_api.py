"""
Integration tests for /api/v1/auth endpoints.

Tests: register, login, invalid credentials, duplicate email, token refresh.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import TEST_USER_DATA


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "SecurePass@1234",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Duplicate",
                "email": TEST_USER_DATA["email"],
                "password": "AnotherPass@123",
            },
        )
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    async def test_register_missing_fields(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "partial@example.com"},
        )
        assert resp.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Short Pass",
                "email": "short@example.com",
                "password": "123",
            },
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Bad Email",
                "email": "not-an-email",
                "password": "ValidPass@1234",
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": TEST_USER_DATA["email"],
                "password": TEST_USER_DATA["password"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": TEST_USER_DATA["email"],
                "password": "WrongPassword@999",
            },
        )
        assert resp.status_code == 401
        assert "invalid credentials" in resp.json()["detail"].lower()

    async def test_login_nonexistent_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "SomePass@1234",
            },
        )
        assert resp.status_code == 401

    async def test_login_missing_password(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_DATA["email"]},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTokenRefresh:
    async def test_refresh_success(self, client: AsyncClient, test_user):
        # First login to get a refresh token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": TEST_USER_DATA["email"],
                "password": TEST_USER_DATA["password"],
            },
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Use it to get a new token pair
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New tokens should differ from original
        assert data["access_token"] != login_resp.json()["access_token"]

    async def test_refresh_with_access_token_fails(self, client: AsyncClient, test_user):
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": TEST_USER_DATA["email"],
                "password": TEST_USER_DATA["password"],
            },
        )
        access_token = login_resp.json()["access_token"]

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401

    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )
        assert resp.status_code == 401
