# Import all worker modules so Celery autodiscover picks up their tasks.
from app.workers import ocr_worker  # noqa: F401
from app.workers import extraction_worker  # noqa: F401
from app.workers import analysis_worker  # noqa: F401
from app.workers import recommendation_worker  # noqa: F401
from app.workers import pdf_worker  # noqa: F401
