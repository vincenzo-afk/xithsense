"""
Cricsheet data ingestion: parse ball-by-ball JSON → matches, innings, deliveries,
players, performances (with fantasy points), then rebuild the feature store.

Usage:
    python -m scripts.ingest_cricsheet --source data/raw/all_json.zip
    python -m scripts.ingest_cricsheet --source data/raw/all_json/ --full   # re-ingest existing matches
Download: https://cricsheet.org/downloads/all_json.zip
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest")


async def ingest(source: str, incremental: bool = True, features: bool = True) -> dict:
    from backend.database import AsyncSessionLocal, create_tables
    from feature_engineering.pipeline import run_pipeline
    from ingestion.loader import ingest_files, iter_source_files

    await create_tables()
    files, people = iter_source_files(source)
    logger.info("Found %d match files (%d people records)", len(files), len(people))
    async with AsyncSessionLocal() as db:
        report = await ingest_files(db, files, people, incremental=incremental)
        logger.info("Ingestion: %s", report.as_dict())
        out = {"ingest": report.as_dict()}
        if features:
            out["features"] = await run_pipeline(db)
    return out


def main():
    ap = argparse.ArgumentParser(description="Ingest Cricsheet data")
    ap.add_argument("--source", default="data/raw/all_json.zip")
    ap.add_argument("--full", action="store_true", help="re-ingest matches that already exist")
    ap.add_argument("--skip-features", action="store_true")
    a = ap.parse_args()
    print(json.dumps(asyncio.run(ingest(a.source, not a.full, not a.skip_features)), indent=2))


if __name__ == "__main__":
    main()
