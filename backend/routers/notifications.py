"""
Notifications router: in-app inbox + delivery preferences (NOTIFICATION_SPEC).
"""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user, has_premium_access
from backend.models import Notification, User
from backend.schemas import NotificationOut, NotificationPrefs

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (await db.execute(select(Notification).where(Notification.user_id == user.id)
                             .order_by(Notification.created_at.desc()).limit(30))).scalars().all()
    unread = (await db.execute(select(func.count()).select_from(Notification).where(
        Notification.user_id == user.id, Notification.is_read.is_(False)))).scalar_one()
    return {"notifications": [NotificationOut.model_validate(n) for n in rows], "unread": unread}


@router.post("/read", status_code=204)
async def mark_all_read(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    await db.commit()


@router.post("/{notification_id}/read", status_code=204)
async def mark_read(notification_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                    user: User = Depends(get_current_user)):
    await db.execute(update(Notification).where(Notification.id == notification_id,
                                                Notification.user_id == user.id).values(is_read=True))
    await db.commit()


@router.get("/preferences", response_model=NotificationPrefs)
async def get_prefs(user: User = Depends(get_current_user)):
    return NotificationPrefs(**(user.notification_prefs or {}))


@router.patch("/preferences", response_model=NotificationPrefs)
async def update_prefs(body: NotificationPrefs, db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    prefs = body.model_dump()
    if not await has_premium_access(db, user):
        # Free users may only use email (FEATURE_GATING_RULES)
        prefs["telegram_enabled"] = False
        prefs["push_enabled"] = False
    user.notification_prefs = prefs
    await db.commit()
    return NotificationPrefs(**prefs)
