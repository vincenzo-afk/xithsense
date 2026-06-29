# Event Flow

All async events in XithSense flow through Celery. This document maps every system event to its triggers, consumers, and side effects.

---

## Event: `match.xi_confirmed`

**Source:** Admin API `PATCH /api/v1/admin/matches/:id` or automated XI scraper  
**Trigger:** Playing XI populated for both teams in `player_team_match`

```
match.xi_confirmed
    │
    ├──► [Celery] refresh_match_prediction(match_id)
    │         └── Invalidate Redis cache for match
    │         └── Re-run full inference pipeline (new player set)
    │         └── Store prediction with phase="pre_toss"
    │
    ├──► [Celery] send_xi_notifications(match_id)
    │         └── Load subscribed Premium users
    │         └── For each: send_telegram_message / send_email
    │
    └──► [Redis] Set flag: xi_confirmed:{match_id} = true (TTL 24h)
```

---

## Event: `match.toss_completed`

**Source:** Admin API `PATCH /api/v1/admin/matches/:id` with toss fields

```
match.toss_completed
    │
    ├──► [Celery] refresh_prediction_post_toss(match_id)
    │         └── Invalidate feature cache (is_chasing changes)
    │         └── Recompute context features with new toss
    │         └── Re-run ensemble (live_weight now active)
    │         └── Re-run optimizer (may change team composition)
    │         └── Store prediction with phase="post_toss"
    │
    ├──► [Celery] send_toss_notifications(match_id)
    │         └── Load subscribed Premium users
    │         └── Build message with toss result + updated captain
    │         └── Send via Telegram / Push / Email
    │
    └──► [WebSocket] Broadcast toss_update event to all live connections
              └── Payload: {toss_winner, toss_decision, updated_captain}
```

---

## Event: `match.injury_alert`

**Source:** Admin API `POST /api/v1/admin/notifications/injury-alert`

```
match.injury_alert(match_id, player_out, replacement)
    │
    ├──► [DB] Update player_team_match (remove player_out, add replacement)
    │
    ├──► [Celery] refresh_prediction_post_injury(match_id)
    │         └── Remove injured player from eligible XI
    │         └── Re-run optimizer without that player
    │         └── Find replacement in credit budget
    │
    ├──► [Celery] send_injury_notifications(match_id, player_out, replacement)
    │         └── Find users who have player_out in predicted_team
    │         └── Send URGENT alert to those users specifically
    │         └── Include suggested replacement
    │
    └──► [Redis] Invalidate prediction cache for match
```

---

## Event: `payment.captured`

**Source:** Razorpay webhook `POST /api/v1/payments/webhook`

```
payment.captured
    │
    ├──► [DB] UPDATE subscription SET status='active'
    │         UPDATE user SET role='premium'
    │
    ├──► [Redis] Set user role cache: user_role:{user_id} = 'premium' (TTL 1h)
    │
    ├──► [Celery] send_welcome_premium_email(user_id)
    │
    └──► [Audit] INSERT admin_action: action='subscription.activated'
```

---

## Event: `model.retrain_requested`

**Source:** Admin API `POST /api/v1/admin/retrain` or monthly Celery Beat schedule

```
model.retrain_requested(format, model_ids)
    │
    ├──► [Celery:ml queue] retrain_models(format, model_ids)
    │         │
    │         ├── Load feature data from DB (training window)
    │         ├── Train XGBoost model
    │         ├── Train LightGBM model
    │         ├── Train CatBoost model
    │         ├── Evaluate all on held-out test set
    │         ├── Compare vs current active model
    │         │     If improved: promote new model
    │         │     If not improved: keep current
    │         ├── Save artifacts to models/artifacts/
    │         ├── Update model_version table
    │         └── Log experiment to EXPERIMENT_TRACKING.md
    │
    ├──► [Celery] send_retrain_complete_email(admin_email, results)
    │
    └──► [Audit] INSERT admin_action: action='model.retrain_completed'
```

---

## Event: `subscription.expiry_check` (Scheduled)

**Source:** Celery Beat — daily at 00:00 IST

```
subscription.expiry_check
    │
    └──► [DB] SELECT subscriptions WHERE status='cancelled' AND period_end < NOW()
              For each:
                  UPDATE subscription SET status='expired'
                  UPDATE user SET role='free'
                  [Celery] send_expiry_email(user_id)
```

---

## Event: `data.ingestion_scheduled` (Scheduled)

**Source:** Celery Beat — daily at 02:00 IST

```
data.ingestion_scheduled
    │
    ├──► [Celery:data] ingest_cricsheet_incremental()
    │         └── Download / read latest JSON files
    │         └── Parse and upsert new matches
    │         └── Compute fantasy points for new matches
    │
    ├──► [Celery:ml] build_features_incremental()
    │         └── Recompute rolling features for affected players
    │
    └──► [Celery] run_quality_checks()
              └── Log report; alert if checks fail
