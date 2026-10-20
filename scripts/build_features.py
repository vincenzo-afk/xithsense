"""
Rebuild the feature store (rolling form, venue stats, matchup stats, inferred roles).
Usage: python -m scripts.build_features
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import AsyncSessionLocal, create_tables  # noqa: E402
from feature_engineering.pipeline import run_pipeline  # noqa: E402


async def main() -> None:
    await create_tables()
    async with AsyncSessionLocal() as db:
        print(json.dumps(await run_pipeline(db), indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
