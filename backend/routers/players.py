"""
Players router: search, profile (form, career, venues, phases), matchups.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import Delivery, MatchupStat, Player, PlayerMatchPerformance, RollingFeature, User
from backend.schemas import (
    FormPoint, MatchupOut, MatchupsResponse, PlayerDetailOut, PlayerOut, PlayerSearchResponse,
    RecentForm, VenueBreakdown,
)

router = APIRouter(prefix="/api/v1/players", tags=["players"])


def _not_found(pid) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "PLAYER_NOT_FOUND", "message": f"Player {pid} not found"})


@router.get("/search", response_model=PlayerSearchResponse)
async def search_players(
    q: Optional[str] = Query(None, max_length=60),
    team: Optional[str] = Query(None, max_length=100),
    role: Optional[str] = Query(None, pattern="^(BAT|BOWL|AR|WK|bat|bowl|ar|wk)$"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cond = [Player.is_active.is_(True)]
    if q:
        if any(ch in q for ch in "';\"\\") or "--" in q:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Invalid search query"})
        cond.append(func.lower(Player.full_name).contains(q.lower()))
    if team:
        cond.append(Player.current_team == team)
    if role:
        cond.append(Player.primary_role == role.upper())
    total = (await db.execute(select(func.count()).select_from(Player).where(*cond))).scalar_one()
    players = (await db.execute(select(Player).where(*cond).order_by(Player.base_credits.desc().nulls_last(),
                                                                     Player.full_name).limit(limit))).scalars().all()
    return PlayerSearchResponse(players=[PlayerOut.model_validate(p) for p in players], total=total)


@router.get("/{player_id}", response_model=PlayerDetailOut)
async def get_player(player_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    player = await db.get(Player, player_id)
    if not player:
        raise _not_found(player_id)

    feats = (await db.execute(select(RollingFeature).where(RollingFeature.player_id == player_id)
                              .order_by(RollingFeature.as_of_date.desc()))).scalars().all()
    windows = {}
    for f in feats:
        windows.setdefault(f.window_matches, f)
    form = None
    if windows:
        w10 = windows.get(10) or next(iter(windows.values()))
        form = RecentForm(
            last_3_fp_avg=windows.get(3).fp_avg if windows.get(3) else None,
            last_5_fp_avg=windows.get(5).fp_avg if windows.get(5) else None,
            last_10_fp_avg=w10.fp_avg, fp_ceiling=w10.fp_ceiling, fp_floor=w10.fp_floor,
            fp_consistency=w10.fp_consistency, fp_30plus_rate=w10.fp_30plus_rate)

    P = PlayerMatchPerformance
    c = (await db.execute(select(
        func.count(), func.sum(P.runs_scored), func.sum(P.balls_faced), func.sum(case((P.is_dismissed, 1), else_=0)),
        func.sum(P.wickets_taken), func.sum(P.runs_conceded), func.sum(P.balls_bowled), func.avg(P.fantasy_points),
        func.max(P.fantasy_points), func.sum(case((P.runs_scored >= 50, 1), else_=0)), func.max(P.runs_scored),
        func.sum(P.catches), func.sum(P.sixes), func.sum(P.fours),
    ).where(P.player_id == player_id))).one()
    m, runs, balls, outs, wkts, conc, bb, fpavg, fpmax, fifties, hs, catches, sixes, fours = c
    career = None
    if m:
        career = {
            "matches": m, "runs": runs or 0, "batting_avg": round((runs or 0) / outs, 2) if outs else None,
            "strike_rate": round((runs or 0) / balls * 100, 1) if balls else None, "fifties": fifties or 0,
            "highest_score": hs or 0, "fours": fours or 0, "sixes": sixes or 0,
            "wickets": wkts or 0, "economy": round(conc / (bb / 6), 2) if bb else None,
            "bowling_avg": round(conc / wkts, 2) if wkts else None, "catches": catches or 0,
            "fp_avg": round(fpavg or 0, 1), "fp_best": round(fpmax or 0, 1),
        }

    recent = (await db.execute(select(P).where(P.player_id == player_id).order_by(P.match_date.desc()).limit(10))).scalars().all()
    chart = [FormPoint(match_id=r.match_id, match_date=r.match_date, opposition=r.opposition,
                       venue=(r.venue_name or "").split(",")[0], fantasy_points=r.fantasy_points or 0,
                       runs=r.runs_scored, balls=r.balls_faced, wickets=r.wickets_taken, overs=r.overs_bowled or 0)
             for r in reversed(recent)]

    vrows = (await db.execute(select(P.venue_name, func.count(), func.avg(P.fantasy_points), func.avg(P.runs_scored),
                                     func.avg(P.wickets_taken))
                              .where(P.player_id == player_id).group_by(P.venue_name)
                              .having(func.count() >= 2).order_by(func.avg(P.fantasy_points).desc()).limit(5))).all()
    venues = [VenueBreakdown(venue=v or "Unknown", matches=n, fp_avg=round(a or 0, 1), runs_avg=round(r or 0, 1),
                             wickets_avg=round(w or 0, 2)) for v, n, a, r, w in vrows]

    D = Delivery
    phase_rows = (await db.execute(select(D.phase, func.sum(case((D.is_wide.is_(False), 1), else_=0)),
                                          func.sum(D.runs_batter),
                                          func.sum(case((D.wicket_player_out == D.batter, 1), else_=0)))
                                   .where(D.batter_id == player.id).group_by(D.phase))).all()
    bowl_rows = (await db.execute(select(D.phase, func.sum(case(((D.is_wide.is_(False)) & (D.is_no_ball.is_(False)), 1), else_=0)),
                                         func.sum(D.runs_batter + D.extra_wides + D.extra_no_balls),
                                         func.sum(case((D.is_wicket.is_(True) & (D.wicket_kind != "run out"), 1), else_=0)))
                                  .where(D.bowler_id == player.id).group_by(D.phase))).all()
    phases = {}
    for ph, b, r, o in phase_rows:
        if ph and b:
            phases.setdefault(ph, {})["bat_sr"] = round(r / b * 100, 1)
            phases[ph]["bat_balls"] = b
            phases[ph]["bat_outs"] = o
    for ph, b, r, w in bowl_rows:
        if ph and b:
            phases.setdefault(ph, {})["bowl_econ"] = round(r / (b / 6), 2)
            phases[ph]["bowl_balls"] = b
            phases[ph]["bowl_wkts"] = w

    return PlayerDetailOut(**PlayerOut.model_validate(player).model_dump(), recent_form=form, career=career,
                           form_chart=chart, venues=venues, phase_split=phases)


@router.get("/{player_id}/matchups", response_model=MatchupsResponse)
async def get_matchups(player_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    player = await db.get(Player, player_id)
    if not player:
        raise _not_found(player_id)
    stats = (await db.execute(select(MatchupStat).where(MatchupStat.player_id == player_id)
                              .order_by(MatchupStat.balls_faced.desc()))).scalars().all()
    return MatchupsResponse(
        player_id=player.id, full_name=player.full_name,
        matchups=[MatchupOut(
            bowler_type=s.bowler_type, balls_faced=s.balls_faced, strike_rate=s.strike_rate, avg_runs=s.avg_runs,
            dismissal_rate=round(s.dismissals / s.balls_faced, 4) if s.balls_faced else None,
            boundary_rate=s.boundary_pct, dot_ball_rate=s.dot_ball_pct,
            confidence=round(min(s.balls_faced / 100, 1.0), 2)) for s in stats])
