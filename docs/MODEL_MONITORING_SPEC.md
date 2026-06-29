# Model Monitoring Specification

**Goal:** Detect model performance degradation before it impacts user trust.

---

## Monitoring Dimensions

| Dimension | What We Watch | Frequency |
|-----------|--------------|-----------|
| Prediction accuracy | Captain accuracy, CPR on recent matches | After every 10 matches |
| Score distribution | Mean and std of predicted FP | Daily |
| Feature drift | Distribution shift in input features | Weekly |
| Prediction drift | Distribution shift in output scores | Daily |
| Model staleness | Days since last training | Daily |
| Segment performance | Accuracy by format/venue/role | Weekly |

---

## Accuracy Monitoring (Live Match Verification)

After each match completes, the system verifies prediction quality:

```python
# backend/services/model_monitor.py

async def verify_prediction_accuracy(match_id: str) -> AccuracyRecord:
    """Compare prediction vs actual for a completed match."""
    prediction = await prediction_repo.get_latest(match_id, phase="post_toss")
    actual_scores = await performance_repo.get_match_scores(match_id)

    if not prediction or not actual_scores:
        return None

    # Captain accuracy
    predicted_captain_id = prediction.recommended_teams[0].captain_id
    actual_top_scorer_id = max(actual_scores, key=lambda p: p.fantasy_points).player_id
    captain_correct = (predicted_captain_id == actual_top_scorer_id)

    # Correct player rate
    predicted_xi = {p.player_id for p in prediction.recommended_teams[0].players}
    actual_top11 = {p.player_id for p in sorted(actual_scores,
                    key=lambda p: p.fantasy_points, reverse=True)[:11]}
    overlap = len(predicted_xi & actual_top11)
    cpr = 1.0 if overlap >= 7 else 0.0

    # Fantasy points MAE
    predicted_fp_map = {p.player_id: p.fp_predicted for p in prediction.predicted_players}
    actual_fp_map = {p.player_id: p.fantasy_points for p in actual_scores}
    common = set(predicted_fp_map) & set(actual_fp_map)
    mae = sum(abs(predicted_fp_map[p] - actual_fp_map[p]) for p in common) / len(common)

    record = AccuracyRecord(
        match_id=match_id,
        captain_correct=captain_correct,
        overlap_count=overlap,
        cpr=cpr,
        fp_mae=mae,
        model_version_id=prediction.model_version_id,
        verified_at=datetime.utcnow()
    )

    await accuracy_repo.save(record)
    await check_accuracy_alert(record)
    return record
```

---

## Rolling Accuracy Tracker

Computed over last N matches:

```python
async def get_rolling_accuracy(n_matches: int = 50) -> RollingAccuracy:
    recent = await accuracy_repo.get_latest(n=n_matches)
    return RollingAccuracy(
        n_matches=len(recent),
        captain_accuracy=sum(r.captain_correct for r in recent) / len(recent),
        cpr=sum(r.cpr for r in recent) / len(recent),
        avg_fp_mae=sum(r.fp_mae for r in recent) / len(recent),
        window_days=(recent[0].verified_at - recent[-1].verified_at).days,
    )
```

---

## Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|---------|--------|
| Captain accuracy (50 matches) | < 37% | < 33% | Warning: log + email admin; Critical: retrain queued |
| CPR (50 matches) | < 58% | < 52% | Warning: investigate; Critical: retrain queued |
| FP MAE | > 15 pts | > 18 pts | Warning: review features; Critical: retrain |
| Prediction drift | z-score > 2.0 | z-score > 3.0 | Warning: review data; Critical: pause predictions |
| Feature drift | PSI > 0.1 | PSI > 0.25 | Warning: review; Critical: full feature rebuild |
| Model staleness | > 45 days | > 90 days | Warning: schedule retrain; Critical: force retrain |

---

## Feature Drift Detection

Population Stability Index (PSI) measures distribution shift:

```python
def compute_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """PSI < 0.1: no change; 0.1-0.25: moderate; > 0.25: significant drift."""
    expected_hist, bin_edges = np.histogram(expected, bins=bins)
    actual_hist, _ = np.histogram(actual, bins=bin_edges)

    expected_pct = (expected_hist + 1e-6) / len(expected)
    actual_pct   = (actual_hist   + 1e-6) / len(actual)

    psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return psi

# Check weekly on key features
KEY_FEATURES_FOR_DRIFT = ["fp_avg_5", "avg_sr_5", "avg_wickets_5", "venue_chasing_win_pct"]
```

---

## Prediction Drift Detection

```python
def detect_prediction_drift(baseline_predictions: list[float],
                             recent_predictions: list[float]) -> DriftReport:
    baseline_mean = np.mean(baseline_predictions)
    baseline_std  = np.std(baseline_predictions)
    recent_mean   = np.mean(recent_predictions)
    z_score = abs(recent_mean - baseline_mean) / (baseline_std + 1e-6)

    return DriftReport(
        baseline_mean=baseline_mean,
        recent_mean=recent_mean,
        z_score=z_score,
        drifted=(z_score > 2.0),
        severity="critical" if z_score > 3.0 else "warning" if z_score > 2.0 else "ok"
    )
```

---

## Monitoring Dashboard Metrics

Exposed at `GET /api/v1/admin/metrics`:

```json
{
  "model_accuracy": {
    "captain_accuracy_last_50": 0.401,
    "captain_accuracy_last_10": 0.420,
    "cpr_last_50": 0.621,
    "fp_mae_last_50": 11.94,
    "matches_evaluated": 50,
    "last_evaluated_at": "2026-06-25T09:00:00Z"
  },
  "model_health": {
    "t20_model_id": "m01-t20-20260601",
    "t20_model_age_days": 24,
    "t20_val_mae": 11.94,
    "feature_drift_psi_max": 0.08,
    "prediction_drift_z_score": 0.31,
    "status": "healthy"
  },
  "alert_history": [
    {"type": "warning", "metric": "captain_accuracy", "value": 0.37,
     "threshold": 0.38, "fired_at": "2026-06-10T09:00:00Z", "resolved": true}
  ]
}
```

---

## Auto-Retrain Trigger

```python
async def check_and_trigger_retrain() -> None:
    """Runs daily at 1 AM IST via Celery Beat."""
    accuracy = await get_rolling_accuracy(n_matches=50)
    model_age_days = (datetime.utcnow() - active_model.trained_at).days

    should_retrain = (
        accuracy.captain_accuracy < CRITICAL_CAPTAIN_ACCURACY or
        accuracy.cpr < CRITICAL_CPR or
        model_age_days > 30  # monthly scheduled retrain
    )

    if should_retrain:
        reason = "accuracy_degraded" if accuracy.captain_accuracy < 0.35 else "scheduled"
        retrain_models.delay(format_type="T20", reason=reason)
        await send_admin_alert(
            subject=f"Model retrain triggered: {reason}",
            body=f"CA={accuracy.captain_accuracy:.1%}, CPR={accuracy.cpr:.1%}, Age={model_age_days}d"
        )
```
