"""OCR text extraction using pdfplumber, PaddleOCR and Tesseract.

Handles both image files and PDFs (digital + scanned). Digital PDFs are read
directly with pdfplumber. Images and scanned PDFs go through an OCR engine:
PaddleOCR when installed, otherwise Tesseract via pytesseract.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import numpy as np
import pdfplumber

from app.schemas import TextBlock

logger = logging.getLogger(__name__)

# Module-level singleton to avoid re-loading models on every call.
# PaddleOCR/cv2 are imported lazily so the service can run (digital-PDF path)
# without the heavy paddlepaddle dependency installed.
_ocr_instance: object | None = None


def _paddle_available() -> bool:
    """True when PaddleOCR can be imported."""
    try:
        import paddleocr  # noqa: F401
    except Exception:
        return False
    return True


def _tesseract_available() -> bool:
    """True when pytesseract and the tesseract binary are both usable."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


def available_ocr_engine() -> str | None:
    """Name of the OCR engine that will be used for images, or None."""
    if _paddle_available():
        return "paddleocr"
    if _tesseract_available():
        return "tesseract"
    return None


def _get_ocr() -> object:
    """Return a cached PaddleOCR instance (lazily imported)."""
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR

        _ocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            show_log=False,
            use_gpu=False,
        )
    return _ocr_instance


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_from_image(image_input: str | np.ndarray) -> list[TextBlock]:
    """Extract text blocks from an image file path or numpy array.

    Parameters
    ----------
    image_input : str | np.ndarray
        File path to the image, or a preprocessed numpy array.

    Returns
    -------
    list[TextBlock]
        Text blocks sorted top-to-bottom, left-to-right.
    """
    engine = available_ocr_engine()
    if engine is None:
        raise RuntimeError(
            "Image/scanned-PDF OCR needs an OCR engine. Install either "
            "'paddleocr + paddlepaddle' or 'pytesseract' plus the tesseract "
            "binary, or upload a digital (text-based) PDF instead."
        )

    if engine == "paddleocr":
        import cv2

        ocr = _get_ocr()
        if isinstance(image_input, str):
            img = cv2.imread(image_input)
            if img is None:
                raise FileNotFoundError(f"Cannot read image at {image_input}")
        else:
            img = image_input

        results = ocr.ocr(img, cls=True)
        return _sort_blocks(_parse_paddle_results(results))

    return _sort_blocks(_extract_with_tesseract(image_input))


