"""
Mode-specific objective scores, differential bonus and ownership estimation.

Formulas follow OPTIMIZATION_ENGINE_SPEC §4 and OWNERSHIP_ESTIMATION_SPEC (MVP
heuristic), using model predictions in place of raw rolling averages.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

MODES = ("safe", "grand_league", "aggressive", "small_league")


@dataclass
class OptPlayer:
    player_id: str
    full_name: str
    role: str                  # WK | BAT | AR | BOWL
    credits: float
    team: str
    predicted_fp: float
    ceiling: float
    floor: float
    fp_std: float = 0.0
    fp_avg_5: float = 0.0
    fp_avg_10: float = 0.0
    consistency: float = 1.0   # std / avg (lower = more consistent)
    ownership: float = 50.0    # estimated % of teams picking this player
    confidence: int = 50
    ensemble_score: float = 50.0
    is_differential: bool = False
    score: float = 0.0         # mode objective (filled by score_for_mode)
    extra: dict = field(default_factory=dict)


def differential_bonus(ownership_pct: float) -> float:
    if ownership_pct < 5:
        return 20.0
    if ownership_pct < 10:
        return 12.0
    if ownership_pct < 20:
        return 6.0
    return 0.0


def score_for_mode(players: List[OptPlayer], mode: str) -> None:
    """Set `p.score` in place for the requested team mode."""
    if mode == "safe":
        ranked = sorted(players, key=lambda p: p.consistency)
        top15 = {p.player_id for p in ranked[:15]}
        for p in players:
            p.score = p.predicted_fp - 0.3 * p.fp_std + (5.0 if p.player_id in top15 else 0.0)
    elif mode == "grand_league":
        for p in players:
            p.score = 0.6 * p.ceiling + 0.4 * p.predicted_fp + differential_bonus(p.ownership)
    elif mode == "aggressive":
        for p in players:
            p.score = p.ceiling
    elif mode == "small_league":
        for p in players:
            p.score = 0.5 * p.predicted_fp + 0.35 * p.ceiling + 0.5 * differential_bonus(p.ownership)
    else:
        raise ValueError(f"unknown mode {mode}")


def estimate_ownership(scores: List[float], roles: List[str], knockout: bool = False) -> List[float]:
    """OWNERSHIP_ESTIMATION_SPEC MVP heuristic: rank-based power curve with boosts."""
    n = len(scores)
    if n == 0:
        return []
    mx = max(scores) or 1.0
    order = sorted(scores, reverse=True)
    out = []
    for s, role in zip(scores, roles):
        rank = order.index(s) + 1
        rank_pct = rank / n
        own = (1 - rank_pct) ** 1.8 * 85 + 2.0
        if role == "WK" and rank <= 3:
            own *= 1.4
        if s / mx > 0.95:
            own = min(own * 1.3, 90)
        if knockout:
            own *= 0.85
        out.append(round(max(0.5, min(95.0, own)), 1))
    return out


def ownership_tier(own: float) -> str:
    if own < 3:
        return "unique"
    if own < 10:
        return "punt"
    if own < 25:
        return "differential"
    if own < 50:
        return "moderate"
    if own <= 75:
        return "popular"
    return "lock"


def confidence_label(c: float) -> str:
    return "High" if c >= 80 else "Medium" if c >= 60 else "Low" if c >= 40 else "Very Low"
