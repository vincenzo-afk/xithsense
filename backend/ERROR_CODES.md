# Error Codes

All API errors follow this format:
```json
{"error": {"code": "ERROR_CODE", "message": "Human-readable description", "details": {}, "request_id": "uuid"}}
```

## Authentication Errors (4xx)

| HTTP | Code | Description |
|------|------|-------------|
| 401 | `MISSING_TOKEN` | Authorization header absent |
| 401 | `INVALID_TOKEN` | JWT signature invalid or malformed |
| 401 | `EXPIRED_TOKEN` | JWT has expired |
| 403 | `INSUFFICIENT_ROLE` | User lacks required role (e.g. admin route) |
| 402 | `PREMIUM_REQUIRED` | Feature requires Premium subscription |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests; retry after `Retry-After` header |

## Resource Errors (4xx)

| HTTP | Code | Description |
|------|------|-------------|
| 404 | `MATCH_NOT_FOUND` | Match ID does not exist |
| 404 | `PLAYER_NOT_FOUND` | Player ID or key does not exist |
| 404 | `PREDICTION_NOT_FOUND` | Prediction record not found |
| 400 | `INVALID_MATCH_ID` | Match ID format invalid |
| 400 | `INVALID_UUID` | UUID parameter malformed |
| 400 | `INVALID_MODE` | Team mode not one of safe/grand_league/aggressive/small_league |
| 400 | `INVALID_COUNT` | Team count out of range [1, 20] |
| 400 | `MISSING_FIELD` | Required request body field absent |
| 422 | `VALIDATION_ERROR` | Pydantic validation failure (detailed errors in `details`) |

## Prediction Errors (5xx that are domain-specific)

| HTTP | Code | Description |
|------|------|-------------|
| 400 | `PREDICTION_NO_PLAYERS` | No player data available for this match |
| 400 | `OPTIMIZER_INFEASIBLE` | LP found no valid team satisfying Dream11 constraints |
| 400 | `INSUFFICIENT_CREDITS` | Available players cannot form a team within credit budget |
| 503 | `MODEL_UNAVAILABLE` | No active model found for this match format |
| 503 | `LLM_UNAVAILABLE` | LLM API unreachable; fallback explanation used |

## Server Errors (5xx)

| HTTP | Code | Description |
|------|------|-------------|
| 500 | `INTERNAL_ERROR` | Unexpected server error (details logged; request_id for tracing) |
| 503 | `DATABASE_UNAVAILABLE` | Cannot reach PostgreSQL |
| 503 | `CACHE_UNAVAILABLE` | Cannot reach Redis |

## Admin Errors

| HTTP | Code | Description |
|------|------|-------------|
| 400 | `RULE_VALIDATION_FAILED` | Submitted rule does not match RULE_SCHEMA.json |
| 409 | `RULE_ID_EXISTS` | Rule ID already registered |
| 400 | `MODEL_NOT_FOUND` | Requested model version does not exist |
