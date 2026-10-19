"""
Integration tests for account-level features: password reset, report and
account deletion, plan history, notifications and the admin console.
"""

import re
from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from tests.conftest import TEST_USER_DATA


@pytest.fixture()
def sent_emails(monkeypatch) -> list[dict]:
    """Capture outgoing email instead of sending it."""
    outbox: list[dict] = []

    async def _fake_send(to: str, subject: str, body: str) -> bool:
        outbox.append({"to": to, "subject": subject, "body": body})
        return True

    monkeypatch.setattr("app.api.v1.endpoints.auth.send_email", _fake_send)
    return outbox


async def _insert_report(db, user_id: str, tmp_path) -> str:
    upload = tmp_path / "report.enc"
    upload.write_bytes(b"encrypted")
    result = await db["reports"].insert_one(
        {
            "user_id": user_id,
            "report_type": "blood_test",
            "file_path": str(upload),
            "original_filename": "report.pdf",
            "status": "completed",
            "uploaded_at": datetime.now(UTC),
        }
    )
    report_id = str(result.inserted_id)
    bio = await db["biomarkers"].insert_one({"user_id": user_id, "report_id": report_id, "hemoglobin": 13.5})
    await db["recommendations"].insert_one({"user_id": user_id, "biomarker_id": str(bio.inserted_id)})
    await db["diet_plans"].insert_one({"user_id": user_id, "report_id": report_id, "meal_plan": [{"day": "Monday"}]})
    return report_id


@pytest.mark.asyncio
class TestPasswordReset:
    async def test_full_reset_flow(self, client: AsyncClient, test_user, sent_emails):
        resp = await client.post("/api/v1/auth/forgot-password", json={"email": TEST_USER_DATA["email"]})
        assert resp.status_code == 200
        assert len(sent_emails) == 1

        token = re.search(r"reset-password\?token=(\S+)", sent_emails[0]["body"]).group(1)
        resp = await client.post("/api/v1/auth/reset-password", json={"token": token, "password": "BrandNew@5678"})
        assert resp.status_code == 200

        login = await client.post(
            "/api/v1/auth/login", json={"email": TEST_USER_DATA["email"], "password": "BrandNew@5678"}
        )
        assert login.status_code == 200

        # Single use.
        again = await client.post("/api/v1/auth/reset-password", json={"token": token, "password": "Another@5678"})
        assert again.status_code == 400

    async def test_repeat_requests_send_one_email_a_minute(self, client: AsyncClient, test_user, sent_emails):
        for _ in range(3):
            resp = await client.post("/api/v1/auth/forgot-password", json={"email": TEST_USER_DATA["email"]})
            assert resp.status_code == 200
        assert len(sent_emails) == 1

    async def test_unknown_email_gets_same_answer(self, client: AsyncClient, sent_emails):
        resp = await client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
        assert resp.status_code == 200
        assert "reset link" in resp.json()["message"]
        assert sent_emails == []

    async def test_expired_token_rejected(self, client: AsyncClient, test_user, test_db, sent_emails):
        await client.post("/api/v1/auth/forgot-password", json={"email": TEST_USER_DATA["email"]})
        token = re.search(r"token=(\S+)", sent_emails[0]["body"]).group(1)
        await test_db["password_resets"].update_many({}, {"$set": {"expires_at": datetime.now(UTC) - timedelta(1)}})

        resp = await client.post("/api/v1/auth/reset-password", json={"token": token, "password": "BrandNew@5678"})
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestDeletion:
    async def test_delete_report_removes_derived_data(
        self, client: AsyncClient, test_user, test_db, auth_headers, tmp_path
    ):
        report_id = await _insert_report(test_db, test_user["id"], tmp_path)

        resp = await client.delete(f"/api/v1/reports/{report_id}", headers=auth_headers)
        assert resp.status_code == 204
        assert await test_db["reports"].count_documents({}) == 0
        assert await test_db["biomarkers"].count_documents({}) == 0
        assert await test_db["recommendations"].count_documents({}) == 0
        assert await test_db["diet_plans"].count_documents({}) == 0
        assert not (tmp_path / "report.enc").exists()

    async def test_cannot_delete_another_users_report(self, client: AsyncClient, test_db, auth_headers, tmp_path):
        report_id = await _insert_report(test_db, str(ObjectId()), tmp_path)
        resp = await client.delete(f"/api/v1/reports/{report_id}", headers=auth_headers)
        assert resp.status_code == 404
        assert await test_db["reports"].count_documents({}) == 1

    async def test_delete_account_requires_password(self, client: AsyncClient, test_user, test_db, auth_headers):
        resp = await client.request("DELETE", "/api/v1/users/me", json={"password": "wrong"}, headers=auth_headers)
        assert resp.status_code == 403
        assert await test_db["users"].count_documents({}) == 1

    async def test_delete_account_removes_everything(
        self, client: AsyncClient, test_user, test_db, auth_headers, tmp_path
    ):
        await _insert_report(test_db, test_user["id"], tmp_path)
        await test_db["notifications"].insert_one({"user_id": test_user["id"], "title": "t", "read": False})

        resp = await client.request(
            "DELETE", "/api/v1/users/me", json={"password": TEST_USER_DATA["password"]}, headers=auth_headers
        )
        assert resp.status_code == 204
        for name in ("users", "reports", "biomarkers", "recommendations", "diet_plans", "notifications"):
            assert await test_db[name].count_documents({}) == 0, name


