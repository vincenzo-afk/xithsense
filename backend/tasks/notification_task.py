"""Notification delivery Celery task: marks in-app notifications sent; Telegram when configured."""
from __future__ import annotations

import asyncio
import logging

from backend.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="backend.tasks.notification_task.deliver_pending", bind=True, max_retries=2)
def deliver_pending(self):
    from datetime import datetime, timezone
    from sqlalchemy import select
    from backend.config import settings
    from backend.database import AsyncSessionLocal
    from backend.models import Notification

    async def run():
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(Notification).where(Notification.status == "pending").limit(500))).scalars().all()
            for n in rows:
                if n.channel == "telegram" and not settings.TELEGRAM_BOT_TOKEN:
                    n.status, n.error_message = "failed", "TELEGRAM_BOT_TOKEN not configured"
                    continue
                n.status, n.sent_at = "sent", datetime.now(timezone.utc)
            await db.commit()
            return len(rows)

    return asyncio.run(run())
