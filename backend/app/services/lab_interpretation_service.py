"""
Deterministic rule engine for interpreting lab biomarker results.

Each biomarker has defined reference ranges (gender-specific where applicable).
The engine produces deficiencies, risk_factors, and warnings.
"""

from typing import Optional


REFERENCE_RANGES: dict[str, dict] = {
    "hemoglobin": {
        "male": (13.0, 17.0),
        "female": (12.0, 15.5),
        "unit": "g/dL",
    },
    "vitamin_d": {
        "general": (30, 100),
        "unit": "ng/mL",
    },
    "vitamin_b12": {
        "general": (200, 900),
        "unit": "pg/mL",
    },
    "ldl": {
        "general": (0, 100),
        "optimal": (0, 70),
        "unit": "mg/dL",
    },
    "hdl": {
        "male": (40, 60),
        "female": (50, 60),
        "unit": "mg/dL",
    },
    "triglycerides": {
        "general": (0, 150),
        "borderline": (150, 199),
        "unit": "mg/dL",
    },
    "fasting_sugar": {
        "general": (70, 100),
        "prediabetic": (100, 125),
        "unit": "mg/dL",
    },
    "hba1c": {
        "general": (4.0, 5.7),
        "prediabetic": (5.7, 6.4),
        "unit": "%",
    },
    "tsh": {
        "general": (0.4, 4.0),
        "unit": "mIU/L",
    },
    "iron": {
        "male": (65, 175),
        "female": (50, 170),
        "unit": "mcg/dL",
    },
    "calcium": {
        "general": (8.5, 10.5),
        "unit": "mg/dL",
    },
    "creatinine": {
        "male": (0.7, 1.3),
        "female": (0.6, 1.1),
        "unit": "mg/dL",
    },
    "urea": {
        "general": (7, 20),
        "unit": "mg/dL",
    },
    "uric_acid": {
        "male": (3.4, 7.0),
        "female": (2.4, 6.0),
        "unit": "mg/dL",
    },
    "sgpt": {
        "general": (7, 56),
        "unit": "U/L",
    },
    "sgot": {
        "general": (10, 40),
        "unit": "U/L",
    },
    "total_cholesterol": {
        "general": (0, 200),
        "borderline": (200, 239),
        "unit": "mg/dL",
    },
    "rbc": {
        "male": (4.7, 6.1),
        "female": (4.2, 5.4),
        "unit": "million/mcL",
    },
    "wbc": {
        "general": (4500, 11000),
        "unit": "cells/mcL",
    },
    "platelets": {
        "general": (150000, 400000),
        "unit": "cells/mcL",
    },
    "ferritin": {
        "male": (20, 500),
        "female": (20, 200),
        "unit": "ng/mL",
    },
    "folate": {
        "general": (2.7, 17.0),
        "unit": "ng/mL",
    },
    "magnesium": {
        "general": (1.7, 2.2),
        "unit": "mg/dL",
    },
    "zinc": {
        "general": (60, 120),
        "unit": "mcg/dL",
    },
    "potassium": {
        "general": (3.5, 5.0),
        "unit": "mEq/L",
    },
    "sodium": {
        "general": (136, 145),
        "unit": "mEq/L",
    },
    "albumin": {
        "general": (3.5, 5.5),
        "unit": "g/dL",
    },
    "bilirubin_total": {
        "general": (0.1, 1.2),
        "unit": "mg/dL",
    },
    "alkaline_phosphatase": {
        "general": (44, 147),
        "unit": "U/L",
    },
    "testosterone": {
        "male": (300, 1000),
        "female": (15, 70),
        "unit": "ng/dL",
    },
    "cortisol": {
        "general": (6, 23),
        "unit": "mcg/dL",
    },
}

# ---- Specific clinical rules that go beyond simple range checks ----

