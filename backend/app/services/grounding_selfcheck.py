"""
Startup self-check for the plan-grounding data and its dependencies.

The accuracy guarantees in `plan_grounding` rest on two curated datasets and a
reachable LLM. If a deployment loses any of that, the system does not crash --
it quietly degrades: every plan falls back to a template, or worse, the
catalogue is empty and nothing resolves. That failure is invisible without an
explicit check, so this runs at startup and is exposed on /health.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("nutrimed.selfcheck")

#: Below these counts the catalogues cannot build a balanced plan, which almost
#: certainly means a packaging or import problem rather than a curation choice.
MIN_FOODS = 50
MIN_EXERCISES = 40
REQUIRED_FOOD_CATEGORIES = {"protein", "grain", "vegetable"}
REQUIRED_MUSCLE_GROUPS = {"chest", "back", "legs", "core"}


def check_grounding_data() -> dict[str, Any]:
    """
    Validate the curated datasets that plan accuracy depends on.

    Returns a dict with `ok` plus per-dataset detail. Never raises: a health
    endpoint must be able to report a problem rather than fail itself.
    """
    result: dict[str, Any] = {"ok": True, "problems": []}

    try:
        from app.data.exercise_database import EXERCISE_DATABASE
        from app.data.food_database import FOOD_DATABASE
    except Exception as exc:  # pragma: no cover - import failure path
        return {
            "ok": False,
            "problems": [f"curated datasets failed to import: {exc}"],
            "foods": 0,
            "exercises": 0,
        }

    foods = len(FOOD_DATABASE)
    exercises = len(EXERCISE_DATABASE)
    result["foods"] = foods
    result["exercises"] = exercises

    if foods < MIN_FOODS:
        result["problems"].append(f"food database has only {foods} entries (expected >= {MIN_FOODS})")

    food_categories = {f.get("category") for f in FOOD_DATABASE}
    missing_categories = REQUIRED_FOOD_CATEGORIES - food_categories
    if missing_categories:
        result["problems"].append(f"food database missing categories: {sorted(missing_categories)}")

    if exercises < MIN_EXERCISES:
        result["problems"].append(f"exercise database has only {exercises} entries (expected >= {MIN_EXERCISES})")

    muscle_groups = {e.get("muscle_group") for e in EXERCISE_DATABASE}
    missing_groups = REQUIRED_MUSCLE_GROUPS - muscle_groups
    if missing_groups:
        result["problems"].append(f"exercise database missing muscle groups: {sorted(missing_groups)}")

    # Form instructions are the safety-relevant field taken from the database
    # rather than the model; an entry without one silently degrades the PDF.
    without_instructions = [e["name"] for e in EXERCISE_DATABASE if not e.get("instructions")]
    if without_instructions:
        result["problems"].append(
            f"{len(without_instructions)} exercise(s) have no form instructions, e.g. {without_instructions[:3]}"
        )

    # The grounding pipeline must actually be able to produce a plan.
    try:
        from app.services.diet_templates import build_fallback_meal_plan
        from app.services.plan_grounding import (
            plan_is_nutritionally_adequate,
            select_exercises,
            select_foods,
        )
        from app.services.workout_templates import build_fallback_days

        if not select_foods("vegetarian", [], None):
            result["problems"].append("food retrieval returned nothing for a vegetarian profile")
        if not select_exercises("beginner", None, None):
            result["problems"].append("exercise retrieval returned nothing for a beginner profile")

        fallback = build_fallback_meal_plan(num_days=1)
        adequate, reasons = plan_is_nutritionally_adequate(fallback, fallback.get("calories") or 2000)
        if not adequate:
            result["problems"].append(f"template diet fallback is not adequate: {reasons[:2]}")
        if not build_fallback_days(days_per_week=2):
            result["problems"].append("template workout fallback produced no days")
    except Exception as exc:
        result["problems"].append(f"grounding pipeline self-check failed: {exc}")

    result["ok"] = not result["problems"]
    return result


def log_startup_selfcheck() -> dict[str, Any]:
    """Run the check at startup and log the outcome prominently."""
    report = check_grounding_data()
    if report["ok"]:
        logger.info(
            "Grounding self-check passed: %s foods, %s exercises",
            report.get("foods"),
            report.get("exercises"),
        )
    else:
        for problem in report["problems"]:
            logger.error("Grounding self-check problem: %s", problem)
        logger.error(
            "Plan accuracy is DEGRADED. Generated diet/workout plans may be "
            "unreliable or fall back to templates for every user."
        )
    return report
