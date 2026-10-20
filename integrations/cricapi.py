"""
CricketData.org (CricAPI v1) client with a persistent cache and a daily quota guard.

The free plan allows 100 "hits" per day; list endpoints cost 1 hit, squads and
scorecards cost 10. Every response is cached in the `api_cache` table, the
provider's own `hitsToday` counter is recorded in `api_usage`, and calls are
refused once fewer than CRICKETDATA_RESERVE hits remain.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import ApiCache, ApiUsage

logger = logging.getLogger(__name__)

HIT_COST = {"match_squad": 10, "match_scorecard": 10, "match_bbb": 10, "match_points": 10}


class QuotaExceeded(RuntimeError):
    pass


class ApiError(RuntimeError):
    pass


def configured() -> bool:
    return bool(settings.CRICKETDATA_API_KEY)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _today():
    return _utcnow().date()


_lock = asyncio.Lock()


async def usage(db: AsyncSession) -> dict:
    row = await db.get(ApiUsage, _today())
    hits = row.hits if row else 0
    limit = row.limit if row else settings.CRICKETDATA_DAILY_LIMIT
    return {"day": str(_today()), "hits": hits, "limit": limit,
            "remaining": max(0, limit - hits), "reserve": settings.CRICKETDATA_RESERVE,
            "configured": configured()}


async def _record_usage(db: AsyncSession, info: dict, cost: int) -> None:
    row = await db.get(ApiUsage, _today())
    if row is None:
        row = ApiUsage(day=_today(), hits=0, limit=settings.CRICKETDATA_DAILY_LIMIT, updated_at=_utcnow())
        db.add(row)
    reported = info.get("hitsToday")
    row.hits = int(reported) if reported is not None else row.hits + cost
    if info.get("hitsLimit"):
        row.limit = int(info["hitsLimit"])
    row.updated_at = _utcnow()


async def call(db: AsyncSession, endpoint: str, max_age: Optional[timedelta] = None,
               allow_stale: bool = True, **params) -> dict:
    """GET /v1/{endpoint}. Returns cached data younger than `max_age`; otherwise fetches
    (quota permitting). On quota exhaustion or network errors returns stale cache if allowed."""
    if not configured():
        raise ApiError("CRICKETDATA_API_KEY is not configured")
    key = endpoint + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    cached = await db.get(ApiCache, key)
    if cached and max_age is not None and _utcnow() - cached.fetched_at < max_age:
        return cached.payload

    cost = HIT_COST.get(endpoint, 1)
    async with _lock:
        u = await usage(db)
        if u["remaining"] - cost < settings.CRICKETDATA_RESERVE:
            if cached and allow_stale:
                return cached.payload
            raise QuotaExceeded(f"Daily API quota nearly used ({u['hits']}/{u['limit']}); '{endpoint}' needs {cost}")
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                r = await client.get(f"{settings.CRICKETDATA_BASE_URL}/{endpoint}",
                                     params={"apikey": settings.CRICKETDATA_API_KEY, **params})
            body = r.json()
        except (httpx.HTTPError, ValueError) as e:
            if cached and allow_stale:
                logger.warning("CricAPI %s failed (%s) — serving cache", endpoint, e)
                return cached.payload
            raise ApiError(f"CricAPI request failed: {e}") from e

    body.pop("apikey", None)
    info = body.get("info") or {}
    await _record_usage(db, info, cost)
    if body.get("status") != "success":
        await db.commit()
        reason = body.get("reason") or body.get("status") or "unknown error"
        if cached and allow_stale:
            logger.warning("CricAPI %s returned %s — serving cache", endpoint, reason)
            return cached.payload
        raise ApiError(f"CricAPI {endpoint}: {reason}")
    if cached:
        cached.payload, cached.fetched_at, cached.hits_cost = body, _utcnow(), cost
    else:
        db.add(ApiCache(key=key, payload=body, hits_cost=cost, fetched_at=_utcnow()))
    await db.commit()
    return body


async def cached_only(db: AsyncSession, endpoint: str, **params) -> Optional[dict]:
    key = endpoint + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    row = await db.get(ApiCache, key)
    return row.payload if row else None


# ── Typed helpers ─────────────────────────────────────────────────────────────

async def current_matches(db: AsyncSession, max_age: timedelta = timedelta(minutes=4), pages: int = 3) -> list[dict]:
    rows: list[dict] = []
    for page in range(pages):
        body = await call(db, "currentMatches", max_age=max_age, offset=page * 25)
        data = body.get("data") or []
        rows += data
        total = (body.get("info") or {}).get("totalRows", 0)
        if (page + 1) * 25 >= total or not data:
            break
    return rows


async def series_page(db: AsyncSession, offset: int, max_age: timedelta = timedelta(hours=24)) -> dict:
    return await call(db, "series", max_age=max_age, offset=offset)


async def series_info(db: AsyncSession, series_id: str, max_age: timedelta = timedelta(hours=12)) -> dict:
    return (await call(db, "series_info", max_age=max_age, id=series_id)).get("data") or {}


async def match_info(db: AsyncSession, match_id: str, max_age: timedelta = timedelta(minutes=30)) -> dict:
    return (await call(db, "match_info", max_age=max_age, id=match_id)).get("data") or {}


async def match_squad(db: AsyncSession, match_id: str, max_age: timedelta = timedelta(hours=6)) -> list[dict]:
    return (await call(db, "match_squad", max_age=max_age, id=match_id)).get("data") or []


async def match_scorecard(db: AsyncSession, match_id: str, max_age: timedelta = timedelta(minutes=45)) -> dict:
    return (await call(db, "match_scorecard", max_age=max_age, id=match_id)).get("data") or {}


def parse_api_datetime(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", ""))
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
    except ValueError:
        return None


def api_match_type(m: dict) -> str:
    """CricAPI matchType (t20/odi/test) → our match_type (T20/ODI/Test; IPL & co. from series name)."""
    name = (m.get("name") or "").lower()
    leagues = {"indian premier league": "IPL", "big bash": "BBL", "pakistan super league": "PSL",
               "caribbean premier league": "CPL", "women's premier league": "WPL", "womens premier league": "WPL"}
    for k, v in leagues.items():
        if k in name:
            return v
    mt = (m.get("matchType") or "").lower()
    return {"t20": "T20", "odi": "ODI", "test": "Test", "t10": "T20"}.get(mt, "T20")


def api_gender(m: dict) -> str:
    teams = " ".join(m.get("teams") or []) + " " + (m.get("name") or "")
    return "female" if " women" in teams.lower() or "women's" in teams.lower() else "male"
