"""
Lab analysis worker.

Reads extracted biomarkers and user profile, runs both a deterministic rule
engine and an LLM-based AI interpretation, combines the results, and chains
to the recommendation task.
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
from app.services.lab_interpretation_service import (
    LabInterpretationService,
    canonicalise_marker,
)

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = settings.LLM_TIMEOUT_SECONDS


def _get_db():
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB_NAME]


def _call_llm_sync(prompt: str) -> str:
    """Synchronous call to Ollama for use inside Celery tasks."""
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    response = httpx.post(url, json=payload, timeout=LLM_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get("response", "")


def _build_analysis_prompt(markers: dict, user: dict, rule_result: dict | None = None) -> str:
    """
    Build a prompt for AI-powered biomarker interpretation.

    The deterministic rule engine's verdict is included as ground truth. Without
    it the model has to guess each reference range and routinely calls abnormal
    results "within normal range", directly contradicting the rule engine shown
    alongside it in the UI.
    """
    age = user.get("age", "unknown")
    gender = user.get("gender", "unknown")
    weight = user.get("weight", "unknown")
    height = user.get("height", "unknown")
    conditions = user.get("conditions", [])
    conditions_text = ", ".join(conditions) if conditions else "none reported"

    details = (rule_result or {}).get("marker_details", {}) or {}
    lines: list[str] = []
    for name, value in markers.items():
        d = details.get(name) or details.get(canonicalise_marker(name)) or {}
        status = str(d.get("status", "")).upper() or "NOT CLASSIFIED"
        unit = d.get("unit") or ""
        rng = d.get("range")
        range_text = f", reference {rng} {unit}".rstrip() if rng else ", no reference range available"
        lines.append(f"  - {name}: {value} {unit}".rstrip() + f"{range_text} -> {status}")
    markers_text = "\n".join(lines)

    flagged = [f["label"] for f in (rule_result or {}).get("deficiencies", []) if f.get("label")]
    flagged += [f["label"] for f in (rule_result or {}).get("risk_factors", []) if f.get("label")]
    flagged += [f["label"] for f in (rule_result or {}).get("warnings", []) if f.get("label")]
    findings_text = "\n".join(f"  - {f}" for f in flagged) or "  - none"

    return (
        f"You are a clinical lab analysis assistant. Interpret the following biomarker "
        f"results for a {age}-year-old {gender}, {weight}kg, {height}cm tall.\n"
        f"Known conditions: {conditions_text}.\n\n"
        f"Biomarker values. The status after each arrow was computed from the "
        f"reference range and is AUTHORITATIVE:\n{markers_text}\n\n"
        f"Findings already established by the rule engine:\n{findings_text}\n\n"
        f"RULES:\n"
        f"- Never describe a marker marked LOW or HIGH as normal, healthy, or "
        f"within range. Treat the statuses above as fact.\n"
        f"- Do not invent values or reference ranges. Use only what is listed.\n"
        f"- Say nothing about markers not listed above.\n\n"
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


#: Phrases that assert a marker is fine. Used to spot LLM output that
#: contradicts the rule engine.
_NORMAL_CLAIM_RE = re.compile(
    r"\b(?:within\s+(?:the\s+)?normal|within\s+(?:the\s+)?reference|"
    r"within\s+range|in\s+(?:the\s+)?normal\s+range|normal\s+range|"
    r"are\s+normal|is\s+normal|were\s+normal|was\s+normal|"
    r"appears?\s+normal|remains?\s+normal|no\s+abnormalit|unremarkable|"
    r"healthy\s+range|optimal\s+range)\b",
    re.IGNORECASE,
)


def _marker_aliases(canonical: str) -> list[str]:
    """Surface forms an LLM might use for a canonical marker name."""
    words = canonical.replace("_", " ")
    aliases = {canonical, words, words.replace(" ", "")}
    extra = {
        "fasting_sugar": ["fasting glucose", "blood sugar", "glucose"],
        "vitamin_b12": ["vitamin b12", "b12", "b-12"],
        "vitamin_d": ["vitamin d", "25-oh", "25 oh"],
        "hdl": ["hdl", "hdl cholesterol", "good cholesterol"],
        "ldl": ["ldl", "ldl cholesterol", "bad cholesterol"],
        "total_cholesterol": ["total cholesterol", "cholesterol"],
        "tsh": ["tsh", "thyroid stimulating hormone"],
        "hemoglobin": ["hemoglobin", "haemoglobin", "hb", "hgb"],
        "ferritin": ["ferritin", "serum ferritin"],
        "triglycerides": ["triglycerides", "trigs"],
    }
    aliases.update(extra.get(canonical, []))
    return [a for a in aliases if len(a) > 2]


def _drop_contradictions(ai_result: dict, rule_result: dict) -> tuple[dict, list[str]]:
    """
    Remove AI statements that call a flagged biomarker normal.

    The rule engine is deterministic and authoritative; the LLM is not. Shipping
    both means a model that says "hemoglobin 11.2 is within normal range" would
    sit directly beside an "Anemia (low hemoglobin)" finding. Rather than trust
    the prompt alone, drop the contradicting statements and record what was
    removed.
    """
    if not isinstance(ai_result, dict) or not ai_result:
        return ai_result, []

    details = (rule_result or {}).get("marker_details", {}) or {}
    abnormal = [name for name, d in details.items() if str(d.get("status", "")).lower() in ("low", "high")]
    if not abnormal:
        return ai_result, []

    alias_map = {name: _marker_aliases(name) for name in abnormal}

    def contradicts(text: str) -> bool:
        if not _NORMAL_CLAIM_RE.search(text):
            return False
        lowered = text.lower()
        return any(
            re.search(rf"\b{re.escape(alias)}\b", lowered) for aliases in alias_map.values() for alias in aliases
        )

    cleaned = dict(ai_result)
    removed: list[str] = []
    for key in ("key_findings", "health_risks", "follow_up_tests", "lifestyle_suggestions"):
        items = cleaned.get(key)
        if not isinstance(items, list):
            continue
        kept = []
        for item in items:
            if isinstance(item, str) and contradicts(item):
                removed.append(item)
            else:
                kept.append(item)
        cleaned[key] = kept

    summary = cleaned.get("summary")
    if isinstance(summary, str) and contradicts(summary):
        removed.append(summary)
        cleaned["summary"] = ""

    return cleaned, removed


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
        markers = {k: v for k, v in biomarker_doc.items() if k not in excluded_keys and isinstance(v, (int, float))}

        gender = (user.get("gender") or "male").lower()

        # --- Deterministic rule engine ---
        rule_engine = LabInterpretationService()
        rule_result = rule_engine.interpret(markers, gender, reported=biomarker_doc.get("as_reported"))

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
            prompt = _build_analysis_prompt(markers, user_context, rule_result)
            raw_response = _call_llm_sync(prompt)
            ai_result = _parse_llm_json(raw_response)
            ai_result, dropped = _drop_contradictions(ai_result, rule_result)
            if dropped:
                logger.warning(
                    "Dropped %d AI statement(s) contradicting the rule engine for report %s: %s",
                    len(dropped),
                    report_id,
                    dropped,
                )
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
            "analyzed_at": datetime.now(UTC),
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
                    "updated_at": datetime.now(UTC),
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
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        raise self.retry(exc=exc, countdown=60) from exc
