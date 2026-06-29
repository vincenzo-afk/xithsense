# Rate Limit Rules

## Limits by Plan

| Plan | Requests per minute | Burst allowance |
|------|-------------------|----------------|
| Free | 30 | 5 additional requests |
| Premium | 300 | 20 additional requests |
| Admin | 1000 | 50 additional requests |

## Limits by Endpoint

Some endpoints have stricter limits regardless of plan:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /api/v1/auth/register` | 5 | per IP per hour |
| `POST /api/v1/auth/login` | 10 | per IP per 15 minutes |
| `POST /api/v1/predict/team` (Free) | 3 | per user per match |
| `POST /api/v1/chat` (Free) | 5 messages | per user per match |
| `POST /api/v1/admin/retrain` | 2 | per admin per hour |

## Headers Returned

Every response includes:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1719309600
Retry-After: 45   (only on 429 responses)
```

## Implementation

Rate limiting implemented via Redis with sliding window algorithm:

```python
key = f"rate:{user_id}:{minute_bucket}"
count = redis.incr(key)
redis.expire(key, 60)
if count > limit: raise RateLimitExceeded()
```

## IP-Based Fallback

For unauthenticated endpoints (auth routes), rate limiting is applied by client IP address.
