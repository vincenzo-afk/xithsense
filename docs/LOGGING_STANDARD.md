# Logging Standard

**Library:** `structlog` 24.x  
**Format:** JSON (production), human-readable (development)  
**Output:** stdout → Railway/Render log drain → optional S3 archival

---

## Log Levels

| Level | Usage |
|-------|-------|
| `DEBUG` | Detailed flow info (feature vector shapes, SQL queries); dev only |
| `INFO` | Normal operations (prediction generated, user registered, match ingested) |
| `WARNING` | Degraded operation (fallback used, data quality issue, low confidence) |
| `ERROR` | Operation failed but service continues (LLM timeout, DB write failed) |
| `CRITICAL` | Service-level failure (DB down, all models unavailable) |

---

## Mandatory Fields

Every log entry must include:

| Field | Source | Example |
|-------|--------|---------|
| `timestamp` | structlog auto | `"2026-06-25T10:30:00.123Z"` |
| `level` | structlog auto | `"info"` |
| `logger` | `__name__` | `"backend.prediction"` |
| `event` | First positional arg | `"prediction_generated"` |
| `request_id` | Middleware inject | UUID string |

---

## Context-Specific Fields

### Prediction Events

```python
log.info("prediction_generated",
    match_id=match_id,
    mode=mode,
    player_count=len(players),
    solver_used=solver,
    duration_ms=elapsed,
    model_version_id=str(model_version_id),
    user_id=str(user.id),
    request_id=request_id,
)
```

### Ingestion Events

```python
log.info("match_ingested",
    match_id=match_id,
    match_type=match_type,
    delivery_count=delivery_count,
    duration_ms=elapsed,
)

log.error("ingestion_failed",
    file=filename,
    error=str(e),
    error_type=type(e).__name__,
)
```

### Rule Trigger Events

```python
log.info("rules_evaluated",
    match_id=match_id,
    player_key=player_key,
    rules_fired=rules_fired,
    total_adjustment=total_adjustment,
)
```

### Payment Events

```python
log.info("subscription_activated",
    user_id=str(user_id),
    plan=plan,
    razorpay_sub_id=razorpay_sub_id,
)
```

---

## Fields to NEVER Log

```python
NEVER_LOG = [
    "password", "password_hash",
    "access_token", "refresh_token",
    "api_key", "secret_key",
    "razorpay_key_secret",
    "card_number", "cvv",
    "otp",
]
```

The `structlog` processor chain includes a `drop_sensitive_fields` processor that removes these.

---

## structlog Configuration

```python
# backend/logging_config.py
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        drop_sensitive_fields,        # custom processor
        structlog.processors.JSONRenderer() if IS_PRODUCTION
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
```

---

## Request ID Propagation

Every incoming API request gets a UUID `request_id` injected by middleware:

```python
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

Users can provide this `X-Request-ID` when reporting issues for precise log lookup.
