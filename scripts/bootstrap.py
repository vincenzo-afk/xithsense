"""
One-shot setup on real data.

    python -m scripts.bootstrap                          # features → train → backtest → fixtures → users
    python -m scripts.bootstrap --ingest data/raw/all_json.zip
    python -m scripts.bootstrap --skip-train --skip-backtest

Steps: (optional) ingest Cricsheet → feature store + inferred bowling styles →
train T20/ODI/Test ensembles → backtest recent T20s → sync live fixtures from
CricketData → ensure the admin account exists.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from backend.database import AsyncSessionLocal, create_tables  # noqa: E402
from backend.models import HumanRule, Subscription, User  # noqa: E402
from backend.security import hash_password  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bootstrap")

async def ensure_user(db, email: str, password: str, name: str, role: str) -> bool:
    if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
        return False
    now = datetime.now(timezone.utc)
    u = User(email=email, password_hash=hash_password(password), full_name=name, role=role, is_active=True,
             is_verified=True, notification_prefs={"email_enabled": True, "telegram_enabled": False,
                                                   "events": {"EVT-01": True, "EVT-02": True, "EVT-03": True}})
    db.add(u)
    await db.flush()
    plan = {"premium": "premium_monthly", "admin": "premium_annual"}.get(role, "free")
    db.add(Subscription(user_id=u.id, plan=plan, status="active", current_period_start=now,
                        current_period_end=None if plan == "free" else now + timedelta(days=30 if role == "premium" else 3650),
                        amount_paise=29900 if role == "premium" else None))
    await db.commit()
    return True


async def seed_rules(db) -> int:
    from human_rules.loader import load_file_rules
    existing = {r for (r,) in (await db.execute(select(HumanRule.ext_id))).all()}
    n = 0
    for rid, r in load_file_rules().items():
        if rid in existing:
            continue
        db.add(HumanRule(ext_id=rid, rule_type=r["rule_type"], player_key=r.get("player_key"),
                         condition_json=r.get("condition", {}), match_types=r.get("match_types"),
                         impact_score=r["impact_score"], confidence=r["confidence"], description=r.get("description"),
                         source=r.get("source"), is_active=r.get("is_active", True)))
        n += 1
    await db.commit()
    return n


async def main(a) -> None:
    await create_tables()
    async with AsyncSessionLocal() as db:
        if a.ingest:
            from ingestion.loader import ingest_files, iter_source_files
            files, people = iter_source_files(a.ingest)
            log.info("Ingesting %d match files…", len(files))
            log.info("Ingestion: %s", (await ingest_files(db, files, people)).as_dict())

        if not a.skip_features:
            from feature_engineering.pipeline import run_pipeline
            log.info("Feature store: %s", await run_pipeline(db))
        log.info("Rules mirrored: %d", await seed_rules(db))

        frame = None
        if not a.skip_train or not a.skip_backtest:
            from feature_engineering.builder import build_feature_frame, load_frames
            log.info("Building leakage-free feature frame…")
            frame = await asyncio.to_thread(build_feature_frame, await load_frames(db))
            log.info("Feature rows: %d", len(frame))
        if not a.skip_train:
            from training.train import train_and_register
            for g in ("T20", "ODI", "Test"):
                try:
                    r = await train_and_register(db, group=g, frame=frame)
                    ml, base = r["metrics"]["ml"], r["metrics"]["baseline_form10"]
                    log.info("%s model %s — %d rows, holdout MAE %.2f (form baseline %.2f), ρ %.3f",
                             g, r["model_version"], r["rows"], ml["val_mae"], base["val_mae"], ml["val_spearman"])
                except RuntimeError as e:
                    log.warning("%s model skipped: %s", g, e)
        if not a.skip_backtest:
            from evaluation.backtest import run_backtest
            bt = await run_backtest(db, n=a.backtest_n, name=f"Recent men's T20s ({a.backtest_n})", frame=frame)
            log.info("Backtest %s: %s", bt["date_range"], json.dumps(bt["metrics"]))

        from integrations import cricapi
        if cricapi.configured() and not a.skip_fixtures:
            from integrations.fixtures import sync_fixtures
            r = await sync_fixtures(db)
            log.info("Fixtures: %d upserted from %s · API usage %s", r.get("matches_upserted", 0),
                     r.get("series_tracked"), r.get("api_usage"))

        pw = a.admin_password or secrets.token_urlsafe(10)
        if await ensure_user(db, a.admin_email, pw, "Administrator", "admin"):
            print(f"\nAdmin account created: {a.admin_email} / {pw}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ingest", help="Cricsheet zip or folder to ingest first")
    ap.add_argument("--skip-features", action="store_true")
    ap.add_argument("--skip-train", action="store_true")
    ap.add_argument("--skip-backtest", action="store_true")
    ap.add_argument("--skip-fixtures", action="store_true")
    ap.add_argument("--backtest-n", type=int, default=300)
    ap.add_argument("--admin-email", default="admin@xithsense.app")
    ap.add_argument("--admin-password")
    asyncio.run(main(ap.parse_args()))
