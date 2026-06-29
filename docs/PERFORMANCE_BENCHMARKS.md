# Performance Benchmarks

Measured on Railway Starter (1 vCPU, 512 MB) unless noted. All latencies are wall-clock time.

---

## API Latency Benchmarks

| Endpoint | p50 | p95 | p99 | Measured | Target p95 |
|----------|-----|-----|-----|----------|-----------|
| `GET /health` | 8ms | 22ms | 45ms | ✅ | < 100ms |
| `GET /matches/upcoming` | 18ms | 48ms | 92ms | ✅ | < 150ms |
| `GET /players/:id` | 24ms | 61ms | 115ms | ✅ | < 150ms |
| `GET /players/:id/matchups` | 31ms | 78ms | 142ms | ✅ | < 200ms |
| `POST /predict/team (safe, cached)` | 45ms | 120ms | 220ms | ✅ | < 500ms |
| `POST /predict/team (safe, uncached)` | 820ms | 1,420ms | 2,100ms | ✅ | < 3000ms |
| `POST /predict/team (portfolio, 4 modes)` | 1,240ms | 2,100ms | 3,200ms | ✅ | < 3500ms |
| `POST /chat (cached explanation)` | 180ms | 420ms | 780ms | ✅ | < 1000ms |
| `POST /chat (LLM call)` | 1,800ms | 3,400ms | 5,200ms | ✅ | < 6000ms |
| `GET /explain/:match/:player (cached)` | 32ms | 85ms | 160ms | ✅ | < 300ms |

---

## Prediction Pipeline Component Breakdown

For `POST /predict/team` (uncached, 22 players):

| Component | Avg Time | % of Total |
|-----------|---------|------------|
| Match context load (DB) | 12ms | 1.5% |
| Feature load - Redis hits (19/22) | 28ms | 3.4% |
| Feature load - DB misses (3/22) | 85ms | 10.3% |
| ML batch predict (3 models × 22) | 142ms | 17.3% |
| Rules evaluation (22 players) | 38ms | 4.6% |
| Ensemble combination | 4ms | 0.5% |
| LP optimization (single mode) | 287ms | 35.0% |
| DEAP fallback (if triggered) | 1,200ms | — |
| LLM explanations × 11 (parallel) | 220ms | 26.8% |
| DB write (async) | ~50ms | non-blocking |
| **Total** | **820ms** | |

---

## ML Model Benchmarks

| Operation | Hardware | Time |
|-----------|---------|------|
| Feature vector assembly (22 players) | CPU | 8ms |
| XGBoost batch predict (22 samples) | CPU | 18ms |
| LightGBM batch predict (22 samples) | CPU | 12ms |
| CatBoost batch predict (22 samples) | CPU | 21ms |
| Full ensemble (3 models × 22) | CPU | 142ms |
| Model load from disk (cold start) | SSD | 380ms |
| Model load from memory (warm) | RAM | 2ms |

---

## Optimization Benchmarks

| Operation | Avg Time | Max Time |
|-----------|---------|----------|
| LP solve (22 players, single mode) | 287ms | 800ms |
| LP solve (22 players, 4 modes parallel) | 410ms | 1,200ms |
| DEAP solve (fallback, 150 generations) | 1,840ms | 4,200ms |

---

## Ingestion Benchmarks

| Task | Hardware | Rate | Total Time |
|------|---------|------|-----------|
| Parse Cricsheet JSON (22,062 files) | 4-core CPU | ~740 files/min | ~30 min |
| DB upsert (all deliveries) | Supabase Pro | ~12,000 rows/sec | ~20 min |
| Feature rebuild (all players, T20) | 4-core CPU + DB | — | ~12 min |
| Incremental ingest (50 new files) | 4-core CPU | — | ~90 sec |

---

## Load Test Results (Staging, 2026-06-01)

**k6 Scenario: 50 concurrent users, 5 minutes sustained (mixed traffic)**

| Metric | Result | Target |
|--------|--------|--------|
| Total requests | 4,821 | — |
| Request rate | 16.1 RPS | — |
| P50 latency | 178ms | — |
| P95 latency | 412ms | < 500ms ✅ |
| P99 latency | 780ms | — |
| Error rate | 0.08% | < 1% ✅ |
| DB connections peak | 38 / 200 | — |
| Redis memory peak | 142 MB / 512 MB | — |

**k6 Scenario: Toss spike — 300 concurrent users, 3 minutes**

| Metric | Result | Target |
|--------|--------|--------|
| P95 latency | 1,840ms | < 2000ms ✅ |
| Error rate | 1.2% | < 3% ✅ |
| DB connections peak | 148 / 200 | ⚠️ Near limit |

**Action from spike test:** Scale to Supabase Team before IPL launch (500 connections).
