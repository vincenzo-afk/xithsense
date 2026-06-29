"""
Players router: search, detail, matchups
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import Player, RollingFeature, MatchupStat, User
from backend.schemas import (
    MatchupOut, MatchupsResponse, PlayerDetailOut, PlayerOut,
    PlayerSearchResponse, RecentForm,
)

router = APIRouter(prefix="/api/v1/players", tags=["players"])


@router.get("/search", response_model=PlayerSearchResponse)
async def search_players(
    q: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Player).where(Player.is_active == True)
    if q:
        query = query.where(func.lower(Player.full_name).contains(q.lower()))
    if role:
        query = query.where(Player.primary_role == role.upper())
    query = query.limit(limit)

    result = await db.execute(query)
    players = result.scalars().all()
    return PlayerSearchResponse(players=[PlayerOut.model_validate(p) for p in players])


@router.get("/{player_id}", response_model=PlayerDetailOut)
async def get_player(
    player_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail={"code": "PLAYER_NOT_FOUND", "message": f"Player {player_id} not found"})

    # Fetch rolling features for recent form
    rf_result = await db.execute(
        select(RollingFeature)
        .where(RollingFeature.player_id == player_id)
        .order_by(RollingFeature.as_of_date.desc())
        .limit(3)
    )
    features = rf_result.scalars().all()

    form = None
    if features:
        windows = {f.window_matches: f for f in features}
        w5 = windows.get(5) or windows.get(3) or features[0]
        w10 = windows.get(10) or w5
        w3 = windows.get(3) or w5
        form = RecentForm(
            last_3_fp_avg=float(w3.fp_avg) if w3.fp_avg else None,
            last_5_fp_avg=float(w5.fp_avg) if w5.fp_avg else None,
            last_10_fp_avg=float(w10.fp_avg) if w10.fp_avg else None,
            fp_ceiling=float(w10.fp_ceiling) if w10.fp_ceiling else None,
            fp_floor=float(w10.fp_floor) if w10.fp_floor else None,
            fp_consistency=float(w10.fp_consistency) if w10.fp_consistency else None,
        )

    return PlayerDetailOut(
        **PlayerOut.model_validate(player).model_dump(),
        recent_form=form,
    )


@router.get("/{player_id}/matchups", response_model=MatchupsResponse)
async def get_matchups(
    player_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MatchupStat).where(MatchupStat.player_id == player_id)
    )
    stats = result.scalars().all()

    return MatchupsResponse(
        matchups=[
            MatchupOut(
                bowler_type=s.bowler_type,
                balls_faced=s.balls_faced,
                strike_rate=float(s.strike_rate) if s.strike_rate else None,
                avg_runs=float(s.avg_runs) if s.avg_runs else None,
                dismissal_rate=(s.dismissals / s.balls_faced) if s.balls_faced else None,
                boundary_rate=float(s.boundary_pct) if s.boundary_pct else None,
            )
            for s in stats
        ]
    )
