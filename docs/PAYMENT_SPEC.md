# Payment Specification

**Provider:** Razorpay  
**Currency:** INR  
**Billing Model:** Recurring subscription

## Plans

| Plan | Monthly Price | Annual Price | Billing |
|------|--------------|-------------|---------|
| Free | ₹0 | ₹0 | — |
| Premium Monthly | ₹299 | — | Monthly recurring |
| Premium Annual | — | ₹2,499 | Annual recurring (~30% saving) |

## Subscription Flow

```
1. User clicks "Upgrade to Premium"
2. Frontend calls: POST /api/v1/payments/create-subscription
3. Backend creates Razorpay subscription → returns razorpay_sub_id
4. Frontend opens Razorpay Checkout modal
5. User completes payment
6. Razorpay sends webhook: payment.captured
7. Backend verifies webhook signature
8. Backend updates subscription.status = "active"
9. Backend updates user.role = "premium"
10. Frontend polls GET /api/v1/auth/me until role = "premium" (max 60s)
```

## Razorpay Webhook Events

| Event | Handler Action |
|-------|---------------|
| `payment.captured` | Activate subscription, set role=premium |
| `subscription.charged` | Update period_start, period_end |
| `subscription.cancelled` | Set status=cancelled, keep premium until period_end |
| `subscription.completed` | Set status=expired |
| `payment.failed` | Log failure, send retry email |

## Webhook Signature Verification

```python
import hmac, hashlib

def verify_razorpay_webhook(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Always verify before processing. Reject if signature mismatch (return 400).

## Refund Policy

- 7-day refund for Annual plan if no predictions accessed
- No refund after first prediction accessed
- Monthly plan: cancel anytime; no prorated refund
- Refunds via Razorpay API: `POST /api/v1/admin/payments/refund` (admin only)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/payments/create-subscription` | Create Razorpay subscription |
| `POST` | `/api/v1/payments/webhook` | Razorpay webhook receiver (no auth) |
| `GET` | `/api/v1/payments/status` | Current subscription status |
| `POST` | `/api/v1/payments/cancel` | Cancel active subscription |

## Test Credentials

Use Razorpay test mode (`rzp_test_*` key). Test card: `4111 1111 1111 1111`, any future expiry, any CVV.

Never commit real Razorpay keys. Use `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` env vars.
