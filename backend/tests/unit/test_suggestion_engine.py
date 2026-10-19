"""
Tests for the suggestion engine.

Suggestions -- not full plans -- are the product's default output. They must
work with a lab report, without one, and from self-reported conditions, and
they must never invent a food or exercise.
"""

import pytest

from app.data.exercise_database import EXERCISE_DATABASE
from app.data.food_database import FOOD_DATABASE
from app.services.lab_interpretation_service import LabInterpretationService
from app.services.suggestion_engine import build_suggestions

FOOD_NAMES = {f["name"] for f in FOOD_DATABASE}
EXERCISE_NAMES = {e["name"] for e in EXERCISE_DATABASE}

PROFILE = {
    "age": 30, "gender": "male", "weight": 75, "height": 175,
    "activity_level": "moderately_active",
}

ABNORMAL = {
    "vitamin_d": 14.5, "vitamin_b12": 180.0, "ferritin": 18.0, "hemoglobin": 11.2,
    "fasting_glucose": 118.0, "total_cholesterol": 232.0, "triglycerides": 195.0,
    "tsh": 5.8, "hdl": 38.0,
}


@pytest.fixture()
def labs() -> dict:
    return LabInterpretationService().interpret(dict(ABNORMAL), "male")


def _all_examples(suggestions: dict) -> tuple[list[str], list[str]]:
    foods = [x for e in suggestions["nutrition"]["emphasise"] for x in e.get("examples", [])]
    exercises = [x for t in suggestions["training"]["focus"] for x in t.get("examples", [])]
    return foods, exercises


class TestNeverInventsItems:
    """The whole point of the curated databases."""

    def test_lab_driven_examples_are_all_real(self, labs):
        foods, exercises = _all_examples(build_suggestions(user=PROFILE, rule_engine=labs, goal="fat_loss"))
        assert foods
        assert all(f in FOOD_NAMES for f in foods)
        assert all(e in EXERCISE_NAMES for e in exercises)

    @pytest.mark.parametrize("goal", [
        "fat_loss", "muscle_gain", "weight_gain", "recomposition",
        "endurance", "strength", "maintenance",
    ])
    def test_every_goal_produces_only_real_items(self, goal):
        foods, exercises = _all_examples(build_suggestions(user=PROFILE, goal=goal))
        assert all(f in FOOD_NAMES for f in foods)
        assert all(e in EXERCISE_NAMES for e in exercises)


class TestWithLabReport:
    def test_flags_source_as_labs(self, labs):
        s = build_suggestions(user=PROFILE, rule_engine=labs, goal="fat_loss")
        assert s["based_on"] == "labs+profile"
        assert any(e["source"] == "labs" for e in s["nutrition"]["emphasise"])

    def test_low_haemoglobin_caps_intensity(self, labs):
        s = build_suggestions(user=PROFILE, rule_engine=labs, goal="fat_loss")
        assert s["training"]["intensity_capped"] is True

    def test_high_glucose_emphasises_cardio(self, labs):
        s = build_suggestions(user=PROFILE, rule_engine=labs, goal="fat_loss")
        assert s["training"]["cardio_emphasised"] is True

    def test_merges_lipid_findings_into_one_entry(self, labs):
        """High cholesterol, high triglycerides and low HDL are one action."""
        s = build_suggestions(user=PROFILE, rule_engine=labs, goal="fat_loss")
        lipid = [e for e in s["nutrition"]["emphasise"] if "Omega-3" in e["label"]]
        assert len(lipid) == 1
        assert len(lipid[0]["why"]) >= 3

    def test_does_not_return_a_full_plan(self, labs):
        s = build_suggestions(user=PROFILE, rule_engine=labs, goal="fat_loss")
        assert "meal_plan" not in s
        assert "days" not in s
        assert s["available_on_request"] == ["full_diet_plan", "full_workout_plan"]


