"""
Backtesting harness (BACKTESTING_SPEC / METRICS_DEFINITIONS).

A model is trained only on matches before the test window; every test match is
then replayed with its actual playing XI: leakage-free features → ensemble →
safe-mode optimizer → captain engine. Metrics:

  correct_player_rate  share of matches with ≥7 of our XI in the actual top-11 by FP
  avg_players_correct  mean overlap with the actual top-11
  captain_accuracy     our captain == actual top scorer
  vc_accuracy          our VC == actual 2nd-highest scorer
  top3_captain_rate    actual top scorer is among our 3 captain recommendations
  avg_fp_error         mean |predicted − actual| team total (11 players, no multipliers)
  spearman_rho         per-match rank correlation of predicted vs actual FP, averaged
  simulated_roi        ₹50 entry, 2× payout when our C/VC-weighted total beats the
                       75th percentile of 60 random valid teams for that match
"""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import BacktestRun, Match, Player, Venue
from feature_engineering.builder import FORMAT_GROUP, build_feature_frame, load_frames
from human_rules.engine import MatchContext, evaluate_rules_detailed
from optimizer.captain_engine import recommend
from optimizer.lp_optimizer import solve_team, _valid
from optimizer.constraints import ROLE_MAX
from optimizer.scoring import OptPlayer, estimate_ownership, score_for_mode
from training.models import fit_bundle, spearman
from training.train import training_rows

logger = logging.getLogger(__name__)


def _random_teams(players: List[OptPlayer], n: int, rng: random.Random) -> List[List[OptPlayer]]:
    teams, tries = [], 0
    by_role = {r: [p for p in players if p.role == r] for r in ("WK", "BAT", "AR", "BOWL")}
    while len(teams) < n and tries < n * 200:
        tries += 1
        shape = rng.choice([(1, 4, 2, 4), (1, 3, 3, 4), (2, 3, 2, 4), (1, 4, 1, 5), (1, 5, 2, 3), (2, 4, 2, 3)])
        try:
            pick = [p for r, k in zip(("WK", "BAT", "AR", "BOWL"), shape) for p in rng.sample(by_role[r], k)]
        except ValueError:
            continue
        if _valid(pick, ROLE_MAX):
            teams.append(pick)
    return teams


def _weighted_total(team: List[OptPlayer], actual: Dict[str, float], cap: str, vc: str) -> float:
    return sum(actual.get(p.player_id, 0) * (2 if p.player_id == cap else 1.5 if p.player_id == vc else 1)
               for p in team)


