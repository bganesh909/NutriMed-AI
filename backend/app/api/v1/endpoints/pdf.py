import io

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.dependencies import get_current_user, get_db
from app.core.security import decrypt_data
from app.services.lab_interpretation_service import LabInterpretationService
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/pdf")


@router.get("/reports/{report_id}/pdf")
async def download_generated_pdf(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Generate and stream a full NutriMed AI PDF report including:
    biomarkers, interpretation, diet plan, workout plan, supplements.
    """
    # Verify report ownership
    report_doc = await db["reports"].find_one(
        {"_id": ObjectId(report_id), "user_id": current_user["id"]}
    )
    if not report_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Fetch user full profile
    user_doc = await db["users"].find_one({"_id": ObjectId(current_user["id"])})
    if user_doc:
        user_doc["id"] = str(user_doc.pop("_id"))
        user_doc.pop("hashed_password", None)
    else:
        user_doc = current_user

    # Fetch biomarkers for this report
    biomarker_doc = await db["biomarkers"].find_one({"report_id": report_id})
    biomarkers = None
    if biomarker_doc:
        biomarker_doc.pop("_id", None)
        biomarkers = biomarker_doc

    # Run interpretation if biomarkers exist
    interpretation = None
    if biomarkers:
        markers = biomarkers.get("markers", {})
        # Also handle flat biomarker format (individual fields)
        if not markers:
            exclude = {"user_id", "report_id", "extracted_at", "created_at", "id"}
            markers = {
                k: v for k, v in biomarkers.items()
                if k not in exclude and v is not None and isinstance(v, (int, float))
            }
        if markers:
            lab_service = LabInterpretationService()
            gender = (user_doc.get("gender") or "male").lower()
            interpretation = lab_service.interpret(markers, gender)

    # Fetch latest diet plan
    diet_plan = await db["diet_plans"].find_one(
        {"user_id": current_user["id"]},
        sort=[("created_at", -1)],
    )
    if diet_plan:
        diet_plan.pop("_id", None)

    # Fetch the most recent workout plan that actually has exercises (skip
    # placeholder/failed plans, e.g. a report-derived plan whose LLM step timed out).
    workout_plan = None
    async for wp in db["workout_plans"].find(
        {"user_id": current_user["id"]}
    ).sort("created_at", -1):
        days = wp.get("plan") or wp.get("days") or []
        if isinstance(days, list) and any(
            isinstance(d, dict) and d.get("exercises") for d in days
        ):
            wp.pop("_id", None)
            workout_plan = wp
            break

    # Extract supplements from the most recent recommendation that has any.
    supplements = None
    async for rec_doc in db["recommendations"].find(
        {"user_id": current_user["id"]}
    ).sort("created_at", -1):
        candidate = rec_doc.get("supplements") or rec_doc.get("supplement_suggestions")
        if isinstance(candidate, list) and candidate:
            supplements = candidate
            break

    # Generate PDF
    pdf_service = PDFService()
    pdf_bytes = pdf_service.generate_report_pdf(
        user=user_doc,
        biomarkers=biomarkers,
        interpretation=interpretation,
        diet_plan=diet_plan,
        workout_plan=workout_plan,
        supplements=supplements if isinstance(supplements, list) else None,
    )

    filename = f"nutrimed_report_{report_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/report/{report_id}")
async def download_original_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Download the original uploaded report file (decrypted)."""
    doc = await db["reports"].find_one({"_id": ObjectId(report_id), "user_id": current_user["id"]})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    file_path = doc.get("file_path")
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not available")

    try:
        with open(file_path, "rb") as f:
            encrypted_content = f.read()
        content = decrypt_data(encrypted_content)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found on disk")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to decrypt report")

    original_filename = doc.get("original_filename", "report.pdf")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{original_filename}"'},
    )
