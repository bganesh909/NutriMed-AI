"""
Unit tests for app.services.lab_interpretation_service.

Tests reference range checking, clinical rule evaluation for:
anemia, vitamin D deficiency, diabetic risk, cholesterol, thyroid, and
combined risk scenarios.
"""

import pytest

from app.services.lab_interpretation_service import (
    LabInterpretationService,
    REFERENCE_RANGES,
)


@pytest.fixture()
def lab_service():
    return LabInterpretationService()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _find_label(results: dict, label_fragment: str, category: str) -> bool:
    """Check if any finding in the given category contains the label fragment."""
    for item in results.get(category, []):
        if label_fragment.lower() in item["label"].lower():
            return True
    return False


# ---------------------------------------------------------------------------
# Reference range checks -- normal values
# ---------------------------------------------------------------------------


class TestNormalValues:
    def test_all_normal_markers(self, lab_service):
        markers = {
            "hemoglobin": 15.0,
            "vitamin_d": 50.0,
            "vitamin_b12": 500.0,
            "ldl": 90.0,
            "hdl": 55.0,
            "triglycerides": 120.0,
            "fasting_sugar": 85.0,
            "hba1c": 5.2,
            "tsh": 2.5,
            "iron": 100.0,
            "calcium": 9.5,
            "creatinine": 1.0,
        }
        result = lab_service.interpret(markers, "male")
        assert len(result["deficiencies"]) == 0
        assert len(result["risk_factors"]) == 0
        assert len(result["warnings"]) == 0
        assert len(result["normal"]) > 0

    def test_marker_details_populated(self, lab_service):
        result = lab_service.interpret({"hemoglobin": 14.5}, "male")
        assert "hemoglobin" in result["marker_details"]
        detail = result["marker_details"]["hemoglobin"]
        assert detail["value"] == 14.5
        assert detail["status"] == "normal"
        assert detail["unit"] == "g/dL"

    def test_unknown_marker_recorded(self, lab_service):
        result = lab_service.interpret({"unknown_marker": 42.0}, "male")
        assert "unknown_marker" in result["marker_details"]
        assert result["marker_details"]["unknown_marker"]["status"] == "unknown"


# ---------------------------------------------------------------------------
# Anemia detection
# ---------------------------------------------------------------------------


class TestAnemiaDetection:
    def test_male_anemia(self, lab_service):
        result = lab_service.interpret({"hemoglobin": 11.5}, "male")
        assert _find_label(result, "anemia", "deficiencies")

    def test_female_anemia(self, lab_service):
        result = lab_service.interpret({"hemoglobin": 10.5}, "female")
        assert _find_label(result, "anemia", "deficiencies")

    def test_female_normal_hemoglobin(self, lab_service):
        result = lab_service.interpret({"hemoglobin": 13.0}, "female")
        assert not _find_label(result, "anemia", "deficiencies")

    def test_male_normal_hemoglobin(self, lab_service):
        result = lab_service.interpret({"hemoglobin": 14.5}, "male")
        assert not _find_label(result, "anemia", "deficiencies")

    def test_elevated_hemoglobin_warning(self, lab_service):
        result = lab_service.interpret({"hemoglobin": 18.0}, "male")
        assert _find_label(result, "elevated hemoglobin", "warnings")

    def test_female_elevated_hemoglobin(self, lab_service):
        result = lab_service.interpret({"hemoglobin": 16.0}, "female")
        assert _find_label(result, "elevated hemoglobin", "warnings")


# ---------------------------------------------------------------------------
# Vitamin D deficiency
# ---------------------------------------------------------------------------


class TestVitaminDDeficiency:
    def test_severe_deficiency(self, lab_service):
        result = lab_service.interpret({"vitamin_d": 12.0}, "male")
        assert _find_label(result, "vitamin d deficiency", "deficiencies")

    def test_insufficiency(self, lab_service):
        result = lab_service.interpret({"vitamin_d": 25.0}, "male")
        assert _find_label(result, "vitamin d insufficiency", "deficiencies")

    def test_normal_vitamin_d(self, lab_service):
        result = lab_service.interpret({"vitamin_d": 50.0}, "male")
        assert not _find_label(result, "vitamin d", "deficiencies")

    def test_vitamin_b12_deficiency(self, lab_service):
        result = lab_service.interpret({"vitamin_b12": 150.0}, "female")
        assert _find_label(result, "vitamin b12 deficiency", "deficiencies")


