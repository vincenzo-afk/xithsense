"""Retrain Celery task."""
from __future__ import annotations

import asyncio

from backend.worker import celery_app


@celery_app.task(name="backend.tasks.retrain_task.retrain_models_task", bind=True, max_retries=2)
def retrain_models_task(self, format: str = "T20", model_ids: list | None = None):
    from backend.database import AsyncSessionLocal
    from backend.jobs import job_retrain

    async def run():
        async with AsyncSessionLocal() as db:
            return await job_retrain(db, format=format)

    try:
        return asyncio.run(run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)
