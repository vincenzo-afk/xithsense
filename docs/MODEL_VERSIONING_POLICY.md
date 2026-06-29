# Model Versioning Policy

## Naming Convention

```
{model_id}-{match_type_lower}-{YYYYMMDD}

Examples:
  m01-t20-20260601       XGBoost T20, trained June 1 2026
  m02-t20-20260601       LightGBM T20, trained June 1 2026
  m03-t20-20260601       CatBoost T20, trained June 1 2026
  m07-odi-20260615       LightGBM ODI, trained June 15 2026
```

## Model IDs

| ID | Name | Format | Backend |
|----|------|--------|---------|
| M-01 | `fantasy_points_xgb` | T20/IPL | XGBoost |
| M-02 | `fantasy_points_lgb` | T20/IPL | LightGBM |
| M-03 | `fantasy_points_cat` | T20/IPL | CatBoost |
| M-04 | `batting_runs_xgb` | T20/IPL | XGBoost |
| M-05 | `bowling_wickets_xgb` | T20/IPL | XGBoost |
| M-06 | `fp_ceiling_xgb` | T20/IPL | XGBoost |
| M-07 | `fantasy_points_odi` | ODI | LightGBM |
| M-08 | `fantasy_points_test` | Test | CatBoost |

## Storage

```
models/artifacts/
├── m01_t20_20260601.pkl         # Active XGB T20
├── m01_t20_20260501.pkl         # Previous XGB T20 (kept 30 days)
├── m02_t20_20260601.pkl         # Active LGB T20
├── m03_t20_20260601.cbm         # Active CAT T20
├── m07_odi_20260601.pkl         # Active LGB ODI
└── .gitkeep
```

## Promotion Criteria

A new model version is promoted to `is_active=true` only if:

```
(val_MAE_new < val_MAE_current - 1.0)          # Meaningful MAE improvement
OR
(captain_accuracy_new > captain_accuracy_current + 0.02)  # 2pp captain accuracy improvement
```

If neither condition is met, the old model stays active. The new version is stored but not promoted.

## Promotion Process

```python
def promote_model_if_better(new_version: ModelVersion) -> bool:
    current = get_active_model(new_version.model_type, new_version.match_type)
    if current is None:
        # First version — promote unconditionally
        new_version.is_active = True
        db.save(new_version)
        return True

    mae_improved = new_version.val_mae < current.val_mae - 1.0
    cap_improved = new_version.captain_accuracy > current.captain_accuracy + 0.02

    if mae_improved or cap_improved:
        current.is_active = False
        new_version.is_active = True
        db.save_all([current, new_version])
        log_experiment(new_version, promoted=True, reason="mae" if mae_improved else "captain")
        return True

    log_experiment(new_version, promoted=False)
    return False
```

## Rollback Procedure

If a promoted model degrades in production:

```bash
# 1. Find previous active model ID
curl /api/v1/admin/models | jq '.[] | select(.model_type=="xgboost" and .match_type=="T20")'

# 2. Revert via admin API
curl -X POST /api/v1/admin/models/m01-t20-20260501/activate \
  -H "Authorization: Bearer $ADMIN_JWT"

# 3. Verify
curl /api/v1/admin/models | jq '.[] | select(.is_active)'
```

## Retention Policy

- Keep previous 2 versions of each model in `models/artifacts/`
- Delete models older than 3 versions
- Archive to S3 before deletion: `aws s3 cp models/artifacts/m01_t20_20260401.pkl s3://xithsense-models/`

## Retraining Schedule

| Trigger | Condition |
|---------|-----------|
| Scheduled (monthly) | 1st of every month, 3 AM IST |
| Data trigger | After 100 new T20 matches ingested |
| Accuracy trigger | Captain accuracy drops below 35% over 50 matches |
| Manual | Admin calls `POST /api/v1/admin/retrain` |
