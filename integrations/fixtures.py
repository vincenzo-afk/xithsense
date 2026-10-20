"""
Fixture sync: CricketData series schedules → upcoming / live Match rows with squads.

* Series are discovered from the paginated `series` list, filtered to those
  overlapping the next FIXTURE_DAYS_AHEAD days and ranked by importance
  (internationals and major franchise leagues first). Admins can pin series.
* Team and venue names are mapped onto Cricsheet's names (gender-aware, fuzzy).
* Squads: the official squad when the provider has one (`hasSquad`, 10 hits),
  otherwise a **probable squad** built from the team's real recent line-ups in
  Cricsheet data. Credits are priced from each player's real recent form.
"""
from __future__ import annotations

import difflib
import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import ApiCache, Match, Player, PlayerMatchPerformance, PlayerTeamMatch, Venue
from feature_engineering.builder import FORMAT_GROUP
from integrations import cricapi

logger = logging.getLogger(__name__)

PINNED_KEY = "xithsense:pinned_series"
NOT_API = func.coalesce(Match.source, "cricsheet") != "cricapi"   # historical (Cricsheet) rows have source NULL/cricsheet
MAJOR = ["indian premier league", "big bash", "pakistan super league", "caribbean premier league",
         "sa20", "the hundred", "major league cricket", "women's premier league", "womens premier league",
         "international league t20", "bangladesh premier league", "lanka premier league", "super smash"]
INTERNATIONAL = [" tour of ", "world cup", "icc ", "champions trophy", "asia cup", "tri-series", "tri series",
                 " vs ", "world test championship"]
LOW = ["ranji", "sheffield shield", "county championship", "plunket", "duleep", "vijay hazare", "syed mushtaq",
       "provincial", "one-day cup", "plate", "under-19", "u19", " a tour of ", " a team", "emerging", "qualifier"]
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def match_id_for(api_id: str) -> str:
    return "CA" + uuid.UUID(api_id).hex[:18]


