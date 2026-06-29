"""
FastAPI Application — XithSense API
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.routers import auth, matches, players, predict, chat, admin, payments

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))
logger = logging.getLogger("xithsense")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("XithSense API starting up...")
    # Create database tables for development/testing
    try:
        from backend.database import create_tables
        await create_tables()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}", exc_info=True)

    # Load human rules at startup
    try:
        from human_rules.loader import load_all_rules
        load_all_rules()
        logger.info("Human intelligence rules loaded")
    except Exception as e:
        logger.warning(f"Could not load human rules: {e}")
    yield
    logger.info("XithSense API shutting down...")


app = FastAPI(
    title="XithSense API",
    description="AI-powered fantasy cricket intelligence platform",
    version="0.5.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handling ────────────────────────────────────────────────────────────
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # If the detail is a dict, return it directly, otherwise wrap it
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content={"error": detail})
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(detail)}},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = "Validation error"
    if errors:
        loc = " -> ".join(str(x) for x in errors[0].get("loc", []))
        msg = f"{loc}: {errors[0].get('msg')}"
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": msg, "details": errors}},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
    )

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(matches.router)
app.include_router(players.router)
app.include_router(predict.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(payments.router)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "version": "0.5.0",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "environment": settings.ENV,
    }


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", tags=["root"])
async def root():
    return {
        "name": "XithSense API",
        "version": "0.5.0",
        "docs": "/docs",
        "health": "/health",
    }
