# Ownership Estimation Specification

**Module:** `optimizer/ownership_estimator.py`

Ownership % = the fraction of fantasy contest entries expected to include a given player.

---

## Why Ownership Matters

- **Safe teams:** prefer high-ownership picks (consensus; lower risk)
- **Grand league teams:** prefer low-ownership, high-ceiling picks (differential edge)
- **Captain choice:** in GL, a low-ownership captain who outperforms creates massive rank jumps

---

## Ownership Estimation Methods

### Method 1: Historical Ownership Model (MVP)

No real-time crowd data available in MVP. Estimate from historical patterns:

```python
def estimate_ownership_pct(
    player: Player,
    match_context: MatchContext,
    ensemble_score: float,
    all_player_scores: list[float],
) -> float:
    """
    Estimate ownership % based on:
    - Player popularity tier
    - Relative ensemble score rank
    - Recent media visibility
    - Captain/VC likelihood
    """
    # Base ownership from score rank
    rank = sorted(all_player_scores, reverse=True).index(ensemble_score) + 1
    n_players = len(all_player_scores)
    rank_pct = rank / n_players   # 0 = best, 1 = worst

    # Ownership follows power law: top players get disproportionate ownership
    base_ownership = (1 - rank_pct) ** 1.8 * 85.0   # max ~85% for rank 1

    # Adjustments
    if player.primary_role == "WK" and rank <= 3:
        base_ownership *= 1.4   # WK options limited; top WK gets more

    if ensemble_score / max(all_player_scores) > 0.95:
        base_ownership = min(base_ownership * 1.3, 90.0)   # near-lock pick

    if match_context.is_final_or_knockout:
        base_ownership *= 0.85   # more spread in knockout contests

    return round(min(max(base_ownership, 0.5), 95.0), 1)
```

### Method 2: Crowd-Sourced (Phase 2)

In Phase 2, collect ownership data from:
- XithSense users (anonymised, opt-in)
- Community APIs (if available)

```python
# Store in ownership_estimate table
# Update hourly during pre-match window
# Use real data instead of model estimate
```

---

## Ownership Tiers

| Tier | Ownership % | Label | Strategy |
|------|------------|-------|---------|
| Lock | > 75% | 🔒 Lock | Must-pick in all modes |
| Popular | 50–75% | ⭐ Popular | Safe teams; skip in GL |
| Moderate | 25–50% | Moderate | Include or exclude based on mode |
| Differential | 10–25% | 🔀 Diff | GL potential if ceiling high |
| Punt | < 10% | 🎯 Punt | High-risk GL only |
| Unique | < 3% | 💡 Unique | Extreme GL differentiator |

---

## Differential Pick Identification

A player is flagged as a **differential pick** for GL if:

```python
def is_differential(player: Player, ownership_pct: float,
                     ceiling_score: float, mean_ceiling: float) -> bool:
    """Identify high-upside, low-ownership players for GL."""
    return (
        ownership_pct < 20.0          # low ownership
        and ceiling_score > mean_ceiling * 0.85   # reasonable ceiling
        and player.fp_avg_10 > 15.0   # some track record
        and player.fp_30plus_rate > 0.2  # has done it before
    )
```

---

## Output in API Response

```json
{
  "player_id": "uuid",
  "full_name": "Noor Ahmad",
  "ownership_estimate": "4%",
  "ownership_tier": "punt",
  "is_differential": true,
  "differential_reason": "Death-overs specialist, 4% ownership vs 95 FP ceiling. Dry pitch suits wrist spin.",
  "ceiling_score": 95.0,
  "fp_avg_5": 28.3
}
```

---

## Ownership Table (Phase 2)

```sql
CREATE TABLE ownership_estimate (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id    VARCHAR(20) NOT NULL REFERENCES match(id),
    player_id   UUID NOT NULL REFERENCES player(id),
    contest_type VARCHAR(20),      -- "grand_league" | "small_league"
    ownership_pct DECIMAL(5,2),
    source       VARCHAR(50),      -- "model" | "crowd_sourced" | "manual"
    estimated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(match_id, player_id, contest_type, source)
);
```
