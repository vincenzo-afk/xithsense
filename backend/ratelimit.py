"""
Rate limiting (RATE_LIMITING_POLICY / RATE_LIMIT_RULES).

Global per-user RPM by plan (free 30, premium 300, admin 1000) plus per-IP limits
on register/login. Fixed one-minute windows; Redis when available, otherwise an
in-process counter. Emits X-RateLimit-* headers and 429 RATE_LIMIT_EXCEEDED.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import settings
from backend.security import decode_token

PLAN_RPM = {"free": settings.RATE_LIMIT_FREE_RPM, "premium": settings.RATE_LIMIT_PREMIUM_RPM,
            "admin": settings.RATE_LIMIT_ADMIN_RPM}
BURST = {"free": 5, "premium": 20, "admin": 50}
IP_RULES = {  # path -> (limit, window seconds)
    "/api/v1/auth/register": (5, 3600),
    "/api/v1/auth/login": (10, 900),
}
EXEMPT_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json", "/api/v1/payments/webhook", "/api/v1/live")


class _Counter:
    def __init__(self):
        self.buckets: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))

    async def hit(self, key: str, window: int) -> Tuple[int, int]:
        """Increment and return (count, reset_epoch)."""
        from backend.cache import get_redis, MockRedis
        r = await get_redis()
        now = time.time()
        bucket = int(now // window)
        reset = (bucket + 1) * window
        full = f"rate:{key}:{bucket}"
        if not isinstance(r, MockRedis):
            try:
                n = await r.incr(full)
                if n == 1:
                    await r.expire(full, window)
                return int(n), reset
            except Exception:
                pass
        count, exp = self.buckets[full]
        if exp < now:
            count = 0
        self.buckets[full] = (count + 1, reset)
        if len(self.buckets) > 50_000:
            self.buckets = defaultdict(lambda: (0, 0.0), {k: v for k, v in self.buckets.items() if v[1] > now})
        return count + 1, reset


counter = _Counter()


def _identity(request: Request) -> Tuple[Optional[str], str]:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            p = decode_token(auth[7:])
            return p.get("sub"), p.get("role", "free")
        except JWTError:
            pass
    return None, "free"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not settings.RATE_LIMIT_ENABLED or not path.startswith("/api/") or path.startswith(EXEMPT_PREFIXES):
            return await call_next(request)
        ip = request.client.host if request.client else "?"
        if path in IP_RULES and request.method == "POST":
            limit, window = IP_RULES[path]
            n, reset = await counter.hit(f"ip:{ip}:{path}", window)
            if n > limit:
                return self._reject(limit, reset, "ip-" + path.rsplit("/", 1)[-1], "anonymous")

        uid, role = _identity(request)
        key = f"user:{uid}" if uid else f"anon:{ip}"
        limit = PLAN_RPM.get(role, PLAN_RPM["free"])
        n, reset = await counter.hit(key, 60)
        if n > limit + BURST.get(role, 0):
            return self._reject(limit, reset, f"{role}-global-rpm", role)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - n))
        response.headers["X-RateLimit-Reset"] = str(reset)
        response.headers["X-RateLimit-Policy"] = f"{role}-global-rpm"
        return response

    @staticmethod
    def _reject(limit: int, reset: int, policy: str, plan: str) -> JSONResponse:
        retry = max(1, int(reset - time.time()))
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests — slow down a little",
                               "details": {"retry_after_seconds": retry, "limit": limit, "plan": plan}}},
            headers={"Retry-After": str(retry), "X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": "0",
                     "X-RateLimit-Reset": str(reset), "X-RateLimit-Policy": policy},
        )
