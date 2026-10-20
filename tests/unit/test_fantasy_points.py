"""
Unit tests for the fantasy points calculator (AC-03 / TC-01 reference values).
"""
from ingestion.fantasy_points import (
    compute_batting_fp, compute_bowling_fp, compute_fielding_fp, compute_total_fp
)


class TestBattingFP:
    def test_basic_run_scoring(self):
        fp = compute_batting_fp(runs=35, balls=20, fours=3, sixes=1, is_dismissed=False)
        assert fp == 35 + 3 + 2

    def test_half_century_ac03(self):
        # AC-03: 60 runs with 1 four and 2 sixes = 73
        assert compute_batting_fp(runs=60, balls=40, fours=1, sixes=2, is_dismissed=True) == 73

    def test_century_ac03(self):
        # 100 runs with 5x4 and 3x6 = 100 + 5 + 6 + 16 = 127
        assert compute_batting_fp(runs=100, balls=60, fours=5, sixes=3, is_dismissed=False) == 127

    def test_bonuses_not_cumulative(self):
        assert compute_batting_fp(100, 60, 0, 0, False) == 116

    def test_duck_penalty(self):
        assert compute_batting_fp(runs=0, balls=4, fours=0, sixes=0, is_dismissed=True) == -2

    def test_no_duck_penalty_for_bowlers(self):
        assert compute_batting_fp(0, 2, 0, 0, True, role="BOWL") == 0

    def test_not_out_zero_is_not_duck(self):
        assert compute_batting_fp(0, 1, 0, 0, False) == 0


class TestBowlingFP:
    def test_three_wickets_ac03(self):
        assert compute_bowling_fp(wickets=3, runs_conceded=20, overs=4, maidens=0) == 75

    def test_five_wickets_ac03(self):
        assert compute_bowling_fp(wickets=5, runs_conceded=25, overs=4, maidens=0) == 141

    def test_four_wicket_bonus(self):
        assert compute_bowling_fp(wickets=4, runs_conceded=25, overs=4, maidens=0) == 108

    def test_lbw_bowled_bonus(self):
        assert compute_bowling_fp(wickets=2, runs_conceded=20, overs=4, maidens=0, lbw_bowled=1) == 58

    def test_maiden(self):
        assert compute_bowling_fp(wickets=0, runs_conceded=0, overs=1, maidens=1) == 4


class TestFieldingFP:
    def test_catches(self):
        assert compute_fielding_fp(catches=2, stumpings=0, run_outs_direct=0, run_outs_indirect=0) == 16

    def test_stumpings_ac03(self):
        assert compute_fielding_fp(catches=0, stumpings=2, run_outs_direct=0, run_outs_indirect=0) == 24

    def test_run_outs(self):
        assert compute_fielding_fp(0, 0, 1, 1) == 18


class TestTotalFP:
    def test_all_rounder(self):
        fp = compute_total_fp(runs=30, balls=20, fours=2, sixes=1, wickets=2, runs_conceded=20,
                              overs=4, catches=1)
        assert fp == (30 + 2 + 2) + 50 + 8

    def test_pure_batter(self):
        fp = compute_total_fp(runs=75, balls=40, fours=8, sixes=3)
        assert fp == 75 + 8 + 6 + 8
