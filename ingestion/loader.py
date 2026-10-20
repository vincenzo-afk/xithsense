"""
Write parsed Cricsheet matches into the database.

Players and venues are upserted by natural key; matches are idempotent (an
existing match id is skipped when `incremental=True`, replaced otherwise).
Optional `people.json` metadata (role, batting/bowling style, nationality)
enriches players — Cricsheet itself carries no styles or roles.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    Delivery, Innings, Match, Player, PlayerMatchPerformance, PlayerTeamMatch, Venue,
)
from ingestion.parser import ValidationError, get_bowler_type, parse_match

logger = logging.getLogger(__name__)


@dataclass
class IngestReport:
    files_seen: int = 0
    ingested: int = 0
    skipped: int = 0
    errors: int = 0
    deliveries: int = 0
    error_samples: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def iter_source_files(source: str) -> tuple[List[Path], Dict[str, dict]]:
    """Resolve a zip / directory into JSON match files plus optional people metadata."""
    src = Path(source)
    people: Dict[str, dict] = {}
    if src.suffix == ".zip":
        extract_dir = src.parent / src.stem
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as zf:
            zf.extractall(extract_dir)
        src = extract_dir
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {source}")
    people_file = src / "people.json"
    if people_file.exists():
        people = json.loads(people_file.read_text(encoding="utf-8"))
    files = sorted(p for p in src.glob("**/*.json") if p.name not in ("people.json", "fixtures.json"))
    return files, people


class Loader:
    def __init__(self, db: AsyncSession, people_meta: Optional[Dict[str, dict]] = None):
        self.db = db
        self.people_meta = people_meta or {}
        self._players: Dict[str, uuid.UUID] = {}     # cricsheet_key -> id
        self._by_reg: Dict[str, uuid.UUID] = {}      # Cricsheet registry id -> id
        self._venues: Dict[str, uuid.UUID] = {}

    async def warm(self) -> None:
        for pid, key, reg in (await self.db.execute(select(Player.id, Player.cricsheet_key, Player.cricsheet_id))).all():
            self._players[key] = pid
            if reg:
                self._by_reg[reg] = pid
        for vid, name in (await self.db.execute(select(Venue.id, Venue.name))).all():
            self._venues[name] = vid

    async def player_id(self, name: str, team: Optional[str] = None, cricsheet_id: Optional[str] = None) -> uuid.UUID:
        """Resolve a player. Registry id is the identity; names can collide between different people."""
        if cricsheet_id and cricsheet_id in self._by_reg:
            return self._by_reg[cricsheet_id]
        if not cricsheet_id and name in self._players:
            return self._players[name]
        key = name if name not in self._players else f"{name} [{cricsheet_id}]"
        meta = self.people_meta.get(name, {})
        pid = uuid.uuid4()
        await self.db.execute(insert(Player).values(
            id=pid, full_name=meta.get("full_name", name), cricsheet_key=key, cricsheet_id=cricsheet_id,
            short_name=name.split(" ")[-1][:50], nationality=meta.get("nationality"),
            batting_style=meta.get("batting_style"), bowling_style=meta.get("bowling_style"),
            bowler_type=get_bowler_type(meta.get("bowling_style")),
            style_source="metadata" if meta.get("bowling_style") else None, primary_role=meta.get("role"),
            current_team=meta.get("team") or team, base_credits=meta.get("credits"), is_active=True,
        ))
        self._players[key] = pid
        if cricsheet_id:
            self._by_reg[cricsheet_id] = pid
        return pid

    async def venue_id(self, name: Optional[str], city: Optional[str], meta: Optional[dict] = None) -> Optional[uuid.UUID]:
        if not name:
            return None
        if name in self._venues:
            return self._venues[name]
        meta = meta or {}
        vid = uuid.uuid4()
        await self.db.execute(insert(Venue).values(
            id=vid, name=name, city=city or meta.get("city"), country=meta.get("country"),
            pitch_type=meta.get("pitch_type"), dew_factor=bool(meta.get("dew_factor")),
            capacity=meta.get("capacity"),
        ))
        self._venues[name] = vid
        return vid

    async def load_match(self, match_id: str, data: dict, incremental: bool = True) -> int:
        existing = await self.db.get(Match, match_id)
        if existing is not None:
            if incremental:
                return -1
            await self._delete_match(match_id)

        pm = parse_match(data)
        rec = pm.match
        mtype = rec["match_type"]
        rec["match_date"] = date.fromisoformat(rec["match_date"])
        rec["venue_id"] = await self.venue_id(rec["venue_name"], rec["city"])
        await self.db.execute(insert(Match).values(id=match_id, **rec))

        # Players + playing XI (name -> id is unambiguous within one match)
        local: Dict[str, uuid.UUID] = {}
        for team, names in pm.players.items():
            for name in names:
                local[name] = await self.player_id(name, team, pm.registry.get(name))
        for name, ln in pm.lines.items():
            if name not in local:
                local[name] = await self.player_id(name, ln.team, pm.registry.get(name))
        seen: set = set()
        for team, names in pm.players.items():
            for order, name in enumerate(names, start=1):
                pid = local[name]
                if pid in seen:          # same person listed twice (name variants share a registry id)
                    continue
                seen.add(pid)
                meta = self.people_meta.get(name, {})
                await self.db.execute(insert(PlayerTeamMatch).values(
                    id=uuid.uuid4(), match_id=match_id, player_id=pid, team=team,
                    batting_order=pm.lines[name].batting_position if name in pm.lines else order,
                    is_keeper=meta.get("role") == "WK", is_playing=True, credits=meta.get("credits"),
                ))

        # Innings + deliveries
        n_del = 0
        for inn_rec, dels in zip(pm.innings, pm.deliveries):
            inn_id = uuid.uuid4()
            await self.db.execute(insert(Innings).values(id=inn_id, match_id=match_id, **inn_rec))
            if dels:
                rows = [{**d, "id": uuid.uuid4(), "innings_id": inn_id, "match_id": match_id,
                         "batter_id": local.get(d["batter"]), "bowler_id": local.get(d["bowler"])} for d in dels]
                await self.db.execute(insert(Delivery), rows)
                n_del += len(rows)

        # Performances
        first_batting = pm.innings[0]["batting_team"] if pm.innings else None
        perf_rows = []
        perf_seen: set = set()
        for name, ln in pm.lines.items():
            pid = local[name]
            if pid in perf_seen:
                continue
            perf_seen.add(pid)
            role = self.people_meta.get(name, {}).get("role")
            opp = rec["team_b"] if ln.team == rec["team_a"] else rec["team_a"]
            perf_rows.append({
                "id": uuid.uuid4(), "match_id": match_id, "player_id": pid,
                "match_date": rec["match_date"], "match_type": mtype, "venue_name": rec["venue_name"],
                "team": ln.team, "opposition": opp,
                "is_chasing": (ln.team != first_batting) if first_batting else None,
                "runs_scored": ln.runs, "balls_faced": ln.balls, "fours": ln.fours, "sixes": ln.sixes,
                "strike_rate": round(ln.runs / ln.balls * 100, 2) if ln.balls else None,
                "did_bat": ln.did_bat, "is_dismissed": ln.dismissed, "dismissal_type": ln.dismissal,
                "batting_position": ln.batting_position,
                "overs_bowled": ln.overs, "balls_bowled": ln.legal_balls_bowled,
                "runs_conceded": ln.runs_conceded, "wickets_taken": ln.wickets, "lbw_bowled": ln.lbw_bowled,
                "maidens": ln.maidens,
                "economy": round(ln.runs_conceded / ln.overs, 2) if ln.legal_balls_bowled else None,
                "dot_balls": ln.dots, "catches": ln.catches,
                "run_outs": ln.run_out_direct + ln.run_out_indirect, "stumpings": ln.stumpings,
                "fantasy_points": ln.fantasy_points(mtype, role), "fantasy_platform": "dream11",
            })
        if perf_rows:
            await self.db.execute(insert(PlayerMatchPerformance), perf_rows)
        return n_del

    async def _delete_match(self, match_id: str) -> None:
        for model in (Delivery, PlayerMatchPerformance, PlayerTeamMatch, Innings):
            await self.db.execute(delete(model).where(model.match_id == match_id))
        await self.db.execute(delete(Match).where(Match.id == match_id))


async def ingest_files(db: AsyncSession, files: Iterable[Path], people: Dict[str, dict],
                       incremental: bool = True, venue_meta: Optional[Dict[str, dict]] = None,
                       progress_every: int = 500) -> IngestReport:
    report = IngestReport()
    loader = Loader(db, people)
    await loader.warm()
    for vname, vm in (venue_meta or {}).items():
        await loader.venue_id(vname, vm.get("city"), vm)
    async def resync():
        loader._players.clear()
        loader._by_reg.clear()
        loader._venues.clear()
        await loader.warm()

    for f in files:
        report.files_seen += 1
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for attempt in range(4):
                try:
                    n = await loader.load_match(f.stem, data, incremental)
                    await db.commit()
                    break
                except OperationalError as e:      # transient (locked / Windows file-scanner I/O) — retry
                    await db.rollback()
                    await resync()
                    if attempt == 3:
                        raise
                    logger.warning("Retrying %s after %s", f.name, str(e).splitlines()[0][:80])
                    await asyncio.sleep(1.5 * (attempt + 1))
            if n < 0:
                report.skipped += 1
                continue
            report.ingested += 1
            report.deliveries += n
            if report.ingested % progress_every == 0:
                logger.info("Progress: %d matches ingested", report.ingested)
        except (ValidationError, KeyError, ValueError, OperationalError, IntegrityError) as e:
            await db.rollback()
            await resync()      # ids cached during the failed transaction are gone
            report.errors += 1
            if len(report.error_samples) < 10:
                report.error_samples.append(f"{f.name}: {e}")
            logger.warning("Skipping %s: %s", f.name, e)
    await db.commit()
    if report.ingested:      # history changed — never serve stale cached frames
        from feature_engineering.builder import drop_frames_cache
        drop_frames_cache()
    return report
