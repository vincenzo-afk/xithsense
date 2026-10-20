"""
Background job runner for admin operations (ingest, feature rebuild, retrain, backtest).

Jobs run as asyncio tasks in the API process, each with its own DB session, so
no broker is needed locally (the Celery tasks in backend/tasks/ wrap the same
functions for worker deployments). Status for the last 50 jobs is kept in
memory and exposed via GET /api/v1/admin/jobs.
"""
from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_JOBS: "OrderedDict[str, dict]" = OrderedDict()
_LOCKS: Dict[str, asyncio.Lock] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_jobs() -> list[dict]:
    return list(reversed(_JOBS.values()))


def get_job(job_id: str) -> Optional[dict]:
    return _JOBS.get(job_id)


def submit(kind: str, fn: Callable[..., Awaitable[Any]], **params) -> dict:
    """Queue `fn(db, **params)`. Jobs of the same kind run one at a time (queued behind each other)."""
    job_id = str(uuid.uuid4())
    job = {"id": job_id, "kind": kind, "status": "queued", "params": {k: str(v) for k, v in params.items()},
           "created_at": _now(), "started_at": None, "finished_at": None, "result": None, "error": None}
    _JOBS[job_id] = job
    while len(_JOBS) > 50:
        _JOBS.popitem(last=False)
    lock = _LOCKS.setdefault(kind, asyncio.Lock())

    async def runner():
        async with lock:
            job["status"], job["started_at"] = "running", _now()
            try:
                async with AsyncSessionLocal() as db:
                    job["result"] = await fn(db, **params)
                job["status"] = "succeeded"
            except Exception as e:
                logger.error("Job %s (%s) failed: %s", job_id, kind, e)
                job["status"], job["error"] = "failed", f"{e}\n{traceback.format_exc(limit=3)}"
            finally:
                job["finished_at"] = _now()

    asyncio.get_running_loop().create_task(runner())
    return job


# ── Job implementations ──────────────────────────────────────────────────────

async def job_ingest(db, source: str, incremental: bool = True) -> dict:
    from ingestion.loader import ingest_files, iter_source_files
    from feature_engineering.pipeline import run_pipeline
    from backend.services.engine import invalidate_caches
    files, people = iter_source_files(source)
    report = await ingest_files(db, files, people, incremental=incremental)
    features = await run_pipeline(db)
    invalidate_caches()
    return {"ingest": report.as_dict(), "features": features}


async def job_features(db) -> dict:
    from feature_engineering.pipeline import run_pipeline
    from backend.services.engine import invalidate_caches
    out = await run_pipeline(db)
    invalidate_caches()
    return out


async def job_retrain(db, format: str = "all") -> dict:
    from training.train import train_all
    groups = ("T20", "ODI", "Test") if format in ("all", None) else (format,)
    r = await train_all(db, groups)
    return {g: ({k: v for k, v in x.items() if k != "feature_importance"} if isinstance(x, dict) else x) for g, x in r.items()}


async def job_backtest(db, from_date=None, to_date=None, n: int = 200, name: Optional[str] = None,
                       group: str = "T20") -> dict:
    from evaluation.backtest import run_backtest
    return await run_backtest(db, from_date=from_date, to_date=to_date, n=n, name=name, group=group)


async def job_sync_fixtures(db, refresh: bool = False) -> dict:
    from integrations.fixtures import sync_fixtures
    from backend.services.engine import invalidate_caches
    out = await sync_fixtures(db, refresh_series=refresh)
    invalidate_caches()
    return out
