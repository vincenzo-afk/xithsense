"""
SQLAlchemy ORM Models — all 22 tables from DATABASE_SCHEMA.md
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey,
    Integer, Numeric, SmallInteger, String, Text, UniqueConstraint,
    text, JSON, UUID
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator

class SafeJSONB(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON)

class SafeArray(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy import ARRAY
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(JSON)


from backend.database import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def now_utc():
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(128))
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    google_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="user")
    chat_sessions: Mapped[List["ChatSession"]] = relationship(back_populates="user")


# ── Subscription ─────────────────────────────────────────────────────────────

class Subscription(Base):
    __tablename__ = "subscription"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    plan: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    razorpay_sub_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    razorpay_customer_id: Mapped[Optional[str]] = mapped_column(String(100))
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="subscriptions")


# ── Venue ─────────────────────────────────────────────────────────────────────

class Venue(Base):
    __tablename__ = "venue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    capacity: Mapped[Optional[int]] = mapped_column(Integer)
    pitch_type: Mapped[Optional[str]] = mapped_column(String(50))
    avg_first_innings_score: Mapped[Optional[int]] = mapped_column(Integer)
    boundary_short_m: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    boundary_long_m: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    dew_factor: Mapped[bool] = mapped_column(Boolean, default=False)
    altitude_m: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    matches: Mapped[List["Match"]] = relationship(back_populates="venue_ref")
    venue_stats: Mapped[List["VenueStat"]] = relationship(back_populates="venue")


# ── Match ────────────────────────────────────────────────────────────────────

class Match(Base):
    __tablename__ = "match"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    team_type: Mapped[str] = mapped_column(String(20), nullable=False)
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
    match_date: Mapped[date] = mapped_column(Date, nullable=False)
    day_night: Mapped[bool] = mapped_column(Boolean, default=False)
    balls_per_over: Mapped[int] = mapped_column(Integer, default=6)
    data_version: Mapped[Optional[str]] = mapped_column(String(10))
    is_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    venue_ref: Mapped[Optional["Venue"]] = relationship(back_populates="matches")
    innings_list: Mapped[List["Innings"]] = relationship(back_populates="match_ref")
    player_team_matches: Mapped[List["PlayerTeamMatch"]] = relationship(back_populates="match_ref")
    predictions: Mapped[List["Prediction"]] = relationship(back_populates="match_ref")


# ── Player ────────────────────────────────────────────────────────────────────

class Player(Base):
    __tablename__ = "player"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cricsheet_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(String(50))
    nationality: Mapped[Optional[str]] = mapped_column(String(100))
    batting_style: Mapped[Optional[str]] = mapped_column(String(30))
    bowling_style: Mapped[Optional[str]] = mapped_column(String(50))
    primary_role: Mapped[Optional[str]] = mapped_column(String(20))
    dob: Mapped[Optional[date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    player_team_matches: Mapped[List["PlayerTeamMatch"]] = relationship(back_populates="player")
    performances: Mapped[List["PlayerMatchPerformance"]] = relationship(back_populates="player")
    rolling_features: Mapped[List["RollingFeature"]] = relationship(back_populates="player")
    matchup_stats: Mapped[List["MatchupStat"]] = relationship(back_populates="player")


# ── PlayerTeamMatch ───────────────────────────────────────────────────────────

class PlayerTeamMatch(Base):
    __tablename__ = "player_team_match"
    __table_args__ = (UniqueConstraint("match_id", "player_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[str] = mapped_column(String(20), ForeignKey("match.id"), nullable=False)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    team: Mapped[str] = mapped_column(String(100), nullable=False)
    batting_order: Mapped[Optional[int]] = mapped_column(Integer)
    is_captain: Mapped[bool] = mapped_column(Boolean, default=False)
    is_keeper: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    match_ref: Mapped["Match"] = relationship(back_populates="player_team_matches")
    player: Mapped["Player"] = relationship(back_populates="player_team_matches")


# ── Innings ───────────────────────────────────────────────────────────────────

class Innings(Base):
    __tablename__ = "innings"
    __table_args__ = (UniqueConstraint("match_id", "innings_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[str] = mapped_column(String(20), ForeignKey("match.id"), nullable=False)
    innings_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    batting_team: Mapped[str] = mapped_column(String(100), nullable=False)
    bowling_team: Mapped[str] = mapped_column(String(100), nullable=False)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    total_wickets: Mapped[int] = mapped_column(Integer, default=0)
    total_overs: Mapped[float] = mapped_column(Numeric(5, 1), default=0)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    match_ref: Mapped["Match"] = relationship(back_populates="innings_list")
    deliveries: Mapped[List["Delivery"]] = relationship(back_populates="innings")


# ── Delivery ──────────────────────────────────────────────────────────────────

class Delivery(Base):
    __tablename__ = "delivery"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    innings_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("innings.id"), nullable=False)
    match_id: Mapped[str] = mapped_column(String(20), nullable=False)
    over_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ball_number: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    batter: Mapped[str] = mapped_column(String(200), nullable=False)
    bowler: Mapped[str] = mapped_column(String(200), nullable=False)
    non_striker: Mapped[Optional[str]] = mapped_column(String(200))
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    innings: Mapped["Innings"] = relationship(back_populates="deliveries")


# ── PlayerMatchPerformance ────────────────────────────────────────────────────

class PlayerMatchPerformance(Base):
    __tablename__ = "player_match_performance"
    __table_args__ = (UniqueConstraint("match_id", "player_id", "fantasy_platform"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[str] = mapped_column(String(20), ForeignKey("match.id"), nullable=False)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    team: Mapped[str] = mapped_column(String(100), nullable=False)
    runs_scored: Mapped[int] = mapped_column(Integer, default=0)
    balls_faced: Mapped[int] = mapped_column(Integer, default=0)
    fours: Mapped[int] = mapped_column(Integer, default=0)
    sixes: Mapped[int] = mapped_column(Integer, default=0)
    strike_rate: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissal_type: Mapped[Optional[str]] = mapped_column(String(50))
    batting_position: Mapped[Optional[int]] = mapped_column(SmallInteger)
    overs_bowled: Mapped[float] = mapped_column(Numeric(4, 1), default=0)
    balls_bowled: Mapped[int] = mapped_column(Integer, default=0)
    runs_conceded: Mapped[int] = mapped_column(Integer, default=0)
    wickets_taken: Mapped[int] = mapped_column(Integer, default=0)
    maidens: Mapped[int] = mapped_column(Integer, default=0)
    economy: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    dot_balls: Mapped[int] = mapped_column(Integer, default=0)
    catches: Mapped[int] = mapped_column(Integer, default=0)
    run_outs: Mapped[int] = mapped_column(Integer, default=0)
    stumpings: Mapped[int] = mapped_column(Integer, default=0)
    fantasy_points: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    fantasy_platform: Mapped[str] = mapped_column(String(30), default="dream11")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    player: Mapped["Player"] = relationship(back_populates="performances")


# ── RollingFeature ────────────────────────────────────────────────────────────

class RollingFeature(Base):
    __tablename__ = "rolling_feature"
    __table_args__ = (UniqueConstraint("player_id", "match_type", "as_of_date", "window_matches"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    window_matches: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    avg_runs: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    avg_balls: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    avg_sr: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    avg_fours: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    avg_sixes: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    avg_wickets: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    avg_economy: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    avg_overs: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    fp_avg: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    fp_ceiling: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    fp_floor: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    fp_consistency: Mapped[Optional[float]] = mapped_column(Numeric(5, 3))
    fp_last_3: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    matches_included: Mapped[Optional[int]] = mapped_column(Integer)
    last_match_id: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    player: Mapped["Player"] = relationship(back_populates="rolling_features")


# ── VenueStat ─────────────────────────────────────────────────────────────────

class VenueStat(Base):
    __tablename__ = "venue_stat"
    __table_args__ = (UniqueConstraint("venue_id", "match_type"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("venue.id"), nullable=False)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    avg_runs_per_innings: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    avg_first_innings: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    avg_second_innings: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    avg_wickets_per_match: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    spin_wicket_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    pace_wicket_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    chasing_win_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    toss_advantage: Mapped[Optional[str]] = mapped_column(String(10))
    dew_impact: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    total_matches: Mapped[Optional[int]] = mapped_column(Integer)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    venue: Mapped["Venue"] = relationship(back_populates="venue_stats")


# ── MatchupStat ───────────────────────────────────────────────────────────────

class MatchupStat(Base):
    __tablename__ = "matchup_stat"
    __table_args__ = (UniqueConstraint("player_id", "match_type", "bowler_type"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    bowler_type: Mapped[str] = mapped_column(String(50), nullable=False)
    balls_faced: Mapped[int] = mapped_column(Integer, default=0)
    runs_scored: Mapped[int] = mapped_column(Integer, default=0)
    dismissals: Mapped[int] = mapped_column(Integer, default=0)
    strike_rate: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    avg_runs: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    dot_ball_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    boundary_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    player: Mapped["Player"] = relationship(back_populates="matchup_stats")


# ── HumanRule ─────────────────────────────────────────────────────────────────

class HumanRule(Base):
    __tablename__ = "human_rule"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    player_key: Mapped[Optional[str]] = mapped_column(String(200))
    condition_json: Mapped[dict] = mapped_column(SafeJSONB, nullable=False)
    impact_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ── RuleTrigger ───────────────────────────────────────────────────────────────

class RuleTrigger(Base):
    __tablename__ = "rule_trigger"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prediction.id"), nullable=False)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("human_rule.id"), nullable=False)
    rule_ext_id: Mapped[Optional[str]] = mapped_column(String(20))  # RULE-0001 style
    impact_applied: Mapped[float] = mapped_column(Numeric(6, 2))
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── Prediction ────────────────────────────────────────────────────────────────

class Prediction(Base):
    __tablename__ = "prediction"
    __table_args__ = (UniqueConstraint("match_id", "user_id", "match_phase"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[str] = mapped_column(String(20), ForeignKey("match.id"), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"))
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    ensemble_weights: Mapped[Optional[dict]] = mapped_column(SafeJSONB)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    match_phase: Mapped[Optional[str]] = mapped_column(String(20))

    match_ref: Mapped["Match"] = relationship(back_populates="predictions")
    predicted_players: Mapped[List["PredictedPlayer"]] = relationship(back_populates="prediction")
    recommended_teams: Mapped[List["RecommendedTeam"]] = relationship(back_populates="prediction")


# ── PredictedPlayer ───────────────────────────────────────────────────────────

class PredictedPlayer(Base):
    __tablename__ = "predicted_player"
    __table_args__ = (UniqueConstraint("prediction_id", "player_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prediction.id"), nullable=False)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    ensemble_score: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    ml_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 3))
    rules_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 3))
    form_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 3))
    live_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 3))
    fp_predicted: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    fp_ceiling: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    fp_floor: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    confidence: Mapped[Optional[int]] = mapped_column(SmallInteger)
    rank: Mapped[Optional[int]] = mapped_column(SmallInteger)
    rules_fired: Mapped[Optional[dict]] = mapped_column(SafeJSONB)
    explanation: Mapped[Optional[str]] = mapped_column(Text)

    prediction: Mapped["Prediction"] = relationship(back_populates="predicted_players")


# ── RecommendedTeam ───────────────────────────────────────────────────────────

class RecommendedTeam(Base):
    __tablename__ = "recommended_team"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prediction.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    captain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    vice_captain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), nullable=False)
    total_credits: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    prediction: Mapped["Prediction"] = relationship(back_populates="recommended_teams")
    team_players: Mapped[List["TeamPlayer"]] = relationship(back_populates="team")


# ── TeamPlayer ────────────────────────────────────────────────────────────────

class TeamPlayer(Base):
    __tablename__ = "team_player"

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recommended_team.id"), primary_key=True)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("player.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    credits: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))

    team: Mapped["RecommendedTeam"] = relationship(back_populates="team_players")


# ── ChatSession ───────────────────────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    match_id: Mapped[Optional[str]] = mapped_column(String(20))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(back_populates="session")


# ── ChatMessage ───────────────────────────────────────────────────────────────

class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_session.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)   # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


# ── BacktestRun ───────────────────────────────────────────────────────────────

class BacktestRun(Base):
    __tablename__ = "backtest_run"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    match_type: Mapped[Optional[str]] = mapped_column(String(20))
    from_date: Mapped[Optional[date]] = mapped_column(Date)
    to_date: Mapped[Optional[date]] = mapped_column(Date)
    total_matches: Mapped[Optional[int]] = mapped_column(Integer)
    correct_player_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 3))
    captain_accuracy: Mapped[Optional[float]] = mapped_column(Numeric(5, 3))
    avg_fp_error: Mapped[Optional[float]] = mapped_column(Numeric(7, 3))
    simulated_roi: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── ModelVersion ──────────────────────────────────────────────────────────────

class ModelVersion(Base):
    __tablename__ = "model_version"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    match_type: Mapped[Optional[str]] = mapped_column(String(20))
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    feature_count: Mapped[Optional[int]] = mapped_column(Integer)
    train_mae: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    val_mae: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    train_from: Mapped[Optional[date]] = mapped_column(Date)
    train_to: Mapped[Optional[date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── AdminAction ───────────────────────────────────────────────────────────────

class AdminAction(Base):
    __tablename__ = "admin_action"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(50))
    target_id: Mapped[Optional[str]] = mapped_column(String(100))
    payload: Mapped[Optional[dict]] = mapped_column(SafeJSONB)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
