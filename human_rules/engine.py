"""
Human Rules Engine: evaluate applicable analyst rules for each player in a match context.

Matching is strict: a rule fires only when every condition key is known for this
player/match and satisfied. (Unknown context never counts as a match — e.g. the
Kohli-chasing rule does not fire before the toss.)
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from human_rules.loader import get_all_rules

logger = logging.getLogger(__name__)

# Condition keys that are substring matches (rule "Wankhede" ⊂ "Wankhede Stadium, Mumbai")
SUBSTRING_KEYS = {"venue"}
ALIASES = {"home_match": "is_home"}


def normalise_player_key(key: Optional[str]) -> str:
    """'Kohli, V' -> 'v kohli'; 'V Kohli' -> 'v kohli'."""
    if not key:
        return ""
    k = key.strip()
    if "," in k:
        last, first = [s.strip() for s in k.split(",", 1)]
        k = f"{first} {last}"
    return " ".join(k.lower().split())


class MatchContext:
    """Contextual conditions for one player in one match prediction."""

    def __init__(
        self,
        match_type: str,
        venue: Optional[str] = None,
        pitch_type: Optional[str] = None,
        is_chasing: Optional[bool] = None,
        toss_decision: Optional[str] = None,
        opposition_bowling_type: Optional[str] = None,
        phase: Optional[str] = None,
        batting_position: Optional[int] = None,
        is_final_or_knockout: bool = False,
        is_home: Optional[bool] = None,
        rest_days: Optional[int] = None,
        batting_style: Optional[str] = None,
        bowling_style: Optional[str] = None,
        primary_role: Optional[str] = None,
        match_date: Optional[date] = None,
    ):
        self.match_type = match_type
        self.venue = venue
        self.pitch_type = pitch_type
        self.is_chasing = is_chasing
        self.toss_decision = toss_decision
        self.opposition_bowling_type = opposition_bowling_type
        self.phase = phase
        self.batting_position = batting_position
        self.is_final_or_knockout = is_final_or_knockout
        self.is_home = is_home
        self.rest_days = rest_days
        self.batting_style = batting_style
        self.bowling_style = bowling_style
        self.primary_role = primary_role
        self.match_date = match_date

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def copy_with(self, **kw) -> "MatchContext":
        d = dict(self.__dict__)
        d.update(kw)
        return MatchContext(**d)


def _match_types_ok(expected: Any, actual: str) -> bool:
    exp = expected if isinstance(expected, list) else [expected]
    # IPL/BBL/... are T20 matches; a rule for "T20" applies to them and vice versa
    t20 = {"T20", "IT20", "IPL", "BBL", "PSL", "CPL", "WPL"}
    return actual in exp or (actual in t20 and any(e in t20 for e in exp))


def _condition_matches(condition: dict, context: MatchContext) -> bool:
    for key, expected in condition.items():
        if key == "match_type":
            if not _match_types_ok(expected, context.match_type):
                return False
            continue
        if key == "bowling_style_contains":
            style = (context.bowling_style or "").lower().replace("-", "")
            if not style or str(expected).lower().replace("-", "") not in style:
                return False
            continue
        actual = getattr(context, ALIASES.get(key, key), None)
        if actual is None:
            return False
        if isinstance(actual, (set, frozenset)):   # e.g. opposition attack contains a bowler type
            exp = set(expected) if isinstance(expected, list) else {expected}
            if not exp & actual:
                return False
        elif isinstance(expected, dict):           # numeric range {"min": x, "max": y}
            if "min" in expected and actual < expected["min"]:
                return False
            if "max" in expected and actual > expected["max"]:
                return False
        elif isinstance(expected, list):
            if actual not in expected:
                return False
        elif key in SUBSTRING_KEYS:
            if str(expected).lower() not in str(actual).lower():
                return False
        elif actual != expected:
            return False
    return True


def _in_validity(rule: dict, on: Optional[date]) -> bool:
    if on is None:
        return True
    vf, vu = rule.get("valid_from"), rule.get("valid_until")
    try:
        if vf and on < date.fromisoformat(str(vf)[:10]):
            return False
        if vu and on > date.fromisoformat(str(vu)[:10]):
            return False
    except ValueError:
        pass
    return True


def evaluate_rules_detailed(player_cricsheet_key: str, context: MatchContext) -> Tuple[float, List[dict]]:
    """Return (total_adjustment, [{id, impact, description, rule_type}]) for fired rules."""
    rules = get_all_rules()
    me = normalise_player_key(player_cricsheet_key)
    total = 0.0
    fired: List[dict] = []
    for rule_id, rule in rules.items():
        if not rule.get("is_active", True):
            continue
        rk = rule.get("player_key")
        if rk and normalise_player_key(rk) != me:
            continue
        mts = rule.get("match_types")
        if mts and not _match_types_ok(mts, context.match_type):
            continue
        if not _in_validity(rule, context.match_date):
            continue
        if not _condition_matches(rule.get("condition", {}) or {}, context):
            continue
        impact = float(rule.get("impact_score", 0)) * float(rule.get("confidence", 0.5))
        total += impact
        fired.append({"id": rule_id, "impact": round(impact, 2), "rule_type": rule.get("rule_type"),
                      "description": rule.get("description", "")})
        logger.debug("Rule %s fired for %s: %+.2f", rule_id, player_cricsheet_key, impact)
    return total, fired


def evaluate_rules(player_cricsheet_key: str, context: MatchContext) -> Tuple[float, List[str]]:
    """Return (total_adjustment, list_of_fired_rule_ids)."""
    total, fired = evaluate_rules_detailed(player_cricsheet_key, context)
    return total, [f["id"] for f in fired]


def evaluate_all_players(players: List[Dict], context: MatchContext) -> List[Dict]:
    results = []
    for p in players:
        adjustment, fired = evaluate_rules(p.get("cricsheet_key", ""), context)
        results.append({**p, "rules_score": adjustment, "rules_fired": fired})
    return results