_CLINICAL_RULES: list[dict] = [
    {
        "marker": "hemoglobin",
        "condition": lambda val, gender: val < (12.0 if gender == "female" else 13.0),
        "category": "deficiency",
        "label": "Anemia (low hemoglobin)",
        "detail": "Hemoglobin is below the normal threshold. Consider iron-rich foods and further evaluation.",
    },
    {
        "marker": "hemoglobin",
        "condition": lambda val, gender: val > (15.5 if gender == "female" else 17.0),
        "category": "warning",
        "label": "Elevated hemoglobin",
        "detail": "High hemoglobin may indicate dehydration or polycythemia. Consult a physician.",
    },
    {
        "marker": "vitamin_d",
        "condition": lambda val, _: val < 20,
        "category": "deficiency",
        "label": "Vitamin D deficiency",
        "detail": "Severe vitamin D deficiency (<20 ng/mL). Sun exposure, supplementation, and vitamin D-rich foods recommended.",
    },
    {
        "marker": "vitamin_d",
        "condition": lambda val, _: 20 <= val < 30,
        "category": "deficiency",
        "label": "Vitamin D insufficiency",
        "detail": "Vitamin D is suboptimal (20-30 ng/mL). Consider supplementation with 1000-2000 IU daily.",
    },
    {
        "marker": "vitamin_b12",
        "condition": lambda val, _: val < 200,
        "category": "deficiency",
        "label": "Vitamin B12 deficiency",
        "detail": "Low B12 can cause fatigue, neurological issues. Consider supplementation or dietary adjustments.",
    },
    {
        "marker": "ldl",
        "condition": lambda val, _: val > 130,
        "category": "risk_factor",
        "label": "High LDL cholesterol",
        "detail": "LDL >130 mg/dL increases cardiovascular risk. Dietary changes, exercise, and medical review advised.",
    },
    {
        "marker": "ldl",
        "condition": lambda val, _: 100 < val <= 130,
        "category": "warning",
        "label": "Borderline high LDL",
        "detail": "LDL is above optimal. Consider reducing saturated fats and increasing fiber intake.",
    },
    {
        "marker": "hdl",
        "condition": lambda val, gender: val < (50 if gender == "female" else 40),
        "category": "risk_factor",
        "label": "Low HDL cholesterol",
        "detail": "Low HDL increases cardiovascular risk. Exercise, omega-3 fatty acids, and healthy fats can help.",
    },
    {
        "marker": "triglycerides",
        "condition": lambda val, _: val > 200,
        "category": "risk_factor",
        "label": "High triglycerides",
        "detail": "Triglycerides >200 mg/dL. Reduce sugar, refined carbs, and alcohol. Increase omega-3 intake.",
    },
    {
        "marker": "triglycerides",
        "condition": lambda val, _: 150 < val <= 200,
        "category": "warning",
        "label": "Borderline high triglycerides",
        "detail": "Triglycerides slightly elevated. Monitor diet and consider reducing refined carbohydrates.",
    },
    {
        "marker": "fasting_sugar",
        "condition": lambda val, _: val > 125,
        "category": "risk_factor",
        "label": "Diabetic-range fasting glucose",
        "detail": "Fasting glucose >125 mg/dL suggests diabetes. Urgent medical evaluation recommended.",
    },
    {
        "marker": "fasting_sugar",
        "condition": lambda val, _: 100 <= val <= 125,
        "category": "warning",
        "label": "Pre-diabetic fasting glucose",
        "detail": "Fasting glucose 100-125 mg/dL indicates pre-diabetes. Lifestyle modifications recommended.",
    },
    {
        "marker": "hba1c",
        "condition": lambda val, _: val >= 6.5,
        "category": "risk_factor",
        "label": "Diabetic-range HbA1c",
        "detail": "HbA1c >= 6.5% indicates diabetes. Medical consultation and glucose management needed.",
    },
    {
        "marker": "hba1c",
        "condition": lambda val, _: 5.7 <= val < 6.5,
        "category": "warning",
        "label": "Pre-diabetic HbA1c",
        "detail": "HbA1c 5.7-6.4% indicates pre-diabetes. Diet, exercise, and monitoring recommended.",
    },
    {
        "marker": "tsh",
        "condition": lambda val, _: val > 4.5,
        "category": "risk_factor",
        "label": "Hypothyroid risk (elevated TSH)",
        "detail": "TSH >4.5 mIU/L suggests hypothyroidism. Thyroid panel and endocrine evaluation advised.",
    },
    {
        "marker": "tsh",
        "condition": lambda val, _: val < 0.4,
        "category": "risk_factor",
        "label": "Hyperthyroid risk (suppressed TSH)",
        "detail": "TSH <0.4 mIU/L suggests hyperthyroidism. Further thyroid evaluation needed.",
    },
    {
        "marker": "iron",
        "condition": lambda val, gender: val < (50 if gender == "female" else 65),
        "category": "deficiency",
        "label": "Iron deficiency",
        "detail": "Low serum iron. Consider iron-rich foods (spinach, red meat, lentils) and supplementation.",
    },
    {
        "marker": "calcium",
        "condition": lambda val, _: val < 8.5,
        "category": "deficiency",
        "label": "Low calcium",
        "detail": "Calcium below normal. Increase dairy, leafy greens, or consider supplementation.",
    },
    {
        "marker": "creatinine",
        "condition": lambda val, gender: val > (1.1 if gender == "female" else 1.3),
        "category": "risk_factor",
        "label": "Elevated creatinine (kidney stress)",
        "detail": "High creatinine may indicate impaired kidney function. Medical review recommended.",
    },
    {
        "marker": "sgpt",
        "condition": lambda val, _: val > 56,
        "category": "risk_factor",
        "label": "Elevated SGPT (liver stress)",
        "detail": "High SGPT/ALT may indicate liver inflammation. Reduce alcohol, processed foods; consult physician.",
    },
    {
        "marker": "sgot",
        "condition": lambda val, _: val > 40,
        "category": "risk_factor",
        "label": "Elevated SGOT (liver/muscle stress)",
        "detail": "High SGOT/AST may indicate liver or muscle damage. Further evaluation recommended.",
    },
    {
        "marker": "uric_acid",
        "condition": lambda val, gender: val > (6.0 if gender == "female" else 7.0),
        "category": "risk_factor",
        "label": "Elevated uric acid (gout risk)",
        "detail": "High uric acid can cause gout. Reduce purine-rich foods (red meat, shellfish), increase hydration.",
    },
    {
        "marker": "ferritin",
        "condition": lambda val, _: val < 20,
        "category": "deficiency",
        "label": "Low ferritin (depleted iron stores)",
        "detail": "Low ferritin even with normal hemoglobin suggests depleted iron stores. Supplementation advised.",
    },
    {
        "marker": "folate",
        "condition": lambda val, _: val < 2.7,
        "category": "deficiency",
        "label": "Folate deficiency",
        "detail": "Low folate can cause megaloblastic anemia. Increase leafy greens, legumes, or supplement with folic acid.",
    },
    {
        "marker": "magnesium",
        "condition": lambda val, _: val < 1.7,
        "category": "deficiency",
        "label": "Low magnesium",
        "detail": "Low magnesium may cause muscle cramps, fatigue. Consider nuts, seeds, whole grains, or supplementation.",
    },
    {
        "marker": "potassium",
        "condition": lambda val, _: val < 3.5,
        "category": "warning",
        "label": "Low potassium (hypokalemia)",
        "detail": "Low potassium can cause weakness, cramps. Increase bananas, potatoes, avocados.",
    },
    {
        "marker": "potassium",
        "condition": lambda val, _: val > 5.0,
        "category": "warning",
        "label": "High potassium (hyperkalemia)",
        "detail": "Elevated potassium may affect heart rhythm. Medical evaluation recommended.",
    },
]


