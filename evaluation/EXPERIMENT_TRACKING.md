# Experiment Tracking

All ML experiments must be logged here before any model is promoted to production.

---

## Log Format

```
## EXP-{NUMBER}: {Short Description}

**Date:** YYYY-MM-DD
**Author:** {name or "system"}
**Status:** Completed | In Progress | Abandoned

### Hypothesis
{What you're trying to improve and why}

### Changes Made
{What was changed: new features, hyperparameters, training data, etc.}

### Results

| Metric | Baseline | Experiment | Delta |
|--------|---------|-----------|-------|
| Val MAE | X.X | X.X | ±X.X |
| Captain Accuracy | X.XX | X.XX | ±X.XX |
| CPR | X.XX | X.XX | ±X.XX |

### Decision
{Promote / Reject / Investigate further}

### Notes
{Any observations, next steps, edge cases}
```

---

## EXP-001: Baseline T20 Ensemble

**Date:** 2026-06-01  
**Author:** system  
**Status:** Completed

### Hypothesis
Establish baseline model performance for T20/IPL format using XGBoost + LightGBM + CatBoost ensemble.

### Changes Made
- Initial feature set v1.2 (47 features)
- Training data: 2010–2024 T20/IPL matches
- Validation: 2025 T20/IPL matches

### Results

| Metric | Baseline (XGB only) | Ensemble (XGB+LGB+CAT) | Delta |
|--------|---------------------|------------------------|-------|
| Val MAE | 12.84 | 11.94 | -0.90 |
| Captain Accuracy | 0.378 | 0.401 | +0.023 |
| CPR (≥7/11) | 0.591 | 0.621 | +0.030 |
| Rank Correlation | 0.612 | 0.641 | +0.029 |

### Decision
**Promote.** Ensemble M-01/M-02/M-03 activated as production models.

### Notes
CatBoost contributed most at extreme ends (very high FP performers and zeros). LightGBM best for mid-range bowlers.

---

## EXP-002: {Next Experiment}

**Date:**  
**Author:**  
**Status:** Not started

_Template ready — log next experiment here._
