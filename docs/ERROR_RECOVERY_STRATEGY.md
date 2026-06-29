# Error Recovery Strategy

Defines how XithSense detects, handles, and recovers from every failure type.

---

## Recovery Tiers

| Tier | Response Time | Automation | Example |
|------|--------------|-----------|---------|
| T1 — Instant | < 5 seconds | Fully automatic | LLM fallback to template |
| T2 — Fast | < 2 minutes | Automatic + alert | Redis reconnect, container restart |
| T3 — Managed | < 30 minutes | Manual with runbook | DB restore, model rollback |
| T4 — Extended | < 4 hours | Full team response | Full infrastructure rebuild |

---

## Per-Component Recovery

### API Server Down

```
Detection: UptimeRobot /health check fails
           Sentry uptime alert fires

T1 Actions:
  Docker: auto-restart (restart: unless-stopped)
  Railway: auto-restart policy

T2 Actions (if restart fails):
  Alert on-call engineer
  Check container logs: docker compose logs api --tail=100
  Check disk space: df -h
  Check memory: docker stats

T3 Actions (if T2 fails):
  Full redeploy from clean image
  Verify DB and Redis are healthy first
  Scale down → restart → scale up
```

---

### PostgreSQL Unavailable

```
Detection: /health returns DB check=fail
           SQLAlchemy connection error logged

T1 Actions:
  API switches to Redis read-only mode
  Serve cached predictions from Redis
  Block write operations (return 503 for non-cached requests)

T2 Actions:
  Check Supabase status page
  Check connection pool: docker exec api python -c "from backend.db import engine; print(engine.pool.status())"
  Restart API to clear stale connections

T3 Actions (if Supabase outage):
  Post status to users: "Predictions temporarily limited"
  Wait for Supabase SLA restoration (99.9% uptime)
  Run reconciliation job after restoration
```

---

### Redis Cache Down

```
Detection: redis-cli ping fails; connection error in logs

T1 Actions:
  All cache reads bypass Redis (DB fallback)
  Write operations skip cache
  Log degraded_mode=true for all predictions

T2 Actions:
  Docker restart Redis container
  Check Redis logs for OOM or config errors
  docker compose restart redis

Recovery:
  Cache auto-repopulates over 30–60 min as requests come in
  OR: run scripts/warm_cache.py --hours-ahead 12 to pre-warm
```

---

### LLM API (All Providers Down)

```
Detection: anthropic.APIError, openai.APIError, 3 consecutive failures

T1 Actions (immediate, automatic):
  Switch to fallback template explanation
  Log llm_unavailable=true on all predicted_player records
  Never block team generation — templates used instead

T2 Actions:
  Try secondary LLM provider:
    LLM_PROVIDER=anthropic fails → try openai → try google
  Alert admin if all 3 providers fail

User impact: explanations are less detailed; team quality unaffected
```

---

### ML Model Not Found / Corrupt

```
Detection: FileNotFoundError or pickle.UnpicklingError on model load

T1 Actions:
  Fall back to form-only prediction:
    ensemble_weights = {ml: 0, rules: 0.50, form: 0.40, live: 0.10}
  Log model_unavailable=true; confidence scores reduced by 20%
  Alert admin immediately

T2 Actions:
  Restore from S3: aws s3 cp s3://xithsense-models/m01_t20_*.pkl models/artifacts/
  Verify restored model: python training/verify_model.py --model m01_t20_20260601.pkl

T3 Actions (if restore fails):
  Emergency retrain on subset (last 2 years only): make train-t20
  ETA: ~2 hours
```

---

### LP Optimizer Infeasible

```
Detection: pulp.LpStatus == "Infeasible" after 10-second timeout

T1 Actions (automatic):
  Fall back to DEAP genetic algorithm
  Log solver_fallback=deap

T2 Actions (if DEAP also fails):
  Relax constraint: increase MAX_PLAYERS_PER_TEAM from 7 to 8
  Re-run LP
  Log constraint_relaxed=true in response

T3 Actions (if still infeasible):
  Return 400 OPTIMIZER_INFEASIBLE to user
  Log full player list and credits for debugging
```

---

### Celery Worker Crash

```
Detection: Flower shows 0 active workers; task queue depth grows

T1 Actions:
  Docker auto-restart worker container
  Tasks remain in Redis queue; processed when worker restarts

T2 Actions (if auto-restart fails):
  Manually restart: docker compose restart worker
  Check worker logs: docker compose logs worker --tail=200

Alert thresholds:
  Queue depth > 500 → WARNING
  Queue depth > 2000 → CRITICAL (data loss risk for TTL tasks)
```

---

## Graceful Degradation Matrix

| Service Down | User Impact | System Response |
|---|---|---|
| LLM | Template explanations (no quality loss) | T1 automatic |
| Redis | Slower responses (~3× slower) | T1 cache bypass |
| Qdrant | No vector rules (file rules still apply) | T1 fallback |
| ML model | Form-only predictions (lower accuracy) | T1 fallback + alert |
| LP solver | DEAP fallback (slower teams) | T1 automatic |
| PostgreSQL | Read-only from cache | T2 manual |
| All infra | Maintenance page | T4 |
