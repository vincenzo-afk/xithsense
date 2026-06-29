# End-to-End Scenarios

Full system walkthroughs from API call to database and back.

---

## E2E-01: Premium User Generates GL Portfolio

**Actor:** Premium user  
**Pre-conditions:** User logged in; IPL match 1539584 upcoming; playing XI confirmed

```
1. CLIENT
   POST /api/v1/predict/team/portfolio
   Authorization: Bearer <premium_jwt>
   Body: {"match_id": "1539584"}

2. API → JWT middleware
   Decode JWT → user_id, role=premium
   Check rate limit (Redis) → OK

3. API → Feature gate
   check_premium_access(user) → True

4. API → prediction_service.generate_portfolio(match_id, user)

5. prediction_service → load_match (Redis cache hit) → match data
   prediction_service → load_playing_xi (DB query) → 22 players

6. prediction_service → feature_service.load_features (22 players)
   → asyncio.gather: 22 parallel Redis lookups
   → 19 cache hits, 3 cache misses → DB query for 3 → store in Redis

7. prediction_service → ml_service.batch_predict (feature_matrix 22×47)
   → XGBoost.predict → 22 FP scores
   → LightGBM.predict → 22 FP scores
   → CatBoost.predict → 22 FP scores
   → ensemble: mean of 3 models

8. prediction_service → rules_engine.evaluate_all (22 players, match_context)
   → RULE-0001 fires for Kohli (+19.14)
   → RULE-0004 fires for Bumrah (+25.48)
   → 6 other rules fire for various players

9. prediction_service → ensemble.combine (ml + rules + form + live)
   → Final ranked list of 22 players

10. For each mode (safe, grand_league, aggressive, small_league):
    → optimizer.solve(players, scores, mode)
    → LP solves in 200–350ms each
    → captain_engine.recommend(team, mode)

11. asyncio.gather: 44 LLM explanation calls (11 players × 4 teams)
    → 38 Redis cache hits
    → 6 LLM API calls (Claude) → cache results

12. DB write (async, non-blocking for response):
    INSERT prediction, 22 predicted_player rows, 4 recommended_team rows, 44 team_player rows

13. API → build response (prediction_id, 4 teams with explanations)

14. CLIENT receives response:
    {
      "prediction_id": "uuid",
      "teams": {
        "safe": {..., "players": [11], "captain": {...}},
        "grand_league": {...},
        "aggressive": {...},
        "small_league": {...}
      }
    }
    Total wall-clock time: 2.1 seconds
```

---

## E2E-02: Toss Announced → Prediction Refresh → Notification

```
1. Admin/system calls PATCH /api/v1/admin/matches/1539584
   Body: {"toss_winner": "India", "toss_decision": "bat"}
   → match.toss_winner and toss_decision updated in DB

2. DB trigger (or post-update hook) queues Celery task:
   send_toss_notification.delay(match_id="1539584")
   refresh_predictions.delay(match_id="1539584", trigger="toss")

3. refresh_predictions task:
   → Invalidates Redis cache keys for match 1539584
   → Re-runs prediction pipeline with toss context
   → is_chasing updates for all players
   → RULE-0001 (Kohli chasing) now fires (was conditional on is_chasing)
   → New ensemble scores computed
   → New teams generated
   → New explanations generated (or served from cache if unchanged)
   → prediction stored with match_phase="post_toss"

4. send_toss_notification task:
   → Load all premium users subscribed to match 1539584 format
   → For each user:
     check notification preferences (telegram_enabled, EVT-02=True)
     → queue send_telegram_message.delay(chat_id, formatted_message)

5. Telegram messages delivered within 45 seconds of toss
   → Message: "Toss Result! India elected to bat. Updated captain: Rohit Sharma (74%)"
```

---

## E2E-03: User Cancels Subscription → Access Revoked at Period End

```
1. POST /api/v1/payments/cancel
   Authorization: Bearer <premium_jwt>
   → subscription.status = "cancelled"
   → subscription.cancelled_at = NOW()
   → role stays "premium" (access until period_end)
   → Razorpay API called: client.subscription.cancel(sub_id)

2. Celery Beat scheduler (daily at midnight):
   check_expired_subscriptions()
   → SELECT * FROM subscription WHERE status='cancelled' AND current_period_end < NOW()
   → For each: UPDATE user SET role='free'
               UPDATE subscription SET status='expired'

3. Next user login: JWT issued with role='free'
   → All premium features blocked
   → User sees upgrade prompt in app
```
