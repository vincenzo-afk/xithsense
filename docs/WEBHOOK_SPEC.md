# Webhook Specification

## Incoming Webhooks (XithSense Receives)

### Razorpay Webhook

**Endpoint:** `POST /api/v1/payments/webhook`  
**Auth:** HMAC-SHA256 signature in `X-Razorpay-Signature` header  
**Content-Type:** `application/json`

#### Supported Events

**`payment.captured`**
```json
{
  "event": "payment.captured",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_OexamplePayment01",
        "amount": 29900,
        "currency": "INR",
        "status": "captured",
        "subscription_id": "sub_OexampleRazorpay01",
        "email": "user@example.com",
        "contact": "+919999999999",
        "created_at": 1750830000
      }
    }
  }
}
```

**`subscription.charged`**
```json
{
  "event": "subscription.charged",
  "payload": {
    "subscription": {
      "entity": {
        "id": "sub_OexampleRazorpay01",
        "plan_id": "plan_monthly_299",
        "status": "active",
        "current_start": 1750830000,
        "current_end": 1753508400
      }
    }
  }
}
```

**`subscription.cancelled`**
```json
{
  "event": "subscription.cancelled",
  "payload": {
    "subscription": {
      "entity": {
        "id": "sub_OexampleRazorpay01",
        "status": "cancelled",
        "ended_at": 1753508400
      }
    }
  }
}
```

#### Webhook Handler Logic

```python
@router.post("/api/v1/payments/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(...),
):
    body = await request.body()

    # 1. Verify signature
    if not verify_razorpay_webhook(body, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 2. Parse event
    payload = json.loads(body)
    event = payload["event"]

    # 3. Idempotency: check if already processed
    event_id = payload.get("id") or payload["payload"]["payment"]["entity"]["id"]
    if await is_webhook_processed(event_id):
        return {"status": "already_processed"}

    # 4. Handle event
    if event == "payment.captured":
        await handle_payment_captured(payload)
    elif event == "subscription.charged":
        await handle_subscription_charged(payload)
    elif event == "subscription.cancelled":
        await handle_subscription_cancelled(payload)

    # 5. Mark as processed
    await mark_webhook_processed(event_id)
    return {"status": "ok"}
```

---

## Outgoing Webhooks (XithSense Sends) — Phase 2

**For developer/API tier subscribers who want to receive XithSense events in their own systems.**

**Endpoint:** User-configured URL in account settings  
**Auth:** HMAC-SHA256 signature in `X-XithSense-Signature` header  
**Content-Type:** `application/json`

### Outgoing Event: `prediction.ready`

```json
{
  "event": "prediction.ready",
  "match_id": "1539584",
  "match_type": "T20",
  "teams": ["India", "Australia"],
  "match_date": "2026-06-27",
  "prediction_url": "https://api.xithsense.com/api/v1/predict/team",
  "timestamp": "2026-06-27T10:00:00Z"
}
```

### Outgoing Event: `toss.completed`

```json
{
  "event": "toss.completed",
  "match_id": "1539584",
  "toss_winner": "India",
  "toss_decision": "bat",
  "updated_captain": {"player": "Rohit Sharma", "confidence": 74},
  "timestamp": "2026-06-27T14:28:00Z"
}
```

### Signature Generation

```python
def sign_outgoing_webhook(payload: dict, secret: str) -> str:
    body = json.dumps(payload, separators=(",", ":"))
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
```
