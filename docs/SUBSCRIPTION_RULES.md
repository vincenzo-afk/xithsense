# Subscription Rules

## Plan Definitions

| Plan | Price | Billing | Razorpay Plan ID |
|------|-------|---------|-----------------|
| `free` | ₹0 | None | — |
| `premium_monthly` | ₹299/month | Monthly recurring | `plan_monthly_299` |
| `premium_annual` | ₹2,499/year | Annual recurring | `plan_annual_2499` |

---

## Status Lifecycle

```
Registration
    │
    ▼
status = "free" (role = free)
    │
    │ [User subscribes]
    ▼
status = "active" (role = premium)
    │
    ├── [Monthly/Annual renewal] → status stays "active"
    │
    ├── [User cancels] → status = "cancelled"
    │       │              role stays "premium" until period_end
    │       └── [period_end reached] → status = "expired", role = "free"
    │
    └── [Payment fails after retries] → status = "expired", role = "free"
```

---

## Access Rules by Status

| Status | `role` | Feature Access |
|--------|--------|----------------|
| `free` | `free` | Free tier only |
| `active` | `premium` | Full premium access |
| `cancelled` | `premium` | Premium until `period_end` |
| `expired` | `free` | Free tier only |
| `trial` | `premium` | Full premium access for trial duration |

---

## Proration Policy

- Monthly plan: no proration; cancel anytime; access until period_end
- Annual plan: no proration after 7 days; full refund within 7 days (no predictions accessed)
- Upgrade from monthly to annual: credit remaining days; charge difference

---

## Grace Period

If a renewal payment fails:
1. Retry payment after 24 hours
2. If still failed, retry after 72 hours
3. If still failed: set `status=expired`, `role=free`, send email notification

User has 7-day grace period to update payment method before losing access.

---

## Subscription API Behaviour

```python
def check_premium_access(user: User) -> bool:
    """Returns True if user has active premium access."""
    if user.role == "admin":
        return True
    if user.role != "premium":
        return False
    # Check if subscription is within valid period
    sub = user.subscription
    if sub.status in ("active", "cancelled"):
        if sub.current_period_end and sub.current_period_end > datetime.utcnow():
            return True
    return False
```

---

## Concurrent Subscription Rule

A user can only have one active subscription at a time. Attempting to create a new subscription while one is active upgrades/downgrades the existing one via Razorpay's subscription update API.
