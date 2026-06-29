# Admin Panel Specification

**Access:** `role=admin` JWT required  
**Interface:** API-first (MVP); React dashboard (Phase 2)

## Admin Capabilities

### Data Management
- `POST /api/v1/admin/ingest` — Trigger Cricsheet ingestion
- `POST /api/v1/admin/features/rebuild` — Rebuild feature store
- `GET /api/v1/admin/ingestion/status` — Current ingestion job status

### Model Management
- `POST /api/v1/admin/retrain` — Queue model retraining
- `GET /api/v1/admin/models` — List all model versions with metrics
- `POST /api/v1/admin/models/:id/activate` — Promote model version to active
- `GET /api/v1/admin/backtest/:id` — Fetch backtest results

### Human Rules Management
- `GET /api/v1/admin/rules` — List all rules
- `POST /api/v1/admin/rules` — Create new rule
- `PATCH /api/v1/admin/rules/:id` — Update or deactivate rule
- `DELETE /api/v1/admin/rules/:id` — Delete rule (soft delete)
- `POST /api/v1/admin/rules/validate` — Validate rule JSON before saving

### User Management
- `GET /api/v1/admin/users` — List users with subscription status
- `PATCH /api/v1/admin/users/:id/role` — Change user role
- `POST /api/v1/admin/payments/refund` — Issue refund

### Metrics Dashboard
- `GET /api/v1/admin/metrics` — Aggregated KPIs:
  - Total users, premium users, MRR
  - Captain accuracy (last 30 days)
  - Correct player rate (last 30 days)
  - API uptime, p95 response time
  - Model MAE on recent matches

### Notifications
- `POST /api/v1/admin/notifications/broadcast` — Send manual broadcast to all premium users

## Admin Action Audit Log

All admin actions written to `admin_action` table:
```sql
CREATE TABLE admin_action (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id UUID NOT NULL REFERENCES "user"(id),
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id VARCHAR(100),
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
