"""
Team Optimizer: generates Dream11-compliant teams using Linear Programming (PuLP).
Falls back to greedy solver if PuLP is not installed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)

ROLE_MIN = {"WK": settings.MIN_WK, "BAT": settings.MIN_BAT, "AR": settings.MIN_AR, "BOWL": settings.MIN_BOWL}
ROLE_MAX = {"WK": settings.MAX_WK, "BAT": settings.MAX_BAT, "AR": settings.MAX_AR, "BOWL": settings.MAX_BOWL}


@dataclass
class OptPlayer:
    player_id: str
    full_name: str
    role: str          # WK | BAT | AR | BOWL
    credits: float
    score: float       # ensemble score for this mode
    ceiling: float
    floor: float
    confidence: int
    team: str          # which real team (team_a / team_b)
    is_differential: bool = False
    ownership_estimate: str = "N/A"


def _greedy_solve(players: List[OptPlayer], mode: str) -> List[OptPlayer]:
    """Greedy fallback: select highest-score players respecting constraints."""
    # Sort by score descending
    sorted_players = sorted(players, key=lambda p: p.score, reverse=True)
    selected: List[OptPlayer] = []
    role_count: Dict[str, int] = {"WK": 0, "BAT": 0, "AR": 0, "BOWL": 0}
    team_count: Dict[str, int] = {}
    total_credits = 0.0

    for p in sorted_players:
        if len(selected) >= settings.TOTAL_PLAYERS:
            break
        if total_credits + p.credits > settings.MAX_CREDITS:
            continue
        if role_count.get(p.role, 0) >= ROLE_MAX[p.role]:
            continue
        tc = team_count.get(p.team, 0)
        if tc >= settings.MAX_PLAYERS_PER_TEAM:
            continue
        selected.append(p)
        role_count[p.role] = role_count.get(p.role, 0) + 1
        team_count[p.team] = tc + 1
        total_credits += p.credits

    # Validate minimums
    for role, min_count in ROLE_MIN.items():
        if role_count.get(role, 0) < min_count:
            logger.warning(f"Greedy solver could not satisfy min for role {role}")

    return selected


def _lp_solve(players: List[OptPlayer], mode: str) -> Optional[List[OptPlayer]]:
    """Linear programming optimizer via PuLP."""
    try:
        import pulp  # type: ignore
    except ImportError:
        logger.warning("PuLP not installed; falling back to greedy solver")
        return None

    n = len(players)
    prob = pulp.LpProblem("fantasy_team", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]

    # Objective: maximise ensemble score
    prob += pulp.lpSum(players[i].score * x[i] for i in range(n))

    # Constraints
    prob += pulp.lpSum(x) == settings.TOTAL_PLAYERS, "team_size"
    prob += pulp.lpSum(players[i].credits * x[i] for i in range(n)) <= settings.MAX_CREDITS, "credits"

    for role in ["WK", "BAT", "AR", "BOWL"]:
        idxs = [i for i, p in enumerate(players) if p.role == role]
        prob += pulp.lpSum(x[i] for i in idxs) >= ROLE_MIN[role], f"min_{role}"
        prob += pulp.lpSum(x[i] for i in idxs) <= ROLE_MAX[role], f"max_{role}"

    teams = set(p.team for p in players)
    for team in teams:
        idxs = [i for i, p in enumerate(players) if p.team == team]
        prob += pulp.lpSum(x[i] for i in idxs) <= settings.MAX_PLAYERS_PER_TEAM, f"max_per_team_{team}"

    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)

    if pulp.LpStatus[prob.status] != "Optimal":
        logger.warning("LP solver did not find optimal solution")
        return None

    return [players[i] for i in range(n) if pulp.value(x[i]) == 1]


def build_team(players: List[OptPlayer], mode: str) -> List[OptPlayer]:
    """
    Build a Dream11-compliant team of 11 players.
    Uses LP optimizer with greedy fallback.
    """
    # For grand_league: boost differential players' scores
    adjusted = []
    for p in players:
        score = p.score
        if mode == "grand_league" and p.is_differential:
            score *= 1.3
        elif mode == "aggressive":
            score = p.ceiling * 0.7 + p.score * 0.3
        elif mode == "small_league":
            # Favour consistent players
            score = (p.score + p.floor) / 2
        adjusted.append(OptPlayer(**{**p.__dict__, "score": score}))

    result = _lp_solve(adjusted, mode)
    if result is None:
        result = _greedy_solve(adjusted, mode)
    return result
