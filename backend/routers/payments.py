"""
Payments router (PAYMENT_SPEC): Razorpay checkout, verification, webhook, status, cancel.

Without Razorpay keys checkout returns 503 PAYMENT_NOT_CONFIGURED; admins can still grant
Premium from the console.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.dependencies import active_subscription, get_current_user
from backend.models import ProcessedWebhook, Subscription, User
from backend.schemas import (
    CancelRequest, CreateSubscriptionRequest, CreateSubscriptionResponse, SubscriptionOut, VerifyPaymentRequest,
)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])
logger = logging.getLogger(__name__)

PLAN_AMOUNTS = {"premium_monthly": 29900, "premium_annual": 249900}   # paise
PLAN_DAYS = {"premium_monthly": 30, "premium_annual": 365}


def razorpay_configured() -> bool:
    k, s = settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET
    return bool(k and s and not k.endswith("...") and s != "...")


async def activate_premium(db: AsyncSession, user: User, plan: str, order_id: str | None = None,
                           sub_id: str | None = None) -> Subscription:
    now = datetime.now(timezone.utc)
    # One subscription row per user — upgrades/renewals update it (SUBSCRIPTION_RULES)
    sub = await active_subscription(db, user)
    if sub is None:
        sub = Subscription(user_id=user.id, plan=plan, status="active")
        db.add(sub)
    sub.plan, sub.status, sub.cancelled_at = plan, "active", None
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=PLAN_DAYS[plan])
    sub.amount_paise = PLAN_AMOUNTS[plan]
    sub.razorpay_order_id = order_id or sub.razorpay_order_id
    sub.razorpay_sub_id = sub_id or sub.razorpay_sub_id
    if user.role != "admin":
        user.role = "premium"
    await db.commit()
    return sub


@router.post("/create-subscription", response_model=CreateSubscriptionResponse)
async def create_subscription(body: CreateSubscriptionRequest, db: AsyncSession = Depends(get_db),
                              user: User = Depends(get_current_user)):
    amount = PLAN_AMOUNTS[body.plan]
    if razorpay_configured():
        try:
            import razorpay  # type: ignore
        except ImportError:
            raise HTTPException(status_code=503, detail={"code": "PAYMENT_ERROR", "message": "Razorpay SDK not installed"})
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order = client.order.create({"amount": amount, "currency": "INR", "receipt": f"xs_{str(user.id)[:8]}_{body.plan}",
                                     "notes": {"user_id": str(user.id), "plan": body.plan}})
        return CreateSubscriptionResponse(order_id=order["id"], razorpay_key_id=settings.RAZORPAY_KEY_ID,
                                          amount=amount, plan=body.plan, checkout_mode="razorpay")
    raise HTTPException(status_code=503, detail={"code": "PAYMENT_NOT_CONFIGURED", "message": "Payment gateway not configured"})


@router.post("/verify", response_model=SubscriptionOut)
async def verify_payment(body: VerifyPaymentRequest, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user)):
    """Called by the frontend after checkout succeeds."""
    if not razorpay_configured():
        raise HTTPException(status_code=503, detail={"code": "PAYMENT_NOT_CONFIGURED", "message": "Payment gateway not configured"})
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f"{body.order_id}|{body.payment_id}".encode(),
                        hashlib.sha256).hexdigest()
    if not body.signature or not hmac.compare_digest(expected, body.signature):
        raise HTTPException(status_code=400, detail={"code": "PAYMENT_VERIFICATION_FAILED",
                                                     "message": "Payment signature mismatch"})
    sub = await activate_premium(db, user, body.plan, order_id=body.order_id)
    return SubscriptionOut.model_validate(sub)


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Razorpay events: payment.captured / failed, subscription.charged / cancelled / completed."""
    raw = await request.body()
    if not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail={"code": "PAYMENT_NOT_CONFIGURED", "message": "Webhook secret not set"})
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Razorpay-Signature", "")):
        raise HTTPException(status_code=400, detail={"code": "INVALID_SIGNATURE", "message": "Invalid webhook signature"})

    payload = json.loads(raw)
    event = payload.get("event", "")
    entity = (payload.get("payload", {}).get("payment") or payload.get("payload", {}).get("subscription") or {}).get("entity", {})
    event_id = payload.get("id") or f"{event}:{entity.get('id')}"
    if await db.get(ProcessedWebhook, event_id):
        return {"status": "already_processed"}

    notes = entity.get("notes") or {}
    user = None
    if notes.get("user_id"):
        user = await db.get(User, uuid.UUID(notes["user_id"]))
    elif entity.get("email"):
        user = (await db.execute(select(User).where(User.email == entity["email"]))).scalar_one_or_none()

    if event == "payment.captured" and user and notes.get("plan") in PLAN_AMOUNTS:
        await activate_premium(db, user, notes["plan"], order_id=entity.get("order_id"))
    elif event == "subscription.charged" and user:
        sub = await active_subscription(db, user)
        if sub:
            if entity.get("current_start"):
                sub.current_period_start = datetime.fromtimestamp(entity["current_start"], timezone.utc)
            if entity.get("current_end"):
                sub.current_period_end = datetime.fromtimestamp(entity["current_end"], timezone.utc)
            sub.status = "active"
    elif event == "subscription.cancelled" and user:
        sub = await active_subscription(db, user)
        if sub:
            sub.status, sub.cancelled_at = "cancelled", datetime.now(timezone.utc)
    elif event == "subscription.completed" and user:
        sub = await active_subscription(db, user)
        if sub:
            sub.status = "expired"
        if user.role == "premium":
            user.role = "free"
    elif event == "payment.failed":
        logger.warning("Payment failed for %s", notes.get("user_id") or entity.get("email"))

    db.add(ProcessedWebhook(event_id=event_id, event_type=event))
    await db.commit()
    return {"status": "ok"}


@router.get("/status", response_model=SubscriptionOut)
async def payment_status(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    sub = await active_subscription(db, user)
    if not sub:
        return SubscriptionOut(plan="free", status="active")
    return SubscriptionOut.model_validate(sub)


@router.post("/cancel", response_model=SubscriptionOut)
async def cancel_subscription(body: CancelRequest, db: AsyncSession = Depends(get_db),
                              user: User = Depends(get_current_user)):
    sub = await active_subscription(db, user)
    if not sub or sub.plan == "free" or sub.status != "active":
        raise HTTPException(status_code=402, detail={"code": "NO_ACTIVE_SUBSCRIPTION", "message": "No active subscription"})
    if razorpay_configured() and sub.razorpay_sub_id:
        try:
            import razorpay  # type: ignore
            razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)).subscription.cancel(sub.razorpay_sub_id)
        except Exception as e:
            logger.error("Razorpay cancel failed: %s", e)
    sub.status, sub.cancelled_at = "cancelled", datetime.now(timezone.utc)   # premium kept until period end
    await db.commit()
    return SubscriptionOut.model_validate(sub)
