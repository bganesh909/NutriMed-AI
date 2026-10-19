"""
Blood counts reported on different scales must be judged on one scale.

The bug this guards against: labs commonly print WBC as 7.1 (x10^3/uL) and
platelets as 250 (x10^3/uL) or 2.5 (lakhs), while the rule engine's ranges are
in cells/uL -- so healthy counts were reported as low.
"""

import pytest

from app.services.lab_interpretation_service import LabInterpretationService
from app.services.lab_units import parse_range, to_canonical


@pytest.mark.parametrize(
    ("marker", "value", "unit", "printed_range", "expected", "basis"),
    [
        # Unit printed and recognised
        ("wbc", 7.1, "10^3/uL", None, 7100, "unit"),
        ("wbc", 7.1, "x10³/µL", None, 7100, "unit"),
        ("wbc", 7.1, "x 10^9/L", None, 7100, "unit"),
        ("wbc", 7500, "cells/cumm", None, 7500, "unit"),
        ("platelets", 250, "K/uL", None, 250_000, "unit"),
        ("platelets", 2.5, "lakhs/cumm", None, 250_000, "unit"),
        ("platelets", 250_000, "/cumm", None, 250_000, "unit"),
        ("rbc", 4.8, "mill/cumm", None, 4.8, "unit"),
        ("rbc", 4.8, "x10^12/L", None, 4.8, "unit"),
        ("rbc", 4_800_000, "/cumm", None, 4.8, "unit"),
        ("hemoglobin", 11.2, "g/dL", None, 11.2, "unit"),
        ("hemoglobin", 11.2, "gm%", None, 11.2, "unit"),
        ("hemoglobin", 112, "g/L", None, 11.2, "unit"),
        # Unit printed but impossible for the value: old OCR output filled in
        # default units ("/cumm" beside 7.1), so a unit alone is not trusted.
        ("wbc", 7.1, "/cumm", None, 7100, "magnitude"),
        ("platelets", 250, "lakh/cumm", None, 250_000, "magnitude"),
        # No unit: the printed range's scale decides...
        ("platelets", 7, "", (150, 400), 7_000, "range"),  # critically low, not "7 lakhs"
        ("platelets", 7, "", (1.5, 4.5), 700_000, "range"),
        ("wbc", 7.1, "", (4.0, 11.0), 7100, "range"),
        # ...else the value's magnitude, where scales cannot overlap
        ("wbc", 7.1, "", None, 7100, "magnitude"),
        ("wbc", 7100, "", None, 7100, "magnitude"),
        ("platelets", 2.5, "", None, 250_000, "magnitude"),
        ("platelets", 250, "", None, 250_000, "magnitude"),
        ("platelets", 250_000, "", None, 250_000, "magnitude"),
        ("hemoglobin", 112, "", None, 11.2, "magnitude"),
    ],
)
def test_conversion_to_canonical_units(marker, value, unit, printed_range, expected, basis):
    conversion = to_canonical(marker, value, unit, printed_range)
    assert conversion.value == pytest.approx(expected)
    assert conversion.basis == basis


@pytest.mark.parametrize(
    ("marker", "value"),
    [
        ("platelets", 7),  # 7 lakhs (high) or 7 thousand (critically low)?
        ("wbc", 500),  # 500 cells/uL or 500 thousand?
        ("hemoglobin", 27),
    ],
)
def test_ambiguous_scale_is_reported_as_unclear(marker, value):
    conversion = to_canonical(marker, value)
    assert conversion.value is None
    assert conversion.basis == "unclear"


def test_markers_without_scales_pass_through():
    assert to_canonical("ldl", 130, "mg/dL").value == 130


def test_parse_range():
    assert parse_range("4.0 - 11.0") == (4.0, 11.0)
    assert parse_range("150 to 400") == (150, 400)
    assert parse_range("< 200") is None
    assert parse_range("11 - 4") is None
    assert parse_range("") is None


class TestRuleEngine:
    service = LabInterpretationService()

    def test_counts_in_thousands_are_normal(self):
        """The reported bug: WBC 7.1 and platelets 250 were classed as low."""
        result = self.service.interpret({"wbc": 7.1, "platelets": 250, "hemoglobin": 11.2}, "male")
        details = result["marker_details"]
        assert details["wbc"]["status"] == "normal"
        assert details["platelets"]["status"] == "normal"
        assert details["hemoglobin"]["status"] == "low"
        # Shown on the scale it was reported in, with a matching range.
        assert details["wbc"]["value"] == 7.1
        assert details["wbc"]["unit"] == "×10³/µL"
        assert details["wbc"]["range"] == "4.5-11"

    def test_canonical_values_are_unchanged(self):
        details = self.service.interpret({"wbc": 7100, "platelets": 250_000}, "female")["marker_details"]
        assert details["wbc"]["status"] == "normal"
        assert details["wbc"]["range"] == "4500-11000"
        assert details["platelets"]["status"] == "normal"

    def test_genuinely_low_counts_still_flagged(self):
        details = self.service.interpret({"wbc": 2.1, "platelets": 45}, "male")["marker_details"]
        assert details["wbc"]["status"] == "low"
        assert details["platelets"]["status"] == "low"

    def test_lab_range_decides_for_counts(self):
        reported = {"wbc": {"value": 4.2, "unit": "10^3/uL", "reference_range": "4.0 - 11.0"}}
        detail = self.service.interpret({"wbc": 4200}, "male", reported=reported)["marker_details"]["wbc"]
        # 4.2 is inside the lab's 4.0-11.0 though below the standard 4.5.
        assert detail["status"] == "normal"
        assert detail["source"] == "lab"
        assert detail["range"] == "4-11"

    def test_default_range_from_old_ocr_output_is_ignored(self):
        reported = {"wbc": {"value": 7.1, "unit": "/cumm", "reference_range": "4000 - 11000"}}
        detail = self.service.interpret({"wbc": 7.1}, "male", reported=reported)["marker_details"]["wbc"]
        assert detail["status"] == "normal"
        assert detail["source"] == "standard"

    def test_unclear_count_is_not_classified_or_used_by_rules(self):
        reported = {"platelets": {"value": 7, "unit": "", "reference_range": ""}}
        result = self.service.interpret({}, "male", reported=reported)
        detail = result["marker_details"]["platelets"]
        assert detail["status"] == "unknown"
        assert detail["range"] is None
        assert "unclear" in detail["note"].lower()
        assert "platelets" not in result["normal"]

    def test_hemoglobin_in_g_per_litre_drives_the_anemia_rule(self):
        result = self.service.interpret({"hemoglobin": 112}, "male")
        assert result["marker_details"]["hemoglobin"]["status"] == "low"
        assert result["marker_details"]["hemoglobin"]["range"] == "130-170"
        assert any(d["label"] == "Anemia (low hemoglobin)" for d in result["deficiencies"])
