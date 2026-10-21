"""
Inference engine: squad → features → ML + human rules + form (+ live) ensemble.

Produces one `PlayerScore` per squad player for a match. HTTP-independent so
the API, the backtester and the chat assistant all share it.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import Delivery, Match, Player, PlayerTeamMatch, Venue
from feature_engineering.builder import Frames, build_feature_frame, load_frames
from human_rules.engine import MatchContext, evaluate_rules_detailed
from optimizer.scoring import OptPlayer, estimate_ownership
from training.models import load_active

logger = logging.getLogger(__name__)


@dataclass
class PlayerScore:
    player_id: str
    cricsheet_key: str
    full_name: str
    role: str
    team: str
    credits: float
    batting_style: Optional[str]
    bowling_style: Optional[str]
    is_playing: bool
    predicted_fp: float
    fp_ceiling: float
    fp_floor: float
    fp_std: float
    fp_avg_3: float
    fp_avg_5: float
    fp_avg_10: float
    fp_30plus_rate: float
    consistency: float
    confidence: int
    ownership: float
    is_differential: bool
    ensemble_score: float
    ml_score: float
    rules_score: float
    form_score: float
    live_score: float
    components_norm: Dict[str, float]
    rules_fired: List[dict]
    features: Dict[str, float]
    low_data: bool

    def to_opt(self) -> OptPlayer:
        return OptPlayer(
            player_id=self.player_id, full_name=self.full_name, role=self.role, credits=self.credits,
            team=self.team, predicted_fp=self.predicted_fp, ceiling=self.fp_ceiling, floor=self.fp_floor,
            fp_std=self.fp_std, fp_avg_5=self.fp_avg_5, fp_avg_10=self.fp_avg_10, consistency=self.consistency,
            ownership=self.ownership, confidence=self.confidence, ensemble_score=self.ensemble_score,
            is_differential=self.is_differential,
        )


@dataclass
class MatchScores:
    match: Match
    venue: Optional[Venue]
    players: List[PlayerScore]
    weights: Dict[str, float]
    phase: str                      # pre_toss | post_toss | live
    model_version: Optional[str]
    xi_confirmed: bool
    computed_ms: int
    by_id: Dict[str, PlayerScore] = field(default_factory=dict)

    def __post_init__(self):
        self.by_id = {p.player_id: p for p in self.players}


# ── Process-level caches (invalidated after ingest / retrain) ─────────────────

class _Cache:
    frames: Optional[Frames] = None
    bowler_death_share: Dict[str, float] = {}
    scores: Dict[tuple, MatchScores] = {}
    lock = asyncio.Lock()
    generation = 0


def invalidate_caches() -> None:
    _Cache.frames = None
    _Cache.bowler_death_share = {}
    _Cache.scores = {}
    _Cache.generation += 1


async def _get_frames(db: AsyncSession) -> Frames:
    if _Cache.frames is None:
        async with _Cache.lock:
            if _Cache.frames is None:
                t0 = time.perf_counter()
                _Cache.frames = await load_frames(db)
                _Cache.bowler_death_share = _Cache.frames.death_share or {}
                logger.info("Feature frames loaded in %.0f ms", (time.perf_counter() - t0) * 1000)
    return _Cache.frames


def _minmax(x: np.ndarray) -> np.ndarray:
    lo, hi = float(np.min(x)), float(np.max(x))
    if hi - lo < 1e-9:
        return np.full_like(x, 50.0, dtype=float)
    return (x - lo) / (hi - lo) * 100.0


def _weights(phase: str) -> Dict[str, float]:
    w = {"ml": settings.ENSEMBLE_ML_WEIGHT, "human_rules": settings.ENSEMBLE_HUMAN_RULES_WEIGHT,
         "form": settings.ENSEMBLE_FORM_WEIGHT, "live": settings.ENSEMBLE_LIVE_WEIGHT}
    if phase != "live":
        # Live component is 0 before the match starts — re-normalise the rest (ENSEMBLE_STRATEGY)
        w["live"] = 0.0
    total = sum(w.values()) or 1.0
    return {k: round(v / total, 4) for k, v in w.items()}


async def score_match(db: AsyncSession, match_id: str, override_toss: Optional[dict] = None,
                      live_fp: Optional[Dict[str, float]] = None) -> MatchScores:
    match = await db.get(Match, match_id)
    if match is None:
        raise LookupError(match_id)
    toss_winner = (override_toss or {}).get("winner", match.toss_winner)
    toss_decision = (override_toss or {}).get("decision", match.toss_decision)
    phase = "live" if match.status == "live" else ("post_toss" if toss_winner else "pre_toss")
    from feature_engineering.builder import FORMAT_GROUP
    group = FORMAT_GROUP.get(match.match_type, "T20")
    model = load_active(group)
    cache_key = (match_id, toss_winner, toss_decision, match.playing_xi_confirmed, phase,
                 model.version if model else None, _Cache.generation)
    if live_fp is None and cache_key in _Cache.scores:
        return _Cache.scores[cache_key]

    t0 = time.perf_counter()
    frames = await _get_frames(db)
    venue = await db.get(Venue, match.venue_id) if match.venue_id else None

    rows = (await db.execute(
        select(PlayerTeamMatch, Player).join(Player, Player.id == PlayerTeamMatch.player_id)
        .where(PlayerTeamMatch.match_id == match_id)
    )).all()
    if match.playing_xi_confirmed:
        rows = [r for r in rows if r[0].is_playing]
    per_team = {t: sum(1 for ptm, _ in rows if ptm.team == t) for t in (match.team_a, match.team_b)}
    if min(per_team.values()) < 11:
        raise ValueError("PREDICTION_NO_PLAYERS")

    batting_first = None
    if toss_winner and toss_decision:
        other = match.team_b if toss_winner == match.team_a else match.team_a
        batting_first = toss_winner if toss_decision == "bat" else other

    pending = pd.DataFrame([{
        "match_id": match_id, "player_id": ptm.player_id, "match_date": match.match_date,
        "match_type": match.match_type, "venue_name": match.venue_name, "team": ptm.team,
        "opposition": match.team_b if ptm.team == match.team_a else match.team_a,
        "is_chasing": (ptm.team != batting_first) if batting_first else np.nan,
        "event_stage": match.event_stage, "pitch_type": venue.pitch_type if venue else None, "fp": np.nan,
    } for ptm, _ in rows])
    feat_all = build_feature_frame(frames, pending)
    feat = feat_all[feat_all.is_pending & (feat_all.match_id == match_id)].set_index("player_id")
    feat = feat.loc[[ptm.player_id for ptm, _ in rows]]

    # ── ML component ──────────────────────────────────────────────────────
    if model is not None:
        pred = model.predict(feat)
        ml, m_ceil, m_floor = pred["ml"], pred["ceiling"], pred["floor"]
    else:  # cold start: no trained model yet
        ml = (0.6 * feat.fp_avg_5 + 0.4 * feat.career_fp_avg).values
        m_ceil, m_floor = feat.fp_ceiling.values, feat.fp_floor.values

    # ── Human rules component ─────────────────────────────────────────────
    opp_types: Dict[str, set] = {}
    for team in (match.team_a, match.team_b):
        opp_types[team] = {p.bowler_type for ptm, p in rows
                           if ptm.team != team and p.bowler_type and p.primary_role in ("BOWL", "AR")}
    rules_adj, rules_fired = [], []
    importance = float(feat.match_importance.iloc[0]) if len(feat) else 0.5
    for ptm, p in rows:
        f = feat.loc[ptm.player_id]
        is_chasing = None if not batting_first else ptm.team != batting_first
        death = _Cache.bowler_death_share.get(p.id, 0.0)
        ctx = MatchContext(
            match_type=match.match_type, venue=match.venue_name,
            pitch_type=venue.pitch_type if venue else None, is_chasing=is_chasing,
            toss_decision=toss_decision, opposition_bowling_type=frozenset(opp_types.get(ptm.team, set())),
            phase="death" if p.primary_role in ("BOWL", "AR") and death >= 0.25 else None,
            batting_position=int(round(f.avg_bat_pos_5)) if f.avg_bat_pos_5 > 0 else None,
            is_final_or_knockout=importance > 0.6, is_home=bool(f.is_home),
            rest_days=int(f.days_since_last_match) if f.days_since_last_match < 30 else None,
            batting_style=p.batting_style, bowling_style=p.bowling_style, primary_role=p.primary_role,
            match_date=match.match_date,
        )
        adj, fired = evaluate_rules_detailed(p.cricsheet_key, ctx)
        rules_adj.append(adj)
        rules_fired.append(fired)
    rules_adj = np.array(rules_adj, dtype=float)

    # ── Form + live components ────────────────────────────────────────────
    form = (0.5 * feat.fp_avg_3 + 0.3 * feat.fp_avg_5 + 0.2 * feat.fp_avg_10).values
    live = np.array([float((live_fp or {}).get(str(ptm.player_id), 0.0)) for ptm, _ in rows])

    weights = _weights(phase)
    norm = {"ml": _minmax(ml), "human_rules": _minmax(rules_adj), "form": _minmax(form), "live": _minmax(live)}
    ensemble = sum(weights[k] * norm[k] for k in weights)

    # Point projections: model estimate shifted by rule impact (rule impacts are point-scaled)
    predicted = np.clip(ml + 0.35 * rules_adj, 0, None)
    hist_ceil, hist_floor = feat.fp_ceiling.values, feat.fp_floor.values
    ceiling = np.maximum(0.6 * m_ceil + 0.4 * hist_ceil + 0.35 * rules_adj, predicted * 1.25)
    floor = np.clip(np.minimum(0.6 * m_floor + 0.4 * hist_floor, predicted * 0.8), 0, None)
    if phase == "live":
        predicted = np.maximum(predicted, live)
        ceiling = np.maximum(ceiling, live)

    roles = [p.primary_role or "BAT" for _, p in rows]
    ownership = estimate_ownership(list(ensemble), roles, knockout=importance > 0.6)
    mean_ceiling = float(np.mean(ceiling))
    max_ens = float(np.max(ensemble)) or 1.0

    players: List[PlayerScore] = []
    for i, (ptm, p) in enumerate(rows):
        f = feat.loc[ptm.player_id]
        cv = float(min(f.fp_consistency, 1.0))
        conf = ensemble[i] / max_ens * 75 + (1 - cv) * 15 + float(f.matchup_confidence) * 10
        conf = int(max(1, min(100, round(conf))))
        if bool(f.low_data):
            conf = min(conf, 50)
        own = ownership[i]
        is_diff = own < 20 and ceiling[i] > 0.85 * mean_ceiling and f.fp_avg_10 > 15 and f.fp_30plus_rate > 0.2
        credits = ptm.credits or p.base_credits or 8.0
        players.append(PlayerScore(
            player_id=str(p.id), cricsheet_key=p.cricsheet_key, full_name=p.full_name, role=roles[i],
            team=ptm.team, credits=float(credits), batting_style=p.batting_style, bowling_style=p.bowling_style,
            is_playing=bool(ptm.is_playing),
            predicted_fp=round(float(predicted[i]), 1), fp_ceiling=round(float(ceiling[i]), 1),
            fp_floor=round(float(floor[i]), 1), fp_std=round(float(f.fp_std_10), 1),
            fp_avg_3=round(float(f.fp_avg_3), 1), fp_avg_5=round(float(f.fp_avg_5), 1),
            fp_avg_10=round(float(f.fp_avg_10), 1), fp_30plus_rate=round(float(f.fp_30plus_rate), 2),
            consistency=round(float(f.fp_consistency), 3), confidence=conf, ownership=own,
            is_differential=bool(is_diff), ensemble_score=round(float(ensemble[i]), 2),
            ml_score=round(float(ml[i]), 2), rules_score=round(float(rules_adj[i]), 2),
            form_score=round(float(form[i]), 2), live_score=round(float(live[i]), 2),
            components_norm={k: round(float(v[i]), 1) for k, v in norm.items()},
            rules_fired=rules_fired[i],
            features={k: round(float(f[k]), 3) for k in (
                "fp_avg_3", "fp_avg_5", "fp_avg_10", "venue_fp_avg", "venue_matches", "sr_vs_spin", "sr_vs_pace",
                "opp_spin_share", "expected_matchup_sr", "avg_sr_5", "avg_runs_5", "avg_wickets_5",
                "avg_economy_5", "is_chasing", "is_home", "career_matches", "venue_avg_first_innings",
                "venue_chasing_win_pct", "days_since_last_match", "matchup_confidence", "opposition_fp_allowed")},
            low_data=bool(f.low_data),
        ))
    players.sort(key=lambda s: -s.ensemble_score)
    result = MatchScores(match=match, venue=venue, players=players, weights=weights, phase=phase,
                         model_version=model.version if model else None, xi_confirmed=match.playing_xi_confirmed,
                         computed_ms=int((time.perf_counter() - t0) * 1000))
    if live_fp is None:
        _Cache.scores[cache_key] = result
    return result
