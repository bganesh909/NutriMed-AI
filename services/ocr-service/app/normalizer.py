"""Text normalization for OCR output.

Fixes common OCR misreads, normalizes units and biomarker names,
and cleans up whitespace/formatting issues.
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Common OCR character substitution errors
# ---------------------------------------------------------------------------

# Map of (regex_pattern, replacement) applied in sequence
_OCR_CHAR_FIXES: list[tuple[str, str]] = [
    # Digit/letter confusion in numeric contexts
    (r"(?<=\d)[Oo](?=\d)", "0"),         # 1O5 -> 105
    (r"(?<=\d)[lI](?=\d)", "1"),         # 2l3 -> 213
    (r"(?<=\d)[S](?=\d)", "5"),          # 1S0 -> 150
    (r"(?<=\d)[B](?=\d)", "8"),          # 1B0 -> 180
    (r"(?<=\d)[Z](?=\d)", "2"),          # 1Z3 -> 123
    # Common unit misreads
    (r"\bmg/d[iI1]\b", "mg/dL"),
    (r"\bmg/d1\b", "mg/dL"),
    (r"\bg/d[iI1]\b", "g/dL"),
    (r"\bg/d1\b", "g/dL"),
    (r"\bm[iI1]U/[mM][lL1]\b", "mIU/mL"),
    (r"\bp[gG]/m[lL1]\b", "pg/mL"),
    (r"\bn[gG]/m[lL1]\b", "ng/mL"),
    (r"\bn[gG]/d[lL1]\b", "ng/dL"),
    (r"\bu[gG]/d[lL1]\b", "ug/dL"),
    (r"\bU/[lL1]\b", "U/L"),
    (r"\b[iI1]U/[lL1]\b", "IU/L"),
    (r"\bmEq/[lL1]\b", "mEq/L"),
    (r"\bmmol/[lL1]\b", "mmol/L"),
    (r"\bumol/[lL1]\b", "umol/L"),
    (r"\bm[iI1]ll?/cumm\b", "mill/cumm"),
    (r"\b/cumm\b", "/cumm"),
    (r"\bcells/cumm\b", "cells/cumm"),
    (r"\blac\b", "lakh"),
    # Fix decimal points that got turned into commas in numbers < 100
    (r"(\d{1,2}),(\d{1,2})(?!\d)", r"\1.\2"),
]

# ---------------------------------------------------------------------------
# Unit normalization
# ---------------------------------------------------------------------------

_UNIT_MAP: dict[str, str] = {
    "mg/dl": "mg/dL",
    "mg/DL": "mg/dL",
    "MG/DL": "mg/dL",
    "g/dl": "g/dL",
    "g/DL": "g/dL",
    "G/DL": "g/dL",
    "ng/ml": "ng/mL",
    "ng/ML": "ng/mL",
    "NG/ML": "ng/mL",
    "pg/ml": "pg/mL",
    "pg/ML": "pg/mL",
    "ug/dl": "ug/dL",
    "UG/DL": "ug/dL",
    "u/l": "U/L",
    "u/L": "U/L",
    "U/l": "U/L",
    "iu/l": "IU/L",
    "IU/l": "IU/L",
    "iu/L": "IU/L",
    "iu/ml": "IU/mL",
    "miu/ml": "mIU/mL",
    "MIU/ML": "mIU/mL",
    "miu/l": "mIU/L",
    "meq/l": "mEq/L",
    "MEQ/L": "mEq/L",
    "mmol/l": "mmol/L",
    "MMOL/L": "mmol/L",
    "umol/l": "umol/L",
    "UMOL/L": "umol/L",
    "fl": "fL",
    "FL": "fL",
    "Fl": "fL",
    "pg": "pg",
    "PG": "pg",
    "%": "%",
    "percent": "%",
    "thou/cumm": "thou/cumm",
    "lakhs/cumm": "lakh/cumm",
    "lacs/cumm": "lakh/cumm",
    "mill/cumm": "mill/cumm",
    "million/cumm": "mill/cumm",
    "millions/cumm": "mill/cumm",
    "cells/cumm": "cells/cumm",
    "/cumm": "/cumm",
    "x10^3/ul": "x10^3/uL",
    "x10^6/ul": "x10^6/uL",
    "10^3/ul": "x10^3/uL",
    "10^6/ul": "x10^6/uL",
}

# ---------------------------------------------------------------------------
# Biomarker name canonicalization
# ---------------------------------------------------------------------------

_BIOMARKER_NAME_MAP: dict[str, str] = {
    # CBC
    "haemoglobin": "hemoglobin",
    "hgb": "hemoglobin",
    "hb": "hemoglobin",
    "hb%": "hemoglobin",
    "total rbc count": "rbc",
    "total rbc": "rbc",
    "red blood cell count": "rbc",
    "red blood cells": "rbc",
    "r.b.c": "rbc",
    "r.b.c.": "rbc",
    "erythrocyte count": "rbc",
    "total wbc count": "wbc",
    "total wbc": "wbc",
    "white blood cell count": "wbc",
    "white blood cells": "wbc",
    "w.b.c": "wbc",
    "w.b.c.": "wbc",
    "total leucocyte count": "wbc",
    "tlc": "wbc",
    "leucocyte count": "wbc",
    "platelet count": "platelets",
    "plt": "platelets",
    "plt count": "platelets",
    "thrombocyte count": "platelets",
    "packed cell volume": "pcv",
    "hematocrit": "pcv",
    "hct": "pcv",
    "mean corpuscular volume": "mcv",
    "mean corp vol": "mcv",
    "mean corpuscular hemoglobin": "mch",
    "mean corp hb": "mch",
    "mean corp haemoglobin": "mch",
    "mean corpuscular hb conc": "mchc",
    "mean corp hb conc": "mchc",
    "mean corpuscular hemoglobin concentration": "mchc",
    # Lipid profile
    "total cholesterol": "total_cholesterol",
    "cholesterol total": "total_cholesterol",
    "cholesterol": "total_cholesterol",
    "serum cholesterol": "total_cholesterol",
    "ldl cholesterol": "ldl",
    "ldl-cholesterol": "ldl",
    "ldl-c": "ldl",
    "low density lipoprotein": "ldl",
    "hdl cholesterol": "hdl",
    "hdl-cholesterol": "hdl",
    "hdl-c": "hdl",
    "high density lipoprotein": "hdl",
    "vldl cholesterol": "vldl",
    "vldl-cholesterol": "vldl",
    "vldl-c": "vldl",
    "very low density lipoprotein": "vldl",
    "triglyceride": "triglycerides",
    "tg": "triglycerides",
    "serum triglycerides": "triglycerides",
    # LFT
    "sgpt": "alt",
    "s.g.p.t": "alt",
    "alt (sgpt)": "alt",
    "alanine aminotransferase": "alt",
    "alanine transaminase": "alt",
    "sgot": "ast",
    "s.g.o.t": "ast",
    "ast (sgot)": "ast",
    "aspartate aminotransferase": "ast",
    "aspartate transaminase": "ast",
    "alkaline phosphatase": "alp",
    "alk phosphatase": "alp",
    "alk. phosphatase": "alp",
    "total bilirubin": "total_bilirubin",
    "serum bilirubin total": "total_bilirubin",
    "bilirubin total": "total_bilirubin",
    "direct bilirubin": "direct_bilirubin",
    "bilirubin direct": "direct_bilirubin",
    "conjugated bilirubin": "direct_bilirubin",
    "indirect bilirubin": "indirect_bilirubin",
    "bilirubin indirect": "indirect_bilirubin",
    "unconjugated bilirubin": "indirect_bilirubin",
    "total protein": "total_protein",
    "serum protein total": "total_protein",
    "serum albumin": "albumin",
    "serum globulin": "globulin",
    "a/g ratio": "ag_ratio",
    "albumin/globulin ratio": "ag_ratio",
    "albumin globulin ratio": "ag_ratio",
    "gamma gt": "ggt",
    "gamma-gt": "ggt",
    "gamma glutamyl transferase": "ggt",
    "ggtp": "ggt",
    # KFT
    "blood urea nitrogen": "bun",
    "urea nitrogen": "bun",
    "serum urea": "urea",
    "blood urea": "urea",
    "serum creatinine": "creatinine",
    "creat": "creatinine",
    "uric acid": "uric_acid",
    "serum uric acid": "uric_acid",
    "estimated gfr": "egfr",
    "egfr": "egfr",
    "glomerular filtration rate": "egfr",
    "serum sodium": "sodium",
    "na+": "sodium",
    "serum potassium": "potassium",
    "k+": "potassium",
    "serum chloride": "chloride",
    "cl-": "chloride",
    "serum calcium": "calcium",
    "ca++": "calcium",
    "serum phosphorus": "phosphorus",
    "phosphate": "phosphorus",
    # Thyroid
    "tsh": "tsh",
    "thyroid stimulating hormone": "tsh",
    "serum tsh": "tsh",
    "free t3": "free_t3",
    "ft3": "free_t3",
    "free triiodothyronine": "free_t3",
    "total t3": "total_t3",
    "t3": "total_t3",
    "triiodothyronine": "total_t3",
    "free t4": "free_t4",
    "ft4": "free_t4",
    "free thyroxine": "free_t4",
    "total t4": "total_t4",
    "t4": "total_t4",
    "thyroxine": "total_t4",
    # Diabetes
    "fasting blood sugar": "fasting_glucose",
    "fasting glucose": "fasting_glucose",
    "fbs": "fasting_glucose",
    "fasting blood glucose": "fasting_glucose",
    "fasting sugar": "fasting_glucose",
    "post prandial blood sugar": "pp_glucose",
    "ppbs": "pp_glucose",
    "pp blood sugar": "pp_glucose",
    "pp sugar": "pp_glucose",
    "post prandial glucose": "pp_glucose",
    "pp glucose": "pp_glucose",
    "random blood sugar": "random_glucose",
    "rbs": "random_glucose",
    "random glucose": "random_glucose",
    "hba1c": "hba1c",
    "glycosylated hemoglobin": "hba1c",
    "glycated hemoglobin": "hba1c",
    "glycated haemoglobin": "hba1c",
    "hemoglobin a1c": "hba1c",
    "haemoglobin a1c": "hba1c",
    # Vitamins
    "vitamin d": "vitamin_d",
    "vit d": "vitamin_d",
    "25-oh vitamin d": "vitamin_d",
    "25 hydroxy vitamin d": "vitamin_d",
    "25(oh)d": "vitamin_d",
    "vitamin d total": "vitamin_d",
    "vitamin b12": "vitamin_b12",
    "vit b12": "vitamin_b12",
    "cyanocobalamin": "vitamin_b12",
    "cobalamin": "vitamin_b12",
    "folate": "folate",
    "folic acid": "folate",
    "serum folate": "folate",
    "iron": "iron",
    "serum iron": "iron",
    "ferritin": "ferritin",
    "serum ferritin": "ferritin",
    "tibc": "tibc",
    "total iron binding capacity": "tibc",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Run full normalization pipeline on OCR text."""
    text = fix_ocr_errors(text)
    text = normalize_whitespace(text)
    text = normalize_units(text)
    text = fix_decimal_points(text)
    return text


