"""Unit tests for the LP team optimizer, ownership heuristic and captain engine."""
import random

import pytest

from optimizer.captain_engine import recommend
from optimizer.constraints import team_violations
from optimizer.lp_optimizer import _local_search, solve_team
from optimizer.constraints import ROLE_MAX
from optimizer.scoring import OptPlayer, differential_bonus, estimate_ownership, score_for_mode

ROLES = ["WK"] * 2 + ["BAT"] * 4 + ["AR"] * 2 + ["BOWL"] * 4


def pool(seed=1, n_per_team=12):
    rng = random.Random(seed)
    out = []
    for t in ("A", "B"):
        for i in range(n_per_team):
            role = ROLES[i % len(ROLES)]
            fp = rng.uniform(15, 60)
            out.append(OptPlayer(player_id=f"{t}{i}", full_name=f"{t} player {i}", role=role,
                                 credits=rng.choice([7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]), team=t,
                                 predicted_fp=fp, ceiling=fp * 1.8, floor=fp * 0.3, fp_std=fp * 0.6,
                                 fp_avg_5=fp, fp_avg_10=fp, consistency=0.6, ownership=rng.uniform(2, 80),
                                 confidence=rng.randint(30, 95)))
    return out


@pytest.mark.parametrize("mode", ["safe", "grand_league", "aggressive", "small_league"])
def test_lp_team_satisfies_dream11_rules(mode):
    ps = pool()
    score_for_mode(ps, mode)
    res = solve_team(ps, min_differentials=1 if mode == "grand_league" else 0)
    assert res is not None and res.solver == "lp"
    assert team_violations(res.players, res.captain.player_id, res.vice_captain.player_id) == []
    if mode == "grand_league":
        assert any(p.ownership < 20 for p in res.players)


def test_lp_beats_or_matches_local_search():
    ps = pool(seed=3)
    score_for_mode(ps, "safe")
    lp = solve_team(ps)
    ls = _local_search(ps, [], 11, ROLE_MAX)
    lp_val = sum(p.score for p in lp.players)
    ls_val = sum(ps[i].score for i in ls)
    assert lp_val >= ls_val - 1e-6


def test_diversity_constraint():
    ps = pool(seed=5)
    score_for_mode(ps, "safe")
    first = solve_team(ps)
    second = solve_team(ps, previous=[{p.player_id for p in first.players}], max_overlap=9)
    overlap = {p.player_id for p in first.players} & {p.player_id for p in second.players}
    assert len(overlap) <= 9


def test_captain_is_highest_scorer_on_lp():
    ps = pool(seed=7)
    score_for_mode(ps, "safe")
    res = solve_team(ps)
    assert res.captain.score == max(p.score for p in res.players)


def test_infeasible_pool_returns_none():
    ps = [p for p in pool() if p.team == "A"]  # one team only
    score_for_mode(ps, "safe")
    assert solve_team(ps) is None


def test_ownership_heuristic_monotone_and_bounded():
    scores = [90, 70, 50, 30, 10]
    own = estimate_ownership(scores, ["BAT"] * 5)
    assert own == sorted(own, reverse=True)
    assert all(0.5 <= o <= 95 for o in own)


def test_differential_bonus_tiers():
    assert differential_bonus(3) == 20 and differential_bonus(7) == 12
    assert differential_bonus(15) == 6 and differential_bonus(40) == 0


def test_captain_engine_constraints():
    ps = pool(seed=9)
    score_for_mode(ps, "grand_league")
    res = solve_team(ps)
    picks = recommend(res.players, "grand_league")
    ids = [p.player.player_id for p in picks]
    xi = {p.player_id for p in res.players}
    assert len(set(ids)) == len(ids) and set(ids) <= xi
    assert [p.type for p in picks] == ["best_captain", "safe_captain", "risk_captain"]
    rotated = recommend(res.players, "grand_league", rotation=1)
    assert rotated[0].player.player_id != picks[0].player.player_id
