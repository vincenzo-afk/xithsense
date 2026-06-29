# Test Plan

## Scope

All modules in the XithSense backend, ML pipeline, and optimizer.  
Frontend testing is deferred to Phase 2 (React SPA).

## Test Environments

| Environment | DB | LLM | Purpose |
|------------|-----|-----|---------|
| Local unit | In-memory / mocked | Mocked | Fast developer feedback |
| Local integration | PostgreSQL (Docker) + Redis | Mocked | Full stack verification |
| CI | PostgreSQL (GitHub Actions service) + Redis | Mocked | Automated quality gate |
| Staging | Supabase (staging) | Real (limited) | Pre-production verification |

## Test Types

### Unit Tests
- Location: `tests/unit/`
- Scope: Single functions and classes with all external dependencies mocked
- Speed target: Full suite < 60 seconds
- No database, no network, no file system (unless testing file parsing)

### Integration Tests
- Location: `tests/integration/`
- Scope: API endpoints, database operations, Celery tasks
- Requires running PostgreSQL and Redis
- Speed target: Full suite < 5 minutes

### Backtesting Tests
- Location: `tests/backtesting/`
- Scope: Model accuracy regression tests on held-out historical data
- Run weekly in CI; always run before model promotion
- Speed target: < 20 minutes

### Load Tests
- Location: `tests/performance/`
- Tool: k6
- Run before major releases
- See `tests/PERFORMANCE_TESTS.md`

## Coverage Requirements

All PRs must maintain or improve these thresholds:

| Module | Minimum |
|--------|---------|
| `backend/services/` | 85% |
| `backend/routes/` | 80% |
| `optimizer/` | 90% |
| `human_rules/` | 90% |
| `training/` | 75% |
| `llm/` | 70% |
| `notifications/` | 70% |
| **Overall** | **75%** |

## Test Data

- Sample Cricsheet JSON files: `tests/fixtures/matches/` (10 files covering T20, ODI, IPL, BBL)
- Player fixtures: `tests/fixtures/players.json`
- Feature vector fixtures: `tests/fixtures/features.json`
- All fixtures must use realistic data (real match IDs from Cricsheet; no fake names)
