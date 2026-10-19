"""
Tests for plan grounding and verification.

The contract these protect: an LLM may choose *which* real foods and exercises
go into a plan, but every number and every safety-relevant instruction is
resolved from the curated databases, never taken from the model.
"""

import pytest

from app.data.exercise_database import EXERCISE_DATABASE
from app.data.food_database import FOOD_DATABASE
from app.services.lab_interpretation_service import LabInterpretationService
from app.services.plan_grounding import (
    format_exercise_catalogue,
    format_food_catalogue,
    select_exercises,
    select_foods,
    verify_diet_plan,
    verify_workout_plan,
)


ABNORMAL = {
    "vitamin_d": 14.5, "vitamin_b12": 180.0, "ferritin": 18.0,
    "hemoglobin": 11.2, "fasting_glucose": 118.0, "total_cholesterol": 232.0,
    "triglycerides": 195.0, "tsh": 5.8, "hdl": 38.0,
}


@pytest.fixture()
def rule_engine() -> dict:
    return LabInterpretationService().interpret(dict(ABNORMAL), "male")


def _food(name: str) -> dict:
    return next(f for f in FOOD_DATABASE if f["name"] == name)


class TestFoodSelection:
    def test_respects_vegan_preference(self, rule_engine):
        foods = select_foods("vegan", [], rule_engine)
        assert foods
        assert all("vegan" in f["tags"] for f in foods)

    def test_respects_vegetarian_preference(self, rule_engine):
        foods = select_foods("vegetarian", [], rule_engine)
        assert all("vegetarian" in f["tags"] for f in foods)

    def test_excludes_dairy_allergy(self, rule_engine):
        foods = select_foods("non_vegetarian", ["dairy"], rule_engine)
        assert all(f["category"] != "dairy" for f in foods)

    def test_excludes_shellfish_allergy(self, rule_engine):
        foods = select_foods("non_vegetarian", ["shellfish"], rule_engine)
        assert all("shellfish" not in f["tags"] for f in foods)

    def test_gluten_allergy_keeps_only_gluten_free(self, rule_engine):
        foods = select_foods("non_vegetarian", ["gluten"], rule_engine)
        assert all("gluten_free" in f["tags"] for f in foods)

    def test_prioritises_clinically_relevant_foods(self, rule_engine):
        """Dyslipidemia in the panel should surface omega-3 foods early."""
        foods = select_foods("non_vegetarian", [], rule_engine)
        top = foods[:10]
        assert any("omega3" in f["tags"] for f in top)

    def test_covers_multiple_categories(self, rule_engine):
        foods = select_foods("non_vegetarian", [], rule_engine)
        assert len({f["category"] for f in foods}) >= 6

    def test_unknown_allergen_falls_back_to_name_match(self, rule_engine):
        foods = select_foods("non_vegetarian", ["banana"], rule_engine)
        assert all("banana" not in f["name"].lower() for f in foods)


class TestExerciseSelection:
    def test_anemia_caps_difficulty(self, rule_engine):
        """Low hemoglobin must cap intensity even if 'advanced' was requested."""
        exercises = select_exercises("advanced", None, rule_engine)
        assert exercises
        assert all(e["difficulty"] == "beginner" for e in exercises)

    def test_includes_cardio_when_glucose_high(self, rule_engine):
        exercises = select_exercises("beginner", None, rule_engine)
        assert any(e["muscle_group"] == "cardio" for e in exercises)

    def test_covers_major_muscle_groups(self, rule_engine):
        exercises = select_exercises("intermediate", None, rule_engine)
        groups = {e["muscle_group"] for e in exercises}
        assert {"chest", "back", "legs", "core"} <= groups

    def test_equipment_filter(self):
        exercises = select_exercises("beginner", ["bodyweight"], None)
        assert all(e["equipment"] == "bodyweight" for e in exercises)

    def test_empty_equipment_match_does_not_strand_caller(self):
        exercises = select_exercises("beginner", ["jetpack"], None)
        assert exercises, "must fall back rather than return nothing"

    def test_no_findings_allows_requested_difficulty(self):
        exercises = select_exercises("intermediate", None, None)
        assert any(e["difficulty"] == "intermediate" for e in exercises)


