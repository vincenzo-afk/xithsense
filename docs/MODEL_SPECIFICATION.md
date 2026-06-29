# Model Specification

**Module:** `training/`, `models/`  
**Framework:** scikit-learn, XGBoost, LightGBM, CatBoost  
**Registry:** `models/MODEL_REGISTRY.yaml`

---

## 1. Model Inventory

| Model ID | Name | Target | Format | Backend |
|----------|------|--------|--------|---------|
| M-01 | `fantasy_points_xgb` | `fantasy_points` | T20, IPL | XGBoost |
| M-02 | `fantasy_points_lgb` | `fantasy_points` | T20, IPL | LightGBM |
| M-03 | `fantasy_points_cat` | `fantasy_points` | T20, IPL | CatBoost |
| M-04 | `batting_runs_xgb` | `runs_scored` | T20, IPL | XGBoost |
| M-05 | `bowling_wickets_xgb` | `wickets_taken` | T20, IPL | XGBoost |
| M-06 | `fp_ceiling_xgb` | `fp_90th_pctile` | T20, IPL | XGBoost |
| M-07 | `fantasy_points_odi` | `fantasy_points` | ODI | LightGBM |
| M-08 | `fantasy_points_test` | `fantasy_points` | Test | CatBoost |

---

## 2. Primary Target: Fantasy Points

### 2.1 Dream11 Scoring System

```
BATTING:
  Run scored             +1.0 pt
  Boundary bonus (4)     +1.0 pt
  Six bonus (6)          +2.0 pt
  Half-century bonus     +8.0 pts
  Century bonus          +16.0 pts
  Dismissal for duck (batters only) -2.0 pts

BOWLING:
  Wicket                 +25.0 pts
  LBW / Bowled bonus     +8.0 pts
  5-wicket haul bonus    +16.0 pts
  4-wicket haul bonus    +8.0 pts
  Maiden over            +4.0 pts

FIELDING:
  Catch                  +8.0 pts
  Stumping               +12.0 pts
  Run out (direct)       +12.0 pts
  Run out (indirect)     +6.0 pts

WICKETKEEPER:
  Catch (WK)             +8.0 pts
  Stumping               +12.0 pts
```

### 2.2 Fantasy Points Computed From Cricsheet

```python
def compute_fantasy_points(performance: PlayerMatchPerformance) -> float:
    pts = 0.0
    # Batting
    pts += performance.runs_scored * 1.0
    pts += performance.fours * 1.0
    pts += performance.sixes * 2.0
    if performance.runs_scored >= 100: pts += 16.0
    elif performance.runs_scored >= 50: pts += 8.0
    if performance.runs_scored == 0 and performance.is_dismissed \
       and performance.primary_role in ('BAT','WK','AR'): pts -= 2.0
    # Bowling
    pts += performance.wickets_taken * 25.0
    if performance.wickets_taken >= 5: pts += 16.0
    elif performance.wickets_taken >= 4: pts += 8.0
    pts += performance.maidens * 4.0
    # Fielding
    pts += performance.catches * 8.0
    pts += performance.stumpings * 12.0
    pts += performance.run_outs * 12.0
    return round(pts, 2)
```

---

## 3. Model Architecture

### 3.1 XGBoost Fantasy Points (M-01)

```python
XGBRegressor(
    n_estimators=1200,
    max_depth=6,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.7,
    reg_alpha=0.1,
    reg_lambda=1.0,
    min_child_weight=5,
    gamma=0.1,
    objective="reg:squarederror",
    eval_metric="mae",
    early_stopping_rounds=50,
    random_state=42,
    n_jobs=-1
)
```

### 3.2 LightGBM Fantasy Points (M-02)

```python
LGBMRegressor(
    n_estimators=1500,
    max_depth=7,
    learning_rate=0.025,
    num_leaves=63,
    subsample=0.8,
    colsample_bytree=0.7,
    reg_alpha=0.05,
    reg_lambda=0.5,
    min_child_samples=20,
    objective="regression_l1",
    metric="mae",
    early_stopping_rounds=50,
    random_state=42,
    n_jobs=-1
)
```

