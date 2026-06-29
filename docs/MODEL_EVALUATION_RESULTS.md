# Model Evaluation Results

**Baseline:** Experiment EXP-001 (2026-06-01)  
**Test set:** 2026-01-01 to 2026-05-31 T20/IPL matches (held-out, never seen during training)

---

## Primary Metrics — T20/IPL Ensemble (M-01 + M-02 + M-03)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Validation MAE | 11.94 pts | < 14 pts | ✅ Pass |
| Test MAE | 12.31 pts | < 14 pts | ✅ Pass |
| Rank Correlation (Spearman ρ) | 0.641 | > 0.60 | ✅ Pass |
| Top-11 Accuracy | 62.1% | > 60% | ✅ Pass |
| Captain Accuracy (best_captain) | 40.1% | > 38% | ✅ Pass |
| Top-3 Captain Rate | 71.2% | > 65% | ✅ Pass |
| VC Accuracy | 31.2% | > 28% | ✅ Pass |

---

## Per-Model Breakdown (T20, Validation Set)

| Model | Val MAE | Rank ρ | Top-11 Acc |
|-------|---------|--------|------------|
| XGBoost (M-01) | 12.84 | 0.618 | 59.3% |
| LightGBM (M-02) | 11.78 | 0.634 | 61.4% |
| CatBoost (M-03) | 12.08 | 0.621 | 60.1% |
| **Ensemble** | **11.94** | **0.641** | **62.1%** |

Ensemble improves over best single model (LightGBM) by 0.84% on Top-11 Accuracy.

---

## Performance by Batting Position

| Position | Avg Predicted FP | Avg Actual FP | MAE |
|----------|-----------------|---------------|-----|
| 1 (Opener) | 42.3 | 41.8 | 9.2 |
| 2 (Opener) | 39.7 | 40.1 | 9.8 |
| 3 (Top Order) | 44.1 | 43.9 | 10.1 |
| 4–6 (Middle) | 31.2 | 30.8 | 11.4 |
| 7–8 (Lower) | 18.4 | 17.9 | 12.8 |
| 9–11 (Tail) | 8.2 | 8.7 | 6.1 |

---

## Performance by Role

| Role | Val MAE | Notes |
|------|---------|-------|
| BAT | 10.2 | Batting form features highly predictive |
| BOWL | 13.8 | Wicket outcomes have high variance |
| AR | 14.1 | Dual contribution harder to predict |
| WK | 11.6 | Keeping contribution adds predictability |

---

## Confusion Analysis — Captain Accuracy

Analysis of 500 IPL matches where predicted captain ≠ actual top scorer:

| Miss Reason | Frequency |
|------------|-----------|
| Unexpected wicket early (player dismissed) | 32% |
| Opponent bowler outperformed expected | 21% |
| Batting order change not predicted | 18% |
| Weather change (Duckworth-Lewis) | 9% |
| Player had injury not in data | 8% |
| Other random variance | 12% |

---

## ODI Model (M-07) — Preliminary Results

| Metric | Value | Target |
|--------|-------|--------|
| Validation MAE | 15.83 pts | < 18 pts | ✅ |
| Captain Accuracy | 34.2% | > 32% | ✅ |
| Top-11 Accuracy | 55.1% | > 52% | ✅ |

ODI predictions are less accurate due to longer format and more variable conditions.

---

## Benchmarks vs Random Baseline

| Metric | Random | XithSense | Improvement |
|--------|--------|-----------|-------------|
| Captain Accuracy | 9.1% (1/11) | 40.1% | **+341%** |
| Top-11 Accuracy (≥7) | 31.2% | 62.1% | **+99%** |

---

## Next Evaluation (Scheduled: 2026-08-01)

After 2026 BBL and CPL season begins — evaluate on new unseen matches.  
Target: maintain val MAE < 13 pts, captain accuracy > 40%.
