# Real-Time Event Specification

**Protocol:** WebSocket (RFC 6455) · **Endpoint:** `GET /api/v1/live/{match_id}`

---

## Connection

```javascript
const token = localStorage.getItem("access_token");  // Premium JWT
const ws = new WebSocket(
  `wss://api.xithsense.com/api/v1/live/${matchId}?token=${token}`
);

ws.onopen = () => console.log("Connected to live feed");
ws.onmessage = (e) => handleEvent(JSON.parse(e.data));
ws.onclose = (e) => handleDisconnect(e.code, e.reason);
ws.onerror = (e) => console.error("WS error", e);
```

---

## Event Catalog

### `connection_established`
Sent immediately on successful connection.

```json
{
  "event": "connection_established",
  "match_id": "1535465",
  "connection_id": "uuid",
  "match_status": "in_progress",
  "current_over": "16.3",
  "timestamp": "2026-05-25T18:42:15Z"
}
```

---

### `match_update`
Sent after each completed over or on significant score change (boundary, wicket).

```json
{
  "event": "match_update",
  "match_id": "1535465",
  "timestamp": "2026-05-25T18:43:00Z",
  "innings": {
    "number": 1,
    "batting_team": "Gujarat Titans",
    "bowling_team": "Royal Challengers Bengaluru",
    "runs": 142,
    "wickets": 4,
    "overs": "16.3",
    "current_run_rate": 8.49,
    "projected_total": 172
  },
  "win_probability": {
    "Gujarat Titans": 0.34,
    "Royal Challengers Bengaluru": 0.66
  },
  "required": {
    "runs": 31,
    "balls": 21,
    "run_rate": 8.86
  }
}
```

---

### `player_update`
Sent when a player's live fantasy points change by ≥ 5 points.

```json
{
  "event": "player_update",
  "player_id": "d4e5f6a7-b8c9-0123-defa-bc4567890123",
  "full_name": "Virat Kohli",
  "team": "Royal Challengers Bengaluru",
  "batting": {
    "runs": 52,
    "balls": 38,
    "fours": 4,
    "sixes": 3,
    "strike_rate": 136.8,
    "is_batting": true,
    "is_dismissed": false
  },
  "bowling": null,
  "live_fantasy_points": 82.0,
  "captain_multiplier": true,
  "effective_fp_as_captain": 164.0,
  "prediction_accuracy": {
    "predicted_fp": 65.2,
    "current_fp": 82.0,
    "on_track": true
  }
}
```

---

### `wicket_fell`
Sent immediately on wicket.

```json
{
  "event": "wicket_fell",
  "match_id": "1535465",
  "timestamp": "2026-05-25T18:41:32Z",
  "player_out": "Shubman Gill",
  "player_id": "uuid",
  "kind": "caught",
  "bowler": "JR Hazlewood",
  "fielder": "RM Patidar",
  "over": "2.2",
  "score_at_fall": "14/1",
  "fantasy_points_at_dismissal": 0.0,
  "warning": "Player in your predicted team dismissed for duck"
}
```

---

### `toss_update`
Sent when toss result is entered.

```json
{
  "event": "toss_update",
  "match_id": "1535465",
  "toss_winner": "Royal Challengers Bengaluru",
  "toss_decision": "field",
  "prediction_refreshing": true,
  "updated_captain": {
    "player_id": "d4e5f6a7-b8c9-0123-defa-bc4567890123",
    "full_name": "Virat Kohli",
    "confidence": 87,
    "reason": "Chasing specialist rule activated"
  },
  "timestamp": "2026-05-25T14:28:00Z"
}
```

---

### `playing_xi_update`
Sent when XI is confirmed or changes.

```json
{
  "event": "playing_xi_update",
  "match_id": "1535465",
  "team": "Gujarat Titans",
  "xi": ["Shubman Gill", "B Sai Sudharsan", "Vijay Shankar"],
  "changes": [
    {"type": "replaced", "out": "Abhinav Manohar", "in": "Vijay Shankar", "reason": "injury"}
  ],
  "prediction_refreshing": true,
  "timestamp": "2026-05-25T14:05:00Z"
}
```

---

### `match_ended`
Sent when match concludes.

```json
{
  "event": "match_ended",
  "match_id": "1535465",
  "winner": "Royal Challengers Bengaluru",
  "result": "Royal Challengers Bengaluru won by 5 wickets",
  "player_of_match": "V Kohli",
  "top_fantasy_scorer": {
    "player_id": "d4e5f6a7-b8c9-0123-defa-bc4567890123",
    "full_name": "Virat Kohli",
    "fantasy_points": 116.0
  },
  "captain_accuracy": {
    "predicted_captain": "Virat Kohli",
    "actual_top_scorer": "Virat Kohli",
    "correct": true
  },
  "connection_closing_in_seconds": 30
}
```

---

## Client → Server Messages

```json
// Keep-alive ping (every 30 seconds)
{"action": "ping"}

// Server responds
{"action": "pong", "timestamp": "2026-05-25T18:43:00Z"}

// Subscribe to specific player updates
{"action": "subscribe_player", "player_id": "uuid"}

// Request latest state (on reconnect)
{"action": "request_state"}
```

---

## Connection Lifecycle

```
Client          Server
  │               │
  │  Connect      │
  │──────────────►│  Validate JWT (query param)
  │               │  Check premium access
  │               │  Register connection in Redis set
  │◄──────────────│  connection_established
  │               │
  │◄──────────────│  (events stream...)
  │               │
  │ Every 30s:    │
  │──────────────►│  ping
  │◄──────────────│  pong
  │               │
  │               │  [match_ended event]
  │◄──────────────│  match_ended (30s warning)
  │               │  connection closed after 30s
```

**Reconnection:** Client should reconnect with exponential backoff on unexpected close.  
**Max connections:** 5 simultaneous WebSocket connections per Premium user.
