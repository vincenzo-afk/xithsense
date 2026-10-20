"""
Create a user.   python -m scripts.create_user EMAIL PASSWORD [--role free|premium|admin] [--name "Full Name"]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import AsyncSessionLocal, create_tables  # noqa: E402
from scripts.bootstrap import ensure_user  # noqa: E402


async def main(a) -> None:
    await create_tables()
    async with AsyncSessionLocal() as db:
        created = await ensure_user(db, a.email.lower(), a.password, a.name or a.email.split("@")[0], a.role)
    print("created" if created else "already exists")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("email")
    ap.add_argument("password")
    ap.add_argument("--role", default="free", choices=["free", "premium", "admin"])
    ap.add_argument("--name")
    asyncio.run(main(ap.parse_args()))
