"""Ingestion Celery task."""
from __future__ import annotations
import asyncio
from backend.worker import celery_app


@celery_app.task(name="backend.tasks.ingestion_task.ingest_cricsheet_task", bind=True)
def ingest_cricsheet_task(self, source: str = "data/raw/all_json/", incremental: bool = True):
    """Celery wrapper for the async ingest function."""
    try:
        from scripts.ingest_cricsheet import ingest
        asyncio.run(ingest(source, incremental))
        return {"status": "success"}
    except Exception as exc:
        self.retry(exc=exc, countdown=60, max_retries=3)
