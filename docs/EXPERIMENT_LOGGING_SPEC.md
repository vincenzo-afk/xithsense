# Experiment Logging Specification

Every ML experiment — training run, hyperparameter change, feature addition — must be logged here before any code merges.

---

## Log Entry Format

```markdown
## EXP-{NNN}: {Short Title}

**Date:** YYYY-MM-DD
**Author:** {name or "system (scheduled retrain)"}
**Branch:** {git branch name}
**Status:** Completed | In Progress | Abandoned | Promoted | Rejected

### Hypothesis
{What are you trying to improve? Why do you expect this change to help?}

### Changes
- Feature changes: {list any new/removed/modified features}
- Hyperparameter changes: {what changed from baseline}
- Training data changes: {date range, format filter, etc.}
- Architecture changes: {new model type, ensemble weights, etc.}

### Dataset
- Train: {date range}
- Val: {date range}
- Test: {date range (if used)}
- Match count (train): {N}

### Results

| Metric | Baseline | This Experiment | Delta | Better? |
|--------|---------|-----------------|-------|---------|
| Val MAE | | | | |
| Test MAE | | | | |
| Captain Accuracy | | | | |
| Correct Player Rate | | | | |
| Rank Correlation ρ | | | | |
| Training Time | | | | |

### Bias Analysis
{Any systematic over/under-prediction for specific roles, formats, venues?}

### Decision
**{Promote / Reject / Continue}**

Reason: {Why was this decision made?}

### Notes
{Observations, anomalies, next steps}

### Artifacts
- Model files: {paths in models/artifacts/}
- Config: {path to HYPERPARAMETERS.yaml used}
```

---

## EXP-001: Baseline T20 Ensemble

**Date:** 2026-06-01  
**Author:** system (initial training)  
**Branch:** `feat/initial-ml-pipeline`  
**Status:** Promoted

### Hypothesis
Establish baseline using XGBoost + LightGBM + CatBoost ensemble on 47 features.

### Changes
- Initial feature set v1.2 (47 features as defined in FEATURE_LIST.yaml)
- Default hyperparameters per HYPERPARAMETERS.yaml

### Dataset
- Train: 2010-01-01 to 2024-12-31 (T20/IPL format)
- Val: 2025-01-01 to 2025-12-31
- Train match count: ~12,000 T20/IPL matches

### Results

| Metric | XGB Only | LGB Only | CAT Only | Ensemble | Target |
|--------|---------|---------|---------|---------|--------|
| Val MAE | 12.84 | 11.78 | 12.08 | **11.94** | < 14 pts |
| Captain Acc | 37.8% | 38.9% | 37.2% | **40.1%** | ≥ 38% |
| CPR (≥7/11) | 59.3% | 61.4% | 60.1% | **62.1%** | ≥ 60% |
| Rank ρ | 0.618 | 0.634 | 0.621 | **0.641** | > 0.60 |

### Decision
**Promote.** All mandatory thresholds passed. Ensemble beats best single model by 1.2pp CPR.

### Artifacts
- `models/artifacts/m01_t20_20260601.pkl`
- `models/artifacts/m02_t20_20260601.pkl`
- `models/artifacts/m03_t20_20260601.cbm`

---

## EXP-002: {Next Experiment Title}

**Date:** —  
**Author:** —  
**Status:** Planned

*Template ready. Log next experiment here before starting implementation.*

---

## Required Experiments Queue

| ID | Proposed Change | Expected Benefit | Priority |
|----|----------------|-----------------|---------|
| EXP-002 | Add wrist-spin matchup feature | Improve bowling predictions on spin tracks | High |
| EXP-003 | Separate IPL model from generic T20 | Reduce IPL-specific bias | Medium |
| EXP-004 | Add player injury return flag feature | Reduce over-prediction for returning players | Medium |
| EXP-005 | Neural network comparison (TabNet) | Benchmark vs GBT ensemble | Low |
| EXP-006 | Retrain with 2026 data | Incorporate latest season | High (monthly) |
