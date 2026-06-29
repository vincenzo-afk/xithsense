# Feature Formulas

All mathematical formulas used in feature engineering and scoring. Canonical reference for implementation.

---

## 1. Fantasy Points (Dream11)

```
FP(player) =
    R × 1.0                           R = runs scored
  + 4s × 1.0                          4s = boundaries (4-run shots)
  + 6s × 2.0                          6s = sixes
  + CENTURY_BONUS                      if R ≥ 100: +16; elif R ≥ 50: +8; else 0
  + DUCK_PENALTY                       if R=0 AND dismissed AND role∈{BAT,WK,AR}: -2; else 0
  + W × 25.0                          W = wickets taken
  + HAUL_BONUS                         if W ≥ 5: +16; elif W ≥ 4: +8; else 0
  + M × 4.0                           M = maiden overs
  + C × 8.0                           C = catches
  + ST × 12.0                         ST = stumpings
  + RO_D × 12.0                       RO_D = direct run-outs
  + RO_I × 6.0                        RO_I = indirect run-outs
```

---

## 2. Rolling Fantasy Features

Let **FP₁, FP₂, ..., FPₙ** = fantasy points in last N matches (newest first).

```
fp_avg_N       = (Σᵢ FPᵢ) / N

fp_std_N       = √[ Σᵢ(FPᵢ - fp_avg_N)² / (N - 1) ]

fp_consistency = fp_std_10 / fp_avg_10
                 [0 = perfectly consistent; higher = volatile]
                 [0 if fp_avg_10 = 0]

fp_ceiling     = PERCENTILE(FP₁..FP₁₀, 0.90)
                 [90th percentile over last 10 matches]

fp_floor       = PERCENTILE(FP₁..FP₁₀, 0.10)
                 [10th percentile over last 10 matches]

fp_30plus_rate = COUNT(FPᵢ ≥ 30, i=1..10) / 10
```

---

## 3. Rolling Batting Features

Let **Rᵢ, Bᵢ, 4ᵢ, 6ᵢ** = runs/balls/fours/sixes in match i.

```
avg_runs_N     = Σ Rᵢ / N

avg_sr_N       = (Σ Rᵢ / Σ Bᵢ) × 100     [0 if Σ Bᵢ = 0]

avg_fours_N    = Σ 4ᵢ / N

avg_sixes_N    = Σ 6ᵢ / N

boundary_pct_N = (Σ 4ᵢ × 4 + Σ 6ᵢ × 6) / Σ Rᵢ    [0 if Σ Rᵢ = 0]

dismissal_rate_N = Σ dismissed_i / N
```

---

## 4. Rolling Bowling Features

Let **Wᵢ, ERᵢ, OVᵢ, DBᵢ** = wickets/runs conceded/overs/dot balls in match i.

```
avg_wickets_N  = Σ Wᵢ / N

avg_economy_N  = Σ ERᵢ / Σ OVᵢ            [0 if Σ OVᵢ = 0]

avg_overs_N    = Σ OVᵢ / N

dot_ball_rate_N = Σ DBᵢ / Σ (OVᵢ × 6)    [legal deliveries]

wicket_per_over_N = Σ Wᵢ / Σ OVᵢ         [0 if Σ OVᵢ = 0]
```

---

## 5. Venue Features

Let **M** = all matches at venue V of format F.

```
venue_avg_first_innings  = AVG(total_runs WHERE innings_number=1)

venue_avg_second_innings = AVG(total_runs WHERE innings_number=2)

venue_chasing_win_pct    = COUNT(winner = batting_second) / |M|

venue_spin_wicket_pct    = COUNT(wickets WHERE bowler_type LIKE 'spin%') /
                           COUNT(all_wickets)

venue_pace_wicket_pct    = COUNT(wickets WHERE bowler_type LIKE 'pace%') /
                           COUNT(all_wickets)

venue_boundary_index     = (Σ fours + Σ sixes) / Σ legal_balls × 100

venue_player_avg_runs(P,V,F) = AVG(runs_scored WHERE player=P AND venue=V AND format=F)
                                [use global avg if < 3 matches]

venue_player_avg_wickets(P,V,F) = AVG(wickets WHERE player=P AND venue=V AND format=F)
```

