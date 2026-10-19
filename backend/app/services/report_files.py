"""
Uploaded report files, stored encrypted in MongoDB (GridFS).

Files live in the database rather than on a local disk so every API instance
and background worker can reach them -- hosts such as Render give each service
its own disk, wiped on every deploy -- and so database backups include them.
Each file is encrypted with AES_KEY before it is stored.

Reports uploaded before this module kept the encrypted file on local disk
(``file_path``); those are still read and deleted from there.
"""

import contextlib
import logging
import os

import gridfs
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket

from app.core.security import decrypt_data, encrypt_data

logger = logging.getLogger(__name__)

BUCKET = "report_files"


def _bucket(db: AsyncIOMotorDatabase) -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(db, bucket_name=BUCKET)


async def save(db: AsyncIOMotorDatabase, data: bytes, filename: str, user_id: str) -> str:
    """Encrypt and store an upload; returns the file id to keep on the report."""
    file_id = await _bucket(db).upload_from_stream(filename, encrypt_data(data), metadata={"user_id": user_id})
    return str(file_id)


async def read(db: AsyncIOMotorDatabase, report_doc: dict) -> bytes:
    """The decrypted file of a report. Raises FileNotFoundError if it is gone."""
    if report_doc.get("file_id"):
        try:
            stream = await _bucket(db).open_download_stream(ObjectId(report_doc["file_id"]))
        except gridfs.errors.NoFile as exc:
            raise FileNotFoundError(report_doc["file_id"]) from exc
        return decrypt_data(await stream.read())
    return _read_legacy(report_doc)


def read_sync(db, report_doc: dict) -> bytes:
    """`read` for Celery workers (pymongo)."""
    if report_doc.get("file_id"):
        try:
            data = gridfs.GridFSBucket(db, bucket_name=BUCKET).open_download_stream(ObjectId(report_doc["file_id"]))
        except gridfs.errors.NoFile as exc:
            raise FileNotFoundError(report_doc["file_id"]) from exc
        return decrypt_data(data.read())
    return _read_legacy(report_doc)


async def delete(db: AsyncIOMotorDatabase, report_doc: dict) -> None:
    """Remove a report's file, wherever it is stored. Missing files are fine."""
    if report_doc.get("file_id"):
        with contextlib.suppress(gridfs.errors.NoFile):
            await _bucket(db).delete(ObjectId(report_doc["file_id"]))
    _remove_legacy(report_doc.get("file_path"))


async def delete_all_for_user(db: AsyncIOMotorDatabase, user_id: str) -> None:
    """Remove every stored file of a user, including any no report points at."""
    bucket = _bucket(db)
    async for grid_out in bucket.find({"metadata.user_id": user_id}):
        with contextlib.suppress(gridfs.errors.NoFile):
            await bucket.delete(grid_out._id)
    async for report in db["reports"].find({"user_id": user_id}, {"file_path": 1}):
        _remove_legacy(report.get("file_path"))


def _read_legacy(report_doc: dict) -> bytes:
    path = report_doc.get("file_path")
    if not path:
        raise FileNotFoundError("report has no stored file")
    with open(path, "rb") as fh:
        return decrypt_data(fh.read())


def _remove_legacy(path: str | None) -> None:
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        logger.exception("Could not delete report file %s", path)
