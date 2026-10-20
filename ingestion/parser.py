"""
Cricsheet JSON parser: converts ball-by-ball match files into relational records
and per-player match performances (with fantasy points).

Handles the real Cricsheet format: deliveries carry no ball number (position
within `overs[].deliveries` is used), super overs are skipped, franchise
leagues are identified from `event.name`, caught-and-bowled has no fielder entry.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ingestion.fantasy_points import NON_BOWLER_DISMISSALS, compute_total_fp

logger = logging.getLogger(__name__)

SUPPORTED_MATCH_TYPES = {
    "T20", "ODI", "Test", "IT20", "IPL", "BBL", "PSL", "CPL", "WPL",
    "NTB", "CCH", "ODM", "MDM", "WTB", "WOD", "IPT",
}

EVENT_LEAGUE_MAP = {
    "indian premier league": "IPL",
    "big bash league": "BBL",
    "pakistan super league": "PSL",
    "caribbean premier league": "CPL",
    "women's premier league": "WPL",
}

T20_TYPES = {"T20", "IT20", "IPL", "BBL", "PSL", "CPL", "WPL"}

BOWLER_TYPE_MAP = [
    ("left-arm fast", "pace_left"), ("left-arm medium", "pace_left"),
    ("right-arm fast", "pace_right"), ("right-arm medium", "pace_right"),
    ("offbreak", "spin_off"), ("off-break", "spin_off"), ("off-spin", "spin_off"),
    ("chinaman", "spin_wrist"), ("left-arm wrist", "spin_wrist"),
    ("slow left-arm orthodox", "spin_left"),
    ("legbreak", "spin_wrist"),
]


def get_bowler_type(bowling_style: Optional[str]) -> Optional[str]:
    if not bowling_style:
        return None
    s = bowling_style.lower()
    for k, v in BOWLER_TYPE_MAP:
        if k in s:
            return v
    return "pace_right"


def normalise_match_type(info: dict) -> str:
    """Cricsheet only uses Test/ODI/T20/IT20/ODM/MDM; leagues come from event name."""
    mt = info.get("match_type", "T20")
    event = info.get("event")
    name = (event.get("name") if isinstance(event, dict) else event) or ""
    for k, v in EVENT_LEAGUE_MAP.items():
        if k in name.lower():
            return v
    return mt


def phase_of(over_num: int, match_type: str) -> str:
    if match_type in T20_TYPES:
        return "powerplay" if over_num < 6 else "middle" if over_num < 15 else "death"
    if match_type in ("ODI", "WOD", "ODM"):
        return "powerplay" if over_num < 10 else "middle" if over_num < 40 else "death"
    return "middle"


@dataclass
class PlayerLine:
    name: str
    team: str
    batting_position: Optional[int] = None
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    did_bat: bool = False
    dismissed: bool = False
    dismissal: Optional[str] = None
    legal_balls_bowled: int = 0
    runs_conceded: int = 0
    wickets: int = 0
    lbw_bowled: int = 0
    maidens: int = 0
    dots: int = 0
    catches: int = 0
    stumpings: int = 0
    run_out_direct: int = 0
    run_out_indirect: int = 0

    @property
    def overs(self) -> float:
        return round(self.legal_balls_bowled / 6, 2)

    def fantasy_points(self, match_type: str, role: Optional[str]) -> float:
        return compute_total_fp(
            runs=self.runs, balls=self.balls, fours=self.fours, sixes=self.sixes,
            is_dismissed=self.dismissed, wickets=self.wickets, runs_conceded=self.runs_conceded,
            overs=self.overs, maidens=self.maidens, lbw_bowled=self.lbw_bowled,
            catches=self.catches, stumpings=self.stumpings, run_outs_direct=self.run_out_direct,
            run_outs_indirect=self.run_out_indirect, match_type=match_type, role=role,
        )


@dataclass
class ParsedMatch:
    match: Dict[str, Any]
    innings: List[Dict[str, Any]]
    deliveries: List[List[Dict[str, Any]]]          # per innings
    players: Dict[str, List[str]]                   # team -> names (XI)
    registry: Dict[str, str]
    lines: Dict[str, PlayerLine] = field(default_factory=dict)


class ValidationError(ValueError):
    pass


def validate(data: dict) -> None:
    info = data.get("info") or {}
    if normalise_match_type(info) not in SUPPORTED_MATCH_TYPES:
        raise ValidationError(f"unsupported match_type {info.get('match_type')}")
    if info.get("gender") not in ("male", "female"):
        raise ValidationError("invalid gender")
    if len(info.get("teams", [])) != 2:
        raise ValidationError("match must have exactly 2 teams")
    if not info.get("dates"):
        raise ValidationError("missing dates")
    if not data.get("innings"):
        raise ValidationError("no innings")


def parse_match(data: dict) -> ParsedMatch:
    validate(data)
    info = data["info"]
    meta = data.get("meta", {})
    match_type = normalise_match_type(info)
    teams = info["teams"]
    toss = info.get("toss", {}) or {}
    outcome = info.get("outcome", {}) or {}
    event = info.get("event") if isinstance(info.get("event"), dict) else {}
    toss_decision = toss.get("decision") if toss.get("decision") in ("bat", "field") else None

    match_record = {
        "match_type": match_type,
        "gender": info.get("gender", "male"),
        "team_type": info.get("team_type", "club"),
        "venue_name": info.get("venue"),
        "city": info.get("city"),
        "team_a": teams[0],
        "team_b": teams[1],
        "toss_winner": toss.get("winner"),
        "toss_decision": toss_decision,
        "match_winner": outcome.get("winner"),
        "win_by_runs": (outcome.get("by") or {}).get("runs"),
        "win_by_wickets": (outcome.get("by") or {}).get("wickets"),
        "player_of_match": info.get("player_of_match", []),
        "season": str(info.get("season", "")),
        "event_name": event.get("name"),
        "event_stage": event.get("stage"),
        "match_number": event.get("match_number"),
        "match_date": info["dates"][0],
        "balls_per_over": info.get("balls_per_over", 6),
        "data_version": meta.get("data_version"),
        "is_complete": True,
        "status": "complete",
        "playing_xi_confirmed": True,
        "source": "cricsheet",
    }

    players = {t: list(names) for t, names in (info.get("players") or {}).items()}
    registry = (info.get("registry") or {}).get("people", {})
    team_of: Dict[str, str] = {n: t for t, names in players.items() for n in names}
    lines: Dict[str, PlayerLine] = {n: PlayerLine(n, t) for n, t in team_of.items()}

    def line(name: str, team: str) -> PlayerLine:
        if name not in lines:
            lines[name] = PlayerLine(name, team)
            team_of[name] = team
        return lines[name]

    innings_records: List[dict] = []
    all_deliveries: List[List[dict]] = []

    regular_innings = [i for i in data["innings"] if not i.get("super_over")]
    for inn_idx, inn in enumerate(regular_innings, start=1):
        bat_team = inn.get("team", teams[0])
        bowl_team = teams[1] if bat_team == teams[0] else teams[0]
        inn_rec = {
            "innings_number": inn_idx, "batting_team": bat_team, "bowling_team": bowl_team,
            "total_runs": 0, "total_wickets": 0, "total_overs": 0.0,
            "target_runs": (inn.get("target") or {}).get("runs"), "is_complete": True,
        }
        dels: List[dict] = []
        legal_total = 0
        batting_order: List[str] = []

        for over_data in inn.get("overs", []):
            over_num = over_data.get("over", 0)
            legal_in_over = 0
            over_conceded: Dict[str, int] = {}
            for seq, d in enumerate(over_data.get("deliveries", []), start=1):
                runs = d.get("runs", {})
                extras = d.get("extras", {}) or {}
                batter, bowler, ns = d.get("batter", ""), d.get("bowler", ""), d.get("non_striker")
                rb = runs.get("batter", 0)
                if not 0 <= rb <= 36:
                    rb = 0
                rt = runs.get("total", 0)
                if rt < rb:
                    rt = rb + runs.get("extras", 0)
                wides, noballs = extras.get("wides", 0), extras.get("noballs", 0)
                byes, legbyes = extras.get("byes", 0), extras.get("legbyes", 0)
                is_legal = not wides and not noballs
                if is_legal:
                    legal_in_over += 1
                    legal_total += 1

                for name in (batter, ns):
                    if name and name not in batting_order:
                        batting_order.append(name)

                b = line(batter, bat_team)
                b.did_bat = True
                b.runs += rb
                if not wides:
                    b.balls += 1
                if rb == 4 and not d.get("runs", {}).get("non_boundary"):
                    b.fours += 1
                elif rb == 6:
                    b.sixes += 1
                if ns:
                    line(ns, bat_team).did_bat = True

                bw = line(bowler, bowl_team)
                conceded = rb + wides + noballs
                bw.runs_conceded += conceded
                over_conceded[bowler] = over_conceded.get(bowler, 0) + conceded
                if is_legal:
                    bw.legal_balls_bowled += 1
                    if rt == 0:
                        bw.dots += 1

                wickets = d.get("wickets", []) or []
                w0 = wickets[0] if wickets else {}
                for w in wickets:
                    kind = w.get("kind", "")
                    out = w.get("player_out")
                    if out and kind not in ("retired hurt", "retired not out"):
                        po = line(out, bat_team)
                        po.dismissed = True
                        po.dismissal = kind
                        po.did_bat = True
                    if kind not in NON_BOWLER_DISMISSALS:
                        bw.wickets += 1
                        if kind in ("lbw", "bowled"):
                            bw.lbw_bowled += 1
                    fielders = [f.get("name") for f in (w.get("fielders") or []) if f.get("name") and not f.get("substitute")]
                    if kind == "caught and bowled":
                        bw.catches += 1
                    elif kind == "caught" and fielders:
                        line(fielders[0], bowl_team).catches += 1
                    elif kind == "stumped" and fielders:
                        line(fielders[0], bowl_team).stumpings += 1
                    elif kind == "run out" and fielders:
                        if len(fielders) == 1:
                            line(fielders[0], bowl_team).run_out_direct += 1
                        else:
                            for f in fielders[:2]:
                                line(f, bowl_team).run_out_indirect += 1

                inn_rec["total_runs"] += rt
                inn_rec["total_wickets"] += len(wickets)
                dels.append({
                    "over_number": over_num,
                    "ball_seq": seq,
                    "ball_number": float(f"{over_num}.{max(legal_in_over, 1) if is_legal else legal_in_over + 1}"),
                    "batter": batter, "bowler": bowler, "non_striker": ns,
                    "runs_batter": rb, "runs_extras": runs.get("extras", 0), "runs_total": rt,
                    "is_wide": bool(wides), "is_no_ball": bool(noballs),
                    "is_bye": bool(byes), "is_leg_bye": bool(legbyes),
                    "extra_wides": wides, "extra_no_balls": noballs,
                    "extra_byes": byes, "extra_leg_byes": legbyes,
                    "is_wicket": bool(wickets),
                    "wicket_player_out": w0.get("player_out"),
                    "wicket_kind": w0.get("kind"),
                    "wicket_fielder": ((w0.get("fielders") or [{}])[0].get("name")
                                       if w0.get("fielders") else (bowler if w0.get("kind") == "caught and bowled" else None)),
                    "is_powerplay": over_num < 6 and match_type in T20_TYPES,
                    "phase": phase_of(over_num, match_type),
                    "review_by": (d.get("review") or {}).get("by"),
                    "review_decision": (d.get("review") or {}).get("decision"),
                })
            # Maidens: a complete over with zero runs conceded by its bowler
            if legal_in_over >= 6:
                for bname, c in over_conceded.items():
                    if c == 0:
                        lines[bname].maidens += 1

        for pos, name in enumerate(batting_order, start=1):
            if lines[name].batting_position is None:
                lines[name].batting_position = pos
        inn_rec["total_overs"] = round(legal_total // 6 + (legal_total % 6) / 10, 1)
        innings_records.append(inn_rec)
        all_deliveries.append(dels)

    return ParsedMatch(match_record, innings_records, all_deliveries, players, registry, lines)