class TestCatalogueFormatting:
    def test_food_catalogue_lists_macros(self):
        text = format_food_catalogue([_food("Oats (dry)")])
        assert "Oats (dry)" in text and "per 100g" in text and "389kcal" in text

    def test_exercise_catalogue_lists_metadata(self):
        ex = next(e for e in EXERCISE_DATABASE if e["name"] == "Push-ups")
        text = format_exercise_catalogue([ex])
        assert "Push-ups" in text and "chest" in text and "bodyweight" in text


class TestDietVerification:
    def _plan(self, foods):
        return {"meal_plan": [{"day": "Monday", "meals": [
            {"name": "Breakfast", "foods": foods}]}]}

    def test_recomputes_macros_from_database(self):
        oats = _food("Oats (dry)")
        plan, _ = verify_diet_plan(
            self._plan([{"name": "Oats (dry)", "quantity_g": 60, "calories": 9999}])
        )
        item = plan["meal_plan"][0]["meals"][0]["foods"][0]
        assert item["calories"] == pytest.approx(round(oats["calories"] * 0.6, 1))
        assert item["protein_g"] == pytest.approx(round(oats["protein_g"] * 0.6, 1))

    def test_drops_hallucinated_food(self):
        plan, warnings = verify_diet_plan(
            self._plan([{"name": "Unicorn Steak", "quantity_g": 200}])
        )
        assert plan["meal_plan"] == []
        assert any("Unicorn Steak" in w for w in warnings)

    def test_tolerates_typo_via_fuzzy_match(self):
        plan, _ = verify_diet_plan(
            self._plan([{"name": "Chicken Brest (cooked)", "quantity_g": 100}])
        )
        item = plan["meal_plan"][0]["meals"][0]["foods"][0]
        assert item["name"] == "Chicken Breast (cooked)"

    def test_parses_string_gram_quantity(self):
        plan, _ = verify_diet_plan(self._plan([{"name": "Almonds", "quantity_g": "30g"}]))
        assert plan["meal_plan"][0]["meals"][0]["foods"][0]["quantity_g"] == 30.0

    def test_unusable_quantity_defaults_and_warns(self):
        plan, warnings = verify_diet_plan(
            self._plan([{"name": "Almonds", "quantity_g": "a bowl"}])
        )
        assert plan["meal_plan"][0]["meals"][0]["foods"][0]["quantity_g"] == 100.0
        assert any("unusable quantity" in w for w in warnings)

    def test_rejects_absurd_portion(self):
        plan, warnings = verify_diet_plan(
            self._plan([{"name": "Almonds", "quantity_g": 99999}])
        )
        assert plan["meal_plan"][0]["meals"][0]["foods"][0]["quantity_g"] == 100.0
        assert warnings

    def test_totals_are_sums_of_items(self):
        plan, _ = verify_diet_plan(self._plan([
            {"name": "Almonds", "quantity_g": 100},
            {"name": "Chicken Breast (cooked)", "quantity_g": 100},
        ]))
        meal = plan["meal_plan"][0]["meals"][0]
        assert meal["calories"] == pytest.approx(
            sum(f["calories"] for f in meal["foods"]), abs=0.2
        )

    def test_marks_plan_verified(self):
        plan, _ = verify_diet_plan(self._plan([{"name": "Almonds", "quantity_g": 30}]))
        assert plan["verified"] is True

    def test_non_dict_input_passes_through(self):
        plan, warnings = verify_diet_plan("not a plan")
        assert plan == "not a plan" and warnings == []


