# Feature Engineering Specification

**Module:** `feature_engineering/`  
**Pipeline entry:** `scripts/build_features.py`  
**Storage:** `rolling_feature`, `venue_stat`, `matchup_stat` tables + Redis cache

---

## 1. Feature Categories

| Category | Count | Primary Table |
|----------|-------|--------------|
| Rolling form features | 18 | `rolling_feature` |
| Venue features | 10 | `venue_stat` |
| Matchup features | 6 | `matchup_stat` |
| Context features | 8 | Computed at prediction time |
| Fantasy features | 5 | `rolling_feature` |

---

## 2. Rolling Form Features

Computed for windows of **3, 5, and 10** most recent matches of the same `match_type`.

### 2.1 Batting Rolling Features

| Feature Name | Formula | Window | Notes |
|---|---|---|---|
| `avg_runs_{w}` | `SUM(runs_scored) / COUNT(matches)` | 3, 5, 10 | Excludes matches where player did not bat |
| `avg_sr_{w}` | `SUM(runs_scored) / SUM(balls_faced) * 100` | 3, 5, 10 | |
| `avg_fours_{w}` | `SUM(fours) / COUNT(matches)` | 3, 5, 10 | |
| `avg_sixes_{w}` | `SUM(sixes) / COUNT(matches)` | 3, 5, 10 | |
| `dismissal_rate_{w}` | `SUM(is_dismissed) / COUNT(matches)` | 3, 5, 10 | |
| `boundary_pct_{w}` | `(SUM(fours)*4 + SUM(sixes)*6) / SUM(runs_scored)` | 5 | |

### 2.2 Bowling Rolling Features

| Feature Name | Formula | Window | Notes |
|---|---|---|---|
| `avg_wickets_{w}` | `SUM(wickets_taken) / COUNT(matches)` | 3, 5, 10 | |
| `avg_economy_{w}` | `SUM(runs_conceded) / SUM(overs_bowled)` | 3, 5, 10 | |
| `avg_overs_{w}` | `SUM(overs_bowled) / COUNT(matches)` | 3, 5, 10 | |
| `dot_ball_rate_{w}` | `SUM(dot_balls) / SUM(balls_bowled)` | 5 | |
| `wicket_per_over_{w}` | `SUM(wickets_taken) / SUM(overs_bowled)` | 5 | |

### 2.3 Fantasy Rolling Features

| Feature Name | Formula | Window | Notes |
|---|---|---|---|
| `fp_avg_{w}` | `SUM(fantasy_points) / COUNT(matches)` | 3, 5, 10 | Core feature |
| `fp_ceiling` | `PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY fantasy_points)` | 10 | Best-case scenario |
| `fp_floor` | `PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY fantasy_points)` | 10 | Worst-case scenario |
| `fp_consistency` | `STDDEV(fantasy_points) / AVG(fantasy_points)` | 10 | Lower = more consistent |
| `fp_30plus_rate` | `COUNT(matches WHERE fp >= 30) / COUNT(matches)` | 10 | 30+ point games rate |

---

## 3. Venue Features

Computed from all historical matches at the same venue with the same `match_type`.

| Feature Name | Formula | Notes |
|---|---|---|
| `venue_avg_runs_batting` | `AVG(runs_scored) WHERE venue = V AND player = P` | Player-venue specific |
| `venue_avg_wickets_bowling` | `AVG(wickets_taken) WHERE venue = V AND player = P` | Player-venue specific |
| `venue_avg_first_innings` | `AVG(innings_total) WHERE innings_number = 1` | Venue-level baseline |
| `venue_avg_second_innings` | `AVG(innings_total) WHERE innings_number = 2` | |
| `venue_spin_wicket_pct` | `COUNT(wickets WHERE bowler_type LIKE 'spin%') / COUNT(all_wickets)` | Surface assessment |
| `venue_pace_wicket_pct` | `COUNT(wickets WHERE bowler_type LIKE 'pace%') / COUNT(all_wickets)` | |
| `venue_chasing_win_pct` | `COUNT(matches WHERE winner = batting_second_team) / COUNT(matches)` | Toss relevance |
| `venue_boundary_index` | `(SUM(fours) + SUM(sixes)) / SUM(balls_faced) * 100` | Boundary-friendliness |
| `venue_total_matches` | `COUNT(matches)` | Data confidence indicator |
| `venue_toss_win_bat_pct` | `COUNT(matches WHERE toss_winner_batted AND won) / COUNT(...)` | Toss decision bias |

---

## 4. Matchup Features

Computed from all historical ball-by-ball deliveries per batter vs bowler-type pair.

### 4.1 Bowler Type Classification

