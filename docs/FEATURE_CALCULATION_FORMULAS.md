# Feature Calculation Formulas

All formulas as implemented in `feature_engineering/compute_features.py`.

---

## Rolling Batting Features

```
Given: last W matches for player P of format F (sorted by match_date DESC)

avg_runs_W       = Σ(runs_scored) / W
avg_sr_W         = Σ(runs_scored) / Σ(balls_faced) × 100
avg_fours_W      = Σ(fours) / W
avg_sixes_W      = Σ(sixes) / W
avg_balls_W      = Σ(balls_faced) / W
dismissal_rate_W = Σ(is_dismissed) / W
boundary_pct_W   = (Σ(fours)×4 + Σ(sixes)×6) / Σ(runs_scored)
                   [set to 0 if Σ(runs_scored) = 0]
```

## Rolling Bowling Features

```
avg_wickets_W    = Σ(wickets_taken) / W
avg_economy_W    = Σ(runs_conceded) / Σ(overs_bowled)
                   [set to 0 if Σ(overs_bowled) = 0]
avg_overs_W      = Σ(overs_bowled) / W
dot_ball_rate_W  = Σ(dot_balls) / Σ(balls_bowled)
wicket_per_over_W = Σ(wickets_taken) / Σ(overs_bowled)
```

## Fantasy Points Rolling Features

```
fp_avg_W         = Σ(fantasy_points) / W
fp_std_W         = √( Σ(fantasy_points - fp_avg_W)² / (W-1) )
fp_consistency_W = fp_std_W / fp_avg_W   [CV; 0 if fp_avg_W = 0]
fp_ceiling       = PERCENTILE(fantasy_points, 0.90, window=10)
fp_floor         = PERCENTILE(fantasy_points, 0.10, window=10)
fp_30plus_rate   = COUNT(fantasy_points >= 30) / 10  [window=10 only]
```

## Fantasy Points Computation (Dream11)

```
fantasy_points =
    runs_scored × 1.0
  + fours × 1.0
  + sixes × 2.0
  + (100 if runs_scored >= 100 else 8 if runs_scored >= 50 else 0)
  + (-2 if runs_scored == 0 AND is_dismissed AND role IN ('BAT','WK','AR') else 0)
  + wickets_taken × 25.0
  + (16 if wickets_taken >= 5 else 8 if wickets_taken >= 4 else 0)
  + maidens × 4.0
  + catches × 8.0
  + stumpings × 12.0
  + (run_out_direct × 12.0) + (run_out_indirect × 6.0)
```

## Venue Features

```
Given: all historical matches of format F at venue V

venue_avg_runs_batting(P, V, F):
    = AVG(runs_scored) WHERE player=P AND venue=V AND format=F
    [fallback to global avg if matches < 3]

venue_chasing_win_pct(V, F):
    = COUNT(matches WHERE winner = batting_second_team) /
      COUNT(matches)   [for format F at venue V]

venue_spin_wicket_pct(V, F):
    = COUNT(wickets WHERE bowler_type LIKE 'spin%') /
      COUNT(all_wickets)   [for format F at venue V]

venue_boundary_index(V, F):
    = (Σfours + Σsixes) / Σballs_faced × 100
```

## Matchup Features

```
Given: all deliveries where batter=B, classified bowler_type=T, format=F

matchup_sr_vs_T    = Σ(runs_batter) / Σ(legal_balls) × 100
matchup_avg_vs_T   = Σ(runs_batter) / (Σ(wickets)+ε)   [ε=0.01]
matchup_dot_rate_T = Σ(runs_batter == 0) / Σ(legal_balls)
matchup_boundary_T = Σ(runs_batter >= 4) / Σ(legal_balls)
matchup_dismissal_T = Σ(is_wicket) / Σ(legal_balls)
```

## Context Features

```
is_chasing:
    1 if player's team bats second (post-toss), else 0

batting_position_encoded:
    expected_position / 11.0   [1=0.09, 11=1.0]

match_importance:
    1.0  if event_stage IN ('Final', 'Final (D/N)')
    0.85 if event_stage IN ('Eliminator', '2nd Qualifier')
    0.70 if event_stage IN ('1st Qualifier', '1st Semi-Final')
    0.60 if event_stage IN ('2nd Semi-Final')
    0.50 otherwise (league stage)

days_since_last_match:
    match_date - max(previous_match_date for player P)

opposition_bowling_strength:
    normalise(avg_fp_of_opposition_bowlers) to [0, 1]
    using min-max across all teams in format
```

## Normalisation (Pre-Model)

```
# Applied per prediction batch (not globally)
def normalise_feature(values: list[float]) -> list[float]:
    min_v, max_v = min(values), max(values)
    if max_v == min_v:
        return [0.5] * len(values)
    return [(v - min_v) / (max_v - min_v) for v in values]
```
