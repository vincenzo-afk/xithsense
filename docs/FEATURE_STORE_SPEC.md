# Feature Store Specification

**Purpose:** Centralised, versioned storage of pre-computed features for fast prediction inference.

---

## Architecture

```
                    Feature Store Architecture
                    ──────────────────────────

  Cricsheet DB                    Feature Store                   Model Inference
  (raw data)                      (computed features)              (prediction)
  ──────────     ETL Pipeline     ───────────────────   Lookup    ──────────────
  delivery   ──────────────────►  rolling_feature   ──────────►
  innings                         venue_stat         (Redis+PG)   assemble_vector()
  match                           matchup_stat                     → 47-dim array
  player                                                           → batch_predict()
```

---

## Feature Store Layers

### Layer 1: Persistent Store (PostgreSQL)

Ground truth for all computed features. Rebuilt from raw data via `build_features.py`.

| Table | Primary Key | Update Frequency |
|-------|------------|-----------------|
| `rolling_feature` | `(player_id, match_type, as_of_date, window)` | After each new match |
| `venue_stat` | `(venue_id, match_type)` | After each new match at venue |
| `matchup_stat` | `(player_id, bowler_type, match_type)` | After each new match |

### Layer 2: Cache (Redis)

Pre-serialised feature vectors for fast lookup. Avoids repeated DB joins per prediction.

```python
# Key: feat:{player_id}:{match_type}:{date}
# Value: JSON-serialised dict of all 47 features
# TTL: 6 hours

cache_key = f"feat:{player_id}:{match_type}:{as_of_date}"
cached = await redis.get(cache_key)
if cached:
    return FeatureVector.parse_raw(cached)
```

### Layer 3: Request-Time Context (In-Memory)

Context features computed at prediction time, not stored:

```python
@dataclass
class ContextFeatures:
    is_chasing: int
    batting_position_encoded: float
    is_home_ground: int
    match_importance: float
    days_since_last_match: int
    opposition_bowling_strength: float
    match_type_encoded: int
    primary_role_encoded: int
    batting_style_encoded: int
    bowling_style_encoded: int
```

---

## Feature Vector Assembly

```python
async def assemble_feature_vector(
    player_id: UUID,
    match_type: str,
    as_of_date: date,
    match_context: MatchContext,
) -> np.ndarray:
    """
    Assembles the full 47-feature vector for a player.
    Returns numpy array in FEATURE_ORDER (defined in FEATURE_LIST.yaml).
    """
    # 1. Load persistent features (cache-first)
    rolling = await feature_cache.get_or_load_rolling(player_id, match_type, as_of_date)
    venue   = await feature_cache.get_or_load_venue(player_id, match_context.venue_id, match_type)
    matchup = await feature_cache.get_or_load_matchup(player_id, match_context.opp_bowling_type, match_type)

    # 2. Compute context features in-memory
    context = compute_context_features(player_id, match_context)

    # 3. Apply missing value fallbacks
    rolling = apply_rolling_fallbacks(rolling, player_id, match_type)
    venue   = apply_venue_fallbacks(venue, match_type)
    matchup = apply_matchup_fallbacks(matchup, match_type)

    # 4. Assemble in canonical order
    vector = np.array([
        rolling.fp_avg_3,     rolling.fp_avg_5,     rolling.fp_avg_10,
        rolling.fp_ceiling,   rolling.fp_floor,     rolling.fp_consistency,
        rolling.fp_30plus_rate,
        rolling.avg_runs_3,   rolling.avg_runs_5,   rolling.avg_runs_10,
        rolling.avg_sr_3,     rolling.avg_sr_5,
        rolling.avg_sixes_5,  rolling.avg_fours_5,
        rolling.avg_wickets_3, rolling.avg_wickets_5, rolling.avg_wickets_10,
        rolling.avg_economy_3, rolling.avg_economy_5,
        rolling.dot_ball_rate_5, rolling.wicket_per_over_5,
        venue.avg_runs_batting, venue.avg_wickets_bowling,
        venue.avg_first_innings, venue.chasing_win_pct,
        venue.spin_wicket_pct,  venue.total_matches,
        matchup.sr_vs_pace_right,  matchup.sr_vs_pace_left,
        matchup.sr_vs_spin_off,    matchup.sr_vs_spin_left,
        matchup.dismissal_rate_vs_pace_left, matchup.dismissal_rate_vs_spin_wrist,
        context.is_chasing,        context.batting_position_encoded,
        context.is_home_ground,    context.match_importance,
        context.days_since_last_match, context.opposition_bowling_strength,
        context.match_type_encoded, context.primary_role_encoded,
        context.batting_style_encoded, context.bowling_style_encoded,
    ], dtype=np.float32)

    assert len(vector) == EXPECTED_FEATURE_COUNT, f"Got {len(vector)} features"
    return vector
```

---

## Missing Value Fallback Hierarchy

```
Player has sufficient data?
    Yes → use player's own computed feature value
    No  → Player's career average (ignoring window)
              No career data → Role average (all BAT/BOWL/AR/WK)
                    No role data → Global match average
                           Still missing → 0.0 (with low_data=True flag)
```

---

## Feature Store Rebuild

```bash
# Full rebuild (all players, all formats)
python scripts/build_features.py
# Runtime: ~12 minutes

# Incremental (only new matches since date)
python scripts/build_features.py --from 2026-06-01
# Runtime: ~2 minutes

# Single player rebuild
python scripts/build_features.py --player-id d4e5f6a7-b8c9-0123-defa-bc4567890123
```

---

## Feature Versioning

`models/FEATURE_LIST.yaml` tracks feature versions.  
When a new feature is added or renamed, bump `version: "v1.3"`.  
Active models store the feature version they were trained on.  
If active model's feature version ≠ current feature list → deployment blocked until model retrained.
