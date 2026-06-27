"""
Workout plan generator.
Creates structured workout plans based on fitness level, goal, and available equipment.
"""

import random
from typing import Optional

from app.exercise_database import get_exercises_filtered

WORKOUT_TEMPLATES = {
    "beginner_fat_loss": {
        "days_per_week": 4,
        "split": "upper_lower",
        "exercises_per_session": 6,
        "sets": 3,
        "reps": "12-15",
        "rest": 60,
        "cardio": "20min moderate",
    },
    "beginner_muscle_gain": {
        "days_per_week": 4,
        "split": "upper_lower",
        "exercises_per_session": 6,
        "sets": 3,
        "reps": "10-12",
        "rest": 90,
        "cardio": "10min warmup",
    },
    "beginner_general_fitness": {
        "days_per_week": 3,
        "split": "full_body",
        "exercises_per_session": 6,
        "sets": 3,
        "reps": "10-15",
        "rest": 60,
        "cardio": "15min moderate",
    },
    "intermediate_fat_loss": {
        "days_per_week": 5,
        "split": "push_pull_legs",
        "exercises_per_session": 7,
        "sets": 4,
        "reps": "10-15",
        "rest": 45,
        "cardio": "25min moderate-high",
    },
    "intermediate_muscle_gain": {
        "days_per_week": 5,
        "split": "push_pull_legs",
        "exercises_per_session": 8,
        "sets": 4,
        "reps": "8-12",
        "rest": 90,
        "cardio": "10min warmup",
    },
    "intermediate_strength": {
        "days_per_week": 4,
        "split": "upper_lower",
        "exercises_per_session": 6,
        "sets": 4,
        "reps": "5-8",
        "rest": 120,
        "cardio": "10min warmup",
    },
    "intermediate_general_fitness": {
        "days_per_week": 4,
        "split": "upper_lower",
        "exercises_per_session": 7,
        "sets": 3,
        "reps": "8-12",
        "rest": 60,
        "cardio": "20min moderate",
    },
    "advanced_fat_loss": {
        "days_per_week": 6,
        "split": "ppl_upper_lower",
        "exercises_per_session": 8,
        "sets": 4,
        "reps": "12-15",
        "rest": 30,
        "cardio": "30min HIIT",
    },
    "advanced_muscle_gain": {
        "days_per_week": 6,
        "split": "ppl_upper_lower",
        "exercises_per_session": 8,
        "sets": 4,
        "reps": "6-12",
        "rest": 90,
        "cardio": "10min warmup",
    },
    "advanced_strength": {
        "days_per_week": 6,
        "split": "ppl_upper_lower",
        "exercises_per_session": 8,
        "sets": 5,
        "reps": "3-6",
        "rest": 180,
        "cardio": "optional",
    },
    "advanced_endurance": {
        "days_per_week": 5,
        "split": "push_pull_legs",
        "exercises_per_session": 8,
        "sets": 3,
        "reps": "15-20",
        "rest": 30,
        "cardio": "30min moderate-high",
    },
}

# Define which muscle groups go on each day for each split type
SPLIT_DEFINITIONS = {
    "full_body": {
        "days": [
            {"name": "Full Body A", "focus": "Full Body", "muscles": ["chest", "back", "legs", "shoulders", "core"]},
            {"name": "Full Body B", "focus": "Full Body", "muscles": ["back", "chest", "legs", "biceps", "triceps", "core"]},
            {"name": "Full Body C", "focus": "Full Body", "muscles": ["legs", "shoulders", "back", "chest", "core"]},
        ],
    },
    "upper_lower": {
        "days": [
            {"name": "Upper Body A", "focus": "Upper Body (Push Focus)", "muscles": ["chest", "shoulders", "triceps", "core"]},
            {"name": "Lower Body A", "focus": "Lower Body", "muscles": ["legs", "core"]},
            {"name": "Upper Body B", "focus": "Upper Body (Pull Focus)", "muscles": ["back", "biceps", "shoulders", "core"]},
            {"name": "Lower Body B", "focus": "Lower Body", "muscles": ["legs", "core"]},
        ],
    },
    "push_pull_legs": {
        "days": [
            {"name": "Push Day", "focus": "Chest, Shoulders, Triceps", "muscles": ["chest", "shoulders", "triceps"]},
            {"name": "Pull Day", "focus": "Back, Biceps", "muscles": ["back", "biceps"]},
            {"name": "Leg Day", "focus": "Legs, Core", "muscles": ["legs", "core"]},
            {"name": "Push Day B", "focus": "Chest, Shoulders, Triceps", "muscles": ["chest", "shoulders", "triceps"]},
            {"name": "Pull Day B", "focus": "Back, Biceps, Rear Delts", "muscles": ["back", "biceps", "shoulders"]},
        ],
    },
    "ppl_upper_lower": {
        "days": [
            {"name": "Push Day", "focus": "Chest, Shoulders, Triceps", "muscles": ["chest", "shoulders", "triceps"]},
            {"name": "Pull Day", "focus": "Back, Biceps", "muscles": ["back", "biceps"]},
            {"name": "Leg Day", "focus": "Legs", "muscles": ["legs", "core"]},
            {"name": "Upper Body", "focus": "Upper Body", "muscles": ["chest", "back", "shoulders", "biceps", "triceps"]},
            {"name": "Lower Body", "focus": "Lower Body & Core", "muscles": ["legs", "core"]},
            {"name": "Full Body / Weak Points", "focus": "Full Body", "muscles": ["chest", "back", "legs", "shoulders", "core"]},
        ],
    },
}

