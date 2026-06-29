# Acceptance Criteria

**Definition of Done:** A feature is complete when ALL criteria for its section are met, tests pass, and documentation is updated.

---

## AC-01: Data Ingestion

- [ ] Running `python scripts/ingest_cricsheet.py --source data/raw/all_json.zip` completes without errors
- [ ] All 22,062 match records are present in the `match` table
- [ ] Total row count in `delivery` table ≥ 4,000,000
- [ ] No duplicate deliveries (verified by unique constraint on innings_id + over + ball)
- [ ] `player_match_performance` populated for every player in every match
- [ ] Incremental run (`--incremental`) processes only new files
- [ ] Ingestion runtime < 30 minutes for full dataset on standard hardware
- [ ] Error log created for any malformed files; pipeline continues

---

## AC-02: Feature Engineering

- [ ] `rolling_feature` table populated for all players with windows 3, 5, 10
- [ ] `venue_stat` populated for all venues with ≥ 5 matches
- [ ] `matchup_stat` populated for all batter/bowler-type pairs with ≥ 30 balls faced
- [ ] `fp_avg_5` for any player with 5 matches matches manual calculation (within 0.01 tolerance)
- [ ] `fp_ceiling` = 90th percentile of last 10 fantasy points (verified for 5 random players)
- [ ] Missing value fallbacks applied: no NULL in any feature column used by models
- [ ] `build_features.py --from 2026-01-01` runs in < 5 minutes
- [ ] Redis cache key exists after feature build; cache TTL = 6 hours

---

## AC-03: Fantasy Points Computation

- [ ] A player scoring 60 runs (with 1×4, 2×6) earns: 60 + 1 + 4 + 8 = 73 pts
- [ ] A bowler taking 3 wickets earns: 75 pts
- [ ] A wicketkeeper taking 2 stumpings earns: 24 pts
- [ ] A duck dismissal for a batter deducts 2 pts
- [ ] 5-wicket haul earns base 125 pts + 16 bonus = 141 pts
- [ ] All `fantasy_points` values verified against 10 randomly selected real matches

---

## AC-04: Human Rules Engine

- [ ] All rules in all JSON files pass `python human_rules/validate_rules.py` with zero errors
- [ ] Rule `RULE-0001` fires when player_key = "Kohli, V" and `is_chasing=true` in T20
- [ ] Effective impact = `impact_score * confidence` (verified in unit test)
- [ ] Rules with `is_active=false` do not fire
- [ ] Rules outside `valid_from`/`valid_until` dates do not fire
- [ ] `rule_trigger` table log entry created for every fired rule
- [ ] Admin can add, deactivate, and delete a rule via `POST/PATCH /api/v1/admin/rules`
- [ ] Minimum 50 active player rules, 20 venue rules, 15 matchup rules, 15 context rules loaded at startup

---

## AC-05: ML Models

- [ ] Model M-01 (XGBoost T20) trained without errors and artifact saved to `models/artifacts/`
- [ ] M-01 validation MAE < 14 points on 2025 held-out T20 matches
- [ ] M-01 rank correlation (Spearman ρ) > 0.60 on held-out test set
- [ ] `ModelRegistry` correctly identifies active model for format "T20"
- [ ] Model prediction returns a float between 0 and 200 for any valid input vector
- [ ] Training run completes in < 60 minutes on CPU

---

## AC-06: Ensemble Engine

- [ ] `predict_match(match_id)` returns ranked list of all available players
- [ ] Each player in output has: `ensemble_score`, `ml_score`, `rules_score`, `form_score`, `confidence`
- [ ] Ensemble weights sum to 1.0
- [ ] Changing `ENSEMBLE_ML_WEIGHT` in env vars affects output without code changes
- [ ] Output is deterministic for same inputs (no random state in ensemble)
- [ ] Prediction completes in < 1 second for a 22-player match

---

## AC-07: Team Optimizer

