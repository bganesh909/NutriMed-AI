"""
Unit tests for biomarker extraction from OCR text.

Tests the regex patterns in the OCR service's medical_parser and
biomarker_engine (CBC, Lipid, etc.).
"""

import sys
import os

import pytest

# Add OCR service to path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "ocr-service"),
)

from app.medical_parser import MedicalParser, ParsedBiomarker
from app.biomarker_engine import (
    CBCParser,
    LipidProfileParser,
    LFTParser,
    ThyroidParser,
    DiabetesParser,
    VitaminParser,
    run_all_parsers,
)


# ---------------------------------------------------------------------------
# Sample OCR texts
# ---------------------------------------------------------------------------

SAMPLE_CBC_TEXT = """
COMPLETE BLOOD COUNT (CBC)
Patient Name: Rahul Sharma          Date: 15-Jan-2026

Test Name               Value       Unit          Reference Range
Haemoglobin             14.5        g/dL          13.0 - 17.0
RBC Count               5.2         mill/cumm     4.5 - 5.5
WBC Count               7500        /cumm         4000 - 11000
Platelet Count          2.5         lakh/cumm     1.5 - 4.0
PCV                     42.0        %             40 - 50
MCV                     88.5        fL            80 - 100
MCH                     29.5        pg            27 - 32
MCHC                    33.2        g/dL          32 - 36
RDW                     13.0        %             11.5 - 14.5
ESR                     8           mm/hr         0 - 20

Differential Count:
Neutrophils             60          %             40 - 70
Lymphocytes             30          %             20 - 40
Monocytes               5           %             2 - 8
Eosinophils             3           %             1 - 4
Basophils               0.5         %             0 - 1
"""

SAMPLE_LIPID_TEXT = """
LIPID PROFILE
Patient Name: Priya Patel          Date: 20-Feb-2026

Test                        Result      Unit        Reference Range
Total Cholesterol           220         mg/dL       < 200
LDL Cholesterol             145         mg/dL       < 100
HDL Cholesterol             42          mg/dL       > 40
VLDL Cholesterol            33          mg/dL       < 40
Triglycerides               165         mg/dL       < 150
Cholesterol/HDL Ratio       5.2                     < 5.0
LDL/HDL Ratio              3.4                     < 3.5
"""

SAMPLE_DIABETES_TEXT = """
DIABETES SCREENING
Fasting Blood Sugar:  126 mg/dL    (Normal: 70 - 100)
HbA1c (Glycosylated Haemoglobin): 6.8%  (Normal: 4.0 - 5.7)
Post Prandial Blood Sugar: 185 mg/dL  (Normal: 70 - 140)
"""

SAMPLE_THYROID_TEXT = """
THYROID FUNCTION TEST
TSH (Thyroid Stimulating Hormone): 5.8 mIU/mL  (0.4 - 4.0)
Free T3: 2.8 pg/mL  (2.0 - 4.4)
Free T4: 1.1 ng/dL  (0.8 - 1.8)
Total T3: 120 ng/dL  (80 - 200)
Total T4: 7.5 ug/dL  (5.1 - 14.1)
"""

SAMPLE_VITAMIN_TEXT = """
VITAMIN PROFILE
Vitamin D (25-OH) Total:   18.5  ng/mL    (30 - 100)
Vitamin B12:               185   pg/mL    (200 - 900)
Serum Ferritin:            15    ng/mL    (20 - 250)
Serum Iron:                45    ug/dL    (60 - 170)
Serum Folate:              4.5   ng/mL    (3.0 - 17.0)
"""


# ---------------------------------------------------------------------------
# MedicalParser (master parser)
# ---------------------------------------------------------------------------


