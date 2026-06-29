"""
Payments router: Razorpay subscription creation and webhook handling
"""
from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import Subscription, User
from backend.schemas import CreateSubscriptionRequest, CreateSubscriptionResponse

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

PLAN_AMOUNTS = {
    "premium_monthly": 29900,   # ₹299 in paise
    "premium_annual": 249900,   # ₹2499 in paise
}


@router.post("/create-subscription", response_model=CreateSubscriptionResponse)
async def create_subscription(
    body: CreateSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail={"code": "PAYMENT_NOT_CONFIGURED", "message": "Payment gateway not configured"})

    try:
        import razorpay
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order = client.order.create({
            "amount": PLAN_AMOUNTS[body.plan],
            "currency": "INR",
            "receipt": f"xs_{user.id}_{body.plan}",
        })
        return CreateSubscriptionResponse(
            order_id=order["id"],
            razorpay_key_id=settings.RAZORPAY_KEY_ID,
            amount=PLAN_AMOUNTS[body.plan],
            plan=body.plan,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail={"code": "PAYMENT_ERROR", "message": "Razorpay not installed"})


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Razorpay payment events: captured, failed, subscription events."""
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")

    if settings.RAZORPAY_KEY_SECRET:
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    payload = json.loads(body)
    event = payload.get("event", "")

    if event == "payment.captured":
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        notes = payment.get("notes", {})
        user_id = notes.get("user_id")
        plan = notes.get("plan")
        if user_id and plan:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.role = "premium"
                sub = Subscription(user_id=user.id, plan=plan, status="active")
                db.add(sub)
                await db.commit()

    return {"status": "ok"}
