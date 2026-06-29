# Ensemble Strategy

## Weights

| Component | Default Weight | Environment Variable |
|-----------|---------------|---------------------|
| ML Prediction | 40% | `ENSEMBLE_ML_WEIGHT=0.40` |
| Human Rules | 30% | `ENSEMBLE_HUMAN_RULES_WEIGHT=0.30` |
| Recent Form | 20% | `ENSEMBLE_FORM_WEIGHT=0.20` |
| Live Context | 10% | `ENSEMBLE_LIVE_WEIGHT=0.10` |

Live context weight is 0 pre-toss; rises to 10% post-toss; can reach 25% during live match.

## Score Normalisation

Each component score is normalised to [0, 100] before weighting:

```python
def normalise(scores: list[float]) -> list[float]:
    min_s, max_s = min(scores), max(scores)
    if max_s == min_s: return [50.0] * len(scores)
    return [(s - min_s) / (max_s - min_s) * 100 for s in scores]
```

## Final Score Formula

```python
final_score = (
    ml_weight    * normalised_ml_score    +
    rules_weight * normalised_rules_score +
    form_weight  * normalised_form_score  +
    live_weight  * normalised_live_score
)
```

## ML Component

Average of three model predictions (XGBoost, LightGBM, CatBoost):

```python
ml_score = (xgb_fp + lgb_fp + cat_fp) / 3
```

If a model artifact is unavailable, it is excluded and weights re-normalised.

## Form Component

```python
form_score = (fp_avg_3 * 0.50) + (fp_avg_5 * 0.30) + (fp_avg_10 * 0.20)
```

More weight on recent form (3-match window).

## Confidence Score

```python
confidence = int(clamp(
    (ensemble_score / 100) * 90  +  # raw score contribution
    (1 - fp_consistency) * 10,       # consistency bonus
    min=1, max=100
))
```
