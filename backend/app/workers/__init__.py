# Import all worker modules so Celery autodiscover picks up their tasks.
from app.workers import (
    analysis_worker,  # noqa: F401
    extraction_worker,  # noqa: F401
    ocr_worker,  # noqa: F401
    pdf_worker,  # noqa: F401
    recommendation_worker,  # noqa: F401
)
