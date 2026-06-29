# Retry Policy

## Principles

- Retry only **idempotent** or **safe** operations.
- Use **exponential backoff** with jitter to prevent thundering herd.
- Set **maximum retry counts** to avoid infinite loops.
- Log every retry attempt with attempt number and error.

---

## Per-Service Retry Configuration

| Service | Max Retries | Base Delay | Backoff | Jitter |
|---------|------------|-----------|---------|--------|
| PostgreSQL (transient) | 3 | 0.5s | ×2 | ±20% |
| Redis | 3 | 0.2s | ×2 | ±20% |
| Anthropic Claude | 2 | 1.0s | ×2 | ±30% |
| OpenAI | 2 | 1.0s | ×2 | ±30% |
| Razorpay API | 3 | 0.5s | ×2 | ±20% |
| Telegram Bot API | 2 | 2.0s | ×2 | ±20% |
| OpenWeatherMap | 2 | 1.0s | ×2 | ±20% |
| Cricsheet download | 5 | 5.0s | ×2 | ±30% |

---

## Retry Implementation

```python
# backend/utils/retry.py
import asyncio, random, functools
from typing import Callable, Type

def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.2,
    retry_on: tuple[Type[Exception], ...] = (Exception,),
    no_retry_on: tuple[Type[Exception], ...] = (),
):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except no_retry_on:
                    raise
                except retry_on as e:
                    if attempt == max_attempts:
                        log.error("max_retries_exceeded", func=func.__name__, error=str(e))
                        raise
                    jitter_amount = delay * jitter * (random.random() * 2 - 1)
                    sleep_time = delay + jitter_amount
                    log.warning("retry_attempt", func=func.__name__, attempt=attempt, delay=sleep_time)
                    await asyncio.sleep(sleep_time)
                    delay *= backoff_factor
        return wrapper
    return decorator

# Usage
@with_retry(max_attempts=2, base_delay=1.0, retry_on=(anthropic.APIError,),
            no_retry_on=(anthropic.AuthenticationError,))
async def call_claude(prompt: str) -> str:
    ...
```

---

## Celery Task Retry Policy

```python
# backend/worker.py

@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,          # Celery exponential backoff
    retry_backoff_max=300,       # Cap at 5 minutes
    retry_jitter=True,
)
def send_notification(self, user_id: str, event_id: str, message: str):
    ...

@app.task(
    bind=True,
    autoretry_for=(ExternalServiceError,),
    retry_kwargs={"max_retries": 5, "countdown": 60},
    # Retry after 1 min for external service errors only
)
def ingest_new_match(self, match_id: str):
    ...
```

---

## Do NOT Retry On

| Exception | Reason |
|-----------|--------|
| `AuthenticationError` | Wrong credentials; retry won't help |
| `ValidationError` | Bad input data; retry won't help |
| `RateLimitError` | Must wait; use exponential backoff, not immediate retry |
| `PaymentError (non-transient)` | Card declined; user action required |
| `IntegrityError (unique constraint)` | Duplicate insert; no retry needed |

---

## Dead Letter Queue (Celery)

Failed tasks that exhaust retries go to a dead letter queue:

```python
CELERY_TASK_ROUTES = {
    "notifications.*": {"queue": "notifications", "dead_letter_queue": "notifications_dlq"},
    "ml.*": {"queue": "ml", "dead_letter_queue": "ml_dlq"},
}
```

Admin reviews DLQ via Flower. Manual retry available via `celery task retry --id <task_id>`.
