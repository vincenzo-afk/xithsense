# Notification Event Triggers

## Event Definitions

### EVT-01: Playing XI Announced

**Trigger condition:** `player_team_match` records inserted for both teams of a match  
**Detection method:** Celery task polls for matches within 6 hours; XI marked confirmed  
**Audience:** All Premium users who have opted in for this format  
**Priority:** High (send within 2 minutes of trigger)

```python
# Celery task
@app.task
def check_playing_xi_announcements():
    upcoming = get_matches_within_hours(hours=6)
    for match in upcoming:
        if is_xi_now_confirmed(match.id) and not already_notified(match.id, "EVT-01"):
            send_xi_notification.delay(match.id)
            mark_notified(match.id, "EVT-01")
```

---

### EVT-02: Toss Completed

**Trigger condition:** `match.toss_winner` and `match.toss_decision` populated  
**Detection:** Polling every 5 minutes for live matches approaching start time  
**Audience:** All Premium users subscribed to that match  
**Priority:** Critical (send within 1 minute; affects team selection)  
**Side effect:** Trigger prediction refresh with new toss context

---

### EVT-03: Last-Minute Injury / Substitution

**Trigger condition:** Player removed from confirmed XI within 60 minutes of match start  
**Detection:** Admin manual trigger via `POST /api/v1/admin/notifications/injury-alert`  
**Audience:** Users who have that player in any of their predicted teams for this match  
**Priority:** Critical

---

### EVT-04: Playing XI Changes

**Trigger condition:** Player added/removed from XI after initial confirmation  
**Audience:** All Premium users subscribed to that match  
**Priority:** High

---

### EVT-05: Captain Recommendation Updated

**Trigger condition:** Post-toss prediction regenerated; captain recommendation changes  
**Audience:** Users who viewed the pre-toss prediction  
**Priority:** Medium

---

### EVT-07: Prediction Ready

**Trigger condition:** First prediction generated for an upcoming match  
**Audience:** Users who have viewed that match page (based on `prediction.user_id`)  
**Priority:** Low (can batch)

---

## Event Processing Queue

All notification events go through Celery:

```
Event trigger
    │
    ▼
Celery task: send_notification(event_id, match_id, target_users)
    │
    ├─► For each user in target_users:
    │       check user.notification_preferences
    │       for each enabled channel:
    │           queue channel-specific task
    │
    ├─► telegram: send_telegram_message.delay(user_id, message)
    ├─► push: send_push_notification.delay(user_id, message)
    └─► email: send_email_notification.delay(user_id, message)
```
