"""
FastAPI shared dependencies: current user, plan gates, client info.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import cache_exists, revoked_token_key
from backend.database import get_db
from backend.models import Subscription, User
from backend.security import decode_token

security = HTTPBearer(auto_error=False)


def _unauth(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": code, "message": message})


async def user_from_token(token: str, db: AsyncSession) -> User:
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        raise _unauth("EXPIRED_TOKEN", "Token has expired")
    except JWTError:
        raise _unauth("INVALID_TOKEN", "Invalid token")
    if payload.get("type") == "refresh":
        raise _unauth("INVALID_TOKEN", "Refresh tokens cannot access the API")
    if await cache_exists(revoked_token_key(payload.get("jti", ""))):
        raise _unauth("REVOKED_TOKEN", "Token has been revoked")
    try:
        uid = uuid.UUID(payload.get("sub", ""))
    except ValueError:
        raise _unauth("INVALID_TOKEN", "Invalid token subject")
    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user or not user.is_active:
        raise _unauth("USER_NOT_FOUND", "User does not exist or is inactive")
    return user


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode JWT and return the authenticated User object."""
    if not credentials:
        raise _unauth("MISSING_TOKEN", "Authorization header required")
    user = await user_from_token(credentials.credentials, db)
    request.state.user = user
    return user


async def active_subscription(db: AsyncSession, user: User) -> Optional[Subscription]:
    subs = (await db.execute(select(Subscription).where(Subscription.user_id == user.id)
                             .order_by(Subscription.created_at.desc()))).scalars().all()
    return subs[0] if subs else None


async def has_premium_access(db: AsyncSession, user: User) -> bool:
    """SUBSCRIPTION_RULES check_premium_access: admin always; premium needs a live period."""
    if user.role == "admin":
        return True
    if user.role != "premium":
        return False
    sub = await active_subscription(db, user)
    if sub is None or sub.status not in ("active", "cancelled", "trial"):
        return False
    end = sub.current_period_end
    if end is None:
        return True
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return end > datetime.now(timezone.utc)


async def require_premium(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
    if not await has_premium_access(db, user):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "PREMIUM_REQUIRED", "message": "This feature requires a Premium subscription",
                    "details": {"upgrade_url": "/subscribe"}},
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "INSUFFICIENT_ROLE", "message": "Admin role required"},
        )
    return user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not credentials:
        return None
    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


def client_info(request: Request) -> tuple[str, str]:
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[-1].strip() if fwd else (request.client.host if request.client else "")
    return ip, request.headers.get("user-agent", "")[:300]
