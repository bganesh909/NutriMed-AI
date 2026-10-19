"""
Nutrition and training suggestions.

This is the default output of the product: what to eat more of, what to cut
back on, and how to train -- derived from lab findings where a report exists,
and from the profile, goal and self-reported conditions where one does not.

Full day-by-day diet and workout plans are deliberately not returned here. They
are generated only when the user explicitly asks, via the endpoints below.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user, get_db
from app.services.lab_interpretation_service import LabInterpretationService
from app.services.suggestion_engine import build_suggestions
from app.utils.validators import to_object_id

router = APIRouter(prefix="/suggestions")


class SuggestionRequest(BaseModel):
    """
    Everything is optional: the profile fills in what the caller omits, and
    `missing_info` in the response says what would sharpen the result.
    """

    goal: str | None = Field(
        None, description="fat_loss, muscle_gain, weight_gain, recomposition, endurance, strength, maintenance"
    )
    report_id: str | None = Field(None, description="Base suggestions on this report's biomarkers")
    conditions: list[str] = Field(default_factory=list, description="Self-reported, e.g. diabetes, thyroid, PCOS")
    allergies: list[str] = Field(default_factory=list)
    dietary_preference: str | None = Field(None, description="vegetarian, vegan, eggetarian, non_vegetarian")
    fitness_level: str | None = Field(None, description="beginner, intermediate, advanced")
    # Optional overrides for users who have not filled in their profile.
    age: int | None = Field(None, ge=1, le=120)
    gender: str | None = None
    weight: float | None = Field(None, ge=20, le=400)
    height: float | None = Field(None, ge=80, le=250)
    activity_level: str | None = None


async def _user_context(db, current_user: dict, body: SuggestionRequest) -> dict:
    """Merge the stored profile with any overrides supplied in the request."""
    user_doc = await db["users"].find_one({"_id": to_object_id(current_user["id"], "User")}) or {}
    profile = await db["medical_profiles"].find_one({"user_id": current_user["id"]}) or {}

    context = {k: v for k, v in user_doc.items() if k not in ("_id", "hashed_password")}
    context.setdefault("conditions", profile.get("chronic_conditions", []))
    context.setdefault("allergies", profile.get("allergies", []))

    for field in ("age", "gender", "weight", "height", "activity_level"):
        override = getattr(body, field)
        if override is not None:
            context[field] = override
    return context


@router.post("", status_code=status.HTTP_200_OK)
async def get_suggestions(
    body: SuggestionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Nutrition and training suggestions, with or without a lab report.

    Pass `report_id` to ground the advice in measured biomarkers. Without it,
    the advice comes from the profile, goal and any reported conditions.
    """
    context = await _user_context(db, current_user, body)

    rule_engine = None
    if body.report_id:
        report = await db["reports"].find_one(
            {
                "_id": to_object_id(body.report_id, "Report"),
                "user_id": current_user["id"],
            }
        )
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

        analysis = await db["analyses"].find_one({"report_id": body.report_id})
        rule_engine = (analysis or {}).get("rule_engine")
        if rule_engine is None:
            # Analysis has not run yet; derive it from the biomarkers we have.
            biomarkers = await db["biomarkers"].find_one({"report_id": body.report_id})
            if biomarkers:
                exclude = {"_id", "user_id", "report_id", "extracted_at"}
                markers = {k: v for k, v in biomarkers.items() if k not in exclude and isinstance(v, (int, float))}
                if markers:
                    rule_engine = LabInterpretationService().interpret(
                        markers,
                        (context.get("gender") or "male").lower(),
                        reported=biomarkers.get("as_reported"),
                    )

    goals = context.get("goals") or []
    return build_suggestions(
        user=context,
        rule_engine=rule_engine,
        goal=body.goal or (goals[0] if goals else "maintenance"),
        dietary_preference=(body.dietary_preference or context.get("dietary_preference") or "non_vegetarian"),
        allergies=body.allergies or context.get("allergies") or [],
        conditions=body.conditions or context.get("conditions") or [],
        fitness_level=body.fitness_level or context.get("fitness_level") or "beginner",
    )


@router.get("/report/{report_id}", status_code=status.HTTP_200_OK)
async def get_report_suggestions(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Suggestions already generated for a report by the analysis pipeline."""
    doc = await db["suggestions"].find_one(
        {
            "report_id": report_id,
            "user_id": current_user["id"],
        }
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No suggestions for this report yet. It may still be processing.",
        )
    doc.pop("_id", None)
    return doc
