# API Examples

Complete request/response examples for every major endpoint with real match data.

---

## Authentication

### Register
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "arjun@example.com",
  "password": "Fantasy@Cricket2026",
  "full_name": "Arjun Mehta"
}
```
```json
HTTP/1.1 201 Created
{
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "arjun@example.com",
  "role": "free",
  "access_token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhMWIyYzNkNC1lNWY2LTc4OTAtYWJjZC1lZjEyMzQ1Njc4OTAiLCJyb2xlIjoiZnJlZSIsImV4cCI6MTc1MDkxNjQwMH0.sig",
  "token_type": "bearer"
}
```

---

## Match Endpoints

### List Upcoming Matches
```http
GET /api/v1/matches/upcoming?format=T20&limit=5
Authorization: Bearer eyJ...
```
```json
HTTP/1.1 200 OK
{
  "matches": [
    {
      "id": "1539584",
      "team_a": "India",
      "team_b": "Australia",
      "venue": "Wankhede Stadium, Mumbai",
      "match_date": "2026-06-27",
      "match_type": "T20",
      "event": "India vs Australia T20I Series",
      "event_stage": "3rd T20I",
      "prediction_ready": true,
      "playing_xi_confirmed": true,
      "toss_done": false
    }
  ],
  "total": 1
}
```

### Get Match Detail
```http
GET /api/v1/matches/1535465
Authorization: Bearer eyJ...
```
```json
HTTP/1.1 200 OK
{
  "id": "1535465",
  "match_type": "T20",
  "gender": "male",
  "team_a": "Gujarat Titans",
  "team_b": "Royal Challengers Bengaluru",
  "venue_name": "Narendra Modi Stadium, Ahmedabad",
  "city": "Ahmedabad",
  "toss": {"winner": "Royal Challengers Bengaluru", "decision": "field"},
  "outcome": {"winner": "Royal Challengers Bengaluru", "by": {"wickets": 5}},
  "season": "2026",
  "event_name": "Indian Premier League",
  "event_stage": "Final",
  "match_date": "2026-05-25",
  "player_of_match": ["V Kohli"],
  "prediction_ready": true,
  "playing_xi_confirmed": true
}
```

---

## Player Endpoints

### Search Players
```http
GET /api/v1/players/search?q=kohli&role=BAT
Authorization: Bearer eyJ...
```
```json
HTTP/1.1 200 OK
{
  "players": [
    {
      "id": "d4e5f6a7-b8c9-0123-defa-bc4567890123",
      "full_name": "Virat Kohli",
      "short_name": "V Kohli",
      "primary_role": "BAT",
      "batting_style": "Right-hand bat",
      "bowling_style": "Right-arm medium",
      "nationality": "India",
      "is_active": true
    }
  ],
  "total": 1
}
```

### Get Player Matchups
```http
GET /api/v1/players/d4e5f6a7-b8c9-0123-defa-bc4567890123/matchups
Authorization: Bearer eyJ...
```
```json
HTTP/1.1 200 OK
{
  "player_id": "d4e5f6a7-b8c9-0123-defa-bc4567890123",
  "full_name": "Virat Kohli",
  "match_type": "T20",
  "matchups": [
    {
      "bowler_type": "pace_right",
      "balls_faced": 1842,
      "strike_rate": 138.4,
      "avg_runs": 51.2,
      "dismissal_rate": 0.019,
      "boundary_rate": 0.24,
      "confidence": 1.0
    },
    {
      "bowler_type": "pace_left",
      "balls_faced": 612,
      "strike_rate": 121.6,
      "avg_runs": 38.4,
      "dismissal_rate": 0.028,
      "boundary_rate": 0.18,
      "confidence": 0.87
    },
    {
      "bowler_type": "spin_off",
      "balls_faced": 924,
      "strike_rate": 145.2,
      "avg_runs": 56.1,
      "dismissal_rate": 0.016,
      "boundary_rate": 0.27,
      "confidence": 0.95
    }
  ]
}
```

---

## Prediction Endpoints

### Generate Safe Team (Free User)
```http
POST /api/v1/predict/team
Authorization: Bearer eyJ...free-user-token...
Content-Type: application/json

