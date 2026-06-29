# Coding Standards

## Python

**Formatter:** `black` (line length 88)  
**Linter:** `ruff`  
**Type checker:** `mypy`  
**Import order:** `isort` (profile=black)

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Module | snake_case | `team_optimizer.py` |
| Class | PascalCase | `EnsembleEngine` |
| Function | snake_case | `compute_rolling_features()` |
| Variable | snake_case | `player_score` |
| Constant | UPPER_SNAKE | `MAX_CREDITS = 100.0` |
| Private | leading underscore | `_normalise_scores()` |
| Type alias | PascalCase | `PlayerScoreMap = dict[UUID, float]` |

### Type Hints

All public functions must have complete type hints:

```python
# Good
def predict_fantasy_points(
    player_id: UUID,
    match_context: MatchContext,
    model: BaseModel,
) -> FantasyPointsPrediction:
    ...

# Bad
def predict_fantasy_points(player_id, match_context, model):
    ...
```

### Docstrings

All public modules, classes, and functions require docstrings (Google style):

```python
def compute_rolling_features(
    player_id: UUID,
    window: int,
    match_type: str,
) -> RollingFeature:
    """Compute rolling batting and bowling features for a player.

    Args:
        player_id: UUID of the player in the `player` table.
        window: Number of most recent matches to include (3, 5, or 10).
        match_type: Cricket format string (T20, ODI, IPL, etc.)

    Returns:
        RollingFeature dataclass with all computed fields.

    Raises:
        PlayerNotFoundError: If player_id does not exist in the database.
        InsufficientDataError: If player has fewer than 1 match in window.
    """
```

### Error Handling

```python
# Good — specific exception types
try:
    feature = load_feature(player_id)
except PlayerNotFoundError as e:
    logger.warning("player_not_found", player_id=str(player_id))
    raise HTTPException(status_code=404, detail=str(e))

# Bad — bare except
try:
    feature = load_feature(player_id)
except:
    pass
```

### Logging

Use `structlog` for all logging. Never use `print()` in production code.

```python
import structlog
log = structlog.get_logger(__name__)

log.info("prediction_generated", match_id=match_id, player_count=len(players))
log.warning("low_data_player", player_id=str(player_id), match_count=n)
log.error("optimizer_failed", error=str(e), match_id=match_id)
```

## API (FastAPI)

- Route functions must be `async def`
- Business logic belongs in `backend/services/`, not in route functions
- All request/response models use Pydantic v2 with explicit field types
- Route functions must not access the database directly — use repository classes
- Every route has a response_model declared

```python
# Good
@router.post("/predict/team", response_model=TeamPredictionResponse)
async def predict_team(
    request: TeamPredictionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamPredictionResponse:
    return await prediction_service.generate_team(request, db, current_user)

# Bad — logic in route
@router.post("/predict/team")
async def predict_team(request):
    players = db.query(Player).all()
    # ... 100 lines of logic ...
```

## Tests

- Test function names: `test_<what>_<scenario>_<expected_result>`
- One assertion concept per test function
- Never import from `__main__`
- Always use fixtures for shared state; never modify global state in tests

```python
# Good
def test_compute_fantasy_points_century_returns_correct_bonus():
    perf = make_performance(runs=100, fours=5, sixes=2)
    assert compute_fantasy_points(perf) == 100 + 5 + 4 + 16  # bonus

# Bad
def test_fantasy():
    # tests multiple things at once
```

## Git

- Commits follow Conventional Commits (see CONTRIBUTING.md)
- Maximum 400 lines changed per PR (excluding generated files)
- Every PR requires a description explaining the why, not just the what
