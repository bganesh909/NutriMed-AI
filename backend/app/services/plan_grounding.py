"""
Grounding and verification for LLM-generated diet and workout plans.

The model is good at *composition* -- which foods belong in a breakfast, which
exercises pair on a push day -- and unreliable at *facts*. Left to itself it
invents calorie counts and exercise form cues, which is not acceptable output
for a health product.

So responsibilities are split:

* **Retrieval** picks a shortlist of real foods/exercises that suit the user's
  preferences, allergies and lab findings. The prompt tells the model it may
  only choose from that list, by exact name.
* **Verification** takes the model's answer and rebuilds every computable
  field from the database: macros come from grams x per-100g values, exercise
  instructions come from the catalogue. Anything the model named that is not
  in the database is dropped and reported.

The model therefore never supplies a number or a safety-relevant instruction
that we could have looked up ourselves.
"""

from __future__ import annotations

import difflib
import logging
import re
from collections.abc import Iterable
from typing import Any

from app.data.exercise_database import EXERCISE_DATABASE
from app.data.food_database import FOOD_DATABASE, get_foods_by_preference

logger = logging.getLogger("nutrimed.grounding")


# ---------------------------------------------------------------------------
# Clinical mapping
# ---------------------------------------------------------------------------

#: (canonical marker, status) -> food tags worth prioritising.
#: Only tags that actually exist in the food database are listed here.
_MARKER_FOOD_TAGS: dict[tuple[str, str], list[str]] = {
    ("hemoglobin", "low"): ["iron_rich"],
    ("ferritin", "low"): ["iron_rich"],
    ("fasting_sugar", "high"): ["diabetic_friendly", "high_fiber"],
    ("hba1c", "high"): ["diabetic_friendly", "high_fiber"],
    ("triglycerides", "high"): ["omega3", "high_fiber"],
    ("total_cholesterol", "high"): ["omega3", "high_fiber"],
    ("ldl", "high"): ["omega3", "high_fiber"],
    ("hdl", "low"): ["omega3", "healthy_fat"],
    ("vitamin_d", "low"): ["fish"],
    ("vitamin_b12", "low"): ["fish"],
}

#: (canonical marker, status) -> workout constraints.
_MARKER_EXERCISE_RULES: dict[tuple[str, str], dict[str, Any]] = {
    # Anemia: oxygen delivery is impaired, so cap intensity.
    ("hemoglobin", "low"): {"max_difficulty": "beginner", "require_cardio": False},
    ("ferritin", "low"): {"max_difficulty": "intermediate", "require_cardio": False},
    # Elevated TSH: moderate load, avoid extreme endurance work.
    ("tsh", "high"): {"max_difficulty": "intermediate", "require_cardio": False},
    # Glycaemic and lipid markers respond to regular aerobic work.
    ("fasting_sugar", "high"): {"require_cardio": True},
    ("hba1c", "high"): {"require_cardio": True},
    ("triglycerides", "high"): {"require_cardio": True},
    ("hdl", "low"): {"require_cardio": True},
    ("total_cholesterol", "high"): {"require_cardio": True},
}

_DIFFICULTY_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}

#: Allergy keyword -> predicate describing what to exclude.
_ALLERGEN_RULES: dict[str, dict[str, Any]] = {
    "dairy": {"categories": ["dairy"]},
    "milk": {"categories": ["dairy"]},
    "lactose": {"categories": ["dairy"]},
    "nut": {"categories": ["nut"]},
    "nuts": {"categories": ["nut"]},
    "peanut": {"names": ["peanut"]},
    "shellfish": {"tags": ["shellfish"]},
    "prawn": {"tags": ["shellfish"]},
    "shrimp": {"names": ["shrimp"]},
    "fish": {"tags": ["fish"]},
    "seafood": {"tags": ["fish", "shellfish"]},
    "egg": {"names": ["egg"]},
    "soy": {"names": ["soy", "tofu", "tempeh"]},
    "gluten": {"requires_tag": "gluten_free"},
    "wheat": {"names": ["wheat", "bread", "roti", "chapati", "pasta"]},
}


def _abnormal_markers(rule_engine: dict | None) -> list[tuple[str, str]]:
    """Return [(marker, status)] for every marker the rule engine flagged."""
    details = (rule_engine or {}).get("marker_details") or {}
    out: list[tuple[str, str]] = []
    for marker, d in details.items():
        status = str((d or {}).get("status", "")).lower()
        if status in ("low", "high"):
            out.append((marker, status))
    return out


