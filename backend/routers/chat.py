"""
Chat router: AI assistant endpoint
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import User, ChatSession, ChatMessage
from backend.schemas import ChatRequest, ChatResponse
from backend.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

FREE_CHAT_LIMIT = 5


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Free users: 5 messages per match session
    if user.role == "free" and body.match_id:
        count_q = (
            select(func.count(ChatMessage.id))
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                ChatSession.user_id == user.id,
                ChatSession.match_id == body.match_id,
                ChatMessage.role == "user",
            )
        )
        count = (await db.execute(count_q)).scalar_one()
        if count >= FREE_CHAT_LIMIT:
            raise HTTPException(
                status_code=402,
                detail={"code": "CHAT_LIMIT_REACHED", "message": f"Free users are limited to {FREE_CHAT_LIMIT} messages per match"},
            )

    svc = ChatService(db)
    return await svc.respond(
        user=user,
        message=body.message,
        match_id=body.match_id,
        session_id=body.session_id,
    )
