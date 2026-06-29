# Rate Limiting Policy

**Implementation:** Redis sliding-window counter · **Header prefix:** `X-RateLimit-`

---

## Limits by Plan

| Plan | Global RPM | Burst (extra) | Per-Endpoint Overrides |
|------|-----------|--------------|----------------------|
| Free | 30 | +5 | See endpoint table below |
| Premium | 300 | +20 | See endpoint table below |
| Admin | 1,000 | +50 | No per-endpoint limits |

---

## Per-Endpoint Limits (Override Global)

| Endpoint | Free | Premium | Window |
|----------|------|---------|--------|
| `POST /auth/register` | 5 per IP/hour | 5 per IP/hour | 60 min |
| `POST /auth/login` | 10 per IP/15 min | 10 per IP/15 min | 15 min |
| `POST /predict/team` | 3 per match | Unlimited | Per match |
| `POST /predict/team/portfolio` | ❌ Not allowed | 5 per match | Per match |
| `POST /chat` | ❌ Not allowed | 20 per match | Per match |
| `GET /explain/:match/:player` | 5 per match | Unlimited | Per match |
| `POST /admin/retrain` | ❌ Not allowed | ❌ Not allowed | — |
| `POST /admin/ingest` | ❌ Not allowed | ❌ Not allowed | — |

---

## Response Headers

Every response includes:

```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 17
X-RateLimit-Reset: 1750831260
X-RateLimit-Policy: free-global-rpm
```

On 429:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 43
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1750831260
```

---

## Implementation

```python
# backend/middleware/rate_limiter.py

class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check(self, user_id: str, plan: str, endpoint: str) -> RateLimitResult:
        # 1. Check endpoint-specific limit
        ep_limit = ENDPOINT_LIMITS.get(endpoint, {}).get(plan)
        if ep_limit:
            ep_key = f"rate:ep:{user_id}:{endpoint}:{current_match_bucket()}"
            ep_count = await self.redis.incr(ep_key)
            await self.redis.expire(ep_key, ep_limit.window_seconds)
            if ep_count > ep_limit.max:
                return RateLimitResult(
                    allowed=False,
                    limit=ep_limit.max,
                    remaining=0,
                    reset_at=current_match_bucket() + ep_limit.window_seconds
                )

        # 2. Check global per-minute limit
        global_limit = PLAN_LIMITS[plan].rpm
        bucket = int(time.time() / 60)
        global_key = f"rate:{user_id}:{bucket}"
        count = await self.redis.incr(global_key)
        await self.redis.expire(global_key, 60)

        remaining = max(0, global_limit - count)
        reset_at = (bucket + 1) * 60

        if count > global_limit + PLAN_LIMITS[plan].burst:
            return RateLimitResult(False, global_limit, 0, reset_at)

        return RateLimitResult(True, global_limit, remaining, reset_at)
```

---

## IP-Based Rate Limiting (Unauthenticated Endpoints)

For `/auth/register`, `/auth/login`, and `/health`:

```python
# Rate limit by IP + endpoint combination
ip_key = f"rate:ip:{client_ip}:{endpoint}:{hour_bucket}"
```

X-Forwarded-For header used behind proxy; validate and take last non-private IP.

---

## Rate Limit Bypass Rules

1. **Admin users** are exempt from all per-minute rate limits.
2. **Health endpoint** is never rate-limited.
3. **Webhook endpoints** (`/api/v1/payments/webhook`) are never rate-limited but are IP-filtered to Razorpay's IP ranges.

---

## Rate Limit Escalation Policy

If a user consistently hits rate limits:
1. Log pattern to `admin_action` table
2. Flag account for admin review after 5 429s in 1 hour
3. Admin can increase per-user limits via `PATCH /api/v1/admin/users/:id/rate-limit`
4. Suspected abuse (automated scraping) → suspend account pending review
