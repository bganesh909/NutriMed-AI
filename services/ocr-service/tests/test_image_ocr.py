"""
Tests for the image / scanned-document OCR path.

These exercise the Tesseract backend, which is the default engine when
PaddleOCR is not installed (e.g. on Apple Silicon).
"""

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.extractor import available_ocr_engine, extract_from_image
from app.pipeline import run_pipeline_from_file


REPORT_LINES = [
    "CITY DIAGNOSTIC LABORATORY",
    "Patient: Test Patient   Age: 30 / Male",
    "",
    "TEST NAME            RESULT   UNIT      REFERENCE",
    "Haemoglobin          11.2     g/dL      13.0 - 17.0",
    "Vitamin D (25-OH)    14.5     ng/mL     30 - 100",
    "Fasting Glucose      118      mg/dL     70 - 100",
    "TSH                  5.8      uIU/mL    0.4 - 4.0",
]


def _font():
    try:
        return ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Courier New.ttf", 26
        )
    except OSError:
        try:
            return ImageFont.truetype("DejaVuSansMono.ttf", 26)
        except OSError:
            return ImageFont.load_default()


@pytest.fixture(scope="module")
def report_image(tmp_path_factory) -> str:
    """Render a small tabular lab report to a PNG and return its path."""
    img = Image.new("RGB", (1100, 480), "white")
    draw = ImageDraw.Draw(img)
    font = _font()
    y = 20
    for line in REPORT_LINES:
        draw.text((40, y), line, fill="black", font=font)
        y += 50
    path = tmp_path_factory.mktemp("ocr") / "report.png"
    img.save(path)
    return str(path)


pytestmark = pytest.mark.skipif(
    available_ocr_engine() is None,
    reason="no OCR engine installed (paddleocr or pytesseract)",
)


class TestExtractFromImage:
    def test_engine_is_detected(self):
        assert available_ocr_engine() in ("paddleocr", "tesseract")

    def test_returns_one_block_per_line(self, report_image):
        blocks = extract_from_image(report_image)
        assert len(blocks) >= 6
        # Each row must stay on one line for the tabular parsers to work.
        joined = " | ".join(b.text for b in blocks)
        assert "Haemoglobin" in joined
        assert any("11.2" in b.text and "Haemoglobin" in b.text for b in blocks)

    def test_blocks_carry_confidence_and_bbox(self, report_image):
        blocks = extract_from_image(report_image)
        for b in blocks:
            assert 0.0 <= b.confidence <= 1.0
            assert b.bbox is not None and len(b.bbox) == 4

    def test_accepts_numpy_array(self, report_image):
        arr = np.array(Image.open(report_image).convert("RGB"))
        blocks = extract_from_image(arr)
        assert any("Haemoglobin" in b.text for b in blocks)

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            extract_from_image("/nonexistent/does-not-exist.png")


class TestImagePipeline:
    """The image must flow all the way through to classified biomarkers."""

    def test_extracts_and_classifies_biomarkers(self, report_image):
        result = run_pipeline_from_file(report_image, filename="report.png")
        found = {b.name: b for b in result.biomarkers.biomarkers}

        assert found["hemoglobin"].value == pytest.approx(11.2)
        assert found["hemoglobin"].status == "low"

        # The "(25-OH)" in the assay name must not be read as the result.
        assert found["vitamin_d"].value == pytest.approx(14.5)
        assert found["vitamin_d"].status == "low"

        assert found["fasting_glucose"].value == pytest.approx(118.0)
        assert found["fasting_glucose"].status == "high"

        assert found["tsh"].value == pytest.approx(5.8)
        assert found["tsh"].status == "high"
