# Observability Specification

**Stack:** Sentry (errors) · Prometheus + Grafana (metrics) · Structlog (logs) · UptimeRobot (uptime)

---

## The Three Pillars

### 1. Logs (Structlog → JSON)

Every log entry has: `timestamp`, `level`, `logger`, `event`, `request_id`.  
Production logs shipped to Railway log drain → optional S3 archival.

**Key log events:**
```
prediction_generated     match_id, mode, duration_ms, solver, player_count
prediction_cache_hit     match_id, mode
rule_fired               rule_id, player_key, impact, effective_impact
llm_called               provider, tokens_used, duration_ms, cached
llm_fallback             reason (timeout/error)
ingestion_complete       files_processed, files_failed, duration_s
model_loaded             model_id, format, is_active
payment_webhook          event_type, sub_id, status
rate_limit_exceeded      user_id, plan, rpm_used
```

**Never log:** passwords, tokens, API keys, card numbers, raw SQL.

---

### 2. Metrics (Prometheus)

```python
# backend/metrics.py
from prometheus_client import Histogram, Counter, Gauge, Summary

# API Latency
api_latency = Histogram(
    "xithsense_api_request_duration_seconds",
    "Request latency by endpoint",
    ["method", "route", "status_code"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Prediction metrics
prediction_duration = Histogram(
    "xithsense_prediction_duration_seconds",
    "Team generation duration",
    ["mode", "solver"]
)

# Cache metrics
cache_hits   = Counter("xithsense_cache_hits_total",   "Cache hits",   ["type"])
cache_misses = Counter("xithsense_cache_misses_total", "Cache misses", ["type"])

# LLM metrics
llm_calls    = Counter("xithsense_llm_calls_total",    "LLM API calls",     ["provider"])
llm_fallback = Counter("xithsense_llm_fallbacks_total","LLM fallback count", ["reason"])
llm_tokens   = Summary("xithsense_llm_tokens",         "Tokens used",       ["provider"])

# Business metrics
active_premium_users  = Gauge("xithsense_premium_users",   "Current premium users")
predictions_per_hour  = Counter("xithsense_predictions_total", "Predictions", ["mode"])
captain_accuracy_gauge = Gauge("xithsense_captain_accuracy", "30-day captain accuracy")
```

---

### 3. Tracing (Request ID)

Every request has `X-Request-ID` header (UUID). Propagated through:
- API middleware → structlog context
- Celery tasks: passed as kwarg `_request_id`
- LLM calls: added to metadata
- DB queries: available via SQLAlchemy event hooks

Users can include `X-Request-ID` in bug reports for exact log lookup.

---

## Grafana Dashboards

### Dashboard 1: API Health
- Request rate (RPM) by endpoint
- Error rate (5xx %)
- P50 / P95 / P99 latency
- Active WebSocket connections
- Rate limit hit rate

### Dashboard 2: ML Quality
- Rolling captain accuracy (last 7 days)
- Correct player rate (last 7 days)
- Prediction generation time
- Cache hit rate by type
- LLM fallback rate

### Dashboard 3: Infrastructure
- Redis memory usage %
- Redis hit rate
- Celery queue depths
- PostgreSQL connection pool utilisation
- Disk usage (model artifacts)

### Dashboard 4: Business
- Daily active users
- Predictions per hour (chart vs IPL schedule)
- Free → Premium conversions
- Subscription churn rate

---

## Alert Rules

| Alert | Condition | Severity | Notification |
|-------|-----------|---------|-------------|
| API Down | /health fails for 2 min | Critical | PagerDuty + Telegram |
| High Error Rate | 5xx > 2% for 5 min | Critical | PagerDuty |
| Slow API | P95 > 2s for 10 min | Warning | Telegram |
| Redis OOM | Memory > 85% | Warning | Telegram |
| DB Pool Exhausted | Pool > 90% for 5 min | Warning | Telegram |
| Queue Backed Up | Queue depth > 500 | Warning | Telegram |
| Accuracy Drop | Captain acc < 35% over 50 matches | Warning | Email to admin |
| LLM Outage | All providers failing for 3 min | Warning | Telegram |
| Disk Full | > 80% on any volume | Warning | Telegram |

---

## Health Check Details

`GET /health` verifies and returns:

```python
async def health_check():
    checks = {}

    # Database
    try:
        await db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "fail"

    # Redis
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "fail"

    # Active ML model
    try:
        active_model = model_registry.get_active("T20")
        checks["models"] = "ok" if active_model else "no_active_model"
    except Exception:
        checks["models"] = "fail"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks,
                 "version": settings.VERSION,
                 "timestamp": datetime.utcnow().isoformat()}
    )
```