def fix_ocr_errors(text: str) -> str:
    """Apply common OCR character-substitution fixes."""
    for pattern, replacement in _OCR_CHAR_FIXES:
        text = re.sub(pattern, replacement, text)
    return text


def normalize_units(text: str) -> str:
    """Normalize unit strings to canonical forms."""
    for variant, canonical in _UNIT_MAP.items():
        # Use word-boundary-aware replacement
        pattern = re.escape(variant)
        text = re.sub(rf"\b{pattern}\b", canonical, text, flags=re.IGNORECASE)
    return text


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/tabs to single space, strip lines."""
    # Replace tabs with spaces
    text = text.replace("\t", "  ")
    # Collapse multiple spaces (but keep newlines)
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        line = re.sub(r" {2,}", "  ", line)  # Keep double-space as column separator
        line = line.strip()
        if line:
            cleaned.append(line)
    return "\n".join(cleaned)


def fix_decimal_points(text: str) -> str:
    """Fix common decimal point issues in numeric values.

    Handles cases like '12 .5' -> '12.5', '12. 5' -> '12.5'.
    """
    # Fix space before decimal: "12 .5" -> "12.5"
    text = re.sub(r"(\d)\s+\.(\d)", r"\1.\2", text)
    # Fix space after decimal: "12. 5" -> "12.5"
    text = re.sub(r"(\d)\.\s+(\d)", r"\1.\2", text)
    return text


def canonicalize_biomarker_name(name: str) -> str:
    """Map a biomarker name (possibly OCR-mangled) to its canonical form."""
    key = name.strip().lower()
    # Direct lookup
    if key in _BIOMARKER_NAME_MAP:
        return _BIOMARKER_NAME_MAP[key]
    # Try removing extra whitespace
    compressed = re.sub(r"\s+", " ", key)
    if compressed in _BIOMARKER_NAME_MAP:
        return _BIOMARKER_NAME_MAP[compressed]
    # Try removing dots
    no_dots = key.replace(".", "")
    if no_dots in _BIOMARKER_NAME_MAP:
        return _BIOMARKER_NAME_MAP[no_dots]
    return key