class TestMedicalParser:
    def setup_method(self):
        self.parser = MedicalParser()

    def test_parse_hemoglobin(self):
        results = self.parser.parse("Haemoglobin  14.5  g/dL  13.0 - 17.0")
        assert len(results) >= 1
        hb = next((r for r in results if r.canonical_name == "hemoglobin"), None)
        assert hb is not None
        assert hb.value == pytest.approx(14.5)

    def test_parse_fasting_sugar(self):
        results = self.parser.parse("Fasting Blood Sugar: 95 mg/dL (70 - 100)")
        fbs = next((r for r in results if r.canonical_name == "fasting_glucose"), None)
        assert fbs is not None
        assert fbs.value == pytest.approx(95.0)

    def test_parse_hba1c(self):
        results = self.parser.parse("HbA1c  6.2  %  4.0 - 5.7")
        a1c = next((r for r in results if r.canonical_name == "hba1c"), None)
        assert a1c is not None
        assert a1c.value == pytest.approx(6.2)

    def test_parse_vitamin_d(self):
        results = self.parser.parse("Vitamin D (25-OH): 22 ng/mL (30-100)")
        vd = next((r for r in results if r.canonical_name == "vitamin_d"), None)
        assert vd is not None
        assert vd.value == pytest.approx(22.0)

    def test_parse_tsh(self):
        results = self.parser.parse("TSH  3.5  mIU/mL  0.4-4.0")
        tsh = next((r for r in results if r.canonical_name == "tsh"), None)
        assert tsh is not None
        assert tsh.value == pytest.approx(3.5)

    def test_parse_ldl(self):
        results = self.parser.parse("LDL Cholesterol  130  mg/dL  <100")
        ldl = next((r for r in results if r.canonical_name == "ldl"), None)
        assert ldl is not None
        assert ldl.value == pytest.approx(130.0)

    def test_parse_creatinine(self):
        results = self.parser.parse("Serum Creatinine: 1.1 mg/dL (0.7-1.3)")
        cr = next((r for r in results if r.canonical_name == "creatinine"), None)
        assert cr is not None
        assert cr.value == pytest.approx(1.1)

    def test_parsed_biomarker_to_dict(self):
        bio = ParsedBiomarker(
            test_name="Hemoglobin",
            canonical_name="hemoglobin",
            value=14.5,
            value_raw="14.5",
            unit="g/dL",
            reference_range="13.0 - 17.0",
        )
        d = bio.to_dict()
        assert d["canonical_name"] == "hemoglobin"
        assert d["value"] == 14.5
        assert d["unit"] == "g/dL"


# ---------------------------------------------------------------------------
# CBC Parser
# ---------------------------------------------------------------------------


class TestCBCParser:
    def setup_method(self):
        self.parser = CBCParser()

    def test_parse_full_cbc(self):
        results = self.parser.parse(SAMPLE_CBC_TEXT)
        names = {r.canonical_name for r in results}
        assert "hemoglobin" in names
        assert "rbc" in names
        assert "wbc" in names
        assert "platelets" in names
        assert "mcv" in names

    def test_hemoglobin_value(self):
        results = self.parser.parse(SAMPLE_CBC_TEXT)
        hb = next(r for r in results if r.canonical_name == "hemoglobin")
        assert hb.value == pytest.approx(14.5)

    def test_wbc_value(self):
        results = self.parser.parse(SAMPLE_CBC_TEXT)
        wbc = next(r for r in results if r.canonical_name == "wbc")
        assert wbc.value == pytest.approx(7500.0)

    def test_neutrophils_parsed(self):
        results = self.parser.parse(SAMPLE_CBC_TEXT)
        neut = next((r for r in results if r.canonical_name == "neutrophils"), None)
        assert neut is not None
        assert neut.value == pytest.approx(60.0)

    def test_evaluate_normal_status(self):
        bio = ParsedBiomarker(
            test_name="Hemoglobin",
            canonical_name="hemoglobin",
            value=14.5,
            value_raw="14.5",
            unit="g/dL",
        )
        assert self.parser.evaluate_status(bio) == "normal"

    def test_evaluate_low_status(self):
        bio = ParsedBiomarker(
            test_name="Hemoglobin",
            canonical_name="hemoglobin",
            value=10.0,
            value_raw="10.0",
            unit="g/dL",
        )
        assert self.parser.evaluate_status(bio) == "low"


# ---------------------------------------------------------------------------
# Lipid Profile Parser
# ---------------------------------------------------------------------------


class TestLipidProfileParser:
    def setup_method(self):
        self.parser = LipidProfileParser()

    def test_parse_full_lipid(self):
        results = self.parser.parse(SAMPLE_LIPID_TEXT)
        names = {r.canonical_name for r in results}
        assert "total_cholesterol" in names
        assert "ldl" in names
        assert "hdl" in names
        assert "triglycerides" in names

    def test_total_cholesterol_value(self):
        results = self.parser.parse(SAMPLE_LIPID_TEXT)
        tc = next(r for r in results if r.canonical_name == "total_cholesterol")
        assert tc.value == pytest.approx(220.0)

    def test_ldl_value(self):
        results = self.parser.parse(SAMPLE_LIPID_TEXT)
        ldl = next(r for r in results if r.canonical_name == "ldl")
        assert ldl.value == pytest.approx(145.0)

    def test_triglycerides_value(self):
        results = self.parser.parse(SAMPLE_LIPID_TEXT)
        tg = next(r for r in results if r.canonical_name == "triglycerides")
        assert tg.value == pytest.approx(165.0)

    def test_evaluate_high_ldl(self):
        bio = ParsedBiomarker(
            test_name="LDL",
            canonical_name="ldl",
            value=145.0,
            value_raw="145",
            unit="mg/dL",
        )
        assert self.parser.evaluate_status(bio) == "high"


