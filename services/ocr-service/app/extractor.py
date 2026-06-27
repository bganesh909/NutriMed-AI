"""OCR text extraction using PaddleOCR and pdfplumber.

Handles both image files and PDFs (digital + scanned).
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pdfplumber
from paddleocr import PaddleOCR
from PIL import Image

from app.schemas import TextBlock

logger = logging.getLogger(__name__)

# Module-level singleton to avoid re-loading models on every call
_ocr_instance: Optional[PaddleOCR] = None


def _get_ocr() -> PaddleOCR:
    """Return a cached PaddleOCR instance."""
    global _ocr_instance
    if _ocr_instance is None:
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
    ocr = _get_ocr()

    if isinstance(image_input, str):
        img = cv2.imread(image_input)
        if img is None:
            raise FileNotFoundError(f"Cannot read image at {image_input}")
    else:
        img = image_input

    results = ocr.ocr(img, cls=True)
    blocks = _parse_paddle_results(results)
    return _sort_blocks(blocks)


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
        blocks = [
            TextBlock(text=line.strip(), confidence=1.0)
            for line in digital_text.splitlines()
            if line.strip()
        ]
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
