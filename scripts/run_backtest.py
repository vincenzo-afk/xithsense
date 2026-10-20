"""
Backtest the full prediction pipeline on held-out matches.
Usage: python -m scripts.run_backtest [--n 10000] [--from 2025-01-01] [--to 2025-12-31]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import AsyncSessionLocal  # noqa: E402
from evaluation.backtest import run_backtest  # noqa: E402


async def main(a) -> None:
    async with AsyncSessionLocal() as db:
        r = await run_backtest(db, from_date=a.from_date, to_date=a.to_date, n=a.n, name=a.name)
        print(json.dumps(r, indent=2, default=str))


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--from", dest="from_date", type=date.fromisoformat)
    ap.add_argument("--to", dest="to_date", type=date.fromisoformat)
    ap.add_argument("--name")
    asyncio.run(main(ap.parse_args()))
