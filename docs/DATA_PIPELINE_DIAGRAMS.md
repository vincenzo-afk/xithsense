# Data Pipeline Diagrams

---

## 1. ETL Pipeline — Cricsheet Ingestion

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ETL PIPELINE (scripts/ingest_cricsheet.py)         │
│                                                                         │
│  EXTRACT                TRANSFORM                   LOAD                │
│  ─────────              ─────────────               ──────              │
│                                                                         │
│  data/raw/              validate_schema()           match table         │
│  all_json.zip           ──────────────────►         innings table       │
│      │                  parse_match_info()          delivery table      │
│      │ unzip            parse_innings()             player table        │
│      ▼                  parse_deliveries()          player_team_match   │
│  {match_id}.json        normalize_venue()           venue table         │
│  ×22,062 files          deduplicate_players()                          │
│      │                  ──────────────────►                             │
│      │ ijson             UPSERT logic                                  │
│      │ streaming         (on conflict: update)                         │
│      ▼                                                                  │
│  Parsed delivery                                                        │
│  dict per ball          compute_fantasy_pts()   ──► player_match_       │
│                         Dream11 scoring formula      performance table  │
│                                                                         │
│  Error handling:                                                        │
│  ┌──────────────────────────────────────────┐                          │
│  │ File fails validation                    │                          │
│  │    → log error to errors.jsonl           │                          │
│  │    → increment error_count               │                          │
│  │    → CONTINUE to next file               │                          │
│  └──────────────────────────────────────────┘                          │
│                                                                         │
│  Progress: tqdm bar showing files processed / total                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Feature Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│               FEATURE PIPELINE (scripts/build_features.py)              │
│                                                                         │
│  player_match_performance table                                         │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  STEP 1: Rolling Features                                        │   │
│  │                                                                  │   │
│  │  For each (player, match_type):                                  │   │
│  │    window=3  → fp_avg_3, avg_runs_3, avg_wickets_3, avg_sr_3     │   │
│  │    window=5  → fp_avg_5, avg_runs_5, ... + dot_ball_rate_5       │   │
│  │    window=10 → fp_avg_10, fp_ceiling, fp_floor, fp_consistency   │   │
│  │                                                                  │   │
│  │  → INSERT/UPDATE rolling_feature table                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  STEP 2: Venue Stats                                             │   │
│  │                                                                  │   │
│  │  For each (venue, match_type):                                   │   │
│  │    avg_first_innings, avg_second_innings                         │   │
│  │    chasing_win_pct, spin_wicket_pct, pace_wicket_pct             │   │
│  │    boundary_index, toss_advantage                                │   │
│  │                                                                  │   │
│  │  For each (player, venue, match_type):                           │   │
│  │    player-specific venue_avg_runs, venue_avg_wickets             │   │
│  │                                                                  │   │
│  │  → INSERT/UPDATE venue_stat table                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  STEP 3: Matchup Stats                                           │   │
│  │                                                                  │   │
│  │  Classify each bowler → bowler_type                              │   │
│  │  For each (batter, bowler_type, match_type):                     │   │
│  │    SR, avg, dismissal_rate, dot_rate, boundary_rate              │   │
│  │    (only if ≥ 30 balls faced)                                    │   │
│  │                                                                  │   │
│  │  → INSERT/UPDATE matchup_stat table                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  STEP 4: Cache Warm-Up                                           │   │
│  │                                                                  │   │
│  │  For each active player in upcoming matches:                     │   │
│  │    Build 47-dim feature vector                                   │   │
│  │    Store in Redis with 6h TTL                                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Real-Time Data Flow (Post-Toss)

```
External Trigger (Admin or Scraper)
         │
         ▼
PATCH /api/v1/admin/matches/:id {toss_winner, toss_decision}
         │
         ├──► DB write: match.toss_winner, match.toss_decision
         │
         ├──► Redis: invalidate match:{match_id}, pred:{match_id}:*
         │
         └──► Celery queue: 2 tasks in parallel
                   │
              ┌────┴────────────────────────────────────────┐
              │                                             │
              ▼                                             ▼
    refresh_prediction(match_id)            send_toss_notifications(match_id)
              │                                             │
    Context rebuild                          Load subscribed users
    (is_chasing recomputed)                 Render Telegram templates
    ML re-predict                           Send via Bot API
    Rules re-evaluate                       Log delivery status
    LP re-optimize                          Set dedup flags in Redis
    LLM re-explain (cache check)
    Store prediction(phase=post_toss)
              │
              ▼
    WebSocket broadcast:
    {event: toss_update,
     captain: {name, confidence},
     toss_winner, toss_decision}
    → All live connections for this match
```

---

## 4. Model Training Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│            TRAINING PIPELINE (training/train_ensemble.py)               │
│                                                                         │
│  DB: player_match_performance + rolling_feature + venue_stat            │
│         │                                                               │
│         ▼                                                               │
│  data_loader.py                                                         │
│    SELECT matches WHERE match_type='T20'                                │
│    AND match_date BETWEEN '2010-01-01' AND '2024-12-31'                 │
│    JOIN feature vectors per player per match                            │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  TimeSeriesSplit (n=5, gap=30 days)                          │       │
│  │  Fold 1: train 2010-2021 | val 2022                          │       │
│  │  Fold 2: train 2010-2022 | val 2023                          │       │
│  │  Fold 3: train 2010-2023 | val 2024                          │       │
│  └─────────────────────────────────────────────────────────────┘       │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐       │
│  │  XGBoost Train  │  │ LightGBM Train  │  │  CatBoost Train  │       │
│  │  early_stop=50  │  │  early_stop=50  │  │  early_stop=50   │       │
│  │  → m01_t20.pkl  │  │  → m02_t20.pkl  │  │  → m03_t20.cbm   │       │
│  └────────┬────────┘  └────────┬────────┘  └────────┬─────────┘       │
│           │                    │                     │                  │
│           └────────────────────┴─────────────────────┘                 │
│                                │                                        │
│                                ▼                                        │
│                     Evaluate on held-out 2025 set                      │
│                     Compute: MAE, Spearman ρ, CPR, CA                  │
│                                │                                        │
│                     promote_model_if_better()                           │
│                     Log to EXPERIMENT_TRACKING.md                      │
│                     Update model_version table                          │
│                     Send admin email: retrain complete + metrics        │
└─────────────────────────────────────────────────────────────────────────┘
```
