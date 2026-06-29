# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          XithSense Platform                         │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                        Data Layer                            │  │
│  │   Cricsheet JSONs ──► ETL Pipeline ──► PostgreSQL (Supabase) │  │
│  │         22,062 matches  |                 ▲                  │  │
│  │         ball-by-ball    └─► Redis Cache ──┘                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   Intelligence Layer                          │  │
│  │                                                               │  │
│  │   Feature Engineering ─► ML Models (XGB+LGB+CAT)            │  │
│  │              +                    +                           │  │
│  │   Human Rules Engine ──────► Ensemble Engine                 │  │
│  │              +               (40/30/20/10)                   │  │
│  │   Live Context ─────────────────────┘                        │  │
│  │                          │                                    │  │
│  │              Team Optimizer (PuLP / DEAP)                    │  │
│  │              Captain Engine                                   │  │
│  │              LLM Explainer (Claude/GPT/Gemini)               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     API Layer (FastAPI)                       │  │
│  │   REST Endpoints     WebSocket     Admin API                  │  │
│  │   JWT Auth           Rate Limiting  Celery Tasks              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Client Layer                               │  │
│  │   React SPA (Web)    Mobile App    Third-party API consumers  │  │
│  │   Telegram Bot       WhatsApp      Tipster tools              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Service Dependencies

```
API Server
 ├── PostgreSQL (Supabase) — primary data store
 ├── Redis — feature cache + Celery broker
 ├── Qdrant — player embeddings + rule similarity
 └── LLM API — Anthropic/OpenAI/Google

Celery Worker
 ├── PostgreSQL — read/write model results
 ├── Redis — task queue
 └── Model artifacts (local filesystem)

Celery Beat Scheduler
 └── Redis — schedule store
```

## Request Flow — Team Prediction

```
Client → FastAPI → validate JWT → check rate limit
                 → load match features (Redis hit? serve; miss? DB + cache)
                 → run ensemble (ML models + rules + form)
                 → run LP optimizer
                 → run LLM explainer (Redis hit? serve; miss? LLM API + cache)
                 → persist prediction to DB
                 → return JSON response
```