{
  "match_id": "1535465",
  "mode": "safe",
  "count": 1
}
```
```json
HTTP/1.1 200 OK
{
  "prediction_id": "e5f6a7b8-c9d0-1234-efab-cd5678901234",
  "match_id": "1535465",
  "mode": "safe",
  "match_phase": "post_toss",
  "generated_at": "2026-05-25T14:32:00Z",
  "teams": [{
    "players": [
      {
        "player_id": "d4e5f6a7-b8c9-0123-defa-bc4567890123",
        "full_name": "Virat Kohli",
        "role": "BAT",
        "credits": 10.5,
        "predicted_fp": 65.2,
        "fp_ceiling": 116.0,
        "fp_floor": 18.0,
        "confidence": 87,
        "is_differential": false,
        "ownership_estimate": "68%",
        "explanation": "Kohli is the standout pick as a chasing specialist. Last 5 T20s avg: 68.3 FP. Career chasing avg 54.2 runs. Confidence: High."
      },
      {
        "player_id": "e5f6a7b8-c9d0-1234-efab-cd5678901234",
        "full_name": "Jasprit Bumrah",
        "role": "BOWL",
        "credits": 10.0,
        "predicted_fp": 48.1,
        "fp_ceiling": 87.0,
        "fp_floor": 10.0,
        "confidence": 82,
        "is_differential": false,
        "ownership_estimate": "55%",
        "explanation": "Bumrah's death-overs dominance is elite. Economy 6.8 at death (last 5 matches), 2.4 wickets avg per game. Confidence: High."
      }
    ],
    "captain": {
      "player_id": "d4e5f6a7-b8c9-0123-defa-bc4567890123",
      "full_name": "Virat Kohli",
      "confidence": 87,
      "ceiling_score": 116.0,
      "type": "best_captain",
      "reasoning": "Chasing specialist, highest ceiling, venue avg 72 runs"
    },
    "vice_captain": {
      "player_id": "e5f6a7b8-c9d0-1234-efab-cd5678901234",
      "full_name": "Jasprit Bumrah",
      "confidence": 71,
      "type": "safe_vc"
    },
    "total_credits": 98.5,
    "predicted_total_fp": 498.2,
    "team_ceiling": 712.0,
    "solver_used": "lp",
    "solve_time_ms": 287
  }],
  "ensemble_weights": {"ml": 0.40, "human_rules": 0.30, "form": 0.20, "live": 0.10}
}
```

### Explain a Player Selection
```http
GET /api/v1/explain/1535465/d4e5f6a7-b8c9-0123-defa-bc4567890123
Authorization: Bearer eyJ...
```
```json
HTTP/1.1 200 OK
{
  "player_id": "d4e5f6a7-b8c9-0123-defa-bc4567890123",
  "full_name": "Virat Kohli",
  "match_id": "1535465",
  "explanation": "Virat Kohli is the top pick for this match. He averages 68.3 fantasy points over his last 5 T20s with a ceiling of 116 and a floor of 18. His career chasing average is 54.2 — 60% higher than when setting. The toss confirms RCB field first, so Kohli bats in chase. His venue average at Ahmedabad is 72 runs. Two specialist rules boosted his score. Confidence: High (87%).",
  "factors": [
    {"factor": "Recent Form",    "value": "Excellent",  "detail": "68.3 avg FP last 5 T20s"},
    {"factor": "Venue Record",   "value": "Outstanding","detail": "72 run career avg at Ahmedabad"},
    {"factor": "Chasing Bonus",  "value": "+19.1 pts",  "detail": "Rule RULE-0001: chasing specialist"},
    {"factor": "Matchup",        "value": "Positive",   "detail": "SR 138.4 vs right-arm pace (1842 balls)"}
  ],
  "rules_fired": ["RULE-0001"],
  "confidence": 87,
  "predicted_fp": 65.2,
  "fp_ceiling": 116.0,
  "fp_floor": 18.0,
  "ensemble_breakdown": {
    "ml_score_norm": 0.82,
    "rules_score_norm": 0.91,
    "form_score_norm": 0.88,
    "live_score_norm": 0.0
  }
}
```

---

## Chat Endpoint

```http
POST /api/v1/chat
Authorization: Bearer eyJ...premium-token...
Content-Type: application/json

