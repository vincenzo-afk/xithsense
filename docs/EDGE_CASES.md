# Edge Cases

## Data Edge Cases

| ID | Edge Case | System Behaviour |
|----|-----------|-----------------|
| EC-01 | Match with no result (rain, DLS) | `is_complete=false`, `match_winner=null`; prediction still generated using historical data |
| EC-02 | Player plays in only 1 or 2 matches (new player) | Features computed from available matches; `low_data=true` flag set; confidence capped at 50% |
| EC-03 | Same player in both teams (multi-team tournament format) | Impossible in cricket — handled by unique `(match_id, player_id)` constraint |
| EC-04 | Wide ball that also results in a wicket | `is_wide=true AND is_wicket=true` — both fields set; wicket not credited to bowler per Laws |
| EC-05 | Player listed twice in Cricsheet with different key formats | Deduplication via `cricsheet_key` normalisation; merge script in `scripts/dedup_players.py` |
| EC-06 | Test match with 4 innings | All 4 innings parsed; fantasy points computed per innings and summed |
| EC-07 | Match abandoned mid-innings | Partial deliveries stored; `is_complete=false` on match |
| EC-08 | No toss result in Cricsheet metadata | `toss_winner=null`, `toss_decision=null`; live context weight set to 0 |
| EC-09 | Player of the match field has multiple players | Stored as array; used for validation only, not prediction target |
| EC-10 | Venue name changes across seasons (renamed stadium) | Venue alias table maps historical names to canonical venue_id |
| EC-11 | Substitute fielder takes a catch | Fielder stored in `wicket_fielder`; no fantasy points awarded to substitute |
| EC-12 | Super Over | Parsed as separate innings; tagged `is_super_over=true` (schema addition in migration 0013) |

---

## Prediction Edge Cases

| ID | Edge Case | System Behaviour |
|----|-----------|-----------------|
| EC-20 | Match has fewer than 22 players (only 14 available) | Optimizer must still form valid 11; reduces mode variety; logs warning |
| EC-21 | All available players belong to one team (one team forfeits) | Constraint violation detected pre-optimization; return `400 PREDICTION_NO_PLAYERS` |
| EC-22 | Credits don't allow any valid 11-player combination | LP infeasible → DEAP fallback; if still no solution, relax WK/AR max limits by 1 |
| EC-23 | Two players have identical ensemble scores | Tie broken by `fp_consistency` (lower is better for ranking) |
| EC-24 | LLM API times out during explanation generation | Return fallback template explanation; mark `explanation_source=fallback` in response |
| EC-25 | Same player is predicted top captain in all 4 team modes | Allowed; each mode can have the same captain |
| EC-26 | Player marked unavailable after prediction generated | Add `stale_warning: true` field to response on next fetch; prompt user to regenerate |
| EC-27 | Feature vector has >20% missing values for a player | Prediction proceeds with global fallback values; confidence reduced by 20 points |

---

## Payment Edge Cases

| ID | Edge Case | System Behaviour |
|----|-----------|-----------------|
| EC-30 | Razorpay webhook received twice (duplicate) | Idempotency key check; second webhook is a no-op |
| EC-31 | Payment captured but webhook delayed 30 minutes | User shown "pending" status; webhook activates Premium when it arrives |
| EC-32 | User cancels mid-Razorpay-checkout | No subscription created; user remains on Free |
| EC-33 | Subscription expires during an active match window | Premium access retained until end of period_end timestamp |
| EC-34 | Annual subscriber requests refund after 8 days | >7 days: no refund (per policy); explain policy clearly in response |

---

## API Edge Cases

| ID | Edge Case | System Behaviour |
|----|-----------|-----------------|
| EC-40 | Request body has extra unknown fields | Pydantic `model_config = ConfigDict(extra='ignore')` — silently ignored |
| EC-41 | `count=0` in team prediction request | Return `422 VALIDATION_ERROR` (minimum is 1) |
| EC-42 | `match_id` is valid but match is in the past | Prediction generated using historical XI; response includes `historical_warning=true` |
| EC-43 | Chat message with 0 characters | Return `422` with "message must not be empty" |
| EC-44 | WebSocket connection drops mid-match | Client auto-reconnects; server resumes from latest state |
| EC-45 | Admin triggers retrain while another retrain is running | Second request queued; runs after first completes |
