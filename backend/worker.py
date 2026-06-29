"""
Celery worker configuration.
"""
from celery import Celery
from backend.config import settings

celery_app = Celery(
    "xithsense",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.tasks.ingestion_task",
        "backend.tasks.feature_task",
        "backend.tasks.retrain_task",
        "backend.tasks.notification_task",
    ],
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
    beat_schedule={
        "ingest-every-hour": {
            "task": "backend.tasks.ingestion_task.ingest_cricsheet_task",
            "schedule": 3600.0,
            "kwargs": {"source": "cricsheet_latest", "incremental": True},
        },
    },
)