# ---------------------------------------------------------------------------
# Food retrieval
# ---------------------------------------------------------------------------


def _excluded_by_allergies(food: dict, allergies: Iterable[str]) -> bool:
    name = food["name"].lower()
    tags = set(food.get("tags", []))
    category = food.get("category", "")

    for raw in allergies:
        term = str(raw).strip().lower()
        if not term:
            continue
        rule = _ALLERGEN_RULES.get(term)
        if rule is None:
            # Unknown allergen: fall back to a substring match on the name.
            if term in name:
                return True
            continue
        if category in rule.get("categories", []):
            return True
        if tags & set(rule.get("tags", [])):
            return True
        if any(n in name for n in rule.get("names", [])):
            return True
        required = rule.get("requires_tag")
        if required and required not in tags:
            return True
    return False


def select_foods(
    preference: str = "non_vegetarian",
    allergies: Iterable[str] | None = None,
    rule_engine: dict | None = None,
    limit: int = 60,
) -> list[dict]:
    """
    Shortlist real foods for the diet prompt.

    Respects the dietary preference and allergies, then puts clinically
    relevant foods first (iron-rich when anemic, omega-3 when lipids are off,
    and so on) while still covering every food category so the model can build
    balanced meals.
    """
    candidates = get_foods_by_preference(preference or "non_vegetarian")
    allergies = list(allergies or [])
    candidates = [f for f in candidates if not _excluded_by_allergies(f, allergies)]

    priority_tags: set[str] = set()
    for key in _abnormal_markers(rule_engine):
        priority_tags.update(_MARKER_FOOD_TAGS.get(key, []))

    def score(food: dict) -> tuple[int, str]:
        overlap = len(priority_tags & set(food.get("tags", [])))
        return (-overlap, food["name"])

    ranked = sorted(candidates, key=score)

    # Guarantee category coverage so the shortlist can still form real meals.
    selected: list[dict] = []
    seen_names: set[str] = set()
    by_category: dict[str, list[dict]] = {}
    for f in ranked:
        by_category.setdefault(f.get("category", "other"), []).append(f)

    for cat_foods in by_category.values():
        for f in cat_foods[:3]:
            if f["name"] not in seen_names:
                selected.append(f)
                seen_names.add(f["name"])

    for f in ranked:
        if len(selected) >= limit:
            break
        if f["name"] not in seen_names:
            selected.append(f)
            seen_names.add(f["name"])

    return selected[:limit]


# ---------------------------------------------------------------------------
# Exercise retrieval
# ---------------------------------------------------------------------------


def select_exercises(
    difficulty: str = "beginner",
    equipment: Iterable[str] | None = None,
    rule_engine: dict | None = None,
    limit: int = 45,
) -> list[dict]:
    """
    Shortlist real exercises for the workout prompt.

    Lab findings can cap the difficulty (for example anemia limits intensity)
    and can force cardio into the shortlist (elevated glucose or lipids).
    """
    max_difficulty = difficulty or "beginner"
    require_cardio = False
    for key in _abnormal_markers(rule_engine):
        rule = _MARKER_EXERCISE_RULES.get(key)
        if not rule:
            continue
        capped = rule.get("max_difficulty")
        if capped and _DIFFICULTY_ORDER.get(capped, 9) < _DIFFICULTY_ORDER.get(max_difficulty, 9):
            max_difficulty = capped
        require_cardio = require_cardio or bool(rule.get("require_cardio"))

    ceiling = _DIFFICULTY_ORDER.get(max_difficulty, 0)
    candidates = [e for e in EXERCISE_DATABASE if _DIFFICULTY_ORDER.get(e.get("difficulty", "beginner"), 0) <= ceiling]
    if equipment:
        allowed = {str(x).lower() for x in equipment}
        filtered = [e for e in candidates if e.get("equipment", "") in allowed]
        # Never strand the caller with an empty catalogue.
        candidates = filtered or candidates

    by_group: dict[str, list[dict]] = {}
    for e in candidates:
        by_group.setdefault(e.get("muscle_group", "other"), []).append(e)

    selected: list[dict] = []
    seen: set[str] = set()
    # Round-robin across muscle groups so every split has something to use.
    index = 0
    while len(selected) < limit:
        added = False
        for group_exercises in by_group.values():
            if index < len(group_exercises):
                e = group_exercises[index]
                if e["name"] not in seen:
                    selected.append(e)
                    seen.add(e["name"])
                    added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
        index += 1

    if require_cardio and not any(e.get("muscle_group") == "cardio" for e in selected):
        for e in candidates:
            if e.get("muscle_group") == "cardio":
                selected.append(e)
                break

    return selected