async def run_backtest(db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None,
                       n: int = 10000, name: Optional[str] = None, seed: int = 11, group: str = "T20",
                       frame: Optional[pd.DataFrame] = None, gender: Optional[str] = "male") -> dict:
    if frame is None:
        frames = await load_frames(db)
        frame = await asyncio.to_thread(build_feature_frame, frames)
    hist = frame[~frame.is_pending & frame.fp.notna()]
    hist = hist[hist.match_type.map(FORMAT_GROUP).fillna(hist.match_type) == group].copy()
    dates = np.sort(hist.match_date.unique())
    if len(dates) < 20:
        raise RuntimeError("Not enough history to backtest")
    start = pd.Timestamp(from_date) if from_date else pd.Timestamp(dates[int(len(dates) * 0.8)])
    end = pd.Timestamp(to_date) if to_date else pd.Timestamp(dates[-1])

    train = training_rows(hist[hist.match_date < start], group)
    bundle = await asyncio.to_thread(fit_bundle, train, None, group)

    test = hist[(hist.match_date >= start) & (hist.match_date <= end)]
    if gender:
        gmap = dict((await db.execute(select(Match.id, Match.gender).where(Match.id.in_(list(test.match_id.unique()))))).all())
        test = test[test.match_id.map(gmap) == gender]
    match_ids = list(dict.fromkeys(test.sort_values("match_date").match_id))[-n:]

    players = {str(p.id): p for p in (await db.execute(select(Player))).scalars()}
    matches = {m.id: m for m in (await db.execute(select(Match).where(Match.id.in_(match_ids)))).scalars()}
    venues = {v.name: v for v in (await db.execute(select(Venue))).scalars()}
    rng = random.Random(seed)

    per_match = []
    for mid in match_ids:
        g = test[test.match_id == mid]
        m = matches.get(mid)
        if m is None or len(g) < 18 or g.team.nunique() != 2:
            continue
        pred = bundle.predict(g)
        venue = venues.get(m.venue_name)
        other = m.team_b if m.toss_winner == m.team_a else m.team_a
        bat_first = (m.toss_winner if m.toss_decision == "bat" else other) if m.toss_winner else None
        rules = []
        for _, row in g.iterrows():
            p = players[str(row.player_id)]
            ctx = MatchContext(match_type=m.match_type, venue=m.venue_name,
                               pitch_type=venue.pitch_type if venue else None,
                               is_chasing=(row.team != bat_first) if bat_first else None,
                               toss_decision=m.toss_decision, is_home=bool(row.is_home),
                               batting_style=p.batting_style, bowling_style=p.bowling_style,
                               primary_role=p.primary_role, match_date=m.match_date,
                               is_final_or_knockout=row.match_importance > 0.6)
            rules.append(evaluate_rules_detailed(p.cricsheet_key, ctx)[0])
        rules = np.array(rules)
        predicted = np.clip(pred["ml"] + 0.35 * rules, 0, None)
        ceiling = np.maximum(0.6 * pred["ceiling"] + 0.4 * g.fp_ceiling.values, predicted * 1.25)
        floor = np.clip(np.minimum(0.6 * pred["floor"] + 0.4 * g.fp_floor.values, predicted * 0.8), 0, None)
        roles = [players[str(pid)].primary_role or "BAT" for pid in g.player_id]
        own = estimate_ownership(list(predicted), roles)
        opts = [OptPlayer(player_id=str(r.player_id), full_name=players[str(r.player_id)].full_name, role=roles[i],
                          credits=float(players[str(r.player_id)].base_credits or 8.0), team=r.team,
                          predicted_fp=float(predicted[i]), ceiling=float(ceiling[i]), floor=float(floor[i]),
                          fp_std=float(r.fp_std_10), fp_avg_5=float(r.fp_avg_5), fp_avg_10=float(r.fp_avg_10),
                          consistency=float(r.fp_consistency), ownership=own[i], confidence=60)
                for i, (_, r) in enumerate(g.iterrows())]
        score_for_mode(opts, "safe")
        res = solve_team(opts)
        if res is None:
            continue
        caps = recommend(res.players, "safe")
        actual = dict(zip(g.player_id.astype(str), g.fp.astype(float)))
        ranked_actual = sorted(actual, key=actual.get, reverse=True)
        top11 = set(ranked_actual[:11])
        ours = {p.player_id for p in res.players}
        cap_id, vc_id = caps[0].player.player_id, caps[1].player.player_id
        our_total = _weighted_total(res.players, actual, cap_id, vc_id)
        field = [_weighted_total(t, actual, *[x.player_id for x in sorted(t, key=lambda p: -p.predicted_fp)[:2]])
                 for t in _random_teams(opts, 60, rng)]
        threshold = float(np.percentile(field, 75)) if field else our_total
        per_match.append({
            "match_id": mid, "date": str(m.match_date), "teams": f"{m.team_a} vs {m.team_b}",
            "players_correct": len(ours & top11),
            "captain_correct": cap_id == ranked_actual[0],
            "vc_correct": vc_id == ranked_actual[1],
            "top3_captain": ranked_actual[0] in {c.player.player_id for c in caps},
            "fp_error": abs(sum(p.predicted_fp for p in res.players) - sum(actual[p.player_id] for p in res.players)),
            "rho": spearman(predicted, g.fp.values),
            "our_points": round(our_total, 1), "field_p75": round(threshold, 1),
            "won": our_total > threshold,
            "captain": caps[0].player.full_name,
            "top_scorer": players[ranked_actual[0]].full_name,
        })

    if not per_match:
        raise RuntimeError("No backtestable matches in range")
    pm = pd.DataFrame(per_match)
    entries = len(pm) * 50
    payout = pm.won.sum() * 100
    metrics = {
        "total_matches": int(len(pm)),
        "correct_player_rate": round(float((pm.players_correct >= 7).mean()), 4),
        "avg_players_correct": round(float(pm.players_correct.mean()), 2),
        "captain_accuracy": round(float(pm.captain_correct.mean()), 4),
        "vc_accuracy": round(float(pm.vc_correct.mean()), 4),
        "top3_captain_rate": round(float(pm.top3_captain.mean()), 4),
        "avg_fp_error": round(float(pm.fp_error.mean()), 2),
        "spearman_rho": round(float(pm.rho.dropna().mean()), 4),
        "simulated_roi": round(float((payout - entries) / entries), 4),
        "baselines": {"captain_random": round(1 / 11, 4), "top3_random": round(3 / 11, 4)},
    }
    run = BacktestRun(
        name=name or f"{group} backtest {start.date()} → {end.date()}", match_type=group,
        from_date=start.date(), to_date=end.date(), total_matches=metrics["total_matches"],
        correct_player_rate=metrics["correct_player_rate"], captain_accuracy=metrics["captain_accuracy"],
        vc_accuracy=metrics["vc_accuracy"], top3_captain_rate=metrics["top3_captain_rate"],
        avg_players_correct=metrics["avg_players_correct"], avg_fp_error=metrics["avg_fp_error"],
        spearman_rho=metrics["spearman_rho"], simulated_roi=metrics["simulated_roi"],
        details={"matches": per_match[-60:], "train_rows": len(train), "baselines": metrics["baselines"]},
    )
    db.add(run)
    await db.commit()
    return {"run_id": str(run.id), "date_range": [str(start.date()), str(end.date())], "metrics": metrics}
