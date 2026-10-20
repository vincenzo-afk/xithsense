"""
FastAPI Application — XithSense API
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import settings
from backend.ratelimit import RateLimitMiddleware
from backend.routers import admin, auth, chat, live, matches, notifications, payments, players, predict

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("xithsense")
VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("XithSense API starting up (%s, db=%s)", settings.ENV, settings.DATABASE_URL.split("://")[0])
    from backend.database import AsyncSessionLocal, create_tables
    await create_tables()
    from human_rules.loader import load_all_rules
    load_all_rules()
    try:
        async with AsyncSessionLocal() as db:
            await admin.sync_rules(db)
    except Exception as e:
        logger.warning("Could not sync DB rules: %s", e)
    import asyncio
    scheduler = asyncio.create_task(_fixture_scheduler())
    yield
    scheduler.cancel()
    from integrations.live_feed import live_manager
    await live_manager.shutdown()
    logger.info("XithSense API shutting down")


async def _fixture_scheduler():
    """Keep upcoming fixtures fresh: sync on startup and every FIXTURE_SYNC_HOURS (quota-aware)."""
    import asyncio
    from integrations import cricapi
    from backend.jobs import job_sync_fixtures
    from backend.database import AsyncSessionLocal
    if not cricapi.configured():
        logger.info("CRICKETDATA_API_KEY not set — live fixture sync disabled")
        return
    await asyncio.sleep(3)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                result = await job_sync_fixtures(db)
            logger.info("Fixture sync: %s matches from %s", result.get("matches_upserted"), result.get("series_tracked"))
        except Exception as e:
            logger.warning("Fixture sync failed: %s", e)
        await asyncio.sleep(settings.FIXTURE_SYNC_HOURS * 3600)


app = FastAPI(
    title="XithSense API",
    description="AI-powered fantasy cricket intelligence platform",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "X-Request-ID"],
)


@app.middleware("http")
async def request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or str(uuid.uuid4())


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    body = dict(detail) if isinstance(detail, dict) else {"code": "HTTP_ERROR", "message": str(detail)}
    if exc.status_code == 404 and not isinstance(detail, dict):
        body["code"] = "NOT_FOUND"
    body.setdefault("details", {})
    body["request_id"] = _rid(request)
    return JSONResponse(status_code=exc.status_code, content={"error": body}, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = "Validation error"
    if errors:
        loc = ".".join(str(x) for x in errors[0].get("loc", []) if x != "body")
        msg = f"{loc}: {errors[0].get('msg')}" if loc else errors[0].get("msg", msg)
    return JSONResponse(status_code=422, content={"error": {
        "code": "VALIDATION_ERROR", "message": msg,
        "details": {"errors": [{"loc": e.get("loc"), "msg": e.get("msg")} for e in errors]},
        "request_id": _rid(request)}})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": {
        "code": "INTERNAL_ERROR", "message": "An unexpected error occurred", "details": {},
        "request_id": _rid(request)}})


for r in (auth.router, matches.router, players.router, predict.router, predict.explain_router, chat.router,
          live.router, admin.router, payments.router, notifications.router):
    app.include_router(r)


@app.get("/health", tags=["health"])
async def health():
    from backend.cache import MockRedis, get_redis
    from training.models import load_active
    checks = {"database": "ok", "redis": "memory-fallback", "models": "ok" if load_active() else "missing"}
    try:
        from sqlalchemy import text
        from backend.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "error"
    if not isinstance(await get_redis(), MockRedis):
        checks["redis"] = "ok"
    status = "ok" if checks["database"] == "ok" else "degraded"
    return {"status": status, "version": VERSION, "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "environment": settings.ENV, "checks": checks}


# ── Serve the built frontend (single-process deployment) ─────────────────────
DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

if DIST.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "health")):
            return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": "Not found"}})
        f = DIST / full_path
        return FileResponse(f if full_path and f.is_file() else DIST / "index.html")
else:
    @app.get("/", tags=["root"])
    async def root():
        return {"name": "XithSense API", "version": VERSION, "docs": "/docs", "health": "/health"}
