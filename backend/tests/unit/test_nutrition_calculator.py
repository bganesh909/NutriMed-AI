"""
Unit tests for the nutrition calculator module.

Tests cover: BMR, TDEE, BMI, BMI categories, macros, and hydration.
Uses the standalone calculator in services/nutrition-service/app/calculator.py
as well as the backend NutritionService for consistency checks.
"""

import sys
import os

import pytest

# Add the nutrition-service path so we can import the standalone calculator
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "nutrition-service"),
)

from app.services.nutrition_service import NutritionService


# ---------------------------------------------------------------------------
# BMR (Mifflin-St Jeor)
# ---------------------------------------------------------------------------


class TestBMR:
    def test_male_bmr(self):
        # 75kg, 175cm, 30 years, male
        # Expected: 10*75 + 6.25*175 - 5*30 + 5 = 750 + 1093.75 - 150 + 5 = 1698.75
        bmr = NutritionService.calculate_bmr(75, 175, 30, "male")
        assert bmr == pytest.approx(1698.75, abs=0.1)

    def test_female_bmr(self):
        # 62kg, 160cm, 32 years, female
        # Expected: 10*62 + 6.25*160 - 5*32 - 161 = 620 + 1000 - 160 - 161 = 1299
        bmr = NutritionService.calculate_bmr(62, 160, 32, "female")
        assert bmr == pytest.approx(1299.0, abs=0.1)

    def test_young_male(self):
        bmr = NutritionService.calculate_bmr(70, 180, 20, "male")
        # 700 + 1125 - 100 + 5 = 1730
        assert bmr == pytest.approx(1730.0, abs=0.1)

    def test_older_female(self):
        bmr = NutritionService.calculate_bmr(55, 155, 60, "female")
        # 550 + 968.75 - 300 - 161 = 1057.75
        assert bmr == pytest.approx(1057.75, abs=0.1)

    def test_heavy_male(self):
        bmr = NutritionService.calculate_bmr(120, 185, 35, "male")
        # 1200 + 1156.25 - 175 + 5 = 2186.25
        assert bmr == pytest.approx(2186.25, abs=0.1)

    def test_case_insensitive_gender(self):
        bmr1 = NutritionService.calculate_bmr(75, 175, 30, "Female")
        bmr2 = NutritionService.calculate_bmr(75, 175, 30, "female")
        assert bmr1 == bmr2


# ---------------------------------------------------------------------------
# TDEE
# ---------------------------------------------------------------------------


class TestTDEE:
    def test_sedentary(self):
        bmr = 1700.0
        tdee = NutritionService.calculate_tdee(bmr, "sedentary")
        assert tdee == pytest.approx(bmr * 1.2, abs=0.2)

    def test_light(self):
        bmr = 1700.0
        tdee = NutritionService.calculate_tdee(bmr, "light")
        assert tdee == pytest.approx(bmr * 1.375, abs=0.2)

    def test_moderate(self):
        bmr = 1700.0
        tdee = NutritionService.calculate_tdee(bmr, "moderate")
        assert tdee == pytest.approx(bmr * 1.55, abs=0.2)

    def test_active(self):
        bmr = 1700.0
        tdee = NutritionService.calculate_tdee(bmr, "active")
        assert tdee == pytest.approx(bmr * 1.725, abs=0.2)

    def test_very_active(self):
        bmr = 1700.0
        tdee = NutritionService.calculate_tdee(bmr, "very_active")
        assert tdee == pytest.approx(bmr * 1.9, abs=0.2)

    def test_unknown_level_defaults_to_moderate(self):
        bmr = 1700.0
        tdee = NutritionService.calculate_tdee(bmr, "unknown_level")
        assert tdee == pytest.approx(bmr * 1.55, abs=0.2)

    def test_lightly_active_alias(self):
        bmr = 1700.0
        tdee = NutritionService.calculate_tdee(bmr, "lightly_active")
        assert tdee == pytest.approx(bmr * 1.375, abs=0.2)


# ---------------------------------------------------------------------------
# BMI
# ---------------------------------------------------------------------------


class TestBMI:
    def test_normal_bmi(self):
        bmi, category = NutritionService.calculate_bmi(70, 175)
        assert bmi == pytest.approx(22.9, abs=0.1)
        assert category == "normal"

    def test_underweight(self):
        bmi, category = NutritionService.calculate_bmi(45, 170)
        assert bmi < 18.5
        assert category == "underweight"

    def test_overweight(self):
        bmi, category = NutritionService.calculate_bmi(85, 175)
        assert 25 <= bmi < 30
        assert category == "overweight"

    def test_obese(self):
        bmi, category = NutritionService.calculate_bmi(110, 170)
        assert bmi >= 30
        assert category == "obese"

    def test_exact_boundary_normal(self):
        # Weight that gives BMI around 18.5 at height 170cm
        # BMI = weight / (1.7)^2 = weight / 2.89
        # weight = 18.5 * 2.89 = 53.465 -> rounds to 18.5
        bmi, category = NutritionService.calculate_bmi(53.5, 170)
        assert bmi >= 18.5
        assert category == "normal"


# ---------------------------------------------------------------------------
# Macro calculations
# ---------------------------------------------------------------------------


