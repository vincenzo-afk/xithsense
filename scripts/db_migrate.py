"""
Create all database tables (idempotent). For schema changes in production, use Alembic.
Usage: python -m scripts.db_migrate
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import settings  # noqa: E402
from backend.database import create_tables  # noqa: E402

if __name__ == "__main__":
    asyncio.run(create_tables())
    print(f"Schema ready on {settings.DATABASE_URL.split('@')[-1]}")
