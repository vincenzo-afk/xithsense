"""
Chat router: AI assistant (Premium) + session history.
"""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import require_premium
from backend.models import ChatMessage, ChatSession, User
from backend.schemas import ChatMessageOut, ChatRequest, ChatResponse, ChatSessionOut
from backend.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db), user: User = Depends(require_premium)):
    return await ChatService(db).respond(user=user, message=body.message, match_id=body.match_id,
                                         session_id=body.session_id)


@router.get("/sessions", response_model=List[ChatSessionOut])
async def list_sessions(db: AsyncSession = Depends(get_db), user: User = Depends(require_premium)):
    rows = (await db.execute(select(ChatSession).where(ChatSession.user_id == user.id)
                             .order_by(ChatSession.created_at.desc()).limit(30))).scalars().all()
    return [ChatSessionOut.model_validate(s) for s in rows]


async def _own_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> ChatSession:
    s = (await db.execute(select(ChatSession).where(ChatSession.id == session_id,
                                                    ChatSession.user_id == user.id))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Chat session not found"})
    return s


@router.get("/sessions/{session_id}", response_model=List[ChatMessageOut])
async def session_messages(session_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                           user: User = Depends(require_premium)):
    await _own_session(db, user, session_id)
    rows = (await db.execute(select(ChatMessage).where(ChatMessage.session_id == session_id)
                             .order_by(ChatMessage.created_at))).scalars().all()
    return [ChatMessageOut.model_validate(m) for m in rows]


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                         user: User = Depends(require_premium)):
    await _own_session(db, user, session_id)
    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.commit()
