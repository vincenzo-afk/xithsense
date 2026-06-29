# Notification Delivery Rules

## Channel Priority Order

When a user has multiple channels enabled, send to all enabled channels in parallel.

## Delivery Windows

| Event | Send Window | Max Delay |
|-------|-------------|-----------|
| EVT-01 Playing XI | Any time | 2 minutes from trigger |
| EVT-02 Toss | Any time | 1 minute from trigger |
| EVT-03 Injury | Any time | 30 seconds from trigger |
| EVT-04 XI Change | Any time | 2 minutes from trigger |
| EVT-05 Captain Update | Any time | 5 minutes from trigger |
| EVT-07 Prediction Ready | 6 AM – 11 PM IST only | 10 minutes from trigger |

Never send marketing-style notifications between 11 PM and 6 AM IST.  
Emergency alerts (EVT-03) are exempt from quiet hours.

## Deduplication

Each (user_id, match_id, event_id) combination is sent at most once per match phase.  
Stored in Redis: `notif:dedup:{user_id}:{match_id}:{event_id}` TTL 24 hours.

## Retry Policy

```python
RETRY_SCHEDULE = [
    120,    # retry after 2 minutes
    600,    # retry after 10 minutes
]
MAX_RETRIES = 2

# After max retries: mark delivery as "failed", log for monitoring
```

## Opt-Out Handling

- User can unsubscribe from all notifications via `PATCH /api/v1/notifications/preferences`
- Hard unsubscribe (user deletes account): all preferences deleted immediately
- Telegram: if user blocks bot, log `TelegramBotBlocked`, set `telegram_enabled=false` automatically

## Notification Table Schema

```sql
CREATE TABLE notification (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES "user"(id),
    match_id VARCHAR(20),
    event_type VARCHAR(20) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    message_preview VARCHAR(200),
    sent_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    retry_count SMALLINT DEFAULT 0,
    error_message VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notif_user ON notification(user_id);
CREATE INDEX idx_notif_status ON notification(status);
```

## Monitoring

Alert on:
- Delivery failure rate > 5% in any 15-minute window
- EVT-02 (toss) average delivery time > 90 seconds
- Queue depth > 500 pending notifications
