# Failure Scenarios

## Scenario Matrix

| ID | Failure | Probability | Severity | Detection | Recovery |
|----|---------|------------|---------|-----------|---------|
| FS-01 | PostgreSQL unavailable | Low | Critical | `/health` check fails; Sentry alert | Redis cache serves recent predictions; alert on-call |
| FS-02 | Redis unavailable | Low | High | Connection error on first request | Degrade gracefully: skip cache, query DB directly; alert |
| FS-03 | Qdrant unavailable | Low | Medium | Health check; rule retrieval timeout | Disable vector-based rule lookup; use file-based rules only |
| FS-04 | LLM API down (all providers) | Medium | Medium | HTTP 5xx from LLM endpoint | Fallback template explanations; no impact on team selection |
| FS-05 | Celery worker crash | Medium | High | Task queue grows; Flower alert | Auto-restart via Docker; tasks requeued |
| FS-06 | Model artifact missing/corrupted | Low | Critical | `ModelNotFoundError` on prediction | Fall back to previous version; alert admin |
| FS-07 | Feature store stale (>12h) | Low | Medium | Staleness check in health | Alert admin; serve stale features with staleness warning |
| FS-08 | Razorpay webhook delivery fails | Low | High | No `subscription.status` update | Reconcile job runs hourly; manual retry via admin API |
| FS-09 | Ingestion pipeline fails mid-run | Medium | Low | Error log; Celery failure alert | Idempotent retry; already-processed files skipped |
| FS-10 | LP optimizer timeout (>10s) | Low | Medium | Solver timeout flag | DEAP genetic algorithm fallback activates automatically |
| FS-11 | Disk full (model artifacts) | Low | High | Disk usage alert > 80% | Auto-delete models older than 5 versions; alert admin |
| FS-12 | Memory exhaustion (OOM) | Low | Critical | Container OOM kill | Auto-restart; increase memory limit; profile memory leak |
| FS-13 | Playing XI not confirmed at match time | Medium | Low | `playing_xi_confirmed=false` flag | Use last-known XI; add warning banner in response |
| FS-14 | Cricsheet data format version change | Low | High | Schema validation failures in ingestion | Fail loud; notify team; update parser before resuming |

---

## Graceful Degradation Order

When components fail, XithSense degrades in this priority order:

```
Full Features
    │
    │ LLM unavailable
    ▼
Template explanations (no AI, same predictions)
    │
    │ Redis unavailable
    ▼
No caching (slower responses, higher DB load)
    │
    │ Qdrant unavailable
    ▼
File-based rules only (no vector similarity)
    │
    │ Model unavailable
    ▼
Form-only predictions (no ML, rules + form only)
    │
    │ Database unavailable
    ▼
Cached responses from Redis only (read-only mode)
    │
    │ All services down
    ▼
Maintenance page with ETA
```

---

## On-Call Runbook: Database Down

```bash
# 1. Check if Supabase is the issue
curl https://status.supabase.com

# 2. Check connection pool
docker compose exec api python -c "from backend.db import engine; print(engine.pool.status())"

# 3. Check if it's just the connection string
docker compose exec api alembic current

# 4. Restart API (clears connection pool)
docker compose restart api

# 5. If Supabase outage: switch to read-only Redis mode
# Set ENV var: READONLY_MODE=true
# API will serve cached predictions; reject writes with 503
```

---

## On-Call Runbook: Prediction Quality Degraded

```bash
# 1. Check recent captain accuracy
curl -H "Authorization: Bearer $ADMIN_JWT" \
  https://api.xithsense.com/api/v1/admin/metrics | jq .captain_accuracy_30d

# 2. If below 35%, check model versions
curl .../api/v1/admin/models | jq '.[] | select(.is_active==true)'

# 3. Trigger retraining with latest data
curl -X POST .../api/v1/admin/retrain -d '{"format":"T20"}'

# 4. Monitor retrain progress in Flower
open http://localhost:5555
```
