"""Feature-store rebuild Celery task."""
from __future__ import annotations

import asyncio

from backend.worker import celery_app


@celery_app.task(name="backend.tasks.feature_task.rebuild_features_task")
def rebuild_features_task():
    from backend.database import AsyncSessionLocal
    from backend.jobs import job_features

    async def run():
        async with AsyncSessionLocal() as db:
            return await job_features(db)

    return asyncio.run(run())