### 3.3 CatBoost Fantasy Points (M-03)

```python
CatBoostRegressor(
    iterations=1000,
    depth=7,
    learning_rate=0.05,
    l2_leaf_reg=3.0,
    border_count=128,
    loss_function="MAE",
    eval_metric="MAE",
    early_stopping_rounds=50,
    random_state=42,
    verbose=False
)
```

---

## 4. Training Pipeline

### 4.1 Data Split Strategy

```
Timeline-based split — NO random shuffle:

Training set:  matches from 2010-01-01 to 2024-12-31
Validation set: matches from 2025-01-01 to 2025-12-31
Test set (held out): matches from 2026-01-01 onward
```

Never use future data to predict past matches. Always split on date.

### 4.2 Cross-Validation Strategy

```python
# Time-series cross-validation with 5 folds
TimeSeriesSplit(n_splits=5, gap=30)  # 30-day gap between train and val
```

### 4.3 Feature Scaling

- Tree-based models (XGBoost, LightGBM, CatBoost): **no scaling required**
- Feature importance computed using gain-based importance
- SHAP values computed for top-20 features

### 4.4 Training Command

```bash
# Train all models for T20 format
python training/train_ensemble.py --format T20

# Train specific model
python training/train_model.py --model M-01 --format IPL

# Train all formats
python training/train_ensemble.py --all-formats
```

---

## 5. Model Evaluation Metrics

| Metric | Definition | Target (T20) |
|--------|-----------|-------------|
| MAE | Mean Absolute Error on fantasy points | < 12 pts |
| RMSE | Root Mean Squared Error | < 18 pts |
| Rank Correlation | Spearman ρ between predicted and actual rank | > 0.65 |
| Top-11 Accuracy | % of actual top-11 players correctly predicted | > 60% |
| Captain Accuracy | % of matches where predicted captain = actual top scorer | > 38% |

---

## 6. Model Versioning

Every trained model is registered in `models/MODEL_REGISTRY.yaml`:

```yaml
- id: "m01-t20-20260601"
  name: "fantasy_points_xgb"
  match_type: "T20"
  artifact_path: "models/artifacts/m01_t20_20260601.pkl"
  train_mae: 10.82
  val_mae: 11.94
  train_from: "2010-01-01"
  train_to: "2024-12-31"
  feature_count: 47
  is_active: true
  created_at: "2026-06-01"
```

### Version Promotion Policy

1. Train candidate model on current data
2. Backtest candidate on 2025 held-out set
3. Compare MAE and captain accuracy to current active model
4. Promote if val_MAE improves by ≥ 1 pt OR captain accuracy improves by ≥ 2%
5. Keep previous version as fallback for 30 days

---

## 7. Feature Importance (Top 15, T20 Model M-01)

Based on XGBoost gain importance (approximate, updated each training run):

| Rank | Feature | Importance (gain) |
|------|---------|------------------|
| 1 | `fp_avg_5` | 0.142 |
| 2 | `fp_avg_10` | 0.118 |
| 3 | `fp_ceiling` | 0.094 |
| 4 | `avg_runs_5` | 0.087 |
| 5 | `avg_wickets_5` | 0.081 |
| 6 | `venue_avg_runs_batting` | 0.063 |
| 7 | `fp_avg_3` | 0.058 |
| 8 | `avg_sr_5` | 0.052 |
| 9 | `matchup_sr_vs_pace_right` | 0.044 |
| 10 | `venue_chasing_win_pct` | 0.039 |
| 11 | `fp_consistency` | 0.035 |
| 12 | `is_chasing` | 0.031 |
| 13 | `dot_ball_rate_5` | 0.027 |
| 14 | `opposition_bowling_strength` | 0.025 |
| 15 | `batting_position_encoded` | 0.022 |

---

## 8. Retraining Schedule

| Trigger | Action |
|---------|--------|
| Monthly (first day) | Retrain all active models with latest data |
| After 100 new T20 matches ingested | Re-evaluate model; retrain if needed |
| Admin manual trigger | On-demand retrain via `POST /api/v1/admin/retrain` |
| Accuracy drops below threshold | Auto-alert admin; retrain queued |
