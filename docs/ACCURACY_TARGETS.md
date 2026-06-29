# Accuracy Targets

## Tiered Accuracy Goals

### MVP (Launch — Q4 2026)

| Metric | Format | Target | Minimum |
|--------|--------|--------|---------|
| Captain Accuracy | T20/IPL | 40% | 35% |
| VC Accuracy | T20/IPL | 30% | 25% |
| Top-3 Captain Rate | T20/IPL | 70% | 62% |
| Correct Player Rate (≥7/11) | T20/IPL | 60% | 55% |
| Fantasy Points MAE | T20/IPL | 14 pts | 18 pts |
| Rank Correlation (ρ) | T20/IPL | 0.65 | 0.55 |

### Year 1 (Q4 2027)

| Metric | Format | Target |
|--------|--------|--------|
| Captain Accuracy | T20/IPL | 45% |
| Top-3 Captain Rate | T20/IPL | 78% |
| Correct Player Rate | T20/IPL | 68% |
| Fantasy Points MAE | T20/IPL | 11 pts |
| Captain Accuracy | ODI | 38% |
| Captain Accuracy | Test | 32% |

---

## Accuracy by Match Phase

| Phase | Captain Accuracy | Correct Player Rate |
|-------|-----------------|---------------------|
| Pre-toss prediction | 36% (baseline) | 55% |
| Post-toss prediction | 40%+ (target) | 62%+ (target) |
| Live (in-match) | 44%+ (Phase 2 target) | 65%+ |

Toss result improves accuracy by ~4pp for captain and ~7pp for correct player rate.

---

## Differential Pick Accuracy (GL Focus)

| Metric | Target |
|--------|--------|
| % of differential picks (ownership <15%) that score 40+ FP | 35% |
| Avg FP of recommended differentials vs overall player avg | +12 pts |
| GL team finishing in top 10% of grand league leaderboard | 25% of submissions |

---

## Accuracy Floor Alerts

If any of these thresholds are breached over 50 consecutive matches, auto-alert admin:

| Alert Condition | Action |
|----------------|--------|
| Captain accuracy < 35% | Alert + queue emergency retrain |
| Correct player rate < 55% | Alert + investigate feature drift |
| Fantasy points MAE > 18 | Alert + check model artifacts |
| > 3 predictions with optimizer infeasible | Alert + check optimizer |

---

## Baseline Comparison (Random Picker)

| Metric | Random Baseline | XithSense MVP Target | Improvement |
|--------|----------------|---------------------|-------------|
| Captain Accuracy | 9.1% (1/11) | 40% | +340% |
| Correct Player Rate | 31.2% (statistical) | 62% | +99% |
| Top-3 Captain | 27.3% (3/11) | 70% | +156% |

XithSense must outperform random selection by at least 2× on all primary metrics.

---

## Backtesting Validation Schedule

| Frequency | Action |
|-----------|--------|
| Before any model promotion | Run 2,000-match backtest |
| Monthly | Run 10,000-match backtest; update EXP log |
| Before major release | Run full held-out test set; document results |
| After rule changes | Run 500-match backtest on affected formats |

All backtest results documented in `evaluation/EXPERIMENT_TRACKING.md`.
