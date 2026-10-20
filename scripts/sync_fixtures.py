"""
Sync upcoming / live fixtures from CricketData now (quota-aware).
Usage: python -m scripts.sync_fixtures [--refresh]   (--refresh re-fetches series schedules)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import AsyncSessionLocal, create_tables  # noqa: E402
from integrations.fixtures import sync_fixtures  # noqa: E402


async def main(refresh: bool) -> None:
    await create_tables()
    async with AsyncSessionLocal() as db:
        print(json.dumps(await sync_fixtures(db, refresh_series=refresh), indent=2, default=str))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    asyncio.run(main(ap.parse_args().refresh))