WARMUP_ROUTINES = {
    "upper": [
        "Arm circles (30 seconds each direction)",
        "Band pull-aparts (15 reps)",
        "Shoulder dislocates with band (10 reps)",
        "Cat-Cow stretches (10 reps)",
        "Light push-ups (10 reps)",
    ],
    "lower": [
        "Bodyweight squats (15 reps)",
        "Leg swings (10 each leg)",
        "Hip circles (10 each direction)",
        "Walking lunges (10 steps)",
        "Glute bridges (15 reps)",
    ],
    "full": [
        "Jumping jacks (30 seconds)",
        "Arm circles (20 seconds each direction)",
        "Bodyweight squats (10 reps)",
        "Inchworms (5 reps)",
        "High knees (20 seconds)",
    ],
    "cardio": [
        "Light jog in place (1 minute)",
        "Dynamic stretching (2 minutes)",
        "Leg swings (10 each leg)",
        "Arm circles (20 seconds each direction)",
    ],
}

COOLDOWN_ROUTINES = {
    "upper": [
        "Doorway chest stretch (30 seconds each side)",
        "Cross-body shoulder stretch (30 seconds each)",
        "Tricep stretch (30 seconds each)",
        "Cat-Cow (10 reps)",
        "Deep breathing (1 minute)",
    ],
    "lower": [
        "Standing quad stretch (30 seconds each leg)",
        "Seated hamstring stretch (30 seconds each leg)",
        "Pigeon pose (30 seconds each side)",
        "Calf stretch against wall (30 seconds each)",
        "Deep breathing (1 minute)",
    ],
    "full": [
        "Standing forward fold (30 seconds)",
        "Quad stretch (30 seconds each leg)",
        "Cross-body shoulder stretch (30 seconds each)",
        "Child's pose (30 seconds)",
        "Deep breathing (1 minute)",
    ],
}

