"""
Nutrition calculations module.
Implements standard formulas for BMR, TDEE, BMI, body fat, macros, and hydration.
"""

import math
from typing import Optional


ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Calculate Basal Metabolic Rate using the Mifflin-St Jeor equation.
    Considered the most accurate for most populations.

    Args:
        weight_kg: Body weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        gender: 'male' or 'female'

    Returns:
        BMR in kcal/day
    """
    if gender == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """
    Calculate Total Daily Energy Expenditure.

    Args:
        bmr: Basal Metabolic Rate in kcal/day
        activity_level: One of sedentary, light, moderate, active, very_active

    Returns:
        TDEE in kcal/day
    """
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    return round(bmr * multiplier, 1)


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """
    Calculate Body Mass Index.

    Args:
        weight_kg: Body weight in kilograms
        height_cm: Height in centimeters

    Returns:
        BMI value
    """
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def get_bmi_category(bmi: float) -> str:
    """Return BMI category string."""
    if bmi < 16.0:
        return "Severe Thinness"
    elif bmi < 17.0:
        return "Moderate Thinness"
    elif bmi < 18.5:
        return "Underweight"
    elif bmi < 25.0:
        return "Normal"
    elif bmi < 30.0:
        return "Overweight"
    elif bmi < 35.0:
        return "Obese Class I"
    elif bmi < 40.0:
        return "Obese Class II"
    else:
        return "Obese Class III"


def estimate_body_fat(
    waist_cm: float,
    neck_cm: float,
    height_cm: float,
    hip_cm: Optional[float] = None,
    gender: str = "male",
) -> float:
    """
    Estimate body fat percentage using the US Navy method.

    Args:
        waist_cm: Waist circumference in cm (measured at navel)
        neck_cm: Neck circumference in cm
        height_cm: Height in cm
        hip_cm: Hip circumference in cm (required for females)
        gender: 'male' or 'female'

    Returns:
        Estimated body fat percentage
    """
    if gender == "male":
        # Male formula: 86.010 * log10(waist - neck) - 70.041 * log10(height) + 36.76
        if waist_cm <= neck_cm:
            return 5.0  # minimum reasonable value
        bf = (
            86.010 * math.log10(waist_cm - neck_cm)
            - 70.041 * math.log10(height_cm)
            + 36.76
        )
    else:
        # Female formula: 163.205 * log10(waist + hip - neck) - 97.684 * log10(height) - 78.387
        if hip_cm is None:
            hip_cm = waist_cm * 1.1  # rough estimate if not provided
        denominator = waist_cm + hip_cm - neck_cm
        if denominator <= 0:
            return 10.0  # minimum reasonable value
        bf = (
            163.205 * math.log10(denominator)
            - 97.684 * math.log10(height_cm)
            - 78.387
        )

    return round(max(bf, 3.0), 1)  # clamp to minimum 3%


def calculate_macros(tdee: float, goal: str, weight_kg: float) -> dict:
    """
    Calculate macronutrient targets based on goal.

    Args:
        tdee: Total Daily Energy Expenditure
        goal: fat_loss, muscle_gain, maintenance, or recomposition
        weight_kg: Body weight in kg (used for protein calculation)

    Returns:
        Dict with calories, protein_g, carbs_g, fat_g, and fiber_g
    """
    if goal == "fat_loss":
        target_calories = tdee - 500
        protein_per_kg = 2.2
        fat_pct = 0.25
    elif goal == "muscle_gain":
        target_calories = tdee + 300
        protein_per_kg = 2.0
        fat_pct = 0.25
    elif goal == "recomposition":
        target_calories = tdee
        protein_per_kg = 2.4
        fat_pct = 0.25
    else:  # maintenance
        target_calories = tdee
        protein_per_kg = 1.8
        fat_pct = 0.25

    target_calories = max(target_calories, 1200)  # safety floor

    protein_g = round(protein_per_kg * weight_kg, 1)
    protein_cal = protein_g * 4

    fat_cal = target_calories * fat_pct
    fat_g = round(fat_cal / 9, 1)

    carbs_cal = target_calories - protein_cal - fat_cal
    carbs_g = round(max(carbs_cal / 4, 50), 1)  # minimum 50g carbs

    # Recalculate actual total
    actual_calories = round(protein_g * 4 + carbs_g * 4 + fat_g * 9, 0)

    fiber_g = round(target_calories / 1000 * 14, 1)  # ~14g per 1000 cal

    return {
        "calories": int(actual_calories),
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
        "fiber_g": fiber_g,
        "protein_pct": round(protein_cal / actual_calories * 100, 1) if actual_calories > 0 else 0,
        "carbs_pct": round(carbs_g * 4 / actual_calories * 100, 1) if actual_calories > 0 else 0,
        "fat_pct": round(fat_g * 9 / actual_calories * 100, 1) if actual_calories > 0 else 0,
    }


def calculate_hydration(weight_kg: float, activity_level: str) -> float:
    """
    Calculate recommended daily water intake.

    Base recommendation: 35ml per kg of body weight.
    Adjusted upward for higher activity levels.

    Args:
        weight_kg: Body weight in kg
        activity_level: Activity level string

    Returns:
        Recommended water intake in ml
    """
    base_ml = 35 * weight_kg

    activity_adjustments = {
        "sedentary": 1.0,
        "light": 1.1,
        "moderate": 1.2,
        "active": 1.35,
        "very_active": 1.5,
    }

    multiplier = activity_adjustments.get(activity_level, 1.2)
    return round(base_ml * multiplier, 0)