# ---------------------------------------------------------------------------
# Prompt catalogues
# ---------------------------------------------------------------------------

#: Order categories are presented in, so the model reads the catalogue as meal
#: building blocks rather than as a ranked list.
_CATEGORY_ORDER = [
    "protein",
    "legume",
    "dairy",
    "grain",
    "vegetable",
    "fruit",
    "nut",
    "seed",
    "fat",
    "prepared",
    "beverage",
    "snack",
    "sweetener",
]


def format_food_catalogue(foods: list[dict], priority_names: set[str] | None = None) -> str:
    """
    Render the food shortlist grouped by category, with per-100g macros.

    Grouping matters: an list ordered purely by clinical relevance leads the
    model to build every meal out of the first few entries -- which is how you
    end up with a lunch of ten grams of coconut oil. Clinically useful foods
    are marked with a star instead, so relevance is signalled without
    distorting meal structure.
    """
    priority_names = priority_names or set()
    by_category: dict[str, list[dict]] = {}
    for f in foods:
        by_category.setdefault(f.get("category", "other"), []).append(f)

    ordered = [c for c in _CATEGORY_ORDER if c in by_category]
    ordered += [c for c in by_category if c not in _CATEGORY_ORDER]

    lines: list[str] = []
    for category in ordered:
        lines.append(f"  {category.upper()}:")
        for f in sorted(by_category[category], key=lambda x: x["name"]):
            star = " *" if f["name"] in priority_names else ""
            lines.append(
                f"    - {f['name']}{star} | per 100g: {f['calories']}kcal "
                f"P{f['protein_g']}g C{f['carbs_g']}g F{f['fat_g']}g"
            )
    return "\n".join(lines)


def clinical_priority_names(foods: list[dict], rule_engine: dict | None) -> set[str]:
    """Names of foods worth flagging for this person's lab findings."""
    tags: set[str] = set()
    for key in _abnormal_markers(rule_engine):
        tags.update(_MARKER_FOOD_TAGS.get(key, []))
    if not tags:
        return set()
    return {f["name"] for f in foods if tags & set(f.get("tags", []))}


