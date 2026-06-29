"""
XithSense Configuration
All settings loaded from environment variables via Pydantic Settings.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Runtime ──────────────────────────────────
    ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me-to-a-32-char-min-random-string-xxxxxxxx"
    XITHSENSE_API_KEY: str = "xs-dev-changeme"

    # ── Database ─────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/xithsense"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None

    # ── Redis ────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_FEATURE_TTL_SECONDS: int = 21600      # 6 hours
    REDIS_PREDICTION_TTL_SECONDS: int = 3600    # 1 hour
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Qdrant ───────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_PLAYERS: str = "player_embeddings"
    QDRANT_COLLECTION_RULES: str = "human_rules"

    # ── LLM ──────────────────────────────────────
    LLM_PROVIDER: str = "anthropic"             # anthropic | openai | google
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    LLM_MODEL: str = "claude-sonnet-4-6"
    LLM_MAX_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.3

    # ── Data Paths ───────────────────────────────
    CRICSHEET_DATA_PATH: str = "data/raw/all_json/"
    MODEL_ARTIFACTS_PATH: str = "models/artifacts/"
    FEATURE_STORE_PATH: str = "data/features/"

    # ── ML / Ensemble Weights ────────────────────
    ENSEMBLE_ML_WEIGHT: float = 0.40
    ENSEMBLE_HUMAN_RULES_WEIGHT: float = 0.30
    ENSEMBLE_FORM_WEIGHT: float = 0.20
    ENSEMBLE_LIVE_WEIGHT: float = 0.10
    FORM_WINDOW_SHORT: int = 3
    FORM_WINDOW_MEDIUM: int = 5
    FORM_WINDOW_LONG: int = 10

    # ── Dream11 Constraints ──────────────────────
    MAX_PLAYERS_PER_TEAM: int = 7
    TOTAL_PLAYERS: int = 11
    MAX_CREDITS: float = 100.0
    MIN_WK: int = 1
    MAX_WK: int = 4
    MIN_BAT: int = 3
    MAX_BAT: int = 6
    MIN_AR: int = 1
    MAX_AR: int = 4
    MIN_BOWL: int = 3
    MAX_BOWL: int = 6

    # ── Backtesting ──────────────────────────────
    BACKTEST_DEFAULT_MATCHES: int = 10000
    BACKTEST_MIN_DATE: str = "2018-01-01"

    # ── External APIs ────────────────────────────
    WEATHER_API_KEY: Optional[str] = None
    WEATHER_API_URL: str = "https://api.openweathermap.org/data/2.5"

    # ── Notifications ────────────────────────────
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    WHATSAPP_API_KEY: Optional[str] = None
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # ── Payments ─────────────────────────────────
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None

    # ── Rate Limits ──────────────────────────────
    RATE_LIMIT_FREE_RPM: int = 30
    RATE_LIMIT_PREMIUM_RPM: int = 300
    RATE_LIMIT_ADMIN_RPM: int = 1000

    # ── CORS ─────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,https://app.xithsense.com"

    # ── JWT ──────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def sync_database_url(self) -> str:
        """Synchronous DB URL for Alembic migrations."""
        return self.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
