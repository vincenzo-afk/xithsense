# Data Validation Rules

## Cricsheet Ingestion Validation

Every JSON file is validated against these rules before any database writes.

### Match-Level Validation

| Field | Rule | Action on Fail |
|-------|------|----------------|
| `meta.data_version` | Must be `"1.2.0"` | Log warning; continue with parsing |
| `info.match_type` | Must be in allowed list: T20, ODI, Test, IT20, IPL, BBL, PSL, CPL, WPL, NTB, CCH, ODM, MDM, WTB, WOD, IPT | Skip file; log error |
| `info.gender` | Must be `"male"` or `"female"` | Skip file |
| `info.team_type` | Must be `"club"` or `"international"` | Skip file |
| `info.teams` | Array of exactly 2 strings | Skip file |
| `info.dates` | Array of at least 1 valid ISO date | Skip file |
| `info.toss.decision` | Must be `"bat"` or `"field"` | Set NULL; continue |
| `info.innings` | Array of at least 1 | Skip file |

### Delivery-Level Validation

| Field | Rule | Action on Fail |
|-------|------|----------------|
| `batter` | Non-empty string | Skip delivery; log |
| `bowler` | Non-empty string | Skip delivery; log |
| `runs.batter` | Integer 0–36 | Set to 0; log |
| `runs.total` | Integer >= runs.batter | Recompute; log |
| `actual_delivery` | Pattern `\d+\.\d+` | Skip delivery; log |
| `wickets[].kind` | Must be in dismissal kinds list | Log; store raw value |

---

## API Input Validation (Pydantic Models)

### TeamPredictionRequest

```python
class TeamPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    match_id: str = Field(..., pattern=r"^\d+$", min_length=1, max_length=10)
    mode: Literal["safe", "grand_league", "aggressive", "small_league"]
    count: int = Field(default=1, ge=1, le=20)
    override_toss: Optional[TossOverride] = None
    override_playing_xi: Optional[dict[str, list[str]]] = None
```

### ChatRequest

```python
class ChatRequest(BaseModel):
    match_id: str = Field(..., pattern=r"^\d+$")
    message: str = Field(..., min_length=1, max_length=500)
    session_id: Optional[UUID] = None
```

### HumanRuleRequest (Admin)

```python
class HumanRuleRequest(BaseModel):
    id: str = Field(..., pattern=r"^RULE-\d{4}$")
    rule_type: Literal["player", "venue", "matchup", "context"]
    player_key: Optional[str] = Field(None, max_length=200)
    condition: dict = Field(..., min_length=1)
    impact_score: int = Field(..., ge=-100, le=100)
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: str = Field(..., min_length=5)
    is_active: bool = True
```

---

## Feature Store Validation

Before any feature vector is used in prediction:

```python
def validate_feature_vector(vector: np.ndarray, player_id: UUID) -> bool:
    # Check dimension
    assert len(vector) == EXPECTED_FEATURE_COUNT, f"Expected {EXPECTED_FEATURE_COUNT}, got {len(vector)}"

    # Check for NaN/Inf
    if np.any(np.isnan(vector)) or np.any(np.isinf(vector)):
        log.warning("nan_in_features", player_id=str(player_id))
        return False

    # Check range for known bounded features
    assert 0 <= vector[FEATURE_IDX["fp_consistency"]] <= 10
    assert 0 <= vector[FEATURE_IDX["is_chasing"]] <= 1
    assert 0 <= vector[FEATURE_IDX["batting_position_encoded"]] <= 1
    assert 0 <= vector[FEATURE_IDX["match_importance"]] <= 1

    return True
```

---

## Generated Team Validation

Every team output from the optimizer is validated before returning to user:

```python
def validate_team(team: GeneratedTeam) -> list[str]:
    errors = []
    if len(team.players) != 11:
        errors.append(f"Team has {len(team.players)} players, expected 11")
    if team.total_credits > 100.0:
        errors.append(f"Credits {team.total_credits} exceed 100.0")
    role_counts = Counter(p.role for p in team.players)
    if not (1 <= role_counts["WK"] <= 4):
        errors.append(f"WK count {role_counts['WK']} out of range [1,4]")
    if not (3 <= role_counts["BAT"] <= 6):
        errors.append(f"BAT count {role_counts['BAT']} out of range [3,6]")
    if not (1 <= role_counts["AR"] <= 4):
        errors.append(f"AR count {role_counts['AR']} out of range [1,4]")
    if not (3 <= role_counts["BOWL"] <= 6):
        errors.append(f"BOWL count {role_counts['BOWL']} out of range [3,6]")
    team_counts = Counter(p.team for p in team.players)
    for t, cnt in team_counts.items():
        if cnt > 7:
            errors.append(f"Team {t} has {cnt} players (max 7)")
    if team.captain.player_id == team.vice_captain.player_id:
        errors.append("Captain and VC are the same player")
    return errors
```
