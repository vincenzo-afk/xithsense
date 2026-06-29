# Performance Tests

**Tool:** k6 (https://k6.io)  
**Location:** `tests/performance/`  
**Run before:** every major release, monthly in staging

---

## Scenarios

### Scenario 1: Sustained Load (Baseline)

```javascript
// tests/performance/sustained_load.js
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "1m", target: 50 },   // ramp up
    { duration: "5m", target: 50 },   // sustain
    { duration: "1m", target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_duration: ["p95<500"],
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  const res = http.post(
    "https://staging-api.xithsense.com/api/v1/predict/team",
    JSON.stringify({ match_id: "1535465", mode: "safe", count: 1 }),
    { headers: { "Content-Type": "application/json", Authorization: `Bearer ${__ENV.TEST_JWT}` } }
  );
  check(res, { "status is 200": (r) => r.status === 200 });
  sleep(1);
}
```

**Pass criteria:** p95 < 500ms, error rate < 1%

---

### Scenario 2: IPL Toss Spike

Simulates the 5-minute burst after toss is announced.

```javascript
export const options = {
  stages: [
    { duration: "10s", target: 200 },  // instant spike
    { duration: "2m", target: 200 },   // 2 min at peak
    { duration: "30s", target: 0 },    // drop off
  ],
  thresholds: {
    http_req_duration: ["p95<2000"],
    http_req_failed: ["rate<0.05"],
  },
};
```

**Pass criteria:** p95 < 2000ms, error rate < 5% during spike

---

### Scenario 3: Mixed Traffic

Mix of prediction, player lookup, and chat requests (realistic distribution).

```javascript
// 60% predictions, 30% player lookups, 10% chat
export default function () {
  const roll = Math.random();
  if (roll < 0.60) {
    http.post(`${BASE_URL}/api/v1/predict/team`, ...);
  } else if (roll < 0.90) {
    http.get(`${BASE_URL}/api/v1/players/${PLAYER_IDS[Math.floor(Math.random()*10)]}`);
  } else {
    http.post(`${BASE_URL}/api/v1/chat`, ...);
  }
  sleep(Math.random() * 2);
}
```

---

## Database Performance Tests

```sql
-- Test: Feature lookup by player + match_type + date (must use index)
EXPLAIN ANALYZE
SELECT * FROM rolling_feature
WHERE player_id = 'uuid' AND match_type = 'T20' AND as_of_date = '2026-06-24'
AND window_matches = 5;
-- Expected: Index Scan on idx_rf_player_type, < 10ms

-- Test: Delivery count query (must use index)
EXPLAIN ANALYZE
SELECT COUNT(*) FROM delivery WHERE match_id = '1535465';
-- Expected: Index Scan on idx_delivery_match, < 5ms
```

## Running Performance Tests

```bash
# Install k6
brew install k6   # macOS
# or: sudo apt install k6  (Ubuntu)

# Run sustained load test against staging
k6 run tests/performance/sustained_load.js \
  -e TEST_JWT=$(python scripts/generate_test_jwt.py) \
  -e BASE_URL=https://staging-api.xithsense.com

# Run spike test
k6 run tests/performance/spike_test.js ...

# Generate HTML report
k6 run --out csv=results.csv tests/performance/sustained_load.js
```

## Benchmark History

| Date | Scenario | p95 Latency | Error Rate | Result |
|------|---------|-------------|------------|--------|
| 2026-06-01 | Baseline | 342ms | 0.2% | PASS |
| — | — | — | — | — |
