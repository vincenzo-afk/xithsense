"""
Matches router: upcoming, detail, live WebSocket
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import Match, User
from backend.schemas import MatchListResponse, MatchOut

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


@router.get("/upcoming", response_model=MatchListResponse)
async def list_upcoming(
    format: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Match).where(Match.is_complete == False)
    if format:
        q = q.where(Match.match_type == format)
    q = q.order_by(Match.match_date).offset(offset).limit(limit)

    result = await db.execute(q)
    matches = result.scalars().all()

    count_q = select(func.count()).select_from(Match).where(Match.is_complete == False)
    if format:
        count_q = count_q.where(Match.match_type == format)
    total = (await db.execute(count_q)).scalar_one()

    match_outs = [
        MatchOut(
            **{c.key: getattr(m, c.key) for c in Match.__table__.columns},
            prediction_ready=True,
            playing_xi_confirmed=False,
        )
        for m in matches
    ]
    return MatchListResponse(matches=match_outs, total=total)


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(
    match_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail={"code": "MATCH_NOT_FOUND", "message": f"Match {match_id} not found"})
    return MatchOut(
        **{c.key: getattr(match, c.key) for c in Match.__table__.columns},
        prediction_ready=True,
        playing_xi_confirmed=False,
    )


@router.websocket("/{match_id}/live")
async def live_feed(websocket: WebSocket, match_id: str):
    """WebSocket endpoint for live match intelligence."""
    await websocket.accept()
    try:
        import asyncio, json, random
        # Simulate live updates — in production, events come from Celery + Redis pub/sub
        over = 0
        while True:
            update = {
                "match_id": match_id,
                "over": over,
                "win_probability": {"team_a": round(random.uniform(30, 70), 1)},
                "live_fp": {},
            }
            await websocket.send_text(json.dumps(update))
            await asyncio.sleep(10)
            over += 1
    except WebSocketDisconnect:
        pass
