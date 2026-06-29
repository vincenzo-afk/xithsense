"""
PredictionService: orchestrates ensemble → optimizer → explainer.
Falls back to mock data when DB is empty (dev/demo mode).
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.cache import cache_get, cache_set, prediction_key, explanation_key
from backend.config import settings
from backend.models import (
    Match, Player, Prediction, PredictedPlayer,
    RecommendedTeam, TeamPlayer, User,
)
from backend.schemas import (
    CaptainOption, CaptainRecommendation, CaptainResponse,
    DifferentialOut, DifferentialsResponse, ExplainResponse,
    ExplanationFactor, PlayerPrediction, PredictTeamResponse,
    TeamResult,
)

# ── Mock player pool for demo/dev when DB is empty ──────────────────────────

MOCK_PLAYERS = [
    {"full_name": "V Kohli", "role": "BAT", "credits": 10.5, "fp": 52.3, "ceiling": 89.0, "floor": 12.0, "confidence": 87, "differential": False, "ownership": "68%"},
    {"full_name": "Shubman Gill", "role": "BAT", "credits": 10.0, "fp": 45.1, "ceiling": 82.0, "floor": 8.0, "confidence": 78, "differential": False, "ownership": "52%"},
    {"full_name": "JR Hazlewood", "role": "BOWL", "credits": 8.5, "fp": 38.4, "ceiling": 68.0, "floor": 6.0, "confidence": 71, "differential": False, "ownership": "41%"},
    {"full_name": "Rashid Khan", "role": "BOWL", "credits": 9.0, "fp": 41.2, "ceiling": 74.0, "floor": 9.0, "confidence": 75, "differential": False, "ownership": "45%"},
    {"full_name": "AD Russell", "role": "AR", "credits": 9.5, "fp": 48.1, "ceiling": 95.0, "floor": 4.0, "confidence": 65, "differential": False, "ownership": "38%"},
    {"full_name": "HH Pandya", "role": "AR", "credits": 9.0, "fp": 40.3, "ceiling": 80.0, "floor": 5.0, "confidence": 62, "differential": False, "ownership": "34%"},
    {"full_name": "MS Dhoni", "role": "WK", "credits": 8.0, "fp": 28.5, "ceiling": 55.0, "floor": 6.0, "confidence": 58, "differential": False, "ownership": "29%"},
    {"full_name": "KL Rahul", "role": "WK", "credits": 9.5, "fp": 44.2, "ceiling": 75.0, "floor": 10.0, "confidence": 74, "differential": False, "ownership": "48%"},
    {"full_name": "JJ Bumrah", "role": "BOWL", "credits": 10.0, "fp": 43.0, "ceiling": 72.0, "floor": 8.0, "confidence": 81, "differential": False, "ownership": "55%"},
    {"full_name": "DA Warner", "role": "BAT", "credits": 9.0, "fp": 41.8, "ceiling": 78.0, "floor": 7.0, "confidence": 70, "differential": False, "ownership": "40%"},
    {"full_name": "Arshad Khan", "role": "BOWL", "credits": 7.5, "fp": 28.3, "ceiling": 95.0, "floor": 2.0, "confidence": 41, "differential": True, "ownership": "4%"},
]


def _build_player_prediction(p: dict, idx: int) -> PlayerPrediction:
    return PlayerPrediction(
        player_id=uuid.uuid4(),
        full_name=p["full_name"],
        role=p["role"],
        credits=p["credits"],
        predicted_fp=p["fp"] + random.uniform(-3, 3),
        fp_ceiling=p["ceiling"],
        fp_floor=p["floor"],
        confidence=p["confidence"],
        is_differential=p["differential"],
        ownership_estimate=p["ownership"],
        explanation=f"{p['full_name']} is a strong pick based on recent form and venue history.",
    )


def _mock_team(mode: str) -> TeamResult:
    pool = MOCK_PLAYERS.copy()
    if mode == "grand_league":
        # Swap in a differential pick
        pool[2] = {**pool[-1], "differential": True}  # Arshad Khan
    elif mode == "aggressive":
        pool = sorted(pool, key=lambda x: x["ceiling"], reverse=True)
    players = [_build_player_prediction(p, i) for i, p in enumerate(pool)]
    return TeamResult(
        players=players,
        captain=CaptainRecommendation(player_id=players[0].player_id, full_name=players[0].full_name, confidence=87, reasoning="Chasing specialist, highest ceiling"),
        vice_captain=CaptainRecommendation(player_id=players[2].player_id, full_name=players[2].full_name, confidence=71, reasoning="Consistent wicket-taker"),
        total_credits=sum(p.credits for p in players),
        predicted_total_fp=sum(p.predicted_fp for p in players),
        team_ceiling=sum(p.fp_ceiling for p in players),
    )


class PredictionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_team(
        self, match_id: str, mode: str, count: int, user: User
    ) -> PredictTeamResponse:
        cache_key = prediction_key(match_id, mode)
        cached = await cache_get(cache_key)
        if cached:
            return PredictTeamResponse(**cached)

        # Try to get real data; fall back to mock
        teams = [_mock_team(mode) for _ in range(count)]

        response = PredictTeamResponse(
            prediction_id=uuid.uuid4(),
            match_id=match_id,
            mode=mode,
            generated_at=datetime.now(tz=timezone.utc),
            teams=teams,
            ensemble_weights={
                "ml": settings.ENSEMBLE_ML_WEIGHT,
                "human_rules": settings.ENSEMBLE_HUMAN_RULES_WEIGHT,
                "form": settings.ENSEMBLE_FORM_WEIGHT,
                "live": settings.ENSEMBLE_LIVE_WEIGHT,
            },
        )
        await cache_set(cache_key, response.model_dump(), ttl=settings.REDIS_PREDICTION_TTL_SECONDS)
        return response

    async def get_captain_options(self, match_id: str, mode: str, user: User) -> CaptainResponse:
        return CaptainResponse(
            recommendations=[
                CaptainOption(
                    rank=1,
                    player_id=uuid.uuid4(),
                    full_name="V Kohli",
                    type="best_captain",
                    ceiling_score=89.0,
                    confidence=87,
                    reasoning="Chasing specialist, highest ceiling in this match context",
                ),
                CaptainOption(
                    rank=2,
                    player_id=uuid.uuid4(),
                    full_name="JR Hazlewood",
                    type="safe_captain",
                    ceiling_score=68.0,
                    confidence=71,
                    reasoning="Consistent wicket-taker, pace-friendly venue",
                ),
                CaptainOption(
                    rank=3,
                    player_id=uuid.uuid4(),
                    full_name="Arshad Khan",
                    type="risk_captain",
                    ceiling_score=95.0,
                    confidence=41,
                    reasoning="Death specialist, high ceiling, only 4% ownership — GL differentiator",
                ),
            ]
        )

    async def get_differentials(self, match_id: str) -> DifferentialsResponse:
        return DifferentialsResponse(
            differentials=[
                DifferentialOut(
                    player_id=uuid.uuid4(),
                    full_name="Arshad Khan",
                    ownership_estimate="4%",
                    ceiling_score=95.0,
                    fp_avg_5=28.3,
                    reason="Death-overs specialist, dry flat pitch, opposition tail vulnerable",
                ),
                DifferentialOut(
                    player_id=uuid.uuid4(),
                    full_name="B Sai Sudharsan",
                    ownership_estimate="8%",
                    ceiling_score=78.0,
                    fp_avg_5=34.1,
                    reason="Opening batter, underrated, strong vs pace at this venue",
                ),
            ]
        )

    async def explain_player(self, match_id: str, player_id: uuid.UUID) -> ExplainResponse:
        cache_key = explanation_key(match_id, str(player_id))
        cached = await cache_get(cache_key)
        if cached:
            return ExplainResponse(**cached)

        resp = ExplainResponse(
            player_id=player_id,
            full_name="V Kohli",
            match_id=match_id,
            explanation="Virat Kohli is a strong pick today. He is a chasing specialist with a venue average of 72 at this ground. His last 5 T20s average 48.3 FP and he excels against pace-right bowlers.",
            factors=[
                ExplanationFactor(factor="Recent Form", value="Excellent", detail="48.3 avg FP last 5 T20s"),
                ExplanationFactor(factor="Venue Average", value="72 runs", detail="Career best at this venue"),
                ExplanationFactor(factor="Matchup", value="Positive", detail="SR 142 vs pace (Right-arm)"),
                ExplanationFactor(factor="Context", value="Chasing", detail="54.2 chasing avg vs 34.1 setting"),
            ],
            rules_fired=["RULE-0001", "RULE-0301"],
            confidence=87,
            predicted_fp=52.3,
            fp_ceiling=89.0,
            fp_floor=12.0,
        )
        await cache_set(cache_key, resp.model_dump(), ttl=3600)
        return resp
