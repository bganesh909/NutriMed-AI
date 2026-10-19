"""
Deletion of a user's medical data.

Reports and everything derived from them (biomarkers, analyses,
recommendations, suggestions, report-linked plans) are removed together, as is
the encrypted upload on disk. Audit logs are kept: they are the security
record of who accessed what, not health data.
"""

import logging
import os

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Collections whose documents hang off a report via ``report_id``.
_REPORT_LINKED = ("biomarkers", "analyses", "suggestions", "diet_plans", "workout_plans", "generation_metrics")

# Collections holding a user's own data via ``user_id``.
_USER_OWNED = (
    "reports",
    "biomarkers",
    "analyses",
    "recommendations",
    "suggestions",
    "diet_plans",
    "workout_plans",
    "progress",
    "medical_profiles",
    "notifications",
    "generation_metrics",
    "password_resets",
)


def _remove_file(path: str | None) -> None:
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        logger.exception("Could not delete report file %s", path)


async def delete_report(db: AsyncIOMotorDatabase, report_doc: dict) -> None:
    """Delete one report, its upload and all data derived from it."""
    report_id = str(report_doc["_id"])

    # Recommendations are linked to the biomarker document, not the report.
    biomarker_ids = [str(d["_id"]) async for d in db["biomarkers"].find({"report_id": report_id}, {"_id": 1})]
    if biomarker_ids:
        await db["recommendations"].delete_many({"biomarker_id": {"$in": biomarker_ids}})
    await db["recommendations"].delete_many({"report_id": report_id})

    for name in _REPORT_LINKED:
        await db[name].delete_many({"report_id": report_id})

    await db["reports"].delete_one({"_id": report_doc["_id"]})
    _remove_file(report_doc.get("file_path"))


async def delete_user(db: AsyncIOMotorDatabase, user_id: str) -> None:
    """Delete a user account and all of its data."""
    async for report in db["reports"].find({"user_id": user_id}, {"file_path": 1}):
        _remove_file(report.get("file_path"))

    for name in _USER_OWNED:
        await db[name].delete_many({"user_id": user_id})

    await db["users"].delete_one({"_id": ObjectId(user_id)})
