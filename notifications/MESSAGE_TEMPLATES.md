# Notification Message Templates

All templates support variable substitution using `{variable}` syntax.

---

## Telegram Templates

### EVT-01: Playing XI Announced

```
🏏 *Playing XI Confirmed!*

*{team_a} vs {team_b}*
📅 {match_date} | 📍 {venue}

✅ *{team_a}:*
{team_a_players}

✅ *{team_b}:*
{team_b_players}

🔮 [View Prediction]({prediction_url})
⚡ Hurry — contest deadline: {deadline}
```

### EVT-02: Toss Result

```
🪙 *Toss Result — {team_a} vs {team_b}*

{toss_winner} won the toss and elected to *{toss_decision}*.

⚡ *Updated predictions are ready!*
👑 Recommended Captain: *{captain_name}* ({captain_confidence}% confidence)
🔄 Captain changed from pre-toss pick: {captain_changed}

🔮 [View Updated Team]({prediction_url})
```

### EVT-03: Injury Alert

```
🚨 *INJURY ALERT — Act Now!*

*{player_name}* is OUT of {team_name} for {match_title}.

🔄 Suggested replacement: *{replacement_name}* ({replacement_credits} cr)

⏰ Contest deadline: *{deadline}*
📲 [Update Your Team]({update_url})
```

### EVT-05: Captain Updated

```
👑 *Captain Pick Updated — {match_title}*

New recommended captain: *{new_captain}*
Reason: {update_reason}

Previous pick: {old_captain}

🔮 [View Latest Prediction]({prediction_url})
```

### EVT-07: Prediction Ready

```
⚡ *Your XithSense prediction is ready!*

*{team_a} vs {team_b}*
📅 Today, {match_time} IST

👑 Captain Pick: *{captain_name}* ({captain_confidence}% confidence)
🎯 Top Pick: *{top_player_name}* — {top_player_fp:.0f} predicted FP

🔮 [View Full Prediction]({prediction_url})
```

---

## Email Templates

### EVT-01: Playing XI Subject
```
Subject: 🏏 Playing XI Confirmed — {team_a} vs {team_b} | XithSense
```

### EVT-02: Toss Subject
```
Subject: 🪙 Toss Result: {toss_winner} elected to {toss_decision} — Updated Picks Ready
```

### EVT-03: Injury Subject
```
Subject: 🚨 URGENT: {player_name} is OUT — Update Your Team Now
```

---

## Character Limits

| Channel | Max Length |
|---------|-----------|
| Telegram | 4096 chars (Markdown) |
| WhatsApp | 1024 chars (plain text) |
| Push notification title | 65 chars |
| Push notification body | 240 chars |
| Email subject | 78 chars |
