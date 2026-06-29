# Monitoring Specification

## Observability Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Error tracking | Sentry | Exceptions, stack traces, release tracking |
| Metrics | Prometheus + Grafana | API latency, cache hit rate, queue depth |
| Logs | Structlog → stdout → Railway log drain | Structured JSON logs |
| Uptime | UptimeRobot / BetterUptime | `/health` check every 60s |
| ML accuracy | Custom dashboard (admin API) | Captain accuracy, CPR tracking |

## Key Metrics to Track

### API Metrics (Prometheus)

```python
# Instrument with prometheus_client
api_request_duration = Histogram(
    "api_request_duration_seconds",
    "Request latency",
    ["method", "endpoint", "status_code"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

prediction_generation_time = Histogram(
    "prediction_generation_seconds",
    "Team prediction generation time",
    ["mode", "solver"]
)

cache_hit_rate = Counter("cache_hits_total", "Redis cache hits", ["cache_type"])
cache_miss_rate = Counter("cache_misses_total", "Redis cache misses", ["cache_type"])
```

### Business Metrics

- Active premium users (daily)
- Predictions generated per hour
- Chat messages per hour
- Notifications delivered vs failed

## Alerting Rules

| Alert | Condition | Severity | Action |
|-------|-----------|---------|--------|
| High error rate | 5xx > 2% for 5 min | Critical | Page on-call |
| Slow API | p95 > 2s for 10 min | Warning | Investigate |
| Redis down | Health check fail | Critical | Page on-call |
| DB connection pool exhausted | Pool > 90% for 5 min | Warning | Scale DB |
| Celery queue backed up | Queue depth > 500 | Warning | Scale workers |
| Model accuracy drop | Captain accuracy < 35% over 50 matches | Warning | Notify ML team |
| Disk space | > 80% full | Warning | Clean old artifacts |

## Log Format

All logs are structured JSON via structlog:

```json
{
  "timestamp": "2026-06-25T10:30:00.123Z",
  "level": "info",
  "logger": "backend.prediction",
  "event": "prediction_generated",
  "match_id": "1535465",
  "mode": "grand_league",
  "duration_ms": 342,
  "player_count": 22,
  "solver": "lp",
  "request_id": "uuid",
  "user_id": "uuid"
}
```

Never log: passwords, API keys, JWT tokens, user emails, payment card numbers.

## Health Check Endpoint

`GET /health` checks:
1. Database connection: `SELECT 1`
2. Redis connection: `PING`
3. Active model exists for at least T20 format
4. Returns 200 if all pass, 503 if any fail

```json
{
  "status": "ok",
  "version": "0.5.0",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "models": "ok"
  },
  "timestamp": "2026-06-25T10:00:00Z"
}
```