@pytest.mark.asyncio
class TestPlanHistory:
    async def test_diet_plans_listed_newest_first(self, client: AsyncClient, test_user, test_db, auth_headers):
        now = datetime.now(UTC)
        await test_db["diet_plans"].insert_many(
            [
                {
                    "user_id": test_user["id"],
                    "goal": "old",
                    "meal_plan": [{"day": "Monday"}],
                    "created_at": now - timedelta(1),
                },
                {"user_id": test_user["id"], "goal": "new", "meal_plan": [{"day": "Monday"}], "created_at": now},
                {"user_id": test_user["id"], "goal": "empty", "meal_plan": [], "created_at": now},
            ]
        )
        resp = await client.get("/api/v1/nutrition/diet-plans", headers=auth_headers)
        assert resp.status_code == 200
        assert [p["goal"] for p in resp.json()] == ["new", "old"]

    async def test_workout_plans_skip_failed(self, client: AsyncClient, test_user, test_db, auth_headers):
        await test_db["workout_plans"].insert_many(
            [
                {
                    "user_id": test_user["id"],
                    "goal": "ok",
                    "days": [{"day_name": "Day 1", "exercises": [{"name": "Squat"}]}],
                },
                {"user_id": test_user["id"], "goal": "failed", "plan": {"error": "timeout"}},
            ]
        )
        resp = await client.get("/api/v1/fitness/plans", headers=auth_headers)
        assert resp.status_code == 200
        assert [p["goal"] for p in resp.json()] == ["ok"]


@pytest.mark.asyncio
class TestNotifications:
    async def test_list_and_mark_read(self, client: AsyncClient, test_user, test_db, auth_headers):
        await test_db["notifications"].insert_many(
            [
                {
                    "user_id": test_user["id"],
                    "title": "a",
                    "message": "m",
                    "read": False,
                    "created_at": datetime.now(UTC),
                },
                {
                    "user_id": test_user["id"],
                    "title": "b",
                    "message": "m",
                    "read": False,
                    "created_at": datetime.now(UTC),
                },
                {
                    "user_id": "someone-else",
                    "title": "c",
                    "message": "m",
                    "read": False,
                    "created_at": datetime.now(UTC),
                },
            ]
        )
        data = (await client.get("/api/v1/notifications/", headers=auth_headers)).json()
        assert data["unread_count"] == 2 and len(data["items"]) == 2

        first = data["items"][0]["id"]
        assert (await client.post(f"/api/v1/notifications/{first}/read", headers=auth_headers)).status_code == 204
        assert (await client.get("/api/v1/notifications/", headers=auth_headers)).json()["unread_count"] == 1

        assert (await client.post("/api/v1/notifications/read-all", headers=auth_headers)).status_code == 204
        assert (await client.get("/api/v1/notifications/", headers=auth_headers)).json()["unread_count"] == 0
        assert await test_db["notifications"].count_documents({"read": False}) == 1  # other user's untouched


