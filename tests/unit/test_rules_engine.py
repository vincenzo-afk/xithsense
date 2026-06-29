"""
Unit tests for the human rules engine.
"""
import pytest
from unittest.mock import patch
from human_rules.engine import MatchContext, evaluate_rules

MOCK_RULES = {
    "RULE-0001": {
        "id": "RULE-0001",
        "rule_type": "PLAYER",
        "player_key": "v kohli",
        "condition": {"is_chasing": True},
        "match_types": ["T20", "IPL"],
        "impact_score": 12,
        "confidence": 0.85,
        "is_active": True,
    },
    "RULE-0101": {
        "id": "RULE-0101",
        "rule_type": "VENUE",
        "player_key": None,  # applies to all players
        "condition": {"pitch_type": "batting"},
        "match_types": ["T20"],
        "impact_score": 5,
        "confidence": 0.7,
        "is_active": True,
    },
}


class TestRulesEngine:
    @patch("human_rules.engine.get_all_rules", return_value=MOCK_RULES)
    def test_player_rule_fires_when_chasing(self, _):
        ctx = MatchContext(match_type="T20", is_chasing=True)
        adj, fired = evaluate_rules("v kohli", ctx)
        assert "RULE-0001" in fired
        assert adj == pytest.approx(12 * 0.85, rel=0.01)

    @patch("human_rules.engine.get_all_rules", return_value=MOCK_RULES)
    def test_player_rule_does_not_fire_when_not_chasing(self, _):
        ctx = MatchContext(match_type="T20", is_chasing=False)
        adj, fired = evaluate_rules("v kohli", ctx)
        assert "RULE-0001" not in fired

    @patch("human_rules.engine.get_all_rules", return_value=MOCK_RULES)
    def test_venue_rule_fires_for_all_players(self, _):
        ctx = MatchContext(match_type="T20", pitch_type="batting")
        adj, fired = evaluate_rules("random player", ctx)
        assert "RULE-0101" in fired

    @patch("human_rules.engine.get_all_rules", return_value=MOCK_RULES)
    def test_wrong_match_type_excludes_rule(self, _):
        ctx = MatchContext(match_type="Test", is_chasing=True)
        adj, fired = evaluate_rules("v kohli", ctx)
        assert "RULE-0001" not in fired

    @patch("human_rules.engine.get_all_rules", return_value=MOCK_RULES)
    def test_total_adjustment_accumulates(self, _):
        ctx = MatchContext(match_type="T20", is_chasing=True, pitch_type="batting")
        adj, fired = evaluate_rules("v kohli", ctx)
        assert len(fired) == 2
        assert adj == pytest.approx(12 * 0.85 + 5 * 0.7, rel=0.01)
