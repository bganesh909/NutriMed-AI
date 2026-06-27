"""
Integration tests for /api/v1/reports endpoints.

Tests: upload, get, list, analyze.
"""

import io

import pytest
from httpx import AsyncClient
from bson import ObjectId


@pytest.mark.asyncio
class TestReportUpload:
    async def test_upload_report(self, client: AsyncClient, auth_headers, test_user):
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake content for testing")
        resp = await client.post(
            "/api/v1/reports/upload",
            headers=auth_headers,
            data={"report_type": "CBC"},
            files={"file": ("blood_test.pdf", fake_pdf, "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["report_type"] == "CBC"
        assert data["original_filename"] == "blood_test.pdf"
        assert data["status"] == "uploaded"
        assert "id" in data

    async def test_upload_without_auth(self, client: AsyncClient):
        fake_pdf = io.BytesIO(b"%PDF-1.4 test")
        resp = await client.post(
            "/api/v1/reports/upload",
            data={"report_type": "CBC"},
            files={"file": ("test.pdf", fake_pdf, "application/pdf")},
        )
        assert resp.status_code in (401, 403)

    async def test_upload_invalid_report_type(self, client: AsyncClient, auth_headers, test_user):
        fake_pdf = io.BytesIO(b"%PDF-1.4 test")
        resp = await client.post(
            "/api/v1/reports/upload",
            headers=auth_headers,
            data={"report_type": "INVALID_TYPE"},
            files={"file": ("test.pdf", fake_pdf, "application/pdf")},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestReportGet:
    async def _create_report(self, client: AsyncClient, auth_headers) -> str:
        fake_pdf = io.BytesIO(b"%PDF-1.4 test content")
        resp = await client.post(
            "/api/v1/reports/upload",
            headers=auth_headers,
            data={"report_type": "LIPID"},
            files={"file": ("lipid.pdf", fake_pdf, "application/pdf")},
        )
        return resp.json()["id"]

    async def test_get_report_by_id(self, client: AsyncClient, auth_headers, test_user):
        report_id = await self._create_report(client, auth_headers)
        resp = await client.get(
            f"/api/v1/reports/{report_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == report_id
        assert resp.json()["report_type"] == "LIPID"

    async def test_get_nonexistent_report(self, client: AsyncClient, auth_headers, test_user):
        fake_id = str(ObjectId())
        resp = await client.get(
            f"/api/v1/reports/{fake_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestReportList:
    async def test_list_reports_empty(self, client: AsyncClient, auth_headers, test_user):
        resp = await client.get("/api/v1/reports/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_reports_with_data(self, client: AsyncClient, auth_headers, test_user):
        # Upload two reports
        for name in ("report1.pdf", "report2.pdf"):
            fake_pdf = io.BytesIO(b"%PDF-1.4 content")
            await client.post(
                "/api/v1/reports/upload",
                headers=auth_headers,
                data={"report_type": "CBC"},
                files={"file": (name, fake_pdf, "application/pdf")},
            )

        resp = await client.get("/api/v1/reports/", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


@pytest.mark.asyncio
class TestReportAnalyze:
    async def test_trigger_analysis(self, client: AsyncClient, auth_headers, test_user):
        # Upload a report first
        fake_pdf = io.BytesIO(b"%PDF-1.4 test content")
        upload_resp = await client.post(
            "/api/v1/reports/upload",
            headers=auth_headers,
            data={"report_type": "CBC"},
            files={"file": ("cbc.pdf", fake_pdf, "application/pdf")},
        )
        report_id = upload_resp.json()["id"]

        # Trigger analysis -- may return 503 if Celery is not running, which is expected in tests
        resp = await client.post(
            f"/api/v1/reports/{report_id}/analyze",
            headers=auth_headers,
        )
        assert resp.status_code in (200, 503)

    async def test_analyze_nonexistent_report(self, client: AsyncClient, auth_headers, test_user):
        fake_id = str(ObjectId())
        resp = await client.post(
            f"/api/v1/reports/{fake_id}/analyze",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_get_analysis_before_processing(self, client: AsyncClient, auth_headers, test_user):
        fake_pdf = io.BytesIO(b"%PDF-1.4 test")
        upload_resp = await client.post(
            "/api/v1/reports/upload",
            headers=auth_headers,
            data={"report_type": "VITAMIN"},
            files={"file": ("vitamins.pdf", fake_pdf, "application/pdf")},
        )
        report_id = upload_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/reports/{report_id}/analysis",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "uploaded"
