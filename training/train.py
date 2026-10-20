"""
Train the ensemble on historical performances and register it.

Validation is a strict time split (latest season held out). The production
artifact is then refit on all data. CLI: `python -m training.train`.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import ModelVersion
from feature_engineering.builder import FEATURE_COLUMNS, FORMAT_GROUP, build_feature_frame, load_frames
from training.models import TrainedBundle, fit_bundle, save_bundle

logger = logging.getLogger(__name__)
MIN_PLAYER_MATCHES = 3


def training_rows(frame: pd.DataFrame, match_type_group: str = "T20") -> pd.DataFrame:
    df = frame[~frame.is_pending & frame.fp.notna()]
    df = df[df.match_type.map(FORMAT_GROUP).fillna(df.match_type) == match_type_group]
    return df[df.career_matches >= MIN_PLAYER_MATCHES].copy()


def time_split(df: pd.DataFrame, cutoff: Optional[pd.Timestamp] = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    if cutoff is None:
        # Hold out the most recent ~20% of match dates
        dates = df.match_date.sort_values().unique()
        cutoff = pd.Timestamp(dates[int(len(dates) * 0.8)])
    return df[df.match_date < cutoff], df[df.match_date >= cutoff], cutoff


async def train_all(db: AsyncSession, groups=("T20", "ODI", "Test")) -> dict:
    """Train one ensemble per format group from a single feature build."""
    frames = await load_frames(db)
    frame = await asyncio.to_thread(build_feature_frame, frames)
    out = {}
    for g in groups:
        try:
            out[g] = await train_and_register(db, group=g, frame=frame)
        except RuntimeError as e:
            out[g] = {"skipped": str(e)}
    return out


async def train_and_register(db: AsyncSession, activate: bool = True, group: str = "T20",
                             frame: Optional[pd.DataFrame] = None) -> dict:
    if frame is None:
        frames = await load_frames(db)
        frame = await asyncio.to_thread(build_feature_frame, frames)
    rows = training_rows(frame, group)
    if len(rows) < 200:
        raise RuntimeError(f"Not enough training rows ({len(rows)}); ingest more matches first")
    train, val, cutoff = time_split(rows)
    logger.info("Training on %d rows, validating on %d (cutoff %s)", len(train), len(val), cutoff.date())
    evaluated = await asyncio.to_thread(fit_bundle, train, val, group)
    # Refit on everything for the production artifact, keep holdout metrics
    final: TrainedBundle = await asyncio.to_thread(fit_bundle, rows, None, group)
    final.metrics = evaluated.metrics
    final.feature_importance = evaluated.feature_importance
    path = save_bundle(final)

    ml = evaluated.metrics.get("ml", {})
    if activate:
        await db.execute(update(ModelVersion).where(ModelVersion.match_type == group).values(is_active=False))
    mv = ModelVersion(
        name=f"XithSense {group} ensemble {final.version}", model_type="+".join(final.model_types.values()),
        match_type=group, artifact_path=str(path), feature_count=len(FEATURE_COLUMNS), train_rows=len(rows),
        train_mae=evaluated.metrics.get("M-01", {}).get("train_mae"), val_mae=ml.get("val_mae"),
        baseline_mae=evaluated.metrics.get("baseline_form10", {}).get("val_mae"),
        val_spearman=ml.get("val_spearman"), feature_importance=evaluated.feature_importance,
        train_from=date.fromisoformat(final.train_from), train_to=date.fromisoformat(final.train_to),
        is_active=activate,
    )
    db.add(mv)
    await db.commit()
    from backend.services.engine import invalidate_caches
    invalidate_caches()
    return {"model_version": final.version, "artifact": str(path), "rows": len(rows),
            "holdout_cutoff": str(cutoff.date()), "metrics": evaluated.metrics,
            "feature_importance": evaluated.feature_importance, "model_id": str(mv.id)}


if __name__ == "__main__":
    import json
    from backend.database import AsyncSessionLocal

    logging.basicConfig(level=logging.INFO)

    async def _main():
        async with AsyncSessionLocal() as db:
            print(json.dumps(await train_all(db), indent=2, default=str))

    asyncio.run(_main())
