# Backtesting Specification

**Module:** `backtesting/`  
**Entry:** `backtesting/run_backtest.py`

## Purpose

Simulate historical predictions using only data available before each match. Measure accuracy of team selection, captain picks, and fantasy points prediction.

## Strict No-Lookahead Rule

For a match on date D:
- Features use only data from matches before date D
- Playing XI from the actual match record (known post-match)
- Weather and toss from match metadata

Never use data from date D or later in feature computation for match D.

## Metrics Computed

| Metric | Definition |
|--------|-----------|
| `correct_player_rate` | Fraction of matches where ≥ 7 of predicted 11 match actual top-11 by FP |
| `captain_accuracy` | Fraction of matches where predicted best_captain = actual highest FP scorer |
| `vc_accuracy` | Fraction of matches where predicted vc = actual 2nd highest FP scorer |
| `avg_fp_error` | Mean absolute error: predicted_total_fp vs actual_total_fp of selected team |
| `top3_captain_rate` | Fraction of matches where actual top scorer is in predicted top-3 captains |
| `simulated_roi` | Simulated return if ₹50 bet on GL team per match (simplified) |

## CLI

```bash
# Full backtest on last 10,000 T20 matches
python backtesting/run_backtest.py --n 10000 --format T20

# IPL-only backtest for 2025 season
python backtesting/run_backtest.py --format IPL --from 2025-03-01 --to 2025-05-31

# Output to file
python backtesting/run_backtest.py --n 5000 --output results/backtest_20260601.json
```

## Report Format

```json
{
  "run_id": "uuid",
  "match_type": "T20",
  "total_matches": 10000,
  "date_range": ["2018-01-01", "2025-12-31"],
  "metrics": {
    "correct_player_rate": 0.621,
    "captain_accuracy": 0.401,
    "vc_accuracy": 0.312,
    "avg_fp_error": 47.3,
    "top3_captain_rate": 0.712
  },
  "model_version": "m01-t20-20260601",
  "run_at": "2026-06-01T12:00:00Z"
}
```
