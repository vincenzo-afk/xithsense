"""
Pydantic schemas for all API request/response models (docs/API_SPEC.md).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Mode = Literal["safe", "grand_league", "aggressive", "small_league"]


class _In(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(_In):
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


class LoginRequest(_In):
    email: EmailStr
    password: str


class RefreshRequest(_In):
    refresh_token: str


class ChangePasswordRequest(_In):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strength(cls, v: str) -> str:
        return RegisterRequest.password_strength(v)


class UpdateProfileRequest(_In):
    full_name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)


class SubscriptionOut(BaseModel):
    plan: str
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    role: str
    is_verified: bool
    created_at: datetime
    phone: Optional[str] = None
    notification_prefs: Optional[Dict[str, Any]] = None
    subscription: Optional[SubscriptionOut] = None
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 86400
    user: UserOut


# ── Match ─────────────────────────────────────────────────────────────────────

class TossOut(BaseModel):
    winner: Optional[str]
    decision: Optional[str]


class VenueOut(BaseModel):
    name: str
    city: Optional[str] = None
    country: Optional[str] = None
    pitch_type: Optional[str] = None
    dew_factor: bool = False
    avg_first_innings_score: Optional[int] = None
    chasing_win_pct: Optional[float] = None
    spin_wicket_pct: Optional[float] = None
    pace_wicket_pct: Optional[float] = None
    total_matches: Optional[int] = None


class MatchOut(BaseModel):
    id: str
    match_type: str
    team_a: str
    team_b: str
    venue_name: Optional[str]
    city: Optional[str] = None
    toss_winner: Optional[str]
    toss_decision: Optional[str]
    toss: Optional[TossOut] = None
    match_winner: Optional[str]
    win_by_runs: Optional[int] = None
    win_by_wickets: Optional[int] = None
    season: Optional[str]
    event_name: Optional[str]
    event_stage: Optional[str]
    match_number: Optional[int] = None
    match_date: date
    start_time: Optional[datetime] = None
    status: str = "upcoming"
    status_text: Optional[str] = None
    gender: Optional[str] = None
    source: Optional[str] = None
    live_state: Optional[Dict[str, Any]] = None
    team_info: Optional[Dict[str, Any]] = None
    squad_source: Optional[str] = None
    is_live: bool = False
    prediction_ready: bool = False
    playing_xi_confirmed: bool = False
    player_of_match: Optional[List[str]] = None
    model_config = {"from_attributes": True}


class SquadPlayerOut(BaseModel):
    player_id: uuid.UUID
    full_name: str
    role: Optional[str]
    team: str
    credits: Optional[float]
    is_playing: bool
    batting_style: Optional[str] = None
    bowling_style: Optional[str] = None


class HeadToHead(BaseModel):
    matches: int
    team_a_wins: int
    team_b_wins: int
    last_results: List[Dict[str, Any]]


class MatchDetailOut(MatchOut):
    venue: Optional[VenueOut] = None
    squads: Dict[str, List[SquadPlayerOut]] = {}
    head_to_head: Optional[HeadToHead] = None
    team_form: Dict[str, List[str]] = {}


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
    current_team: Optional[str] = None
    base_credits: Optional[float] = None
    is_active: bool
    model_config = {"from_attributes": True}


class RecentForm(BaseModel):
    last_3_fp_avg: Optional[float]
    last_5_fp_avg: Optional[float]
    last_10_fp_avg: Optional[float]
    fp_ceiling: Optional[float]
    fp_floor: Optional[float]
    fp_consistency: Optional[float]
    fp_30plus_rate: Optional[float] = None


class FormPoint(BaseModel):
    match_id: str
    match_date: date
    opposition: Optional[str]
    venue: Optional[str]
    fantasy_points: float
    runs: int
    balls: int
    wickets: int
    overs: float


class VenueBreakdown(BaseModel):
    venue: str
    matches: int
    fp_avg: float
    runs_avg: float
    wickets_avg: float


class PlayerDetailOut(PlayerOut):
    recent_form: Optional[RecentForm] = None
    career: Optional[Dict[str, Any]] = None
    form_chart: List[FormPoint] = []
    venues: List[VenueBreakdown] = []
    phase_split: Dict[str, Dict[str, float]] = {}


class MatchupOut(BaseModel):
    bowler_type: str
    balls_faced: int
    strike_rate: Optional[float]
    avg_runs: Optional[float]
    dismissal_rate: Optional[float]
    boundary_rate: Optional[float]
    dot_ball_rate: Optional[float] = None
    confidence: float = 0.0


class MatchupsResponse(BaseModel):
    player_id: uuid.UUID
    full_name: str
    match_type: str = "T20"
    matchups: List[MatchupOut]


class PlayerSearchResponse(BaseModel):
    players: List[PlayerOut]
    total: int = 0


# ── Predict ───────────────────────────────────────────────────────────────────

class PredictTeamRequest(_In):
    match_id: str
    mode: Mode = "safe"
    count: int = Field(default=1, ge=1, le=20)
    override_toss: Optional[Dict[str, str]] = None
    override_playing_xi: Optional[Dict[str, List[str]]] = None


class MatchRequest(_In):
    match_id: str
    mode: Mode = "safe"


class PortfolioRequest(_In):
    match_id: str


class PlayerPrediction(BaseModel):
    player_id: uuid.UUID
    full_name: str
    role: str
    team: str
    credits: float
    predicted_fp: float
    fp_ceiling: float
    fp_floor: float
    confidence: int
    confidence_label: str
    is_differential: bool
    ownership_estimate: str
    ownership_tier: str
    rules_fired: List[str] = []
    explanation: Optional[str] = None


class CaptainRecommendation(BaseModel):
    player_id: uuid.UUID
    full_name: str
    confidence: int
    ceiling_score: Optional[float] = None
    type: Optional[str] = None
    reasoning: Optional[str] = None


class TeamResult(BaseModel):
    players: List[PlayerPrediction]
    captain: CaptainRecommendation
    vice_captain: CaptainRecommendation
    total_credits: float
    predicted_total_fp: float
    team_ceiling: float
    team_confidence: int = 0
    team_split: Dict[str, int] = {}
    role_split: Dict[str, int] = {}
    solver_used: str = "lp"
    solve_time_ms: int = 0


class PredictTeamResponse(BaseModel):
    prediction_id: uuid.UUID
    match_id: str
    mode: str
    generated_at: datetime
    match_phase: str
    playing_xi_confirmed: bool = False
    model_version: Optional[str] = None
    teams: List[TeamResult]
    ensemble_weights: Dict[str, float]
    pool: List[PlayerPrediction] = []


class CaptainOption(BaseModel):
    rank: int
    player_id: uuid.UUID
    full_name: str
    type: str   # best_captain | safe_captain | risk_captain
    ceiling_score: float
    confidence: int
    ownership_estimate: Optional[str] = None
    predicted_fp: Optional[float] = None
    reasoning: str


class CaptainResponse(BaseModel):
    recommendations: List[CaptainOption]


class DifferentialOut(BaseModel):
    player_id: uuid.UUID
    full_name: str
    role: str
    team: str
    credits: float
    ownership_estimate: str
    ceiling_score: float
    fp_avg_5: Optional[float]
    predicted_fp: float
    reason: str


class DifferentialsResponse(BaseModel):
    differentials: List[DifferentialOut]


class ExplanationFactor(BaseModel):
    factor: str
    value: str
    detail: str
    sentiment: str = "neutral"     # positive | negative | neutral


class ExplainResponse(BaseModel):
    player_id: uuid.UUID
    full_name: str
    role: str
    team: str
    match_id: str
    explanation: str
    explanation_source: str = "template"     # llm | template
    depth: str = "full"                      # basic | full
    factors: List[ExplanationFactor]
    rules_fired: List[str]
    rules_detail: List[Dict[str, Any]] = []
    confidence: int
    confidence_label: str
    predicted_fp: float
    fp_ceiling: float
    fp_floor: float
    ownership_estimate: str
    ensemble_breakdown: Optional[Dict[str, float]] = None


# ── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(_In):
    match_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=1000)
    session_id: Optional[uuid.UUID] = None

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be empty")
        return v


class RelatedPlayer(BaseModel):
    player_id: uuid.UUID
    full_name: str


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    answer: str
    intent: str = "GENERAL_STRATEGY"
    related_players: List[RelatedPlayer] = []
    sources_used: List[str] = []
    answer_source: str = "engine"            # llm | engine


class ChatMessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatSessionOut(BaseModel):
    id: uuid.UUID
    match_id: Optional[str]
    title: Optional[str]
    message_count: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Admin ─────────────────────────────────────────────────────────────────────

class IngestRequest(_In):
    source: str = "data/raw/demo"
    incremental: bool = True


class RetrainRequest(_In):
    format: str = "T20"
    model_ids: List[str] = ["M-01", "M-02", "M-03"]


class BacktestRequest(_In):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    n: int = Field(default=200, ge=5, le=10000)
    name: Optional[str] = None


class AdminMetricsResponse(BaseModel):
    total_matches: int
    total_players: int
    total_users: int
    premium_users: int = 0
    total_predictions: int
    total_deliveries: int = 0
    upcoming_matches: int = 0
    mrr_inr: float = 0
    captain_accuracy: Optional[float]
    correct_player_rate: Optional[float]
    top3_captain_rate: Optional[float] = None
    avg_fp_error: Optional[float]
    model_mae: Optional[float] = None
    baseline_mae: Optional[float] = None
    model_spearman: Optional[float] = None
    active_model_version: Optional[str]
    active_rules: int = 0
    system_health: str = "ok"
    checks: Dict[str, str] = {}
    predictions_by_day: List[Dict[str, Any]] = []
    users_by_role: Dict[str, int] = {}


class RuleCreateRequest(_In):
    id: Optional[str] = Field(None, pattern=r"^RULE-\d{4}$")
    rule_type: Literal["player", "venue", "matchup", "context"]
    player_key: Optional[str] = None
    condition: Dict[str, Any] = Field(min_length=1)
    match_types: Optional[List[str]] = None
    impact_score: int = Field(ge=-100, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    description: Optional[str] = None
    source: Optional[str] = Field(None, min_length=5)
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_active: bool = True


class RuleUpdateRequest(_In):
    player_key: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    match_types: Optional[List[str]] = None
    impact_score: Optional[int] = Field(None, ge=-100, le=100)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    description: Optional[str] = None
    source: Optional[str] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_active: Optional[bool] = None


class RuleOut(BaseModel):
    id: str
    rule_type: str
    player_key: Optional[str]
    condition: Dict[str, Any]
    match_types: Optional[List[str]] = None
    impact_score: int
    confidence: float
    effective_impact: float
    description: Optional[str]
    source: Optional[str]
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_active: bool
    created_at: Optional[datetime] = None


class MatchAdminUpdate(_In):
    toss_winner: Optional[str] = None
    toss_decision: Optional[Literal["bat", "field"]] = None
    status: Optional[Literal["upcoming", "live", "complete"]] = None
    playing_xi: Optional[Dict[str, List[str]]] = None


class RoleUpdateRequest(_In):
    role: Literal["free", "premium", "admin"]


# ── Payments ──────────────────────────────────────────────────────────────────

class CreateSubscriptionRequest(_In):
    plan: Literal["premium_monthly", "premium_annual"]


class CreateSubscriptionResponse(BaseModel):
    order_id: str
    razorpay_key_id: Optional[str]
    amount: int
    currency: str = "INR"
    plan: str
    checkout_mode: str = "razorpay"          # razorpay | simulated


class VerifyPaymentRequest(_In):
    order_id: str
    payment_id: Optional[str] = None
    signature: Optional[str] = None
    plan: Literal["premium_monthly", "premium_annual"]


class CancelRequest(_In):
    reason: Optional[str] = None


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationPrefs(_In):
    email_enabled: bool = True
    telegram_enabled: bool = False
    push_enabled: bool = False
    events: Dict[str, bool] = {}
    formats: List[str] = ["T20", "IPL"]


class NotificationOut(BaseModel):
    id: uuid.UUID
    match_id: Optional[str]
    event_type: str
    title: Optional[str]
    message_preview: Optional[str]
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Error / Health ────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = {}
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
