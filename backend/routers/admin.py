"""
Admin router: ingest, retrain, metrics, rules CRUD
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.dependencies import require_admin
from backend.models import (
    AdminAction, HumanRule, Match, Player, Prediction, User,
)
from backend.schemas import (
    AdminMetricsResponse, IngestRequest, RetrainRequest,
    RuleCreateRequest, RuleOut,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/metrics", response_model=AdminMetricsResponse)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    total_matches = (await db.execute(select(func.count()).select_from(Match))).scalar_one()
    total_players = (await db.execute(select(func.count()).select_from(Player))).scalar_one()
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_preds = (await db.execute(select(func.count()).select_from(Prediction))).scalar_one()

    return AdminMetricsResponse(
        total_matches=total_matches,
        total_players=total_players,
        total_users=total_users,
        total_predictions=total_preds,
        captain_accuracy=None,
        correct_player_rate=None,
        avg_fp_error=None,
        active_model_version=None,
        system_health="ok",
    )


@router.post("/ingest")
async def trigger_ingest(
    body: IngestRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    # Queue Celery task
    try:
        from backend.tasks.ingestion_task import ingest_cricsheet_task
        task = ingest_cricsheet_task.delay(source=body.source, incremental=body.incremental)
        task_id = task.id
    except Exception:
        task_id = "celery-not-configured"

    action = AdminAction(admin_id=admin.id, action_type="ingest", payload=body.model_dump())
    db.add(action)
    await db.commit()
    return {"status": "queued", "task_id": task_id}


@router.post("/retrain")
async def trigger_retrain(
    body: RetrainRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        from backend.tasks.retrain_task import retrain_models_task
        task = retrain_models_task.delay(format=body.format, model_ids=body.model_ids)
        task_id = task.id
    except Exception:
        task_id = "celery-not-configured"

    action = AdminAction(admin_id=admin.id, action_type="retrain", payload=body.model_dump())
    db.add(action)
    await db.commit()
    return {"status": "queued", "task_id": task_id}


@router.post("/rules", response_model=RuleOut, status_code=201)
async def create_rule(
    body: RuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    rule = HumanRule(
        rule_type=body.rule_type,
        player_key=body.player_key,
        condition_json=body.condition_json,
        impact_score=body.impact_score,
        confidence=body.confidence,
        source=body.source,
        is_active=body.is_active,
        created_by=admin.id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return RuleOut.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=RuleOut)
async def update_rule(
    rule_id: uuid.UUID,
    body: RuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(HumanRule).where(HumanRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "RULE_NOT_FOUND", "message": "Rule not found"})
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    await db.commit()
    await db.refresh(rule)
    return RuleOut.model_validate(rule)
