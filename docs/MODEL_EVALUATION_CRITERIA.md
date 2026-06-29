# Model Evaluation Criteria

Criteria that determine whether a model is fit for production deployment.

---

## Mandatory Thresholds (All Must Pass)

| Metric | Format | Minimum to Deploy | Target |
|--------|--------|------------------|--------|
| Validation MAE | T20/IPL | ≤ 14.0 pts | ≤ 11.0 pts |
| Test MAE (held-out) | T20/IPL | ≤ 15.0 pts | ≤ 12.0 pts |
| Captain Accuracy | T20/IPL | ≥ 35% | ≥ 40% |
| Correct Player Rate (≥7/11) | T20/IPL | ≥ 55% | ≥ 62% |
| Rank Correlation (Spearman ρ) | T20/IPL | ≥ 0.55 | ≥ 0.65 |
| Validation MAE | ODI | ≤ 18.0 pts | ≤ 15.0 pts |

**A model that fails any mandatory threshold is REJECTED, regardless of other scores.**

---

## Promotion Criteria (Must Beat Current Active)

| Condition | Model Promoted |
|-----------|---------------|
| val_MAE_new < val_MAE_active − 1.0 | Yes |
| captain_accuracy_new > captain_accuracy_active + 0.02 | Yes |
| Both MAE and captain accuracy regress | No |
| No active model exists (first training) | Yes (unconditionally) |

---

## Per-Segment Evaluation

Model must not be significantly worse on any individual segment:

| Segment | Max Allowed MAE Degradation vs Baseline |
|---------|----------------------------------------|
| Batters (role=BAT) | +2.0 pts |
| Bowlers (role=BOWL) | +2.0 pts |
| All-rounders (role=AR) | +3.0 pts |
| Wicketkeepers (role=WK) | +2.0 pts |
| Batting position 1-3 | +1.5 pts |
| IPL-specific matches | +1.0 pts |

---

## Bias Checks

Before deployment, verify the model is not systematically biased:

```python
def check_model_bias(model, test_df):
    """Check for systematic over/under prediction by category."""
    results = {}

    for match_type in ["T20", "IPL", "BBL", "PSL"]:
        subset = test_df[test_df["match_type"] == match_type]
        if len(subset) < 50:
            continue
        pred = model.predict(subset[FEATURES])
        bias = (pred - subset["fantasy_points"]).mean()
        results[match_type] = bias
        assert abs(bias) < 3.0, f"Systematic bias {bias:.2f} for {match_type}"

    for role in ["BAT", "BOWL", "AR", "WK"]:
        subset = test_df[test_df["primary_role"] == role]
        pred = model.predict(subset[FEATURES])
        bias = (pred - subset["fantasy_points"]).mean()
        results[role] = bias
        assert abs(bias) < 3.0, f"Systematic bias {bias:.2f} for role {role}"

    return results
```

---

## Evaluation Dataset Specification

| Split | Date Range | Purpose | Never Used For |
|-------|-----------|---------|----------------|
| Training | 2010-01-01 → 2024-12-31 | Model fitting | Evaluation |
| Validation | 2025-01-01 → 2025-12-31 | Hyperparameter tuning | Final reporting |
| Test (held-out) | 2026-01-01 → present | Final evaluation only | Training or tuning |

The test set is **strictly held out** — never used during training or validation.  
Results on the test set are the official numbers reported in `MODEL_EVALUATION_RESULTS.md`.

---

## Red Flags (Automatic Rejection)

Any of these conditions automatically reject a model, regardless of metric scores:

- Any NaN or Inf in model predictions on the validation set
- Prediction range outside [-10, 500] for any player in test set
- Training time > 4 hours (suggests data leakage or infinite loop)
- Val MAE > Train MAE × 1.5 (severe overfitting)
- Captain accuracy < 30% on any IPL season in the validation set