@pytest.mark.asyncio
class TestAdmin:
    async def _admin_headers(self, db) -> tuple[str, dict]:
        result = await db["users"].insert_one(
            {
                "name": "Admin",
                "email": "admin@test.ai",
                "hashed_password": hash_password("Admin@1234"),
                "role": "admin",
                "created_at": datetime.now(UTC),
            }
        )
        admin_id = str(result.inserted_id)
        return admin_id, {"Authorization": f"Bearer {create_access_token(subject=admin_id, role='admin')}"}

    async def test_regular_user_forbidden(self, client: AsyncClient, auth_headers):
        assert (await client.get("/api/v1/admin/stats", headers=auth_headers)).status_code == 403
        assert (await client.get("/api/v1/admin/users", headers=auth_headers)).status_code == 403
        assert (await client.get("/api/v1/admin/client-ip", headers=auth_headers)).status_code == 403

    async def test_client_ip_shows_the_recorded_address_and_proxy_headers(self, client: AsyncClient, test_db):
        _, headers = await self._admin_headers(test_db)
        resp = await client.get(
            "/api/v1/admin/client-ip", headers={**headers, "X-Forwarded-For": "203.0.113.9, 198.51.100.7"}
        )
        assert resp.status_code == 200
        body = resp.json()
        # CLIENT_IP_HEADER is unset in tests, so the connecting address is kept.
        assert body["client_ip"] == "127.0.0.1"
        assert body["client_ip_header"] is None
        assert body["headers"]["x-forwarded-for"] == "203.0.113.9, 198.51.100.7"
        assert body["headers"]["cf-connecting-ip"] is None

    async def test_stats_and_users(self, client: AsyncClient, test_user, test_db, tmp_path):
        _, headers = await self._admin_headers(test_db)
        await _insert_report(test_db, test_user["id"], tmp_path)

        stats = (await client.get("/api/v1/admin/stats", headers=headers)).json()
        assert stats["users"] == 2 and stats["reports"] == 1

        users = (await client.get("/api/v1/admin/users", params={"q": "testuser"}, headers=headers)).json()
        assert len(users) == 1
        assert users[0]["report_count"] == 1
        assert "hashed_password" not in users[0]

    async def test_role_change_and_delete(self, client: AsyncClient, test_user, test_db):
        admin_id, headers = await self._admin_headers(test_db)

        resp = await client.patch(
            f"/api/v1/admin/users/{test_user['id']}/role", json={"role": "admin"}, headers=headers
        )
        assert resp.status_code == 200
        assert (await test_db["users"].find_one({"_id": ObjectId(test_user["id"])}))["role"] == "admin"

        own = await client.patch(f"/api/v1/admin/users/{admin_id}/role", json={"role": "user"}, headers=headers)
        assert own.status_code == 400

        assert (await client.delete(f"/api/v1/admin/users/{test_user['id']}", headers=headers)).status_code == 204
        assert await test_db["users"].count_documents({}) == 1


@pytest.mark.asyncio
class TestSessionsAfterPasswordChange:
    async def test_reset_signs_out_existing_sessions(self, client: AsyncClient, test_user, test_db, sent_emails):
        old_token = create_access_token(subject=test_user["id"])
        await client.post("/api/v1/auth/forgot-password", json={"email": TEST_USER_DATA["email"]})
        token = re.search(r"token=(\S+)", sent_emails[0]["body"]).group(1)
        resp = await client.post("/api/v1/auth/reset-password", json={"token": token, "password": "BrandNew@5678"})
        assert resp.status_code == 200
        user = await test_db["users"].find_one({})
        assert user["password_changed_at"] is not None

        # iat has whole-second granularity, so a token minted in the same second
        # as the reset is still accepted. Move the change forward to make the
        # outcome independent of the clock.
        await test_db["users"].update_one(
            {}, {"$set": {"password_changed_at": datetime.now(UTC) + timedelta(seconds=2)}}
        )
        resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {old_token}"})
        assert resp.status_code == 401

        # Signing in again works.
        login = await client.post(
            "/api/v1/auth/login", json={"email": TEST_USER_DATA["email"], "password": "BrandNew@5678"}
        )
        assert login.status_code == 200

    async def test_change_password_keeps_current_session(self, client: AsyncClient, test_user, auth_headers):
        wrong = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "nope", "new_password": "BrandNew@5678"},
            headers=auth_headers,
        )
        assert wrong.status_code == 403

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": TEST_USER_DATA["password"], "new_password": "BrandNew@5678"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        fresh = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        assert (await client.get("/api/v1/users/me", headers=fresh)).status_code == 200

        login = await client.post(
            "/api/v1/auth/login", json={"email": TEST_USER_DATA["email"], "password": "BrandNew@5678"}
        )
        assert login.status_code == 200

    async def test_register_records_terms_acceptance(self, client: AsyncClient, test_db):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"name": "New", "email": "consent@example.com", "password": "Secure@12345", "accepted_terms": True},
        )
        assert resp.status_code == 201
        user = await test_db["users"].find_one({"email": "consent@example.com"})
        assert user["terms_accepted_at"] is not None


@pytest.mark.asyncio
class TestMedicalProfile:
    async def test_dietary_preference_round_trips(self, client: AsyncClient, test_user, auth_headers):
        assert (await client.get("/api/v1/users/me/medical-profile", headers=auth_headers)).status_code == 404

        payload = {"blood_type": "O+", "dietary_preference": "vegetarian", "allergies": ["peanuts"]}
        resp = await client.post("/api/v1/users/me/medical-profile", json=payload, headers=auth_headers)
        assert resp.status_code == 200

        saved = (await client.get("/api/v1/users/me/medical-profile", headers=auth_headers)).json()
        assert saved["dietary_preference"] == "vegetarian"
        assert saved["allergies"] == ["peanuts"]

    async def test_unsupported_preference_rejected(self, client: AsyncClient, test_user, auth_headers):
        resp = await client.post(
            "/api/v1/users/me/medical-profile", json={"dietary_preference": "keto"}, headers=auth_headers
        )
        assert resp.status_code == 422