class LabInterpretationService:
    """
    Stateless deterministic rule engine for interpreting biomarker values.
    No database dependency -- operates purely on input data.
    """

    def interpret(
        self,
        markers: dict[str, float],
        gender: Optional[str] = None,
    ) -> dict:
        """
        Interpret biomarker values and return structured findings.

        Returns:
            {
                "deficiencies": [...],
                "risk_factors": [...],
                "warnings": [...],
                "normal": [...],
                "marker_details": {marker: {value, unit, status, range}}
            }
        """
        gender = (gender or "male").lower()
        if gender not in ("male", "female"):
            gender = "male"

        deficiencies: list[dict] = []
        risk_factors: list[dict] = []
        warnings: list[dict] = []
        normal: list[str] = []
        marker_details: dict[str, dict] = {}

        for marker, value in markers.items():
            ref = REFERENCE_RANGES.get(marker)
            if ref is None:
                # Unknown marker -- skip rule checks, still record it
                marker_details[marker] = {
                    "value": value,
                    "unit": "unknown",
                    "status": "unknown",
                    "range": None,
                }
                continue

            # Determine reference range
            if gender in ref:
                low, high = ref[gender]
            elif "general" in ref:
                low, high = ref["general"]
            else:
                low, high = 0, float("inf")

            unit = ref.get("unit", "")

            if value < low:
                range_status = "low"
            elif value > high:
                range_status = "high"
            else:
                range_status = "normal"

            marker_details[marker] = {
                "value": value,
                "unit": unit,
                "status": range_status,
                "range": f"{low}-{high}",
            }

            if range_status == "normal":
                normal.append(marker)

        # Apply clinical rules
        triggered_labels: set[str] = set()
        for rule in _CLINICAL_RULES:
            marker_name = rule["marker"]
            if marker_name not in markers:
                continue
            value = markers[marker_name]
            if rule["condition"](value, gender):
                label = rule["label"]
                if label in triggered_labels:
                    continue
                triggered_labels.add(label)

                finding = {
                    "marker": marker_name,
                    "value": markers[marker_name],
                    "label": label,
                    "detail": rule["detail"],
                }
                cat = rule["category"]
                if cat == "deficiency":
                    deficiencies.append(finding)
                elif cat == "risk_factor":
                    risk_factors.append(finding)
                elif cat == "warning":
                    warnings.append(finding)

        return {
            "deficiencies": deficiencies,
            "risk_factors": risk_factors,
            "warnings": warnings,
            "normal": normal,
            "marker_details": marker_details,
        }
