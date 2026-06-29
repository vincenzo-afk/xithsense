# Captain Engine Specification

**Module:** `optimizer/captain_engine.py`

## Captain Types

| Type | Strategy | User |
|------|---------|------|
| `best_captain` | Highest ceiling × confidence | All modes |
| `safe_captain` | Highest consistency × moderate ceiling | Safe mode |
| `risk_captain` | Highest ceiling, low ownership (<15%) | GL mode |
| `vc_recommendation` | Second-highest ceiling, different team | All modes |

## Scoring Formula

```python
def captain_score(player, mode):
    if mode == "safe":
        return (player.fp_ceiling * 0.4) + (player.fp_avg_10 * 0.4) \
             + ((1 - player.fp_consistency) * 20)
    elif mode == "grand_league":
        return (player.fp_ceiling * 0.7) + (player.fp_avg_5 * 0.2) \
             + (differential_bonus(player.ownership_estimate) * 0.1)
    else:  # aggressive, small_league
        return (player.fp_ceiling * 0.6) + (player.fp_avg_5 * 0.4)
```

## Constraints

- Captain and VC must both be in the generated team's 11 players
- Captain ≠ Vice-Captain always
- Risk captain must have ownership_estimate < 15%
- All recommendations must have confidence ≥ 20%

## Output

```python
CaptainRecommendation(
    player_id=uuid,
    type="best_captain",
    ceiling_score=89.0,
    confidence=87,
    reasoning="Chasing specialist, highest ceiling this match"
)
```
