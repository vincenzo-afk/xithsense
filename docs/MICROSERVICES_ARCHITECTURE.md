# Microservices Architecture

## Service Map

| Service | Responsibility | Tech |
|---------|---------------|------|
| `api` | REST + WebSocket gateway, auth, rate limiting | FastAPI |
| `worker` | Async tasks: ingestion, training, notifications | Celery |
| `scheduler` | Cron-style periodic tasks | Celery Beat |
| `redis` | Cache + message broker | Redis 7 |
| `qdrant` | Vector similarity (player embeddings, rule retrieval) | Qdrant 1.9 |
| `database` | All structured data | Supabase PostgreSQL 15 |

## Communication Patterns

- **Sync (request/response):** Client ↔ API over HTTPS/WebSocket
- **Async (fire-and-forget):** API enqueues Celery task → Worker processes
- **Cache read-through:** API checks Redis → on miss, queries PostgreSQL → writes back to Redis

## Celery Tasks

| Task | Queue | Trigger |
|------|-------|---------|
| `ingest_new_matches` | `data` | Daily cron 02:00 IST |
| `build_features_incremental` | `ml` | After ingestion completes |
| `retrain_models` | `ml` | Monthly cron or admin trigger |
| `run_backtest` | `ml` | Admin trigger |
| `send_notification` | `notifications` | Event-driven (toss, XI) |
| `generate_explanation` | `llm` | After prediction generated |

## Scaling Strategy

- API: horizontal scale behind load balancer (Railway/Render auto-scale)
- Workers: scale worker count with `--concurrency` flag
- Redis: single instance sufficient for MVP; upgrade to Redis Cluster at 10k DAU
- PostgreSQL: Supabase connection pooling (PgBouncer) handles concurrency
