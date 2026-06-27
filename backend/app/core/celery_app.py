from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "nutrimed_worker",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    # Task routing: report-related tasks go to the reports queue,
    # AI-heavy tasks go to the ai queue.
    task_routes={
        "tasks.process_ocr": {"queue": "reports"},
        "tasks.extract_biomarkers": {"queue": "reports"},
        "tasks.analyze_biomarkers": {"queue": "ai"},
        "tasks.generate_recommendations": {"queue": "ai"},
        "tasks.generate_pdf": {"queue": "reports"},
    },
    # Hard time limit kills the worker process; soft limit raises SoftTimeLimitExceeded.
    task_time_limit=600,
    task_soft_time_limit=540,
)

celery_app.autodiscover_tasks([
    "app.workers",
])
