"""Medical regex extraction engine for structured lab report parsing.

Handles multiple report formats:
- Tabular (columns: Test Name | Value | Unit | Reference Range)
- Key-value (Test Name: Value Unit)
- Free-text (biomarker mentions within running text)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.normalizer import canonicalize_biomarker_name

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParsedBiomarker:
    test_name: str
    canonical_name: str
    value: Optional[float] = None
    value_raw: str = ""
    unit: str = ""
    reference_range: str = ""

    def to_dict(self) -> dict:
        return {
            "test_name": self.test_name,
            "canonical_name": self.canonical_name,
            "value": self.value,
            "value_raw": self.value_raw,
            "unit": self.unit,
            "reference_range": self.reference_range,
        }


# ---------------------------------------------------------------------------
# Master biomarker patterns
# ---------------------------------------------------------------------------

# Each entry: biomarker_key -> (name_pattern, value_with_unit_pattern)
BIOMARKER_PATTERNS: dict[str, tuple[str, str]] = {
    # CBC
    "hemoglobin": (
        r"(?:h[ae]moglobin|hgb|hb)\s*(?:\(%\))?",
        r"(\d+\.?\d*)\s*(g/dL|gm/dl|g%|gm%)?",
    ),
    "rbc": (
        r"(?:r\.?b\.?c\.?|red\s*blood\s*cell|erythrocyte)\s*(?:count)?",
        r"(\d+\.?\d*)\s*(mill/cumm|million/cumm|x10\^6/uL|mill\.?/cumm)?",
    ),
    "wbc": (
        r"(?:w\.?b\.?c\.?|white\s*blood\s*cell|total\s*leucocyte|tlc)\s*(?:count)?",
        r"(\d+\.?\d*)\s*(/cumm|cells/cumm|x10\^3/uL|thou/cumm)?",
    ),
    "platelets": (
        r"(?:platelet|plt)\s*(?:count)?",
        r"(\d+\.?\d*)\s*(lakh/cumm|lac/cumm|x10\^3/uL|thou/cumm|/cumm)?",
    ),
    "pcv": (
        r"(?:pcv|hematocrit|hct|packed\s*cell\s*volume)",
        r"(\d+\.?\d*)\s*(%|percent|L/L)?",
    ),
    "mcv": (
        r"(?:mcv|mean\s*corp(?:uscular)?\s*vol(?:ume)?)",
        r"(\d+\.?\d*)\s*(fL|fl|cu\.?\s*micron)?",
    ),
    "mch": (
        r"(?:(?<!m)mch(?!c)|mean\s*corp(?:uscular)?\s*h(?:ae)?moglobin(?!\s*conc))",
        r"(\d+\.?\d*)\s*(pg)?",
    ),
    "mchc": (
        r"(?:mchc|mean\s*corp(?:uscular)?\s*h(?:ae)?moglobin\s*conc(?:entration)?)",
        r"(\d+\.?\d*)\s*(g/dL|gm/dl|g%)?",
    ),
    # Lipid profile
    "total_cholesterol": (
        r"(?:total\s*cholesterol|cholesterol\s*total|serum\s*cholesterol|cholesterol(?!\s*(?:hdl|ldl|vldl)))",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "ldl": (
        r"(?:ldl[\s-]*(?:cholesterol|c)?|low\s*density\s*lipoprotein)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "hdl": (
        r"(?:hdl[\s-]*(?:cholesterol|c)?|high\s*density\s*lipoprotein)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "vldl": (
        r"(?:vldl[\s-]*(?:cholesterol|c)?|very\s*low\s*density\s*lipoprotein)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "triglycerides": (
        r"(?:triglyceride[s]?|tg|serum\s*triglyceride[s]?)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    # LFT
    "alt": (
        r"(?:sgpt|alt\s*\(?sgpt\)?|alanine\s*(?:amino)?transf?erase)",
        r"(\d+\.?\d*)\s*(U/L|IU/L)?",
    ),
    "ast": (
        r"(?:sgot|ast\s*\(?sgot\)?|aspartate\s*(?:amino)?transf?erase)",
        r"(\d+\.?\d*)\s*(U/L|IU/L)?",
    ),
    "alp": (
        r"(?:alk(?:aline)?\.?\s*phosphatase|alp)",
        r"(\d+\.?\d*)\s*(U/L|IU/L)?",
    ),
    "total_bilirubin": (
        r"(?:total\s*bilirubin|bilirubin\s*total|serum\s*bilirubin\s*total)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "direct_bilirubin": (
        r"(?:direct\s*bilirubin|bilirubin\s*direct|conjugated\s*bilirubin)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "indirect_bilirubin": (
        r"(?:indirect\s*bilirubin|bilirubin\s*indirect|unconjugated\s*bilirubin)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "total_protein": (
        r"(?:total\s*protein|serum\s*protein\s*total)",
        r"(\d+\.?\d*)\s*(g/dL|gm/dl)?",
    ),
    "albumin": (
        r"(?:albumin|serum\s*albumin)(?!\s*/)",
        r"(\d+\.?\d*)\s*(g/dL|gm/dl)?",
    ),
    "globulin": (
        r"(?:globulin|serum\s*globulin)",
        r"(\d+\.?\d*)\s*(g/dL|gm/dl)?",
    ),
    "ag_ratio": (
        r"(?:a/g\s*ratio|albumin\s*/?\s*globulin\s*ratio)",
        r"(\d+\.?\d*)\s*(?:ratio)?",
    ),
    "ggt": (
        r"(?:gamma[\s-]*gt|ggtp|gamma\s*glutamyl\s*transferase)",
        r"(\d+\.?\d*)\s*(U/L|IU/L)?",
    ),
    # KFT
    "urea": (
        r"(?:(?:serum|blood)\s*urea(?!\s*nitrogen)|urea(?!\s*nitrogen))",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "bun": (
        r"(?:blood\s*urea\s*nitrogen|bun|urea\s*nitrogen)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "creatinine": (
        r"(?:(?:serum\s*)?creatinine|creat)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "uric_acid": (
        r"(?:(?:serum\s*)?uric\s*acid)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "egfr": (
        r"(?:e?gfr|estimated\s*gfr|glomerular\s*filtration\s*rate)",
        r"(\d+\.?\d*)\s*(mL/min(?:/1\.73\s*m2)?)?",
    ),
    "sodium": (
        r"(?:(?:serum\s*)?sodium|na\+?(?!\s*[a-z]))",
        r"(\d+\.?\d*)\s*(mEq/L|mmol/L)?",
    ),
    "potassium": (
        r"(?:(?:serum\s*)?potassium|k\+(?!\s*[a-z]))",
        r"(\d+\.?\d*)\s*(mEq/L|mmol/L)?",
    ),
    "chloride": (
        r"(?:(?:serum\s*)?chloride|cl-?)",
        r"(\d+\.?\d*)\s*(mEq/L|mmol/L)?",
    ),
    "calcium": (
        r"(?:(?:serum\s*)?calcium|ca\+?\+?(?!\s*[a-z]))",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "phosphorus": (
        r"(?:(?:serum\s*)?phosphorus|phosphate)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    # Thyroid
    "tsh": (
        r"(?:tsh|thyroid\s*stimulating\s*hormone|serum\s*tsh)",
        r"(\d+\.?\d*)\s*(mIU/mL|uIU/mL|mIU/L)?",
    ),
    "free_t3": (
        r"(?:free\s*t3|ft3|free\s*triiodothyronine)",
        r"(\d+\.?\d*)\s*(pg/mL|pmol/L)?",
    ),
    "total_t3": (
        r"(?:total\s*t3|t3|triiodothyronine)(?!\s*free)",
        r"(\d+\.?\d*)\s*(ng/dL|ng/mL|nmol/L)?",
    ),
    "free_t4": (
        r"(?:free\s*t4|ft4|free\s*thyroxine)",
        r"(\d+\.?\d*)\s*(ng/dL|pmol/L)?",
    ),
    "total_t4": (
        r"(?:total\s*t4|t4|thyroxine)(?!\s*free)",
        r"(\d+\.?\d*)\s*(ug/dL|nmol/L)?",
    ),
    # Diabetes
    "fasting_glucose": (
        r"(?:fasting\s*(?:blood\s*)?(?:sugar|glucose)|fbs|fasting\s*blood\s*glucose)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "pp_glucose": (
        r"(?:post\s*prandial\s*(?:blood\s*)?(?:sugar|glucose)|ppbs|pp\s*(?:blood\s*)?(?:sugar|glucose))",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "random_glucose": (
        r"(?:random\s*(?:blood\s*)?(?:sugar|glucose)|rbs)",
        r"(\d+\.?\d*)\s*(mg/dL)?",
    ),
    "hba1c": (
        r"(?:hba1c|glyc(?:osyl|at)ated\s*h[ae]moglobin|h[ae]moglobin\s*a1c)",
        r"(\d+\.?\d*)\s*(%)?",
    ),
    # Vitamins
    "vitamin_d": (
        r"(?:(?:25[\s-]*(?:oh|hydroxy)\s*)?vitamin\s*d(?:\s*total)?|25\s*\(?oh\)?\s*d)",
        r"(\d+\.?\d*)\s*(ng/mL|nmol/L)?",
    ),
    "vitamin_b12": (
        r"(?:vitamin\s*b\s*12|vit\s*b\s*12|cyanocobalamin|cobalamin)",
        r"(\d+\.?\d*)\s*(pg/mL|pmol/L)?",
    ),
    "folate": (
        r"(?:folate|folic\s*acid|serum\s*folate)",
        r"(\d+\.?\d*)\s*(ng/mL|nmol/L)?",
    ),
    "iron": (
        r"(?:(?:serum\s*)?iron)(?!\s*binding)",
        r"(\d+\.?\d*)\s*(ug/dL|umol/L)?",
    ),
    "ferritin": (
        r"(?:(?:serum\s*)?ferritin)",
        r"(\d+\.?\d*)\s*(ng/mL|ug/L)?",
    ),
    "tibc": (
        r"(?:tibc|total\s*iron\s*binding\s*capacity)",
        r"(\d+\.?\d*)\s*(ug/dL|umol/L)?",
    ),
}

# Reference range pattern (matches things like "13.0-17.0", "< 200", "> 40", "70 - 100")
_REF_RANGE_PATTERN = re.compile(
    r"(?:"
    r"(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)"  # range: 13.0-17.0
    r"|[<>]\s*(\d+\.?\d*)"                  # inequality: < 200
    r"|(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*(mg/dL|g/dL|U/L|IU/L|mEq/L|mmol/L|ng/mL|pg/mL|%|fL|mIU/mL|ug/dL)?"
    r")"
)


# ---------------------------------------------------------------------------
# Parser class
# ---------------------------------------------------------------------------

class MedicalParser:
    """Main engine for extracting biomarkers from OCR text."""

    def __init__(self, patterns: Optional[dict[str, tuple[str, str]]] = None):
        self.patterns = patterns or BIOMARKER_PATTERNS

    def parse(self, text: str) -> list[ParsedBiomarker]:
        """Parse text and return all found biomarkers."""
        results: list[ParsedBiomarker] = []

        # Strategy 1: Tabular format
        table_results = self._parse_tabular(text)
        results.extend(table_results)

        # Strategy 2: Key-value / inline patterns
        kv_results = self._parse_key_value(text)

        # Merge: add kv_results only if canonical name not already found
        found_names = {r.canonical_name for r in results}
        for r in kv_results:
            if r.canonical_name not in found_names:
                results.append(r)
                found_names.add(r.canonical_name)

        return results

    def _parse_tabular(self, text: str) -> list[ParsedBiomarker]:
        """Parse tabular lab reports where columns are separated by whitespace.

        Common Indian lab report format:
        Test Name          Value     Unit        Reference Range
        Hemoglobin         14.5      g/dL        13.0 - 17.0
        """
        results: list[ParsedBiomarker] = []
        lines = text.splitlines()

        for line in lines:
            for bio_key, (name_pat, val_pat) in self.patterns.items():
                # Check if biomarker name is in this line
                name_match = re.search(name_pat, line, re.IGNORECASE)
                if not name_match:
                    continue

                # Extract value + unit from the rest of the line after the name
                remainder = line[name_match.end():]
                val_match = re.search(val_pat, remainder, re.IGNORECASE)
                if not val_match:
                    continue

                value_str = val_match.group(1)
                unit = val_match.group(2) if val_match.lastindex and val_match.lastindex >= 2 else ""
                unit = unit or ""

                # Try to extract reference range from the remainder
                ref_range = self._extract_reference_range(remainder, val_match.end())

                try:
                    value = float(value_str)
                except (ValueError, TypeError):
                    value = None

                results.append(ParsedBiomarker(
                    test_name=name_match.group(0).strip(),
                    canonical_name=bio_key,
                    value=value,
                    value_raw=value_str,
                    unit=unit.strip(),
                    reference_range=ref_range,
                ))
                break  # Found match for this line, move to next line

        return results

    def _parse_key_value(self, text: str) -> list[ParsedBiomarker]:
        """Parse key-value style reports (Test: Value Unit)."""
        results: list[ParsedBiomarker] = []

        for bio_key, (name_pat, val_pat) in self.patterns.items():
            # Search entire text for each biomarker
            for name_match in re.finditer(name_pat, text, re.IGNORECASE):
                # Look for value within 100 characters after the name
                search_window = text[name_match.end():name_match.end() + 100]
                # Skip optional colon/equals separator
                search_window = re.sub(r"^\s*[:=]\s*", "", search_window)

                val_match = re.search(val_pat, search_window, re.IGNORECASE)
                if not val_match:
                    continue

                value_str = val_match.group(1)
                unit = val_match.group(2) if val_match.lastindex and val_match.lastindex >= 2 else ""
                unit = unit or ""

                ref_range = self._extract_reference_range(search_window, val_match.end())

                try:
                    value = float(value_str)
                except (ValueError, TypeError):
                    value = None

                results.append(ParsedBiomarker(
                    test_name=name_match.group(0).strip(),
                    canonical_name=bio_key,
                    value=value,
                    value_raw=value_str,
                    unit=unit.strip(),
                    reference_range=ref_range,
                ))
                break  # Take first match per biomarker

        return results

    def _extract_reference_range(self, text: str, start_pos: int = 0) -> str:
        """Extract reference range string from text after the value."""
        search_text = text[start_pos:start_pos + 80]
        # Look for patterns like "13.0 - 17.0", "< 200", "(70-100)"
        ref_match = _REF_RANGE_PATTERN.search(search_text)
        if ref_match:
            return ref_match.group(0).strip()
        return ""
