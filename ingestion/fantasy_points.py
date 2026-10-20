"""
Fantasy Points Calculator — canonical XithSense Dream11 subset.

Matches docs/FEATURE_FORMULAS.md §1 and the acceptance criteria (AC-03, TC-01):

    batting:  run +1, four +1, six +2, 50 +8 / 100 +16 (not cumulative),
              duck -2 (dismissed for 0; BAT/WK/AR only)
    bowling:  wicket +25, LBW/bowled +8, 4-wkt +8 / 5-wkt +16 (not cumulative),
              maiden +4
    fielding: catch +8, stumping +12, run-out direct +12 / indirect +6
"""
from __future__ import annotations

from typing import Optional

BATTING_POINTS = {
    "run": 1,
    "boundary_bonus": 1,
    "six_bonus": 2,
    "half_century_bonus": 8,
    "century_bonus": 16,
    "duck_penalty": -2,
}

BOWLING_POINTS = {
    "wicket": 25,
    "lbw_bowled_bonus": 8,
    "four_wicket_bonus": 8,
    "five_wicket_bonus": 16,
    "maiden": 4,
}

FIELDING_POINTS = {
    "catch": 8,
    "stumping": 12,
    "run_out_direct": 12,
    "run_out_indirect": 6,
}

DUCK_ROLES = {"BAT", "WK", "AR"}

# Dismissals that are NOT credited to the bowler
NON_BOWLER_DISMISSALS = {
    "run out", "retired hurt", "retired out", "retired not out",
    "obstructing the field", "timed out", "handled the ball",
}


def compute_batting_fp(
    runs: int,
    balls: int,
    fours: int,
    sixes: int,
    is_dismissed: bool,
    match_type: str = "T20",
    role: Optional[str] = None,
) -> float:
    fp = runs * BATTING_POINTS["run"] + fours * BATTING_POINTS["boundary_bonus"] + sixes * BATTING_POINTS["six_bonus"]
    if runs >= 100:
        fp += BATTING_POINTS["century_bonus"]
    elif runs >= 50:
        fp += BATTING_POINTS["half_century_bonus"]
    if is_dismissed and runs == 0 and (role is None or role in DUCK_ROLES):
        fp += BATTING_POINTS["duck_penalty"]
    return round(float(fp), 2)


def compute_bowling_fp(
    wickets: int,
    runs_conceded: int,
    overs: float,
    maidens: int,
    match_type: str = "T20",
    lbw_bowled: int = 0,
) -> float:
    fp = wickets * BOWLING_POINTS["wicket"] + lbw_bowled * BOWLING_POINTS["lbw_bowled_bonus"]
    if wickets >= 5:
        fp += BOWLING_POINTS["five_wicket_bonus"]
    elif wickets >= 4:
        fp += BOWLING_POINTS["four_wicket_bonus"]
    fp += maidens * BOWLING_POINTS["maiden"]
    return round(float(fp), 2)


def compute_fielding_fp(catches: int, stumpings: int, run_outs_direct: int, run_outs_indirect: int) -> float:
    fp = (catches * FIELDING_POINTS["catch"] + stumpings * FIELDING_POINTS["stumping"]
          + run_outs_direct * FIELDING_POINTS["run_out_direct"]
          + run_outs_indirect * FIELDING_POINTS["run_out_indirect"])
    return round(float(fp), 2)


def compute_total_fp(
    runs: int = 0,
    balls: int = 0,
    fours: int = 0,
    sixes: int = 0,
    is_dismissed: bool = False,
    wickets: int = 0,
    runs_conceded: int = 0,
    overs: float = 0.0,
    maidens: int = 0,
    lbw_bowled: int = 0,
    catches: int = 0,
    stumpings: int = 0,
    run_outs_direct: int = 0,
    run_outs_indirect: int = 0,
    match_type: str = "T20",
    role: Optional[str] = None,
) -> float:
    """Compute total fantasy points for one player in one match."""
    bat = compute_batting_fp(runs, balls, fours, sixes, is_dismissed, match_type, role)
    bowl = compute_bowling_fp(wickets, runs_conceded, overs, maidens, match_type, lbw_bowled)
    field = compute_fielding_fp(catches, stumpings, run_outs_direct, run_outs_indirect)
    return round(bat + bowl + field, 2)
