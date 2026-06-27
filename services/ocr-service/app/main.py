"""FastAPI application for the OCR & Biomarker Extraction Service.

Endpoints:
    POST /ocr/extract        - Accept file upload (image or PDF)
    POST /ocr/extract-text   - Accept base64-encoded image
    GET  /health             - Health check
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.pipeline import run_pipeline_from_base64, run_pipeline_from_file
from app.schemas import (
    Base64ImageRequest,
    HealthResponse,
    PipelineResponse,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("ocr-service")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NutriMed AI - OCR & Biomarker Extraction Service",
    description=(
        "Extracts text from medical lab report images/PDFs using PaddleOCR "
        "and parses biomarker values into structured JSON."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/tiff",
    "image/webp",
    "application/pdf",
}

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@app.post("/ocr/extract", response_model=PipelineResponse)
async def extract_from_upload(file: UploadFile = File(...)):
    """Extract biomarkers from an uploaded image or PDF file.

    Accepts JPEG, PNG, BMP, TIFF, WebP images and PDF documents.
    Maximum file size: 20 MB.
    """
    # Validate content type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        # Fall back to extension check
        ext = Path(file.filename or "").suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".pdf"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {content_type}. "
                       f"Accepted types: JPEG, PNG, BMP, TIFF, WebP, PDF.",
            )

    # Read and validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB.",
        )

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Write to temp file
    suffix = Path(file.filename or "upload.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = run_pipeline_from_file(tmp_path, filename=file.filename)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Pipeline error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {exc}",
        ) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/ocr/extract-text", response_model=PipelineResponse)
async def extract_from_base64(request: Base64ImageRequest):
    """Extract biomarkers from a base64-encoded image.

    The ``image_base64`` field may include a data URI prefix
    (e.g. ``data:image/png;base64,...``), which will be stripped automatically.
    """
    if not request.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 field is required.")

    try:
        result = run_pipeline_from_base64(
            request.image_base64,
            filename=request.filename,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Pipeline error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {exc}",
        ) from exc


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok", service="ocr-service", version="1.0.0")
