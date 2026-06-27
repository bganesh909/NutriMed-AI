"""
PDF report generation worker.

Reads all report data (biomarkers, analysis, diet plan, workout plan,
recommendations) and uses PDFService to generate a comprehensive PDF.
Saves the file to the uploads directory and creates a notification.
"""

import logging
import os
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import MongoClient

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)

PDF_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "uploads",
    "pdfs",
)


def _get_db():
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB_NAME]


@celery_app.task(name="tasks.generate_pdf", bind=True, max_retries=3)
def generate_pdf_report(self, report_id: str, user_id: str):
    """
    1. Read all data: user, biomarkers, analysis, diet plan, workout plan, recommendations.
    2. Call PDFService to generate the report PDF.
    3. Save the PDF to the uploads/pdfs directory.
    4. Store the PDF path in the report document.
    5. Create a notification for the user.
    """
    db = _get_db()
    report_oid = ObjectId(report_id)
    now = datetime.now(timezone.utc)

    logger.info("Starting PDF generation for report %s, user %s", report_id, user_id)

    try:
        # ---- Gather all data ----
        report = db.reports.find_one({"_id": report_oid})
        if not report:
            raise ValueError(f"Report {report_id} not found")

        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError(f"User {user_id} not found")

        biomarker_doc = db.biomarkers.find_one({"report_id": report_id})
        analysis = db.analyses.find_one({"report_id": report_id})
        diet_plan_doc = db.diet_plans.find_one({"report_id": report_id})
        workout_plan_doc = db.workout_plans.find_one({"report_id": report_id})
        recommendation_doc = db.recommendations.find_one({"report_id": report_id})

        # ---- Prepare data for PDFService ----
        # Clean user dict (remove password and ObjectId)
        user_data = {
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "age": user.get("age"),
            "gender": user.get("gender"),
            "weight": user.get("weight"),
            "height": user.get("height"),
        }

        # Extract clean markers dict
        biomarkers_data = None
        if biomarker_doc:
            excluded_keys = {"_id", "user_id", "report_id", "extracted_at"}
            biomarkers_data = {
                k: v
                for k, v in biomarker_doc.items()
                if k not in excluded_keys and isinstance(v, (int, float))
            }

        # Interpretation from rule engine
        interpretation_data = None
        if analysis:
            interpretation_data = analysis.get("rule_engine")

        # Diet plan
        diet_data = None
        if diet_plan_doc:
            plan = diet_plan_doc.get("plan", {})
            if isinstance(plan, dict):
                diet_data = plan
            else:
                diet_data = {"meal_plan": plan}

        # Workout plan
        workout_data = None
        if workout_plan_doc:
            plan = workout_plan_doc.get("plan", {})
            if isinstance(plan, dict):
                workout_data = plan
            else:
                workout_data = {"plan": plan}

        # Supplements
        supplements_data = None
        if recommendation_doc:
            supp = recommendation_doc.get("supplement_suggestions", [])
            if isinstance(supp, list) and supp:
                supplements_data = supp

        # ---- Generate PDF ----
        pdf_service = PDFService()
        pdf_bytes = pdf_service.generate_report_pdf(
            user=user_data,
            biomarkers=biomarkers_data,
            interpretation=interpretation_data,
            diet_plan=diet_data,
            workout_plan=workout_data,
            supplements=supplements_data,
        )

        # ---- Save PDF to disk ----
        os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"report_{report_id}_{timestamp}.pdf"
        pdf_path = os.path.join(PDF_OUTPUT_DIR, pdf_filename)

        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        logger.info("PDF saved to %s (%d bytes)", pdf_path, len(pdf_bytes))

        # ---- Update report document with PDF path ----
        db.reports.update_one(
            {"_id": report_oid},
            {
                "$set": {
                    "pdf_path": pdf_path,
                    "pdf_generated_at": now,
                    "updated_at": now,
                }
            },
        )

        # ---- Create notification ----
        notification = {
            "user_id": user_id,
            "type": "pdf_ready",
            "title": "PDF Report Ready",
            "message": "Your comprehensive health report PDF has been generated and is ready for download.",
            "read": False,
            "created_at": now,
        }
        db.notifications.insert_one(notification)

        logger.info("PDF generation completed for report %s", report_id)

    except Exception as exc:
        logger.exception("PDF generation failed for report %s", report_id)
        db.reports.update_one(
            {"_id": report_oid},
            {
                "$set": {
                    "status": "failed",
                    "error": f"PDF generation failed: {exc}",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        raise self.retry(exc=exc, countdown=60)