# ---------------------------------------------------------------------------
# Diabetes Parser
# ---------------------------------------------------------------------------


class TestDiabetesParser:
    def setup_method(self):
        self.parser = DiabetesParser()

    def test_parse_fasting_glucose(self):
        results = self.parser.parse(SAMPLE_DIABETES_TEXT)
        fbs = next((r for r in results if r.canonical_name == "fasting_glucose"), None)
        assert fbs is not None
        assert fbs.value == pytest.approx(126.0)

    def test_parse_hba1c(self):
        results = self.parser.parse(SAMPLE_DIABETES_TEXT)
        a1c = next((r for r in results if r.canonical_name == "hba1c"), None)
        assert a1c is not None
        assert a1c.value == pytest.approx(6.8)

    def test_parse_pp_glucose(self):
        results = self.parser.parse(SAMPLE_DIABETES_TEXT)
        pp = next((r for r in results if r.canonical_name == "pp_glucose"), None)
        assert pp is not None
        assert pp.value == pytest.approx(185.0)


# ---------------------------------------------------------------------------
# Thyroid Parser
# ---------------------------------------------------------------------------


class TestThyroidParser:
    def setup_method(self):
        self.parser = ThyroidParser()

    def test_parse_tsh(self):
        results = self.parser.parse(SAMPLE_THYROID_TEXT)
        tsh = next((r for r in results if r.canonical_name == "tsh"), None)
        assert tsh is not None
        assert tsh.value == pytest.approx(5.8)

    def test_parse_free_t3(self):
        results = self.parser.parse(SAMPLE_THYROID_TEXT)
        ft3 = next((r for r in results if r.canonical_name == "free_t3"), None)
        assert ft3 is not None
        assert ft3.value == pytest.approx(2.8)

    def test_parse_free_t4(self):
        results = self.parser.parse(SAMPLE_THYROID_TEXT)
        ft4 = next((r for r in results if r.canonical_name == "free_t4"), None)
        assert ft4 is not None
        assert ft4.value == pytest.approx(1.1)

    def test_elevated_tsh_status(self):
        bio = ParsedBiomarker(
            test_name="TSH",
            canonical_name="tsh",
            value=5.8,
            value_raw="5.8",
            unit="mIU/mL",
        )
        assert self.parser.evaluate_status(bio) == "high"


# ---------------------------------------------------------------------------
# Vitamin Parser
# ---------------------------------------------------------------------------


class TestVitaminParser:
    def setup_method(self):
        self.parser = VitaminParser()

    def test_parse_vitamin_d(self):
        results = self.parser.parse(SAMPLE_VITAMIN_TEXT)
        vd = next((r for r in results if r.canonical_name == "vitamin_d"), None)
        assert vd is not None
        assert vd.value == pytest.approx(18.5)

    def test_parse_vitamin_b12(self):
        results = self.parser.parse(SAMPLE_VITAMIN_TEXT)
        b12 = next((r for r in results if r.canonical_name == "vitamin_b12"), None)
        assert b12 is not None
        assert b12.value == pytest.approx(185.0)

    def test_parse_ferritin(self):
        results = self.parser.parse(SAMPLE_VITAMIN_TEXT)
        ferr = next((r for r in results if r.canonical_name == "ferritin"), None)
        assert ferr is not None
        assert ferr.value == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# run_all_parsers
# ---------------------------------------------------------------------------


class TestRunAllParsers:
    def test_deduplication(self):
        """When multiple parsers find the same biomarker, only the first is kept."""
        combined_text = SAMPLE_CBC_TEXT + "\n" + SAMPLE_LIPID_TEXT
        results = run_all_parsers(combined_text)
        canonical_names = [r.canonical_name for r in results]
        assert len(canonical_names) == len(set(canonical_names))

    def test_returns_results_from_multiple_parsers(self):
        combined_text = SAMPLE_CBC_TEXT + "\n" + SAMPLE_LIPID_TEXT
        results = run_all_parsers(combined_text)
        names = {r.canonical_name for r in results}
        assert "hemoglobin" in names  # from CBC
        assert "ldl" in names  # from Lipid