def _norm(s: str) -> str:
    s = s.lower().replace("bangalore", "bengaluru").replace("&", "and")
    s = re.sub(r"\bwomen\b|\bwomens\b|\(w\)|\bxi\b", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _parse_series_date(s: str, ref: date) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    m = re.match(r"([A-Za-z]{3})\w*\s+(\d{1,2})", s.strip())
    if not m or m.group(1).lower() not in MONTHS:
        return None
    mon, day = MONTHS[m.group(1).lower()], int(m.group(2))
    best = None
    for yr in (ref.year - 1, ref.year, ref.year + 1):
        try:
            d = date(yr, mon, day)
        except ValueError:
            continue
        if best is None or abs((d - ref).days) < abs((best - ref).days):
            best = d
    return best


def series_priority(name: str) -> int:
    n = f" {name.lower()} "
    if any(k in n for k in LOW):
        return 1
    if any(k in n for k in MAJOR):
        return 4
    if any(k in n for k in INTERNATIONAL):
        return 3 if "women" not in n else 2
    return 2


# ── Name mapping ──────────────────────────────────────────────────────────────

class NameIndex:
    """Cricsheet team & venue names for fuzzy mapping of provider names."""

    def __init__(self, teams: Dict[str, List[str]], venues: List[str]):
        self.teams = teams            # gender -> team names
        self.venues = venues

    @classmethod
    async def build(cls, db: AsyncSession) -> "NameIndex":
        cutoff = date.today() - timedelta(days=5 * 365)
        rows = (await db.execute(select(Match.team_a, Match.team_b, Match.gender)
                                 .where(NOT_API, Match.match_date >= cutoff).distinct())).all()
        teams: Dict[str, set] = {"male": set(), "female": set()}
        for a, b, g in rows:
            teams.setdefault(g or "male", set()).update([a, b])
        venues = [v for (v,) in (await db.execute(select(Venue.name))).all()]
        return cls({g: sorted(t) for g, t in teams.items()}, venues)

    def team(self, api_name: str, gender: str) -> str:
        """Map 'India Women' → 'India' (female), 'Royal Challengers Bangalore' → current Cricsheet name."""
        cands = self.teams.get(gender, [])
        target = _norm(api_name)
        exact = [t for t in cands if _norm(t) == target]
        if exact:
            return exact[0]
        best = difflib.get_close_matches(target, [_norm(t) for t in cands], n=1, cutoff=0.82)
        if best:
            return next(t for t in cands if _norm(t) == best[0])
        return re.sub(r"\s+Women$", "", api_name).strip()

    def venue(self, api_venue: str) -> str:
        if not api_venue:
            return api_venue
        head = _norm(api_venue.split(",")[0])
        heads = {v: _norm(v.split(",")[0]) for v in self.venues}
        exact = [v for v, h in heads.items() if h == head]
        if exact:
            return max(exact, key=len)
        best = difflib.get_close_matches(head, list(heads.values()), n=1, cutoff=0.8)
        if best:
            return next(v for v, h in heads.items() if h == best[0])
        return api_venue


# ── Squads ────────────────────────────────────────────────────────────────────

async def probable_squad(db: AsyncSession, team: str, gender: str, match_type: str, before: date,
                         size: int = 16) -> List[Tuple[uuid.UUID, int]]:
    """Players ranked by appearances in the team's most recent real matches (same format group first)."""
    group = FORMAT_GROUP.get(match_type, match_type)
    fmt_types = [t for t, g in FORMAT_GROUP.items() if g == group]
    for types in (fmt_types, None):
        q = (select(Match.id).where(Match.gender == gender, Match.match_date < before,
                                    (Match.team_a == team) | (Match.team_b == team), NOT_API)
             .order_by(Match.match_date.desc()).limit(8))
        if types:
            q = q.where(Match.match_type.in_(types))
        ids = [m for (m,) in (await db.execute(q)).all()]
        if len(ids) >= 3:
            break
    if not ids:
        return []
    recency = {mid: len(ids) - i for i, mid in enumerate(ids)}
    rows = (await db.execute(select(PlayerTeamMatch.player_id, PlayerTeamMatch.match_id)
                             .where(PlayerTeamMatch.match_id.in_(ids), PlayerTeamMatch.team == team))).all()
    score: Dict[uuid.UUID, float] = {}
    for pid, mid in rows:
        score[pid] = score.get(pid, 0) + 1 + recency[mid] * 0.15
    ranked = sorted(score.items(), key=lambda kv: -kv[1])[:size]
    return [(pid, round(s * 10)) for pid, s in ranked]


_ROLE_DIST: Dict[str, List[float]] = {}


async def _role_distributions(db: AsyncSession) -> Dict[str, List[float]]:
    """League-wide distribution of per-player average fantasy points by role (last 3 years, 8+ matches)."""
    if _ROLE_DIST:
        return _ROLE_DIST
    import bisect  # noqa: F401
    P = PlayerMatchPerformance
    since = date.today() - timedelta(days=3 * 365)
    rows = (await db.execute(
        select(Player.primary_role, func.avg(P.fantasy_points))
        .join(Player, Player.id == P.player_id).where(P.match_date >= since)
        .group_by(P.player_id, Player.primary_role).having(func.count() >= 8))).all()
    for role, avg in rows:
        _ROLE_DIST.setdefault(role or "BAT", []).append(float(avg or 0))
    for v in _ROLE_DIST.values():
        v.sort()
    return _ROLE_DIST


ROLE_MAX_CREDITS = {"WK": 10.5, "BAT": 10.5, "AR": 10.5, "BOWL": 10.0}


async def price_credits(db: AsyncSession, player_ids: List[uuid.UUID]) -> Dict[uuid.UUID, float]:
    """Dream11-style credits (6.0–10.5), priced like Dream11 does — relative to the player's role:
    percentile of his fantasy points (last 30 weighted 60%, last 10 weighted 40%) among all
    players of that role across the league. Small samples shrink towards a modest prior."""
    import bisect
    P = PlayerMatchPerformance
    dist = await _role_distributions(db)
    roles = dict((await db.execute(select(Player.id, Player.primary_role).where(Player.id.in_(player_ids)))).all())
    out: Dict[uuid.UUID, float] = {}
    for pid in player_ids:
        rows = [r or 0 for r in (await db.execute(select(P.fantasy_points).where(P.player_id == pid)
                                                  .order_by(P.match_date.desc()).limit(30))).scalars().all()]
        role = roles.get(pid) or "BAT"
        if rows:
            recent = rows[:10]
            value = 0.4 * (sum(recent) / len(recent)) + 0.6 * (sum(rows) / len(rows))
            value = (value * len(rows) + 20.0 * 3) / (len(rows) + 3)
        else:
            value = 15.0
        ref = dist.get(role) or sorted(x for v in dist.values() for x in v) or [value]
        pct = bisect.bisect_left(ref, value) / len(ref)
        top = ROLE_MAX_CREDITS.get(role, 10.5)
        out[pid] = round((6.0 + min(1.0, pct) ** 1.2 * (top - 6.0)) * 2) / 2
    return out


def _surname_key(name: str) -> Tuple[str, str]:
    parts = re.sub(r"[^A-Za-z\s'-]", "", name).split()
    return (parts[-1].lower() if parts else "", parts[0][0].lower() if parts else "")


async def resolve_player(db: AsyncSession, api_player: dict, team_pool: List[Player], team: str) -> Player:
    """Map a provider player ('Virat Kohli') onto a Cricsheet player ('V Kohli') within the team pool."""
    api_id = api_player.get("id")
    if api_id:
        known = (await db.execute(select(Player).where(Player.cricapi_id == api_id))).scalars().first()
        if known:
            return known
    name = api_player.get("name", "")
    sur, ini = _surname_key(name)
    cands = [p for p in team_pool if _surname_key(p.full_name)[0] == sur]
    if len(cands) > 1:
        cands = [p for p in cands if _surname_key(p.full_name)[1] == ini] or cands
    if not cands:
        full = (await db.execute(select(Player).where(func.lower(Player.full_name) == name.lower()))).scalars().all()
        cands = full
    player = cands[0] if cands else None
    if player is None:
        player = Player(full_name=name, cricsheet_key=f"{name} [api:{(api_id or uuid.uuid4().hex)[:8]}]",
                        current_team=team, is_active=True)
        db.add(player)
        await db.flush()
    player.cricapi_id = api_id or player.cricapi_id
    if api_player.get("playerImg") and "icon512" not in api_player["playerImg"]:
        player.image_url = api_player["playerImg"]
    role = (api_player.get("role") or "").lower()
    if role:
        player.primary_role = ("WK" if "wk" in role or "keeper" in role else "AR" if "allrounder" in role or "all-rounder" in role
                               else "BOWL" if "bowl" in role else "BAT")
    if api_player.get("battingStyle"):
        player.batting_style = "Left-hand bat" if "left" in api_player["battingStyle"].lower() else "Right-hand bat"
    if api_player.get("bowlingStyle"):
        from ingestion.parser import get_bowler_type
        player.bowling_style = api_player["bowlingStyle"]
        player.bowler_type = get_bowler_type(api_player["bowlingStyle"])
        player.style_source = "api"
    return player


async def build_squads(db: AsyncSession, m: Match, use_official: bool = False) -> str:
    """(Re)build PlayerTeamMatch rows for an upcoming match. Returns the squad source used."""
    official: List[dict] = []
    if use_official and m.cricapi_id:
        try:
            official = await cricapi.match_squad(db, m.cricapi_id)
        except (cricapi.QuotaExceeded, cricapi.ApiError) as e:
            logger.warning("Official squad unavailable for %s: %s", m.id, e)
    await db.execute(delete(PlayerTeamMatch).where(PlayerTeamMatch.match_id == m.id))

    picked: Dict[str, List[uuid.UUID]] = {}
    source = "probable"
    if official and all(t.get("players") for t in official):
        source = "official"
        index = await NameIndex.build(db)
        for t in official:
            team = index.team(t.get("teamName", ""), m.gender)
            if team not in (m.team_a, m.team_b):
                team = m.team_a if difflib.SequenceMatcher(None, team, m.team_a).ratio() >= \
                    difflib.SequenceMatcher(None, team, m.team_b).ratio() else m.team_b
            pool_ids = [pid for pid, _ in await probable_squad(db, team, m.gender, m.match_type, m.match_date, size=40)]
            pool = list((await db.execute(select(Player).where(Player.id.in_(pool_ids)))).scalars()) if pool_ids else []
            picked[team] = []
            for ap in t["players"]:
                p = await resolve_player(db, ap, pool, team)
                if p.id not in picked[team]:
                    picked[team].append(p.id)
    else:
        for team in (m.team_a, m.team_b):
            picked[team] = [pid for pid, _ in await probable_squad(db, team, m.gender, m.match_type, m.match_date)]

    credits = await price_credits(db, [pid for ids in picked.values() for pid in ids])
    for team, ids in picked.items():
        for order, pid in enumerate(ids, start=1):
            db.add(PlayerTeamMatch(match_id=m.id, player_id=pid, team=team, batting_order=order,
                                   is_playing=True, credits=credits.get(pid, 8.0)))
    m.squad_source = source if any(picked.values()) else None
    await db.flush()
    return source


# ── Sync ──────────────────────────────────────────────────────────────────────

async def discover_series(db: AsyncSession, today: Optional[date] = None, max_pages: int = 12) -> List[dict]:
    """Series overlapping [today-2, today+FIXTURE_DAYS_AHEAD], ranked by importance."""
    today = today or date.today()
    lo, hi = today - timedelta(days=2), today + timedelta(days=settings.FIXTURE_DAYS_AHEAD)
    found: List[dict] = []
    for page in range(max_pages):
        body = await cricapi.series_page(db, offset=page * 25)
        data = body.get("data") or []
        stop = False
        for s in data:
            start = _parse_series_date(s.get("startDate", ""), today)
            end = _parse_series_date(s.get("endDate", ""), start or today) or start
            if start and end and end < start:
                end = date(end.year + 1, end.month, end.day)
            if not start:
                continue
            if start < today - timedelta(days=150):
                stop = True
            if start <= hi and (end or start) >= lo and (s.get("matches") or 0) > 0:
                found.append({**s, "_start": start.isoformat(), "_end": (end or start).isoformat(),
                              "_priority": series_priority(s.get("name", ""))})
        if stop or not data:
            break
    found.sort(key=lambda s: (-s["_priority"], s["_start"]))
    return found


async def pinned_series(db: AsyncSession) -> List[str]:
    row = await db.get(ApiCache, PINNED_KEY)
    return list((row.payload or {}).get("ids", [])) if row else []


async def set_pinned_series(db: AsyncSession, ids: List[str]) -> None:
    row = await db.get(ApiCache, PINNED_KEY)
    if row is None:
        db.add(ApiCache(key=PINNED_KEY, payload={"ids": ids}, hits_cost=0, fetched_at=datetime.now(timezone.utc)))
    else:
        row.payload = {"ids": ids}
    await db.commit()


def _status(m: dict) -> str:
    if m.get("matchEnded"):
        return "complete"
    if m.get("matchStarted"):
        return "live"
    return "upcoming"


async def upsert_api_match(db: AsyncSession, am: dict, series_name: str, index: NameIndex) -> Optional[Match]:
    teams = am.get("teams") or []
    if len(teams) != 2 or any(t.lower() in ("tbc", "tba") for t in teams):
        return None
    start = cricapi.parse_api_datetime(am.get("dateTimeGMT"))
    if start is None:
        return None
    gender = cricapi.api_gender(am)
    mt = cricapi.api_match_type({**am, "name": f"{am.get('name', '')} {series_name}"})
    mid = match_id_for(am["id"])
    m = await db.get(Match, mid)
    ta, tb = index.team(teams[0], gender), index.team(teams[1], gender)
    venue_name = index.venue(am.get("venue") or "")
    v = (await db.execute(select(Venue).where(Venue.name == venue_name))).scalars().first() if venue_name else None
    if v is None and venue_name:
        v = Venue(name=venue_name, city=venue_name.split(",")[-1].strip() if "," in venue_name else None)
        db.add(v)
        await db.flush()
    team_info = {}
    for ti in am.get("teamInfo") or []:
        mapped = index.team(ti.get("name", ""), gender)
        team_info[mapped] = {"short": ti.get("shortname"), "img": ti.get("img")}
    new = m is None
    if new:
        m = Match(id=mid, cricapi_id=am["id"], source="cricapi", match_type=mt, gender=gender,
                  team_type="international" if any(k in series_name.lower() for k in (" tour of ", "world cup", "icc")) else "club",
                  team_a=ta, team_b=tb, match_date=start.date(), is_complete=False)
        db.add(m)
    m.venue_id, m.venue_name = (v.id if v else None), venue_name or None
    m.city = v.city if v else None
    m.start_time, m.series_id = start, am.get("series_id") or m.series_id
    m.event_name = series_name
    m.event_stage = (am.get("name") or "").split(",")[1].strip() if am.get("name", "").count(",") >= 2 else None
    m.season = str(start.year)
    m.day_night = start.hour >= 12
    m.team_info = team_info or m.team_info
    m.status = _status(am)
    m.is_complete = m.status == "complete"
    m.status_text = am.get("status")
    if am.get("tossWinner"):
        m.toss_winner = index.team(am["tossWinner"], gender)
        m.toss_decision = "bat" if "bat" in (am.get("tossChoice") or "").lower() else "field"
    await db.flush()
    if new or not m.squad_source:
        await build_squads(db, m, use_official=False)
    return m


async def sync_fixtures(db: AsyncSession, refresh_series: bool = False) -> dict:
    """Pull schedules for tracked series and upsert upcoming/live matches. ~1 hit per series (cached 12h)."""
    if not cricapi.configured():
        return {"status": "skipped", "reason": "CRICKETDATA_API_KEY not set"}
    index = await NameIndex.build(db)
    series = await discover_series(db)
    pinned = await pinned_series(db)
    chosen = [s for s in series if s["id"] in pinned]
    chosen += [s for s in series if s["id"] not in pinned and s["_priority"] >= 2][: max(0, settings.TRACKED_SERIES_MAX - len(chosen))]
    today = date.today()
    lo, hi = today - timedelta(days=1), today + timedelta(days=settings.FIXTURE_DAYS_AHEAD)
    upserted, skipped = 0, 0
    for s in chosen:
        try:
            info = await cricapi.series_info(db, s["id"], max_age=timedelta(0) if refresh_series else timedelta(hours=settings.FIXTURE_SYNC_HOURS))
        except cricapi.QuotaExceeded:
            break
        except cricapi.ApiError as e:
            logger.warning("series_info %s failed: %s", s["id"], e)
            continue
        for am in info.get("matchList") or []:
            start = cricapi.parse_api_datetime(am.get("dateTimeGMT"))
            if not start or not (lo <= start.date() <= hi) or am.get("matchEnded"):
                continue
            m = await upsert_api_match(db, am, s.get("name", ""), index)
            upserted += 1 if m else 0
            skipped += 0 if m else 1
    await db.commit()
    live = await refresh_live_status(db)
    return {"status": "ok", "series_considered": len(series), "series_tracked": [s["name"] for s in chosen],
            "matches_upserted": upserted, "skipped_tbc": skipped, "live_updates": live,
            "api_usage": await cricapi.usage(db)}


async def refresh_live_status(db: AsyncSession, max_age: timedelta = timedelta(minutes=4)) -> int:
    """One currentMatches call updates status / toss / score summary of every tracked match."""
    try:
        rows = await cricapi.current_matches(db, max_age=max_age)
    except (cricapi.QuotaExceeded, cricapi.ApiError) as e:
        logger.info("Live status refresh skipped: %s", e)
        return 0
    by_id = {r["id"]: r for r in rows if r.get("id")}
    tracked = (await db.execute(select(Match).where(Match.cricapi_id.in_(list(by_id))))).scalars().all()
    index = await NameIndex.build(db) if tracked else None
    for m in tracked:
        am = by_id[m.cricapi_id]
        m.status = _status(am)
        m.is_complete = m.status == "complete"
        m.status_text = am.get("status")
        m.live_state = {"score": am.get("score") or [], "status": am.get("status"),
                        "updated_at": datetime.now(timezone.utc).isoformat()}
        if am.get("tossWinner") and not m.toss_winner:
            m.toss_winner = index.team(am["tossWinner"], m.gender)
            m.toss_decision = "bat" if "bat" in (am.get("tossChoice") or "").lower() else "field"
    await db.commit()
    return len(tracked)