| Bowler Type Key | Cricsheet bowling_style patterns |
|---|---|
| `pace_right` | `Right-arm fast`, `Right-arm fast-medium`, `Right-arm medium-fast`, `Right-arm medium` |
| `pace_left` | `Left-arm fast`, `Left-arm fast-medium`, `Left-arm medium-fast`, `Left-arm medium` |
| `spin_off` | `Right-arm off-break`, `Right-arm off-spin` |
| `spin_left` | `Slow left-arm orthodox` |
| `spin_wrist` | `Legbreak`, `Legbreak googly`, `Slow left-arm chinaman` |

### 4.2 Matchup Features

| Feature Name | Formula |
|---|---|
| `matchup_sr_vs_{type}` | `SUM(runs_batter) / SUM(balls_faced) * 100` |
| `matchup_avg_vs_{type}` | `SUM(runs_batter) / SUM(dismissals + 0.01)` |
| `matchup_dismissal_rate_vs_{type}` | `SUM(is_wicket) / SUM(balls_faced)` |
| `matchup_dot_ball_rate_vs_{type}` | `SUM(runs_batter == 0) / SUM(balls_faced)` |
| `matchup_boundary_rate_vs_{type}` | `SUM(runs_batter >= 4) / SUM(balls_faced)` |
| `matchup_balls_faced_vs_{type}` | `COUNT(deliveries)` — confidence weight |

---

## 5. Context Features

Computed at prediction time from match metadata. Not stored in DB; computed inline.

| Feature Name | Values | Source |
|---|---|---|
| `is_chasing` | 0 / 1 | Toss decision + innings order |
| `batting_position_encoded` | 1–11 normalised to 0–1 | Historical batting order |
| `is_home_ground` | 0 / 1 | Player nationality vs venue country |
| `match_importance` | 0.5–1.0 | Qualifier / Eliminator / Final → higher |
| `days_since_last_match` | integer | Rest/fatigue proxy |
| `phase_powerplay_exposure` | 0–1 | Expected overs in each phase |
| `opposition_bowling_strength` | 0–1 | Normalised opposition bowling avg |
| `opposition_batting_strength` | 0–1 | Normalised opposition batting avg |

---

## 6. Feature Pipeline

```
raw deliveries (PostgreSQL)
        │
        ▼
aggregate_per_match()        → player_match_performance table
        │
        ▼
compute_rolling_features()   → rolling_feature table (windows 3,5,10)
        │
        ▼
compute_venue_stats()        → venue_stat table
        │
        ▼
compute_matchup_stats()      → matchup_stat table
        │
        ▼
build_feature_vector()       → merged DataFrame for model input
        │
        ▼
Redis cache (6h TTL)
```

### Incremental Mode

```bash
# Recompute only for matches after a given date
python scripts/build_features.py --from 2026-01-01
```

The pipeline identifies players with new matches since `--from` date and updates only those rows.

---

## 7. Feature Vector Assembly

At prediction time, features are assembled in this order for model input:

```python
FEATURE_ORDER = [
    # Rolling batting (3, 5, 10 windows)
    "fp_avg_3", "fp_avg_5", "fp_avg_10",
    "avg_runs_3", "avg_runs_5", "avg_runs_10",
    "avg_sr_3", "avg_sr_5", "avg_sr_10",
    "avg_sixes_5", "avg_fours_5",
    "fp_ceiling", "fp_floor", "fp_consistency", "fp_30plus_rate",
    # Rolling bowling
    "avg_wickets_3", "avg_wickets_5", "avg_wickets_10",
    "avg_economy_3", "avg_economy_5",
    "dot_ball_rate_5", "wicket_per_over_5",
    # Venue
    "venue_avg_runs_batting", "venue_avg_wickets_bowling",
    "venue_avg_first_innings", "venue_chasing_win_pct",
    "venue_spin_wicket_pct", "venue_total_matches",
    # Matchup
    "matchup_sr_vs_pace_right", "matchup_sr_vs_spin_left",
    "matchup_sr_vs_spin_off", "matchup_dismissal_rate_vs_pace_left",
    # Context
    "is_chasing", "batting_position_encoded", "is_home_ground",
    "match_importance", "days_since_last_match",
    "opposition_bowling_strength",
    # Categorical (label-encoded)
    "match_type_encoded", "primary_role_encoded",
    "batting_style_encoded", "bowling_style_encoded",
]
```

---

## 8. Missing Value Strategy

| Situation | Strategy |
|-----------|---------|
| Player has < 3 matches in window | Use available matches; flag `low_data=True` |
| Player has no matches at venue | Use global venue average |
| Matchup has < 30 balls | Use global player stats; weight down matchup feature |
| New player (< 5 career matches) | Use team/role average as prior |
