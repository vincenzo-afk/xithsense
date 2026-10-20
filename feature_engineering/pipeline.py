"""
Feature store rebuild: persists the latest rolling form, venue stats and batter
matchup stats, and infers player roles where no metadata exists.

Run via `python scripts/build_features.py` or the admin "Rebuild features" action.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import case, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.models import (
    Delivery, Innings, Match, MatchupStat, Player, PlayerMatchPerformance, RollingFeature, Venue, VenueStat,
)
from feature_engineering.builder import FORMAT_GROUP

logger = logging.getLogger(__name__)

MIN_MATCHUP_BALLS = 30
MIN_VENUE_MATCHES = 5


async def infer_roles(db: AsyncSession) -> int:
    """Assign WK/BAT/AR/BOWL to players without a role from their career numbers."""
    P = PlayerMatchPerformance
    rows = (await db.execute(
        select(P.player_id, func.count(), func.avg(P.balls_bowled), func.avg(P.balls_faced),
               func.sum(P.stumpings), func.avg(P.batting_position))
        .join(Player, Player.id == P.player_id).where(Player.primary_role.is_(None))
        .group_by(P.player_id)
    )).all()
    n = 0
    for pid, cnt, bb, bf, st, pos in rows:
        bb, bf, st, pos = bb or 0, bf or 0, st or 0, pos or 11
        if st and st >= max(1, cnt * 0.05):
            role = "WK"
        elif bb >= 12 and bf >= 10 and pos <= 7:
            role = "AR"
        elif bb >= 9:
            role = "BOWL"
        else:
            role = "BAT"
        await db.execute(update(Player).where(Player.id == pid).values(primary_role=role))
        n += 1
    await db.commit()
    return n


async def refresh_current_teams(db: AsyncSession) -> int:
    """current_team = the side a player represented in his most recent match (franchise renames,
    transfers and international/club switches all resolve to the latest real line-up)."""
    P = PlayerMatchPerformance
    latest = (select(P.player_id, func.max(P.match_date).label("d")).group_by(P.player_id)).subquery()
    rows = (await db.execute(select(P.player_id, P.team).join(
        latest, (latest.c.player_id == P.player_id) & (latest.c.d == P.match_date)))).all()
    teams = {pid: team for pid, team in rows}
    for pid, team in teams.items():
        await db.execute(update(Player).where(Player.id == pid).values(current_team=team))
    await db.commit()
    return len(teams)


async def rebuild_rolling_features(db: AsyncSession) -> int:
    P = PlayerMatchPerformance
    rows = (await db.execute(select(
        P.player_id, P.match_id, P.match_date, P.match_type, P.runs_scored, P.balls_faced, P.fours, P.sixes,
        P.wickets_taken, P.runs_conceded, P.balls_bowled, P.fantasy_points))).all()
    if not rows:
        return 0
    df = pd.DataFrame(rows, columns=["player_id", "match_id", "match_date", "match_type", "runs", "balls", "fours",
                                     "sixes", "wickets", "conceded", "bb", "fp"])
    df["fmt"] = df.match_type.map(FORMAT_GROUP).fillna(df.match_type)
    df = df.sort_values(["player_id", "fmt", "match_date"], ascending=[True, True, False])
    await db.execute(delete(RollingFeature))
    out = []
    for (pid, fmt), g in df.groupby(["player_id", "fmt"], sort=False):
        as_of = g.match_date.iloc[0]
        for w in (3, 5, 10):
            h = g.head(w)
            fps = h.fp.astype(float).values
            last10 = g.head(10).fp.astype(float).values
            overs = h.bb.sum() / 6
            std = float(np.std(last10, ddof=1)) if len(last10) > 1 else 0.0
            avg10 = float(last10.mean())
            out.append({
                "id": uuid.uuid4(), "player_id": pid, "match_type": fmt, "as_of_date": as_of, "window_matches": w,
                "avg_runs": float(h.runs.mean()), "avg_balls": float(h.balls.mean()),
                "avg_sr": float(h.runs.sum() / h.balls.sum() * 100) if h.balls.sum() else None,
                "avg_fours": float(h.fours.mean()), "avg_sixes": float(h.sixes.mean()),
                "avg_wickets": float(h.wickets.mean()),
                "avg_economy": float(h.conceded.sum() / overs) if overs else None,
                "avg_overs": float(overs / len(h)),
                "fp_avg": float(fps.mean()),
                "fp_ceiling": float(np.percentile(last10, 90)), "fp_floor": float(np.percentile(last10, 10)),
                "fp_consistency": min(10.0, std / avg10) if avg10 > 0 else 0.0,
                "fp_30plus_rate": float((last10 >= 30).mean()),
                "fp_last_3": float(g.head(3).fp.mean()),
                "matches_included": int(len(h)), "last_match_id": g.match_id.iloc[0],
            })
    for i in range(0, len(out), 2000):
        await db.execute(insert(RollingFeature), out[i:i + 2000])
    await db.commit()
    return len(out)


async def rebuild_venue_stats(db: AsyncSession) -> int:
    M, I, D = Match, Innings, Delivery
    rows = (await db.execute(
        select(M.id, M.venue_id, M.match_type, M.match_winner, M.toss_winner, I.innings_number,
               I.batting_team, I.total_runs, I.total_wickets)
        .join(I, I.match_id == M.id).where(M.venue_id.is_not(None), M.status == "complete")
    )).all()
    if not rows:
        return 0
    df = pd.DataFrame(rows, columns=["match_id", "venue_id", "match_type", "winner", "toss_winner", "inn",
                                     "batting_team", "runs", "wkts"])
    df["fmt"] = df.match_type.map(FORMAT_GROUP).fillna(df.match_type)
    bnd = (await db.execute(
        select(D.match_id,
               func.sum(case((D.runs_batter >= 4, 1), else_=0)),
               func.sum(case(((D.is_wide.is_(False)) & (D.is_no_ball.is_(False)), 1), else_=0)))
        .group_by(D.match_id)
    )).all()
    wkdf = pd.DataFrame(bnd, columns=["match_id", "boundaries", "legal"])
    BP = aliased(Player)
    spin_w = (await db.execute(select(D.match_id, func.count()).join(BP, BP.id == D.bowler_id)
                               .where(D.is_wicket.is_(True), BP.bowler_type.like("spin%")).group_by(D.match_id))).all()
    pace_w = (await db.execute(select(D.match_id, func.count()).join(BP, BP.id == D.bowler_id)
                               .where(D.is_wicket.is_(True), BP.bowler_type.like("pace%")).group_by(D.match_id))).all()
    sw, pw = dict(spin_w), dict(pace_w)

    await db.execute(delete(VenueStat))
    n = 0
    for (vid, fmt), g in df.groupby(["venue_id", "fmt"]):
        matches = g.match_id.unique()
        first = g[g.inn == 1]
        second = g[g.inn == 2]
        chase_wins = (second.batting_team == second.winner).sum()
        toss_wins = (g.drop_duplicates("match_id").pipe(lambda x: (x.toss_winner == x.winner).sum()))
        spin_total = sum(sw.get(m, 0) for m in matches)
        pace_total = sum(pw.get(m, 0) for m in matches)
        all_w = spin_total + pace_total
        sub = wkdf[wkdf.match_id.isin(matches)]
        await db.execute(insert(VenueStat).values(
            id=uuid.uuid4(), venue_id=vid, match_type=fmt,
            avg_runs_per_innings=float(g.runs.mean()),
            avg_first_innings=float(first.runs.mean()) if len(first) else None,
            avg_second_innings=float(second.runs.mean()) if len(second) else None,
            avg_wickets_per_match=float(g.groupby("match_id").wkts.sum().mean()),
            spin_wicket_pct=float(spin_total / all_w) if all_w else None,
            pace_wicket_pct=float(pace_total / all_w) if all_w else None,
            chasing_win_pct=float(chase_wins / len(second)) if len(second) else None,
            boundary_index=float(sub.boundaries.sum() / sub.legal.sum() * 100) if sub.legal.sum() else None,
            toss_advantage="toss" if len(matches) and toss_wins / len(matches) > 0.55 else "neutral",
            total_matches=int(len(matches)),
        ))
        n += 1
    # Venue average first innings (T20 when available) for quick display
    t20_first = df[(df.inn == 1) & (df.fmt == "T20")]
    for vid, g in (t20_first if len(t20_first) else df[df.inn == 1]).groupby("venue_id"):
        await db.execute(update(Venue).where(Venue.id == vid).values(avg_first_innings_score=int(g.runs.mean())))

    # Pitch character from real T20 numbers (recomputed every rebuild):
    # batting = scores ≥12 above the global T20 par; spin / pace = wicket share skewed to that style
    t20 = (await db.execute(select(VenueStat).where(VenueStat.match_type == "T20",
                                                    VenueStat.total_matches >= MIN_VENUE_MATCHES))).scalars().all()
    if t20:
        par = float(np.nanmean([v.avg_first_innings for v in t20 if v.avg_first_innings]))
        for v in t20:
            if (v.avg_first_innings or 0) >= par + 12:
                pt = "batting"
            elif (v.spin_wicket_pct or 0) >= 0.45:
                pt = "spin"
            elif (v.pace_wicket_pct or 0) >= 0.72:
                pt = "pace"
            else:
                pt = "balanced"
            await db.execute(update(Venue).where(Venue.id == v.venue_id).values(pitch_type=pt))
    await db.commit()
    return n


async def rebuild_matchup_stats(db: AsyncSession) -> int:
    D = Delivery
    BP = aliased(Player)
    rows = (await db.execute(
        select(D.batter_id, BP.bowler_type, Match.match_type,
               func.sum(case((D.is_wide.is_(False), 1), else_=0)),
               func.sum(D.runs_batter),
               func.sum(case((D.wicket_player_out == D.batter, 1), else_=0)),
               func.sum(case(((D.runs_batter == 0) & D.is_wide.is_(False), 1), else_=0)),
               func.sum(case((D.runs_batter >= 4, 1), else_=0)))
        .join(Match, Match.id == D.match_id).join(BP, BP.id == D.bowler_id)
        .where(BP.bowler_type.is_not(None))
        .group_by(D.batter_id, BP.bowler_type, Match.match_type)
    )).all()
    agg: dict = {}
    for pid, bt, mt, balls, runs, outs, dots, bnd in rows:
        if pid is None:
            continue
        k = (pid, FORMAT_GROUP.get(mt, mt), bt)
        a = agg.setdefault(k, [0, 0, 0, 0, 0])
        for i, v in enumerate((balls, runs, outs, dots, bnd)):
            a[i] += v or 0
    await db.execute(delete(MatchupStat))
    out = []
    for (pid, fmt, bt), (balls, runs, outs, dots, bnd) in agg.items():
        if balls < MIN_MATCHUP_BALLS:
            continue
        out.append({
            "id": uuid.uuid4(), "player_id": pid, "match_type": fmt, "bowler_type": bt,
            "balls_faced": int(balls), "runs_scored": int(runs), "dismissals": int(outs),
            "strike_rate": round(runs / balls * 100, 2), "avg_runs": round(runs / (outs + 0.01), 2) if outs else float(runs),
            "dot_ball_pct": round(dots / balls, 4), "boundary_pct": round(bnd / balls, 4),
        })
    for i in range(0, len(out), 2000):
        await db.execute(insert(MatchupStat), out[i:i + 2000])
    await db.commit()
    return len(out)


async def run_pipeline(db: AsyncSession) -> dict:
    from feature_engineering.bowling_style import infer_bowling_styles
    roles = await infer_roles(db)
    styles = await infer_bowling_styles(db)
    teams = await refresh_current_teams(db)
    rolling = await rebuild_rolling_features(db)
    venues = await rebuild_venue_stats(db)
    matchups = await rebuild_matchup_stats(db)
    from feature_engineering.builder import _load_frames_sql, save_frames_cache
    save_frames_cache(await _load_frames_sql(db))
    report = {"roles_inferred": roles, "current_teams": teams, "bowling_styles": styles, "rolling_features": rolling, "venue_stats": venues,
              "matchup_stats": matchups, "built_at": date.today().isoformat()}
    logger.info("Feature pipeline: %s", report)
    return report