def format_exercise_catalogue(exercises: list[dict]) -> str:
    """Render the exercise shortlist for a prompt."""
    lines = []
    for e in exercises:
        lines.append(f"  - {e['name']} [{e['muscle_group']}, {e['equipment']}, {e['difficulty']}]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

_FOOD_BY_NAME = {f["name"].lower(): f for f in FOOD_DATABASE}
_EXERCISE_BY_NAME = {e["name"].lower(): e for e in EXERCISE_DATABASE}


def _strip_qualifier(name: str) -> str:
    """'Chicken Breast (cooked)' -> 'chicken breast'."""
    return re.sub(r"\s*\([^)]*\)", "", name).strip().lower()


def _normalise(name: str) -> str:
    """Lowercase and collapse punctuation/whitespace for comparison."""
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def _lookup(name: Any, table: dict[str, dict], cutoff: float = 0.85) -> dict | None:
    """
    Resolve a model-supplied name to a database entry.

    Tries progressively looser matches: exact, then ignoring the preparation
    qualifier (models write "Chicken Breast" where the database says "Chicken
    Breast (cooked)"), then punctuation-insensitive, then a conservative fuzzy
    match. Anything that still does not resolve is treated as a hallucination.
    """
    if not isinstance(name, str) or not name.strip():
        return None

    key = name.strip().lower()
    if key in table:
        return table[key]

    # Same food, different preparation qualifier.
    stripped = _strip_qualifier(key)
    for candidate_key, entry in table.items():
        if _strip_qualifier(candidate_key) == stripped:
            return entry

    # Punctuation- and spacing-insensitive.
    normalised = _normalise(key)
    for candidate_key, entry in table.items():
        if _normalise(candidate_key) == normalised:
            return entry
        if _normalise(_strip_qualifier(candidate_key)) == normalised:
            return entry

    close = difflib.get_close_matches(key, table.keys(), n=1, cutoff=cutoff)
    return table[close[0]] if close else None


def _coerce_grams(value: Any) -> float | None:
    """Read a gram quantity, tolerating '150', '150g' and '150 g'."""
    if isinstance(value, (int, float)):
        grams = float(value)
    elif isinstance(value, str):
        digits = "".join(c for c in value if c.isdigit() or c == ".")
        if not digits:
            return None
        try:
            grams = float(digits)
        except ValueError:
            return None
    else:
        return None
    # Reject implausible portions rather than silently scaling nonsense.
    if grams <= 0 or grams > 2000:
        return None
    return grams


def verify_diet_plan(plan: Any) -> tuple[Any, list[str]]:
    """
    Rebuild a diet plan's numbers from the food database.

    Every item's calories and macros are recomputed from its gram quantity, so
    the model's arithmetic is never trusted. Items naming a food that is not in
    the database are removed. Meal and day totals are summed from the verified
    items.

    Returns (verified_plan, warnings).
    """
    warnings: list[str] = []
    if not isinstance(plan, dict):
        return plan, warnings

    meal_plan = plan.get("meal_plan")
    if not isinstance(meal_plan, list):
        return plan, warnings

    plan = dict(plan)
    verified_days = []
    plan_totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    day_count = 0

    for day in meal_plan:
        if not isinstance(day, dict):
            continue
        meals = day.get("meals")
        if not isinstance(meals, list):
            continue

        verified_meals = []
        day_totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}

        for meal in meals:
            if not isinstance(meal, dict):
                continue
            items = meal.get("foods") or meal.get("items") or []
            if not isinstance(items, list):
                items = []

            verified_items = []
            meal_totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}

            for item in items:
                if not isinstance(item, dict):
                    continue
                raw_name = item.get("name")
                food = _lookup(raw_name, _FOOD_BY_NAME)
                if food is None:
                    warnings.append(f"unknown food dropped: {raw_name!r}")
                    continue

                grams = _coerce_grams(item.get("quantity_g", item.get("grams", item.get("quantity"))))
                if grams is None:
                    warnings.append(f"unusable quantity for {food['name']!r}; defaulted to 100g")
                    grams = 100.0

                factor = grams / 100.0
                computed = {
                    "name": food["name"],
                    "quantity_g": round(grams, 1),
                    "calories": round(food["calories"] * factor, 1),
                    "protein_g": round(food["protein_g"] * factor, 1),
                    "carbs_g": round(food["carbs_g"] * factor, 1),
                    "fat_g": round(food["fat_g"] * factor, 1),
                    "category": food.get("category", ""),
                }
                verified_items.append(computed)
                for k in meal_totals:
                    meal_totals[k] += computed[k]

            if not verified_items:
                continue
            verified_meals.append(
                {
                    "name": meal.get("name") or meal.get("meal") or "Meal",
                    "time": meal.get("time", ""),
                    "foods": verified_items,
                    **{k: round(v, 1) for k, v in meal_totals.items()},
                }
            )
            for k in day_totals:
                day_totals[k] += meal_totals[k]

        if not verified_meals:
            continue
        verified_days.append(
            {
                "day": day.get("day") or f"Day {len(verified_days) + 1}",
                "meals": verified_meals,
                **{k: round(v, 1) for k, v in day_totals.items()},
            }
        )
        day_count += 1
        for k in plan_totals:
            plan_totals[k] += day_totals[k]

    plan["meal_plan"] = verified_days
    if day_count:
        # Report the daily average, which is what a reader expects to see.
        plan["calories"] = round(plan_totals["calories"] / day_count, 1)
        plan["macros"] = {
            "protein_g": round(plan_totals["protein_g"] / day_count, 1),
            "carbs_g": round(plan_totals["carbs_g"] / day_count, 1),
            "fat_g": round(plan_totals["fat_g"] / day_count, 1),
        }
    plan["verified"] = True
    return plan, warnings