---

## 6. Matchup Features

Let **D** = all deliveries where batter=B faces bowler of type T in format F.

```
matchup_sr(B,T,F)           = Σ runs_batter / Σ legal_balls × 100

matchup_avg(B,T,F)          = Σ runs_batter / (Σ wickets + 0.01)

matchup_dismissal_rate(B,T,F) = Σ is_wicket / Σ legal_balls

matchup_dot_rate(B,T,F)     = Σ (runs_batter = 0) / Σ legal_balls

matchup_boundary_rate(B,T,F) = Σ (runs_batter ≥ 4) / Σ legal_balls

matchup_confidence(B,T,F)   = min(Σ legal_balls / 100, 1.0)
                               [0 = no data; 1 = full confidence]
```

---

## 7. Context Features

```
is_chasing(player) =
    1  if player's team bats second (toss_decision = field for batting team
                                      OR toss_decision = bat for fielding team)
    0  otherwise

batting_position_encoded(player) =
    expected_batting_order_position / 11.0
    [opener=1→0.09; #11=11→1.0]

match_importance(event_stage) =
    1.00  if stage = "Final"
    0.85  if stage ∈ {"Eliminator", "2nd Qualifier", "2nd Semi-Final"}
    0.70  if stage ∈ {"1st Qualifier", "1st Semi-Final"}
    0.60  if stage ∈ {"3rd Place Playoff"}
    0.50  otherwise (league stage)

days_since_last_match(player) =
    match_date - MAX(previous_match_date for this player)
    [cap at 30 if no previous match found]

opposition_strength(team, type) =
    MinMaxNorm(AVG(fantasy_points of type='bowl' OR 'bat' for opposition))
    [normalised to [0,1] across all teams in format]
```

---

## 8. Ensemble Score Formula

```
Let:
  ml_norm    = MinMaxNorm(ml_score,    across all 22 players)
  rules_norm = MinMaxNorm(rules_score, across all 22 players)
  form_norm  = MinMaxNorm(form_score,  across all 22 players)
  live_norm  = MinMaxNorm(live_score,  across all 22 players)

MinMaxNorm(x, values) = (x - min(values)) / (max(values) - min(values) + ε)
                         [ε = 1e-8 to avoid division by zero]
                         [returns 0.5 if all values equal]

ensemble_score = (
    W_ml    × ml_norm    +    W_ml    = 0.40 (default)
    W_rules × rules_norm +    W_rules = 0.30
    W_form  × form_norm  +    W_form  = 0.20
    W_live  × live_norm         W_live  = 0.10
)

form_score(player) =
    fp_avg_3 × 0.50 +
    fp_avg_5 × 0.30 +
    fp_avg_10 × 0.20
```

---

## 9. Confidence Score Formula

```
confidence(player) = int(clamp(
    (ensemble_score / max_ensemble_score) × 75.0    # score contribution: 0-75
  + (1.0 - fp_consistency) × 15.0                   # consistency bonus: 0-15
  + matchup_confidence_avg × 10.0,                  # data quality bonus: 0-10
    min=1, max=100
))

clamp(x, min, max) = max(min, min(max, x))
```

---

## 10. Differential Bonus (GL Mode)

```
differential_bonus(ownership_pct) =
    20.0  if ownership_pct < 5%
    12.0  if 5% ≤ ownership_pct < 10%
     6.0  if 10% ≤ ownership_pct < 20%
     0.0  if ownership_pct ≥ 20%

gl_score(player) =
    fp_ceiling × 0.60 +
    fp_avg_5   × 0.25 +
    differential_bonus(ownership_pct) × 0.15
```
