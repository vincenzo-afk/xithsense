# Testing Strategy

## Test Pyramid

```
         ┌──────────────┐
         │  E2E Tests   │  (5%)  — Critical user flows only
         ├──────────────┤
         │ Integration  │  (25%) — API routes, DB, Redis
         ├──────────────┤
         │  Unit Tests  │  (70%) — Functions, services, rules engine
         └──────────────┘
```

## Unit Tests (`tests/unit/`)

**Scope:** Individual functions and classes with all external dependencies mocked.

**Tools:** `pytest`, `pytest-mock`, `freezegun`

**Coverage targets:**
| Module | Target |
|--------|--------|
| `backend/services/` | ≥ 85% |
| `training/` | ≥ 75% |
| `optimizer/` | ≥ 90% |
| `human_rules/` | ≥ 90% |
| `llm/` | ≥ 70% |

**Key unit test suites:**
- `test_fantasy_points.py` — Verify Dream11 scoring formula for 20+ scenarios
- `test_feature_engineering.py` — Rolling window computations on known datasets
- `test_rule_engine.py` — Rule firing, condition evaluation, confidence weighting
- `test_ensemble.py` — Weight combination, normalisation, score ranges
- `test_optimizer.py` — All generated teams satisfy Dream11 constraints
- `test_captain_engine.py` — Captain/VC logic, type differentiation

## Integration Tests (`tests/integration/`)

**Scope:** Full stack with real DB (test schema), real Redis, mocked LLM.

**Tools:** `pytest-asyncio`, `httpx` (async test client), `factory-boy`

**Key integration tests:**
- `test_api_auth.py` — Register, login, refresh, invalid token
- `test_api_predict.py` — Full prediction pipeline end-to-end
- `test_api_chat.py` — Chat endpoint with mocked LLM
- `test_ingestion.py` — Ingest 50 sample JSON files, assert DB counts
- `test_payments.py` — Webhook handling with test signatures

## Backtesting Tests (`tests/backtesting/`)

```bash
# Run accuracy regression tests on 2025 held-out data
pytest tests/backtesting/test_accuracy.py -v
```

Tests assert:
- Captain accuracy ≥ 35% (regression floor — fail if model degrades)
- Correct player rate ≥ 55%
- No prediction returns team with invalid Dream11 constraints

## Running Tests

```bash
make test               # All tests
make test-unit          # Unit only (fast, ~30s)
make test-integration   # Integration (requires DB + Redis running)
make test-cov           # With coverage report
pytest tests/unit/test_optimizer.py -v  # Single file
```

## Test Database

Integration tests use a `xithsense_test` schema in Supabase (or local PostgreSQL).  
`conftest.py` creates all tables, loads fixtures, and drops them after each test session.

```python
# conftest.py
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(settings.TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
```

## CI Test Matrix

```yaml
# .github/workflows/test.yml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
    os: [ubuntu-latest]
```