{
  "match_id": "1535465",
  "message": "Should I use Maxwell in grand league today?",
  "session_id": null
}
```
```json
HTTP/1.1 200 OK
{
  "session_id": "f6a7b8c9-d0e1-2345-fabc-de6789012345",
  "answer": "Maxwell is a risky pick today. Rule RULE-0201 flags his weakness against quality spin on turning tracks — Chepauk yesterday was spin-friendly, and Ahmedabad shows moderate spin assistance. His last 5 T20s avg FP is 28.3 with high volatility (consistency CV: 0.91). For safe teams, avoid. For grand league, he's a low-upside differential — Noor Ahmad (4% ownership, 95 ceiling) is a stronger differential choice.",
  "related_players": ["Maxwell, GJ", "Noor Ahmad"],
  "sources_used": ["rolling_features", "matchup_stats", "human_rules:RULE-0201", "venue_stats"]
}
```

---

## WebSocket Payloads

### Connect
```
wss://api.xithsense.com/api/v1/live/1535465?token=eyJ...
```

### Server → Client: `match_update`
```json
{
  "event": "match_update",
  "match_id": "1535465",
  "timestamp": "2026-05-25T18:42:15Z",
  "live_score": {
    "batting_team": "Gujarat Titans",
    "runs": 142,
    "wickets": 4,
    "overs": "16.3",
    "crr": 8.49
  },
  "win_probability": {
    "Gujarat Titans": 0.34,
    "Royal Challengers Bengaluru": 0.66
  },
  "required_run_rate": 12.4
}
```

### Server → Client: `player_update`
```json
{
  "event": "player_update",
  "player_id": "d4e5f6a7-b8c9-0123-defa-bc4567890123",
  "full_name": "Virat Kohli",
  "live_fantasy_points": 52.0,
  "runs_scored": 39,
  "balls_faced": 27,
  "fours": 3,
  "sixes": 2,
  "wickets_taken": 0,
  "captain_multiplier_applied": true,
  "effective_fp": 104.0
}
```

---

## Error Responses

### 401 Expired Token
```json
{
  "error": {
    "code": "EXPIRED_TOKEN",
    "message": "Authentication token has expired. Please log in again.",
    "details": {},
    "request_id": "a1b2c3d4-1234-5678-abcd-ef1234567890"
  }
}
```

### 402 Premium Required
```json
{
  "error": {
    "code": "PREMIUM_REQUIRED",
    "message": "Grand League teams require a Premium subscription.",
    "details": {"upgrade_url": "https://app.xithsense.com/subscribe", "feature": "gl_team"},
    "request_id": "b2c3d4e5-2345-6789-bcde-fa2345678901"
  }
}
```

### 400 Optimizer Infeasible
```json
{
  "error": {
    "code": "OPTIMIZER_INFEASIBLE",
    "message": "Could not form a valid 11-player team within the credit budget. Try a different match or mode.",
    "details": {"solver": "lp", "fallback_attempted": true},
    "request_id": "c3d4e5f6-3456-7890-cdef-ab3456789012"
  }
}
```

### 429 Rate Limited
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Free plan: 30 requests/minute.",
    "details": {"retry_after_seconds": 38, "limit": 30, "plan": "free"},
    "request_id": "d4e5f6a7-4567-8901-defa-bc4567890123"
  }
}
```
