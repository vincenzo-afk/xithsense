# Audit Log Specification

**Table:** `admin_action`  
**Purpose:** Immutable record of all privileged operations for compliance and debugging.

---

## Events That Must Be Audited

| Event | Actor | Target |
|-------|-------|--------|
| User role changed | Admin | user_id |
| Subscription manually activated/cancelled | Admin | subscription_id |
| Human rule created | Admin | rule_id |
| Human rule updated | Admin | rule_id |
| Human rule deleted | Admin | rule_id |
| Model version promoted | Admin / System | model_version_id |
| Model retrain triggered | Admin | format |
| Data ingestion triggered | Admin / System | source |
| Feature rebuild triggered | Admin / System | — |
| Refund issued | Admin | payment_id |
| User account suspended | Admin | user_id |
| Admin login | Admin | — |
| Broadcast notification sent | Admin | event_type |
| Backtest triggered | Admin / System | run_id |

---

## `admin_action` Table Schema

```sql
CREATE TABLE admin_action (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id   UUID NOT NULL REFERENCES "user"(id),
    action          VARCHAR(100) NOT NULL,
    target_type     VARCHAR(50),    -- "user" | "rule" | "model" | "subscription" | "system"
    target_id       VARCHAR(100),   -- ID of affected entity
    payload         JSONB,          -- Full payload of the change
    ip_address      INET,           -- Admin IP for security review
    user_agent      VARCHAR(500),   -- Admin browser/tool info
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_admin_action_actor ON admin_action(admin_user_id);
CREATE INDEX idx_admin_action_target ON admin_action(target_type, target_id);
CREATE INDEX idx_admin_action_time ON admin_action(created_at DESC);
```

---

## Sample Audit Records

```json
[
  {
    "id": "uuid",
    "admin_user_id": "uuid-of-admin",
    "action": "rule.created",
    "target_type": "rule",
    "target_id": "RULE-0120",
    "payload": {
      "rule_id": "RULE-0120",
      "player_key": "Maxwell, GJ",
      "impact_score": -20,
      "confidence": 0.76
    },
    "ip_address": "103.21.244.0",
    "created_at": "2026-06-25T10:30:00Z"
  },
  {
    "id": "uuid",
    "admin_user_id": "uuid-of-admin",
    "action": "model.promoted",
    "target_type": "model",
    "target_id": "m01-t20-20260601",
    "payload": {
      "previous_active": "m01-t20-20260501",
      "val_mae_before": 12.84,
      "val_mae_after": 11.94,
      "captain_accuracy_after": 0.401
    },
    "created_at": "2026-06-01T12:00:00Z"
  }
]
```

---

## Audit Log API (Admin Only)

```
GET /api/v1/admin/audit?action=rule.created&from=2026-06-01&limit=50
```

Response includes paginated audit records sorted by `created_at DESC`.

---

## Retention

Audit logs are retained permanently. They are excluded from any data cleanup jobs.  
Archive to S3 after 1 year for cost efficiency: `aws s3 cp audit_export.csv s3://xithsense-audit/`.