PROGRESSIVE_OVERLOAD_GUIDELINES = {
    "beginner": [
        "Increase weight by 2.5-5 lbs when you can complete all sets with good form",
        "Focus on perfecting form before adding weight",
        "Add 1 rep per set each week until hitting the top of rep range, then increase weight",
        "Track your workouts to monitor progression",
    ],
    "intermediate": [
        "Increase weight by 5 lbs for upper body and 10 lbs for lower body when sets become easy",
        "Use double progression: increase reps first, then weight",
        "Consider periodization: alternate heavy and light weeks",
        "Aim to increase total volume (sets x reps x weight) by 5-10% monthly",
    ],
    "advanced": [
        "Use periodized programming (linear, undulating, or block periodization)",
        "Implement deload weeks every 4-6 weeks",
        "Track RPE (Rate of Perceived Exertion) to manage fatigue",
        "Consider advanced techniques: drop sets, supersets, rest-pause",
        "Vary rep ranges across mesocycles for continued adaptation",
    ],
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _select_exercises(
    muscles: list[str],
    equipment: list[str],
    difficulty: str,
    count: int,
) -> list[dict]:
    """Select exercises for given muscle groups using available equipment."""
    selected = []
    exercises_per_muscle = max(1, count // len(muscles))
    remainder = count - exercises_per_muscle * len(muscles)

    for i, muscle in enumerate(muscles):
        available = get_exercises_filtered(
            muscle_group=muscle,
            equipment=equipment,
            difficulty=difficulty,
        )

        if not available:
            # Fallback: try bodyweight only
            available = get_exercises_filtered(
                muscle_group=muscle,
                equipment=["bodyweight"],
                difficulty=difficulty,
            )

        if not available:
            continue

        # Shuffle for variety
        random.shuffle(available)

        take = exercises_per_muscle + (1 if i < remainder else 0)
        selected.extend(available[:take])

    return selected[:count]


def _get_warmup_type(muscles: list[str]) -> str:
    """Determine warmup type based on target muscles."""
    lower_muscles = {"legs"}
    upper_muscles = {"chest", "back", "shoulders", "biceps", "triceps"}

    has_lower = bool(set(muscles) & lower_muscles)
    has_upper = bool(set(muscles) & upper_muscles)

    if has_lower and has_upper:
        return "full"
    elif has_lower:
        return "lower"
    elif has_upper:
        return "upper"
    return "full"


def _distribute_training_days(days_per_week: int) -> list[int]:
    """Distribute training days across the week with rest days."""
    if days_per_week <= 3:
        # Mon, Wed, Fri
        return [0, 2, 4][:days_per_week]
    elif days_per_week == 4:
        return [0, 1, 3, 4]  # Mon, Tue, Thu, Fri
    elif days_per_week == 5:
        return [0, 1, 2, 3, 4]  # Mon-Fri
    elif days_per_week == 6:
        return [0, 1, 2, 3, 4, 5]  # Mon-Sat
    else:
        return list(range(7))


def generate_workout_plan(
    age: int,
    gender: str,
    weight_kg: float,
    height_cm: float,
    fitness_level: str,
    goal: str,
    days_per_week: int,
    session_duration_minutes: int,
    available_equipment: list[str],
    conditions: list[str],
    injuries: list[str],
) -> dict:
    """Generate a complete weekly workout plan."""

    # Find matching template
    template_key = f"{fitness_level}_{goal}"
    if template_key not in WORKOUT_TEMPLATES:
        # Fallback to closest match
        for key in WORKOUT_TEMPLATES:
            if key.startswith(fitness_level):
                template_key = key
                break
        else:
            template_key = "beginner_general_fitness"

    template = WORKOUT_TEMPLATES[template_key]

    # Adjust days per week
    actual_days = min(days_per_week, template["days_per_week"])

    # Get split definition
    split_type = template["split"]
    split_def = SPLIT_DEFINITIONS.get(split_type, SPLIT_DEFINITIONS["full_body"])
    split_days = split_def["days"]

    # Map training to calendar days
    training_day_indices = _distribute_training_days(actual_days)

    sessions = []
    for i, day_idx in enumerate(training_day_indices):
        split_day = split_days[i % len(split_days)]
        muscles = split_day["muscles"]

        # Select exercises
        exercises_raw = _select_exercises(
            muscles=muscles,
            equipment=available_equipment,
            difficulty=fitness_level,
            count=template["exercises_per_session"],
        )

        # Format exercises
        exercises = []
        for ex in exercises_raw:
            exercises.append({
                "name": ex["name"],
                "sets": template["sets"],
                "reps": template["reps"],
                "rest_seconds": template["rest"],
                "notes": f"Target: {ex['muscle_group']}",
                "alternatives": ex.get("alternatives", [])[:2],
            })

        # Add cardio if specified
        cardio_note = template.get("cardio", "")
        session_notes = []
        if cardio_note and cardio_note != "optional":
            session_notes.append(f"Cardio: {cardio_note}")

        # Get warmup/cooldown type
        warmup_type = _get_warmup_type(muscles)

        session = {
            "day": DAY_NAMES[day_idx],
            "focus": split_day["focus"],
            "warmup": WARMUP_ROUTINES.get(warmup_type, WARMUP_ROUTINES["full"]),
            "exercises": exercises,
            "cooldown": COOLDOWN_ROUTINES.get(warmup_type, COOLDOWN_ROUTINES["full"]),
            "estimated_duration_minutes": session_duration_minutes,
            "notes": session_notes,
        }
        sessions.append(session)

    # Add rest day notes
    general_notes = [
        f"Train {actual_days} days per week with adequate rest between sessions",
        "Stay hydrated: drink water before, during, and after workouts",
        "Get 7-9 hours of sleep for optimal recovery",
        "Ensure adequate protein intake (1.6-2.2g per kg body weight)",
    ]

    if age > 50:
        general_notes.append("Focus on joint-friendly exercises and longer warm-ups")
        general_notes.append("Consider working with a trainer to ensure proper form")

    if "flexibility" in goal:
        general_notes.append("Include 10-15 minutes of stretching after each session")
        general_notes.append("Consider adding yoga or mobility work on rest days")

    progressive_overload = PROGRESSIVE_OVERLOAD_GUIDELINES.get(
        fitness_level, PROGRESSIVE_OVERLOAD_GUIDELINES["beginner"]
    )

    return {
        "plan_name": f"{fitness_level.title()} {goal.replace('_', ' ').title()} Plan",
        "fitness_level": fitness_level,
        "goal": goal,
        "days_per_week": actual_days,
        "split_type": split_type,
        "sessions": sessions,
        "progressive_overload": progressive_overload,
        "general_notes": general_notes,
    }
