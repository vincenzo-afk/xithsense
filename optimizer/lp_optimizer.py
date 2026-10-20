"""
Team Optimizer: Dream11-compliant XI selection with captain and vice-captain.

Primary solver is an integer linear program (PuLP/CBC, OPTIMIZATION_ENGINE_SPEC §3).
If PuLP is unavailable or the LP is infeasible, a randomised local search
(the GA-fallback slot) produces a valid team; if even that fails, WK/AR maxima
are relaxed by one as BUSINESS_RULES prescribes.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set

from optimizer.constraints import (
    MAX_CREDITS, MAX_PER_TEAM, ROLE_MAX, ROLE_MIN, ROLES, TEAM_SIZE, team_violations,
)
from optimizer.scoring import OptPlayer

logger = logging.getLogger(__name__)


@dataclass
class SolveResult:
    players: List[OptPlayer]
    captain: OptPlayer
    vice_captain: OptPlayer
    solver: str
    solve_time_ms: int


def _lp_solve(players: Sequence[OptPlayer], previous: Sequence[Set[str]], max_overlap: int,
              min_differentials: int, role_max: Dict[str, int]) -> Optional[tuple[list[int], int, int]]:
    try:
        import pulp  # type: ignore
    except ImportError:
        return None
    n = len(players)
    prob = pulp.LpProblem("XithSense_Team", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]
    c = [pulp.LpVariable(f"c_{i}", cat="Binary") for i in range(n)]
    v = [pulp.LpVariable(f"v_{i}", cat="Binary") for i in range(n)]
    s = [p.score for p in players]

    prob += pulp.lpSum(s[i] * x[i] + s[i] * c[i] + 0.5 * s[i] * v[i] for i in range(n))
    prob += pulp.lpSum(x) == TEAM_SIZE
    prob += pulp.lpSum(players[i].credits * x[i] for i in range(n)) <= MAX_CREDITS
    for role in ROLES:
        idx = [i for i, p in enumerate(players) if p.role == role]
        prob += pulp.lpSum(x[i] for i in idx) >= ROLE_MIN[role]
        prob += pulp.lpSum(x[i] for i in idx) <= role_max[role]
    for team in {p.team for p in players}:
        idx = [i for i, p in enumerate(players) if p.team == team]
        prob += pulp.lpSum(x[i] for i in idx) <= MAX_PER_TEAM
        prob += pulp.lpSum(x[i] for i in idx) >= 1
    prob += pulp.lpSum(c) == 1
    prob += pulp.lpSum(v) == 1
    for i in range(n):
        prob += c[i] <= x[i]
        prob += v[i] <= x[i]
        prob += c[i] + v[i] <= 1
    for k, prev in enumerate(previous):
        idx = [i for i, p in enumerate(players) if p.player_id in prev]
        prob += pulp.lpSum(x[i] for i in idx) <= max_overlap, f"diversity_{k}"
    if min_differentials:
        idx = [i for i, p in enumerate(players) if p.ownership < 20]
        if len(idx) >= min_differentials:
            prob += pulp.lpSum(x[i] for i in idx) >= min_differentials

    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=10))
    if pulp.LpStatus[prob.status] != "Optimal":
        return None
    sel = [i for i in range(n) if (pulp.value(x[i]) or 0) > 0.5]
    cap = next(i for i in range(n) if (pulp.value(c[i]) or 0) > 0.5)
    vc = next(i for i in range(n) if (pulp.value(v[i]) or 0) > 0.5)
    return sel, cap, vc


def _valid(players: Sequence[OptPlayer], role_max: Dict[str, int]) -> bool:
    if len(players) != TEAM_SIZE or sum(p.credits for p in players) > MAX_CREDITS + 1e-9:
        return False
    counts: Dict[str, int] = {}
    teams: Dict[str, int] = {}
    for p in players:
        counts[p.role] = counts.get(p.role, 0) + 1
        teams[p.team] = teams.get(p.team, 0) + 1
    if any(not ROLE_MIN[r] <= counts.get(r, 0) <= role_max[r] for r in ROLES):
        return False
    return max(teams.values()) <= MAX_PER_TEAM and len(teams) >= 2


def _local_search(players: Sequence[OptPlayer], previous: Sequence[Set[str]], max_overlap: int,
                  role_max: Dict[str, int], iters: int = 4000, seed: int = 7) -> Optional[list[int]]:
    """Randomised greedy construction + swap hill-climbing (GA fallback slot)."""
    rng = random.Random(seed)
    n = len(players)

    def ok(sel: List[int]) -> bool:
        team = [players[i] for i in sel]
        if not _valid(team, role_max):
            return False
        ids = {p.player_id for p in team}
        return all(len(ids & prev) <= max_overlap for prev in previous)

    def value(sel: List[int]) -> float:
        sc = sorted((players[i].score for i in sel), reverse=True)
        return sum(sc) + sc[0] + 0.5 * sc[1]

    best: Optional[List[int]] = None
    for attempt in range(200):
        order = sorted(range(n), key=lambda i: -(players[i].score + rng.uniform(0, 15 if attempt else 0)))
        sel: List[int] = []
        need = dict(ROLE_MIN)
        for i in order:
            p = players[i]
            slots_left = TEAM_SIZE - len(sel)
            mandatory = sum(max(0, need[r]) for r in ROLES)
            if need[p.role] <= 0 and slots_left <= mandatory:
                continue
            cand = sel + [i]
            team = [players[j] for j in cand]
            counts = {r: sum(1 for t in team if t.role == r) for r in ROLES}
            tcount: Dict[str, int] = {}
            for t in team:
                tcount[t.team] = tcount.get(t.team, 0) + 1
            if counts[p.role] > role_max[p.role] or max(tcount.values()) > MAX_PER_TEAM:
                continue
            if sum(t.credits for t in team) > MAX_CREDITS:
                continue
            sel = cand
            need[p.role] -= 1
            if len(sel) == TEAM_SIZE:
                break
        if len(sel) == TEAM_SIZE and ok(sel):
            best = sel
            break
    if best is None:
        return None
    cur, cur_v = list(best), value(best)
    for _ in range(iters):
        i_out = rng.randrange(TEAM_SIZE)
        j_in = rng.randrange(n)
        if j_in in cur:
            continue
        cand = list(cur)
        cand[i_out] = j_in
        if ok(cand):
            v = value(cand)
            if v > cur_v:
                cur, cur_v = cand, v
    return cur


def solve_team(players: Sequence[OptPlayer], previous: Sequence[Set[str]] = (), max_overlap: int = 9,
               min_differentials: int = 0) -> Optional[SolveResult]:
    """Pick the optimal XI + C/VC for players whose `.score` is already set."""
    t0 = time.perf_counter()
    for relax in (0, 1):
        role_max = {r: ROLE_MAX[r] + (relax if r in ("WK", "AR") else 0) for r in ROLES}
        lp = _lp_solve(players, previous, max_overlap, min_differentials, role_max)
        if lp is not None:
            sel, cap, vc = lp
            team = [players[i] for i in sel]
            return SolveResult(team, players[cap], players[vc], "lp", int((time.perf_counter() - t0) * 1000))
        ls = _local_search(players, previous, max_overlap, role_max)
        if ls is not None:
            team = sorted((players[i] for i in ls), key=lambda p: -p.score)
            return SolveResult(team, team[0], team[1], "local_search", int((time.perf_counter() - t0) * 1000))
    logger.warning("Optimizer infeasible for %d players", len(players))
    return None


def build_team(players: List[OptPlayer], mode: str) -> List[OptPlayer]:
    """Backward-compatible helper: score for `mode` and return the XI."""
    from optimizer.scoring import score_for_mode
    score_for_mode(players, mode)
    res = solve_team(players)
    return res.players if res else []


__all__ = ["solve_team", "build_team", "SolveResult", "team_violations"]