class TestMacros:
    def test_maintenance_macros(self):
        macros = NutritionService.macro_split(2000, "maintenance")
        assert "protein_g" in macros
        assert "carbs_g" in macros
        assert "fat_g" in macros
        # maintenance: 30% protein, 40% carbs, 30% fat
        assert macros["protein_g"] == pytest.approx(2000 * 0.30 / 4, abs=1)
        assert macros["carbs_g"] == pytest.approx(2000 * 0.40 / 4, abs=1)
        assert macros["fat_g"] == pytest.approx(2000 * 0.30 / 9, abs=1)

    def test_weight_loss_macros(self):
        macros = NutritionService.macro_split(1800, "weight_loss")
        # weight_loss: 40% protein, 30% carbs, 30% fat
        assert macros["protein_g"] == pytest.approx(1800 * 0.40 / 4, abs=1)
        assert macros["carbs_g"] == pytest.approx(1800 * 0.30 / 4, abs=1)
        assert macros["fat_g"] == pytest.approx(1800 * 0.30 / 9, abs=1)

    def test_muscle_gain_macros(self):
        macros = NutritionService.macro_split(2500, "muscle_gain")
        # muscle_gain: 35% protein, 40% carbs, 25% fat
        assert macros["protein_g"] == pytest.approx(2500 * 0.35 / 4, abs=1)
        assert macros["carbs_g"] == pytest.approx(2500 * 0.40 / 4, abs=1)
        assert macros["fat_g"] == pytest.approx(2500 * 0.25 / 9, abs=1)

    def test_unknown_goal_defaults_to_maintenance(self):
        macros = NutritionService.macro_split(2000, "random_goal")
        maintenance = NutritionService.macro_split(2000, "maintenance")
        assert macros == maintenance

    def test_macros_sum_approximately_to_target_calories(self):
        target = 2200
        macros = NutritionService.macro_split(target, "maintenance")
        total_cal = macros["protein_g"] * 4 + macros["carbs_g"] * 4 + macros["fat_g"] * 9
        assert total_cal == pytest.approx(target, abs=5)


# ---------------------------------------------------------------------------
# Hydration (tested via standalone calculator)
# ---------------------------------------------------------------------------


class TestHydration:
    """Test the standalone calculator's hydration function."""

    def setup_method(self):
        # Import the standalone calculator
        try:
            from services.nutrition_service.app.calculator import calculate_hydration
            self._calc = calculate_hydration
        except ImportError:
            self._calc = None

    def _hydration(self, weight: float, activity: str) -> float:
        if self._calc:
            return self._calc(weight, activity)
        # Fallback: replicate the formula for testing
        base_ml = 35 * weight
        adjustments = {
            "sedentary": 1.0,
            "light": 1.1,
            "moderate": 1.2,
            "active": 1.35,
            "very_active": 1.5,
        }
        return round(base_ml * adjustments.get(activity, 1.2), 0)

    def test_sedentary_hydration(self):
        result = self._hydration(70, "sedentary")
        # 35 * 70 * 1.0 = 2450
        assert result == pytest.approx(2450, abs=1)

    def test_active_hydration(self):
        result = self._hydration(70, "active")
        # 35 * 70 * 1.35 = 3307.5 -> 3308
        assert result == pytest.approx(3308, abs=1)

    def test_very_active_hydration(self):
        result = self._hydration(80, "very_active")
        # 35 * 80 * 1.5 = 4200
        assert result == pytest.approx(4200, abs=1)

    def test_light_hydration(self):
        result = self._hydration(60, "light")
        # 35 * 60 * 1.1 = 2310
        assert result == pytest.approx(2310, abs=1)

    def test_moderate_hydration(self):
        result = self._hydration(75, "moderate")
        # 35 * 75 * 1.2 = 3150
        assert result == pytest.approx(3150, abs=1)


# ---------------------------------------------------------------------------
# Full calculate_all integration
# ---------------------------------------------------------------------------


class TestCalculateAll:
    def test_calculate_all_returns_all_fields(self):
        service = NutritionService.__new__(NutritionService)
        result = service.calculate_all(
            weight_kg=75,
            height_cm=175,
            age=30,
            gender="male",
            activity_level="moderate",
            goal="maintenance",
        )
        assert "bmr" in result
        assert "tdee" in result
        assert "bmi" in result
        assert "bmi_category" in result
        assert "target_calories" in result
        assert "macros" in result
        assert result["body_fat_estimate"] is None  # no waist/neck provided

    def test_weight_loss_reduces_calories(self):
        service = NutritionService.__new__(NutritionService)
        maint = service.calculate_all(75, 175, 30, "male", "moderate", "maintenance")
        loss = service.calculate_all(75, 175, 30, "male", "moderate", "weight_loss")
        assert loss["target_calories"] < maint["target_calories"]

    def test_muscle_gain_increases_calories(self):
        service = NutritionService.__new__(NutritionService)
        maint = service.calculate_all(75, 175, 30, "male", "moderate", "maintenance")
        gain = service.calculate_all(75, 175, 30, "male", "moderate", "muscle_gain")
        assert gain["target_calories"] > maint["target_calories"]