def _extract_with_tesseract(image_input: str | np.ndarray) -> list[TextBlock]:
    """
    OCR an image with Tesseract, grouping words into one TextBlock per line.

    Lab reports are tabular, so keeping a line intact ("Hemoglobin 11.2 g/dL
    13.0 - 17.0") is what the downstream parsers expect.
    """
    import pytesseract
    from PIL import Image

    if isinstance(image_input, str):
        path = Path(image_input)
        if not path.exists():
            raise FileNotFoundError(f"Cannot read image at {image_input}")
        img = Image.open(image_input)
    elif isinstance(image_input, np.ndarray):
        arr = image_input
        # Preprocessed arrays arrive as BGR (cv2) or single-channel.
        if arr.ndim == 3 and arr.shape[2] == 3:
            arr = arr[:, :, ::-1]
        img = Image.fromarray(arr.astype("uint8"))
    else:
        img = image_input

    # --psm 6: assume a uniform block of text, which suits tabular reports.
    data = pytesseract.image_to_data(img, config="--psm 6", output_type=pytesseract.Output.DICT)

    lines: dict[tuple[int, int, int], list[int]] = {}
    for i, text in enumerate(data["text"]):
        if not text or not text.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(i)

    blocks: list[TextBlock] = []
    for key in sorted(lines):
        idxs = lines[key]
        words = [data["text"][i].strip() for i in idxs]
        confs = [float(data["conf"][i]) for i in idxs if float(data["conf"][i]) >= 0]
        if not words:
            continue

        x1 = min(data["left"][i] for i in idxs)
        y1 = min(data["top"][i] for i in idxs)
        x2 = max(data["left"][i] + data["width"][i] for i in idxs)
        y2 = max(data["top"][i] + data["height"][i] for i in idxs)

        # Tesseract reports confidence as 0-100; TextBlock wants 0-1.
        confidence = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        blocks.append(
            TextBlock(
                text=" ".join(words),
                confidence=max(0.0, min(1.0, confidence)),
                bbox=[[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
            )
        )
    return blocks


def extract_from_pdf(pdf_path: str) -> tuple[list[TextBlock], str]:
    """Extract text from a PDF, trying digital extraction first.

    For digital (text-based) PDFs, uses pdfplumber for accurate extraction.
    For scanned PDFs (when pdfplumber yields little text), falls back to
    PaddleOCR on rendered page images.

    Returns
    -------
    tuple[list[TextBlock], str]
        (text_blocks, raw_full_text)
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    digital_text = _extract_pdf_digital(pdf_path)

    # Heuristic: if pdfplumber got a decent amount of text, use it
    if len(digital_text.strip()) > 100:
        logger.info("PDF treated as digital text (%d chars)", len(digital_text))
        blocks = [TextBlock(text=line.strip(), confidence=1.0) for line in digital_text.splitlines() if line.strip()]
        return _sort_blocks(blocks), digital_text

    # Fall back to OCR on page images
    logger.info("PDF appears scanned, falling back to PaddleOCR")
    return _extract_pdf_scanned(pdf_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_pdf_digital(pdf_path: str) -> str:
    """Use pdfplumber to extract text from a digital PDF."""
    pages_text: list[str] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                # Also try extracting tables
                tables = page.extract_tables() or []
                table_text_parts: list[str] = []
                for table in tables:
                    for row in table:
                        cells = [str(c).strip() if c else "" for c in row]
                        table_text_parts.append("  ".join(cells))
                combined = text
                if table_text_parts:
                    combined += "\n" + "\n".join(table_text_parts)
                pages_text.append(combined)
    except Exception:
        logger.warning("pdfplumber extraction failed", exc_info=True)
        return ""
    return "\n\n".join(pages_text)


def _extract_pdf_scanned(pdf_path: str) -> tuple[list[TextBlock], str]:
    """Render each PDF page to an image and run PaddleOCR."""
    all_blocks: list[TextBlock] = []
    all_text_parts: list[str] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_image = page.to_image(resolution=300)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    page_image.save(tmp.name)
                    tmp_path = tmp.name

                blocks = extract_from_image(tmp_path)
                all_blocks.extend(blocks)
                page_text = " ".join(b.text for b in blocks)
                all_text_parts.append(page_text)

                # Clean up
                Path(tmp_path).unlink(missing_ok=True)
                logger.debug("OCR page %d: %d blocks", page_num + 1, len(blocks))
    except Exception:
        logger.error("Scanned PDF OCR failed", exc_info=True)

    return _sort_blocks(all_blocks), "\n\n".join(all_text_parts)


def _parse_paddle_results(results: list) -> list[TextBlock]:
    """Convert PaddleOCR raw output into TextBlock list."""
    blocks: list[TextBlock] = []
    if not results:
        return blocks

    for page_result in results:
        if not page_result:
            continue
        for detection in page_result:
            if not detection or len(detection) < 2:
                continue
            bbox_raw = detection[0]
            text_conf = detection[1]
            text = str(text_conf[0]) if isinstance(text_conf, (list, tuple)) else str(text_conf)
            confidence = float(text_conf[1]) if isinstance(text_conf, (list, tuple)) and len(text_conf) > 1 else 0.0

            # Convert bbox to list[list[int]]
            bbox: list[list[int]] = []
            try:
                for point in bbox_raw:
                    bbox.append([int(point[0]), int(point[1])])
            except (TypeError, IndexError):
                bbox = []

            blocks.append(TextBlock(text=text, confidence=confidence, bbox=bbox if bbox else None))

    return blocks


def _sort_blocks(blocks: list[TextBlock]) -> list[TextBlock]:
    """Sort text blocks top-to-bottom, then left-to-right.

    Uses a tolerance band so items on roughly the same line group together.
    """
    if not blocks:
        return blocks

    def sort_key(block: TextBlock) -> tuple[int, int]:
        if block.bbox and len(block.bbox) >= 2:
            y = block.bbox[0][1]
            x = block.bbox[0][0]
            # Round y to nearest 20px band for grouping same-line items
            return (y // 20, x)
        return (0, 0)

    return sorted(blocks, key=sort_key)
