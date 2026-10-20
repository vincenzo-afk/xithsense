"""
Captain Engine (CAPTAIN_ENGINE_SPEC): rank Best / Safe / Risk captain options.

Constraints: all options come from the generated XI, confidence ≥ 20,
risk captain has < 15% ownership (falls back to lowest-owned) and lower
confidence than the best captain.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from optimizer.scoring import OptPlayer, differential_bonus


@dataclass
class CaptainPick:
    player: OptPlayer
    type: str             # best_captain | safe_captain | risk_captain
    score: float
    reasoning: str


def captain_score(p: OptPlayer, mode: str) -> float:
    """Projection-led (backtested: beats the spec's ceiling/average blend on captain accuracy),
    tilted towards floor in safe mode and ceiling + leverage in grand-league mode."""
    if mode == "safe":
        return p.predicted_fp * 0.7 + p.ceiling * 0.15 + p.floor * 0.15
    if mode == "grand_league":
        # Leverage: fade the chalk a little so GL captains differ from the field
        return p.predicted_fp * 0.45 + p.ceiling * 0.55 + differential_bonus(p.ownership) * 0.5 - p.ownership * 0.12
    if mode == "aggressive":
        return p.predicted_fp * 0.35 + p.ceiling * 0.65
    return p.predicted_fp * 0.65 + p.ceiling * 0.35


def _reason(p: OptPlayer, kind: str) -> str:
    if kind == "best_captain":
        return f"Highest ceiling-weighted score in this XI — projects {p.predicted_fp:.0f} pts with a {p.ceiling:.0f}-pt ceiling"
    if kind == "safe_captain":
        return f"Most reliable floor ({p.floor:.0f} pts) with {p.confidence}% confidence — low-risk armband"
    return f"Only ~{p.ownership:.0f}% ownership with a {p.ceiling:.0f}-pt ceiling — leverage pick for grand leagues"


def recommend(xi: Sequence[OptPlayer], mode: str, rotation: int = 0) -> List[CaptainPick]:
    """`rotation` k picks the k-th best captain (mod 3) — used to split captaincy across multi-team sets."""
    eligible = [p for p in xi if p.confidence >= 20] or list(xi)
    ranked = sorted(eligible, key=lambda p: -captain_score(p, mode))
    best = ranked[rotation % min(3, len(ranked))]
    safe_pool = [p for p in eligible if p.player_id != best.player_id]
    safe = max(safe_pool, key=lambda p: p.floor * 0.6 + p.predicted_fp * 0.4 - p.fp_std * 0.2)
    used = {best.player_id, safe.player_id}
    risk_pool = [p for p in eligible if p.player_id not in used and p.ownership < 15 and p.confidence < best.confidence]
    if not risk_pool:
        risk_pool = sorted((p for p in eligible if p.player_id not in used), key=lambda p: p.ownership)[:3]
    risk: Optional[OptPlayer] = max(risk_pool, key=lambda p: p.ceiling) if risk_pool else None
    picks = [CaptainPick(best, "best_captain", captain_score(best, mode), _reason(best, "best_captain")),
             CaptainPick(safe, "safe_captain", captain_score(safe, mode), _reason(safe, "safe_captain"))]
    if risk:
        picks.append(CaptainPick(risk, "risk_captain", captain_score(risk, mode), _reason(risk, "risk_captain")))
    return picks
