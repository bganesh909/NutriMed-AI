"""
Workout adaptation engine.
Adapts workout plans based on health conditions, biomarkers, and injuries.
"""

import copy
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Biomarker reference ranges (common units)
BIOMARKER_THRESHOLDS = {
    "hemoglobin": {"low": 12.0, "high": 17.5, "unit": "g/dL"},
    "vitamin_d": {"low": 30.0, "high": 100.0, "unit": "ng/mL"},
    "vitamin_b12": {"low": 200.0, "high": 900.0, "unit": "pg/mL"},
    "iron": {"low": 60.0, "high": 170.0, "unit": "mcg/dL"},
    "ferritin": {"low": 20.0, "high": 300.0, "unit": "ng/mL"},
    "tsh": {"low": 0.4, "high": 4.0, "unit": "mIU/L"},
    "blood_sugar_fasting": {"low": 70.0, "high": 100.0, "unit": "mg/dL"},
    "hba1c": {"low": 4.0, "high": 5.7, "unit": "%"},
    "total_cholesterol": {"low": 0.0, "high": 200.0, "unit": "mg/dL"},
    "ldl": {"low": 0.0, "high": 100.0, "unit": "mg/dL"},
    "systolic_bp": {"low": 90.0, "high": 120.0, "unit": "mmHg"},
    "diastolic_bp": {"low": 60.0, "high": 80.0, "unit": "mmHg"},
    "creatinine": {"low": 0.6, "high": 1.2, "unit": "mg/dL"},
    "uric_acid": {"low": 2.5, "high": 7.0, "unit": "mg/dL"},
    "calcium": {"low": 8.5, "high": 10.5, "unit": "mg/dL"},
    "potassium": {"low": 3.5, "high": 5.0, "unit": "mEq/L"},
}

# Exercises to avoid for specific injuries
INJURY_EXERCISE_BLACKLIST = {
    "knee": [
        "Barbell Back Squat", "Leg Extension", "Box Jumps", "Burpees",
        "Jump Rope", "Walking Lunges", "Bulgarian Split Squat",
    ],
    "shoulder": [
        "Overhead Press (Barbell)", "Dumbbell Shoulder Press", "Upright Row",
        "Arnold Press", "Lateral Raise", "Pike Push-ups", "Dips (Chest Focus)",
    ],
    "lower_back": [
        "Barbell Deadlift", "Barbell Bent-Over Row", "Barbell Back Squat",
        "T-Bar Row", "Romanian Deadlift", "Good Mornings",
    ],
    "wrist": [
        "Barbell Bench Press", "Barbell Curl", "Overhead Press (Barbell)",
        "Push-ups", "Diamond Push-ups", "Skull Crushers (Lying Tricep Extension)",
    ],
    "ankle": [
        "Box Jumps", "Jump Rope", "Burpees", "Walking Lunges",
        "Calf Raise (Standing)", "High Knees", "Jumping Jacks",
    ],
    "hip": [
        "Barbell Back Squat", "Barbell Deadlift", "Walking Lunges",
        "Sumo Squat", "Bulgarian Split Squat", "Hip Thrust",
    ],
    "elbow": [
        "Skull Crushers (Lying Tricep Extension)", "Close-Grip Bench Press",
        "Barbell Curl", "Preacher Curl", "Diamond Push-ups",
    ],
    "neck": [
        "Overhead Press (Barbell)", "Barbell Back Squat",
        "Upright Row", "Barbell Deadlift",
    ],
}

# Safe alternative exercises for injuries
INJURY_SAFE_ALTERNATIVES = {
    "knee": ["Glute Bridge", "Leg Curl (Lying)", "Wall Sit", "Seated Cable Row", "Plank"],
    "shoulder": ["Dumbbell Bicep Curl", "Leg Press", "Plank", "Dead Bug", "Cable Curl"],
    "lower_back": ["Leg Press", "Machine Chest Press", "Lat Pulldown", "Leg Curl (Lying)", "Plank"],
    "wrist": ["Leg Press", "Leg Curl (Lying)", "Machine Chest Press", "Cable Curl", "Plank"],
    "ankle": ["Seated Cable Row", "Lat Pulldown", "Machine Chest Press", "Leg Press", "Leg Extension"],
    "hip": ["Leg Extension", "Leg Curl (Lying)", "Machine Chest Press", "Lat Pulldown", "Plank"],
    "elbow": ["Leg Press", "Bodyweight Squat", "Plank", "Glute Bridge", "Walking Lunges"],
    "neck": ["Dumbbell Bench Press", "Leg Press", "Cable Curl", "Tricep Pushdown", "Plank"],
}


