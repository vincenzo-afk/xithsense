"""
Matches router: upcoming, recent, detail (venue, squads, head-to-head, form).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import Match, Player, PlayerTeamMatch, User, Venue, VenueStat
from backend.schemas import (
    HeadToHead, MatchDetailOut, MatchListResponse, MatchOut, SquadPlayerOut, TossOut, VenueOut,
)

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])

FORMAT_FILTER = {"T20": ("T20", "IT20", "IPL", "BBL", "PSL", "CPL", "WPL"), "IPL": ("IPL",),
                 "ODI": ("ODI", "ODM", "WOD"), "Test": ("Test", "MDM")}


def match_out(m: Match) -> MatchOut:
    return MatchOut(
        **{c.key: getattr(m, c.key) for c in Match.__table__.columns if c.key in MatchOut.model_fields},
        toss=TossOut(winner=m.toss_winner, decision=m.toss_decision) if m.toss_winner else None,
        is_live=m.status == "live",
        prediction_ready=m.status in ("upcoming", "live"),
    )


@router.get("/upcoming", response_model=MatchListResponse)
async def list_upcoming(
    format: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Cheap freshness: one shared currentMatches call (cached 20 min) updates live status / toss / scores
    from integrations import cricapi
    if cricapi.configured():
        from datetime import timedelta
        from integrations.fixtures import refresh_live_status
        await refresh_live_status(db, max_age=timedelta(minutes=20))
    cond = Match.status.in_(("upcoming", "live"))
    if format and format in FORMAT_FILTER:
        cond = and_(cond, Match.match_type.in_(FORMAT_FILTER[format]))
    q = (select(Match).where(cond)
         .order_by((Match.status != "live"), Match.match_date, Match.start_time).offset(offset).limit(limit))
    matches = (await db.execute(q)).scalars().all()
    total = (await db.execute(select(func.count()).select_from(Match).where(cond))).scalar_one()
    return MatchListResponse(matches=[match_out(m) for m in matches], total=total)


@router.get("/recent", response_model=MatchListResponse)
async def list_recent(
    team: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cond = Match.status == "complete"
    if team:
        cond = and_(cond, or_(Match.team_a == team, Match.team_b == team))
    matches = (await db.execute(select(Match).where(cond).order_by(Match.match_date.desc()).limit(limit))).scalars().all()
    return MatchListResponse(matches=[match_out(m) for m in matches], total=len(matches))


async def _team_form(db: AsyncSession, team: str, before) -> List[str]:
    rows = (await db.execute(
        select(Match.match_winner).where(Match.status == "complete", Match.match_date < before,
                                         or_(Match.team_a == team, Match.team_b == team))
        .order_by(Match.match_date.desc()).limit(5))).scalars().all()
    return ["W" if w == team else "T" if w is None else "L" for w in rows]


@router.get("/{match_id}", response_model=MatchDetailOut)
async def get_match(match_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    m = await db.get(Match, match_id)
    if not m:
        raise HTTPException(status_code=404, detail={"code": "MATCH_NOT_FOUND", "message": f"Match {match_id} not found"})
    base = match_out(m)

    venue_out = None
    if m.venue_id:
        v = await db.get(Venue, m.venue_id)
        vs = (await db.execute(select(VenueStat).where(VenueStat.venue_id == m.venue_id))).scalars().first()
        if v:
            venue_out = VenueOut(name=v.name, city=v.city, country=v.country, pitch_type=v.pitch_type,
                                 dew_factor=bool(v.dew_factor), avg_first_innings_score=v.avg_first_innings_score,
                                 chasing_win_pct=vs.chasing_win_pct if vs else None,
                                 spin_wicket_pct=vs.spin_wicket_pct if vs else None,
                                 pace_wicket_pct=vs.pace_wicket_pct if vs else None,
                                 total_matches=vs.total_matches if vs else None)

    rows = (await db.execute(select(PlayerTeamMatch, Player).join(Player, Player.id == PlayerTeamMatch.player_id)
                             .where(PlayerTeamMatch.match_id == match_id)
                             .order_by(PlayerTeamMatch.batting_order))).all()
    squads: Dict[str, List[SquadPlayerOut]] = {m.team_a: [], m.team_b: []}
    for ptm, p in rows:
        squads.setdefault(ptm.team, []).append(SquadPlayerOut(
            player_id=p.id, full_name=p.full_name, role=p.primary_role, team=ptm.team,
            credits=ptm.credits or p.base_credits, is_playing=ptm.is_playing,
            batting_style=p.batting_style, bowling_style=p.bowling_style))

    h2h_rows = (await db.execute(
        select(Match).where(Match.status == "complete", Match.match_date < m.match_date,
                            or_(and_(Match.team_a == m.team_a, Match.team_b == m.team_b),
                                and_(Match.team_a == m.team_b, Match.team_b == m.team_a)))
        .order_by(Match.match_date.desc()))).scalars().all()
    h2h = HeadToHead(
        matches=len(h2h_rows),
        team_a_wins=sum(1 for x in h2h_rows if x.match_winner == m.team_a),
        team_b_wins=sum(1 for x in h2h_rows if x.match_winner == m.team_b),
        last_results=[{"match_id": x.id, "date": str(x.match_date), "winner": x.match_winner,
                       "margin": (f"{x.win_by_runs} runs" if x.win_by_runs else
                                  f"{x.win_by_wickets} wkts" if x.win_by_wickets else "—"),
                       "venue": (x.venue_name or "").split(",")[0]} for x in h2h_rows[:5]],
    )
    form = {m.team_a: await _team_form(db, m.team_a, m.match_date),
            m.team_b: await _team_form(db, m.team_b, m.match_date)}
    return MatchDetailOut(**base.model_dump(), venue=venue_out, squads=squads, head_to_head=h2h, team_form=form)
