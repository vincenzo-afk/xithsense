"""
Admin router (ADMIN_PANEL_SPEC): metrics, jobs (ingest / features / retrain / backtest),
models, rules CRUD, users, match control (toss / XI / status), audit log.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend import jobs
from backend.database import get_db
from backend.dependencies import client_info, require_admin
from backend.models import (
    AdminAction, BacktestRun, Delivery, HumanRule, Match, ModelVersion, Notification, Player,
    PlayerTeamMatch, Prediction, Subscription, User,
)
from backend.schemas import (
    AdminMetricsResponse, BacktestRequest, IngestRequest, MatchAdminUpdate, RetrainRequest, RoleUpdateRequest,
    RuleCreateRequest, RuleOut, RuleUpdateRequest,
)
from human_rules.loader import all_rules_including_inactive, set_db_rules

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


async def audit(db: AsyncSession, request: Request, admin: User, action: str, target_type: str | None = None,
                target_id: str | None = None, payload: dict | None = None) -> None:
    ip, ua = client_info(request)
    db.add(AdminAction(admin_id=admin.id, action_type=action, target_type=target_type, target_id=target_id,
                       payload=payload, ip_address=ip, user_agent=ua))


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics", response_model=AdminMetricsResponse)
async def get_metrics(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    count = lambda m, *c: select(func.count()).select_from(m).where(*c)  # noqa: E731
    total_matches = (await db.execute(count(Match, Match.status == "complete"))).scalar_one()
    upcoming = (await db.execute(count(Match, Match.status != "complete"))).scalar_one()
    total_players = (await db.execute(count(Player))).scalar_one()
    total_users = (await db.execute(count(User))).scalar_one()
    total_preds = (await db.execute(count(Prediction))).scalar_one()
    total_del = (await db.execute(count(Delivery))).scalar_one()
    roles = dict((await db.execute(select(User.role, func.count()).group_by(User.role))).all())
    mrr = (await db.execute(select(func.sum(Subscription.amount_paise)).where(
        Subscription.plan == "premium_monthly", Subscription.status == "active"))).scalar_one() or 0
    annual = (await db.execute(select(func.sum(Subscription.amount_paise)).where(
        Subscription.plan == "premium_annual", Subscription.status == "active"))).scalar_one() or 0
    bt = (await db.execute(select(BacktestRun).order_by(BacktestRun.run_at.desc()).limit(1))).scalar_one_or_none()
    mv = (await db.execute(select(ModelVersion).where(ModelVersion.is_active.is_(True), ModelVersion.match_type == "T20")
                           .order_by(ModelVersion.created_at.desc()).limit(1))).scalars().first()
    since = datetime.now(timezone.utc) - timedelta(days=14)
    by_day = (await db.execute(select(func.date(Prediction.generated_at), func.count())
                               .where(Prediction.generated_at >= since)
                               .group_by(func.date(Prediction.generated_at)).order_by(func.date(Prediction.generated_at)))).all()
    from backend.cache import MockRedis, get_redis
    from training.models import load_active
    redis = await get_redis()
    checks = {"database": "ok", "cache": "memory" if isinstance(redis, MockRedis) else "redis",
              "model": "ok" if load_active() else "missing"}
    rules = all_rules_including_inactive()
    return AdminMetricsResponse(
        total_matches=total_matches, upcoming_matches=upcoming, total_players=total_players,
        total_users=total_users, premium_users=roles.get("premium", 0), total_predictions=total_preds,
        total_deliveries=total_del, mrr_inr=round((mrr + annual / 12) / 100, 2),
        captain_accuracy=bt.captain_accuracy if bt else None,
        correct_player_rate=bt.correct_player_rate if bt else None,
        top3_captain_rate=bt.top3_captain_rate if bt else None,
        avg_fp_error=bt.avg_fp_error if bt else None,
        model_mae=mv.val_mae if mv else None, baseline_mae=mv.baseline_mae if mv else None,
        model_spearman=mv.val_spearman if mv else None,
        active_model_version=mv.name if mv else None,
        active_rules=sum(1 for r in rules.values() if r.get("is_active", True)),
        system_health="ok" if checks["model"] == "ok" else "degraded", checks=checks,
        predictions_by_day=[{"date": str(d), "count": n} for d, n in by_day], users_by_role=roles,
    )


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.post("/ingest", status_code=202)
async def trigger_ingest(body: IngestRequest, request: Request, db: AsyncSession = Depends(get_db),
                         admin: User = Depends(require_admin)):
    job = jobs.submit("ingest", jobs.job_ingest, source=body.source, incremental=body.incremental)
    await audit(db, request, admin, "data.ingest", "system", job["id"], body.model_dump())
    await db.commit()
    return {"status": "queued", "task_id": job["id"]}


@router.post("/features/rebuild", status_code=202)
async def rebuild_features(request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    job = jobs.submit("features", jobs.job_features)
    await audit(db, request, admin, "features.rebuild", "system", job["id"])
    await db.commit()
    return {"status": "queued", "task_id": job["id"]}


@router.post("/retrain", status_code=202)
async def trigger_retrain(body: RetrainRequest, request: Request, db: AsyncSession = Depends(get_db),
                          admin: User = Depends(require_admin)):
    job = jobs.submit("retrain", jobs.job_retrain, format=body.format)
    await audit(db, request, admin, "model.retrain", "model", job["id"], body.model_dump())
    await db.commit()
    return {"status": "queued", "task_id": job["id"]}


@router.post("/backtest", status_code=202)
async def trigger_backtest(body: BacktestRequest, request: Request, db: AsyncSession = Depends(get_db),
                           admin: User = Depends(require_admin)):
    job = jobs.submit("backtest", jobs.job_backtest, from_date=body.from_date, to_date=body.to_date,
                      n=body.n, name=body.name)
    await audit(db, request, admin, "backtest.run", "system", job["id"], body.model_dump(mode="json"))
    await db.commit()
    return {"status": "queued", "task_id": job["id"]}


@router.get("/jobs")
async def list_jobs(admin: User = Depends(require_admin)):
    return {"jobs": jobs.list_jobs()}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, admin: User = Depends(require_admin)):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "Job not found"})
    return job


# ── Models & backtests ────────────────────────────────────────────────────────

@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    rows = (await db.execute(select(ModelVersion).order_by(ModelVersion.created_at.desc()).limit(20))).scalars().all()
    return {"models": [{"id": str(m.id), "name": m.name, "model_type": m.model_type, "match_type": m.match_type,
                        "feature_count": m.feature_count, "train_rows": m.train_rows, "val_mae": m.val_mae,
                        "baseline_mae": m.baseline_mae, "val_spearman": m.val_spearman,
                        "feature_importance": m.feature_importance, "train_from": m.train_from,
                        "train_to": m.train_to, "is_active": m.is_active, "created_at": m.created_at,
                        "artifact_path": m.artifact_path} for m in rows]}


@router.post("/models/{model_id}/activate")
async def activate_model(model_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
                         admin: User = Depends(require_admin)):
    from pathlib import Path
    from backend.services.engine import invalidate_caches
    from training.models import set_active
    m = await db.get(ModelVersion, model_id)
    if not m or not Path(m.artifact_path).exists():
        raise HTTPException(status_code=400, detail={"code": "MODEL_NOT_FOUND", "message": "Model artifact not found"})
    group = m.match_type or "T20"
    await db.execute(update(ModelVersion).where(ModelVersion.match_type == group).values(is_active=False))
    m.is_active = True
    set_active(group, m.artifact_path, m.name)
    invalidate_caches()
    await audit(db, request, admin, "model.promoted", "model", str(model_id))
    await db.commit()
    return {"status": "active", "model_id": str(model_id)}


@router.get("/backtests")
async def list_backtests(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    rows = (await db.execute(select(BacktestRun).order_by(BacktestRun.run_at.desc()).limit(20))).scalars().all()
    return {"backtests": [{"id": str(b.id), "name": b.name, "from_date": b.from_date, "to_date": b.to_date,
                           "total_matches": b.total_matches, "correct_player_rate": b.correct_player_rate,
                           "avg_players_correct": b.avg_players_correct, "captain_accuracy": b.captain_accuracy,
                           "vc_accuracy": b.vc_accuracy, "top3_captain_rate": b.top3_captain_rate,
                           "avg_fp_error": b.avg_fp_error, "spearman_rho": b.spearman_rho,
                           "simulated_roi": b.simulated_roi, "run_at": b.run_at} for b in rows]}


@router.get("/backtests/{run_id}")
async def get_backtest(run_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    b = await db.get(BacktestRun, run_id)
    if not b:
        raise HTTPException(status_code=404, detail={"code": "BACKTEST_NOT_FOUND", "message": "Backtest not found"})
    return {"id": str(b.id), "name": b.name, "details": b.details, "captain_accuracy": b.captain_accuracy,
            "correct_player_rate": b.correct_player_rate, "total_matches": b.total_matches}


# ── Rules ─────────────────────────────────────────────────────────────────────

def _rule_dict(r: HumanRule) -> dict:
    return {"id": r.ext_id, "rule_type": r.rule_type, "player_key": r.player_key, "condition": r.condition_json,
            "match_types": r.match_types, "impact_score": r.impact_score, "confidence": r.confidence,
            "description": r.description, "source": r.source, "is_active": r.is_active,
            "valid_from": r.valid_from.isoformat() if r.valid_from else None,
            "valid_until": r.valid_until.isoformat() if r.valid_until else None}


def _rule_out(r: HumanRule) -> RuleOut:
    d = _rule_dict(r)
    return RuleOut(**{**d, "valid_from": r.valid_from, "valid_until": r.valid_until},
                   effective_impact=round(r.impact_score * r.confidence, 2), created_at=r.created_at)


async def sync_rules(db: AsyncSession) -> None:
    rows = (await db.execute(select(HumanRule))).scalars().all()
    set_db_rules([_rule_dict(r) for r in rows if r.ext_id])
    from backend.services.engine import invalidate_caches
    invalidate_caches()


@router.get("/rules", response_model=List[RuleOut])
async def list_rules(rule_type: Optional[str] = None, db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    q = select(HumanRule).order_by(HumanRule.ext_id)
    if rule_type:
        q = q.where(HumanRule.rule_type == rule_type)
    return [_rule_out(r) for r in (await db.execute(q)).scalars().all()]


@router.post("/rules", response_model=RuleOut, status_code=201)
async def create_rule(body: RuleCreateRequest, request: Request, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    ext = body.id
    if ext and (await db.execute(select(HumanRule).where(HumanRule.ext_id == ext))).scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"code": "RULE_ID_EXISTS", "message": f"{ext} already exists"})
    if not ext:
        nums = [int(x[5:]) for (x,) in (await db.execute(select(HumanRule.ext_id))).all() if x and x[5:].isdigit()]
        base = {"player": 0, "venue": 100, "matchup": 200, "context": 300}[body.rule_type]
        same = [n for n in nums if base <= n < base + 100]
        ext = f"RULE-{(max(same) + 1) if same else base + 1:04d}"
    rule = HumanRule(ext_id=ext, rule_type=body.rule_type, player_key=body.player_key, condition_json=body.condition,
                     match_types=body.match_types, impact_score=body.impact_score, confidence=body.confidence,
                     description=body.description, source=body.source, valid_from=body.valid_from,
                     valid_until=body.valid_until, is_active=body.is_active, created_by=admin.id)
    db.add(rule)
    await audit(db, request, admin, "rule.created", "rule", ext, body.model_dump(mode="json"))
    await db.commit()
    await db.refresh(rule)
    await sync_rules(db)
    return _rule_out(rule)


async def _get_rule(db: AsyncSession, rule_id: str) -> HumanRule:
    rule = (await db.execute(select(HumanRule).where(HumanRule.ext_id == rule_id))).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail={"code": "RULE_NOT_FOUND", "message": "Rule not found"})
    return rule


@router.patch("/rules/{rule_id}", response_model=RuleOut)
async def update_rule(rule_id: str, body: RuleUpdateRequest, request: Request, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    rule = await _get_rule(db, rule_id)
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(rule, "condition_json" if k == "condition" else k, v)
    await audit(db, request, admin, "rule.updated", "rule", rule_id, {k: str(v) for k, v in changes.items()})
    await db.commit()
    await db.refresh(rule)
    await sync_rules(db)
    return _rule_out(rule)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, request: Request, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    rule = await _get_rule(db, rule_id)
    rule.is_active = False          # soft delete
    await audit(db, request, admin, "rule.deleted", "rule", rule_id)
    await db.commit()
    await sync_rules(db)


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(q: Optional[str] = None, limit: int = Query(50, le=200), db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    query = select(User).order_by(User.created_at.desc()).limit(limit)
    if q:
        query = query.where(func.lower(User.email).contains(q.lower()) | func.lower(User.full_name).contains(q.lower()))
    users = (await db.execute(query)).scalars().all()
    counts = dict((await db.execute(select(Prediction.user_id, func.count()).group_by(Prediction.user_id))).all())
    return {"users": [{"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": u.role,
                       "is_active": u.is_active, "created_at": u.created_at, "last_login_at": u.last_login_at,
                       "predictions": counts.get(u.id, 0)} for u in users]}


@router.patch("/users/{user_id}/role")
async def set_role(user_id: uuid.UUID, body: RoleUpdateRequest, request: Request, db: AsyncSession = Depends(get_db),
                   admin: User = Depends(require_admin)):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "User not found"})
    old = u.role
    u.role = body.role
    if body.role == "premium":
        from backend.routers.payments import activate_premium
        await activate_premium(db, u, "premium_monthly", order_id="admin_grant")
    await audit(db, request, admin, "user.role_changed", "user", str(user_id), {"from": old, "to": body.role})
    await db.commit()
    return {"id": str(u.id), "role": u.role}


# ── Match control ─────────────────────────────────────────────────────────────

@router.patch("/matches/{match_id}")
async def update_match(match_id: str, body: MatchAdminUpdate, request: Request, db: AsyncSession = Depends(get_db),
                       admin: User = Depends(require_admin)):
    m = await db.get(Match, match_id)
    if not m:
        raise HTTPException(status_code=404, detail={"code": "MATCH_NOT_FOUND", "message": "Match not found"})
    events = []
    if body.toss_winner:
        if body.toss_winner not in (m.team_a, m.team_b):
            raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Toss winner must be a team in the match"})
        m.toss_winner, m.toss_decision = body.toss_winner, body.toss_decision or "field"
        events.append(("EVT-02", "Toss update", f"{m.toss_winner} won the toss and chose to {m.toss_decision}. "
                                               "Predictions have been refreshed."))
    if body.playing_xi:
        rows = (await db.execute(select(PlayerTeamMatch, Player).join(Player, Player.id == PlayerTeamMatch.player_id)
                                 .where(PlayerTeamMatch.match_id == match_id))).all()
        names = {n.lower() for xi in body.playing_xi.values() for n in xi}
        for ptm, p in rows:
            ptm.is_playing = p.full_name.lower() in names or p.cricsheet_key.lower() in names
        m.playing_xi_confirmed = True
        events.append(("EVT-01", "Playing XI confirmed", f"Line-ups are in for {m.team_a} vs {m.team_b}."))
    if body.status:
        m.status = body.status
        m.is_complete = body.status == "complete"
        if body.status == "live":
            events.append(("EVT-06", "Match started", f"{m.team_a} vs {m.team_b} is live."))
    from backend.services.engine import invalidate_caches
    invalidate_caches()
    if events:
        users = (await db.execute(select(User.id).where(User.is_active.is_(True)))).scalars().all()
        for evt, title, msg in events:
            for uid in users:
                db.add(Notification(user_id=uid, match_id=match_id, event_type=evt, channel="in_app",
                                    status="sent", title=title, message_preview=msg,
                                    sent_at=datetime.now(timezone.utc)))
    await audit(db, request, admin, "match.updated", "match", match_id, body.model_dump(mode="json", exclude_none=True))
    await db.commit()
    return {"status": "ok", "match_id": match_id, "notifications": len(events)}


# ── Live data (CricketData) & fixtures ────────────────────────────────────────

@router.get("/live-data")
async def live_data_status(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    from integrations import cricapi
    from integrations.fixtures import pinned_series
    from backend.models import ApiCache
    from backend.config import settings as cfg
    last = (await db.execute(select(ApiCache).where(ApiCache.key.like("series_info%"))
                             .order_by(ApiCache.fetched_at.desc()).limit(1))).scalars().first()
    tracked = (await db.execute(select(Match).where(Match.source == "cricapi", Match.status != "complete")
                                .order_by(Match.start_time))).scalars().all()
    return {"usage": await cricapi.usage(db), "configured": cricapi.configured(),
            "pinned_series": await pinned_series(db), "last_series_sync": last.fetched_at if last else None,
            "settings": {"poll_seconds": cfg.LIVE_POLL_SECONDS, "scorecard_minutes": cfg.LIVE_SCORECARD_MINUTES,
                         "sync_hours": cfg.FIXTURE_SYNC_HOURS, "days_ahead": cfg.FIXTURE_DAYS_AHEAD,
                         "max_series": cfg.TRACKED_SERIES_MAX},
            "fixtures": [{"id": m.id, "name": f"{m.team_a} vs {m.team_b}", "series": m.event_name, "status": m.status,
                          "start_time": m.start_time, "squad_source": m.squad_source, "match_type": m.match_type,
                          "gender": m.gender} for m in tracked]}


@router.get("/live-data/series")
async def list_series(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    from integrations.fixtures import discover_series, pinned_series
    try:
        found = await discover_series(db)
    except Exception as e:
        raise HTTPException(status_code=503, detail={"code": "LIVE_DATA_UNAVAILABLE", "message": str(e)})
    pinned = set(await pinned_series(db))
    return {"series": [{"id": s["id"], "name": s["name"], "start": s["_start"], "end": s["_end"],
                        "matches": s.get("matches"), "t20": s.get("t20"), "odi": s.get("odi"), "test": s.get("test"),
                        "priority": s["_priority"], "pinned": s["id"] in pinned} for s in found]}


@router.put("/live-data/pinned")
async def set_pinned(body: dict, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    from integrations.fixtures import set_pinned_series
    ids = [str(x) for x in (body.get("ids") or [])][:20]
    await set_pinned_series(db, ids)
    await audit(db, request, admin, "live_data.pinned", "system", None, {"ids": ids})
    await db.commit()
    return {"pinned": ids}


@router.post("/fixtures/sync", status_code=202)
async def sync_fixtures_now(request: Request, refresh: bool = False, db: AsyncSession = Depends(get_db),
                            admin: User = Depends(require_admin)):
    job = jobs.submit("fixtures", jobs.job_sync_fixtures, refresh=refresh)
    await audit(db, request, admin, "fixtures.sync", "system", job["id"], {"refresh": refresh})
    await db.commit()
    return {"status": "queued", "task_id": job["id"]}


@router.post("/fixtures", status_code=201)
async def create_fixture(body: dict, request: Request, db: AsyncSession = Depends(get_db),
                         admin: User = Depends(require_admin)):
    """Manual fixture: {team_a, team_b, match_type, start_time ISO, venue, gender, event_name}."""
    from integrations.fixtures import NameIndex, build_squads
    from backend.models import Venue
    try:
        start = datetime.fromisoformat(str(body["start_time"]).replace("Z", "+00:00"))
        team_a, team_b = body["team_a"].strip(), body["team_b"].strip()
    except (KeyError, ValueError):
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "team_a, team_b and ISO start_time are required"})
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    gender = body.get("gender", "male")
    index = await NameIndex.build(db)
    team_a, team_b = index.team(team_a, gender), index.team(team_b, gender)
    venue_name = index.venue(body.get("venue") or "") or None
    v = (await db.execute(select(Venue).where(Venue.name == venue_name))).scalars().first() if venue_name else None
    mid = "MN" + uuid.uuid4().hex[:18]
    m = Match(id=mid, source="manual", match_type=body.get("match_type", "T20"), gender=gender, team_type="club",
              team_a=team_a, team_b=team_b, venue_id=v.id if v else None, venue_name=venue_name,
              city=v.city if v else None, match_date=start.date(), start_time=start,
              event_name=body.get("event_name"), status="upcoming", is_complete=False)
    db.add(m)
    await db.flush()
    source = await build_squads(db, m)
    await audit(db, request, admin, "fixture.created", "match", mid, {k: str(v) for k, v in body.items()})
    await db.commit()
    from backend.services.engine import invalidate_caches
    invalidate_caches()
    n = (await db.execute(select(func.count()).select_from(PlayerTeamMatch).where(PlayerTeamMatch.match_id == mid))).scalar_one()
    return {"id": mid, "team_a": team_a, "team_b": team_b, "venue": venue_name, "squad_source": source, "squad_players": n}


@router.post("/matches/{match_id}/squad")
async def rebuild_squad(match_id: str, request: Request, official: bool = False, db: AsyncSession = Depends(get_db),
                        admin: User = Depends(require_admin)):
    """Rebuild squads: probable (from recent line-ups) or official (CricketData match_squad, 10 API hits)."""
    from integrations.fixtures import build_squads
    m = await db.get(Match, match_id)
    if not m:
        raise HTTPException(status_code=404, detail={"code": "MATCH_NOT_FOUND", "message": "Match not found"})
    source = await build_squads(db, m, use_official=official)
    await audit(db, request, admin, "match.squad_rebuilt", "match", match_id, {"official": official, "source": source})
    await db.commit()
    from backend.services.engine import invalidate_caches
    invalidate_caches()
    return {"match_id": match_id, "squad_source": source}


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/audit")
async def audit_log(action: Optional[str] = None, limit: int = Query(50, le=200), db: AsyncSession = Depends(get_db),
                    admin: User = Depends(require_admin)):
    q = select(AdminAction, User.email).join(User, User.id == AdminAction.admin_id) \
        .order_by(AdminAction.performed_at.desc()).limit(limit)
    if action:
        q = q.where(AdminAction.action_type.like(f"{action}%"))
    rows = (await db.execute(q)).all()
    return {"entries": [{"id": str(a.id), "admin": email, "action": a.action_type, "target_type": a.target_type,
                         "target_id": a.target_id, "payload": a.payload, "ip_address": a.ip_address,
                         "created_at": a.performed_at} for a, email in rows]}