# ---------------------------------------------------------------------------
# Diabetic risk
# ---------------------------------------------------------------------------


class TestDiabeticRisk:
    def test_diabetic_fasting_sugar(self, lab_service):
        result = lab_service.interpret({"fasting_sugar": 140.0}, "male")
        assert _find_label(result, "diabetic-range fasting glucose", "risk_factors")

    def test_prediabetic_fasting_sugar(self, lab_service):
        result = lab_service.interpret({"fasting_sugar": 110.0}, "male")
        assert _find_label(result, "pre-diabetic fasting glucose", "warnings")

    def test_normal_fasting_sugar(self, lab_service):
        result = lab_service.interpret({"fasting_sugar": 85.0}, "male")
        assert not _find_label(result, "fasting glucose", "risk_factors")
        assert not _find_label(result, "fasting glucose", "warnings")

    def test_diabetic_hba1c(self, lab_service):
        result = lab_service.interpret({"hba1c": 7.2}, "female")
        assert _find_label(result, "diabetic-range hba1c", "risk_factors")

    def test_prediabetic_hba1c(self, lab_service):
        result = lab_service.interpret({"hba1c": 6.0}, "female")
        assert _find_label(result, "pre-diabetic hba1c", "warnings")

    def test_normal_hba1c(self, lab_service):
        result = lab_service.interpret({"hba1c": 5.0}, "male")
        assert not _find_label(result, "hba1c", "risk_factors")
        assert not _find_label(result, "hba1c", "warnings")


# ---------------------------------------------------------------------------
# Cholesterol
# ---------------------------------------------------------------------------


class TestCholesterol:
    def test_high_ldl(self, lab_service):
        result = lab_service.interpret({"ldl": 150.0}, "male")
        assert _find_label(result, "high ldl", "risk_factors")

    def test_borderline_ldl(self, lab_service):
        result = lab_service.interpret({"ldl": 115.0}, "male")
        assert _find_label(result, "borderline high ldl", "warnings")

    def test_normal_ldl(self, lab_service):
        result = lab_service.interpret({"ldl": 80.0}, "male")
        assert not _find_label(result, "ldl", "risk_factors")
        assert not _find_label(result, "ldl", "warnings")

    def test_low_hdl_male(self, lab_service):
        result = lab_service.interpret({"hdl": 35.0}, "male")
        assert _find_label(result, "low hdl", "risk_factors")

    def test_low_hdl_female(self, lab_service):
        result = lab_service.interpret({"hdl": 45.0}, "female")
        assert _find_label(result, "low hdl", "risk_factors")

    def test_high_triglycerides(self, lab_service):
        result = lab_service.interpret({"triglycerides": 250.0}, "male")
        assert _find_label(result, "high triglycerides", "risk_factors")

    def test_borderline_triglycerides(self, lab_service):
        result = lab_service.interpret({"triglycerides": 175.0}, "male")
        assert _find_label(result, "borderline high triglycerides", "warnings")


# ---------------------------------------------------------------------------
# Thyroid
# ---------------------------------------------------------------------------


class TestThyroid:
    def test_hypothyroid_risk(self, lab_service):
        result = lab_service.interpret({"tsh": 6.0}, "female")
        assert _find_label(result, "hypothyroid", "risk_factors")

    def test_hyperthyroid_risk(self, lab_service):
        result = lab_service.interpret({"tsh": 0.2}, "female")
        assert _find_label(result, "hyperthyroid", "risk_factors")

    def test_normal_tsh(self, lab_service):
        result = lab_service.interpret({"tsh": 2.0}, "male")
        assert not _find_label(result, "thyroid", "risk_factors")


# ---------------------------------------------------------------------------
# Other markers
# ---------------------------------------------------------------------------


