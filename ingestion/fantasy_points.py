"""
Fantasy Points Calculator for Dream11 scoring system.
"""
from __future__ import annotations


# ── Dream11 Fantasy Points Scoring ─────────────────────────────────────────

BATTING_POINTS = {
    "run": 1,
    "boundary_bonus": 1,     # per 4
    "six_bonus": 2,          # per 6
    "half_century_bonus": 8, # 50+ runs
    "century_bonus": 16,     # 100+ runs
    "duck_penalty": -2,      # dismissed for 0
    "thirty_bonus": 4,       # 30+ runs (T20)
}

BOWLING_POINTS = {
    "wicket": 25,
    "lbw_caught_behind_bonus": 8,
    "maiden": 8,
    "two_wicket_bonus": 8,
    "three_wicket_bonus": 16,
    "four_wicket_bonus": 16,
    "five_wicket_bonus": 16,
    "economy_below_5": 6,    # per match
    "economy_5_to_6": 4,
    "economy_above_9": -2,
    "economy_above_10": -4,
    "economy_above_11": -6,
}

FIELDING_POINTS = {
    "catch": 8,
    "stumping": 12,
    "run_out_direct": 12,
    "run_out_indirect": 6,
    "three_catches_bonus": 4,
}


def compute_batting_fp(
    runs: int,
    balls: int,
    fours: int,
    sixes: int,
    is_dismissed: bool,
    match_type: str = "T20",
) -> float:
    fp = 0.0
    fp += runs * BATTING_POINTS["run"]
    fp += fours * BATTING_POINTS["boundary_bonus"]
    fp += sixes * BATTING_POINTS["six_bonus"]

    if runs >= 100:
        fp += BATTING_POINTS["century_bonus"]
    elif runs >= 50:
        fp += BATTING_POINTS["half_century_bonus"]
    elif runs >= 30 and match_type in ("T20", "IPL", "IT20"):
        fp += BATTING_POINTS["thirty_bonus"]

    if is_dismissed and runs == 0 and match_type != "Test":
        fp += BATTING_POINTS["duck_penalty"]

    # Strike rate bonus/penalty (T20 only)
    if balls >= 10 and match_type in ("T20", "IPL", "IT20"):
        sr = runs / balls * 100
        if sr >= 170:
            fp += 6
        elif sr >= 150:
            fp += 4
        elif sr >= 130:
            fp += 2
        elif sr < 70:
            fp -= 2
        elif sr < 60:
            fp -= 4
        elif sr < 50:
            fp -= 6

    return round(fp, 2)


def compute_bowling_fp(
    wickets: int,
    runs_conceded: int,
    overs: float,
    maidens: int,
    match_type: str = "T20",
    lbw_caught_behind: int = 0,
) -> float:
    fp = 0.0
    fp += wickets * BOWLING_POINTS["wicket"]
    fp += lbw_caught_behind * BOWLING_POINTS["lbw_caught_behind_bonus"]
    fp += maidens * BOWLING_POINTS["maiden"]

    # Wicket bonuses
    if wickets >= 5:
        fp += BOWLING_POINTS["five_wicket_bonus"]
    elif wickets >= 4:
        fp += BOWLING_POINTS["four_wicket_bonus"]
    elif wickets >= 3:
        fp += BOWLING_POINTS["three_wicket_bonus"]
    elif wickets >= 2:
        fp += BOWLING_POINTS["two_wicket_bonus"]

    # Economy rate bonus/penalty (T20 only)
    if overs >= 2 and match_type in ("T20", "IPL", "IT20"):
        economy = runs_conceded / overs if overs > 0 else 0
        if economy < 5:
            fp += BOWLING_POINTS["economy_below_5"]
        elif economy <= 6:
            fp += BOWLING_POINTS["economy_5_to_6"]
        elif economy >= 11:
            fp += BOWLING_POINTS["economy_above_11"]
        elif economy >= 10:
            fp += BOWLING_POINTS["economy_above_10"]
        elif economy >= 9:
            fp += BOWLING_POINTS["economy_above_9"]

    return round(fp, 2)


def compute_fielding_fp(catches: int, stumpings: int, run_outs_direct: int, run_outs_indirect: int) -> float:
    fp = 0.0
    fp += catches * FIELDING_POINTS["catch"]
    fp += stumpings * FIELDING_POINTS["stumping"]
    fp += run_outs_direct * FIELDING_POINTS["run_out_direct"]
    fp += run_outs_indirect * FIELDING_POINTS["run_out_indirect"]
    if catches >= 3:
        fp += FIELDING_POINTS["three_catches_bonus"]
    return round(fp, 2)


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
    lbw_caught_behind: int = 0,
    catches: int = 0,
    stumpings: int = 0,
    run_outs_direct: int = 0,
    run_outs_indirect: int = 0,
    match_type: str = "T20",
) -> float:
    """Compute total Dream11 fantasy points for one player in one match."""
    bat = compute_batting_fp(runs, balls, fours, sixes, is_dismissed, match_type)
    bowl = compute_bowling_fp(wickets, runs_conceded, overs, maidens, match_type, lbw_caught_behind)
    field = compute_fielding_fp(catches, stumpings, run_outs_direct, run_outs_indirect)
    return round(bat + bowl + field, 2)
