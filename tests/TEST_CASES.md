# Test Cases

## TC-01: Fantasy Points Computation

| ID | Input | Expected Output |
|----|-------|----------------|
| TC-01-01 | 60 runs, 1 four, 2 sixes, not dismissed | 60 + 1 + 4 + 8 = 73 pts |
| TC-01-02 | 50 runs exactly, no dismissal | 50 + 8 (50-bonus) = 58 pts |
| TC-01-03 | 100 runs, 5 fours, 3 sixes | 100 + 5 + 6 + 16 = 127 pts |
| TC-01-04 | 0 runs, dismissed (BAT role) | -2 pts |
| TC-01-05 | 3 wickets, 2 LBW/bowled | 75 + 16 = 91 pts |
| TC-01-06 | 5 wickets | 125 + 16 = 141 pts |
| TC-01-07 | 1 maiden over | 4 pts |
| TC-01-08 | 2 stumpings (WK) | 24 pts |
| TC-01-09 | 1 catch + 1 run out direct | 8 + 12 = 20 pts |
| TC-01-10 | Bowler scores 0 runs (not dismissed) | 0 pts (no duck penalty for bowlers) |

---

## TC-02: Rule Engine

| ID | Scenario | Expected |
|----|---------|---------|
| TC-02-01 | RULE-0001 for player "Kohli, V", is_chasing=True, match_type=IPL | Rule fires, impact = 22 × 0.87 = 19.14 |
| TC-02-02 | RULE-0001 for player "Kohli, V", is_chasing=False | Rule does NOT fire |
| TC-02-03 | RULE-0001 for player "Sharma, R" (wrong player) | Rule does NOT fire |
| TC-02-04 | Rule with is_active=False | Rule never fires regardless of condition |
| TC-02-05 | Rule with valid_until="2025-01-01" evaluated on 2026-01-01 | Rule does NOT fire |
| TC-02-06 | Two rules fire for same player | Both impacts added (additive) |
| TC-02-07 | Rule with confidence=0.0 | Effective impact = 0; rule fires but has no effect |
| TC-02-08 | Rule type=venue, player_key=null | Applies to ALL players in matching condition |

---

## TC-03: Team Optimizer

| ID | Scenario | Expected |
|----|---------|---------|
| TC-03-01 | Standard T20 match, 22 players, mode=safe | Team of 11, total credits ≤ 100 |
| TC-03-02 | Generated team role check | WK in [1,4], BAT in [3,6], AR in [1,4], BOWL in [3,6] |
| TC-03-03 | Max team cap check | No team has > 7 players from same real team |
| TC-03-04 | Captain ≠ Vice-Captain | captain_id != vice_captain_id always |
| TC-03-05 | mode=grand_league | At least 1 player with ownership < 20% |
| TC-03-06 | mode=safe | Team has higher avg fp_consistency than GL team |
| TC-03-07 | count=2 (Premium user) | Returns 2 teams; teams differ by ≥ 2 players |
| TC-03-08 | count=5 (Free user) | Returns 402 PAYMENT_REQUIRED |
| TC-03-09 | LP infeasible (extreme credit setup) | Fallback to DEAP; returns valid team |
| TC-03-10 | All 22 players from same real team | Returns 400 with constraint violation |

---

## TC-04: API Authentication

| ID | Scenario | Expected HTTP |
|----|---------|--------------|
| TC-04-01 | Valid JWT in Authorization header | 200 |
| TC-04-02 | No Authorization header | 401 MISSING_TOKEN |
| TC-04-03 | Expired JWT | 401 EXPIRED_TOKEN |
| TC-04-04 | Tampered JWT signature | 401 INVALID_TOKEN |
| TC-04-05 | Admin endpoint with free user JWT | 403 INSUFFICIENT_ROLE |
| TC-04-06 | Premium endpoint with free user JWT | 402 PREMIUM_REQUIRED |
| TC-04-07 | Rate limit exceeded (31st request in 1 min, free user) | 429 |
| TC-04-08 | Valid JWT, wrong endpoint method | 405 |

---

## TC-05: Prediction Pipeline

| ID | Scenario | Expected |
|----|---------|---------|
| TC-05-01 | Valid match_id, mode=safe | Response contains 11 players |
| TC-05-02 | All 11 players have non-null explanation | True |
| TC-05-03 | All 11 players have confidence in [1, 100] | True |
| TC-05-04 | ensemble_weights sum to 1.0 | True |
| TC-05-05 | Response time for single team | < 3 seconds |
| TC-05-06 | Invalid match_id | 404 MATCH_NOT_FOUND |
| TC-05-07 | Match with no player data | 400 PREDICTION_NO_PLAYERS |
| TC-05-08 | Prediction stored in DB after generation | True (query prediction table) |

---

## TC-06: Cricsheet Ingestion

| ID | Scenario | Expected |
|----|---------|---------|
| TC-06-01 | Parse valid T20 JSON file | match record created, deliveries counted correctly |
| TC-06-02 | Parse IPL final (1535465.json) | Outcome = RCB win by 5 wickets, PoM = Kohli |
| TC-06-03 | Re-ingest same file | Upsert; no duplicate match record |
| TC-06-04 | Malformed JSON file | Error logged; pipeline continues |
| TC-06-05 | File with missing player_of_match | Parsed without error; field = NULL |
| TC-06-06 | Wide ball with wicket | Both is_wide=True and is_wicket=True in delivery |
| TC-06-07 | Test match (4 innings) | 4 innings records created |
| TC-06-08 | Fantasy points for century | FP = 100 + boundaries + 16 bonus (computed correctly) |
