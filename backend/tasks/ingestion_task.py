"""Ingestion Celery task (worker deployments; the API runs the same job in-process)."""
from __future__ import annotations

import asyncio

from backend.worker import celery_app


@celery_app.task(name="backend.tasks.ingestion_task.ingest_cricsheet_task", bind=True, max_retries=3)
def ingest_cricsheet_task(self, source: str = "data/raw/all_json/", incremental: bool = True):
    from backend.database import AsyncSessionLocal
    from backend.jobs import job_ingest

    async def run():
        async with AsyncSessionLocal() as db:
            return await job_ingest(db, source=source, incremental=incremental)

    try:
        return asyncio.run(run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
