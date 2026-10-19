"""Blood counts printed on different scales: units captured, nothing invented."""

import pytest

from app.biomarker_engine import CBCParser, evaluate_status_for
from app.medical_parser import MedicalParser
from app.pipeline import _validate_biomarker


def _parse(text: str, name: str):
    return next(b for b in CBCParser().parse(text) if b.canonical_name == name)


@pytest.mark.parametrize(
    ("line", "name", "value", "unit", "ref_range"),
    [
        ("WBC Count   7.1   10^3/uL   4.0 - 11.0", "wbc", 7.1, "10^3/uL", "4.0 - 11.0"),
        ("Total Leucocyte Count  7,500  cells/cumm  4,000 - 11,000", "wbc", 7500, "cells/cumm", "4000 - 11000"),
        ("WBC  7.1 x10³/µL", "wbc", 7.1, "x10³/µL", ""),
        ("Platelet Count  2,50,000  /cumm  1,50,000 - 4,50,000", "platelets", 250000, "/cumm", "150000 - 450000"),
        ("Platelet Count  2.5  lakhs/cumm  1.5 - 4.5", "platelets", 2.5, "lakhs/cumm", "1.5 - 4.5"),
        ("Platelets  250  K/uL  150 - 400", "platelets", 250, "K/uL", "150 - 400"),
        ("RBC Count  4.8  mill/cumm  4.5 - 5.5", "rbc", 4.8, "mill/cumm", "4.5 - 5.5"),
        ("Hemoglobin  112  g/L  130 - 170", "hemoglobin", 112, "g/L", "130 - 170"),
    ],
)
def test_counts_keep_the_printed_unit_and_range(line, name, value, unit, ref_range):
    bio = _parse(line, name)
    assert bio.value == pytest.approx(value)
    assert bio.unit == unit
    assert bio.reference_range == ref_range


def test_no_unit_or_range_is_invented():
    bio = _parse("WBC Count 7.1", "wbc")
    assert bio.unit == ""
    assert bio.reference_range == ""


def test_count_without_its_scale_is_unknown_not_low():
    # 7.1 is low only if the unit is /cumm; with nothing printed, don't guess.
    assert evaluate_status_for(_parse("WBC Count 7.1", "wbc")) == "unknown"
    # With the lab's range printed, its verdict stands.
    assert evaluate_status_for(_parse("WBC Count 7.1 10^3/uL 4.0 - 11.0", "wbc")) == "normal"
    assert evaluate_status_for(_parse("WBC Count 7500 /cumm", "wbc")) == "normal"


def test_counts_in_thousands_are_not_suspect():
    for line, name in (("WBC 7.1 10^3/uL", "wbc"), ("Platelets 250 K/uL", "platelets")):
        valid, warning = _validate_biomarker(_parse(line, name))
        assert valid, warning


def test_generic_parser_reads_grouped_counts():
    results = {b.canonical_name: b for b in MedicalParser().parse("Platelet Count: 2,50,000 /cumm")}
    assert results["platelets"].value == pytest.approx(250000)
    assert results["platelets"].unit == "/cumm"


def test_indian_digit_grouping_survives_normalisation():
    from app.normalizer import fix_ocr_errors

    assert fix_ocr_errors("Platelet Count 2,50,000 /cumm 1,50,000 - 4,50,000") == (
        "Platelet Count 2,50,000 /cumm 1,50,000 - 4,50,000"
    )
    # A real decimal comma is still repaired.
    assert fix_ocr_errors("Hemoglobin 12,5 g/dL") == "Hemoglobin 12.5 g/dL"
