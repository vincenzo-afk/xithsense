"""
Predict router: team, portfolio, captain, differentials, explain.

Gating (FEATURE_GATING_RULES): free users get one Safe-mode team and basic
explanations (5 per match); Premium unlocks all modes, multi-team, portfolio,
differentials and full explanations.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import cache_get, cache_set
from backend.database import get_db
from backend.dependencies import get_current_user, has_premium_access, require_premium
from backend.models import User
from backend.schemas import (
    CaptainResponse, DifferentialsResponse, ExplainResponse, MatchRequest, PortfolioRequest,
    PredictTeamRequest, PredictTeamResponse,
)
from backend.services.prediction_service import PredictionService

router = APIRouter(prefix="/api/v1/predict", tags=["predict"])
explain_router = APIRouter(prefix="/api/v1/explain", tags=["predict"])

FREE_EXPLAIN_LIMIT = 5


def _premium_required(feature: str, message: str) -> HTTPException:
    return HTTPException(status_code=402, detail={"code": "PREMIUM_REQUIRED", "message": message,
                                                  "details": {"upgrade_url": "/subscribe", "feature": feature}})


@router.post("/team", response_model=PredictTeamResponse)
async def predict_team(body: PredictTeamRequest, db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    if not await has_premium_access(db, user):
        if body.count > 1:
            raise _premium_required("multi_team", "Multiple teams require a Premium subscription.")
        if body.mode != "safe":
            raise _premium_required("gl_team" if body.mode == "grand_league" else f"{body.mode}_team",
                                    f"{body.mode.replace('_', ' ').title()} teams require a Premium subscription.")
    svc = PredictionService(db)
    return await svc.generate_team(match_id=body.match_id, mode=body.mode, count=body.count, user=user,
                                   override_toss=body.override_toss, override_xi=body.override_playing_xi)


@router.post("/team/portfolio")
async def predict_portfolio(body: PortfolioRequest, db: AsyncSession = Depends(get_db),
                            user: User = Depends(require_premium)):
    """All four team modes in one call (Premium)."""
    svc = PredictionService(db)
    teams = {}
    prediction_id = None
    for mode in ("safe", "grand_league", "aggressive", "small_league"):
        r = await svc.generate_team(match_id=body.match_id, mode=mode, count=1, user=user)
        prediction_id = prediction_id or r.prediction_id
        teams[mode] = r.teams[0].model_dump(mode="json")
        weights, phase = r.ensemble_weights, r.match_phase
    return {"prediction_id": str(prediction_id), "match_id": body.match_id, "match_phase": phase,
            "ensemble_weights": weights, "teams": teams}


@router.post("/captain", response_model=CaptainResponse)
async def predict_captain(body: MatchRequest, db: AsyncSession = Depends(get_db),
                          user: User = Depends(get_current_user)):
    return await PredictionService(db).get_captain_options(match_id=body.match_id, mode=body.mode, user=user)


@router.get("/differentials/{match_id}", response_model=DifferentialsResponse)
async def get_differentials(match_id: str, db: AsyncSession = Depends(get_db),
                            user: User = Depends(require_premium)):
    return await PredictionService(db).get_differentials(match_id=match_id)


async def _explain(match_id: str, player_id: uuid.UUID, db: AsyncSession, user: User) -> ExplainResponse:
    premium = await has_premium_access(db, user)
    if not premium:
        key = f"explain_count:{user.id}:{match_id}"
        n = int(await cache_get(key) or 0)
        if n >= FREE_EXPLAIN_LIMIT:
            raise _premium_required("explain", f"Free accounts can view {FREE_EXPLAIN_LIMIT} explanations per match.")
        await cache_set(key, n + 1, ttl=7 * 86400)
    return await PredictionService(db).explain_player(match_id, player_id, depth="full" if premium else "basic")


@explain_router.get("/{match_id}/{player_id}", response_model=ExplainResponse)
async def explain_player(match_id: str, player_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user)):
    return await _explain(match_id, player_id, db, user)


@router.get("/explain/{match_id}/{player_id}", response_model=ExplainResponse, include_in_schema=False)
async def explain_player_legacy(match_id: str, player_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                                user: User = Depends(get_current_user)):
    return await _explain(match_id, player_id, db, user)
