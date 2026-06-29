# Model Serving Specification

**Module:** `training/model_registry.py`, `backend/services/ml_service.py`

---

## Model Loading Strategy

### Startup Loading (Eager)

On API server startup, all active models are loaded into memory:

```python
# backend/startup.py
async def load_models_on_startup():
    """Load all active model versions into memory at startup."""
    registry = ModelRegistry()
    for format_type in ["T20", "ODI", "Test"]:
        try:
            model_bundle = registry.load_active_bundle(format_type)
            MODEL_CACHE[format_type] = model_bundle
            log.info("model_loaded",
                format=format_type,
                model_ids=[m.id for m in model_bundle.models],
                artifact_paths=[m.artifact_path for m in model_bundle.models])
        except ModelNotFoundError:
            log.warning("no_active_model", format=format_type)
            MODEL_CACHE[format_type] = None

    if MODEL_CACHE.get("T20") is None:
        log.critical("t20_model_missing_at_startup")
        raise RuntimeError("T20 model required for production")
```

### Model Bundle Structure

```python
@dataclass
class ModelBundle:
    format_type: str                    # "T20" | "ODI" | "Test"
    xgb_model: XGBRegressor
    lgb_model: LGBMRegressor
    cat_model: CatBoostRegressor
    feature_version: str                # e.g. "v1.2"
    trained_at: datetime
    val_mae: float
    captain_accuracy: float

    def predict(self, feature_matrix: np.ndarray) -> np.ndarray:
        """Ensemble prediction: mean of 3 models."""
        xgb_pred = self.xgb_model.predict(feature_matrix)
        lgb_pred = self.lgb_model.predict(feature_matrix)
        cat_pred = self.cat_model.predict(feature_matrix)
        return np.mean([xgb_pred, lgb_pred, cat_pred], axis=0)
```

---

## Model Registry

```python
# training/model_registry.py

class ModelRegistry:
    def __init__(self, artifact_dir: str = settings.MODEL_ARTIFACTS_PATH,
                 db: AsyncSession = None):
        self.artifact_dir = artifact_dir
        self.db = db

    def load_active_bundle(self, format_type: str) -> ModelBundle:
        versions = self._get_active_versions(format_type)
        if not versions:
            raise ModelNotFoundError(f"No active model for format {format_type}")

        return ModelBundle(
            format_type=format_type,
            xgb_model=self._load_artifact(versions["xgboost"]),
            lgb_model=self._load_artifact(versions["lightgbm"]),
            cat_model=self._load_artifact(versions["catboost"]),
            feature_version=versions["feature_version"],
            trained_at=versions["trained_at"],
            val_mae=versions["val_mae"],
            captain_accuracy=versions["captain_accuracy"],
        )

    def _load_artifact(self, version: ModelVersion):
        path = os.path.join(self.artifact_dir, version.artifact_filename)
        if version.model_type == "catboost":
            model = CatBoostRegressor()
            model.load_model(path)
            return model
        else:
            return joblib.load(path)

    def register_new_version(self, version: ModelVersion, artifact: object) -> None:
        filename = f"{version.id}.{'cbm' if version.model_type == 'catboost' else 'pkl'}"
        path = os.path.join(self.artifact_dir, filename)
        if version.model_type == "catboost":
            artifact.save_model(path)
        else:
            joblib.dump(artifact, path)
        version.artifact_path = path
        self.db.add(version)

    def promote(self, new_version_id: str, format_type: str) -> bool:
        current = self._get_active_for_type(format_type)
        new = self._get_by_id(new_version_id)
        if not self._meets_promotion_criteria(new, current):
            return False
        if current:
            current.is_active = False
        new.is_active = True
        self.db.commit()
        MODEL_CACHE[format_type] = self.load_active_bundle(format_type)
        log.info("model_promoted", new_version=new_version_id, format=format_type)
        return True
```

---

## Inference Workflow

```python
# backend/services/ml_service.py

class MLService:
    def __init__(self):
        self.model_cache = MODEL_CACHE  # loaded at startup

    async def batch_predict(
        self,
        feature_matrix: np.ndarray,      # shape: (n_players, 47)
        match_type: str,
    ) -> np.ndarray:
        """Return predicted fantasy points for all players."""
        bundle = self.model_cache.get(self._map_format(match_type))

        if bundle is None:
            log.warning("model_unavailable_using_fallback", match_type=match_type)
            return self._form_only_fallback(feature_matrix)

        # Validate input
        assert feature_matrix.shape[1] == EXPECTED_FEATURE_COUNT, \
            f"Feature mismatch: expected {EXPECTED_FEATURE_COUNT}, got {feature_matrix.shape[1]}"

        # Run ensemble prediction
        start = time.perf_counter()
        predictions = bundle.predict(feature_matrix)
        elapsed_ms = (time.perf_counter() - start) * 1000

        prediction_duration.observe(elapsed_ms / 1000)
        log.info("batch_prediction_complete",
                 n_players=len(predictions),
                 duration_ms=elapsed_ms,
                 model_bundle=bundle.format_type)

        # Clip to valid range
        return np.clip(predictions, a_min=-10.0, a_max=500.0)

    def _map_format(self, match_type: str) -> str:
        T20_FORMATS = {"T20", "IT20", "IPL", "BBL", "PSL", "CPL", "WPL", "NTB", "CCH"}
        ODI_FORMATS  = {"ODI", "ODM", "WOD"}
        TEST_FORMATS = {"Test", "MDM", "WTB"}
        if match_type in T20_FORMATS: return "T20"
        if match_type in ODI_FORMATS:  return "ODI"
        if match_type in TEST_FORMATS: return "Test"
        return "T20"  # default fallback

    def _form_only_fallback(self, feature_matrix: np.ndarray) -> np.ndarray:
        """Return fp_avg_5 as fallback prediction when model unavailable."""
        fp_avg_5_idx = FEATURE_IDX["fp_avg_5"]
        return feature_matrix[:, fp_avg_5_idx]
```

---

## Batch vs Real-Time Prediction

| Mode | Trigger | Use Case | Latency Target |
|------|---------|---------|----------------|
| Real-time (22 players) | API request | Pre-match team generation | < 200ms |
| Batch (historical) | Celery task | Backtesting | Throughput > 1000 matches/min |
| Scheduled | Celery Beat | Cache warm-up | Background, no latency req |

---

## Model Hot-Reload (Zero Downtime)

When admin promotes a new model version:

```python
async def hot_reload_model(format_type: str) -> None:
    """Replace model in cache without restarting the API."""
    new_bundle = model_registry.load_active_bundle(format_type)
    MODEL_CACHE[format_type] = new_bundle
    log.info("model_hot_reloaded",
             format=format_type,
             val_mae=new_bundle.val_mae)
```

No restart required. New predictions use the new model immediately.

---

## Memory Footprint

| Model | Size on Disk | Size in RAM |
|-------|-------------|------------|
| XGBoost T20 (pkl) | ~18 MB | ~45 MB |
| LightGBM T20 (pkl) | ~12 MB | ~30 MB |
| CatBoost T20 (cbm) | ~25 MB | ~60 MB |
| **T20 Bundle total** | **~55 MB** | **~135 MB** |
| ODI Bundle | ~55 MB | ~135 MB |
| **All models loaded** | **~110 MB** | **~270 MB** |