class TestWorkoutVerification:
    def test_instructions_come_from_database_not_model(self):
        days, _ = verify_workout_plan([{"day_name": "D1", "exercises": [
            {"name": "Push-ups", "sets": 3, "reps": "10",
             "instructions": "arch your back hard and bounce"}]}])
        ex = days[0]["exercises"][0]
        real = next(e for e in EXERCISE_DATABASE if e["name"] == "Push-ups")
        assert ex["instructions"] == real["instructions"]
        assert "bounce" not in ex["instructions"]

    def test_drops_hallucinated_exercise(self):
        days, warnings = verify_workout_plan([{"day_name": "D1", "exercises": [
            {"name": "Quantum Bicep Blaster", "sets": 3}]}])
        assert days == []
        assert any("Quantum" in w for w in warnings)

    def test_attaches_metadata_and_alternatives(self):
        days, _ = verify_workout_plan([{"day_name": "D1", "exercises": [
            {"name": "Push-ups", "sets": 3, "reps": "10"}]}])
        ex = days[0]["exercises"][0]
        assert ex["muscle_group"] == "chest"
        assert ex["equipment"] == "bodyweight"
        assert ex["alternatives"]

    def test_coerces_sets_and_reps(self):
        days, _ = verify_workout_plan([{"day_name": "D1", "exercises": [
            {"name": "Push-ups", "sets": "4", "reps": 10}]}])
        ex = days[0]["exercises"][0]
        assert ex["sets"] == 4 and ex["reps"] == "10"

    def test_clamps_absurd_set_count(self):
        days, _ = verify_workout_plan([{"day_name": "D1", "exercises": [
            {"name": "Push-ups", "sets": 500}]}])
        assert days[0]["exercises"][0]["sets"] == 10

    def test_preserves_warmup_and_cooldown(self):
        days, _ = verify_workout_plan([{"day_name": "D1", "warm_up": "5 min walk",
            "cool_down": "stretching", "exercises": [{"name": "Push-ups", "sets": 3}]}])
        assert days[0]["warm_up"] == "5 min walk"
        assert days[0]["cool_down"] == "stretching"

    def test_non_list_input_returns_empty(self):
        days, warnings = verify_workout_plan({"not": "a list"})
        assert days == [] and warnings == []


class TestGoalNormalisation:
    """The app says 'weight_loss'; the calculator was written for 'fat_loss'."""

    def test_weight_loss_maps_to_fat_loss(self):
        from app.services.nutrition_calculator import normalise_goal
        assert normalise_goal("weight_loss") == "fat_loss"

    def test_general_health_maps_to_maintenance(self):
        from app.services.nutrition_calculator import normalise_goal
        assert normalise_goal("general_health") == "maintenance"

    def test_unknown_goal_defaults_to_maintenance(self):
        from app.services.nutrition_calculator import normalise_goal
        assert normalise_goal("banana") == "maintenance"

    def test_weight_loss_applies_a_deficit(self):
        """Regression: 'weight_loss' used to fall through to maintenance."""
        from app.services.plan_grounding import daily_calorie_target
        profile = {"weight": 75, "height": 175, "age": 30, "gender": "male",
                   "activity_level": "moderately_active"}
        cutting = daily_calorie_target({**profile, "goals": ["weight_loss"]})
        maintaining = daily_calorie_target({**profile, "goals": ["maintenance"]})
        assert cutting < maintaining

    def test_target_is_clamped_to_a_safe_range(self):
        from app.services.plan_grounding import daily_calorie_target
        tiny = daily_calorie_target({"weight": 5, "height": 50, "age": 1, "gender": "female"})
        assert 1200 <= tiny <= 4500

    def test_missing_profile_returns_a_default(self):
        from app.services.plan_grounding import daily_calorie_target
        assert 1200 <= daily_calorie_target({}) <= 4500


