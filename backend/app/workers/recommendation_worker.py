"""
Recommendation generation worker.

Reads biomarkers, analysis, and user/medical profiles, then calls the LLM
to generate a personalised diet plan, workout plan, and supplement
suggestions.  Stores all outputs in MongoDB and creates a notification.
"""

import json
import logging
from datetime import datetime, timezone

import httpx
from bson import ObjectId
from pymongo import MongoClient

from app.core.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 120.0


def _get_db():
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB_NAME]


def _call_llm_sync(prompt: str) -> str:
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False}
    response = httpx.post(url, json=payload, timeout=LLM_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get("response", "")


def _parse_llm_json(text: str) -> dict | list:
    """Best-effort JSON extraction from LLM output."""
    # Try object first, then array
    for open_char, close_char in [("{", "}"), ("[", "]")]:
        try:
            start = text.index(open_char)
            end = text.rindex(close_char) + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            continue
    return {"raw_response": text}


def _build_diet_prompt(user: dict, markers: dict, analysis: dict) -> str:
    age = user.get("age", 30)
    gender = user.get("gender", "male")
    weight = user.get("weight", 70)
    height = user.get("height", 170)
    activity = user.get("activity_level", "moderate")
    goals = ", ".join(user.get("goals", [])) or "general wellness"
    allergies = ", ".join(user.get("allergies", [])) or "none"
    conditions = ", ".join(user.get("conditions", [])) or "none"

    deficiencies = [d["label"] for d in analysis.get("rule_engine", {}).get("deficiencies", [])]
    risks = [r["label"] for r in analysis.get("rule_engine", {}).get("risk_factors", [])]
    findings = deficiencies + risks

    findings_text = "; ".join(findings) if findings else "no significant findings"

    return (
        f"Create a detailed 7-day diet plan for a {age}-year-old {gender}, "
        f"{weight}kg, {height}cm, activity level: {activity}.\n"
        f"Goals: {goals}.\n"
        f"Allergies: {allergies}. Conditions: {conditions}.\n"
        f"Lab findings: {findings_text}.\n\n"
        f"For each day provide breakfast, mid-morning snack, lunch, evening snack, "
        f"and dinner with specific food items, quantities, and approximate calories.\n"
        f"Return valid JSON with this structure:\n"
        f'{{"goal": "...", "calories": 2000, "macros": {{"protein_g": 120, '
        f'"carbs_g": 200, "fat_g": 70}}, "meal_plan": [{{"day": "Monday", '
        f'"meals": [{{"name": "Breakfast", "time": "8:00 AM", "foods": '
        f'[{{"name": "Oatmeal", "quantity": "1 cup", "calories": 150}}]}}]}}]}}'
    )


def _build_workout_prompt(user: dict, markers: dict, analysis: dict) -> str:
    age = user.get("age", 30)
    gender = user.get("gender", "male")
    weight = user.get("weight", 70)
    goals = ", ".join(user.get("goals", [])) or "general fitness"
    conditions = ", ".join(user.get("conditions", [])) or "none"
    injuries = ", ".join(user.get("injuries", [])) or "none"

    risks = [r["label"] for r in analysis.get("rule_engine", {}).get("risk_factors", [])]
    warnings = [w["label"] for w in analysis.get("rule_engine", {}).get("warnings", [])]
    health_notes = risks + warnings
    health_text = "; ".join(health_notes) if health_notes else "no concerns"

    return (
        f"Create a 5-day weekly workout plan for a {age}-year-old {gender}, {weight}kg.\n"
        f"Goals: {goals}. Conditions: {conditions}. Injuries: {injuries}.\n"
        f"Health considerations: {health_text}.\n\n"
        f"For each day provide exercises with sets, reps, and rest. "
        f"Include warm-up and cool-down.\n"
        f"Return valid JSON:\n"
        f'{{"goal": "...", "difficulty": "intermediate", "days_per_week": 5, '
        f'"plan": [{{"day_name": "Day 1 - Push", "exercises": '
        f'[{{"name": "Bench Press", "sets": 4, "reps": "8-10", "rest": "90s"}}]}}]}}'
    )


def _build_supplement_prompt(user: dict, markers: dict, analysis: dict) -> str:
    deficiencies = analysis.get("rule_engine", {}).get("deficiencies", [])
    risks = analysis.get("rule_engine", {}).get("risk_factors", [])
    conditions = ", ".join(user.get("conditions", [])) or "none"
    medications = ", ".join(user.get("medications", [])) or "none"

    deficiency_text = "; ".join(
        f"{d['label']} ({d['marker']}: {d['value']})" for d in deficiencies
    ) or "none"
    risk_text = "; ".join(
        f"{r['label']} ({r['marker']}: {r['value']})" for r in risks
    ) or "none"

    return (
        f"Based on the following lab results, suggest appropriate supplements.\n"
        f"Deficiencies: {deficiency_text}.\n"
        f"Risk factors: {risk_text}.\n"
        f"Conditions: {conditions}. Current medications: {medications}.\n\n"
        f"For each supplement provide name, dosage, timing, and notes.\n"
        f"Only suggest non-prescription supplements. Flag any interactions.\n"
        f"Return valid JSON list:\n"
        f'[{{"name": "Vitamin D3", "dosage": "2000 IU daily", '
        f'"timing": "with breakfast", "notes": "Take with fat-containing meal"}}]'
    )


@celery_app.task(name="tasks.generate_recommendations", bind=True, max_retries=3)
def generate_recommendations(self, report_id: str, user_id: str):
    """
    1. Read biomarkers, analysis, user profile, and medical profile.
    2. Generate diet plan via LLM.
    3. Generate workout plan via LLM.
    4. Generate supplement suggestions via LLM.
    5. Store all outputs in MongoDB.
    6. Update report status to 'completed'.
    7. Create a notification for the user.
    """
    db = _get_db()
    report_oid = ObjectId(report_id)
    now = datetime.now(timezone.utc)

    logger.info("Starting recommendation generation for report %s, user %s", report_id, user_id)

    try:
        # ---- Gather context ----
        report = db.reports.find_one({"_id": report_oid})
        if not report:
            raise ValueError(f"Report {report_id} not found")

        biomarker_doc = db.biomarkers.find_one({"report_id": report_id})
        if not biomarker_doc:
            raise ValueError(f"No biomarkers found for report {report_id}")

        analysis = db.analyses.find_one({"report_id": report_id})
        if not analysis:
            raise ValueError(f"No analysis found for report {report_id}")

        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError(f"User {user_id} not found")

        medical_profile = db.medical_profiles.find_one({"user_id": user_id})

        # Build enriched user context
        user_ctx = {
            "age": user.get("age"),
            "gender": user.get("gender"),
            "weight": user.get("weight"),
            "height": user.get("height"),
            "activity_level": user.get("activity_level"),
            "goals": user.get("goals", []),
            "conditions": medical_profile.get("conditions", []) if medical_profile else [],
            "allergies": medical_profile.get("allergies", []) if medical_profile else [],
            "injuries": medical_profile.get("injuries", []) if medical_profile else [],
            "medications": medical_profile.get("medications", []) if medical_profile else [],
        }

        excluded_keys = {"_id", "user_id", "report_id", "extracted_at"}
        markers = {
            k: v
            for k, v in biomarker_doc.items()
            if k not in excluded_keys and isinstance(v, (int, float))
        }

        # ---- Generate diet plan ----
        logger.info("Generating diet plan for report %s", report_id)
        try:
            diet_raw = _call_llm_sync(_build_diet_prompt(user_ctx, markers, analysis))
            diet_plan = _parse_llm_json(diet_raw)
        except Exception as diet_exc:
            logger.warning("Diet plan LLM call failed: %s", diet_exc)
            diet_plan = {"error": str(diet_exc)}

        diet_doc = {
            "user_id": user_id,
            "report_id": report_id,
            "plan": diet_plan,
            "created_at": now,
        }
        db.diet_plans.update_one(
            {"report_id": report_id},
            {"$set": diet_doc},
            upsert=True,
        )

        # ---- Generate workout plan ----
        logger.info("Generating workout plan for report %s", report_id)
        try:
            workout_raw = _call_llm_sync(_build_workout_prompt(user_ctx, markers, analysis))
            workout_plan = _parse_llm_json(workout_raw)
        except Exception as workout_exc:
            logger.warning("Workout plan LLM call failed: %s", workout_exc)
            workout_plan = {"error": str(workout_exc)}

        workout_doc = {
            "user_id": user_id,
            "report_id": report_id,
            "plan": workout_plan,
            "created_at": now,
        }
        db.workout_plans.update_one(
            {"report_id": report_id},
            {"$set": workout_doc},
            upsert=True,
        )

        # ---- Generate supplement suggestions ----
        logger.info("Generating supplement suggestions for report %s", report_id)
        try:
            supp_raw = _call_llm_sync(_build_supplement_prompt(user_ctx, markers, analysis))
            supplements = _parse_llm_json(supp_raw)
        except Exception as supp_exc:
            logger.warning("Supplement LLM call failed: %s", supp_exc)
            supplements = {"error": str(supp_exc)}

        # Store recommendations document
        recommendation_doc = {
            "user_id": user_id,
            "report_id": report_id,
            "biomarker_id": str(biomarker_doc["_id"]),
            "deficiencies": [
                d["label"] for d in analysis.get("rule_engine", {}).get("deficiencies", [])
            ],
            "risk_factors": [
                r["label"] for r in analysis.get("rule_engine", {}).get("risk_factors", [])
            ],
            "dietary_suggestions": (
                diet_plan.get("meal_plan", []) if isinstance(diet_plan, dict) else []
            ),
            "supplement_suggestions": supplements if isinstance(supplements, list) else [],
            "warnings": [
                w["label"] for w in analysis.get("rule_engine", {}).get("warnings", [])
            ],
            "generated_at": now,
        }
        db.recommendations.update_one(
            {"report_id": report_id},
            {"$set": recommendation_doc},
            upsert=True,
        )

        # ---- Update report status ----
        db.reports.update_one(
            {"_id": report_oid},
            {
                "$set": {
                    "status": "completed",
                    "processed_at": now,
                    "updated_at": now,
                }
            },
        )

        # ---- Create notification ----
        notification = {
            "user_id": user_id,
            "type": "report_completed",
            "title": "Report Analysis Complete",
            "message": (
                f"Your lab report has been fully analysed. "
                f"View your personalised diet plan, workout plan, and supplement "
                f"recommendations now."
            ),
            "read": False,
            "created_at": now,
        }
        db.notifications.insert_one(notification)

        logger.info("Recommendation generation completed for report %s", report_id)

    except Exception as exc:
        logger.exception("Recommendation generation failed for report %s", report_id)
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
