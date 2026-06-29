# API Specification

**Framework:** FastAPI 0.111  
**Base URL:** `https://api.xithsense.com`  
**Version:** `v1`  
**Auth:** Bearer JWT via `Authorization: Bearer <token>` header  
**Rate limits:** Free 30 RPM, Premium 300 RPM, Admin 1000 RPM  
**OpenAPI:** Auto-generated at `/docs` (Swagger) and `/redoc`

---

## 1. Authentication

### POST `/api/v1/auth/register`

Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "Rahul Sharma"
}
```

**Response 201:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "free",
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### POST `/api/v1/auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": { "id": "uuid", "email": "...", "role": "free" }
}
```

---

### POST `/api/v1/auth/refresh`

Refresh an expiring JWT.

---

## 2. Matches

### GET `/api/v1/matches/upcoming`

List upcoming matches with prediction-ready status.

**Query params:** `format` (T20|ODI|Test), `limit` (default 10), `offset`

**Response 200:**
```json
{
  "matches": [
    {
      "id": "1535465",
      "team_a": "Gujarat Titans",
      "team_b": "Royal Challengers Bengaluru",
      "venue": "Narendra Modi Stadium, Ahmedabad",
      "match_date": "2026-06-25",
      "match_type": "T20",
      "event": "Indian Premier League",
      "prediction_ready": true,
      "playing_xi_confirmed": false
    }
  ],
  "total": 3
}
```

---

### GET `/api/v1/matches/{match_id}`

Full match metadata.

**Response 200:**
```json
{
  "id": "1535465",
  "match_type": "T20",
  "team_a": "Gujarat Titans",
  "team_b": "Royal Challengers Bengaluru",
  "venue_name": "Narendra Modi Stadium, Ahmedabad",
  "toss": { "winner": "Royal Challengers Bengaluru", "decision": "field" },
  "outcome": { "winner": "Royal Challengers Bengaluru", "by": { "wickets": 5 } },
  "season": "2026",
  "match_date": "2026-05-25",
  "player_of_match": ["V Kohli"]
}
```

---

## 3. Players

### GET `/api/v1/players/search`

**Query params:** `q` (name), `team`, `role` (BAT|BOWL|AR|WK), `limit` (default 20)

**Response 200:**
```json
{
  "players": [
    {
      "id": "uuid",
      "full_name": "Virat Kohli",
      "short_name": "V Kohli",
      "primary_role": "BAT",
      "batting_style": "Right-hand bat",
      "bowling_style": "Right-arm medium",
      "nationality": "India",
      "is_active": true
    }
  ]
}
```

---

### GET `/api/v1/players/{player_id}`

Full player profile with recent stats.

**Response 200:**
```json
{
  "id": "uuid",
  "full_name": "Virat Kohli",
  "primary_role": "BAT",
  "recent_form": {
    "last_3_fp_avg": 48.3,
    "last_5_fp_avg": 42.1,
    "last_10_fp_avg": 38.7,
    "fp_ceiling": 89.0,
    "fp_floor": 8.0,
    "fp_consistency": 0.42
  },
  "career": {
    "t20_matches": 312,
    "t20_runs": 11854,
    "t20_avg": 49.2
  }
}
```

---

### GET `/api/v1/players/{player_id}/matchups`

Batter vs bowler-type breakdown.

**Response 200:**
```json
{
  "matchups": [
    {
      "bowler_type": "pace_left",
      "balls_faced": 412,
      "strike_rate": 118.2,
      "avg_runs": 34.1,
      "dismissal_rate": 0.019,
      "boundary_rate": 0.21
    }
  ]
}
```

---

## 4. Predictions

### POST `/api/v1/predict/team`

Generate fantasy team(s) for a match.

**Request:**
```json
{
  "match_id": "1535465",
  "mode": "grand_league",
  "count": 1,
  "override_toss": null,
  "override_playing_xi": null
}
```

**`mode`:** `"safe"` | `"grand_league"` | `"aggressive"` | `"small_league"`  
**`count`:** 1–20 (Premium: up to 20, Free: max 1)

**Response 200:**
```json
{
  "prediction_id": "uuid",
  "match_id": "1535465",
  "mode": "grand_league",
  "generated_at": "2026-06-25T10:30:00Z",
  "teams": [
    {
      "players": [
        {
          "player_id": "uuid",
          "full_name": "Virat Kohli",
          "role": "BAT",
          "credits": 10.5,
          "predicted_fp": 52.3,
          "fp_ceiling": 89.0,
          "confidence": 87,
          "is_differential": false,
          "ownership_estimate": "68%",
          "explanation": "Chasing specialist with venue avg 72. Last 5 T20s: 48.3 avg FP."
        }
      ],
      "captain": { "player_id": "uuid", "full_name": "Virat Kohli", "confidence": 87 },
      "vice_captain": { "player_id": "uuid", "full_name": "JR Hazlewood", "confidence": 71 },
      "total_credits": 98.5,
      "predicted_total_fp": 498.2,
      "team_ceiling": 712.0
    }
  ],
  "ensemble_weights": { "ml": 0.40, "human_rules": 0.30, "form": 0.20, "live": 0.10 }
}
```

**Errors:**
- `400 BAD_REQUEST`: Invalid match_id or mode
- `402 PAYMENT_REQUIRED`: count > 1 on Free tier
- `404 NOT_FOUND`: Match not found
- `429 TOO_MANY_REQUESTS`: Rate limit exceeded

---

### POST `/api/v1/predict/team/portfolio`

Generate all 4 modes in one request (Premium only).

**Request:**
```json
{ "match_id": "1535465" }
```

**Response 200:** Map of mode → team (same structure as above for each mode).

---

### POST `/api/v1/predict/captain`

Get captain ranking for a match.

**Request:**
```json
{ "match_id": "1535465", "mode": "grand_league" }
```

**Response 200:**
```json
{
  "recommendations": [
    {
      "rank": 1,
      "player_id": "uuid",
      "full_name": "Virat Kohli",
      "type": "best_captain",
      "ceiling_score": 89.0,
      "confidence": 87,
      "reasoning": "Chasing specialist, highest ceiling in this match context"
    },
    {
      "rank": 2,
      "player_id": "uuid",
      "full_name": "JR Hazlewood",
      "type": "safe_captain",
      "ceiling_score": 74.0,
      "confidence": 71,
      "reasoning": "Consistent wicket-taker, pace-friendly venue"
    },
    {
      "rank": 3,
      "player_id": "uuid",
      "full_name": "Arshad Khan",
      "type": "risk_captain",
      "ceiling_score": 95.0,
      "confidence": 41,
      "reasoning": "Death specialist, high ceiling, only 4% ownership — GL differentiator"
    }
  ]
}
```

---

### GET `/api/v1/predict/differentials/{match_id}`

Low-ownership, high-ceiling picks for grand leagues.

**Response 200:**
```json
{
  "differentials": [
    {
      "player_id": "uuid",
      "full_name": "Arshad Khan",
      "ownership_estimate": "4%",
      "ceiling_score": 95.0,
      "fp_avg_5": 28.3,
      "reason": "Death-overs specialist, dry flat pitch, opposition tail vulnerable"
    }
  ]
}
```

---

### GET `/api/v1/explain/{match_id}/{player_id}`

Detailed player selection rationale.

**Response 200:**
```json
{
  "player_id": "uuid",
  "full_name": "Virat Kohli",
  "match_id": "1535465",
  "explanation": "Virat Kohli is a strong pick today...",
  "factors": [
    { "factor": "Recent Form", "value": "Excellent", "detail": "48.3 avg FP last 5 T20s" },
    { "factor": "Venue Average", "value": "72 runs", "detail": "Career best at this venue" },
    { "factor": "Matchup", "value": "Positive", "detail": "SR 142 vs pace (Right-arm)" },
    { "factor": "Context", "value": "Chasing", "detail": "54.2 chasing avg vs 34.1 setting" }
  ],
  "rules_fired": ["RULE-0001", "RULE-0301"],
  "confidence": 87,
  "predicted_fp": 52.3,
  "fp_ceiling": 89.0,
  "fp_floor": 12.0
}
```

---

## 5. AI Chat

### POST `/api/v1/chat`

Ask the AI assistant a fantasy cricket question.

**Request:**
```json
{
  "match_id": "1535465",
  "message": "Why not pick Rohit Sharma as captain today?",
  "session_id": "uuid-optional"
}
```

**Response 200:**
```json
{
  "session_id": "uuid",
  "answer": "Rohit averages 28 while setting at this venue vs his 54 chasing average. Today RCB are fielding first, making Rohit a setting captain — a lower ceiling pick. Virat Kohli, who excels while chasing, is a stronger captain option.",
  "related_players": ["Virat Kohli", "Rohit Sharma"],
  "sources_used": ["rolling_features", "human_rules:RULE-0001"]
}
```

**Free tier limit:** 5 messages per match. Returns `402` when exceeded.

---

## 6. Live

### GET `/api/v1/live/{match_id}`

WebSocket upgrade endpoint for live match intelligence.

See `docs/WEBSOCKET_SPEC.md` for event payloads.

---

## 7. Admin

All admin endpoints require `role=admin` in JWT.

### POST `/api/v1/admin/ingest`
Trigger Cricsheet data ingestion job.

```json
{ "source": "cricsheet_latest", "incremental": true }
```

### POST `/api/v1/admin/retrain`
Queue model retraining.

```json
{ "format": "T20", "model_ids": ["M-01", "M-02", "M-03"] }
```

### GET `/api/v1/admin/metrics`
Prediction accuracy KPIs.

### POST `/api/v1/admin/rules`
Create a new human rule (body = rule JSON per RULE_SCHEMA.json).

### PATCH `/api/v1/admin/rules/{rule_id}`
Update or deactivate a rule.

---

## 8. Health

### GET `/health`

```json
{ "status": "ok", "version": "0.5.0", "timestamp": "2026-06-25T10:00:00Z" }
```

No auth required.

---

## 9. Error Response Format

All errors follow:

```json
{
  "error": {
    "code": "PLAYER_NOT_FOUND",
    "message": "Player with id 'xyz' does not exist",
    "details": {},
    "request_id": "uuid"
  }
}
```

See `backend/ERROR_CODES.md` for full error code reference.
