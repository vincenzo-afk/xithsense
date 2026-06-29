"""
Cricsheet data ingestion script.
Usage: python scripts/ingest_cricsheet.py --source data/raw/all_json.zip
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import zipfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest")


async def ingest(source: str, incremental: bool = True) -> None:
    from backend.database import AsyncSessionLocal, create_tables
    from backend.models import Match
    from ingestion.parser import parse_match
    from sqlalchemy import select

    await create_tables()

    source_path = Path(source)
    json_files = []

    if source_path.suffix == ".zip":
        logger.info(f"Extracting {source_path}...")
        extract_dir = source_path.parent / "all_json"
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(source_path) as zf:
            zf.extractall(extract_dir)
        json_files = list(extract_dir.glob("**/*.json"))
    elif source_path.is_dir():
        json_files = list(source_path.glob("**/*.json"))
    else:
        logger.error(f"Source not found: {source}")
        return

    logger.info(f"Found {len(json_files)} JSON files")
    ingested = 0
    errors = 0

    async with AsyncSessionLocal() as db:
        for json_file in json_files:
            match_id = json_file.stem
            try:
                if incremental:
                    result = await db.execute(select(Match).where(Match.id == match_id))
                    if result.scalar_one_or_none():
                        continue

                with json_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                match_record, innings_records, delivery_records = parse_match(data)
                match_record["id"] = match_id

                from backend.models import Match as MatchModel
                match_obj = MatchModel(**match_record)
                await db.merge(match_obj)
                await db.commit()
                ingested += 1

                if ingested % 1000 == 0:
                    logger.info(f"Progress: {ingested} matches ingested")

            except Exception as e:
                errors += 1
                logger.error(f"Error ingesting {json_file.name}: {e}")
                await db.rollback()

    logger.info(f"Ingestion complete. {ingested} matches ingested, {errors} errors.")


def main():
    parser = argparse.ArgumentParser(description="Ingest Cricsheet data")
    parser.add_argument("--source", default="data/raw/all_json.zip")
    parser.add_argument("--incremental", action="store_true", default=True)
    args = parser.parse_args()
    asyncio.run(ingest(args.source, args.incremental))


if __name__ == "__main__":
    main()
