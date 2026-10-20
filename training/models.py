"""
Fantasy-points regressors and the on-disk model registry.

Three gradient-boosting regressors form the ML component of the ensemble
(M-01..M-03 in MODEL_REGISTRY.yaml). XGBoost / LightGBM / CatBoost are used when
installed; otherwise scikit-learn equivalents fill the same slots so the
platform works out of the box. P90 / P10 quantile models (M-06) supply each
player's ceiling and floor.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from backend.config import settings
from feature_engineering.builder import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

ARTIFACT_DIR = Path(settings.MODEL_ARTIFACTS_PATH)


def _make_estimators() -> Dict[str, tuple[str, object]]:
    """model_id -> (human-readable type, unfitted estimator)."""
    from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor

    models: Dict[str, tuple[str, object]] = {}
    try:
        import xgboost as xgb  # type: ignore
        models["M-01"] = ("xgboost", xgb.XGBRegressor(
            n_estimators=600, max_depth=5, learning_rate=0.03, subsample=0.8, colsample_bytree=0.7,
            reg_alpha=0.1, reg_lambda=1.0, min_child_weight=5, random_state=42))
    except ImportError:
        models["M-01"] = ("hist_gbm_l2", HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.04, max_depth=6, min_samples_leaf=25, l2_regularization=1.0,
            random_state=42))
    try:
        import lightgbm as lgb  # type: ignore
        models["M-02"] = ("lightgbm", lgb.LGBMRegressor(
            n_estimators=700, max_depth=7, learning_rate=0.025, num_leaves=63, subsample=0.8,
            colsample_bytree=0.7, objective="regression_l1", random_state=42, verbose=-1))
    except ImportError:
        models["M-02"] = ("hist_gbm_l1", HistGradientBoostingRegressor(
            loss="absolute_error", max_iter=400, learning_rate=0.04, max_leaf_nodes=31,
            min_samples_leaf=20, random_state=42))
    try:
        import catboost as cb  # type: ignore
        models["M-03"] = ("catboost", cb.CatBoostRegressor(
            iterations=600, depth=7, learning_rate=0.05, l2_leaf_reg=3.0, loss_function="MAE",
            random_seed=42, verbose=False))
    except ImportError:
        models["M-03"] = ("extra_trees", ExtraTreesRegressor(
            n_estimators=120, min_samples_leaf=20, max_features=0.6, max_samples=0.35, bootstrap=True,
            n_jobs=-1, random_state=42))
    return models


def _quantile(q: float):
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=300, learning_rate=0.05,
                                         min_samples_leaf=30, random_state=42)


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3:
        return float("nan")
    ra, rb = pd.Series(a).rank().values, pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


@dataclass
class TrainedBundle:
    version: str
    match_type: str
    features: List[str]
    regressors: Dict[str, object]
    model_types: Dict[str, str]
    ceiling: object
    floor: object
    metrics: Dict[str, dict] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    train_from: Optional[str] = None
    train_to: Optional[str] = None
    train_rows: int = 0

    def predict(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        Xf = X[self.features].astype("float32")
        preds = {mid: np.clip(m.predict(Xf), -5, 250) for mid, m in self.regressors.items()}
        ml = np.mean(np.vstack(list(preds.values())), axis=0)
        ceil = np.maximum(self.ceiling.predict(Xf), ml)
        flo = np.minimum(self.floor.predict(Xf), ml)
        return {"ml": ml, "ceiling": ceil, "floor": np.maximum(flo, -5), **preds}


def fit_bundle(train: pd.DataFrame, val: Optional[pd.DataFrame], match_type: str = "T20") -> TrainedBundle:
    if len(train) > 400_000:   # keep training time/memory bounded on the full Cricsheet archive
        train = train.sort_values("match_date").tail(400_000)
    X, y = train[FEATURE_COLUMNS].astype("float32"), train.fp.astype(float)
    estimators = _make_estimators()
    regs, types, metrics = {}, {}, {}
    for mid, (mtype, est) in estimators.items():
        est.fit(X, y)
        regs[mid], types[mid] = est, mtype
    ceiling, floor = _quantile(0.9), _quantile(0.1)
    ceiling.fit(X, y)
    floor.fit(X, y)
    bundle = TrainedBundle(
        version=f"{match_type.lower()}-{date.today():%Y%m%d}", match_type=match_type, features=list(FEATURE_COLUMNS),
        regressors=regs, model_types=types, ceiling=ceiling, floor=floor,
        train_from=str(train.match_date.min().date()), train_to=str(train.match_date.max().date()),
        train_rows=len(train),
    )
    if val is not None and len(val):
        yv = val.fp.astype(float).values
        p = bundle.predict(val)
        baseline = val.fp_avg_10.values
        for mid in list(regs) + ["ml"]:
            metrics[mid] = {
                "val_mae": float(np.mean(np.abs(p[mid] - yv))),
                "val_spearman": spearman(p[mid], yv),
                "train_mae": float(np.mean(np.abs(regs[mid].predict(X) - y))) if mid in regs else None,
            }
        metrics["baseline_form10"] = {"val_mae": float(np.mean(np.abs(baseline - yv))),
                                      "val_spearman": spearman(baseline, yv)}
        cover = float(np.mean((yv <= p["ceiling"]) & (yv >= p["floor"])))
        metrics["interval_coverage_p10_p90"] = {"value": cover}
    bundle.metrics = metrics
    bundle.feature_importance = _importance(regs, X, y)
    return bundle


def _importance(regs: Dict[str, object], X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
    for m in regs.values():
        imp = getattr(m, "feature_importances_", None)
        if imp is not None:
            s = pd.Series(imp, index=X.columns)
            return (s / s.sum()).sort_values(ascending=False).head(15).round(4).to_dict()
    # HistGradientBoosting has no built-in importances — use permutation on a sample
    from sklearn.inspection import permutation_importance
    m = next(iter(regs.values()))
    sample = X.sample(min(2000, len(X)), random_state=0)
    r = permutation_importance(m, sample, y.loc[sample.index], n_repeats=3, random_state=0, n_jobs=1)
    s = pd.Series(np.clip(r.importances_mean, 0, None), index=X.columns)
    return (s / (s.sum() or 1)).sort_values(ascending=False).head(15).round(4).to_dict()


def _pointer() -> dict:
    p = ARTIFACT_DIR / "ACTIVE.json"
    if not p.exists():
        return {}
    meta = json.loads(p.read_text())
    if "path" in meta:                       # legacy single-model pointer
        return {meta.get("match_type", "T20"): meta}
    return meta


def set_active(group: str, path: str, version: str) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    meta = _pointer()
    meta[group] = {"path": str(path), "version": version, "match_type": group}
    (ARTIFACT_DIR / "ACTIVE.json").write_text(json.dumps(meta, indent=2))
    _cache.clear()


def save_bundle(bundle: TrainedBundle) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / f"ensemble_{bundle.match_type.lower()}_{bundle.version}.joblib"
    joblib.dump(bundle, path)
    set_active(bundle.match_type, str(path), bundle.version)
    return path


_cache: Dict[str, TrainedBundle] = {}


def active_groups() -> Dict[str, dict]:
    return _pointer()


def load_active(group: str = "T20") -> Optional[TrainedBundle]:
    """Active bundle for a format group (T20 / ODI / Test); falls back to the T20 model."""
    meta = _pointer()
    entry = meta.get(group) or meta.get("T20")
    if not entry:
        return None
    path = entry["path"]
    if path not in _cache:
        try:
            _cache[path] = joblib.load(path)
        except Exception as e:  # corrupt / incompatible artifact
            logger.error("Failed to load model %s: %s", path, e)
            return None
    return _cache[path]
