"""Dream11 team constraints (OPTIMIZATION_ENGINE_SPEC §2) and team validation."""
from __future__ import annotations

from collections import Counter
from typing import Iterable, List

from backend.config import settings

ROLES = ("WK", "BAT", "AR", "BOWL")
ROLE_MIN = {"WK": settings.MIN_WK, "BAT": settings.MIN_BAT, "AR": settings.MIN_AR, "BOWL": settings.MIN_BOWL}
ROLE_MAX = {"WK": settings.MAX_WK, "BAT": settings.MAX_BAT, "AR": settings.MAX_AR, "BOWL": settings.MAX_BOWL}
TEAM_SIZE = settings.TOTAL_PLAYERS
MAX_CREDITS = settings.MAX_CREDITS
MAX_PER_TEAM = settings.MAX_PLAYERS_PER_TEAM
CAPTAIN_MULT = 2.0
VC_MULT = 1.5


def team_violations(players: Iterable, captain_id=None, vc_id=None) -> List[str]:
    """Return a list of human-readable rule violations (empty = valid team)."""
    ps = list(players)
    errs: List[str] = []
    if len(ps) != TEAM_SIZE:
        errs.append(f"team has {len(ps)} players, needs {TEAM_SIZE}")
    credits = sum(p.credits for p in ps)
    if credits > MAX_CREDITS + 1e-6:
        errs.append(f"credits {credits:.1f} exceed {MAX_CREDITS}")
    roles = Counter(p.role for p in ps)
    for r in ROLES:
        if not ROLE_MIN[r] <= roles.get(r, 0) <= ROLE_MAX[r]:
            errs.append(f"{r} count {roles.get(r, 0)} outside {ROLE_MIN[r]}-{ROLE_MAX[r]}")
    teams = Counter(p.team for p in ps)
    if teams and max(teams.values()) > MAX_PER_TEAM:
        errs.append(f"more than {MAX_PER_TEAM} players from one team")
    if len(teams) < 2 and ps:
        errs.append("both teams must be represented")
    if captain_id is not None and captain_id == vc_id:
        errs.append("captain and vice-captain must differ")
    ids = {p.player_id for p in ps}
    if captain_id is not None and captain_id not in ids:
        errs.append("captain not in team")
    if vc_id is not None and vc_id not in ids:
        errs.append("vice-captain not in team")
    return errs
