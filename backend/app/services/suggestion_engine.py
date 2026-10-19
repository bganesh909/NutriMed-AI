"""
Builds nutrition and training *suggestions* -- not full plans.

This is what a user gets by default, whether or not they uploaded a lab report.
A full day-by-day diet or workout plan is only produced when they explicitly
ask for one, because most people want to know "what should I change?" long
before they want a seven-day meal schedule.

Deliberately deterministic: suggestions come from the rule engine's biomarker
findings, the user's goal, and the curated food/exercise databases. No LLM is
involved, so this is instant, reproducible, and cannot hallucinate. The model
is reserved for the on-request full plans, where its output is grounded and
verified (see `plan_grounding`).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from app.data.exercise_database import EXERCISE_DATABASE
from app.data.food_database import FOOD_DATABASE
from app.services.nutrition_calculator import normalise_goal
from app.services.plan_grounding import daily_calorie_target, select_foods

logger = logging.getLogger("nutrimed.suggestions")

MAX_EXAMPLES = 4

#: When several findings merge, the combined entry uses this label rather than
#: whichever one happened to be processed first.
_CANONICAL_LABELS = {
    "iron": "Iron-rich foods, paired with vitamin C",
    "lipids": "Omega-3 sources, soluble fibre and healthy fats",
    "glycaemic": "High-fibre, low-glycaemic foods",
    "refined_carbs": "Refined carbohydrates, added sugar and alcohol",
    "fried": "Fried food, reused cooking oil and processed meat",
    "moderate_intensity": "Keep intensity moderate and recover fully",
    "aerobic": "Regular aerobic exercise, most days",
}


# ---------------------------------------------------------------------------
# Lab-driven advice
# ---------------------------------------------------------------------------

#: (marker, status) -> nutrition advice. `tags` selects example foods from the
#: curated database so every suggestion names real, checkable items.
_LAB_NUTRITION: dict[tuple[str, str], dict[str, Any]] = {
    ("hemoglobin", "low"): {
        "merge_key": "iron",
        "label": "Iron-rich foods, paired with vitamin C",
        "why": "haemoglobin is below range",
        "tags": ["iron_rich"],
        "detail": "Vitamin C markedly improves absorption of plant iron, so pair them in the same meal.",
    },
    ("ferritin", "low"): {
        "merge_key": "iron",
        "label": "Iron-rich foods",
        "why": "ferritin is low, so iron stores are depleted",
        "tags": ["iron_rich"],
    },
    ("vitamin_b12", "low"): {
        "merge_key": "b12",
        "label": "Vitamin B12 sources",
        "why": "vitamin B12 is below range",
        "tags": ["fish"],
        "detail": "Mainly animal foods. On a plant-based diet this usually needs a supplement.",
    },
    ("vitamin_d", "low"): {
        "merge_key": "vitamin_d",
        "label": "Vitamin D sources and sunlight",
        "why": "vitamin D is below range",
        "tags": ["fish"],
        "detail": "Diet alone rarely corrects a deficiency; sunlight and supplementation matter more.",
    },
    ("triglycerides", "high"): {
        "merge_key": "lipids",
        "label": "Omega-3 sources and soluble fibre",
        "why": "triglycerides are above range",
        "tags": ["omega3", "high_fiber"],
    },
    ("total_cholesterol", "high"): {
        "merge_key": "lipids",
        "label": "Soluble fibre and omega-3 sources",
        "why": "total cholesterol is above range",
        "tags": ["high_fiber", "omega3"],
    },
    ("ldl", "high"): {
        "merge_key": "lipids",
        "label": "Soluble fibre and unsaturated fats",
        "why": "LDL cholesterol is above range",
        "tags": ["high_fiber", "healthy_fat"],
    },
    ("hdl", "low"): {
        "merge_key": "lipids",
        "label": "Healthy fats and omega-3 sources",
        "why": "HDL cholesterol is below range",
        "tags": ["healthy_fat", "omega3"],
    },
    ("fasting_sugar", "high"): {
        "merge_key": "glycaemic",
        "label": "High-fibre, low-glycaemic foods",
        "why": "fasting glucose is above range",
        "tags": ["diabetic_friendly", "high_fiber"],
    },
    ("hba1c", "high"): {
        "merge_key": "glycaemic",
        "label": "High-fibre, low-glycaemic foods",
        "why": "HbA1c is above range",
        "tags": ["diabetic_friendly", "high_fiber"],
    },
}

#: (marker, status) -> foods to cut back on. No examples: these are categories
#: to reduce, and naming specific items reads as a shopping list.
_LAB_LIMIT: dict[tuple[str, str], dict[str, str]] = {
    ("fasting_sugar", "high"): {
        "merge_key": "refined_carbs",
        "label": "Refined carbohydrates and added sugar",
        "why": "fasting glucose is above range",
    },
    ("hba1c", "high"): {
        "merge_key": "refined_carbs",
        "label": "Refined carbohydrates and added sugar",
        "why": "HbA1c is above range",
    },
    ("triglycerides", "high"): {
        "merge_key": "refined_carbs",
        "label": "Added sugar, refined carbohydrates and alcohol",
        "why": "these raise triglycerides more than dietary fat does",
    },
    ("total_cholesterol", "high"): {
        "merge_key": "fried",
        "label": "Fried food, reused cooking oil and processed meat",
        "why": "total cholesterol is above range",
    },
    ("ldl", "high"): {
        "merge_key": "fried",
        "label": "Fried food and trans fats",
        "why": "LDL cholesterol is above range",
    },
    ("uric_acid", "high"): {
        "label": "Organ meat, shellfish and alcohol",
        "why": "uric acid is above range",
    },
}

#: (marker, status) -> training advice.
_LAB_TRAINING: dict[tuple[str, str], dict[str, Any]] = {
    ("hemoglobin", "low"): {
        "merge_key": "moderate_intensity",
        "label": "Keep intensity moderate for now",
        "why": "low haemoglobin reduces oxygen delivery, so hard sessions will feel disproportionately difficult",
        "caps_intensity": True,
    },
    ("ferritin", "low"): {
        "merge_key": "moderate_intensity",
        "label": "Build volume gradually",
        "why": "depleted iron stores slow recovery",
        "caps_intensity": True,
    },
    ("tsh", "high"): {
        "merge_key": "moderate_intensity",
        "label": "Moderate training with full recovery",
        "why": "elevated TSH suggests underactive thyroid; avoid extreme endurance blocks",
        "caps_intensity": True,
    },
    ("fasting_sugar", "high"): {
        "merge_key": "aerobic",
        "label": "Regular aerobic work, most days",
        "why": "aerobic exercise improves glucose handling",
        "prefer_cardio": True,
    },
    ("hba1c", "high"): {
        "merge_key": "aerobic",
        "label": "Combine resistance training with regular cardio",
        "why": "both improve long-term glucose control",
        "prefer_cardio": True,
    },
    ("triglycerides", "high"): {
        "merge_key": "aerobic",
        "label": "Steady-state cardio 3-4x per week",
        "why": "aerobic work lowers triglycerides",
        "prefer_cardio": True,
    },
    ("hdl", "low"): {
        "merge_key": "aerobic",
        "label": "Regular aerobic exercise",
        "why": "one of the few reliable ways to raise HDL",
        "prefer_cardio": True,
    },
    ("creatinine", "high"): {
        "label": "Keep hydration high; avoid very high protein loading",
        "why": "creatinine is above range",
    },
    ("uric_acid", "high"): {
        "label": "Favour low-impact work (swimming, cycling)",
        "why": "high uric acid can affect joints",
    },
}


# ---------------------------------------------------------------------------
# Goal-driven advice
# ---------------------------------------------------------------------------

_GOAL_NUTRITION: dict[str, list[dict[str, Any]]] = {
    "fat_loss": [
        {
            "label": "Protein at every meal",
            "why": "preserves muscle in a calorie deficit and blunts hunger",
            "tags": ["high_protein"],
        },
        {
            "label": "High-volume, low-calorie vegetables",
            "why": "keeps meals filling while calories stay down",
            "tags": ["low_calorie"],
        },
    ],
    "muscle_gain": [
        {
            "label": "Protein spread across 3-4 meals",
            "why": "supports muscle protein synthesis through the day",
            "tags": ["high_protein"],
        },
        {"label": "Carbohydrate around training", "why": "fuels harder sessions and recovery", "tags": ["whole_grain"]},
    ],
    "weight_gain": [
        {
            "label": "Calorie-dense foods",
            "why": "reaching a surplus on whole foods alone is hard",
            "tags": ["healthy_fat"],
        },
        {
            "label": "Frequent meals and liquid calories",
            "why": "easier to hit a surplus without feeling over-full",
            "tags": ["high_protein"],
        },
    ],
    "recomposition": [
        {
            "label": "High protein at maintenance calories",
            "why": "the main lever for losing fat and gaining muscle at once",
            "tags": ["high_protein"],
        },
    ],
    "endurance": [
        {
            "label": "Carbohydrate as the primary fuel",
            "why": "glycogen availability limits endurance performance",
            "tags": ["whole_grain"],
        },
        {"label": "Iron-rich foods", "why": "endurance athletes are prone to low iron", "tags": ["iron_rich"]},
    ],
    "strength": [
        {
            "label": "Protein and a small calorie surplus",
            "why": "supports force production and recovery",
            "tags": ["high_protein"],
        },
    ],
    "maintenance": [
        {
            "label": "A protein source and vegetables at each main meal",
            "why": "the simplest structure that keeps a diet balanced",
            "tags": ["high_protein"],
        },
        {
            "label": "Fibre from whole grains, legumes and fruit",
            "why": "most people fall short of fibre targets",
            "tags": ["high_fiber"],
        },
    ],
}

_GOAL_TRAINING: dict[str, list[dict[str, Any]]] = {
    "fat_loss": [
        {
            "label": "Keep lifting while dieting",
            "why": "resistance training is what tells the body to keep muscle",
            "groups": ["legs", "back", "chest"],
        },
        {
            "label": "Add cardio you can sustain",
            "why": "adherence matters more than the modality",
            "groups": ["cardio"],
        },
    ],
    "muscle_gain": [
        {
            "label": "Progressive overload on compound lifts",
            "why": "adding weight or reps over time is the primary driver",
            "groups": ["chest", "back", "legs"],
        },
        {
            "label": "Train each muscle group about twice a week",
            "why": "better than once-weekly for growth",
            "groups": ["shoulders", "biceps", "triceps"],
        },
    ],
    "weight_gain": [
        {
            "label": "Prioritise heavy compound movements",
            "why": "directs the surplus toward muscle rather than fat",
            "groups": ["legs", "back", "chest"],
        },
        {"label": "Keep cardio light", "why": "excess cardio works against a surplus", "groups": ["cardio"]},
    ],
    "recomposition": [
        {
            "label": "Resistance training 3-4x per week",
            "why": "the stimulus that drives the muscle side of recomposition",
            "groups": ["chest", "back", "legs"],
        },
    ],
    "endurance": [
        {
            "label": "Build weekly aerobic volume gradually",
            "why": "most endurance progress comes from consistent easy volume",
            "groups": ["cardio"],
        },
        {
            "label": "Keep 2x weekly strength work",
            "why": "protects against injury and improves economy",
            "groups": ["legs", "core"],
        },
    ],
    "strength": [
        {
            "label": "Low reps, heavy loads, long rests",
            "why": "strength responds to intensity, not fatigue",
            "groups": ["legs", "back", "chest"],
        },
        {
            "label": "Train the main lifts frequently",
            "why": "strength is a skill and improves with practice",
            "groups": ["shoulders", "core"],
        },
    ],
    "maintenance": [
        {
            "label": "Mix resistance training and cardio weekly",
            "why": "covers both strength and cardiovascular health",
            "groups": ["legs", "back", "cardio"],
        },
    ],
}


#: Self-reported conditions, used when there is no lab report (and alongside
#: one when there is). Keys are matched loosely against what the user types.
_CONDITION_ADVICE: dict[str, dict[str, Any]] = {
    "diabetes": {
        "nutrition": {
            "merge_key": "glycaemic",
            "label": "High-fibre, low-glycaemic foods",
            "why": "reported diabetes",
            "tags": ["diabetic_friendly", "high_fiber"],
        },
        "limit": {
            "merge_key": "refined_carbs",
            "label": "Refined carbohydrates and added sugar",
            "why": "reported diabetes",
        },
        "training": {
            "merge_key": "aerobic",
            "label": "Regular aerobic exercise, most days",
            "why": "improves insulin sensitivity",
            "prefer_cardio": True,
        },
    },
    "prediabetes": {
        "nutrition": {
            "merge_key": "glycaemic",
            "label": "High-fibre, low-glycaemic foods",
            "why": "reported pre-diabetes",
            "tags": ["diabetic_friendly", "high_fiber"],
        },
        "training": {
            "merge_key": "aerobic",
            "label": "Regular aerobic exercise, most days",
            "why": "improves glucose handling",
            "prefer_cardio": True,
        },
    },
    "hypertension": {
        "nutrition": {
            "merge_key": "potassium",
            "label": "Potassium-rich vegetables and fruit",
            "why": "reported high blood pressure",
            "tags": ["vegetarian"],
        },
        "limit": {
            "merge_key": "salt",
            "label": "Salt, pickles and processed food",
            "why": "reported high blood pressure",
        },
        "training": {
            "merge_key": "aerobic",
            "label": "Regular aerobic exercise, most days",
            "why": "lowers resting blood pressure",
            "prefer_cardio": True,
        },
    },
    "high_cholesterol": {
        "nutrition": {
            "merge_key": "lipids",
            "label": "Omega-3 sources, soluble fibre and healthy fats",
            "why": "reported high cholesterol",
            "tags": ["omega3", "high_fiber"],
        },
        "limit": {
            "merge_key": "fried",
            "label": "Fried food, reused cooking oil and processed meat",
            "why": "reported high cholesterol",
        },
    },
    "thyroid": {
        "training": {
            "merge_key": "moderate_intensity",
            "label": "Keep intensity moderate and recover fully",
            "why": "reported thyroid condition",
            "caps_intensity": True,
        },
    },
    "pcos": {
        "nutrition": {
            "merge_key": "glycaemic",
            "label": "High-fibre, low-glycaemic foods",
            "why": "reported PCOS, which involves insulin resistance",
            "tags": ["diabetic_friendly", "high_fiber"],
        },
        "training": {
            "merge_key": "resistance",
            "label": "Resistance training plus regular walking",
            "why": "improves insulin sensitivity in PCOS",
            "groups": ["legs", "back"],
        },
    },
    "anemia": {
        "nutrition": {
            "merge_key": "iron",
            "label": "Iron-rich foods, paired with vitamin C",
            "why": "reported anaemia",
            "tags": ["iron_rich"],
        },
        "training": {
            "merge_key": "moderate_intensity",
            "label": "Keep intensity moderate and recover fully",
            "why": "reported anaemia limits oxygen delivery",
            "caps_intensity": True,
        },
    },
    "knee_injury": {
        "training": {
            "merge_key": "low_impact",
            "label": "Favour low-impact, joint-friendly work",
            "why": "reported knee problem",
            "groups": ["core", "back"],
        },
    },
    "back_pain": {
        "training": {
            "merge_key": "low_impact",
            "label": "Prioritise core work and avoid heavy spinal loading",
            "why": "reported back pain",
            "groups": ["core"],
        },
    },
}


def _match_conditions(conditions: Iterable[str]) -> list[dict]:
    """Match free-text conditions against the advice table."""
    matched: list[dict] = []
    for raw in conditions or []:
        token = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
        if not token:
            continue
        entry = _CONDITION_ADVICE.get(token)
        if entry is None:
            # Loose match so "type 2 diabetes" or "high cholesterol levels" hit.
            for key, candidate in _CONDITION_ADVICE.items():
                if key in token or token in key:
                    entry = candidate
                    break
        if entry:
            matched.append(entry)
    return matched


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _abnormal(rule_engine: dict | None) -> list[tuple[str, str]]:
    """[(marker, status)] for every marker the rule engine flagged."""
    details = (rule_engine or {}).get("marker_details") or {}
    return [
        (marker, str((d or {}).get("status", "")).lower())
        for marker, d in details.items()
        if str((d or {}).get("status", "")).lower() in ("low", "high")
    ]


def _example_foods(
    tags: Iterable[str],
    preference: str,
    allergies: Iterable[str],
    limit: int = MAX_EXAMPLES,
) -> list[str]:
    """Names of real foods matching the tags, respecting preference and allergies."""
    allowed = {f["name"] for f in select_foods(preference, allergies, None, limit=len(FOOD_DATABASE))}
    wanted = set(tags)
    matches = [f["name"] for f in FOOD_DATABASE if f["name"] in allowed and wanted & set(f.get("tags", []))]
    return matches[:limit]


def _example_exercises(groups: Iterable[str], max_difficulty: str, limit: int = MAX_EXAMPLES) -> list[str]:
    """Names of real exercises for the given muscle groups, capped by difficulty."""
    order = {"beginner": 0, "intermediate": 1, "advanced": 2}
    ceiling = order.get(max_difficulty, 1)
    wanted = set(groups)
    out: list[str] = []
    for group in wanted:
        for e in EXERCISE_DATABASE:
            if e.get("muscle_group") != group:
                continue
            if order.get(e.get("difficulty", "beginner"), 0) > ceiling:
                continue
            out.append(e["name"])
            break
    return out[:limit]


def _merge(items: list[dict]) -> list[dict]:
    """
    Collapse advice that recommends the same thing for different reasons.

    Several findings often point at one action -- high cholesterol, high
    triglycerides and low HDL all say "eat more omega-3". Listing that three
    times with different wording reads as padding, so entries sharing a merge
    key are combined and their reasons joined.
    """
    merged: dict[Any, dict] = {}
    order: list[Any] = []

    for item in items:
        key = item.get("merge_key") or item["label"].lower()
        if key not in merged:
            merged[key] = {**item, "why": [item["why"]]}
            order.append(key)
            continue

        existing = merged[key]
        if item["why"] not in existing["why"]:
            existing["why"].append(item["why"])
        # Prefer the richer example list and keep any detail text.
        if len(item.get("examples", [])) > len(existing.get("examples", [])):
            existing["examples"] = item["examples"]
        if item.get("detail") and not existing.get("detail"):
            existing["detail"] = item["detail"]
        # Lab evidence outranks a stated goal.
        if item.get("source") == "labs":
            existing["source"] = "labs"

    out: list[dict] = []
    for key in order:
        entry = merged[key]
        reasons = entry.pop("why")
        entry.pop("merge_key", None)
        if len(reasons) > 1 and key in _CANONICAL_LABELS:
            entry["label"] = _CANONICAL_LABELS[key]
        # Kept as a list: the reasons often contain their own commas and
        # semicolons, so joining them into one sentence reads badly. The UI
        # renders them as separate lines.
        entry["why"] = reasons
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_suggestions(
    *,
    user: dict | None = None,
    rule_engine: dict | None = None,
    goal: str | None = None,
    dietary_preference: str = "non_vegetarian",
    allergies: list[str] | None = None,
    conditions: list[str] | None = None,
    fitness_level: str = "beginner",
) -> dict[str, Any]:
    """
    Build nutrition and training suggestions.

    Works from lab findings, from the profile and goal alone, or from both.
    Lab-driven advice is listed first because it reflects measured evidence
    rather than a stated preference.

    `missing_info` names the profile fields that would sharpen the result, so
    the caller can ask for them rather than silently guessing.
    """
    user = user or {}
    allergies = allergies or []
    goals = user.get("goals") or []
    goal_key = normalise_goal(goal or (goals[0] if goals else "maintenance"))

    lab_findings = _abnormal(rule_engine)
    has_labs = bool(lab_findings)

    emphasise: list[dict] = []
    limit: list[dict] = []
    training: list[dict] = []
    caps_intensity = False
    prefer_cardio = False

    # --- from labs (measured evidence first) ---
    for key in lab_findings:
        advice = _LAB_NUTRITION.get(key)
        if advice:
            entry = {
                "label": advice["label"],
                "why": advice["why"],
                "source": "labs",
                "merge_key": advice.get("merge_key", advice["label"].lower()),
                "examples": _example_foods(advice.get("tags", []), dietary_preference, allergies),
            }
            if advice.get("detail"):
                entry["detail"] = advice["detail"]
            emphasise.append(entry)

        cut = _LAB_LIMIT.get(key)
        if cut:
            limit.append(
                {
                    "label": cut["label"],
                    "why": cut["why"],
                    "source": "labs",
                    "merge_key": cut.get("merge_key", cut["label"].lower()),
                }
            )

        train = _LAB_TRAINING.get(key)
        if train:
            training.append(
                {
                    "label": train["label"],
                    "why": train["why"],
                    "source": "labs",
                    "merge_key": train.get("merge_key", train["label"].lower()),
                }
            )
            caps_intensity = caps_intensity or bool(train.get("caps_intensity"))
            prefer_cardio = prefer_cardio or bool(train.get("prefer_cardio"))

    # --- from self-reported conditions ---
    for entry in _match_conditions(conditions or user.get("conditions") or []):
        nutrition = entry.get("nutrition")
        if nutrition:
            emphasise.append(
                {
                    "label": nutrition["label"],
                    "why": nutrition["why"],
                    "source": "reported",
                    "merge_key": nutrition.get("merge_key", nutrition["label"].lower()),
                    "examples": _example_foods(nutrition.get("tags", []), dietary_preference, allergies),
                }
            )
        cut = entry.get("limit")
        if cut:
            limit.append(
                {
                    "label": cut["label"],
                    "why": cut["why"],
                    "source": "reported",
                    "merge_key": cut.get("merge_key", cut["label"].lower()),
                }
            )
        train = entry.get("training")
        if train:
            training.append(
                {
                    "label": train["label"],
                    "why": train["why"],
                    "source": "reported",
                    "merge_key": train.get("merge_key", train["label"].lower()),
                }
            )
            caps_intensity = caps_intensity or bool(train.get("caps_intensity"))
            prefer_cardio = prefer_cardio or bool(train.get("prefer_cardio"))

    # --- from the stated goal ---
    max_difficulty = "beginner" if caps_intensity else fitness_level
    for advice in _GOAL_NUTRITION.get(goal_key, []):
        emphasise.append(
            {
                "label": advice["label"],
                "why": advice["why"],
                "source": "goal",
                "examples": _example_foods(advice.get("tags", []), dietary_preference, allergies),
            }
        )
    for advice in _GOAL_TRAINING.get(goal_key, []):
        training.append(
            {
                "label": advice["label"],
                "why": advice["why"],
                "source": "goal",
                "examples": _example_exercises(advice.get("groups", []), max_difficulty),
            }
        )

    # --- what would make this better ---
    missing: list[str] = []
    for field, note in (
        ("age", "age"),
        ("gender", "sex"),
        ("weight", "current weight"),
        ("height", "height"),
        ("activity_level", "activity level"),
    ):
        if not user.get(field):
            missing.append(note)
    if not has_labs:
        missing.append("a recent lab report (blood test) for evidence-based advice")
        if not (conditions or user.get("conditions")):
            missing.append("any known health conditions (e.g. diabetes, thyroid, blood pressure)")

    return {
        "goal": goal_key,
        "based_on": ("labs+profile" if has_labs and user.get("weight") else "labs" if has_labs else "profile"),
        "nutrition": {
            "emphasise": _merge(emphasise),
            "limit": _merge(limit),
            "daily_target_calories": daily_calorie_target({**user, "goals": [goal_key]}),
        },
        "training": {
            "focus": _merge(training),
            "intensity_capped": caps_intensity,
            "cardio_emphasised": prefer_cardio,
        },
        "missing_info": missing,
        # The user asks for these explicitly; they are not generated up front.
        "available_on_request": ["full_diet_plan", "full_workout_plan"],
    }
