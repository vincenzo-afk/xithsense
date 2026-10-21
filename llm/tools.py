"""
Tools the assistant can call. Every tool reads from the real engine / database or the web
and returns a compact JSON string the model must ground its answer in.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from sqlalchemy import func, select

from backend.models import Match, Player, PlayerMatchPerformance, RollingFeature, VenueStat
from backend.services.engine import MatchScores, PlayerScore, score_match
from integrations import web
from optimizer.captain_engine import recommend
from optimizer.lp_optimizer import solve_team
from optimizer.scoring import score_for_mode

MAX_CHARS = 7000


@dataclass
class ToolContext:
    db: Any
    user: Any
    match: Optional[Match]
    premium: bool = True
    sources: List[dict] = field(default_factory=list)       # {title, url}
    related: List[str] = field(default_factory=list)        # player ids surfaced
    used: List[dict] = field(default_factory=list)          # {name, summary}


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    run: Callable[..., Awaitable[Any]]
    premium_only: bool = False


def _j(obj: Any) -> str:
    s = json.dumps(obj, default=str, ensure_ascii=False)
    return s if len(s) <= MAX_CHARS else s[:MAX_CHARS] + "…(truncated)"


def _surname(name: str) -> str:
    parts = re.sub(r"[^A-Za-z\s'-]", "", name or "").split()
    return parts[-1].lower() if parts else ""


def _player_row(p: PlayerScore, detail: bool = False) -> dict:
    row = {"player_id": p.player_id, "name": p.full_name, "role": p.role, "team": p.team, "credits": p.credits,
           "projected_fp": p.predicted_fp, "ceiling": p.fp_ceiling, "floor": p.fp_floor, "confidence": p.confidence,
           "ownership_pct": p.ownership, "differential": p.is_differential, "form_last5": p.fp_avg_5}
    if detail:
        from llm.explainer import build_factors
        row["factors"] = [f"{f['factor']}: {f['value']} — {f['detail']}" for f in build_factors(p, None, None)]
        row["analyst_rules"] = [r.get("description") for r in p.rules_fired]
        row["venue_avg_fp"] = p.features.get("venue_fp_avg")
        row["sr_vs_pace"] = p.features.get("sr_vs_pace")
        row["sr_vs_spin"] = p.features.get("sr_vs_spin")
    return row


async def _resolve_match(ctx: ToolContext, match_id: Optional[str]) -> Optional[Match]:
    if match_id:
        m = await ctx.db.get(Match, match_id)
        if m:
            return m
    return ctx.match


async def _scores(ctx: ToolContext, match_id: Optional[str]) -> tuple[Optional[Match], Optional[MatchScores], Optional[str]]:
    m = await _resolve_match(ctx, match_id)
    if m is None:
        return None, None, "No match selected. Call list_upcoming_matches and pass a match_id."
    try:
        return m, await score_match(ctx.db, m.id), None
    except ValueError:
        return m, None, ("Squad incomplete for this fixture — one side has no recent match data (official squad "
                         "not announced yet), so no projections are available.")


# ── tool implementations ──────────────────────────────────────────────────────

async def list_upcoming_matches(ctx: ToolContext, limit: int = 12) -> str:
    rows = (await ctx.db.execute(select(Match).where(Match.status.in_(("live", "upcoming")))
                                 .order_by((Match.status != "live"), Match.match_date, Match.start_time).limit(limit))).scalars().all()
    return _j([{"match_id": m.id, "fixture": f"{m.team_a} vs {m.team_b}", "format": m.match_type, "gender": m.gender,
                "series": m.event_name, "venue": m.venue_name, "start_utc": m.start_time, "status": m.status,
                "toss": f"{m.toss_winner} chose to {m.toss_decision}" if m.toss_winner else None,
                "squad_source": m.squad_source} for m in rows])


async def get_match_context(ctx: ToolContext, match_id: Optional[str] = None) -> str:
    m = await _resolve_match(ctx, match_id)
    if m is None:
        return "No match selected."
    vs = None
    if m.venue_id:
        vs = (await ctx.db.execute(select(VenueStat).where(VenueStat.venue_id == m.venue_id))).scalars().first()
    h2h = (await ctx.db.execute(select(Match).where(
        Match.status == "complete", ((Match.team_a == m.team_a) & (Match.team_b == m.team_b)) |
        ((Match.team_a == m.team_b) & (Match.team_b == m.team_a))).order_by(Match.match_date.desc()).limit(5))).scalars().all()
    return _j({
        "match_id": m.id, "fixture": f"{m.team_a} vs {m.team_b}", "format": m.match_type, "gender": m.gender,
        "series": m.event_name, "stage": m.event_stage, "venue": m.venue_name, "city": m.city, "start_utc": m.start_time,
        "status": m.status, "status_text": m.status_text, "toss_winner": m.toss_winner, "toss_decision": m.toss_decision,
        "squad_source": m.squad_source, "live_score": (m.live_state or {}).get("score"),
        "venue_stats": {"avg_first_innings": vs.avg_first_innings, "chasing_win_pct": vs.chasing_win_pct,
                        "spin_wicket_pct": vs.spin_wicket_pct, "pace_wicket_pct": vs.pace_wicket_pct,
                        "matches": vs.total_matches} if vs else None,
        "head_to_head_last5": [{"date": str(x.match_date), "winner": x.match_winner, "venue": x.venue_name} for x in h2h],
    })


async def predict_players(ctx: ToolContext, match_id: Optional[str] = None, names: Optional[List[str]] = None,
                          top_n: int = 12) -> str:
    """Model projections for players in a fixture; filter by names for detailed factors."""
    m, ms, err = await _scores(ctx, match_id)
    if err:
        return err
    ctx.used.append({"name": "predict_players", "summary": f"Ran projections for {m.team_a} vs {m.team_b}"})
    if names:
        wanted = {_surname(n) for n in names if n}
        hits = [p for p in ms.players if _surname(p.full_name) in wanted or p.full_name.lower() in {n.lower() for n in names}]
        missing = [n for n in names if _surname(n) not in {_surname(p.full_name) for p in hits}]
        ctx.related += [p.player_id for p in hits]
        rank = {p.player_id: i + 1 for i, p in enumerate(ms.players)}
        out = {"match": f"{m.team_a} vs {m.team_b}", "phase": ms.phase,
               "players": [{**_player_row(p, detail=True), "rank_in_match": rank[p.player_id], "of": len(ms.players)} for p in hits]}
        if missing:
            out["not_in_this_match"] = missing
        return _j(out)
    top = ms.players[:top_n]
    ctx.related += [p.player_id for p in top[:6]]
    return _j({"match": f"{m.team_a} vs {m.team_b}", "phase": ms.phase, "model_version": ms.model_version,
               "ensemble_weights": ms.weights, "top_players": [_player_row(p) for p in top]})


async def build_team(ctx: ToolContext, match_id: Optional[str] = None, mode: str = "safe") -> str:
    m, ms, err = await _scores(ctx, match_id)
    if err:
        return err
    mode = mode if mode in ("safe", "grand_league", "aggressive", "small_league") else "safe"
    opts = [p.to_opt() for p in ms.players]
    score_for_mode(opts, mode)
    res = solve_team(opts, min_differentials=1 if mode == "grand_league" else 0)
    if res is None:
        return "The optimizer found no valid Dream11 XI for this squad."
    picks = recommend(res.players, mode)
    ctx.used.append({"name": "build_team", "summary": f"Built a {mode.replace('_', ' ')} XI"})
    ctx.related += [p.player_id for p in res.players]
    by = ms.by_id
    return _j({"mode": mode, "credits": round(sum(p.credits for p in res.players), 1),
               "projected_total_incl_cvc": round(sum(p.predicted_fp for p in res.players) + picks[0].player.predicted_fp
                                                 + 0.5 * picks[1].player.predicted_fp, 1),
               "captain": picks[0].player.full_name, "vice_captain": picks[1].player.full_name,
               "xi": [{"name": p.full_name, "role": p.role, "team": p.team, "credits": p.credits,
                       "projected_fp": p.predicted_fp, "confidence": by[p.player_id].confidence} for p in
                      sorted(res.players, key=lambda p: ("WK", "BAT", "AR", "BOWL").index(p.role))]})


async def captain_options(ctx: ToolContext, match_id: Optional[str] = None, mode: str = "safe") -> str:
    m, ms, err = await _scores(ctx, match_id)
    if err:
        return err
    opts = [p.to_opt() for p in ms.players]
    score_for_mode(opts, mode if mode in ("safe", "grand_league", "aggressive", "small_league") else "safe")
    res = solve_team(opts)
    if res is None:
        return "No valid team to pick a captain from."
    picks = recommend(res.players, mode)
    ctx.used.append({"name": "captain_options", "summary": "Ranked captaincy options"})
    ctx.related += [c.player.player_id for c in picks]
    return _j([{"type": c.type, "name": c.player.full_name, "role": c.player.role, "projected_fp": c.player.predicted_fp,
                "ceiling": c.player.ceiling, "confidence": c.player.confidence, "ownership_pct": c.player.ownership,
                "reasoning": c.reasoning} for c in picks])


async def differentials(ctx: ToolContext, match_id: Optional[str] = None) -> str:
    m, ms, err = await _scores(ctx, match_id)
    if err:
        return err
    picks = sorted([p for p in ms.players if p.ownership < 25], key=lambda p: -(p.fp_ceiling - p.ownership * 0.5))[:5]
    ctx.used.append({"name": "differentials", "summary": "Found low-ownership picks"})
    ctx.related += [p.player_id for p in picks]
    return _j([_player_row(p) for p in picks])


async def player_profile(ctx: ToolContext, name: str) -> str:
    q = select(Player).where(func.lower(Player.full_name).contains(name.lower().strip()))
    players = (await ctx.db.execute(q.limit(5))).scalars().all()
    if not players:
        sur = _surname(name)
        players = (await ctx.db.execute(select(Player).where(func.lower(Player.full_name).like(f"% {sur}")).limit(5))).scalars().all()
    if not players:
        return f"No player matching {name!r} in the database."
    out = []
    P = PlayerMatchPerformance
    for p in players[:3]:
        c = (await ctx.db.execute(select(func.count(), func.sum(P.runs_scored), func.sum(P.wickets_taken),
                                         func.avg(P.fantasy_points), func.max(P.match_date)).where(P.player_id == p.id))).one()
        recent = (await ctx.db.execute(select(P.match_date, P.opposition, P.runs_scored, P.balls_faced, P.wickets_taken,
                                              P.fantasy_points).where(P.player_id == p.id)
                                       .order_by(P.match_date.desc()).limit(5))).all()
        rf = (await ctx.db.execute(select(RollingFeature).where(RollingFeature.player_id == p.id, RollingFeature.window_matches == 10)
                                   .order_by(RollingFeature.as_of_date.desc()).limit(1))).scalars().first()
        ctx.related.append(str(p.id))
        out.append({"player_id": str(p.id), "name": p.full_name, "role": p.primary_role, "team": p.current_team,
                    "batting": p.batting_style, "bowling": p.bowling_style or p.bowler_type,
                    "career": {"matches": c[0], "runs": c[1], "wickets": c[2], "avg_fp": round(c[3] or 0, 1), "last_played": c[4]},
                    "last10": {"fp_avg": rf.fp_avg, "ceiling": rf.fp_ceiling, "floor": rf.fp_floor,
                               "consistency": rf.fp_consistency} if rf else None,
                    "recent": [{"date": str(r[0]), "vs": r[1], "runs": r[2], "balls": r[3], "wkts": r[4], "fp": r[5]} for r in recent]})
    ctx.used.append({"name": "player_profile", "summary": f"Looked up {players[0].full_name}"})
    return _j(out)


async def web_search(ctx: ToolContext, query: str, max_results: int = 5) -> str:
    results = await web.search(ctx.db, query, max_results=max(1, min(int(max_results or 5), 8)))
    ctx.used.append({"name": "web_search", "summary": f"Searched the web: {query[:60]}"})
    for r in results:
        ctx.sources.append({"title": r.get("title") or r["url"], "url": r["url"]})
    if not results:
        return "No web results (search disabled or provider unavailable)."
    return _j(results)


async def fetch_page(ctx: ToolContext, url: str) -> str:
    page = await web.fetch(ctx.db, url)
    if not page:
        return "Could not fetch that page (blocked, not HTML, or unavailable)."
    ctx.used.append({"name": "fetch_page", "summary": f"Read {page.get('title') or url}"[:80]})
    ctx.sources.append({"title": page.get("title") or url, "url": url})
    return _j(page)


TOOLS: List[Tool] = [
    Tool("list_upcoming_matches", "List upcoming and live fixtures with their match_id, format, venue, toss and squad status.",
         {"type": "object", "properties": {"limit": {"type": "integer", "default": 12}}}, list_upcoming_matches),
    Tool("get_match_context", "Venue stats, toss, status, live score and head-to-head for a fixture (defaults to the selected match).",
         {"type": "object", "properties": {"match_id": {"type": "string"}}}, get_match_context),
    Tool("predict_players", "Model projections (fantasy points, ceiling/floor, confidence, ownership, factors) for players in a "
                            "fixture. Pass names to get full detail for specific players; omit for the top-ranked list.",
         {"type": "object", "properties": {"match_id": {"type": "string"}, "names": {"type": "array", "items": {"type": "string"}},
                                           "top_n": {"type": "integer", "default": 12}}}, predict_players),
    Tool("build_team", "Build an optimal Dream11 XI with captain & vice-captain. mode: safe | grand_league | aggressive | small_league.",
         {"type": "object", "properties": {"match_id": {"type": "string"}, "mode": {"type": "string"}}}, build_team, premium_only=True),
    Tool("captain_options", "Best / safe / risk captaincy picks with reasoning.",
         {"type": "object", "properties": {"match_id": {"type": "string"}, "mode": {"type": "string"}}}, captain_options),
    Tool("differentials", "Low-ownership, high-ceiling picks for grand leagues.",
         {"type": "object", "properties": {"match_id": {"type": "string"}}}, differentials, premium_only=True),
    Tool("player_profile", "Career record, recent form and style for any player in the database (by name).",
         {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, player_profile),
    Tool("web_search", "Search the web for current cricket news: injuries, playing XI announcements, pitch reports, "
                       "weather, team changes. Returns titles, URLs and snippets.",
         {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 5}},
          "required": ["query"]}, web_search),
    Tool("fetch_page", "Read the text of a public web page (use after web_search when a snippet isn't enough).",
         {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, fetch_page),
]
TOOL_INDEX: Dict[str, Tool] = {t.name: t for t in TOOLS}


def specs(premium: bool = True, web_enabled: bool = True) -> List[dict]:
    out = []
    for t in TOOLS:
        if t.premium_only and not premium:
            continue
        if t.name in ("web_search", "fetch_page") and not web_enabled:
            continue
        out.append({"name": t.name, "description": t.description, "parameters": t.parameters})
    return out


async def execute(name: str, args: dict, ctx: ToolContext) -> str:
    tool = TOOL_INDEX.get(name)
    if tool is None:
        return f"Unknown tool {name!r}."
    if tool.premium_only and not ctx.premium:
        return "This tool needs a Premium subscription."
    try:
        return str(await tool.run(ctx, **{k: v for k, v in (args or {}).items() if not k.startswith("_")}))
    except TypeError as e:
        return f"Bad arguments for {name}: {e}"
    except Exception as e:  # never let a tool crash the turn
        return f"{name} failed: {type(e).__name__}: {e}"
