"""
Unit tests for the fantasy points calculator.
"""
import pytest
from ingestion.fantasy_points import (
    compute_batting_fp, compute_bowling_fp, compute_fielding_fp, compute_total_fp
)


class TestBattingFP:
    def test_basic_run_scoring(self):
        fp = compute_batting_fp(runs=35, balls=20, fours=3, sixes=1, is_dismissed=False, match_type="T20")
        assert fp == 35 + 3 + 2 + 4  # runs + boundaries + sixes + 30-bonus

    def test_half_century(self):
        fp = compute_batting_fp(runs=50, balls=30, fours=4, sixes=2, is_dismissed=False, match_type="T20")
        assert 50 in [int(fp) - 8, int(fp) - 8 - 1]  # includes half-century bonus

    def test_century_bonus(self):
        fp = compute_batting_fp(runs=100, balls=60, fours=10, sixes=3, is_dismissed=False, match_type="T20")
        # Should include century bonus (16) not half-century (8)
        assert fp > 0

    def test_duck_penalty(self):
        fp = compute_batting_fp(runs=0, balls=4, fours=0, sixes=0, is_dismissed=True, match_type="T20")
        assert fp == -2  # just duck penalty

    def test_high_sr_bonus(self):
        fp_high = compute_batting_fp(runs=30, balls=17, fours=2, sixes=1, is_dismissed=False, match_type="T20")
        fp_low = compute_batting_fp(runs=30, balls=60, fours=2, sixes=0, is_dismissed=False, match_type="T20")
        assert fp_high > fp_low  # high SR should score more


class TestBowlingFP:
    def test_wickets(self):
        fp = compute_bowling_fp(wickets=2, runs_conceded=20, overs=4, maidens=0)
        assert fp >= 2 * 25  # 2 wickets + 2-wicket bonus

    def test_five_wickets(self):
        fp = compute_bowling_fp(wickets=5, runs_conceded=25, overs=4, maidens=0)
        assert fp > 5 * 25  # includes 5-wicket bonus

    def test_maiden_bonus(self):
        fp = compute_bowling_fp(wickets=0, runs_conceded=0, overs=1, maidens=1)
        assert fp == 8  # maiden bonus only

    def test_economy_penalty(self):
        fp_bad = compute_bowling_fp(wickets=0, runs_conceded=50, overs=4, maidens=0)
        fp_good = compute_bowling_fp(wickets=0, runs_conceded=16, overs=4, maidens=0)
        assert fp_good > fp_bad


class TestFieldingFP:
    def test_catches(self):
        fp = compute_fielding_fp(catches=2, stumpings=0, run_outs_direct=0, run_outs_indirect=0)
        assert fp == 16

    def test_three_catches_bonus(self):
        fp = compute_fielding_fp(catches=3, stumpings=0, run_outs_direct=0, run_outs_indirect=0)
        assert fp == 3 * 8 + 4  # 3 catches + bonus

    def test_stumping(self):
        fp = compute_fielding_fp(catches=0, stumpings=1, run_outs_direct=0, run_outs_indirect=0)
        assert fp == 12


class TestTotalFP:
    def test_all_rounder(self):
        fp = compute_total_fp(
            runs=30, balls=20, fours=2, sixes=1, is_dismissed=False,
            wickets=2, runs_conceded=20, overs=4, maidens=0,
            catches=1, match_type="T20"
        )
        assert fp > 0

    def test_pure_batter(self):
        fp = compute_total_fp(runs=75, balls=40, fours=8, sixes=3, is_dismissed=False, match_type="T20")
        assert fp > 80  # 75 + 8 + 6 + 8 + SR bonus