def _detect_biomarker_issues(biomarkers: dict) -> list[dict]:
    """Detect biomarker values outside normal ranges."""
    issues = []
    for name, value in biomarkers.items():
        name_lower = name.lower().replace(" ", "_")
        if name_lower in BIOMARKER_THRESHOLDS:
            ref = BIOMARKER_THRESHOLDS[name_lower]
            if value < ref["low"]:
                issues.append({
                    "biomarker": name,
                    "value": value,
                    "status": "low",
                    "reference_low": ref["low"],
                    "reference_high": ref["high"],
                })
            elif value > ref["high"]:
                issues.append({
                    "biomarker": name,
                    "value": value,
                    "status": "high",
                    "reference_low": ref["low"],
                    "reference_high": ref["high"],
                })
    return issues


def adapt_workout(
    workout_plan: dict,
    biomarkers: dict,
    conditions: list[str],
    injuries: list[str],
) -> dict:
    """
    Adapt a workout plan based on health data.

    Returns:
        Dict with adapted_plan, adaptations_made, and warnings.
    """
    adapted_plan = copy.deepcopy(workout_plan)
    adaptations = []
    warnings = []

    # Detect biomarker issues
    bio_issues = _detect_biomarker_issues(biomarkers)
    conditions_lower = [c.lower().replace(" ", "_") for c in conditions]
    injuries_lower = [inj.lower().replace(" ", "_") for inj in injuries]

    # ---- Low Hemoglobin / Anemia ----
    hemoglobin_issue = next((i for i in bio_issues if "hemoglobin" in i["biomarker"].lower()), None)
    if hemoglobin_issue and hemoglobin_issue["status"] == "low" or "anemia" in conditions_lower:
        adaptations.append("Reduced exercise intensity due to low hemoglobin/anemia")
        warnings.append("Low hemoglobin detected. Avoid high-intensity training until levels improve.")

        for session in adapted_plan.get("sessions", []):
            # Remove HIIT exercises
            session["exercises"] = [
                ex for ex in session.get("exercises", [])
                if ex["name"] not in ["Burpees", "Box Jumps", "Battle Rope Waves"]
            ]
            # Increase rest periods
            for ex in session.get("exercises", []):
                ex["rest_seconds"] = max(ex.get("rest_seconds", 60), 90)
            session["notes"] = session.get("notes", []) + [
                "Monitor energy levels closely. Stop if feeling dizzy or fatigued.",
                "Reduce intensity by 20-30% from normal.",
            ]

    # ---- Low Vitamin D ----
    vit_d_issue = next((i for i in bio_issues if "vitamin_d" in i["biomarker"].lower()), None)
    if vit_d_issue and vit_d_issue["status"] == "low":
        adaptations.append("Added outdoor exercise recommendations for vitamin D synthesis")
        for session in adapted_plan.get("sessions", []):
            session["notes"] = session.get("notes", []) + [
                "Prefer outdoor workouts when possible for natural vitamin D synthesis.",
                "Morning outdoor exercise (7-10 AM) is ideal for sun exposure.",
            ]

    # ---- Thyroid Issues ----
    tsh_issue = next((i for i in bio_issues if "tsh" in i["biomarker"].lower()), None)
    if tsh_issue or "thyroid" in conditions_lower or "hypothyroid" in conditions_lower or "hyperthyroid" in conditions_lower:
        adaptations.append("Adjusted cardio intensity for thyroid condition")
        warnings.append("Thyroid condition detected. Monitor heart rate during exercise.")

        for session in adapted_plan.get("sessions", []):
            notes = session.get("notes", [])
            notes.append("Keep cardio at moderate intensity (60-70% max heart rate).")
            notes.append("Monitor fatigue levels and adjust volume accordingly.")
            session["notes"] = notes

    # ---- Diabetes / High Blood Sugar ----
    sugar_issue = next((i for i in bio_issues if "blood_sugar" in i["biomarker"].lower() or "hba1c" in i["biomarker"].lower()), None)
    if sugar_issue and sugar_issue["status"] == "high" or "diabetic" in conditions_lower or "diabetes" in conditions_lower:
        adaptations.append("Added regular moderate cardio for blood sugar management")
        warnings.append("Elevated blood sugar. Include regular moderate cardio and monitor glucose levels.")

        for session in adapted_plan.get("sessions", []):
            notes = session.get("notes", [])
            notes.append("Include 15-20 min of moderate cardio (walking, cycling) with each session.")
            notes.append("Carry glucose tablets or a quick sugar source during workouts.")
            notes.append("Check blood sugar before and after exercise.")
            session["notes"] = notes

    # ---- High Blood Pressure ----
    bp_issue = next(
        (i for i in bio_issues if "systolic_bp" in i["biomarker"].lower() or "diastolic_bp" in i["biomarker"].lower()),
        None,
    )
    if bp_issue and bp_issue["status"] == "high" or "hypertension" in conditions_lower or "high_blood_pressure" in conditions_lower:
        adaptations.append("Removed heavy isometric holds and adjusted breathing guidance")
        warnings.append("High blood pressure detected. Avoid Valsalva maneuver and heavy isometric holds.")

        heavy_iso_exercises = {"Wall Sit", "Plank", "Barbell Deadlift", "Barbell Back Squat"}

        for session in adapted_plan.get("sessions", []):
            # Remove or modify heavy isometric exercises
            modified_exercises = []
            for ex in session.get("exercises", []):
                if ex["name"] in heavy_iso_exercises:
                    ex["notes"] = (ex.get("notes") or "") + " Use lighter weight. Breathe continuously. Avoid holding breath."
                    if ex["name"] == "Wall Sit":
                        continue  # Skip wall sits entirely
                modified_exercises.append(ex)
            session["exercises"] = modified_exercises
            session["notes"] = session.get("notes", []) + [
                "Focus on breathing throughout all exercises. Never hold your breath.",
                "Avoid lifting overhead with very heavy weights.",
            ]

    # ---- High Cholesterol ----
    chol_issue = next((i for i in bio_issues if "cholesterol" in i["biomarker"].lower() or "ldl" in i["biomarker"].lower()), None)
    if chol_issue and chol_issue["status"] == "high" or "high_cholesterol" in conditions_lower:
        adaptations.append("Emphasized cardiovascular exercise for cholesterol management")
        for session in adapted_plan.get("sessions", []):
            session["notes"] = session.get("notes", []) + [
                "Include at least 20 minutes of moderate cardio (brisk walking, cycling, swimming).",
                "Aim for 150+ minutes of moderate cardio per week.",
            ]

    # ---- Injuries ----
    for injury in injuries_lower:
        if injury in INJURY_EXERCISE_BLACKLIST:
            blacklisted = set(INJURY_EXERCISE_BLACKLIST[injury])
            safe_alts = INJURY_SAFE_ALTERNATIVES.get(injury, [])

            adaptations.append(f"Removed exercises contraindicated for {injury} injury")

            for session in adapted_plan.get("sessions", []):
                filtered = []
                for ex in session.get("exercises", []):
                    if ex["name"] in blacklisted:
                        # Try to substitute
                        if safe_alts:
                            alt = safe_alts[len(filtered) % len(safe_alts)]
                            ex_copy = copy.deepcopy(ex)
                            ex_copy["name"] = alt
                            ex_copy["notes"] = f"Substituted due to {injury} injury. Original: {ex['name']}"
                            filtered.append(ex_copy)
                    else:
                        filtered.append(ex)
                session["exercises"] = filtered

    # ---- Joint Pain (general) ----
    if "joint_pain" in conditions_lower or "arthritis" in conditions_lower:
        adaptations.append("Replaced high-impact exercises with joint-friendly alternatives")
        warnings.append("Joint pain present. Avoid high-impact exercises.")

        high_impact = {"Burpees", "Box Jumps", "Jump Rope", "Jumping Jacks", "High Knees"}
        for session in adapted_plan.get("sessions", []):
            session["exercises"] = [
                ex for ex in session.get("exercises", [])
                if ex["name"] not in high_impact
            ]
            session["warmup"] = [
                "Gentle joint circles for all major joints (2 minutes)",
                "Light walking in place (2 minutes)",
                "Dynamic stretching at reduced range (3 minutes)",
            ]
            session["notes"] = session.get("notes", []) + [
                "Avoid exercises that cause joint pain. Pain is a signal to stop.",
                "Use lighter weights with controlled movements.",
            ]

    # ---- Low Iron / Ferritin ----
    iron_issue = next(
        (i for i in bio_issues if "iron" in i["biomarker"].lower() or "ferritin" in i["biomarker"].lower()),
        None,
    )
    if iron_issue and iron_issue["status"] == "low":
        adaptations.append("Reduced training volume due to low iron/ferritin")
        warnings.append("Low iron/ferritin. Reduce training volume and prioritize recovery.")
        for session in adapted_plan.get("sessions", []):
            for ex in session.get("exercises", []):
                ex["sets"] = max(2, ex.get("sets", 3) - 1)

    # ---- Kidney Issues ----
    creatinine_issue = next((i for i in bio_issues if "creatinine" in i["biomarker"].lower()), None)
    if creatinine_issue and creatinine_issue["status"] == "high" or "kidney_disease" in conditions_lower:
        adaptations.append("Reduced overall intensity for kidney health")
        warnings.append("Elevated creatinine. Avoid extreme exertion and stay well hydrated.")
        for session in adapted_plan.get("sessions", []):
            session["notes"] = session.get("notes", []) + [
                "Stay very well hydrated throughout the workout.",
                "Avoid extreme exertion. Keep intensity moderate.",
            ]

    if not adaptations:
        adaptations.append("No adaptations needed based on provided health data")

    return {
        "adapted_plan": adapted_plan,
        "adaptations_made": adaptations,
        "warnings": warnings,
    }
