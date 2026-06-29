# WebSocket Specification

**Endpoint:** `GET /api/v1/live/{match_id}`  
**Protocol:** WebSocket (RFC 6455)  
**Auth:** JWT passed as query param: `?token=<jwt>`

## Connection

```javascript
const ws = new WebSocket(
  `wss://api.xithsense.com/api/v1/live/1535465?token=${jwt}`
);
```

## Server → Client Events

### Event: `match_update`
Sent every over or on significant events.

```json
{
  "event": "match_update",
  "match_id": "1535465",
  "timestamp": "2026-06-25T14:32:00Z",
  "live_score": {
    "batting_team": "Gujarat Titans",
    "runs": 142,
    "wickets": 4,
    "overs": 16.3
  },
  "win_probability": {
    "Gujarat Titans": 0.34,
    "Royal Challengers Bengaluru": 0.66
  }
}
```

### Event: `player_update`
Sent when a player's live FP changes materially (≥ 5 pts).

```json
{
  "event": "player_update",
  "player_id": "uuid",
  "full_name": "Virat Kohli",
  "live_fantasy_points": 67.0,
  "runs_scored": 52,
  "balls_faced": 38,
  "wickets_taken": 0,
  "captain_multiplier_applied": true
}
```

### Event: `playing_xi_update`
Sent when confirmed XI differs from predicted.

```json
{
  "event": "playing_xi_update",
  "match_id": "1535465",
  "team": "Gujarat Titans",
  "confirmed_xi": ["Player A", "Player B"],
  "late_changes": ["Player C replaced Player D (injury)"]
}
```

### Event: `toss_update`

```json
{
  "event": "toss_update",
  "match_id": "1535465",
  "toss_winner": "Royal Challengers Bengaluru",
  "toss_decision": "field",
  "prediction_refresh_url": "/api/v1/predict/team"
}
```

## Client → Server Messages

```json
{ "action": "subscribe_player", "player_id": "uuid" }
{ "action": "ping" }
```

## Connection Lifecycle

- Server pings client every 30 seconds
- Client must respond with pong within 10 seconds
- Connection auto-closes when match ends (event: `match_ended`)
- Max 5 simultaneous WebSocket connections per Premium user
