# Data Quality Rules

## Quality Dimensions

| Dimension | Definition | Measurement |
|-----------|-----------|-------------|
| Completeness | Required fields are present | % of records with all mandatory fields populated |
| Accuracy | Values are correct per domain rules | % of fantasy_points values within valid range |
| Consistency | No contradictory values | % of deliveries where runs_total = runs_batter + runs_extras |
| Timeliness | Data freshness for predictions | Hours since last ingestion run |
| Uniqueness | No duplicate records | Duplicate match_id count (should be 0) |

---

## Quality Checks (Run After Every Ingestion)

```python
# scripts/run_quality_checks.py

def check_delivery_completeness(db) -> float:
    """Returns % of deliveries with all mandatory fields non-null."""
    total = db.scalar("SELECT COUNT(*) FROM delivery")
    complete = db.scalar("""
        SELECT COUNT(*) FROM delivery
        WHERE batter IS NOT NULL
          AND bowler IS NOT NULL
          AND runs_total IS NOT NULL
    """)
    return complete / total

def check_fantasy_points_range(db) -> int:
    """Returns count of out-of-range fantasy_points values (should be 0)."""
    return db.scalar("""
        SELECT COUNT(*) FROM player_match_performance
        WHERE fantasy_points < -10 OR fantasy_points > 500
    """)

def check_delivery_consistency(db) -> int:
    """Returns count of inconsistent delivery records (should be 0)."""
    return db.scalar("""
        SELECT COUNT(*) FROM delivery
        WHERE runs_total != (runs_batter + runs_extras)
    """)

def check_duplicate_matches(db) -> int:
    return db.scalar("""
        SELECT COUNT(*) - COUNT(DISTINCT id) FROM match
    """)

def check_feature_freshness(db) -> float:
    """Returns hours since last rolling_feature update."""
    last_update = db.scalar("SELECT MAX(created_at) FROM rolling_feature")
    return (datetime.utcnow() - last_update).total_seconds() / 3600
```

---

## Quality Thresholds

| Check | Pass Threshold | Warning Threshold | Fail |
|-------|---------------|-------------------|------|
| Delivery completeness | ≥ 99.9% | 99.0–99.9% | < 99.0% |
| Fantasy points range violations | 0 | 1–5 | > 5 |
| Delivery consistency errors | 0 | 1–10 | > 10 |
| Duplicate matches | 0 | — | ≥ 1 |
| Feature freshness | < 8 hours | 8–24 hours | > 24 hours |
| Players without cricsheet_key | 0 | — | ≥ 1 |
| Matches with no deliveries | 0 | 1–3 | > 3 |

---

## Known Quality Issues in Cricsheet Data

| Issue | Prevalence | Handling |
|-------|-----------|---------|
| Retired hurt not fully documented in early matches | Rare | Treat as not dismissed |
| Missing `non_striker` in very old matches (pre-2010) | Occasional | Set NULL; not critical |
| Inconsistent venue names across seasons | Common | Venue alias mapping table |
| Player key slightly different across old vs new files | Rare | Fuzzy match + manual review |
| Super over not always tagged as separate innings | Rare | Detect by over count > expected; tag manually |

---

## Quality Report Schedule

Quality checks run automatically after every ingestion pipeline:
1. Results logged to `evaluation/` directory as `quality_report_{date}.json`
2. Failures trigger Sentry alert and Telegram message to admin
3. Weekly summary emailed to admin

```json
{
  "run_at": "2026-06-25T02:15:00Z",
  "checks": {
    "delivery_completeness": {"value": 99.97, "status": "pass"},
    "fantasy_points_range": {"value": 0, "status": "pass"},
    "delivery_consistency": {"value": 0, "status": "pass"},
    "duplicate_matches": {"value": 0, "status": "pass"},
    "feature_freshness_hours": {"value": 0.4, "status": "pass"}
  },
  "overall": "pass"
}
```
