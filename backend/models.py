"""
SQLAlchemy ORM Models — tables from DATABASE_SCHEMA.md.

Portable across PostgreSQL (production) and SQLite (local/dev): JSON columns use
JSONB on Postgres, arrays fall back to JSON, numerics are stored as Float.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Index,
    Integer, JSON, SmallInteger, String, Text, UniqueConstraint, UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator

from backend.database import Base


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every backend (SQLite returns naive values)."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)   # SQLite drops offsets — always store UTC

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class SafeJSONB(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON)


SafeArray = SafeJSONB  # list[str] stored as JSON(B) — portable


def _uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created():
    return mapped_column(UTCDateTime(), server_default=func.now(), nullable=False)


# ── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(128))
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    google_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True)
    notification_prefs: Mapped[Optional[dict]] = mapped_column(SafeJSONB)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    chat_sessions: Mapped[List["ChatSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ── Subscription ─────────────────────────────────────────────────────────────

class Subscription(Base):
    __tablename__ = "subscription"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    plan: Mapped[str] = mapped_column(String(30), nullable=False)          # free | premium_monthly | premium_annual
    status: Mapped[str] = mapped_column(String(30), nullable=False)        # active | cancelled | expired | trial
    razorpay_sub_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    razorpay_customer_id: Mapped[Optional[str]] = mapped_column(String(100))
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(100))
    amount_paise: Mapped[Optional[int]] = mapped_column(Integer)
    current_period_start: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())
    current_period_end: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="subscriptions")


class ProcessedWebhook(Base):
    """Idempotency ledger for Razorpay webhook events."""
    __tablename__ = "processed_webhook"

    event_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    processed_at: Mapped[datetime] = _created()


# ── Venue ─────────────────────────────────────────────────────────────────────

class Venue(Base):
    __tablename__ = "venue"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    capacity: Mapped[Optional[int]] = mapped_column(Integer)
    pitch_type: Mapped[Optional[str]] = mapped_column(String(50))     # batting | spin | pace | balanced
    avg_first_innings_score: Mapped[Optional[int]] = mapped_column(Integer)
    boundary_short_m: Mapped[Optional[float]] = mapped_column(Float)
    boundary_long_m: Mapped[Optional[float]] = mapped_column(Float)
    dew_factor: Mapped[bool] = mapped_column(Boolean, default=False)
    altitude_m: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = _created()

    matches: Mapped[List["Match"]] = relationship(back_populates="venue_ref")
    venue_stats: Mapped[List["VenueStat"]] = relationship(back_populates="venue")


# ── Match ────────────────────────────────────────────────────────────────────

class Match(Base):
    __tablename__ = "match"
    __table_args__ = (Index("ix_match_status_date", "status", "match_date"),)

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False, default="male")
    team_type: Mapped[str] = mapped_column(String(20), nullable=False, default="club")
    venue_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("venue.id"))
    venue_name: Mapped[Optional[str]] = mapped_column(String(200))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    team_a: Mapped[str] = mapped_column(String(100), nullable=False)
    team_b: Mapped[str] = mapped_column(String(100), nullable=False)
    toss_winner: Mapped[Optional[str]] = mapped_column(String(100))
    toss_decision: Mapped[Optional[str]] = mapped_column(String(10))
    match_winner: Mapped[Optional[str]] = mapped_column(String(100))
    win_by_runs: Mapped[Optional[int]] = mapped_column(Integer)
    win_by_wickets: Mapped[Optional[int]] = mapped_column(Integer)
    player_of_match: Mapped[Optional[List[str]]] = mapped_column(SafeArray)
    season: Mapped[Optional[str]] = mapped_column(String(20))
    event_name: Mapped[Optional[str]] = mapped_column(String(200))
    event_stage: Mapped[Optional[str]] = mapped_column(String(100))
    match_number: Mapped[Optional[int]] = mapped_column(Integer)
    match_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())
    day_night: Mapped[bool] = mapped_column(Boolean, default=False)
    balls_per_over: Mapped[int] = mapped_column(Integer, default=6)
    data_version: Mapped[Optional[str]] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="complete")      # upcoming | live | complete
    playing_xi_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[Optional[str]] = mapped_column(String(20))               # cricsheet | cricapi | manual
    cricapi_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    series_id: Mapped[Optional[str]] = mapped_column(String(64))
    status_text: Mapped[Optional[str]] = mapped_column(String(200))
    live_state: Mapped[Optional[dict]] = mapped_column(SafeJSONB)            # latest score summary from the live feed
    team_info: Mapped[Optional[dict]] = mapped_column(SafeJSONB)             # {team: {short, img}}
    squad_source: Mapped[Optional[str]] = mapped_column(String(20))         # official | probable | manual
    is_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _created()

    venue_ref: Mapped[Optional["Venue"]] = relationship(back_populates="matches")
    innings_list: Mapped[List["Innings"]] = relationship(back_populates="match_ref")
    player_team_matches: Mapped[List["PlayerTeamMatch"]] = relationship(back_populates="match_ref")
    predictions: Mapped[List["Prediction"]] = relationship(back_populates="match_ref")


# ── Player ────────────────────────────────────────────────────────────────────

class Player(Base):
    __tablename__ = "player"

    id: Mapped[uuid.UUID] = _uuid_pk()
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cricsheet_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    cricsheet_id: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    short_name: Mapped[Optional[str]] = mapped_column(String(50))
    nationality: Mapped[Optional[str]] = mapped_column(String(100))
    batting_style: Mapped[Optional[str]] = mapped_column(String(30))
    bowling_style: Mapped[Optional[str]] = mapped_column(String(50))
    bowler_type: Mapped[Optional[str]] = mapped_column(String(20))      # pace_* | spin_* | pace | spin (inferred)
    style_source: Mapped[Optional[str]] = mapped_column(String(20))     # api | metadata | inferred
    cricapi_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(300))
    primary_role: Mapped[Optional[str]] = mapped_column(String(20))
    current_team: Mapped[Optional[str]] = mapped_column(String(100))
    base_credits: Mapped[Optional[float]] = mapped_column(Float)
    dob: Mapped[Optional[date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)

    player_team_matches: Mapped[List["PlayerTeamMatch"]] = relationship(back_populates="player")
    performances: Mapped[List["PlayerMatchPerformance"]] = relationship(back_populates="player")
    rolling_features: Mapped[List["RollingFeature"]] = relationship(back_populates="player")
    matchup_stats: Mapped[List["MatchupStat"]] = relationship(back_populates="player")


# ── PlayerTeamMatch (squad / playing XI) ──────────────────────────────────────

class PlayerTeamMatch(Base):
    __tablename__ = "player_team_match"
    __table_args__ = (UniqueConstraint("match_id", "player_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    match_id: Mapped[str] = mapped_column(String(20), ForeignKey("match.id"), nullable=False, index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False, index=True)
    team: Mapped[str] = mapped_column(String(100), nullable=False)
    batting_order: Mapped[Optional[int]] = mapped_column(Integer)
    is_captain: Mapped[bool] = mapped_column(Boolean, default=False)
    is_keeper: Mapped[bool] = mapped_column(Boolean, default=False)
    is_playing: Mapped[bool] = mapped_column(Boolean, default=True)       # False = squad member, not in XI
    credits: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = _created()

    match_ref: Mapped["Match"] = relationship(back_populates="player_team_matches")
    player: Mapped["Player"] = relationship(back_populates="player_team_matches")


# ── Innings ───────────────────────────────────────────────────────────────────

class Innings(Base):
    __tablename__ = "innings"
    __table_args__ = (UniqueConstraint("match_id", "innings_number"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    match_id: Mapped[str] = mapped_column(String(20), ForeignKey("match.id"), nullable=False, index=True)
    innings_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    batting_team: Mapped[str] = mapped_column(String(100), nullable=False)
    bowling_team: Mapped[str] = mapped_column(String(100), nullable=False)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    total_wickets: Mapped[int] = mapped_column(Integer, default=0)
    total_overs: Mapped[float] = mapped_column(Float, default=0)
    target_runs: Mapped[Optional[int]] = mapped_column(Integer)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _created()

    match_ref: Mapped["Match"] = relationship(back_populates="innings_list")
    deliveries: Mapped[List["Delivery"]] = relationship(back_populates="innings")


# ── Delivery ──────────────────────────────────────────────────────────────────

class Delivery(Base):
    __tablename__ = "delivery"
    __table_args__ = (
        UniqueConstraint("innings_id", "over_number", "ball_seq"),
        Index("ix_delivery_batter_id", "batter_id"),
        Index("ix_delivery_bowler_id", "bowler_id"),
        Index("ix_delivery_match", "match_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    innings_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("innings.id"), nullable=False)
    match_id: Mapped[str] = mapped_column(String(20), nullable=False)
    over_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ball_seq: Mapped[int] = mapped_column(SmallInteger, nullable=False)      # position within over incl. extras
    ball_number: Mapped[float] = mapped_column(Float, nullable=False)        # over.legal_ball, e.g. 3.4
    batter: Mapped[str] = mapped_column(String(200), nullable=False)
    bowler: Mapped[str] = mapped_column(String(200), nullable=False)
    non_striker: Mapped[Optional[str]] = mapped_column(String(200))
    batter_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    bowler_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    runs_batter: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    runs_extras: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    runs_total: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_wide: Mapped[bool] = mapped_column(Boolean, default=False)
    is_no_ball: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bye: Mapped[bool] = mapped_column(Boolean, default=False)
    is_leg_bye: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_wides: Mapped[int] = mapped_column(SmallInteger, default=0)
    extra_no_balls: Mapped[int] = mapped_column(SmallInteger, default=0)
    extra_byes: Mapped[int] = mapped_column(SmallInteger, default=0)
    extra_leg_byes: Mapped[int] = mapped_column(SmallInteger, default=0)
    is_wicket: Mapped[bool] = mapped_column(Boolean, default=False)
    wicket_player_out: Mapped[Optional[str]] = mapped_column(String(200))
    wicket_kind: Mapped[Optional[str]] = mapped_column(String(50))
    wicket_fielder: Mapped[Optional[str]] = mapped_column(String(200))
    is_powerplay: Mapped[bool] = mapped_column(Boolean, default=False)
    phase: Mapped[Optional[str]] = mapped_column(String(20))
    review_by: Mapped[Optional[str]] = mapped_column(String(100))
    review_decision: Mapped[Optional[str]] = mapped_column(String(20))

    innings: Mapped["Innings"] = relationship(back_populates="deliveries")


# ── PlayerMatchPerformance ────────────────────────────────────────────────────

class PlayerMatchPerformance(Base):
    __tablename__ = "player_match_performance"
    __table_args__ = (UniqueConstraint("match_id", "player_id", "fantasy_platform"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    match_id: Mapped[str] = mapped_column(String(20), ForeignKey("match.id"), nullable=False, index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False, index=True)
    match_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    match_type: Mapped[Optional[str]] = mapped_column(String(20))
    venue_name: Mapped[Optional[str]] = mapped_column(String(200))
    team: Mapped[str] = mapped_column(String(100), nullable=False)
    opposition: Mapped[Optional[str]] = mapped_column(String(100))
    is_chasing: Mapped[Optional[bool]] = mapped_column(Boolean)
    runs_scored: Mapped[int] = mapped_column(Integer, default=0)
    balls_faced: Mapped[int] = mapped_column(Integer, default=0)
    fours: Mapped[int] = mapped_column(Integer, default=0)
    sixes: Mapped[int] = mapped_column(Integer, default=0)
    strike_rate: Mapped[Optional[float]] = mapped_column(Float)
    did_bat: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissal_type: Mapped[Optional[str]] = mapped_column(String(50))
    batting_position: Mapped[Optional[int]] = mapped_column(SmallInteger)
    overs_bowled: Mapped[float] = mapped_column(Float, default=0)
    balls_bowled: Mapped[int] = mapped_column(Integer, default=0)
    runs_conceded: Mapped[int] = mapped_column(Integer, default=0)
    wickets_taken: Mapped[int] = mapped_column(Integer, default=0)
    lbw_bowled: Mapped[int] = mapped_column(Integer, default=0)
    maidens: Mapped[int] = mapped_column(Integer, default=0)
    economy: Mapped[Optional[float]] = mapped_column(Float)
    dot_balls: Mapped[int] = mapped_column(Integer, default=0)
    catches: Mapped[int] = mapped_column(Integer, default=0)
    run_outs: Mapped[int] = mapped_column(Integer, default=0)
    stumpings: Mapped[int] = mapped_column(Integer, default=0)
    fantasy_points: Mapped[Optional[float]] = mapped_column(Float)
    fantasy_platform: Mapped[str] = mapped_column(String(30), default="dream11")
    created_at: Mapped[datetime] = _created()

    player: Mapped["Player"] = relationship(back_populates="performances")


# ── RollingFeature ────────────────────────────────────────────────────────────

class RollingFeature(Base):
    __tablename__ = "rolling_feature"
    __table_args__ = (UniqueConstraint("player_id", "match_type", "as_of_date", "window_matches"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False, index=True)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    window_matches: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    avg_runs: Mapped[Optional[float]] = mapped_column(Float)
    avg_balls: Mapped[Optional[float]] = mapped_column(Float)
    avg_sr: Mapped[Optional[float]] = mapped_column(Float)
    avg_fours: Mapped[Optional[float]] = mapped_column(Float)
    avg_sixes: Mapped[Optional[float]] = mapped_column(Float)
    avg_wickets: Mapped[Optional[float]] = mapped_column(Float)
    avg_economy: Mapped[Optional[float]] = mapped_column(Float)
    avg_overs: Mapped[Optional[float]] = mapped_column(Float)
    fp_avg: Mapped[Optional[float]] = mapped_column(Float)
    fp_ceiling: Mapped[Optional[float]] = mapped_column(Float)
    fp_floor: Mapped[Optional[float]] = mapped_column(Float)
    fp_consistency: Mapped[Optional[float]] = mapped_column(Float)
    fp_30plus_rate: Mapped[Optional[float]] = mapped_column(Float)
    fp_last_3: Mapped[Optional[float]] = mapped_column(Float)
    matches_included: Mapped[Optional[int]] = mapped_column(Integer)
    last_match_id: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = _created()

    player: Mapped["Player"] = relationship(back_populates="rolling_features")


# ── VenueStat ─────────────────────────────────────────────────────────────────

class VenueStat(Base):
    __tablename__ = "venue_stat"
    __table_args__ = (UniqueConstraint("venue_id", "match_type"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("venue.id"), nullable=False)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    avg_runs_per_innings: Mapped[Optional[float]] = mapped_column(Float)
    avg_first_innings: Mapped[Optional[float]] = mapped_column(Float)
    avg_second_innings: Mapped[Optional[float]] = mapped_column(Float)
    avg_wickets_per_match: Mapped[Optional[float]] = mapped_column(Float)
    spin_wicket_pct: Mapped[Optional[float]] = mapped_column(Float)
    pace_wicket_pct: Mapped[Optional[float]] = mapped_column(Float)
    chasing_win_pct: Mapped[Optional[float]] = mapped_column(Float)
    boundary_index: Mapped[Optional[float]] = mapped_column(Float)
    toss_advantage: Mapped[Optional[str]] = mapped_column(String(10))
    dew_impact: Mapped[Optional[float]] = mapped_column(Float)
    total_matches: Mapped[Optional[int]] = mapped_column(Integer)
    last_updated: Mapped[datetime] = _created()

    venue: Mapped["Venue"] = relationship(back_populates="venue_stats")


# ── MatchupStat ───────────────────────────────────────────────────────────────

class MatchupStat(Base):
    __tablename__ = "matchup_stat"
    __table_args__ = (UniqueConstraint("player_id", "match_type", "bowler_type"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False, index=True)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    bowler_type: Mapped[str] = mapped_column(String(50), nullable=False)
    balls_faced: Mapped[int] = mapped_column(Integer, default=0)
    runs_scored: Mapped[int] = mapped_column(Integer, default=0)
    dismissals: Mapped[int] = mapped_column(Integer, default=0)
    strike_rate: Mapped[Optional[float]] = mapped_column(Float)
    avg_runs: Mapped[Optional[float]] = mapped_column(Float)
    dot_ball_pct: Mapped[Optional[float]] = mapped_column(Float)
    boundary_pct: Mapped[Optional[float]] = mapped_column(Float)
    updated_at: Mapped[datetime] = _created()

    player: Mapped["Player"] = relationship(back_populates="matchup_stats")


# ── HumanRule ─────────────────────────────────────────────────────────────────

class HumanRule(Base):
    __tablename__ = "human_rule"

    id: Mapped[uuid.UUID] = _uuid_pk()
    ext_id: Mapped[Optional[str]] = mapped_column(String(20), unique=True)     # RULE-0001
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    player_key: Mapped[Optional[str]] = mapped_column(String(200))
    condition_json: Mapped[dict] = mapped_column(SafeJSONB, nullable=False)
    match_types: Mapped[Optional[list]] = mapped_column(SafeJSONB)
    impact_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(500))
    valid_from: Mapped[Optional[date]] = mapped_column(Date)
    valid_until: Mapped[Optional[date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)


# ── RuleTrigger ───────────────────────────────────────────────────────────────

class RuleTrigger(Base):
    __tablename__ = "rule_trigger"

    id: Mapped[uuid.UUID] = _uuid_pk()
    prediction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prediction.id"), nullable=False, index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    rule_ext_id: Mapped[Optional[str]] = mapped_column(String(20))
    impact_applied: Mapped[float] = mapped_column(Float)
    fired_at: Mapped[datetime] = _created()


# ── Prediction ────────────────────────────────────────────────────────────────

class Prediction(Base):
    __tablename__ = "prediction"

    id: Mapped[uuid.UUID] = _uuid_pk()
    match_id: Mapped[str] = mapped_column(String(20), ForeignKey("match.id"), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), index=True)
    mode: Mapped[Optional[str]] = mapped_column(String(20))
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    ensemble_weights: Mapped[Optional[dict]] = mapped_column(SafeJSONB)
    generated_at: Mapped[datetime] = _created()
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    match_phase: Mapped[Optional[str]] = mapped_column(String(20))     # pre_toss | post_toss | live

    match_ref: Mapped["Match"] = relationship(back_populates="predictions")
    predicted_players: Mapped[List["PredictedPlayer"]] = relationship(back_populates="prediction", cascade="all, delete-orphan")
    recommended_teams: Mapped[List["RecommendedTeam"]] = relationship(back_populates="prediction", cascade="all, delete-orphan")


class PredictedPlayer(Base):
    __tablename__ = "predicted_player"
    __table_args__ = (UniqueConstraint("prediction_id", "player_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    prediction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prediction.id"), nullable=False)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    ensemble_score: Mapped[float] = mapped_column(Float, nullable=False)
    ml_score: Mapped[Optional[float]] = mapped_column(Float)
    rules_score: Mapped[Optional[float]] = mapped_column(Float)
    form_score: Mapped[Optional[float]] = mapped_column(Float)
    live_score: Mapped[Optional[float]] = mapped_column(Float)
    fp_predicted: Mapped[Optional[float]] = mapped_column(Float)
    fp_ceiling: Mapped[Optional[float]] = mapped_column(Float)
    fp_floor: Mapped[Optional[float]] = mapped_column(Float)
    confidence: Mapped[Optional[int]] = mapped_column(SmallInteger)
    rank: Mapped[Optional[int]] = mapped_column(SmallInteger)
    rules_fired: Mapped[Optional[list]] = mapped_column(SafeJSONB)
    explanation: Mapped[Optional[str]] = mapped_column(Text)

    prediction: Mapped["Prediction"] = relationship(back_populates="predicted_players")


class RecommendedTeam(Base):
    __tablename__ = "recommended_team"

    id: Mapped[uuid.UUID] = _uuid_pk()
    prediction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prediction.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    captain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    vice_captain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    total_credits: Mapped[Optional[float]] = mapped_column(Float)
    predicted_total_fp: Mapped[Optional[float]] = mapped_column(Float)
    solver_used: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = _created()

    prediction: Mapped["Prediction"] = relationship(back_populates="recommended_teams")
    team_players: Mapped[List["TeamPlayer"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class TeamPlayer(Base):
    __tablename__ = "team_player"

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recommended_team.id"), primary_key=True)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    credits: Mapped[Optional[float]] = mapped_column(Float)

    team: Mapped["RecommendedTeam"] = relationship(back_populates="team_players")


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_session"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False, index=True)
    match_id: Mapped[Optional[str]] = mapped_column(String(20))
    title: Mapped[Optional[str]] = mapped_column(String(200))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = _created()

    user: Mapped["User"] = relationship(back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan",
                                                         order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_session.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)   # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


# ── Backtesting / models ──────────────────────────────────────────────────────

class BacktestRun(Base):
    __tablename__ = "backtest_run"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[Optional[str]] = mapped_column(String(200))
    match_type: Mapped[Optional[str]] = mapped_column(String(20))
    from_date: Mapped[Optional[date]] = mapped_column(Date)
    to_date: Mapped[Optional[date]] = mapped_column(Date)
    total_matches: Mapped[Optional[int]] = mapped_column(Integer)
    correct_player_rate: Mapped[Optional[float]] = mapped_column(Float)
    captain_accuracy: Mapped[Optional[float]] = mapped_column(Float)
    vc_accuracy: Mapped[Optional[float]] = mapped_column(Float)
    top3_captain_rate: Mapped[Optional[float]] = mapped_column(Float)
    avg_players_correct: Mapped[Optional[float]] = mapped_column(Float)
    avg_fp_error: Mapped[Optional[float]] = mapped_column(Float)
    spearman_rho: Mapped[Optional[float]] = mapped_column(Float)
    simulated_roi: Mapped[Optional[float]] = mapped_column(Float)
    details: Mapped[Optional[dict]] = mapped_column(SafeJSONB)
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    run_at: Mapped[datetime] = _created()


class ModelVersion(Base):
    __tablename__ = "model_version"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    match_type: Mapped[Optional[str]] = mapped_column(String(20))
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    feature_count: Mapped[Optional[int]] = mapped_column(Integer)
    train_rows: Mapped[Optional[int]] = mapped_column(Integer)
    train_mae: Mapped[Optional[float]] = mapped_column(Float)
    val_mae: Mapped[Optional[float]] = mapped_column(Float)
    baseline_mae: Mapped[Optional[float]] = mapped_column(Float)
    val_spearman: Mapped[Optional[float]] = mapped_column(Float)
    feature_importance: Mapped[Optional[dict]] = mapped_column(SafeJSONB)
    train_from: Mapped[Optional[date]] = mapped_column(Date)
    train_to: Mapped[Optional[date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = _created()


# ── External API cache ────────────────────────────────────────────────────────

class ApiCache(Base):
    """Cached responses from the live-data provider (calls are rationed by a daily quota)."""
    __tablename__ = "api_cache"

    key: Mapped[str] = mapped_column(String(300), primary_key=True)
    payload: Mapped[Optional[dict]] = mapped_column(SafeJSONB)
    hits_cost: Mapped[int] = mapped_column(Integer, default=1)
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ApiUsage(Base):
    __tablename__ = "api_usage"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    hits: Mapped[int] = mapped_column(Integer, default=0)
    limit: Mapped[int] = mapped_column(Integer, default=100)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


# ── Audit / notifications ─────────────────────────────────────────────────────

class AdminAction(Base):
    __tablename__ = "admin_action"

    id: Mapped[uuid.UUID] = _uuid_pk()
    admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)   # e.g. rule.created, model.retrain
    target_type: Mapped[Optional[str]] = mapped_column(String(50))
    target_id: Mapped[Optional[str]] = mapped_column(String(100))
    payload: Mapped[Optional[dict]] = mapped_column(SafeJSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent: Mapped[Optional[str]] = mapped_column(String(300))
    performed_at: Mapped[datetime] = _created()


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False, index=True)
    match_id: Mapped[Optional[str]] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)    # EVT-01..EVT-07
    channel: Mapped[str] = mapped_column(String(20), nullable=False)       # in_app | telegram | email
    status: Mapped[str] = mapped_column(String(20), default="pending")
    title: Mapped[Optional[str]] = mapped_column(String(120))
    message_preview: Mapped[Optional[str]] = mapped_column(String(400))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())
    failed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = _created()
