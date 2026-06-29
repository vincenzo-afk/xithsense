# Environment Variables Reference

Complete reference for all environment variables. All must exist in `.env` (local) or platform secret manager (production).

---

## Runtime

| Variable | Required | Type | Default | Description |
|----------|----------|------|---------|-------------|
| `ENV` | ✅ | string | `development` | `development` \| `staging` \| `production` |
| `DEBUG` | ✅ | boolean | `true` | Enable debug mode (never true in production) |
| `LOG_LEVEL` | ✅ | string | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `SECRET_KEY` | ✅ | string | — | JWT signing secret; min 32 chars; random |
| `XITHSENSE_API_KEY` | ✅ | string | — | Internal service-to-service key |
| `VERSION` | ⬜ | string | `"0.0.0"` | App version (injected by CI) |

---

## Database

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | Full PostgreSQL connection string |
| `SUPABASE_URL` | ✅ | Supabase project API base URL |
| `SUPABASE_SERVICE_KEY` | ✅ | Service role key (full DB access) |
| `SUPABASE_ANON_KEY` | ✅ | Anonymous key (client-side, limited access) |
| `TEST_DATABASE_URL` | ⬜ | Override for test environment |

---

## Cache

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | ✅ | — | Redis connection URL |
| `REDIS_FEATURE_TTL_SECONDS` | ⬜ | `21600` | Feature cache TTL (6 hours) |
| `REDIS_PREDICTION_TTL_SECONDS` | ⬜ | `1800` | Prediction cache TTL (30 min) |
| `REDIS_EXPLANATION_TTL_SECONDS` | ⬜ | `3600` | Explanation cache TTL (1 hour) |

---

## Vector DB

| Variable | Required | Description |
|----------|----------|-------------|
| `QDRANT_URL` | ✅ | Qdrant service URL |
| `QDRANT_API_KEY` | ⬜ | API key for Qdrant Cloud; omit for local |
| `QDRANT_COLLECTION_PLAYERS` | ⬜ | Collection name (default: `player_embeddings`) |
| `QDRANT_COLLECTION_RULES` | ⬜ | Collection name (default: `human_rules`) |

---

## LLM

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | ✅ | `anthropic` \| `openai` \| `google` |
| `ANTHROPIC_API_KEY` | Conditional | Required if `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | Conditional | Required if `LLM_PROVIDER=openai` |
| `GOOGLE_API_KEY` | Conditional | Required if `LLM_PROVIDER=google` |
| `LLM_MODEL` | ⬜ | Default: `claude-sonnet-4-6` |
| `LLM_MAX_TOKENS` | ⬜ | Default: `1024` |
| `LLM_TEMPERATURE` | ⬜ | Default: `0.3` |

---

## ML / Prediction

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CRICSHEET_DATA_PATH` | ⬜ | `data/raw/all_json/` | Path to extracted JSON files |
| `MODEL_ARTIFACTS_PATH` | ⬜ | `models/artifacts/` | Trained model storage |
| `ENSEMBLE_ML_WEIGHT` | ⬜ | `0.40` | ML component weight |
| `ENSEMBLE_HUMAN_RULES_WEIGHT` | ⬜ | `0.30` | Human rules weight |
| `ENSEMBLE_FORM_WEIGHT` | ⬜ | `0.20` | Recent form weight |
| `ENSEMBLE_LIVE_WEIGHT` | ⬜ | `0.10` | Live context weight |
| `FORM_WINDOW_SHORT` | ⬜ | `3` | Short rolling window |
| `FORM_WINDOW_MEDIUM` | ⬜ | `5` | Medium rolling window |
| `FORM_WINDOW_LONG` | ⬜ | `10` | Long rolling window |

---

## Team Optimizer

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MAX_PLAYERS_PER_TEAM` | ⬜ | `7` | Max players from one real team |
| `TOTAL_PLAYERS` | ⬜ | `11` | Team size |
| `MAX_CREDITS` | ⬜ | `100.0` | Total credit budget |
| `MIN_WK` / `MAX_WK` | ⬜ | `1` / `4` | WK slot limits |
| `MIN_BAT` / `MAX_BAT` | ⬜ | `3` / `6` | BAT slot limits |
| `MIN_AR` / `MAX_AR` | ⬜ | `1` / `4` | AR slot limits |
| `MIN_BOWL` / `MAX_BOWL` | ⬜ | `3` / `6` | BOWL slot limits |

---

## Notifications

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ⬜ | Telegram Bot API token |
| `SMTP_HOST` | ⬜ | SMTP server hostname |
| `SMTP_PORT` | ⬜ | SMTP port (587 for TLS) |
| `SMTP_USER` | ⬜ | SMTP sender address |
| `SMTP_PASSWORD` | ⬜ | SMTP password |

---

## Payments

| Variable | Required | Description |
|----------|----------|-------------|
| `RAZORPAY_KEY_ID` | ✅ | Razorpay publishable key |
| `RAZORPAY_KEY_SECRET` | ✅ | Razorpay secret key |

---

## API

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALLOWED_ORIGINS` | ✅ | — | Comma-separated CORS origins |
| `RATE_LIMIT_FREE_RPM` | ⬜ | `30` | Free plan rate limit |
| `RATE_LIMIT_PREMIUM_RPM` | ⬜ | `300` | Premium plan rate limit |
| `RATE_LIMIT_ADMIN_RPM` | ⬜ | `1000` | Admin rate limit |

---

## Infrastructure

| Variable | Required | Description |
|----------|----------|-------------|
| `CELERY_BROKER_URL` | ✅ | Celery broker (usually same Redis) |
| `CELERY_RESULT_BACKEND` | ✅ | Celery result backend |
| `SENTRY_DSN` | ⬜ | Sentry error tracking DSN |
| `WEATHER_API_KEY` | ⬜ | OpenWeatherMap API key |
