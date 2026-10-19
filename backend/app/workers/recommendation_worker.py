"""
Recommendation generation worker.

Reads biomarkers, analysis, and user/medical profiles, then calls the LLM
to generate a personalised diet plan, workout plan, and supplement
suggestions.  Stores all outputs in MongoDB and creates a notification.
"""

import json
import logging
import re
from datetime import UTC, datetime

import httpx
from bson import ObjectId
from pymongo import MongoClient

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.generation_metrics import (
    OUTCOME_FALLBACK,
    OUTCOME_LLM_REPAIRED,
    OUTCOME_LLM_VERIFIED,
    record_generation,
)
from app.services.plan_grounding import (
    clinical_priority_names,
    daily_calorie_target,
    format_exercise_catalogue,
    format_food_catalogue,
    select_exercises,
    select_foods,
)
from app.services.suggestion_engine import build_suggestions

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = settings.LLM_TIMEOUT_SECONDS


def _get_db():
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB_NAME]


def _call_llm_sync(prompt: str) -> str:
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False}
    response = httpx.post(url, json=payload, timeout=LLM_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get("response", "")


def _strip_json_comments(text: str) -> str:
    """
    Remove // line comments and /* */ blocks that local models routinely emit
    inside otherwise-valid JSON, without touching sequences inside string
    literals (e.g. "https://..."). Also drops trailing commas.
    """
    out: list[str] = []
    i, n = 0, len(text)
    in_string = False
    escaped = False

    while i < n:
        ch = text[i]

        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
        elif ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
        else:
            out.append(ch)
            i += 1

    # Trailing commas before a closing brace/bracket.
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def _parse_llm_json(text: str) -> dict | list:
    """Best-effort JSON extraction from LLM output."""
    # Try object first, then array
    for open_char, close_char in [("{", "}"), ("[", "]")]:
        try:
            start = text.index(open_char)
            end = text.rindex(close_char) + 1
        except ValueError:
            continue
        candidate = text[start:end]
        for attempt in (candidate, _strip_json_comments(candidate)):
            try:
                return json.loads(attempt)
            except (ValueError, json.JSONDecodeError):
                continue
    return {"raw_response": text}


def _extract_workout_days(workout_plan) -> list:
    """
    Pull the per-day list out of an LLM workout plan.

    Models variously return {"plan": [...]}, {"days": [...]}, or the bare list.
    """
    if isinstance(workout_plan, list):
        candidate = workout_plan
    elif isinstance(workout_plan, dict):
        candidate = workout_plan.get("plan") or workout_plan.get("days") or []
    else:
        return []
    if not isinstance(candidate, list):
        return []
    return [d for d in candidate if isinstance(d, dict) and d.get("exercises")]


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

    foods = select_foods(
        preference=user.get("dietary_preference") or "non_vegetarian",
        allergies=user.get("allergies") or [],
        rule_engine=analysis.get("rule_engine", {}),
    )
    catalogue = format_food_catalogue(foods, clinical_priority_names(foods, analysis.get("rule_engine", {})))
    target = daily_calorie_target(user)

    return (
        f"Create a 3-day diet plan for a {age}-year-old {gender}, "
        f"{weight}kg, {height}cm, activity level: {activity}.\n"
        f"Goals: {goals}.\n"
        f"Allergies: {allergies}. Conditions: {conditions}.\n"
        f"Lab findings: {findings_text}.\n\n"
        f"DAILY TARGET: about {target} kcal per day, with roughly "
        f"{round(target * 0.30 / 4)}g protein, {round(target * 0.40 / 4)}g carbs "
        f"and {round(target * 0.30 / 9)}g fat.\n\n"
        f"You may ONLY use foods from this catalogue, referenced by their exact "
        f"name. It is grouped by category and already filtered for this "
        f"person's dietary preference, allergies and lab findings. Items marked "
        f"with * are especially useful given their lab results:\n{catalogue}\n\n"
        f"RULES:\n"
        f"- Use exact names from the catalogue. Never invent a food.\n"
        f'- Give each portion as a number of grams in "quantity_g".\n'
        f"- Do NOT output calories or macros. They are calculated from the "
        f"catalogue and any numbers you write are discarded.\n"
        f"- Every day must total close to the daily target above. Use realistic "
        f"portions: a main protein is 100-200g, a grain 50-150g dry, "
        f"vegetables 100-200g, nuts/seeds 15-30g, oils 5-15g.\n"
        f"- Build balanced meals: each main meal needs a protein, a carbohydrate "
        f"and a vegetable. Never build a meal from oils, nuts or seeds alone.\n"
        f"- Work in a few starred items across the week, without letting them "
        f"crowd out normal meals.\n"
        f"- Output all 3 days, each with breakfast, mid-morning snack, lunch, "
        f"evening snack and dinner.\n\n"
        f"Return valid JSON with this structure:\n"
        f'{{"goal": "...", "meal_plan": [{{"day": "Monday", '
        f'"meals": [{{"name": "Breakfast", "time": "8:00 AM", "foods": '
        f'[{{"name": "Oats (dry)", "quantity_g": 60}}]}}]}}]}}'
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

    catalogue = format_exercise_catalogue(
        select_exercises(
            difficulty=user.get("fitness_level") or "intermediate",
            equipment=user.get("equipment") or None,
            rule_engine=analysis.get("rule_engine", {}),
        )
    )

    return (
        f"Create a 5-day weekly workout plan for a {age}-year-old {gender}, {weight}kg.\n"
        f"Goals: {goals}. Conditions: {conditions}. Injuries: {injuries}.\n"
        f"Health considerations: {health_text}.\n\n"
        f"You may ONLY use exercises from this catalogue, referenced by their "
        f"exact name. It has already been filtered for this person's fitness "
        f"level and lab findings (for example intensity is capped when markers "
        f"indicate anemia):\n{catalogue}\n\n"
        f"RULES:\n"
        f"- Use exact names from the catalogue. Never invent an exercise.\n"
        f"- Do NOT write form or technique instructions. They come from the "
        f"catalogue and anything you write is discarded.\n"
        f"- Group each day by muscle group and give sets, reps and rest.\n"
        f"- Include a warm-up and cool-down description for each day.\n\n"
        f"Return valid JSON:\n"
        f'{{"goal": "...", "difficulty": "intermediate", "days_per_week": 5, '
        f'"plan": [{{"day_name": "Day 1 - Push", "warm_up": "...", '
        f'"cool_down": "...", "exercises": '
        f'[{{"name": "Push-ups", "sets": 4, "reps": "8-10", "rest": "90s"}}]}}]}}'
    )


def _build_supplement_prompt(user: dict, markers: dict, analysis: dict) -> str:
    deficiencies = analysis.get("rule_engine", {}).get("deficiencies", [])
    risks = analysis.get("rule_engine", {}).get("risk_factors", [])
    conditions = ", ".join(user.get("conditions", [])) or "none"
    medications = ", ".join(user.get("medications", [])) or "none"

    deficiency_text = "; ".join(f"{d['label']} ({d['marker']}: {d['value']})" for d in deficiencies) or "none"
    risk_text = "; ".join(f"{r['label']} ({r['marker']}: {r['value']})" for r in risks) or "none"

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
    now = datetime.now(UTC)

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
        markers = {k: v for k, v in biomarker_doc.items() if k not in excluded_keys and isinstance(v, (int, float))}

        # ---- Build nutrition and training suggestions ----
        # Full day-by-day diet and workout plans are NOT generated here. Most
        # people want to know what to change before they want a seven-day meal
        # schedule, and generating both up front cost several minutes of LLM
        # time per report that most users never looked at. The endpoints in
        # `nutrition.py` / `fitness.py` produce a full plan when one is asked
        # for. Suggestions are deterministic, so this step is instant.
        logger.info("Building suggestions for report %s", report_id)
        suggestions = build_suggestions(
            user=user_ctx,
            rule_engine=analysis.get("rule_engine", {}),
            goal=(user_ctx.get("goals") or ["maintenance"])[0],
            dietary_preference=user_ctx.get("dietary_preference") or "non_vegetarian",
            allergies=user_ctx.get("allergies") or [],
            conditions=user_ctx.get("conditions") or [],
            fitness_level=user_ctx.get("fitness_level") or "beginner",
        )
        db.suggestions.replace_one(
            {"report_id": report_id},
            {
                "user_id": user_id,
                "report_id": report_id,
                "created_at": now,
                **suggestions,
            },
            upsert=True,
        )
        record_generation(
            db,
            kind="suggestions",
            outcome=OUTCOME_LLM_VERIFIED,
            user_id=user_id,
            report_id=report_id,
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
            "deficiencies": [d["label"] for d in analysis.get("rule_engine", {}).get("deficiencies", [])],
            "risk_factors": [r["label"] for r in analysis.get("rule_engine", {}).get("risk_factors", [])],
            # Now genuinely dietary *suggestions* rather than a meal plan.
            "dietary_suggestions": [
                {"label": e["label"], "why": e["why"], "examples": e.get("examples", [])}
                for e in suggestions["nutrition"]["emphasise"]
            ],
            "foods_to_limit": [{"label": e["label"], "why": e["why"]} for e in suggestions["nutrition"]["limit"]],
            "training_suggestions": [
                {"label": t["label"], "why": t["why"], "examples": t.get("examples", [])}
                for t in suggestions["training"]["focus"]
            ],
            "supplement_suggestions": supplements if isinstance(supplements, list) else [],
            "warnings": [w["label"] for w in analysis.get("rule_engine", {}).get("warnings", [])],
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
            "report_id": report_id,
            "type": "report_completed",
            "title": "Report Analysis Complete",
            "message": (
                "Your lab report has been fully analysed. "
                "View your personalised diet plan, workout plan, and supplement "
                "recommendations now."
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
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        raise self.retry(exc=exc, countdown=60) from exc


# ---------------------------------------------------------------------------
# On-request full plans
# ---------------------------------------------------------------------------
#
# These are NOT part of the report pipeline. A report produces suggestions; a
# full day-by-day plan is built only when the user asks for one, and when it is
# built from a report it uses that report's findings so the plan reflects the
# person's actual labs rather than their profile alone.


def _load_report_context(db, report_id: str, user_id: str) -> tuple[dict, dict, dict]:
    """Return (user_context, markers, analysis) for a completed report."""
    user_doc = db.users.find_one({"_id": ObjectId(user_id)}) or {}
    user_doc.pop("hashed_password", None)
    profile = db.medical_profiles.find_one({"user_id": user_id}) or {}
    user_ctx = {
        **{k: v for k, v in user_doc.items() if k != "_id"},
        "allergies": profile.get("allergies", []),
        "conditions": profile.get("chronic_conditions", []),
        # "dietary_preferences" is the key older profiles were written with.
        "dietary_preference": profile.get("dietary_preference") or profile.get("dietary_preferences"),
    }

    biomarker_doc = db.biomarkers.find_one({"report_id": report_id}) or {}
    exclude = {"_id", "user_id", "report_id", "extracted_at"}
    markers = {k: v for k, v in biomarker_doc.items() if k not in exclude and isinstance(v, (int, float))}
    analysis = db.analyses.find_one({"report_id": report_id}) or {}
    return user_ctx, markers, analysis


@celery_app.task(name="tasks.generate_diet_plan_on_request", bind=True, max_retries=2)
def generate_diet_plan_on_request(self, report_id: str, user_id: str):
    """Build a full diet plan for a report, on the user's explicit request."""
    from app.services.diet_templates import build_fallback_meal_plan
    from app.services.plan_grounding import (
        plan_is_nutritionally_adequate,
        verify_diet_plan,
    )

    db = _get_db()
    now = datetime.now(UTC)
    try:
        user_ctx, markers, analysis = _load_report_context(db, report_id, user_id)

        warnings: list[str] = []
        try:
            raw = _call_llm_sync(_build_diet_prompt(user_ctx, markers, analysis))
            plan = _parse_llm_json(raw)
            plan, warnings = verify_diet_plan(plan)
        except Exception as exc:
            logger.warning("Diet plan LLM call failed for report %s: %s", report_id, exc)
            plan = {"error": str(exc)}

        target = daily_calorie_target(user_ctx)
        adequate, reasons = plan_is_nutritionally_adequate(plan, target)
        outcome = (
            OUTCOME_LLM_REPAIRED if (adequate and warnings) else OUTCOME_LLM_VERIFIED if adequate else OUTCOME_FALLBACK
        )
        if not adequate:
            logger.info("Diet plan fell back to templates for report %s: %s", report_id, reasons[:5])
            plan = build_fallback_meal_plan(
                weight_kg=user_ctx.get("weight") or 70,
                height_cm=user_ctx.get("height") or 170,
                age=user_ctx.get("age") or 30,
                gender=user_ctx.get("gender") or "male",
                activity_level=user_ctx.get("activity_level") or "moderate",
                goal=(user_ctx.get("goals") or ["maintenance"])[0],
                dietary_preference=user_ctx.get("dietary_preference") or "vegetarian",
                conditions=user_ctx.get("conditions") or [],
            )

        db.diet_plans.replace_one(
            {"report_id": report_id},
            {
                "user_id": user_id,
                "report_id": report_id,
                "created_at": now,
                "requested": True,
                **(plan if isinstance(plan, dict) else {}),
            },
            upsert=True,
        )
        record_generation(
            db,
            kind="diet",
            outcome=outcome,
            user_id=user_id,
            report_id=report_id,
            dropped=warnings,
            reasons=reasons,
            model=settings.OLLAMA_MODEL,
        )
        logger.info("Diet plan ready for report %s (%s)", report_id, outcome)
    except Exception as exc:
        logger.error("Diet plan generation failed for report %s", report_id, exc_info=True)
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(name="tasks.generate_workout_plan_on_request", bind=True, max_retries=2)
def generate_workout_plan_on_request(self, report_id: str, user_id: str):
    """Build a full workout plan for a report, on the user's explicit request."""
    from app.services.plan_grounding import verify_workout_plan
    from app.services.workout_templates import build_fallback_days

    db = _get_db()
    now = datetime.now(UTC)
    try:
        user_ctx, markers, analysis = _load_report_context(db, report_id, user_id)

        warnings: list[str] = []
        try:
            raw = _call_llm_sync(_build_workout_prompt(user_ctx, markers, analysis))
            parsed = _parse_llm_json(raw)
        except Exception as exc:
            logger.warning("Workout plan LLM call failed for report %s: %s", report_id, exc)
            parsed = {"error": str(exc)}

        days, warnings = verify_workout_plan(_extract_workout_days(parsed))
        outcome = OUTCOME_LLM_REPAIRED if (days and warnings) else OUTCOME_LLM_VERIFIED if days else OUTCOME_FALLBACK
        if not days:
            logger.info("Workout plan fell back to templates for report %s", report_id)
            days, _ = verify_workout_plan(
                build_fallback_days(
                    age=user_ctx.get("age") or 30,
                    gender=user_ctx.get("gender") or "male",
                    weight_kg=user_ctx.get("weight") or 70,
                    height_cm=user_ctx.get("height") or 170,
                    fitness_level=user_ctx.get("fitness_level") or "beginner",
                    goal=(user_ctx.get("goals") or ["general_fitness"])[0],
                    conditions=user_ctx.get("conditions") or [],
                )
            )

        db.workout_plans.replace_one(
            {"report_id": report_id},
            {
                "user_id": user_id,
                "report_id": report_id,
                "created_at": now,
                "requested": True,
                # Spread the model's metadata (goal, difficulty, days_per_week)
                # first so the verified day list below always wins.
                **(parsed if isinstance(parsed, dict) and "error" not in parsed else {}),
                "days": days,
                "plan": days,
            },
            upsert=True,
        )
        record_generation(
            db,
            kind="workout",
            outcome=outcome,
            user_id=user_id,
            report_id=report_id,
            dropped=warnings,
            model=settings.OLLAMA_MODEL,
        )
        logger.info("Workout plan ready for report %s (%s)", report_id, outcome)
    except Exception as exc:
        logger.error("Workout plan generation failed for report %s", report_id, exc_info=True)
        raise self.retry(exc=exc, countdown=60) from exc
