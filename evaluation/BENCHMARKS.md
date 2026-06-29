# Performance Benchmarks

## Prediction Quality Benchmarks (T20 / IPL)

These are the minimum acceptable targets. Falling below these triggers a model review.

| Metric | Minimum (floor) | Target | Excellent |
|--------|----------------|--------|-----------|
| Captain Accuracy | 35% | 40% | 47%+ |
| Correct Player Rate (≥7/11) | 55% | 62% | 70%+ |
| Top-3 Captain Rate | 62% | 72% | 80%+ |
| Fantasy Points MAE | < 18 pts | < 14 pts | < 10 pts |
| Rank Correlation (ρ) | > 0.55 | > 0.65 | > 0.75 |

## API Performance Benchmarks

| Endpoint | p50 Target | p95 Target | p99 Target |
|----------|-----------|-----------|-----------|
| `POST /predict/team` (1 team) | < 200ms | < 500ms | < 1000ms |
| `POST /predict/team/portfolio` | < 800ms | < 2000ms | < 3000ms |
| `POST /chat` | < 1500ms | < 4000ms | < 8000ms |
| `GET /players/:id` | < 50ms | < 150ms | < 300ms |
| `GET /matches/upcoming` | < 30ms | < 100ms | < 200ms |

## Ingestion Benchmarks

| Task | Target | Measured on |
|------|--------|-------------|
| Full ingest (22,062 files) | < 30 min | 4-core CPU |
| Incremental ingest (50 files) | < 60 sec | Standard hardware |
| Feature rebuild (all players) | < 15 min | 4-core CPU |
| Model training (T20, 3 models) | < 90 min | 8-core CPU |
| Backtest (10,000 matches) | < 20 min | 4-core CPU |

## Load Benchmarks

Tested with k6 load testing tool:

| Scenario | Target |
|----------|--------|
| 100 concurrent users, sustained 10 min | Zero 5xx errors |
| 500 concurrent users, 1 min spike | < 2% error rate |
| 1000 concurrent users, 1 min peak | < 5% error rate |
| Sustained 50 RPS for 30 min | p95 < 500ms, zero OOM |
