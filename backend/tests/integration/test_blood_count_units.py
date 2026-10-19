"""
Blood counts printed in thousands or lakhs, end to end: what extraction stores,
and what the analysis endpoint shows -- including for reports analysed before
the fix, whose saved analysis says "low".
"""

from datetime import UTC, datetime

import pytest
from bson import ObjectId
from httpx import AsyncClient

from app.workers.extraction_worker import _markers_from_ocr_result


def test_extraction_stores_canonical_values_and_the_printed_form():
    ocr_result = {
        "biomarkers": {
            "biomarkers": [
                {"name": "wbc", "value": 7.1, "unit": "10^3/uL", "reference_range": "4.0 - 11.0"},
                {"name": "platelets", "value": 7, "unit": "", "reference_range": ""},
                {"name": "hemoglobin", "value": 11.2, "unit": "g/dL", "reference_range": "13.0 - 17.0"},
            ]
        }
    }
    markers, as_reported = _markers_from_ocr_result(ocr_result)

    assert markers["wbc"] == pytest.approx(7100)
    assert markers["hemoglobin"] == pytest.approx(11.2)
    # 7 could be lakhs or thousands: not stored where other code would read it.
    assert "platelets" not in markers
    assert as_reported["platelets"] == {"value": 7.0, "unit": "", "reference_range": ""}
    assert as_reported["wbc"]["unit"] == "10^3/uL"


async def _completed_report(db, user_id: str, biomarker_fields: dict, stored_details: dict) -> str:
    report_id = str(ObjectId())
    await db["reports"].insert_one(
        {
            "_id": ObjectId(report_id),
            "user_id": user_id,
            "status": "completed",
            "report_type": "CBC",
            "original_filename": "cbc.pdf",
            "uploaded_at": datetime.now(UTC),
        }
    )
    await db["biomarkers"].insert_one({"user_id": user_id, "report_id": report_id, **biomarker_fields})
    await db["analyses"].insert_one({"report_id": report_id, "rule_engine": {"marker_details": stored_details}})
    return report_id


@pytest.mark.asyncio
async def test_old_report_shows_corrected_counts(client: AsyncClient, test_db, test_user, auth_headers):
    # Analysed before the fix: raw values, and a saved analysis that says "low".
    wrong = {
        "wbc": {"value": 7.1, "unit": "cells/mcL", "status": "low", "range": "4500-11000"},
        "platelets": {"value": 250, "unit": "cells/mcL", "status": "low", "range": "150000-400000"},
    }
    report_id = await _completed_report(test_db, test_user["id"], {"wbc": 7.1, "platelets": 250}, wrong)

    resp = await client.get(f"/api/v1/reports/{report_id}/analysis", headers=auth_headers)
    assert resp.status_code == 200
    details = resp.json()["biomarkers"]
    assert details["wbc"]["status"] == "normal"
    assert details["platelets"]["status"] == "normal"


@pytest.mark.asyncio
async def test_new_report_uses_the_lab_range(client: AsyncClient, test_db, test_user, auth_headers):
    fields = {
        "wbc": 4200.0,
        "as_reported": {"wbc": {"value": 4.2, "unit": "10^3/uL", "reference_range": "4.0 - 11.0"}},
    }
    report_id = await _completed_report(test_db, test_user["id"], fields, {})

    detail = (await client.get(f"/api/v1/reports/{report_id}/analysis", headers=auth_headers)).json()["biomarkers"][
        "wbc"
    ]
    assert detail["status"] == "normal"
    assert detail["value"] == 4.2
    assert detail["range"] == "4-11"