class TestWithoutLabReport:
    def test_works_from_profile_and_goal_alone(self):
        s = build_suggestions(user=PROFILE, goal="muscle_gain")
        assert s["based_on"] == "profile"
        assert s["nutrition"]["emphasise"]
        assert s["training"]["focus"]

    def test_asks_for_a_lab_report_and_conditions(self):
        s = build_suggestions(user=PROFILE, goal="muscle_gain")
        assert any("lab report" in m for m in s["missing_info"])
        assert any("health conditions" in m for m in s["missing_info"])

    def test_stops_asking_once_conditions_are_given(self):
        s = build_suggestions(user=PROFILE, goal="muscle_gain", conditions=["diabetes"])
        assert not any("health conditions" in m for m in s["missing_info"])

    def test_names_missing_profile_fields(self):
        s = build_suggestions(user={"age": 30}, goal="fat_loss")
        assert "current weight" in s["missing_info"]
        assert "height" in s["missing_info"]

    def test_goals_produce_different_calorie_targets(self):
        targets = {
            goal: build_suggestions(user=PROFILE, goal=goal)["nutrition"]["daily_target_calories"]
            for goal in ("fat_loss", "muscle_gain", "weight_gain", "maintenance")
        }
        assert targets["fat_loss"] < targets["maintenance"] < targets["muscle_gain"] < targets["weight_gain"]


class TestSelfReportedConditions:
    def test_diabetes_drives_glycaemic_advice(self):
        s = build_suggestions(user=PROFILE, goal="fat_loss", conditions=["diabetes"])
        assert any("glycaemic" in e["label"].lower() for e in s["nutrition"]["emphasise"])
        assert any(e["source"] == "reported" for e in s["nutrition"]["emphasise"])

    def test_free_text_condition_is_matched_loosely(self):
        s = build_suggestions(user=PROFILE, goal="fat_loss", conditions=["Type 2 Diabetes"])
        assert any(e["source"] == "reported" for e in s["nutrition"]["emphasise"])

    def test_thyroid_caps_intensity(self):
        s = build_suggestions(user=PROFILE, goal="strength", conditions=["thyroid"])
        assert s["training"]["intensity_capped"] is True

    def test_knee_injury_adds_low_impact_advice(self):
        s = build_suggestions(user=PROFILE, goal="fat_loss", conditions=["knee injury"])
        assert any("low-impact" in t["label"].lower() for t in s["training"]["focus"])

    def test_unknown_condition_is_ignored_safely(self):
        s = build_suggestions(user=PROFILE, goal="fat_loss", conditions=["zzzz unknown"])
        assert s["nutrition"]["emphasise"]


class TestDietaryPreferenceAndAllergies:
    def test_vegan_examples_are_all_vegan(self, labs):
        s = build_suggestions(user=PROFILE, rule_engine=labs, goal="fat_loss", dietary_preference="vegan")
        by_name = {f["name"]: f for f in FOOD_DATABASE}
        foods, _ = _all_examples(s)
        assert all("vegan" in by_name[f]["tags"] for f in foods)

    def test_allergy_excludes_matching_foods(self, labs):
        s = build_suggestions(user=PROFILE, rule_engine=labs, goal="fat_loss", allergies=["fish"])
        by_name = {f["name"]: f for f in FOOD_DATABASE}
        foods, _ = _all_examples(s)
        assert all("fish" not in by_name[f]["tags"] for f in foods)


class TestShape:
    def test_every_entry_has_a_label_and_reasons(self, labs):
        s = build_suggestions(user=PROFILE, rule_engine=labs, goal="fat_loss")
        for group in (s["nutrition"]["emphasise"], s["nutrition"]["limit"], s["training"]["focus"]):
            for entry in group:
                assert entry["label"]
                assert isinstance(entry["why"], list) and entry["why"]
                assert entry["source"] in ("labs", "goal", "reported")

    def test_handles_a_completely_empty_request(self):
        s = build_suggestions()
        assert s["goal"] == "maintenance"
        assert s["nutrition"]["daily_target_calories"] >= 1200
        assert s["missing_info"]
