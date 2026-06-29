# Notification Specification

## Event Triggers

| Event ID | Event | Trigger Condition | Audience |
|----------|-------|------------------|----------|
| `EVT-01` | Playing XI Announced | XI confirmed for a match | All Premium users subscribed to that match's format |
| `EVT-02` | Toss Completed | Toss result available | All Premium users subscribed to that match |
| `EVT-03` | Last-Minute Injury | Player excluded from XI < 30 min before match | Users who predicted that player |
| `EVT-04` | Team Change | Substitute added, playing XI changes | Users who predicted that match |
| `EVT-05` | Captain Updated | XithSense updates captain recommendation post-toss | All Premium users with that match |
| `EVT-06` | Match Starts | First ball bowled | Users with live subscription active |
| `EVT-07` | Prediction Ready | Pre-match prediction generated | Users who viewed that match |

## Delivery Channels

| Channel | Implementation | Latency Target |
|---------|---------------|----------------|
| Telegram | `python-telegram-bot` via Bot API | < 30 seconds |
| WhatsApp | WhatsApp Business API | < 60 seconds |
| Push notification | Firebase Cloud Messaging (FCM) | < 30 seconds |
| Email | AWS SES / SMTP | < 2 minutes |

## Message Templates

### EVT-01: Playing XI Announced
```
🏏 Playing XI Confirmed!

{match_title}
📅 {match_date} | 📍 {venue}

✅ Team A: {team_a_players}
✅ Team B: {team_b_players}

🔮 View prediction: {prediction_url}
```

### EVT-02: Toss Result
```
🪙 Toss Result!

{match_title}
{toss_winner} won the toss and elected to {toss_decision}.

⚡ Updated predictions ready!
👑 New Captain Pick: {new_captain} ({confidence}% confidence)

🔮 View team: {prediction_url}
```

### EVT-03: Injury Alert
```
🚨 Injury Alert — Team Update Required!

{player_name} is OUT of {match_title}.

🔄 Update your team immediately.
⏰ Contest deadline: {deadline}

📲 Update team: {update_url}
```

## User Preference Model

Users configure notifications via `PATCH /api/v1/notifications/preferences`:

```json
{
  "telegram_enabled": true,
  "email_enabled": false,
  "push_enabled": true,
  "events": {
    "EVT-01": true,
    "EVT-02": true,
    "EVT-03": true,
    "EVT-04": true,
    "EVT-05": false,
    "EVT-06": false,
    "EVT-07": true
  },
  "formats": ["T20", "IPL"]
}
```

## Retry Policy

- Failed delivery: retry after 2 minutes, then 10 minutes
- After 2 failed retries: mark as `failed`, do not retry further
- Log all delivery attempts in `notification` table
