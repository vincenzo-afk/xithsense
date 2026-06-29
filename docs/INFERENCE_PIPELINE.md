# Inference Pipeline

**Entry point:** `backend/services/prediction_service.py → predict_match(match_id, mode, user)`  
**Latency target:** < 3 seconds for 4-mode portfolio

---

## Pipeline Steps

```
predict_match(match_id, mode)
│
├── 1. LOAD MATCH CONTEXT
│       load_match(match_id)          → DB query (cached 10 min)
│       load_playing_xi(match_id)     → DB query (cached 5 min)
│       build_match_context(match)    → toss, venue, pitch, weather
│
├── 2. LOAD PLAYER FEATURES
│       for each player in XI (22 players):
│           load_rolling_features(player_id, match_type)    → Redis → DB
│           load_venue_features(player_id, venue_id)        → Redis → DB
│           load_matchup_features(player_id, opp_bowling)   → Redis → DB
│           compute_context_features(player, match_context) → inline
│           assemble_feature_vector(player)                 → 47-dim array
│
├── 3. ML PREDICTION
│       ml_scores = {}
│       for model in [xgb, lgb, cat]:
│           scores = model.predict(feature_matrix)    → batch predict all 22
│       ml_scores = mean([xgb, lgb, cat], axis=0)    → 22 FP predictions
│
├── 4. HUMAN RULES EVALUATION
│       for each player:
│           rules_adj, rules_fired = evaluate_rules(player, match_context)
│       rules_scores = normalise(rules_adj)
│
├── 5. FORM SCORE
│       form_scores[player] = (
│           fp_avg_3 × 0.50 +
│           fp_avg_5 × 0.30 +
│           fp_avg_10 × 0.20
│       )
│       form_scores = normalise(form_scores)
│
├── 6. LIVE CONTEXT (if available)
│       live_scores = load_live_context(match_id)    → 0 if pre-match
│       live_scores = normalise(live_scores)
│
├── 7. ENSEMBLE
│       for each player:
│           ensemble_score = (
│               0.40 × ml_norm[i]    +
│               0.30 × rules_norm[i] +
│               0.20 × form_norm[i]  +
│               0.10 × live_norm[i]
│           )
│       Sort players by ensemble_score DESC
│
├── 8. TEAM OPTIMISATION
│       team = lp_optimizer.solve(players, scores, mode)
│       if infeasible: team = deap_optimizer.solve(players, scores, mode)
│       captain, vc = captain_engine.recommend(team, mode)
│
├── 9. EXPLANATION GENERATION
│       for each player in team:
│           explanation = llm_explainer.explain(player, match_context)
│                         [Redis cache check first]
│
├── 10. PERSIST
│       prediction_id = db.insert(prediction, predicted_players, recommended_team)
│
└── 11. RETURN
        PredictionResponse(prediction_id, team, explanations, ensemble_weights)
```

---

## Caching Strategy Within Pipeline

| Step | Cache Key | TTL |
|------|-----------|-----|
| Match context | `match:{match_id}` | 10 min |
| Playing XI | `xi:{match_id}` | 5 min (refreshed on EVT-01) |
| Rolling features | `feat:{player_id}:{match_type}:{date}` | 6 hours |
| Venue features | `venue:{player_id}:{venue_id}` | 24 hours |
| Matchup features | `matchup:{player_id}:{bowler_type}` | 24 hours |
| LLM explanation | `explain:{match_id}:{player_id}:{phase}` | 1 hour |
| Full prediction | `pred:{match_id}:{mode}:{phase}` | 30 min (post-toss) |

---

## Parallelism

Steps 2–6 are parallelised using `asyncio.gather`:

```python
features = await asyncio.gather(*[
    load_all_features(player_id, match_context)
    for player_id in playing_xi
])
```

LLM explanations for all 11 players generated concurrently:

```python
explanations = await asyncio.gather(*[
    llm_explainer.explain(player, match_context)
    for player in team.players
])
```

---

## Error Recovery Within Pipeline

| Step | Error | Recovery |
|------|-------|---------|
| Feature load failure | Missing rolling feature | Use global role average |
| ML model failure | Model not found | Fall back to form-only (rules+form, reweight to 0/50/50/0) |
| LP infeasible | No solution | DEAP genetic algorithm |
| LLM timeout | API timeout > 5s | Fallback template explanation |
| DB write failure | Insert error | Log and return response anyway; retry DB write async |