- [ ] Every generated team has exactly 11 players
- [ ] Total credits ≤ 100.0 (verified for 100 random generated teams)
- [ ] No team has more than 7 players from one real team
- [ ] Role counts satisfy: WK ∈ [1,4], BAT ∈ [3,6], AR ∈ [1,4], BOWL ∈ [3,6]
- [ ] `mode=grand_league` selects at least 1 player with ownership < 20%
- [ ] `mode=safe` selects players with higher `fp_consistency` than `mode=grand_league`
- [ ] 4-mode portfolio generation completes in < 3 seconds
- [ ] DEAP fallback activates when LP finds no feasible solution (test with extreme credit constraints)
- [ ] Free user requesting `count > 1` receives `402 PAYMENT_REQUIRED`

---

## AC-08: Captain Engine

- [ ] `predict_captain()` returns at least 3 recommendations: best, safe, risk
- [ ] `type=risk_captain` has lower confidence than `type=best_captain`
- [ ] Captain cannot be the same player as Vice-Captain
- [ ] Both captain and VC are from the predicted team's player list
- [ ] Confidence scores are in range [1, 100]

---

## AC-09: Explainability Engine

- [ ] Every player returned by `predict_team` has a non-empty `explanation` string
- [ ] Explanation includes at least 3 data-backed factors
- [ ] LLM provider switch works: setting `LLM_PROVIDER=openai` uses OpenAI; `anthropic` uses Claude
- [ ] Explanations cached in Redis; second call for same player returns cached response
- [ ] Explanation generated in < 5 seconds per player
- [ ] LLM failure gracefully falls back to template explanation; does not crash API

---

## AC-10: API

- [ ] `GET /health` returns `{"status": "ok"}` with HTTP 200, no auth required
- [ ] `POST /api/v1/auth/register` creates a new user and returns a JWT
- [ ] `POST /api/v1/predict/team` with valid match_id returns a valid team in < 3 seconds
- [ ] `POST /api/v1/chat` returns a relevant answer to "Who should I captain today?"
- [ ] All endpoints return `401` for missing/invalid JWT
- [ ] Free user calling `predict/team` with `count=5` returns `402`
- [ ] Rate limit of 30 RPM for free users enforced; 31st request returns `429`
- [ ] All error responses follow `{"error": {"code": ..., "message": ...}}` format
- [ ] Swagger docs accessible at `/docs`

---

## AC-11: Backtesting

- [ ] `make backtest` runs on ≥ 10,000 historical T20 matches without errors
- [ ] Captain accuracy on 2025 IPL held-out set ≥ 38%
- [ ] Correct-player rate (≥ 7 correct in top 11) ≥ 58% on 2025 held-out set
- [ ] Results stored in `backtest_run` table
- [ ] `--format IPL --n 1000` filters correctly to IPL matches only

---

## AC-12: Notifications

- [ ] Telegram message sent within 2 minutes of playing XI announcement for subscribed users
- [ ] User can enable/disable notification types via API
- [ ] Failed delivery logged; retry attempted once

---

## AC-13: Payments

- [ ] New subscription via Razorpay creates `subscription` record with `status=active`
- [ ] Premium role granted within 60 seconds of successful payment webhook
- [ ] Cancellation webhook sets `status=cancelled` and records `cancelled_at`
- [ ] Sandbox payment flow tested end-to-end with Razorpay test credentials

---

## AC-14: Security

- [ ] OWASP ZAP scan returns zero High or Critical findings
- [ ] SQL injection test: `' OR 1=1 --` in search query returns 400, not 500
- [ ] JWT signed with RS256 or HS256 (min 256-bit secret)
- [ ] Password stored as bcrypt hash (cost ≥ 12); raw password never logged
- [ ] Sensitive env vars absent from all log output
- [ ] Admin endpoints return `403` for non-admin JWT

---

## AC-15: Performance

- [ ] `POST /api/v1/predict/team` p95 < 500ms under 100 concurrent users (k6 load test)
- [ ] API handles 1,000 concurrent connections without 5xx errors
- [ ] Redis hit rate > 80% during a 10-minute sustained load test
- [ ] Memory usage < 2GB under peak load
