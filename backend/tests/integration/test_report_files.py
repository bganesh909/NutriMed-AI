"""Uploaded reports live encrypted in GridFS, reachable by the API and the workers."""

import httpx
import pytest
from bson import ObjectId
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pymongo import MongoClient

from app.core.config import settings
from app.services import report_files
from tests.conftest import TEST_USER_DATA

PDF = b"%PDF-1.4 fake lab report\nHemoglobin 11.2 g/dL\n%%EOF"


async def _upload(client: AsyncClient, headers: dict, name: str = "cbc.pdf") -> str:
    resp = await client.post(
        "/api/v1/reports/upload",
        files={"file": (name, PDF, "application/pdf")},
        data={"report_type": "CBC"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _stored_bytes(db, file_id: str) -> bytes:
    stream = await AsyncIOMotorGridFSBucket(db, bucket_name=report_files.BUCKET).open_download_stream(ObjectId(file_id))
    return await stream.read()


@pytest.mark.asyncio
async def test_upload_is_stored_encrypted_in_gridfs(client: AsyncClient, test_db, test_user, auth_headers):
    report_id = await _upload(client, auth_headers)
    report = await test_db["reports"].find_one({"_id": ObjectId(report_id)})

    assert report["file_id"] and not report.get("file_path")
    stored = await _stored_bytes(test_db, report["file_id"])
    assert stored != PDF and b"Hemoglobin" not in stored  # encrypted at rest
    assert await report_files.read(test_db, report) == PDF


@pytest.mark.asyncio
async def test_original_download(client: AsyncClient, test_db, test_user, auth_headers):
    report_id = await _upload(client, auth_headers)
    resp = await client.get(f"/api/v1/pdf/report/{report_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.content == PDF


@pytest.mark.asyncio
async def test_deleting_a_report_deletes_its_file(client: AsyncClient, test_db, test_user, auth_headers):
    report_id = await _upload(client, auth_headers)
    file_id = (await test_db["reports"].find_one({"_id": ObjectId(report_id)}))["file_id"]

    assert (await client.delete(f"/api/v1/reports/{report_id}", headers=auth_headers)).status_code == 204
    assert await test_db[f"{report_files.BUCKET}.files"].count_documents({"_id": ObjectId(file_id)}) == 0
    assert await test_db[f"{report_files.BUCKET}.chunks"].count_documents({"files_id": ObjectId(file_id)}) == 0


@pytest.mark.asyncio
async def test_deleting_the_account_deletes_every_file(client: AsyncClient, test_db, test_user, auth_headers):
    await _upload(client, auth_headers, "one.pdf")
    await _upload(client, auth_headers, "two.pdf")
    # A file no report points at (e.g. an upload interrupted midway) goes too.
    await report_files.save(test_db, b"orphan", "orphan.pdf", test_user["id"])

    resp = await client.request(
        "DELETE", "/api/v1/users/me", json={"password": TEST_USER_DATA["password"]}, headers=auth_headers
    )
    assert resp.status_code == 204
    assert await test_db[f"{report_files.BUCKET}.files"].count_documents({}) == 0


@pytest.mark.asyncio
async def test_ocr_worker_reads_the_file_from_gridfs(
    client: AsyncClient, test_db, test_user, auth_headers, monkeypatch
):
    from app.workers import extraction_worker, ocr_worker

    report_id = await _upload(client, auth_headers, "blood_test.pdf")
    sent: dict = {}

    def fake_ocr(url, files=None, timeout=None):
        sent["name"], sent["bytes"] = files["file"]
        return httpx.Response(200, json={"ocr": {"text": "Hemoglobin 11.2"}}, request=httpx.Request("POST", url))

    monkeypatch.setattr(ocr_worker.httpx, "post", fake_ocr)
    monkeypatch.setattr(extraction_worker.extract_biomarkers, "delay", lambda *_a: None)

    ocr_worker.process_ocr(report_id)

    assert sent == {"name": "blood_test.pdf", "bytes": PDF}
    report = await test_db["reports"].find_one({"_id": ObjectId(report_id)})
    assert report["status"] == "ocr_completed"


def test_read_sync_for_workers(test_db):
    """The pymongo path the Celery workers use, against the same test database."""
    import asyncio

    file_id = asyncio.run(_save_with_fresh_loop(b"worker bytes"))
    db = MongoClient(settings.MONGO_URI)[settings.MONGO_DB_NAME]
    assert report_files.read_sync(db, {"file_id": file_id}) == b"worker bytes"
    with pytest.raises(FileNotFoundError):
        report_files.read_sync(db, {"file_id": str(ObjectId())})


async def _save_with_fresh_loop(data: bytes) -> str:
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(settings.MONGO_URI)
    try:
        return await report_files.save(client[settings.MONGO_DB_NAME], data, "w.pdf", "user-1")
    finally:
        client.close()
