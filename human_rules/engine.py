"""
Human Rules Engine: evaluate applicable rules for each player in a match context.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from human_rules.loader import get_all_rules

logger = logging.getLogger(__name__)


class MatchContext:
    """Holds the contextual conditions for a match prediction."""
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
        is_home: bool = False,
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

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


def _condition_matches(condition: dict, context: MatchContext, player_key: str) -> bool:
    """Return True if all condition fields are satisfied by the context."""
    for field, expected in condition.items():
        actual = getattr(context, field, None)
        if actual is None:
            continue
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def evaluate_rules(
    player_cricsheet_key: str,
    context: MatchContext,
) -> Tuple[float, List[str]]:
    """
    Evaluate all applicable rules for a player given the match context.

    Returns:
        (total_adjustment, list_of_fired_rule_ids)
    """
    rules = get_all_rules()
    total_adjustment = 0.0
    fired_ids: List[str] = []

    for rule_id, rule in rules.items():
        rule_player_key = rule.get("player_key")
        # Only apply if it's a wildcard rule OR matches the player
        if rule_player_key and rule_player_key.lower() != player_cricsheet_key.lower():
            continue

        # Check match type eligibility
        match_types = rule.get("match_types")
        if match_types and context.match_type not in match_types:
            continue

        # Check condition
        condition = rule.get("condition", {})
        if not _condition_matches(condition, context, player_cricsheet_key):
            continue

        # Apply: impact = impact_score × confidence
        impact_score = rule.get("impact_score", 0)
        confidence = rule.get("confidence", 0.5)
        adjusted = impact_score * confidence

        total_adjustment += adjusted
        fired_ids.append(rule_id)
        logger.debug(f"Rule {rule_id} fired for {player_cricsheet_key}: +{adjusted:.2f}")

    return total_adjustment, fired_ids


def evaluate_all_players(
    players: List[Dict],  # list of {"cricsheet_key": str, "base_score": float, ...}
    context: MatchContext,
) -> List[Dict]:
    """
    Apply rules to all players and return updated scores with rules_fired list.
    """
    results = []
    for p in players:
        adjustment, fired = evaluate_rules(p.get("cricsheet_key", ""), context)
        p_out = {**p, "rules_score": adjustment, "rules_fired": fired}
        results.append(p_out)
    return results
