# XithSense — Full Build Implementation Plan

## Overview

XithSense is an AI-powered fantasy cricket intelligence platform built around:
- **22,062 Cricsheet ball-by-ball JSON matches** (2001–2026)
- **ML ensemble** (XGBoost 40% + Human Rules 30% + Form 20% + Live 10%)
- **Dream11 team optimizer** (4 modes via PuLP/DEAP)
- **LLM explainability** (Claude/GPT/Gemini)
- **FastAPI backend** + **React+Vite frontend**

This plan builds the entire project from scratch in dependency order.

---

## Open Questions

> [!IMPORTANT]
> **LLM API Key**: Which LLM provider should be used for explainability? The `.env.example` supports `anthropic`, `openai`, or `google`. Please set up `.env` with the appropriate key before the backend starts.

> [!IMPORTANT]
> **Database**: Do you have a Supabase project or a local PostgreSQL instance ready? The `DATABASE_URL` in `.env` must point to a live Postgres 15+ server for migrations and data ingestion to work.

> [!IMPORTANT]
> **Cricsheet Data**: The data ingestion pipeline expects `data/raw/all_json.zip` (downloadable from https://cricsheet.org/downloads/all_json.zip). Should we proceed without it and use mock data for the frontend demo?

> [!NOTE]
> **Frontend First**: The docs classify the React SPA as Phase 2 (post-MVP), but the request says "build the entire project". We will build both the backend API and the full frontend simultaneously.

---

## Proposed Changes

### Layer 0 — Project Foundation

#### [MODIFY] Project root config files
- Copy `.env.example` → `.env` (placeholder values)
- Verify `requirements.txt` and `requirements-dev.txt`
- Verify `Makefile`, `Dockerfile`, `docker-compose.yml`

---

### Layer 1 — Backend Core

#### [NEW] `backend/__init__.py`
#### [NEW] `backend/config.py` — Pydantic settings loading all env vars
#### [NEW] `backend/database.py` — SQLAlchemy async engine + session factory
#### [NEW] `backend/models/` — SQLAlchemy ORM models for all 22 tables

Tables (from DATABASE_SCHEMA.md):
`user`, `subscription`, `venue`, `match`, `player`, `player_team_match`,
`innings`, `delivery`, `player_match_performance`, `rolling_feature`,
`venue_stat`, `matchup_stat`, `human_rule`, `rule_trigger`, `prediction`,
`predicted_player`, `recommended_team`, `team_player`, `backtest_run`,
`model_version`, `chat_session`, `chat_message`

#### [NEW] `backend/schemas/` — Pydantic request/response schemas per endpoint group
#### [NEW] `backend/dependencies.py` — Shared FastAPI deps (get_db, get_current_user, rate_limiter)
#### [NEW] `backend/security.py` — JWT creation/verification, bcrypt hashing
#### [NEW] `backend/cache.py` — Redis client + helper functions (get/set with TTL)
#### [NEW] `backend/main.py` — FastAPI app factory, CORS, middleware, router mounting

---

### Layer 2 — Alembic Migrations

#### [NEW] `alembic.ini`
#### [NEW] `alembic/env.py`
#### [NEW] `alembic/versions/0001_initial_schema.py` — All 22 tables

---

### Layer 3 — API Routers

#### [NEW] `backend/routers/auth.py`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

#### [NEW] `backend/routers/matches.py`
- `GET /api/v1/matches/upcoming`
- `GET /api/v1/matches/{match_id}`
- `GET /api/v1/matches/{match_id}/live` (WebSocket upgrade)

#### [NEW] `backend/routers/players.py`
- `GET /api/v1/players/search`
- `GET /api/v1/players/{player_id}`
- `GET /api/v1/players/{player_id}/matchups`

#### [NEW] `backend/routers/predict.py`
- `POST /api/v1/predict/team`
- `POST /api/v1/predict/team/portfolio`
- `POST /api/v1/predict/captain`
- `GET /api/v1/predict/differentials/{match_id}`
- `GET /api/v1/explain/{match_id}/{player_id}`

#### [NEW] `backend/routers/chat.py`
- `POST /api/v1/chat`

#### [NEW] `backend/routers/admin.py`
- `POST /api/v1/admin/ingest`
- `POST /api/v1/admin/retrain`
- `GET /api/v1/admin/metrics`
- `POST /api/v1/admin/rules`
- `PATCH /api/v1/admin/rules/{rule_id}`

#### [NEW] `backend/routers/payments.py`
- `POST /api/v1/payments/create-subscription`
- `POST /api/v1/payments/webhook` (Razorpay)

---

### Layer 4 — Backend Services

#### [NEW] `backend/services/auth_service.py`
#### [NEW] `backend/services/match_service.py`
#### [NEW] `backend/services/player_service.py`
#### [NEW] `backend/services/prediction_service.py` — orchestrates ensemble → optimizer → explainer
#### [NEW] `backend/services/chat_service.py`
#### [NEW] `backend/services/admin_service.py`
#### [NEW] `backend/services/payment_service.py`
#### [NEW] `backend/services/notification_service.py`

---

### Layer 5 — Data Ingestion Pipeline

#### [NEW] `scripts/ingest_cricsheet.py` — parse Cricsheet JSON → upsert all DB tables
#### [NEW] `scripts/build_features.py` — trigger feature engineering pipeline
#### [NEW] `scripts/db_migrate.py` — helper to run Alembic programmatically

#### [NEW] `ingestion/__init__.py`
#### [NEW] `ingestion/parser.py` — Cricsheet JSON → delivery/match/innings/player rows
#### [NEW] `ingestion/fantasy_points.py` — compute Dream11 FP from delivery records
#### [NEW] `ingestion/validator.py` — schema validation per Cricsheet v1.2.0

---

### Layer 6 — Feature Engineering

#### [NEW] `feature_engineering/__init__.py`
#### [NEW] `feature_engineering/rolling.py` — rolling batting/bowling/fantasy features (3/5/10 window)
#### [NEW] `feature_engineering/venue.py` — venue-level aggregation
#### [NEW] `feature_engineering/matchup.py` — batter vs bowler-type breakdown
#### [NEW] `feature_engineering/context.py` — match-time context features (is_chasing, home_ground, etc.)
#### [NEW] `feature_engineering/pipeline.py` — orchestration: runs all four modules in order

---

### Layer 7 — Human Rules Engine

#### [NEW] `human_rules/__init__.py`
#### [NEW] `human_rules/loader.py` — load PLAYER_RULES.json, VENUE_RULES.json, etc. at startup
#### [NEW] `human_rules/engine.py` — evaluate applicable rules per player per match context
#### [NEW] `human_rules/validate_rules.py` — script to validate all rule JSON files

(Rule JSON files already exist: `PLAYER_RULES.json`, `VENUE_RULES.json`, `MATCHUP_RULES.json`, `CONTEXT_RULES.json`)

---

### Layer 8 — ML Models & Ensemble

#### [NEW] `training/__init__.py`
#### [NEW] `training/dataset.py` — build training DataFrame from feature tables
#### [NEW] `training/models/xgboost_model.py`
#### [NEW] `training/models/lightgbm_model.py`
#### [NEW] `training/models/catboost_model.py`
#### [NEW] `training/ensemble.py` — weighted ensemble (40/30/20/10)
#### [NEW] `training/train_ensemble.py` — CLI entry point for training
#### [NEW] `training/evaluate.py` — compute MAE, RMSE, captain accuracy, correct-player rate

---

### Layer 9 — Team Optimizer

#### [NEW] `optimizer/__init__.py`
#### [NEW] `optimizer/constraints.py` — Dream11 rules: 11 players, credits ≤100, role limits, team cap
#### [NEW] `optimizer/lp_optimizer.py` — PuLP linear programming optimizer
#### [NEW] `optimizer/genetic_optimizer.py` — DEAP fallback
#### [NEW] `optimizer/captain_engine.py` — rank captain/VC options
#### [NEW] `optimizer/differential_picker.py` — identify low-ownership high-ceiling picks
#### [NEW] `optimizer/team_builder.py` — orchestrate 4 modes: safe | grand_league | aggressive | small_league

---

### Layer 10 — LLM Explainability

#### [NEW] `llm/__init__.py`
#### [NEW] `llm/providers/anthropic_provider.py`
#### [NEW] `llm/providers/openai_provider.py`
#### [NEW] `llm/providers/google_provider.py`
#### [NEW] `llm/router.py` — select provider based on `LLM_PROVIDER` env var
#### [NEW] `llm/explainer.py` — generate per-player explanations
#### [NEW] `llm/chat_assistant.py` — handle fantasy cricket Q&A with match context

---

### Layer 11 — Celery Workers

#### [NEW] `backend/worker.py` — Celery app definition
#### [NEW] `backend/tasks/ingestion_task.py`
#### [NEW] `backend/tasks/feature_task.py`
#### [NEW] `backend/tasks/retrain_task.py`
#### [NEW] `backend/tasks/notification_task.py`

---

### Layer 12 — Notifications

#### [NEW] `notifications/__init__.py`
#### [NEW] `notifications/telegram.py`
#### [NEW] `notifications/email_sender.py`
#### [NEW] `notifications/dispatcher.py` — route to correct channel per user preferences

---

### Layer 13 — Backtesting

#### [NEW] `evaluation/__init__.py`
#### [NEW] `evaluation/backtest_runner.py` — replay predictions over historical date range
#### [NEW] `evaluation/metrics.py` — captain accuracy, correct-player rate, avg FP error, simulated ROI

---

### Layer 14 — Tests

#### [NEW] `tests/conftest.py` — pytest fixtures, test DB setup/teardown
#### [NEW] `tests/unit/test_rules_engine.py`
#### [NEW] `tests/unit/test_optimizer.py`
#### [NEW] `tests/unit/test_fantasy_points.py`
#### [NEW] `tests/unit/test_feature_engineering.py`
#### [NEW] `tests/integration/test_auth.py`
#### [NEW] `tests/integration/test_predict.py`
#### [NEW] `tests/integration/test_chat.py`

---

### Layer 15 — Frontend (React + Vite)

Using React 18, Vite 5, Zustand, TanStack Query v5, React Router v6, Recharts.
Design tokens from `frontend/DESIGN_TOKENS.json` (Indigo primary, Slate dark mode).

#### [NEW] `frontend/` — Vite React app scaffold

**Pages (11 routes):**
- `/` — Landing page (hero, features, pricing)
- `/login` — Login form
- `/register` — Registration form
- `/matches` — Match list with upcoming matches
- `/matches/:id` — Match detail + prediction (tabs: Safe/GL/Aggressive/SL)
- `/matches/:id/live` — Live intelligence (WebSocket, Premium)
- `/players/:id` — Player profile (form chart, matchup radar)
- `/chat` — AI chat assistant (Premium)
- `/account` — Account + subscription management
- `/subscribe` — Plan comparison + Razorpay checkout
- `/admin` — Admin dashboard

**Key components:**
- `PlayerCard` — role badge, credits, predicted FP, confidence ring
- `CaptainPicker` — modal with Best/Safe/Risk captain options
- `TeamGrid` — cricket field layout with 11 players
- `DifferentialPanel` — low-ownership high-ceiling picks
- `ExplanationDrawer` — slide-up panel with LLM rationale
- `LiveScoreTicker` — WebSocket-connected real-time overlay
- `ChatInterface` — markdown-rendered AI conversation
- `MatchCard` — upcoming match with prediction-ready indicator
- `PricingCards` — Free/Premium/Annual plan comparison
- `AdminMetrics` — charts for accuracy KPIs and system health

---

## Verification Plan

### Automated Tests
```bash
pytest tests/ -v --cov=backend --cov=training --cov=optimizer
```

### Build Verification
```bash
# Backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend && npm run dev
```

### Manual Verification
1. Register → Login → view `/matches` page loads
2. Click a match → prediction loads with player cards
3. AI chat responds correctly
4. Admin metrics page shows system health
5. WebSocket live feed connects on `/matches/:id/live`