class TestOtherMarkers:
    def test_iron_deficiency_male(self, lab_service):
        result = lab_service.interpret({"iron": 50.0}, "male")
        assert _find_label(result, "iron deficiency", "deficiencies")

    def test_iron_deficiency_female(self, lab_service):
        result = lab_service.interpret({"iron": 40.0}, "female")
        assert _find_label(result, "iron deficiency", "deficiencies")

    def test_low_calcium(self, lab_service):
        result = lab_service.interpret({"calcium": 7.5}, "male")
        assert _find_label(result, "low calcium", "deficiencies")

    def test_elevated_creatinine_male(self, lab_service):
        result = lab_service.interpret({"creatinine": 1.5}, "male")
        assert _find_label(result, "elevated creatinine", "risk_factors")

    def test_elevated_creatinine_female(self, lab_service):
        result = lab_service.interpret({"creatinine": 1.3}, "female")
        assert _find_label(result, "elevated creatinine", "risk_factors")

    def test_elevated_sgpt(self, lab_service):
        result = lab_service.interpret({"sgpt": 80.0}, "male")
        assert _find_label(result, "elevated sgpt", "risk_factors")

    def test_elevated_sgot(self, lab_service):
        result = lab_service.interpret({"sgot": 55.0}, "male")
        assert _find_label(result, "elevated sgot", "risk_factors")

    def test_elevated_uric_acid_male(self, lab_service):
        result = lab_service.interpret({"uric_acid": 8.0}, "male")
        assert _find_label(result, "elevated uric acid", "risk_factors")

    def test_low_ferritin(self, lab_service):
        result = lab_service.interpret({"ferritin": 10.0}, "male")
        assert _find_label(result, "low ferritin", "deficiencies")

    def test_low_magnesium(self, lab_service):
        result = lab_service.interpret({"magnesium": 1.3}, "male")
        assert _find_label(result, "low magnesium", "deficiencies")

    def test_low_potassium(self, lab_service):
        result = lab_service.interpret({"potassium": 3.0}, "male")
        assert _find_label(result, "low potassium", "warnings")

    def test_high_potassium(self, lab_service):
        result = lab_service.interpret({"potassium": 5.5}, "male")
        assert _find_label(result, "high potassium", "warnings")


# ---------------------------------------------------------------------------
# Combined risk scenarios
# ---------------------------------------------------------------------------


class TestCombinedRisks:
    def test_metabolic_syndrome_profile(self, lab_service):
        """Patient with high sugar + high lipids + high BP markers."""
        markers = {
            "fasting_sugar": 130.0,
            "hba1c": 6.8,
            "triglycerides": 220.0,
            "hdl": 35.0,
            "ldl": 160.0,
        }
        result = lab_service.interpret(markers, "male")
        assert len(result["risk_factors"]) >= 4
        assert _find_label(result, "diabetic", "risk_factors")
        assert _find_label(result, "high ldl", "risk_factors")
        assert _find_label(result, "high triglycerides", "risk_factors")
        assert _find_label(result, "low hdl", "risk_factors")

    def test_anemia_with_iron_deficiency(self, lab_service):
        markers = {
            "hemoglobin": 10.0,
            "iron": 40.0,
            "ferritin": 8.0,
        }
        result = lab_service.interpret(markers, "female")
        assert _find_label(result, "anemia", "deficiencies")
        assert _find_label(result, "iron deficiency", "deficiencies")
        assert _find_label(result, "low ferritin", "deficiencies")

    def test_multiple_vitamin_deficiencies(self, lab_service):
        markers = {
            "vitamin_d": 15.0,
            "vitamin_b12": 180.0,
            "folate": 2.0,
        }
        result = lab_service.interpret(markers, "male")
        assert len(result["deficiencies"]) >= 3

    def test_liver_stress_profile(self, lab_service):
        markers = {
            "sgpt": 90.0,
            "sgot": 65.0,
        }
        result = lab_service.interpret(markers, "male")
        assert _find_label(result, "elevated sgpt", "risk_factors")
        assert _find_label(result, "elevated sgot", "risk_factors")

    def test_gender_affects_ranges(self, lab_service):
        """Same values interpreted differently by gender."""
        markers = {"hemoglobin": 12.5, "hdl": 42.0}

        male_result = lab_service.interpret(markers, "male")
        female_result = lab_service.interpret(markers, "female")

        # 12.5 hemoglobin: anemia for male (< 13), normal for female (>= 12)
        assert _find_label(male_result, "anemia", "deficiencies")
        assert not _find_label(female_result, "anemia", "deficiencies")

    def test_default_gender_is_male(self, lab_service):
        result = lab_service.interpret({"hemoglobin": 14.0}, None)
        assert "hemoglobin" in result["marker_details"]
        assert result["marker_details"]["hemoglobin"]["status"] == "normal"

    def test_invalid_gender_defaults_to_male(self, lab_service):
        result = lab_service.interpret({"hemoglobin": 14.0}, "other")
        assert result["marker_details"]["hemoglobin"]["status"] == "normal"
