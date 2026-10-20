"""
Database setup: async SQLAlchemy engine + session factory.
"""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings

# Create the async engine
_engine_kwargs = {"echo": False}
if settings.is_sqlite:
    _engine_kwargs["connect_args"] = {"timeout": 30}
else:
    _engine_kwargs.update(pool_pre_ping=True, pool_size=10, max_overflow=20)

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

if settings.is_sqlite:
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables and add any new nullable columns (use Alembic for destructive changes)."""
    import backend.models  # noqa: F401  (register models on Base.metadata)
    async with engine.begin() as conn:
        if settings.is_sqlite:
            await conn.exec_driver_sql("PRAGMA journal_mode=WAL")   # far more robust than a rollback journal on Windows
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)


def _add_missing_columns(sync_conn) -> None:
    """Additive auto-migration: ALTER TABLE ADD COLUMN for model columns missing from the DB."""
    from sqlalchemy import inspect
    insp = inspect(sync_conn)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        existing = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing or col.primary_key:
                continue
            ddl_type = col.type.compile(dialect=sync_conn.dialect)
            sync_conn.exec_driver_sql(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl_type}')
            for idx in table.indexes:
                if [c.name for c in idx.columns] == [col.name]:
                    idx.create(sync_conn, checkfirst=True)
