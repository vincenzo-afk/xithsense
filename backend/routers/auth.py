"""
Auth router: register, login, refresh, me
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import User, Subscription
from backend.schemas import (
    LoginRequest, RegisterRequest, RefreshRequest,
    TokenResponse, UserOut,
)
from backend.security import (
    create_access_token, create_refresh_token,
    decode_token, hash_password, verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"code": "EMAIL_TAKEN", "message": "Email already registered"})

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="free",
        is_active=True,
        is_verified=False,
    )
    db.add(user)

    # Create free subscription record
    sub = Subscription(user=user, plan="free", status="active")
    db.add(sub)

    await db.commit()
    await db.refresh(user)

    access = create_access_token(str(user.id), user.role, user.email)
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail={"code": "ACCOUNT_DISABLED", "message": "Account is disabled"})

    user.last_login_at = datetime.now(tz=timezone.utc)
    await db.commit()

    access = create_access_token(str(user.id), user.role, user.email)
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "Invalid refresh token"})
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "Not a refresh token"})

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": "USER_NOT_FOUND", "message": "User not found"})

    access = create_access_token(str(user.id), user.role, user.email)
    new_refresh = create_refresh_token(str(user.id))
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)
