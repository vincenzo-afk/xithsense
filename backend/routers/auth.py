"""
Auth router: register, login, refresh, logout, me, profile, password.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import cache_exists, cache_set, revoked_token_key
from backend.database import get_db
from backend.dependencies import active_subscription, get_current_user, security
from backend.models import Subscription, User
from backend.schemas import (
    ChangePasswordRequest, LoginRequest, RefreshRequest, RegisterRequest, SubscriptionOut,
    TokenResponse, UpdateProfileRequest, UserOut,
)
from backend.security import (
    create_access_token, create_refresh_token, decode_token, hash_password, verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def user_out(db: AsyncSession, user: User) -> UserOut:
    sub = await active_subscription(db, user)
    out = UserOut.model_validate(user)
    out.subscription = SubscriptionOut.model_validate(sub) if sub else None
    return out


async def _tokens(db: AsyncSession, user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role, user.email),
        refresh_token=create_refresh_token(str(user.id)),
        user=await user_out(db, user),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"code": "EMAIL_TAKEN", "message": "Email already registered"})
    user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name,
                role="free", is_active=True, is_verified=False,
                notification_prefs={"email_enabled": True, "telegram_enabled": False, "push_enabled": False,
                                    "events": {"EVT-01": True, "EVT-02": True, "EVT-03": True}})
    db.add(user)
    db.add(Subscription(user=user, plan="free", status="active", current_period_start=datetime.now(timezone.utc)))
    await db.commit()
    await db.refresh(user)
    return await _tokens(db, user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail={"code": "ACCOUNT_DISABLED", "message": "Account is disabled"})
    user.last_login_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return await _tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "Invalid refresh token"})
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "Not a refresh token"})
    if await cache_exists(revoked_token_key(payload.get("jti", ""))):
        raise HTTPException(status_code=401, detail={"code": "REVOKED_TOKEN", "message": "Refresh token revoked"})
    user = (await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": "USER_NOT_FOUND", "message": "User not found"})
    # Rotate: the presented refresh token is single-use
    await cache_set(revoked_token_key(payload["jti"]), 1, ttl=max(60, int(payload["exp"] - time.time())))
    return await _tokens(db, user)


@router.post("/logout", status_code=204)
async def logout(body: RefreshRequest | None = None,
                 credentials: HTTPAuthorizationCredentials = Depends(security)):
    for tok in filter(None, [credentials.credentials if credentials else None, body.refresh_token if body else None]):
        try:
            p = decode_token(tok)
            await cache_set(revoked_token_key(p["jti"]), 1, ttl=max(60, int(p["exp"] - time.time())))
        except JWTError:
            pass


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await user_out(db, user)


@router.patch("/me", response_model=UserOut)
async def update_me(body: UpdateProfileRequest, user: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return await user_out(db, user)


@router.post("/change-password", status_code=204)
async def change_password(body: ChangePasswordRequest, user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    if not user.password_hash or not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail={"code": "INVALID_CREDENTIALS", "message": "Current password is incorrect"})
    user.password_hash = hash_password(body.new_password)
    await db.commit()
