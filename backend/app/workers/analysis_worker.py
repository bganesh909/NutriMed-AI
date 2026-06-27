"""
Lab analysis worker.

Reads extracted biomarkers and user profile, runs both a deterministic rule
engine and an LLM-based AI interpretation, combines the results, and chains
to the recommendation task.
"""

import json
import logging
from datetime import datetime, timezone

import httpx
from bson import ObjectId
from pymongo import MongoClient

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.lab_interpretation_service import LabInterpretationService

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 120.0


def _get_db():
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB_NAME]


def _call_llm_sync(prompt: str) -> str:
    """Synchronous call to Ollama for use inside Celery tasks."""
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False,
    }
    response = httpx.post(url, json=payload, timeout=LLM_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get("response", "")


def _build_analysis_prompt(markers: dict, user: dict) -> str:
    """Build a detailed prompt for AI-powered biomarker interpretation."""
    age = user.get("age", "unknown")
    gender = user.get("gender", "unknown")
    weight = user.get("weight", "unknown")
    height = user.get("height", "unknown")
    conditions = user.get("conditions", [])

    markers_text = "\n".join(
        f"  - {name}: {value}" for name, value in markers.items()
    )
    conditions_text = ", ".join(conditions) if conditions else "none reported"

    return (
        f"You are a clinical lab analysis assistant. Interpret the following biomarker "
        f"results for a {age}-year-old {gender}, {weight}kg, {height}cm tall.\n"
        f"Known conditions: {conditions_text}.\n\n"
        f"Biomarker values:\n{markers_text}\n\n"
        f"Provide a concise clinical interpretation covering:\n"
        f"1. Key findings (abnormal values and their clinical significance)\n"
        f"2. Potential health risks\n"
        f"3. Recommended follow-up tests\n"
        f"4. Lifestyle suggestions\n\n"
        f"Return valid JSON with keys: key_findings (list of strings), "
        f"health_risks (list of strings), follow_up_tests (list of strings), "
        f"lifestyle_suggestions (list of strings), summary (string)."
    )


def _parse_llm_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from LLM output."""
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw_response": text}


@celery_app.task(name="tasks.analyze_biomarkers", bind=True, max_retries=3)
def analyze_biomarkers(self, report_id: str, user_id: str):
    """
    1. Read biomarkers and user profile from MongoDB.
    2. Run the deterministic rule engine (LabInterpretationService).
    3. Call the LLM for AI-powered interpretation.
    4. Combine both analyses and store the result.
    5. Update report status to 'analyzed'.
    6. Dispatch the recommendation task.
    """
    db = _get_db()
    report_oid = ObjectId(report_id)

    logger.info("Starting biomarker analysis for report %s, user %s", report_id, user_id)

    try:
        # Fetch report and biomarkers
        report = db.reports.find_one({"_id": report_oid})
        if not report:
            raise ValueError(f"Report {report_id} not found")

        biomarker_doc = db.biomarkers.find_one({"report_id": report_id})
        if not biomarker_doc:
            raise ValueError(f"No biomarkers found for report {report_id}")

        # Fetch user profile
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Fetch medical profile if available
        medical_profile = db.medical_profiles.find_one({"user_id": user_id})

        # Build a clean markers dict (exclude metadata fields)
        excluded_keys = {"_id", "user_id", "report_id", "extracted_at"}
        markers = {
            k: v
            for k, v in biomarker_doc.items()
            if k not in excluded_keys and isinstance(v, (int, float))
        }

        gender = (user.get("gender") or "male").lower()

        # --- Deterministic rule engine ---
        rule_engine = LabInterpretationService()
        rule_result = rule_engine.interpret(markers, gender)

        logger.info(
            "Rule engine: %d deficiencies, %d risks, %d warnings for report %s",
            len(rule_result["deficiencies"]),
            len(rule_result["risk_factors"]),
            len(rule_result["warnings"]),
            report_id,
        )

        # --- AI-powered interpretation ---
        user_context = dict(user)
        user_context.pop("_id", None)
        user_context.pop("hashed_password", None)
        if medical_profile:
            user_context["conditions"] = medical_profile.get("conditions", [])
            user_context["medications"] = medical_profile.get("medications", [])
            user_context["allergies"] = medical_profile.get("allergies", [])

        ai_result: dict = {}
        try:
            prompt = _build_analysis_prompt(markers, user_context)
            raw_response = _call_llm_sync(prompt)
            ai_result = _parse_llm_json(raw_response)
            logger.info("LLM analysis completed for report %s", report_id)
        except Exception as llm_exc:
            logger.warning(
                "LLM analysis failed for report %s, proceeding with rules only: %s",
                report_id,
                llm_exc,
            )
            ai_result = {"error": str(llm_exc)}

        # --- Combine results ---
        combined_analysis = {
            "report_id": report_id,
            "user_id": user_id,
            "biomarker_id": str(biomarker_doc["_id"]),
            "rule_engine": rule_result,
            "ai_interpretation": ai_result,
            "analyzed_at": datetime.now(timezone.utc),
        }

        # Upsert analysis document
        db.analyses.update_one(
            {"report_id": report_id},
            {"$set": combined_analysis},
            upsert=True,
        )

        # Update report status
        db.reports.update_one(
            {"_id": report_oid},
            {
                "$set": {
                    "status": "analyzed",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        # Chain to recommendation generation
        from app.workers.recommendation_worker import generate_recommendations

        generate_recommendations.delay(report_id, user_id)

    except Exception as exc:
        logger.exception("Analysis failed for report %s", report_id)
        db.reports.update_one(
            {"_id": report_oid},
            {
                "$set": {
                    "status": "failed",
                    "error": str(exc),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        raise self.retry(exc=exc, countdown=60)
