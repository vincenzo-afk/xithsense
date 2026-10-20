"""
Real live-match feed (WEBSOCKET_SPEC) backed by CricketData.

While at least one client watches a live match, the feed polls the provider:
  * score summary via `currentMatches` every LIVE_POLL_SECONDS (1 hit, shared by
    every live match through the response cache);
  * the full scorecard every LIVE_SCORECARD_MINUTES (10 hits) — used to compute
    live fantasy points per player with the same scoring code as ingestion.
Polling stops when nobody is watching, and never exceeds the daily quota.

Events: connection_established · match_update · player_update · wicket_fell ·
toss_update · match_ended · feed_status
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy import select

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import Match, Player, PlayerTeamMatch
from ingestion.fantasy_points import compute_batting_fp, compute_bowling_fp, compute_fielding_fp
from integrations import cricapi

logger = logging.getLogger(__name__)

MAX_BALLS = {"T20": 120, "IT20": 120, "IPL": 120, "BBL": 120, "PSL": 120, "CPL": 120, "WPL": 120, "ODI": 300, "ODM": 300}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def overs_to_balls(o) -> int:
    o = float(o or 0)
    whole = int(o)
    return whole * 6 + int(round((o - whole) * 10))


def win_probability(runs: int, wickets: int, balls: int, max_balls: int, target: Optional[int], par: float) -> float:
    """P(batting side wins) from remaining resources (balls, wickets, death acceleration, momentum)."""
    left = max(0, max_balls - balls)
    wk_left = 10 - wickets
    death = min(left, max_balls // 4)
    base = (8.2 if max_balls == 120 else 5.6) + (2.6 if max_balls == 120 else 2.0) * (death / left) if left else 0.0
    crr = runs / balls * 6 if balls else base
    rate = 0.65 * base + 0.35 * crr if balls >= 18 else base
    expected = left / 6 * rate * min(1.0, 0.45 + 0.07 * wk_left)
    if target:
        need = target - runs
        if need <= 0:
            return 1.0
        if left == 0 or wk_left == 0:
            return 0.0
        return 1 / (1 + math.exp(-(expected - need) / (4 + math.sqrt(left) * 1.5)))
    return 1 / (1 + math.exp(-(runs + expected - par) / (14 + math.sqrt(left) * 1.4)))


def parse_score(m: Match, score: List[dict]) -> dict:
    """Provider score list → innings summaries + current state + win probability."""
    teams = [m.team_a, m.team_b]
    innings = []
    for i, s in enumerate(score or []):
        label = (s.get("inning") or "").lower()
        hits = [t for t in teams if t.lower().split(" women")[0] in label]
        if len(hits) == 1:
            bat = hits[0]
        elif innings:                      # provider sometimes lists both names — alternate sides
            bat = teams[1] if innings[-1]["team"] == teams[0] else teams[0]
        else:
            bat = teams[0]
        innings.append({"number": i + 1, "team": bat, "runs": int(s.get("r") or 0), "wickets": int(s.get("w") or 0),
                        "overs": str(s.get("o") or 0), "balls": overs_to_balls(s.get("o"))})
    state: dict = {"innings_list": innings, "status_text": m.status_text}
    if not innings:
        return state
    cur = innings[-1]
    max_balls = MAX_BALLS.get(m.match_type)
    bowl = teams[1] if cur["team"] == teams[0] else teams[0]
    crr = cur["runs"] / (cur["balls"] / 6) if cur["balls"] else 0.0
    target = innings[0]["runs"] + 1 if (max_balls and len(innings) >= 2) else None
    state["innings"] = {"number": cur["number"], "batting_team": cur["team"], "bowling_team": bowl,
                        "runs": cur["runs"], "wickets": cur["wickets"], "overs": cur["overs"],
                        "current_run_rate": round(crr, 2), "target": target}
    if len(innings) >= 2:
        state["first_innings"] = {"team": innings[0]["team"], "runs": innings[0]["runs"],
                                  "wickets": innings[0]["wickets"], "overs": innings[0]["overs"]}
    if max_balls:
        par = 170 if max_balls == 120 else 280
        left = max_balls - cur["balls"]
        if target:
            need = target - cur["runs"]
            state["required"] = {"runs": max(0, need), "balls": left,
                                 "run_rate": round(need / (left / 6), 2) if left > 0 else None}
        else:
            state["innings"]["projected_total"] = int(cur["runs"] + left / 6 * max(crr, 6.5 if max_balls == 120 else 4.8)) if cur["balls"] else None
        if m.status != "complete":
            p = win_probability(cur["runs"], cur["wickets"], cur["balls"], max_balls, target, par)
            state["win_probability"] = {cur["team"]: round(p, 3), bowl: round(1 - p, 3)}
    return state


def _key(name: str) -> tuple:
    parts = re.sub(r"[^A-Za-z\s'-]", "", name or "").split()
    return (parts[-1].lower() if parts else "", parts[0][0].lower() if parts else "")


def scorecard_fantasy_points(card: dict, roster: Dict[str, dict]) -> Dict[str, dict]:
    """Provider scorecard → {player_id: {fp, batting, bowling, fielding}} using the canonical scoring.
    `roster` maps provider player ids / names onto our players: {"id:<api>"|"name:<k>": {player_id, role, team}}."""
    lines: Dict[str, dict] = {}

    def resolve(p: dict) -> Optional[dict]:
        if not p:
            return None
        hit = roster.get(f"id:{p.get('id')}")
        if hit:
            return hit
        sur, ini = _key(p.get("name", ""))
        return roster.get(f"name:{sur}:{ini}") or roster.get(f"name:{sur}:")

    def line(r: dict) -> dict:
        return lines.setdefault(r["player_id"], {"player_id": r["player_id"], "full_name": r["full_name"], "team": r["team"],
                                                 "role": r["role"], "bat": None, "bowl": None,
                                                 "field": {"catches": 0, "stumpings": 0, "run_outs": 0}})

    for inn in card.get("scorecard") or []:
        for b in inn.get("batting") or []:
            r = resolve(b.get("batsman"))
            if not r:
                continue
            txt = (b.get("dismissal-text") or "").lower()
            dismissed = bool(b.get("dismissal")) and "not out" not in txt and "retired hurt" not in txt
            line(r)["bat"] = {"runs": int(b.get("r") or 0), "balls": int(b.get("b") or 0), "fours": int(b.get("4s") or 0),
                              "sixes": int(b.get("6s") or 0), "dismissed": dismissed, "how": b.get("dismissal-text")}
        for bw in inn.get("bowling") or []:
            r = resolve(bw.get("bowler"))
            if r:
                line(r)["bowl"] = {"overs": float(bw.get("o") or 0), "maidens": int(bw.get("m") or 0),
                                   "runs": int(bw.get("r") or 0), "wickets": int(bw.get("w") or 0), "lbw_bowled": 0}
        for c in inn.get("catching") or []:
            r = resolve(c.get("catcher"))
            if not r:
                continue
            f = line(r)["field"]
            f["catches"] += int(c.get("catch") or 0) + int(c.get("cb") or 0)
            f["stumpings"] += int(c.get("stumped") or 0)
            f["run_outs"] += int(c.get("runout") or 0)
            lb = int(c.get("lbw") or 0) + int(c.get("bowled") or 0)
            if lb and line(r)["bowl"]:
                line(r)["bowl"]["lbw_bowled"] += lb
    for ln in lines.values():
        fp = 0.0
        if ln["bat"]:
            b = ln["bat"]
            fp += compute_batting_fp(b["runs"], b["balls"], b["fours"], b["sixes"], b["dismissed"], role=ln["role"])
        if ln["bowl"]:
            b = ln["bowl"]
            fp += compute_bowling_fp(b["wickets"], b["runs"], b["overs"], b["maidens"], lbw_bowled=b["lbw_bowled"])
        f = ln["field"]
        fp += compute_fielding_fp(f["catches"], f["stumpings"], f["run_outs"], 0)   # run-outs scored as direct
        ln["fp"] = round(fp, 1)
    return lines


class LiveMatch:
    def __init__(self, match_id: str):
        self.match_id = match_id
        self.subscribers: Set[asyncio.Queue] = set()
        self.state: dict = {"status": "connecting"}
        self.players: Dict[str, dict] = {}       # player_id -> row for the leaderboard
        self.predicted: Dict[str, float] = {}
        self.roster: Dict[str, dict] = {}
        self.last_scorecard: Optional[datetime] = None
        self.last_score_sig = None
        self.task: Optional[asyncio.Task] = None
        self.finished = False
        self.feed_note: Optional[str] = None

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    def _emit(self, msg: dict) -> None:
        msg.setdefault("match_id", self.match_id)
        msg.setdefault("timestamp", _now())
        for q in list(self.subscribers):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass

    def snapshot(self) -> dict:
        return {"event": "match_update", **self.state, "players": self.leaderboard(), "feed_note": self.feed_note}

    def leaderboard(self) -> List[dict]:
        rows = []
        for pid, r in self.players.items():
            rows.append({**r, "predicted_fp": self.predicted.get(pid)})
        return sorted(rows, key=lambda r: -(r.get("live_fantasy_points") or 0))

    async def _load(self, db) -> Optional[Match]:
        m = await db.get(Match, self.match_id)
        if m is None:
            return None
        rows = (await db.execute(select(PlayerTeamMatch, Player).join(Player, Player.id == PlayerTeamMatch.player_id)
                                 .where(PlayerTeamMatch.match_id == self.match_id))).all()
        for ptm, p in rows:
            pid = str(p.id)
            entry = {"player_id": pid, "full_name": p.full_name, "role": p.primary_role or "BAT", "team": ptm.team}
            if p.cricapi_id:
                self.roster[f"id:{p.cricapi_id}"] = entry
            sur, ini = _key(p.full_name)
            self.roster.setdefault(f"name:{sur}:{ini}", entry)
            self.roster.setdefault(f"name:{sur}:", entry)
            self.players.setdefault(pid, {**entry, "live_fantasy_points": 0.0})
        if not self.predicted:
            try:
                from backend.services.engine import score_match
                ms = await score_match(db, self.match_id)
                self.predicted = {p.player_id: p.predicted_fp for p in ms.players}
            except Exception as e:
                logger.info("No projections for live match %s: %s", self.match_id, e)
        return m

    async def run(self) -> None:
        try:
            while True:
                if not self.subscribers:
                    await asyncio.sleep(5)
                    if not self.subscribers:
                        break          # nobody watching — stop polling
                    continue
                async with AsyncSessionLocal() as db:
                    m = await self._load(db)
                    if m is None:
                        break
                    if m.cricapi_id and cricapi.configured():
                        from integrations.fixtures import refresh_live_status
                        await refresh_live_status(db, max_age=timedelta(seconds=settings.LIVE_POLL_SECONDS))
                        await db.refresh(m)
                    await self._update_score(m)
                    await self._maybe_scorecard(db, m)
                    usage = await cricapi.usage(db) if cricapi.configured() else None
                    self._emit({"event": "feed_status", "api_usage": usage, "note": self.feed_note,
                                "next_poll_seconds": settings.LIVE_POLL_SECONDS})
                    if m.status == "complete":
                        self._end(m)
                        break
                await asyncio.sleep(settings.LIVE_POLL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Live feed crashed for %s", self.match_id)
        finally:
            self.finished = True

    async def _update_score(self, m: Match) -> None:
        live = m.live_state or {}
        sig = (str(live.get("score")), m.status_text, m.toss_winner)
        st = parse_score(m, live.get("score") or [])
        prev_wk = (self.state.get("innings") or {}).get("wickets")
        self.state = {"status": "complete" if m.status == "complete" else "in_progress",
                      "teams": [m.team_a, m.team_b], "toss_winner": m.toss_winner, "toss_decision": m.toss_decision,
                      "score_updated_at": live.get("updated_at"), **st}
        if sig != self.last_score_sig:
            self.last_score_sig = sig
            self._emit({"event": "match_update", **self.state})
            cur = self.state.get("innings") or {}
            if prev_wk is not None and cur.get("wickets", 0) > prev_wk:
                self._emit({"event": "wicket_fell", "score_at_fall": f"{cur['runs']}/{cur['wickets']}",
                            "over": cur.get("overs"), "team": cur.get("batting_team")})

    async def _maybe_scorecard(self, db, m: Match) -> None:
        if not (m.cricapi_id and cricapi.configured()):
            self.feed_note = "Live fantasy points need the CricketData scorecard (API key not configured)."
            return
        due = self.last_scorecard is None or datetime.now(timezone.utc) - self.last_scorecard >= timedelta(minutes=settings.LIVE_SCORECARD_MINUTES)
        if not due:
            return
        try:
            card = await cricapi.match_scorecard(db, m.cricapi_id, max_age=timedelta(minutes=settings.LIVE_SCORECARD_MINUTES))
        except cricapi.QuotaExceeded:
            self.feed_note = "Daily API quota reached — score keeps updating, fantasy points paused."
            return
        except cricapi.ApiError as e:
            self.feed_note = f"Scorecard unavailable: {e}"
            return
        self.last_scorecard = datetime.now(timezone.utc)
        self.feed_note = None
        lines = scorecard_fantasy_points(card, self.roster)
        for pid, ln in lines.items():
            prev = self.players.get(pid, {}).get("live_fantasy_points", 0.0)
            row = {"player_id": pid, "full_name": ln["full_name"], "team": ln["team"], "role": ln["role"],
                   "live_fantasy_points": ln["fp"], "batting": ln["bat"], "bowling": ln["bowl"], "fielding": ln["field"]}
            self.players[pid] = row
            if abs(ln["fp"] - prev) >= 1:
                self._emit({"event": "player_update", **row,
                            "prediction_accuracy": {"predicted_fp": self.predicted.get(pid), "current_fp": ln["fp"]}})
        self._emit({"event": "scorecard_update", "players": self.leaderboard(), "fetched_at": _now()})

    def _end(self, m: Match) -> None:
        board = self.leaderboard()
        top = board[0] if board and board[0].get("live_fantasy_points") else None
        pred_top = max(self.predicted.items(), key=lambda kv: kv[1])[0] if self.predicted else None
        names = {r["player_id"]: r["full_name"] for r in board}
        self._emit({"event": "match_ended", "result": m.status_text,
                    "top_fantasy_scorer": ({"player_id": top["player_id"], "full_name": top["full_name"],
                                            "fantasy_points": top["live_fantasy_points"]} if top else None),
                    "captain_accuracy": ({"predicted_captain": names.get(pred_top, pred_top),
                                          "actual_top_scorer": top["full_name"], "correct": pred_top == top["player_id"]}
                                         if top and pred_top else None),
                    "connection_closing_in_seconds": 30})


class LiveManager:
    def __init__(self):
        self.matches: Dict[str, LiveMatch] = {}
        self.lock = asyncio.Lock()

    async def get(self, match_id: str) -> Optional[LiveMatch]:
        async with self.lock:
            async with AsyncSessionLocal() as db:
                m = await db.get(Match, match_id)
                if m is None or m.status not in ("live", "complete"):
                    return None
            lm = self.matches.get(match_id)
            if lm is None or lm.finished:
                lm = LiveMatch(match_id)
                self.matches[match_id] = lm
                async with AsyncSessionLocal() as db:
                    m = await lm._load(db)
                    await lm._update_score(m)
                lm.task = asyncio.create_task(lm.run())
            return lm

    async def shutdown(self) -> None:
        for lm in self.matches.values():
            if lm.task:
                lm.task.cancel()


live_manager = LiveManager()