class TestNutritionalAdequacy:
    """Correct arithmetic is not the same as a sensible plan."""

    def test_rejects_day_far_below_target(self):
        from app.services.plan_grounding import plan_is_nutritionally_adequate
        plan = {"meal_plan": [{"day": "Monday", "calories": 888, "meals": [
            {"name": "Breakfast", "calories": 400, "foods": [{"category": "grain"}]},
            {"name": "Lunch", "calories": 300, "foods": [{"category": "protein"}]},
            {"name": "Dinner", "calories": 188, "foods": [{"category": "protein"}]},
        ]}]}
        ok, reasons = plan_is_nutritionally_adequate(plan, 2134)
        assert not ok
        assert any("below" in r for r in reasons)

    def test_rejects_main_meal_of_only_fats(self):
        """Regression: a live run produced a 'lunch' of 10g of coconut oil."""
        from app.services.plan_grounding import plan_is_nutritionally_adequate
        plan = {"meal_plan": [{"day": "Monday", "calories": 2100, "meals": [
            {"name": "Breakfast", "calories": 700, "foods": [{"category": "grain"}]},
            {"name": "Lunch", "calories": 700, "foods": [{"category": "fat"}]},
            {"name": "Dinner", "calories": 700, "foods": [{"category": "protein"}]},
        ]}]}
        ok, reasons = plan_is_nutritionally_adequate(plan, 2134)
        assert not ok
        assert any("Lunch" in r for r in reasons)

    def test_rejects_too_few_meals(self):
        from app.services.plan_grounding import plan_is_nutritionally_adequate
        plan = {"meal_plan": [{"day": "Monday", "calories": 2100, "meals": [
            {"name": "Breakfast", "calories": 2100, "foods": [{"category": "grain"}]},
        ]}]}
        ok, reasons = plan_is_nutritionally_adequate(plan, 2134)
        assert not ok
        assert any("meal(s)" in r for r in reasons)

    def test_rejects_empty_plan(self):
        from app.services.plan_grounding import plan_is_nutritionally_adequate
        assert not plan_is_nutritionally_adequate({"meal_plan": []}, 2000)[0]

    def test_accepts_a_balanced_day(self):
        from app.services.plan_grounding import plan_is_nutritionally_adequate
        plan = {"meal_plan": [{"day": "Monday", "calories": 2100, "meals": [
            {"name": "Breakfast", "calories": 600,
             "foods": [{"category": "grain"}, {"category": "fruit"}]},
            {"name": "Lunch", "calories": 800,
             "foods": [{"category": "protein"}, {"category": "grain"}, {"category": "vegetable"}]},
            {"name": "Dinner", "calories": 700,
             "foods": [{"category": "protein"}, {"category": "vegetable"}]},
        ]}]}
        ok, reasons = plan_is_nutritionally_adequate(plan, 2134)
        assert ok, reasons


class TestDeterministicFallbacks:
    """A user must never be left with an empty plan."""

    def test_diet_fallback_is_adequate(self):
        from app.services.diet_templates import build_fallback_meal_plan
        from app.services.plan_grounding import plan_is_nutritionally_adequate
        plan = build_fallback_meal_plan(
            weight_kg=75, height_cm=175, age=30, gender="male",
            activity_level="moderate", goal="maintenance",
            dietary_preference="vegetarian", num_days=3,
        )
        assert len(plan["meal_plan"]) == 3
        ok, reasons = plan_is_nutritionally_adequate(plan, plan["calories"])
        assert ok, reasons

    def test_workout_fallback_survives_verification(self):
        from app.services.plan_grounding import verify_workout_plan
        from app.services.workout_templates import build_fallback_days
        days = build_fallback_days(fitness_level="beginner", goal="fat_loss", days_per_week=4)
        verified, warnings = verify_workout_plan(days)
        assert len(verified) == len(days)
        assert warnings == [], "template output must all resolve to the catalogue"
        assert all(e["instructions"] for d in verified for e in d["exercises"])


class TestNameResolution:
    """
    Models write natural names, not database keys. Reasonable variants must
    resolve; invented items must not.
    """

    @pytest.mark.parametrize("written,expected", [
        ("Chicken Breast", "Chicken Breast (cooked)"),
        ("chicken breast", "Chicken Breast (cooked)"),
        ("Chicken Breast (cooked)", "Chicken Breast (cooked)"),
        ("Brown Rice", "Brown Rice (cooked)"),
        ("Oats", "Oats (dry)"),
        ("Greek Yogurt", "Greek Yogurt (plain)"),
    ])
    def test_resolves_food_name_variants(self, written, expected):
        from app.services.plan_grounding import _FOOD_BY_NAME, _lookup
        found = _lookup(written, _FOOD_BY_NAME)
        assert found is not None and found["name"] == expected

    @pytest.mark.parametrize("written", ["Unicorn Steak", "Grilled Dragon", "", None, 42])
    def test_rejects_invented_foods(self, written):
        from app.services.plan_grounding import _FOOD_BY_NAME, _lookup
        assert _lookup(written, _FOOD_BY_NAME) is None

    def test_resolves_exercise_punctuation_variant(self):
        from app.services.plan_grounding import _EXERCISE_BY_NAME, _lookup
        found = _lookup("Push Ups", _EXERCISE_BY_NAME)
        assert found is not None and found["name"] == "Push-ups"

    def test_ambiguous_exercise_is_dropped_not_guessed(self):
        """'Bench Press' could be the barbell or dumbbell variant -- don't guess."""
        from app.services.plan_grounding import _EXERCISE_BY_NAME, _lookup
        assert _lookup("Bench Press", _EXERCISE_BY_NAME) is None
