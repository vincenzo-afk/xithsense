# Metrics Definitions

## Prediction Quality Metrics

### Correct Player Rate (CPR)

**Definition:** Fraction of matches where the predicted XI contains ≥ 7 players from the actual top-11 fantasy point scorers.

```python
def correct_player_rate(predicted_xi: list[str], actual_ranked: list[str]) -> float:
    top_11_actual = set(actual_ranked[:11])
    overlap = len(set(predicted_xi) & top_11_actual)
    return 1.0 if overlap >= 7 else 0.0

cpr = sum(correct_player_rate(p, a) for p, a in matches) / len(matches)
```

---

### Captain Accuracy (CA)

**Definition:** Fraction of matches where the recommended `best_captain` is the actual top fantasy point scorer.

```python
def captain_accuracy(predicted_captain: str, actual_top_scorer: str) -> bool:
    return predicted_captain == actual_top_scorer

ca = sum(captain_accuracy(p, a) for p, a in matches) / len(matches)
```

---

### Top-3 Captain Rate

**Definition:** Fraction of matches where the actual top scorer appears in the top-3 captain recommendations.

```python
top3_rate = sum(
    1 for pred_captains, actual in matches
    if actual in [c.player_name for c in pred_captains[:3]]
) / len(matches)
```

---

### Fantasy Points MAE

**Definition:** Mean absolute error between predicted total fantasy points for the selected team vs actual.

```python
fp_mae = sum(abs(pred_total_fp - actual_total_fp) for ...) / n
```

---

### Rank Correlation (Spearman ρ)

**Definition:** Spearman rank correlation between predicted player scores and actual fantasy points, per match, averaged across all matches.

```python
from scipy.stats import spearmanr
rho_list = [spearmanr(pred_scores, actual_fp).statistic for ... in matches]
avg_rho = sum(rho_list) / len(rho_list)
```

---

## Business Metrics

| Metric | Definition | Measurement |
|--------|-----------|-------------|
| MRR | Monthly Recurring Revenue | Σ(active premium subscriptions × plan price) |
| Churn Rate | % of subscribers who cancel per month | cancelled / active_start_of_month |
| DAU | Daily Active Users | Unique user_ids with API calls per day |
| Conversion Rate | Free to Premium | new_premium / new_free × 100 |
| NPS | Net Promoter Score | % Promoters − % Detractors (from in-app survey) |
| ARPU | Average Revenue Per User | MRR / total_active_users |

---

## Technical Metrics

| Metric | Definition | Tool |
|--------|-----------|------|
| API p50/p95/p99 latency | Response time percentiles | Prometheus histogram |
| Error rate | 5xx responses / total responses | Prometheus counter |
| Cache hit rate | Redis hits / total lookups | Redis INFO stats |
| Ingestion success rate | Files parsed / total files | Custom metric |
| Celery queue depth | Pending tasks in each queue | Flower / Prometheus |
| Model prediction time | ms per `predict_match()` call | Custom metric |
