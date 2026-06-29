# Permissions Matrix

## Role Definitions

| Role | Description | Assigned By |
|------|-------------|-------------|
| `free` | Default role on registration | System (auto) |
| `premium` | Paid subscriber with full feature access | Payment webhook |
| `admin` | Internal staff with system management access | Manual (admin CLI) |

---

## API Endpoint Permissions

| Endpoint | free | premium | admin | Notes |
|----------|------|---------|-------|-------|
| `GET /health` | ✅ | ✅ | ✅ | No auth required |
| `POST /auth/register` | ✅ | ✅ | ✅ | No auth required |
| `POST /auth/login` | ✅ | ✅ | ✅ | No auth required |
| `POST /auth/refresh` | ✅ | ✅ | ✅ | Refresh token required |
| `GET /matches/upcoming` | ✅ | ✅ | ✅ | |
| `GET /matches/:id` | ✅ | ✅ | ✅ | |
| `GET /players/search` | ✅ | ✅ | ✅ | |
| `GET /players/:id` | ✅ | ✅ | ✅ | |
| `GET /players/:id/matchups` | ✅ | ✅ | ✅ | |
| `POST /predict/team` (count=1) | ✅ | ✅ | ✅ | Free: mode=safe only |
| `POST /predict/team` (count>1) | ❌ 402 | ✅ | ✅ | Premium required |
| `POST /predict/team` (mode=grand_league) | ❌ 402 | ✅ | ✅ | Premium required |
| `POST /predict/team/portfolio` | ❌ 402 | ✅ | ✅ | Premium required |
| `POST /predict/captain` | ✅ | ✅ | ✅ | |
| `GET /predict/differentials/:id` | ❌ 402 | ✅ | ✅ | Premium required |
| `GET /explain/:match/:player` | ✅ (basic) | ✅ (full) | ✅ | Free: truncated explanation |
| `POST /chat` | ❌ 402 | ✅ | ✅ | Premium required |
| `GET /live/:match_id` (WebSocket) | ❌ 402 | ✅ | ✅ | Premium required |
| `GET /account` | ✅ | ✅ | ✅ | Own account only |
| `POST /payments/create-subscription` | ✅ | ✅ | ✅ | |
| `POST /payments/cancel` | ❌ | ✅ | ✅ | Active sub required |
| `PATCH /notifications/preferences` | ✅ (email only) | ✅ | ✅ | |
| `GET /admin/*` | ❌ 403 | ❌ 403 | ✅ | Admin only |
| `POST /admin/ingest` | ❌ 403 | ❌ 403 | ✅ | |
| `POST /admin/retrain` | ❌ 403 | ❌ 403 | ✅ | |
| `POST /admin/rules` | ❌ 403 | ❌ 403 | ✅ | |
| `PATCH /admin/rules/:id` | ❌ 403 | ❌ 403 | ✅ | |
| `GET /admin/metrics` | ❌ 403 | ❌ 403 | ✅ | |
| `POST /admin/users/:id/role` | ❌ 403 | ❌ 403 | ✅ | |
| `POST /admin/payments/refund` | ❌ 403 | ❌ 403 | ✅ | |

---

## Feature-Level Permissions

| Feature | free | premium |
|---------|------|---------|
| Teams per match | 1 (safe mode only) | 20 (all modes) |
| Team modes available | Safe | Safe, Grand League, Aggressive, Small League |
| AI chat messages per match | 0 | Unlimited |
| Explanation depth | Basic (2 factors) | Full (4+ factors + rules) |
| Differential picks | ❌ | ✅ |
| Live intelligence (WebSocket) | ❌ | ✅ |
| Telegram notifications | ❌ | ✅ |
| WhatsApp notifications | ❌ | ✅ |
| Push notifications | ❌ | ✅ |
| Email notifications (toss/XI) | ✅ | ✅ |
| Backtesting results view | ❌ | ✅ |
| API access (external) | ❌ | ✅ (300 RPM) |

---

## Data Isolation Rules

- Users can only read their own `prediction`, `chat_session`, `notification`, `subscription` records
- Match data, player data, and venue data are readable by all authenticated users
- Admin can read all records in all tables
- Prediction records created without a `user_id` (system predictions) are readable by all Premium users
