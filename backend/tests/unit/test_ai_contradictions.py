"""
Tests for the guard that stops AI interpretation from contradicting the
deterministic rule engine.

The rule engine is authoritative. If the LLM calls a flagged biomarker normal,
that statement must not reach the user, because it would appear directly
beside the rule engine's opposite finding.
"""

import pytest

from app.services.lab_interpretation_service import LabInterpretationService
from app.workers.analysis_worker import (
    _build_analysis_prompt,
    _drop_contradictions,
    _marker_aliases,
)


ABNORMAL_MARKERS = {
    "vitamin_d": 14.5,
    "vitamin_b12": 180.0,
    "ferritin": 18.0,
    "hemoglobin": 11.2,
    "fasting_glucose": 118.0,
    "total_cholesterol": 232.0,
    "triglycerides": 195.0,
    "tsh": 5.8,
    "hdl": 38.0,
}


@pytest.fixture()
def rule_result() -> dict:
    return LabInterpretationService().interpret(dict(ABNORMAL_MARKERS), "male")


class TestMarkerAliases:
    def test_includes_british_spelling(self):
        assert "haemoglobin" in _marker_aliases("hemoglobin")

    def test_includes_spaced_form(self):
        assert "vitamin b12" in _marker_aliases("vitamin_b12")


class TestDropContradictions:
    def test_drops_blanket_normal_claim(self, rule_result):
        ai = {
            "key_findings": [
                "Within normal range for hemoglobin (11.2), and HDL (38.0).",
            ]
        }
        cleaned, dropped = _drop_contradictions(ai, rule_result)
        assert cleaned["key_findings"] == []
        assert len(dropped) == 1

    def test_drops_single_marker_normal_claim(self, rule_result):
        ai = {"key_findings": ["Haemoglobin is normal at 11.2 g/dL."]}
        cleaned, dropped = _drop_contradictions(ai, rule_result)
        assert cleaned["key_findings"] == []
        assert len(dropped) == 1

    def test_keeps_correct_abnormal_statements(self, rule_result):
        ai = {
            "key_findings": [
                "Elevated total cholesterol (232.0) raises cardiovascular risk.",
                "Low hemoglobin (11.2) is consistent with anemia.",
            ]
        }
        cleaned, dropped = _drop_contradictions(ai, rule_result)
        assert len(cleaned["key_findings"]) == 2
        assert dropped == []

    def test_clears_contradicting_summary(self, rule_result):
        ai = {"summary": "The panel is unremarkable for hemoglobin and HDL."}
        cleaned, dropped = _drop_contradictions(ai, rule_result)
        assert cleaned["summary"] == ""
        assert len(dropped) == 1

    def test_does_not_touch_normal_markers(self):
        """A true 'normal' claim about an in-range marker must survive."""
        rr = LabInterpretationService().interpret(
            {"hemoglobin": 15.0, "tsh": 2.0}, "male"
        )
        ai = {"key_findings": ["Hemoglobin is within the normal range at 15.0 g/dL."]}
        cleaned, dropped = _drop_contradictions(ai, rr)
        assert len(cleaned["key_findings"]) == 1
        assert dropped == []

    def test_handles_missing_or_failed_ai_result(self, rule_result):
        for payload in ({}, {"error": "timed out"}):
            cleaned, dropped = _drop_contradictions(payload, rule_result)
            assert dropped == []

    def test_no_abnormal_markers_is_a_noop(self):
        rr = LabInterpretationService().interpret({"hemoglobin": 15.0}, "male")
        ai = {"key_findings": ["Everything is within normal range."]}
        cleaned, dropped = _drop_contradictions(ai, rr)
        assert cleaned["key_findings"] == ["Everything is within normal range."]
        assert dropped == []


class TestAnalysisPrompt:
    def test_includes_authoritative_statuses(self, rule_result):
        prompt = _build_analysis_prompt(
            ABNORMAL_MARKERS, {"age": 30, "gender": "male"}, rule_result
        )
        assert "AUTHORITATIVE" in prompt
        assert "-> LOW" in prompt
        assert "-> HIGH" in prompt
        assert "reference 13.0-17.0" in prompt

    def test_includes_rule_engine_findings(self, rule_result):
        prompt = _build_analysis_prompt(
            ABNORMAL_MARKERS, {"age": 30, "gender": "male"}, rule_result
        )
        assert "Anemia (low hemoglobin)" in prompt

    def test_works_without_rule_result(self):
        prompt = _build_analysis_prompt(ABNORMAL_MARKERS, {"age": 30})
        assert "hemoglobin" in prompt
        assert "no reference range available" in prompt
