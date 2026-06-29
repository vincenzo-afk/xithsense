# Entity Relationship Diagram

```
user ──────────────────────── subscription
 │  1                              1
 │                                 │
 │ 1..N                            │
 ▼                                 │
chat_session ─── 1..N ─── chat_message
 │
 │ 1..N
 ▼
prediction ──── 1..N ──── predicted_player
    │                         │
    │ 1..N                    │ N..1
    ▼                         ▼
recommended_team ─ 1..N ─ team_player
    │                         │
    │ N..1                    │ N..1
    ▼                         ▼
  match                     player
    │                         │
    │ 1..N                    │ 1..N
    ▼                         ▼
  innings               player_team_match
    │                         │
    │ 1..N               N..1 │
    ▼                         ▼
  delivery             player_match_performance
                              │
                              │ N..1
                              ▼
                         rolling_feature

venue ──── 1..N ──── venue_stat
  │
  │ 1..N
  ▼
match

player ──── 1..N ──── matchup_stat

human_rule ──── 1..N ──── rule_trigger
                               │ N..1
                               ▼
                          predicted_player

backtest_run ──── 1..N ──── backtest_result

model_version ──── 1..N ──── prediction
```

## Key Relationships

| Parent | Child | Cardinality | Join Key |
|--------|-------|-------------|----------|
| `match` | `innings` | 1:N | `innings.match_id` |
| `innings` | `delivery` | 1:N | `delivery.innings_id` |
| `match` | `player_team_match` | 1:N | `player_team_match.match_id` |
| `player` | `player_match_performance` | 1:N | `player_match_performance.player_id` |
| `player` | `rolling_feature` | 1:N | `rolling_feature.player_id` |
| `player` | `matchup_stat` | 1:N | `matchup_stat.player_id` |
| `venue` | `venue_stat` | 1:N | `venue_stat.venue_id` |
| `prediction` | `predicted_player` | 1:N | `predicted_player.prediction_id` |
| `prediction` | `recommended_team` | 1:N | `recommended_team.prediction_id` |
| `recommended_team` | `team_player` | 1:N | `team_player.team_id` |
| `user` | `prediction` | 1:N | `prediction.user_id` |
| `user` | `subscription` | 1:1 | `subscription.user_id` |
| `user` | `chat_session` | 1:N | `chat_session.user_id` |
| `human_rule` | `rule_trigger` | 1:N | `rule_trigger.rule_id` |
| `backtest_run` | `backtest_result` | 1:N | `backtest_result.run_id` |
