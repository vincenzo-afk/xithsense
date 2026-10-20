"""Unit tests for the CricketData integration: score parsing, live fantasy points, name mapping."""
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from ingestion.fantasy_points import compute_batting_fp
from integrations.cricapi import api_gender, api_match_type, parse_api_datetime
from integrations.fixtures import NameIndex, _parse_series_date, match_id_for, series_priority
from integrations.live_feed import overs_to_balls, parse_score, scorecard_fantasy_points, win_probability

CARD = json.loads((Path(__file__).parents[1] / "fixtures" / "cricapi_scorecard.json").read_text())


def _match(**kw):
    base = dict(team_a="India", team_b="Zimbabwe", match_type="T20", status="live",
                status_text=CARD["status"], gender="female")
    return SimpleNamespace(**{**base, **kw})


def test_overs_to_balls():
    assert overs_to_balls(12.2) == 74 and overs_to_balls(20) == 120 and overs_to_balls(None) == 0


def test_parse_score_chase_from_real_payload():
    st = parse_score(_match(), CARD["score"])
    assert [i["team"] for i in st["innings_list"]] == ["India", "Zimbabwe"]
    assert st["innings"]["batting_team"] == "Zimbabwe" and st["innings"]["target"] == CARD["score"][0]["r"] + 1
    assert st["required"]["runs"] == CARD["score"][0]["r"] + 1 - CARD["score"][1]["r"]
    p = st["win_probability"]
    assert abs(sum(p.values()) - 1) < 1e-6 and p["India"] > 0.9      # needing 144 off 46 balls


def test_parse_score_test_match_has_no_win_probability():
    st = parse_score(_match(match_type="Test"), [{"r": 425, "w": 9, "o": 127.1, "inning": "india Inning 1"}])
    assert "win_probability" not in st and st["innings"]["runs"] == 425


@pytest.mark.parametrize("state,expect", [
    ((7, 0, 4, 120, None, 170), (0.4, 0.65)),
    ((150, 4, 102, 120, 171, 170), (0.5, 0.85)),
    ((120, 8, 100, 120, 171, 170), (0.0, 0.1)),
])
def test_win_probability_ranges(state, expect):
    p = win_probability(*state)
    assert expect[0] <= p <= expect[1]


def test_scorecard_fantasy_points_matches_canonical_scoring():
    roster = {}
    for inn in CARD["scorecard"]:
        for b in inn["batting"]:
            pid = b["batsman"]["id"]
            roster[f"id:{pid}"] = {"player_id": pid, "full_name": b["batsman"]["name"], "role": "BAT", "team": "x"}
    lines = scorecard_fantasy_points(CARD, roster)
    b = CARD["scorecard"][0]["batting"][0]
    got = lines[b["batsman"]["id"]]
    expected = compute_batting_fp(b["r"], b["b"], b["4s"], b["6s"], "not out" not in b["dismissal-text"], role="BAT")
    assert got["bat"]["runs"] == b["r"]
    assert got["fp"] >= expected          # batting + any fielding


def test_api_helpers():
    assert api_gender({"teams": ["India Women", "Zimbabwe Women"]}) == "female"
    assert api_match_type({"matchType": "t20", "name": "CSK vs MI, Indian Premier League 2027"}) == "IPL"
    assert api_match_type({"matchType": "odi", "name": "x"}) == "ODI"
    assert parse_api_datetime("2026-10-20T13:30:00").tzinfo is not None
    assert match_id_for("7ef2a3f0-c9f5-402a-9417-078e9d583d6e").startswith("CA") and len(match_id_for("7ef2a3f0-c9f5-402a-9417-078e9d583d6e")) == 20


def test_series_dates_and_priority():
    assert _parse_series_date("2027-10-02", date(2026, 10, 20)) == date(2027, 10, 2)
    assert _parse_series_date("Oct 18", date(2026, 10, 20)) == date(2026, 10, 18)
    assert _parse_series_date("Jan 05", date(2026, 12, 28)) == date(2027, 1, 5)
    assert series_priority("Indian Premier League 2027") > series_priority("Ranji Trophy Elite 2026-27")
    assert series_priority("Australia tour of India, 2027") > series_priority("Vijay Hazare Trophy Plate 2026")


def test_name_index_mapping():
    idx = NameIndex({"male": ["Royal Challengers Bengaluru", "India", "Chennai Super Kings"], "female": ["India", "Zimbabwe"]},
                    ["Wankhede Stadium, Mumbai", "MA Chidambaram Stadium, Chepauk, Chennai"])
    assert idx.team("India Women", "female") == "India"
    assert idx.team("Royal Challengers Bangalore", "male") == "Royal Challengers Bengaluru"
    assert idx.team("Unknown XI Women", "female") == "Unknown XI"
    assert idx.venue("Wankhede Stadium, Mumbai, Maharashtra") == "Wankhede Stadium, Mumbai"
    assert idx.venue("MA Chidambaram Stadium, Chennai") == "MA Chidambaram Stadium, Chepauk, Chennai"
