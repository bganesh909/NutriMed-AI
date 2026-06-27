"""Specialized parsers for specific lab report types.

Each parser class knows the expected markers, their regex patterns,
typical units, and reference ranges for Indian lab report formats.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.medical_parser import ParsedBiomarker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reference range definitions (typical Indian adult ranges)
# ---------------------------------------------------------------------------

@dataclass
class ReferenceInfo:
    """Default reference range and unit for a biomarker."""
    unit: str
    low: Optional[float] = None
    high: Optional[float] = None

    @property
    def range_str(self) -> str:
        if self.low is not None and self.high is not None:
            return f"{self.low} - {self.high}"
        if self.low is not None:
            return f"> {self.low}"
        if self.high is not None:
            return f"< {self.high}"
        return ""


def _evaluate_status(value: Optional[float], ref: ReferenceInfo) -> str:
    """Determine if a value is normal, low, or high relative to reference."""
    if value is None:
        return "unknown"
    if ref.low is not None and value < ref.low:
        return "low"
    if ref.high is not None and value > ref.high:
        return "high"
    if ref.low is not None or ref.high is not None:
        return "normal"
    return "unknown"


# ---------------------------------------------------------------------------
# Base parser
# ---------------------------------------------------------------------------

class BaseReportParser:
    """Base class for all report-type parsers.

    Subclasses define MARKERS dict and REFERENCES dict.

    MARKERS format::

        {
            "canonical_name": [
                r"name_regex_pattern",
                r"value_regex_pattern_with_capture_group",
            ],
            ...
        }

    REFERENCES format::

        {
            "canonical_name": ReferenceInfo(unit="mg/dL", low=70, high=100),
            ...
        }
    """

    MARKERS: dict[str, list[str]] = {}
    REFERENCES: dict[str, ReferenceInfo] = {}

    # Common reference-range pattern found after the value
    _REF_RANGE_RE = re.compile(
        r"[\(\[]?\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*[\)\]]?"
    )

    def parse(self, text: str) -> list[ParsedBiomarker]:
        """Extract all markers this parser knows about from the text."""
        results: list[ParsedBiomarker] = []
        lines = text.splitlines()

        for canonical, patterns in self.MARKERS.items():
            if len(patterns) < 2:
                continue
            name_pat, val_pat = patterns[0], patterns[1]
            found = self._search_marker(text, lines, canonical, name_pat, val_pat)
            if found:
                results.append(found)

        return results

    def _search_marker(
        self,
        full_text: str,
        lines: list[str],
        canonical: str,
        name_pat: str,
        val_pat: str,
    ) -> Optional[ParsedBiomarker]:
        """Search for a single marker across the text."""

        # Strategy 1: Line-by-line (tabular format)
        for line in lines:
            name_m = re.search(name_pat, line, re.IGNORECASE)
            if not name_m:
                continue

            remainder = line[name_m.end():]
            val_m = re.search(val_pat, remainder, re.IGNORECASE)
            if not val_m:
                # Also try the whole line (value might be before name in some formats)
                val_m = re.search(val_pat, line, re.IGNORECASE)
                if not val_m:
                    continue

            return self._build_result(canonical, name_m, val_m, remainder)

        # Strategy 2: Full-text search with proximity
        for name_m in re.finditer(name_pat, full_text, re.IGNORECASE):
            window = full_text[name_m.end():name_m.end() + 120]
            # Skip separator characters
            window_clean = re.sub(r"^[\s:=|]+", "", window)
            val_m = re.search(val_pat, window_clean, re.IGNORECASE)
            if val_m:
                return self._build_result(canonical, name_m, val_m, window_clean)

        return None

    def _build_result(
        self,
        canonical: str,
        name_match: re.Match,
        val_match: re.Match,
        context: str,
    ) -> ParsedBiomarker:
        """Build a ParsedBiomarker from regex matches."""
        value_str = val_match.group(1)
        unit = ""
        if val_match.lastindex and val_match.lastindex >= 2 and val_match.group(2):
            unit = val_match.group(2).strip()

        # Use default unit from REFERENCES if not detected
        ref = self.REFERENCES.get(canonical)
        if not unit and ref:
            unit = ref.unit

        try:
            value = float(value_str)
        except (ValueError, TypeError):
            value = None

        # Extract reference range from context
        ref_range = ""
        ref_range_m = self._REF_RANGE_RE.search(context[val_match.end():])
        if ref_range_m:
            ref_range = f"{ref_range_m.group(1)} - {ref_range_m.group(2)}"
        elif ref:
            ref_range = ref.range_str

        return ParsedBiomarker(
            test_name=name_match.group(0).strip(),
            canonical_name=canonical,
            value=value,
            value_raw=value_str,
            unit=unit,
            reference_range=ref_range,
        )

    def evaluate_status(self, biomarker: ParsedBiomarker) -> str:
        """Evaluate if a parsed biomarker value is normal/low/high."""
        ref = self.REFERENCES.get(biomarker.canonical_name)
        if not ref:
            return "unknown"
        return _evaluate_status(biomarker.value, ref)


# ---------------------------------------------------------------------------
# CBC Parser
# ---------------------------------------------------------------------------

class CBCParser(BaseReportParser):
    """Parse Complete Blood Count reports."""

    MARKERS = {
        "hemoglobin": [
            r"h[ae]moglobin|hgb|hb(?:\s*%)?",
            r"(\d+\.?\d*)\s*(g/dL|gm/dl|g%|gm%)?",
        ],
        "rbc": [
            r"r\.?b\.?c\.?|red\s*blood\s*cell|erythrocyte\s*count",
            r"(\d+\.?\d*)\s*(mill/cumm|million/cumm|x10\^6/uL)?",
        ],
        "wbc": [
            r"w\.?b\.?c\.?|white\s*blood\s*cell|total\s*leucocyte|tlc",
            r"(\d+\.?\d*)\s*(/cumm|cells/cumm|x10\^3/uL|thou/cumm)?",
        ],
        "platelets": [
            r"platelet[s]?|plt",
            r"(\d+\.?\d*)\s*(lakh/cumm|lac/cumm|x10\^3/uL|thou/cumm|/cumm)?",
        ],
        "pcv": [
            r"pcv|hematocrit|hct|packed\s*cell\s*volume",
            r"(\d+\.?\d*)\s*(%|L/L)?",
        ],
        "mcv": [
            r"mcv|mean\s*corp(?:uscular)?\s*vol(?:ume)?",
            r"(\d+\.?\d*)\s*(fL|fl|cu\.?\s*micron)?",
        ],
        "mch": [
            r"(?<!m)mch(?!c)|mean\s*corp(?:uscular)?\s*h[ae]moglobin(?!\s*conc)",
            r"(\d+\.?\d*)\s*(pg)?",
        ],
        "mchc": [
            r"mchc|mean\s*corp(?:uscular)?\s*h[ae]moglobin\s*conc(?:entration)?",
            r"(\d+\.?\d*)\s*(g/dL|gm/dl|g%)?",
        ],
        "rdw": [
            r"rdw|red\s*cell\s*distribution\s*width",
            r"(\d+\.?\d*)\s*(%)?",
        ],
        "mpv": [
            r"mpv|mean\s*platelet\s*volume",
            r"(\d+\.?\d*)\s*(fL|fl)?",
        ],
        "esr": [
            r"esr|erythrocyte\s*sedimentation\s*rate",
            r"(\d+\.?\d*)\s*(mm/hr|mm/1st\s*hr)?",
        ],
        "neutrophils": [
            r"neutrophil[s]?|neut",
            r"(\d+\.?\d*)\s*(%)?",
        ],
        "lymphocytes": [
            r"lymphocyte[s]?|lymph",
            r"(\d+\.?\d*)\s*(%)?",
        ],
        "monocytes": [
            r"monocyte[s]?|mono",
            r"(\d+\.?\d*)\s*(%)?",
        ],
        "eosinophils": [
            r"eosinophil[s]?|eosin",
            r"(\d+\.?\d*)\s*(%)?",
        ],
        "basophils": [
            r"basophil[s]?|baso",
            r"(\d+\.?\d*)\s*(%)?",
        ],
    }

    REFERENCES = {
        "hemoglobin": ReferenceInfo(unit="g/dL", low=13.0, high=17.0),
        "rbc": ReferenceInfo(unit="mill/cumm", low=4.5, high=5.5),
        "wbc": ReferenceInfo(unit="/cumm", low=4000, high=11000),
        "platelets": ReferenceInfo(unit="lakh/cumm", low=1.5, high=4.0),
        "pcv": ReferenceInfo(unit="%", low=40, high=50),
        "mcv": ReferenceInfo(unit="fL", low=80, high=100),
        "mch": ReferenceInfo(unit="pg", low=27, high=32),
        "mchc": ReferenceInfo(unit="g/dL", low=32, high=36),
        "rdw": ReferenceInfo(unit="%", low=11.5, high=14.5),
        "mpv": ReferenceInfo(unit="fL", low=7.5, high=11.5),
        "esr": ReferenceInfo(unit="mm/hr", low=0, high=20),
        "neutrophils": ReferenceInfo(unit="%", low=40, high=70),
        "lymphocytes": ReferenceInfo(unit="%", low=20, high=40),
        "monocytes": ReferenceInfo(unit="%", low=2, high=8),
        "eosinophils": ReferenceInfo(unit="%", low=1, high=4),
        "basophils": ReferenceInfo(unit="%", low=0, high=1),
    }


# ---------------------------------------------------------------------------
# Lipid Profile Parser
# ---------------------------------------------------------------------------

class LipidProfileParser(BaseReportParser):
    """Parse Lipid Profile reports."""

    MARKERS = {
        "total_cholesterol": [
            r"total\s*cholesterol|cholesterol\s*total|serum\s*cholesterol|cholesterol(?!\s*(?:hdl|ldl|vldl))",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "ldl": [
            r"ldl[\s-]*(?:cholesterol|c)?|low\s*density\s*lipoprotein",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "hdl": [
            r"hdl[\s-]*(?:cholesterol|c)?|high\s*density\s*lipoprotein",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "vldl": [
            r"vldl[\s-]*(?:cholesterol|c)?|very\s*low\s*density\s*lipoprotein",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "triglycerides": [
            r"triglyceride[s]?|tg(?!\s*[a-z])|serum\s*triglyceride",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "cholesterol_hdl_ratio": [
            r"(?:total\s*)?cholesterol\s*/\s*hdl\s*ratio|chol/hdl",
            r"(\d+\.?\d*)",
        ],
        "ldl_hdl_ratio": [
            r"ldl\s*/\s*hdl\s*ratio",
            r"(\d+\.?\d*)",
        ],
    }

    REFERENCES = {
        "total_cholesterol": ReferenceInfo(unit="mg/dL", low=None, high=200),
        "ldl": ReferenceInfo(unit="mg/dL", low=None, high=100),
        "hdl": ReferenceInfo(unit="mg/dL", low=40, high=None),
        "vldl": ReferenceInfo(unit="mg/dL", low=None, high=40),
        "triglycerides": ReferenceInfo(unit="mg/dL", low=None, high=150),
        "cholesterol_hdl_ratio": ReferenceInfo(unit="", low=None, high=5.0),
        "ldl_hdl_ratio": ReferenceInfo(unit="", low=None, high=3.5),
    }


# ---------------------------------------------------------------------------
# Liver Function Test (LFT) Parser
# ---------------------------------------------------------------------------

class LFTParser(BaseReportParser):
    """Parse Liver Function Test reports."""

    MARKERS = {
        "total_bilirubin": [
            r"total\s*bilirubin|bilirubin\s*total|serum\s*bilirubin\s*total",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "direct_bilirubin": [
            r"direct\s*bilirubin|bilirubin\s*direct|conjugated\s*bilirubin",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "indirect_bilirubin": [
            r"indirect\s*bilirubin|bilirubin\s*indirect|unconjugated\s*bilirubin",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "alt": [
            r"sgpt|alt\s*\(?sgpt\)?|alanine\s*(?:amino)?transf?erase",
            r"(\d+\.?\d*)\s*(U/L|IU/L)?",
        ],
        "ast": [
            r"sgot|ast\s*\(?sgot\)?|aspartate\s*(?:amino)?transf?erase",
            r"(\d+\.?\d*)\s*(U/L|IU/L)?",
        ],
        "alp": [
            r"alk(?:aline)?\.?\s*phosphatase|alp(?!\s*[a-z])",
            r"(\d+\.?\d*)\s*(U/L|IU/L)?",
        ],
        "ggt": [
            r"gamma[\s-]*gt|ggtp|gamma\s*glutamyl\s*(?:transferase|transpeptidase)",
            r"(\d+\.?\d*)\s*(U/L|IU/L)?",
        ],
        "total_protein": [
            r"total\s*protein|serum\s*protein\s*total",
            r"(\d+\.?\d*)\s*(g/dL|gm/dl)?",
        ],
        "albumin": [
            r"albumin|serum\s*albumin",
            r"(\d+\.?\d*)\s*(g/dL|gm/dl)?",
        ],
        "globulin": [
            r"globulin|serum\s*globulin",
            r"(\d+\.?\d*)\s*(g/dL|gm/dl)?",
        ],
        "ag_ratio": [
            r"a\s*/\s*g\s*ratio|albumin\s*/?\s*globulin\s*ratio",
            r"(\d+\.?\d*)",
        ],
    }

    REFERENCES = {
        "total_bilirubin": ReferenceInfo(unit="mg/dL", low=0.1, high=1.2),
        "direct_bilirubin": ReferenceInfo(unit="mg/dL", low=0.0, high=0.3),
        "indirect_bilirubin": ReferenceInfo(unit="mg/dL", low=0.1, high=1.0),
        "alt": ReferenceInfo(unit="U/L", low=7, high=56),
        "ast": ReferenceInfo(unit="U/L", low=10, high=40),
        "alp": ReferenceInfo(unit="U/L", low=44, high=147),
        "ggt": ReferenceInfo(unit="U/L", low=9, high=48),
        "total_protein": ReferenceInfo(unit="g/dL", low=6.0, high=8.3),
        "albumin": ReferenceInfo(unit="g/dL", low=3.5, high=5.5),
        "globulin": ReferenceInfo(unit="g/dL", low=2.0, high=3.5),
        "ag_ratio": ReferenceInfo(unit="", low=1.0, high=2.2),
    }


# ---------------------------------------------------------------------------
# Kidney Function Test (KFT) Parser
# ---------------------------------------------------------------------------

class KFTParser(BaseReportParser):
    """Parse Kidney Function Test / Renal Function Test reports."""

    MARKERS = {
        "urea": [
            r"(?:serum\s*|blood\s*)?urea(?!\s*nitrogen)",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "bun": [
            r"blood\s*urea\s*nitrogen|bun|urea\s*nitrogen",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "creatinine": [
            r"(?:serum\s*)?creatinine|creat(?!\s*[a-z])",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "uric_acid": [
            r"(?:serum\s*)?uric\s*acid",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "egfr": [
            r"e?gfr|estimated\s*(?:glomerular\s*)?filtration\s*rate|glomerular\s*filtration",
            r"(\d+\.?\d*)\s*(mL/min(?:/1\.73\s*m2)?)?",
        ],
        "sodium": [
            r"(?:serum\s*)?sodium|na\+",
            r"(\d+\.?\d*)\s*(mEq/L|mmol/L)?",
        ],
        "potassium": [
            r"(?:serum\s*)?potassium|k\+",
            r"(\d+\.?\d*)\s*(mEq/L|mmol/L)?",
        ],
        "chloride": [
            r"(?:serum\s*)?chloride|cl-?(?!\s*[a-z])",
            r"(\d+\.?\d*)\s*(mEq/L|mmol/L)?",
        ],
        "calcium": [
            r"(?:serum\s*)?calcium|ca\+?\+?(?!\s*[a-z])",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "phosphorus": [
            r"(?:serum\s*)?phosphorus|phosphate|inorganic\s*phosphorus",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
    }

    REFERENCES = {
        "urea": ReferenceInfo(unit="mg/dL", low=15, high=40),
        "bun": ReferenceInfo(unit="mg/dL", low=7, high=20),
        "creatinine": ReferenceInfo(unit="mg/dL", low=0.7, high=1.3),
        "uric_acid": ReferenceInfo(unit="mg/dL", low=3.5, high=7.2),
        "egfr": ReferenceInfo(unit="mL/min/1.73m2", low=90, high=None),
        "sodium": ReferenceInfo(unit="mEq/L", low=136, high=145),
        "potassium": ReferenceInfo(unit="mEq/L", low=3.5, high=5.1),
        "chloride": ReferenceInfo(unit="mEq/L", low=98, high=106),
        "calcium": ReferenceInfo(unit="mg/dL", low=8.5, high=10.5),
        "phosphorus": ReferenceInfo(unit="mg/dL", low=2.5, high=4.5),
    }


# ---------------------------------------------------------------------------
# Thyroid Parser
# ---------------------------------------------------------------------------

class ThyroidParser(BaseReportParser):
    """Parse Thyroid Function Test reports (TSH, T3, T4)."""

    MARKERS = {
        "tsh": [
            r"tsh|thyroid\s*stimulating\s*hormone|serum\s*tsh",
            r"(\d+\.?\d*)\s*(mIU/mL|uIU/mL|mIU/L)?",
        ],
        "free_t3": [
            r"free\s*t3|ft3|free\s*triiodothyronine",
            r"(\d+\.?\d*)\s*(pg/mL|pmol/L)?",
        ],
        "total_t3": [
            r"total\s*t3(?!\s*free)|(?<!free\s)t3(?!\s*free)|triiodothyronine(?!\s*free)",
            r"(\d+\.?\d*)\s*(ng/dL|ng/mL|nmol/L)?",
        ],
        "free_t4": [
            r"free\s*t4|ft4|free\s*thyroxine",
            r"(\d+\.?\d*)\s*(ng/dL|pmol/L)?",
        ],
        "total_t4": [
            r"total\s*t4(?!\s*free)|(?<!free\s)t4(?!\s*free)|thyroxine(?!\s*free)",
            r"(\d+\.?\d*)\s*(ug/dL|nmol/L)?",
        ],
    }

    REFERENCES = {
        "tsh": ReferenceInfo(unit="mIU/mL", low=0.4, high=4.0),
        "free_t3": ReferenceInfo(unit="pg/mL", low=2.0, high=4.4),
        "total_t3": ReferenceInfo(unit="ng/dL", low=80, high=200),
        "free_t4": ReferenceInfo(unit="ng/dL", low=0.8, high=1.8),
        "total_t4": ReferenceInfo(unit="ug/dL", low=5.1, high=14.1),
    }


# ---------------------------------------------------------------------------
# Vitamin Parser
# ---------------------------------------------------------------------------

class VitaminParser(BaseReportParser):
    """Parse Vitamin and mineral reports (Vitamin D, B12, Iron, Ferritin)."""

    MARKERS = {
        "vitamin_d": [
            r"(?:25[\s-]*(?:oh|hydroxy)\s*)?vitamin\s*d(?:\s*total)?|25\s*\(?oh\)?\s*d|cholecalciferol",
            r"(\d+\.?\d*)\s*(ng/mL|nmol/L)?",
        ],
        "vitamin_b12": [
            r"vitamin\s*b\s*12|vit\s*b\s*12|cyanocobalamin|cobalamin",
            r"(\d+\.?\d*)\s*(pg/mL|pmol/L)?",
        ],
        "folate": [
            r"folate|folic\s*acid|serum\s*folate",
            r"(\d+\.?\d*)\s*(ng/mL|nmol/L)?",
        ],
        "iron": [
            r"(?:serum\s*)?iron(?!\s*binding)",
            r"(\d+\.?\d*)\s*(ug/dL|umol/L)?",
        ],
        "ferritin": [
            r"(?:serum\s*)?ferritin",
            r"(\d+\.?\d*)\s*(ng/mL|ug/L)?",
        ],
        "tibc": [
            r"tibc|total\s*iron\s*binding\s*capacity",
            r"(\d+\.?\d*)\s*(ug/dL|umol/L)?",
        ],
        "transferrin_saturation": [
            r"transferrin\s*saturation|tsat|iron\s*saturation",
            r"(\d+\.?\d*)\s*(%)?",
        ],
    }

    REFERENCES = {
        "vitamin_d": ReferenceInfo(unit="ng/mL", low=30, high=100),
        "vitamin_b12": ReferenceInfo(unit="pg/mL", low=200, high=900),
        "folate": ReferenceInfo(unit="ng/mL", low=3.0, high=17.0),
        "iron": ReferenceInfo(unit="ug/dL", low=60, high=170),
        "ferritin": ReferenceInfo(unit="ng/mL", low=20, high=250),
        "tibc": ReferenceInfo(unit="ug/dL", low=250, high=370),
        "transferrin_saturation": ReferenceInfo(unit="%", low=20, high=50),
    }


# ---------------------------------------------------------------------------
# Diabetes Parser
# ---------------------------------------------------------------------------

class DiabetesParser(BaseReportParser):
    """Parse Diabetes-related reports (Glucose, HbA1c)."""

    MARKERS = {
        "fasting_glucose": [
            r"fasting\s*(?:blood\s*)?(?:sugar|glucose)|fbs|fasting\s*blood\s*glucose|fasting\s*plasma\s*glucose",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "pp_glucose": [
            r"post\s*prandial\s*(?:blood\s*)?(?:sugar|glucose)|ppbs|pp\s*(?:blood\s*)?(?:sugar|glucose)|2\s*hr?\s*(?:post\s*)?(?:prandial|meal)\s*(?:sugar|glucose)",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "random_glucose": [
            r"random\s*(?:blood\s*)?(?:sugar|glucose)|rbs|random\s*plasma\s*glucose",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "hba1c": [
            r"hba1c|glyc(?:osyl|at)ed\s*h[ae]moglobin|h[ae]moglobin\s*a1c|a1c",
            r"(\d+\.?\d*)\s*(%)?",
        ],
        "average_blood_glucose": [
            r"(?:estimated\s*)?average\s*(?:blood\s*)?glucose|eag|mean\s*plasma\s*glucose",
            r"(\d+\.?\d*)\s*(mg/dL)?",
        ],
        "fasting_insulin": [
            r"fasting\s*insulin|serum\s*insulin\s*fasting|insulin\s*fasting",
            r"(\d+\.?\d*)\s*(uIU/mL|mIU/L)?",
        ],
        "homa_ir": [
            r"homa[\s-]*ir|insulin\s*resistance\s*index",
            r"(\d+\.?\d*)",
        ],
    }

    REFERENCES = {
        "fasting_glucose": ReferenceInfo(unit="mg/dL", low=70, high=100),
        "pp_glucose": ReferenceInfo(unit="mg/dL", low=70, high=140),
        "random_glucose": ReferenceInfo(unit="mg/dL", low=70, high=200),
        "hba1c": ReferenceInfo(unit="%", low=4.0, high=5.7),
        "average_blood_glucose": ReferenceInfo(unit="mg/dL", low=70, high=126),
        "fasting_insulin": ReferenceInfo(unit="uIU/mL", low=2.6, high=24.9),
        "homa_ir": ReferenceInfo(unit="", low=None, high=2.5),
    }


# ---------------------------------------------------------------------------
# Registry: map report type string to parser
# ---------------------------------------------------------------------------

PARSER_REGISTRY: dict[str, BaseReportParser] = {
    "cbc": CBCParser(),
    "lipid_profile": LipidProfileParser(),
    "lft": LFTParser(),
    "kft": KFTParser(),
    "thyroid": ThyroidParser(),
    "vitamin": VitaminParser(),
    "diabetes": DiabetesParser(),
}

ALL_PARSERS: list[BaseReportParser] = list(PARSER_REGISTRY.values())


def get_parser(report_type: str) -> Optional[BaseReportParser]:
    """Look up a parser by report type string."""
    return PARSER_REGISTRY.get(report_type.lower())


def run_all_parsers(text: str) -> list[ParsedBiomarker]:
    """Run every parser and return a deduplicated list of biomarkers."""
    seen: set[str] = set()
    results: list[ParsedBiomarker] = []
    for parser in ALL_PARSERS:
        for bio in parser.parse(text):
            if bio.canonical_name not in seen:
                results.append(bio)
                seen.add(bio.canonical_name)
    return results
