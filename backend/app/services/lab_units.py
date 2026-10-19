"""
Bring blood counts reported in different units onto one scale.

Labs write the same white-cell count as 7,100 /cumm, 7.1 x10^3/uL or
7.1 x10^9/L, platelets as 250,000 /uL, 250 x10^3/uL or 2.5 lakhs/cumm, and
hemoglobin as 11.2 g/dL or 112 g/L. The rule engine's ranges use one canonical
unit per marker, so a value must be converted before it is compared --
otherwise a normal count reported in thousands reads as dangerously low.

The scale is taken, in order of trust, from:
  1. the unit printed next to the value, if recognised and the converted value
     is physiologically plausible (OCR output from before this module filled
     in default units when none was printed, so a unit alone is not trusted);
  2. the reference range printed on the report, whose midpoint is a normal
     value and so never ambiguous;
  3. the value's own magnitude, but only where the scales cannot overlap.
Otherwise the value is reported as unclear rather than guessed: platelets of
"7" could be 7 lakhs (high) or 7 thousand (critically low).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

#: Canonical unit per scale-sensitive marker: the unit REFERENCE_RANGES uses.
CANONICAL_UNITS: dict[str, str] = {
    "wbc": "cells/µL",
    "platelets": "cells/µL",
    "rbc": "million/µL",
    "hemoglobin": "g/dL",
}

#: Canonical values outside these bounds are not physiologically possible, so
#: the unit or scale that produced them is wrong.
_PLAUSIBLE: dict[str, tuple[float, float]] = {
    "wbc": (100, 500_000),
    "platelets": (1_000, 3_000_000),
    "rbc": (0.5, 10),
    "hemoglobin": (2, 25),
}

_THOUSANDS_PER_UL = r"x?10\^?3/ul|k/ul|thou(?:sand)?s?/ul|10e3/ul|x?10\^?9/l|g/l"
_PER_UL = r"/?ul"

#: Recognised units per marker: (pattern on the normalised unit, factor to the
#: canonical unit, display label).
_UNITS: dict[str, list[tuple[str, float, str]]] = {
    "wbc": [
        (_THOUSANDS_PER_UL, 1_000, "×10³/µL"),
        (_PER_UL, 1, "cells/µL"),
    ],
    "platelets": [
        (r"la(?:kh|c)s?/ul", 100_000, "lakhs/µL"),
        (_THOUSANDS_PER_UL, 1_000, "×10³/µL"),
        (_PER_UL, 1, "cells/µL"),
    ],
    "rbc": [
        (r"x?10\^?6/ul|mill?(?:ion)?s?/ul|m/ul|x?10\^?12/l|t/l", 1, "million/µL"),
        (_PER_UL, 1e-6, "cells/µL"),
    ],
    "hemoglobin": [
        (r"gm?s?/dl|gm?s?%|g/100ml", 1, "g/dL"),
        (r"gm?s?/l", 0.1, "g/L"),
        (r"mmol/l", 1.611, "mmol/L"),
    ],
}

_SUPERSCRIPTS = str.maketrans({"³": "^3", "⁶": "^6", "⁹": "^9", "¹": "^1", "²": "2", "⁰": "0"})


def _normalise_unit(unit: str) -> str:
    u = (unit or "").translate(_SUPERSCRIPTS).lower()
    u = u.replace("µ", "u").replace("μ", "u").replace("×", "x").replace("*", "^")
    u = re.sub(r"\s+", "", u)
    u = re.sub(r"cells?", "", u)
    # Per cubic millimetre is per microlitre.
    return re.sub(r"mm\^?3|cu\.?mm|cmm|mcl", "ul", u)


def _factor_from_unit(marker: str, unit: str) -> float | None:
    key = _normalise_unit(unit)
    if not key:
        return None
    for pattern, factor, _label in _UNITS[marker]:
        if re.fullmatch(pattern, key):
            return factor
    return None


def _factor_from_magnitude(marker: str, value: float) -> float | None:
    """The scale a value of this size must be on, or None where scales overlap."""
    if marker == "wbc":
        if value <= 100:
            return 1_000  # 7.1 -> x10^3/µL
        return 1 if value >= 1_000 else None
    if marker == "platelets":
        if value < 5:
            return 100_000  # 2.5 -> lakhs
        if 10 <= value < 1_000:
            return 1_000  # 250 -> x10^3/µL
        return 1 if value >= 1_000 else None  # 5-10: lakhs and thousands overlap
    if marker == "rbc":
        if value < 20:
            return 1  # 4.8 -> million/µL
        return 1e-6 if value >= 100_000 else None
    if marker == "hemoglobin":
        if value <= 25:
            return 1  # g/dL
        return 0.1 if 30 <= value <= 250 else None  # g/L
    return None


def _label(marker: str, factor: float) -> str:
    for _pattern, f, label in _UNITS[marker]:
        if math.isclose(f, factor):
            return label
    return CANONICAL_UNITS[marker]


def parse_range(text: str | None) -> tuple[float, float] | None:
    """A printed "low - high" range, or None if absent or malformed."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\s*", text or "", re.IGNORECASE)
    if not m:
        return None
    low, high = float(m.group(1)), float(m.group(2))
    return (low, high) if low < high else None


@dataclass(frozen=True)
class Conversion:
    #: Value in the canonical unit; None when the scale is unclear.
    value: float | None
    #: reported value x factor = canonical value.
    factor: float | None
    #: "unit", "range", "magnitude", "unchanged" (not scale-sensitive) or "unclear".
    basis: str
    #: Display label for the reported value's unit ("" when unknown).
    reported_unit: str


def to_canonical(
    marker: str,
    value: float | None,
    unit: str = "",
    printed_range: tuple[float, float] | None = None,
) -> Conversion:
    """Convert a reported value to the marker's canonical unit."""
    if marker not in CANONICAL_UNITS or value is None:
        return Conversion(value, 1.0, "unchanged", unit or "")

    low, high = _PLAUSIBLE[marker]

    def plausible(factor: float | None) -> bool:
        return factor is not None and low <= value * factor <= high

    candidates = [("unit", _factor_from_unit(marker, unit))]
    if printed_range:
        candidates.append(("range", _factor_from_magnitude(marker, sum(printed_range) / 2)))
    candidates.append(("magnitude", _factor_from_magnitude(marker, value)))

    for basis, factor in candidates:
        if plausible(factor):
            return Conversion(value * factor, factor, basis, _label(marker, factor))
    return Conversion(None, None, "unclear", unit or "")


def range_matches_scale(marker: str, printed_range: tuple[float, float], factor: float | None) -> bool:
    """
    Whether a printed range is on the same scale as the reported value, i.e.
    whether the value can be judged against it directly. Rejects ranges the
    old OCR output filled in from its own defaults (a "4000 - 11000" beside a
    value of 7.1).
    """
    if marker not in CANONICAL_UNITS:
        return False
    range_factor = _factor_from_magnitude(marker, sum(printed_range) / 2)
    return range_factor is not None and factor is not None and math.isclose(range_factor, factor)
