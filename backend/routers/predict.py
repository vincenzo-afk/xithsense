"""
Predict router: team, portfolio, captain, differentials, explain
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user, require_premium
from backend.models import User
from backend.schemas import (
    CaptainResponse, DifferentialsResponse, ExplainResponse,
    PredictTeamRequest, PredictTeamResponse,
)
from backend.services.prediction_service import PredictionService

router = APIRouter(prefix="/api/v1/predict", tags=["predict"])


@router.post("/team", response_model=PredictTeamResponse)
async def predict_team(
    body: PredictTeamRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Free tier can only generate 1 team in safe mode
    if user.role == "free":
        if body.count > 1:
            raise HTTPException(
                status_code=402,
                detail={"code": "PREMIUM_REQUIRED", "message": "Multiple teams require Premium subscription"},
            )
        if body.mode != "safe":
            raise HTTPException(
                status_code=402,
                detail={"code": "PREMIUM_REQUIRED", "message": f"Mode '{body.mode}' requires Premium subscription"},
            )

    svc = PredictionService(db)
    result = await svc.generate_team(
        match_id=body.match_id,
        mode=body.mode,
        count=body.count,
        user=user,
    )
    return result


@router.post("/team/portfolio", response_model=dict)
async def predict_portfolio(
    match_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_premium),
):
    """Generate all 4 team modes in one call (Premium only)."""
    svc = PredictionService(db)
    modes = ["safe", "grand_league", "aggressive", "small_league"]
    portfolio = {}
    for mode in modes:
        result = await svc.generate_team(match_id=match_id, mode=mode, count=1, user=user)
        portfolio[mode] = result
    return portfolio


@router.post("/captain", response_model=CaptainResponse)
async def predict_captain(
    match_id: str,
    mode: str = "safe",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = PredictionService(db)
    return await svc.get_captain_options(match_id=match_id, mode=mode, user=user)


@router.get("/differentials/{match_id}", response_model=DifferentialsResponse)
async def get_differentials(
    match_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = PredictionService(db)
    return await svc.get_differentials(match_id=match_id)


@router.get("/explain/{match_id}/{player_id}", response_model=ExplainResponse)
async def explain_player(
    match_id: str,
    player_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = PredictionService(db)
    return await svc.explain_player(match_id=match_id, player_id=player_id)
