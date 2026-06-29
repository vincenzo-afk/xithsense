"""
Pydantic schemas for all API request/response models.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=200)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 86400
    user: "UserOut"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    role: str
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Match ─────────────────────────────────────────────────────────────────────

class MatchOut(BaseModel):
    id: str
    match_type: str
    team_a: str
    team_b: str
    venue_name: Optional[str]
    toss_winner: Optional[str]
    toss_decision: Optional[str]
    match_winner: Optional[str]
    season: Optional[str]
    event_name: Optional[str]
    event_stage: Optional[str]
    match_date: date
    prediction_ready: bool = False
    playing_xi_confirmed: bool = False

    model_config = {"from_attributes": True}


class MatchListResponse(BaseModel):
    matches: List[MatchOut]
    total: int


# ── Player ────────────────────────────────────────────────────────────────────

class PlayerOut(BaseModel):
    id: uuid.UUID
    full_name: str
    short_name: Optional[str]
    primary_role: Optional[str]
    batting_style: Optional[str]
    bowling_style: Optional[str]
    nationality: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class RecentForm(BaseModel):
    last_3_fp_avg: Optional[float]
    last_5_fp_avg: Optional[float]
    last_10_fp_avg: Optional[float]
    fp_ceiling: Optional[float]
    fp_floor: Optional[float]
    fp_consistency: Optional[float]


class PlayerDetailOut(PlayerOut):
    recent_form: Optional[RecentForm] = None
    career: Optional[Dict[str, Any]] = None


class MatchupOut(BaseModel):
    bowler_type: str
    balls_faced: int
    strike_rate: Optional[float]
    avg_runs: Optional[float]
    dismissal_rate: Optional[float]
    boundary_rate: Optional[float]


class MatchupsResponse(BaseModel):
    matchups: List[MatchupOut]


class PlayerSearchResponse(BaseModel):
    players: List[PlayerOut]


# ── Predict ───────────────────────────────────────────────────────────────────

class PredictTeamRequest(BaseModel):
    match_id: str
    mode: str = Field(default="safe", pattern="^(safe|grand_league|aggressive|small_league)$")
    count: int = Field(default=1, ge=1, le=20)
    override_toss: Optional[Dict[str, str]] = None
    override_playing_xi: Optional[List[str]] = None


class PlayerPrediction(BaseModel):
    player_id: uuid.UUID
    full_name: str
    role: str
    credits: float
    predicted_fp: float
    fp_ceiling: float
    fp_floor: float
    confidence: int
    is_differential: bool
    ownership_estimate: str
    explanation: Optional[str] = None


class CaptainRecommendation(BaseModel):
    player_id: uuid.UUID
    full_name: str
    confidence: int
    reasoning: Optional[str] = None


class TeamResult(BaseModel):
    players: List[PlayerPrediction]
    captain: CaptainRecommendation
    vice_captain: CaptainRecommendation
    total_credits: float
    predicted_total_fp: float
    team_ceiling: float


class PredictTeamResponse(BaseModel):
    prediction_id: uuid.UUID
    match_id: str
    mode: str
    generated_at: datetime
    teams: List[TeamResult]
    ensemble_weights: Dict[str, float]


class CaptainOption(BaseModel):
    rank: int
    player_id: uuid.UUID
    full_name: str
    type: str   # best_captain | safe_captain | risk_captain
    ceiling_score: float
    confidence: int
    reasoning: str


class CaptainResponse(BaseModel):
    recommendations: List[CaptainOption]


class DifferentialOut(BaseModel):
    player_id: uuid.UUID
    full_name: str
    ownership_estimate: str
    ceiling_score: float
    fp_avg_5: Optional[float]
    reason: str


class DifferentialsResponse(BaseModel):
    differentials: List[DifferentialOut]


class ExplanationFactor(BaseModel):
    factor: str
    value: str
    detail: str


class ExplainResponse(BaseModel):
    player_id: uuid.UUID
    full_name: str
    match_id: str
    explanation: str
    factors: List[ExplanationFactor]
    rules_fired: List[str]
    confidence: int
    predicted_fp: float
    fp_ceiling: float
    fp_floor: float


# ── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    match_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=1000)
    session_id: Optional[uuid.UUID] = None


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    answer: str
    related_players: List[str] = []
    sources_used: List[str] = []


# ── Admin ─────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    source: str = "cricsheet_latest"
    incremental: bool = True


class RetrainRequest(BaseModel):
    format: str = "T20"
    model_ids: List[str] = ["M-01", "M-02", "M-03"]


class AdminMetricsResponse(BaseModel):
    total_matches: int
    total_players: int
    total_users: int
    total_predictions: int
    captain_accuracy: Optional[float]
    correct_player_rate: Optional[float]
    avg_fp_error: Optional[float]
    active_model_version: Optional[str]
    system_health: str = "ok"


class RuleCreateRequest(BaseModel):
    rule_type: str
    player_key: Optional[str] = None
    condition_json: Dict[str, Any]
    impact_score: int = Field(ge=-100, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    source: Optional[str] = None
    is_active: bool = True


class RuleOut(BaseModel):
    id: uuid.UUID
    rule_type: str
    player_key: Optional[str]
    condition_json: Dict[str, Any]
    impact_score: int
    confidence: float
    source: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Payments ──────────────────────────────────────────────────────────────────

class CreateSubscriptionRequest(BaseModel):
    plan: str = Field(pattern="^(premium_monthly|premium_annual)$")


class CreateSubscriptionResponse(BaseModel):
    order_id: str
    razorpay_key_id: str
    amount: int
    currency: str = "INR"
    plan: str


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = {}
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.5.0"
    timestamp: datetime


TokenResponse.model_rebuild()