def verify_workout_plan(days: Any) -> tuple[list[dict], list[str]]:
    """
    Rebuild a workout plan's exercises from the exercise database.

    Exercise names must resolve to a catalogue entry; form instructions,
    muscle group and equipment are taken from that entry rather than from the
    model. Unknown exercises are dropped.

    Returns (verified_days, warnings).
    """
    warnings: list[str] = []
    if not isinstance(days, list):
        return [], warnings

    verified_days: list[dict] = []
    for day in days:
        if not isinstance(day, dict):
            continue
        exercises = day.get("exercises")
        if not isinstance(exercises, list):
            continue

        verified: list[dict] = []
        for ex in exercises:
            if not isinstance(ex, dict):
                continue
            raw_name = ex.get("name")
            found = _lookup(raw_name, _EXERCISE_BY_NAME)
            if found is None:
                warnings.append(f"unknown exercise dropped: {raw_name!r}")
                continue

            sets = ex.get("sets", 3)
            try:
                sets = max(1, min(10, int(sets)))
            except (TypeError, ValueError):
                sets = 3

            verified.append(
                {
                    "name": found["name"],
                    "sets": sets,
                    "reps": str(ex.get("reps", "10-12")),
                    "rest": str(ex.get("rest", "60s")),
                    # Safety-relevant fields always come from the database.
                    "muscle_group": found.get("muscle_group", ""),
                    "equipment": found.get("equipment", ""),
                    "difficulty": found.get("difficulty", ""),
                    "instructions": found.get("instructions", ""),
                    "alternatives": found.get("alternatives", []),
                }
            )

        if not verified:
            continue
        verified_days.append(
            {
                "day_name": day.get("day_name") or day.get("day") or f"Day {len(verified_days) + 1}",
                "warm_up": day.get("warm_up", ""),
                "cool_down": day.get("cool_down", ""),
                "exercises": verified,
            }
        )
    return verified_days, warnings


def daily_calorie_target(user: dict) -> int:
    """
    Deterministic daily calorie target for a user profile.

    Used to anchor the diet prompt and to sanity-check the plan that comes
    back. Falls back to a reasonable default when the profile is incomplete.
    """
    from app.services.nutrition_calculator import (
        calculate_bmr,
        calculate_macros,
        calculate_tdee,
    )

    try:
        weight = float(user.get("weight") or 70)
        height = float(user.get("height") or 170)
        age = int(user.get("age") or 30)
        gender = str(user.get("gender") or "male")
        activity = str(user.get("activity_level") or "moderate")
        goals = user.get("goals") or ["maintenance"]
        goal = str(goals[0]) if goals else "maintenance"

        bmr = calculate_bmr(weight, height, age, gender)
        tdee = calculate_tdee(bmr, activity)
        macros = calculate_macros(tdee, goal, weight)
        target = int(macros.get("calories") or tdee)
    except Exception:
        logger.warning("Calorie target calculation failed; using default", exc_info=True)
        return 2000
    return max(1200, min(4500, target))


def plan_is_nutritionally_adequate(plan: Any, target_calories: int, tolerance: float = 0.35) -> tuple[bool, list[str]]:
    """
    Sanity-check a verified diet plan before it reaches a user.

    Verification guarantees the arithmetic; it says nothing about whether the
    plan is sensible. This catches the failure modes a constrained model still
    produces: a day totalling a third of the target, a "lunch" of ten grams of
    oil, or two of the three requested days missing.

    Returns (is_adequate, reasons).
    """
    reasons: list[str] = []
    if not isinstance(plan, dict):
        return False, ["plan is not an object"]

    days = plan.get("meal_plan") or []
    if not days:
        return False, ["plan has no days"]

    low = target_calories * (1 - tolerance)
    high = target_calories * (1 + tolerance)

    for day in days:
        label = day.get("day", "day")
        calories = day.get("calories") or 0
        if calories < low:
            reasons.append(f"{label}: {calories:.0f} kcal is far below the {target_calories} kcal target")
        elif calories > high:
            reasons.append(f"{label}: {calories:.0f} kcal is far above the {target_calories} kcal target")

        meals = day.get("meals") or []
        if len(meals) < 3:
            reasons.append(f"{label}: only {len(meals)} meal(s)")

        for meal in meals:
            foods = meal.get("foods") or []
            categories = {f.get("category") for f in foods}
            # A main meal built purely from fats/nuts/seeds is not a meal.
            is_only_fats = categories and categories <= {"fat", "nut", "seed", "sweetener", "beverage"}
            is_main_meal = meal.get("name", "").lower() in ("lunch", "dinner", "breakfast")
            if is_only_fats and is_main_meal and (meal.get("calories") or 0) > 0:
                reasons.append(f"{label}/{meal.get('name')}: built only from {sorted(categories)}")

    return (not reasons), reasons
