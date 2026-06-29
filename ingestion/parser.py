"""
Cricsheet JSON parser: converts ball-by-ball match files into relational records.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_MATCH_TYPES = {
    "T20", "ODI", "Test", "IT20", "IPL", "BBL", "PSL", "CPL",
    "WPL", "NTB", "CCH", "WOD", "MDM",
}

BOWLER_TYPE_MAP = {
    "Right-arm fast": "pace_right",
    "Right-arm fast-medium": "pace_right",
    "Right-arm medium-fast": "pace_right",
    "Right-arm medium": "pace_right",
    "Left-arm fast": "pace_left",
    "Left-arm fast-medium": "pace_left",
    "Left-arm medium-fast": "pace_left",
    "Left-arm medium": "pace_left",
    "Right-arm off-break": "spin_off",
    "Right-arm off-spin": "spin_off",
    "Slow left-arm orthodox": "spin_left",
    "Legbreak": "spin_wrist",
    "Legbreak googly": "spin_wrist",
    "Slow left-arm chinaman": "spin_wrist",
}


def get_bowler_type(bowling_style: Optional[str]) -> str:
    if not bowling_style:
        return "unknown"
    for k, v in BOWLER_TYPE_MAP.items():
        if k.lower() in bowling_style.lower():
            return v
    return "pace_right"  # default


def parse_match(data: dict) -> Tuple[dict, List[dict], List[dict]]:
    """
    Parse a Cricsheet JSON dict into:
    - match_record: dict for the `match` table
    - innings_records: list of dicts for `innings` table
    - delivery_records: list of dicts for `delivery` table
    """
    info = data.get("info", {})
    meta = data.get("meta", {})

    match_type = info.get("match_type", "T20")
    teams = info.get("teams", [])
    toss = info.get("toss", {})
    outcome = info.get("outcome", {})

    match_record = {
        "match_type": match_type,
        "gender": info.get("gender", "male"),
        "team_type": info.get("team_type", "club"),
        "venue_name": info.get("venue"),
        "city": info.get("city"),
        "team_a": teams[0] if len(teams) > 0 else "Unknown",
        "team_b": teams[1] if len(teams) > 1 else "Unknown",
        "toss_winner": toss.get("winner"),
        "toss_decision": toss.get("decision"),
        "match_winner": outcome.get("winner"),
        "win_by_runs": outcome.get("by", {}).get("runs"),
        "win_by_wickets": outcome.get("by", {}).get("wickets"),
        "player_of_match": info.get("player_of_match", []),
        "season": str(info.get("season", "")),
        "event_name": info.get("event", {}).get("name") if isinstance(info.get("event"), dict) else None,
        "event_stage": info.get("event", {}).get("stage") if isinstance(info.get("event"), dict) else None,
        "match_date": _get_match_date(info),
        "day_night": info.get("match_type_number", 1) != 1,
        "balls_per_over": info.get("balls_per_over", 6),
        "data_version": meta.get("data_version"),
        "is_complete": True,
    }

    innings_records = []
    delivery_records = []

    for inn_idx, innings_data in enumerate(data.get("innings", []), start=1):
        team = innings_data.get("team", "Unknown")
        other_teams = [t for t in teams if t != team]
        bowling_team = other_teams[0] if other_teams else "Unknown"

        inn_record = {
            "innings_number": inn_idx,
            "batting_team": team,
            "bowling_team": bowling_team,
            "total_runs": 0,
            "total_wickets": 0,
            "total_overs": 0.0,
            "is_complete": True,
        }

        for over_data in innings_data.get("overs", []):
            over_num = over_data.get("over", 0)
            for ball_idx, delivery in enumerate(over_data.get("deliveries", []), start=1):
                runs = delivery.get("runs", {})
                wickets = delivery.get("wickets", [])
                extras = delivery.get("extras", {})

                is_wicket = bool(wickets)
                wicket_info = wickets[0] if wickets else {}

                actual_delivery = delivery.get("actual_delivery") or f"{over_num}.{ball_idx}"
                phase = _get_phase(over_num, match_type)

                del_record = {
                    "over_number": over_num,
                    "ball_number": float(actual_delivery) if actual_delivery else float(f"{over_num}.{ball_idx}"),
                    "batter": delivery.get("batter", ""),
                    "bowler": delivery.get("bowler", ""),
                    "non_striker": delivery.get("non_striker"),
                    "runs_batter": runs.get("batter", 0),
                    "runs_extras": runs.get("extras", 0),
                    "runs_total": runs.get("total", 0),
                    "is_wide": "wides" in extras,
                    "is_no_ball": "noballs" in extras,
                    "is_bye": "byes" in extras,
                    "is_leg_bye": "legbyes" in extras,
                    "extra_wides": extras.get("wides", 0),
                    "extra_no_balls": extras.get("noballs", 0),
                    "extra_byes": extras.get("byes", 0),
                    "extra_leg_byes": extras.get("legbyes", 0),
                    "is_wicket": is_wicket,
                    "wicket_player_out": wicket_info.get("player_out"),
                    "wicket_kind": wicket_info.get("kind"),
                    "wicket_fielder": wicket_info.get("fielders", [{}])[0].get("name") if wicket_info.get("fielders") else None,
                    "is_powerplay": over_num < 6 and match_type in ("T20", "ODI", "IPL", "IT20"),
                    "phase": phase,
                }
                delivery_records.append(del_record)

                inn_record["total_runs"] += runs.get("total", 0)
                if is_wicket:
                    inn_record["total_wickets"] += 1

        inn_record["total_overs"] = round(len(delivery_records) / 6, 1)
        innings_records.append(inn_record)

    return match_record, innings_records, delivery_records


def _get_match_date(info: dict) -> str:
    dates = info.get("dates", [])
    return dates[0] if dates else "2000-01-01"


def _get_phase(over_num: int, match_type: str) -> str:
    if match_type in ("T20", "IPL", "IT20"):
        if over_num < 6:
            return "powerplay"
        elif over_num < 15:
            return "middle"
        else:
            return "death"
    elif match_type in ("ODI", "WOD"):
        if over_num < 10:
            return "powerplay"
        elif over_num < 40:
            return "middle"
        else:
            return "death"
    return "middle"
