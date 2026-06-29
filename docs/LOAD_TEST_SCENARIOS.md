# Load Test Scenarios

**Tool:** k6 (https://k6.io)  
**Environment:** Always test against staging, never production  
**Schedule:** Before every major release + monthly

---

## Scenario 1: Baseline API Health

**Goal:** Confirm API handles 50 concurrent users at steady state

```javascript
// tests/performance/baseline.js
export const options = {
  stages: [
    { duration: "30s", target: 10 },
    { duration: "3m",  target: 50 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p50<150", "p95<400", "p99<800"],
    http_req_failed:   ["rate<0.005"],
  },
};

export default function () {
  // Mix: 60% predict, 30% player lookup, 10% match list
  const roll = Math.random();
  if (roll < 0.60) {
    http.post(`${BASE_URL}/api/v1/predict/team`,
      JSON.stringify({ match_id: MATCH_ID, mode: "safe", count: 1 }),
      { headers: HEADERS });
  } else if (roll < 0.90) {
    http.get(`${BASE_URL}/api/v1/players/${randomPlayer()}`, { headers: HEADERS });
  } else {
    http.get(`${BASE_URL}/api/v1/matches/upcoming`, { headers: HEADERS });
  }
  sleep(1 + Math.random());
}
```

**Pass criteria:** p95 < 400ms, error rate < 0.5%

---

## Scenario 2: IPL Toss Spike

**Goal:** Verify system survives the burst of prediction requests after toss

```javascript
export const options = {
  stages: [
    { duration: "10s", target: 300 },   // instant spike
    { duration: "3m",  target: 300 },   // sustain peak
    { duration: "30s", target: 50  },   // settle
    { duration: "2m",  target: 50  },   // steady state
  ],
  thresholds: {
    http_req_duration: ["p95<2000"],
    http_req_failed:   ["rate<0.03"],
  },
};
```

**Pass criteria:** p95 < 2000ms during spike, error rate < 3%

---

## Scenario 3: Portfolio Generation (Premium Load)

**Goal:** Test 4-mode portfolio generation under concurrent Premium users

```javascript
export const options = {
  vus: 50,
  duration: "5m",
  thresholds: {
    http_req_duration: ["p95<3500"],
    http_req_failed:   ["rate<0.01"],
  },
};

export default function () {
  http.post(`${BASE_URL}/api/v1/predict/team/portfolio`,
    JSON.stringify({ match_id: MATCH_ID }),
    { headers: PREMIUM_HEADERS });
  sleep(3 + Math.random() * 2);
}
```

**Pass criteria:** p95 < 3500ms (portfolio is heavier than single team), error rate < 1%

---

## Scenario 4: WebSocket Concurrent Connections

**Goal:** Verify 500 simultaneous WebSocket connections during a live match

```javascript
// Uses k6 websockets extension
export default function () {
  const ws = new WebSocket(`wss://${HOST}/api/v1/live/${MATCH_ID}?token=${JWT}`);
  ws.onmessage = (msg) => { /* validate msg structure */ };
  ws.onclose = () => check(ws, { "closed normally": (ws) => ws.readyState === 3 });
  sleep(300);  // hold connection for 5 minutes
}
```

**Pass criteria:** All 500 connections maintained for 5 minutes, < 1% dropped

---

## Scenario 5: Database Stress

**Goal:** Test feature loading under sustained load (cache bypassed)

```javascript
export const options = {
  vus: 100, duration: "5m",
  env: { BYPASS_CACHE: "true" },  // Custom header signals cache bypass
};
```

**Pass criteria:** No DB connection pool exhaustion (< 80% pool utilisation), p95 < 1000ms

---

## Load Test Execution

```bash
# Set up test user JWT
export TEST_JWT=$(python scripts/generate_test_jwt.py --role premium)
export BASE_URL=https://staging-api.xithsense.com
export MATCH_ID=1535465

# Run baseline
k6 run tests/performance/baseline.js \
  -e TEST_JWT=$TEST_JWT -e BASE_URL=$BASE_URL -e MATCH_ID=$MATCH_ID

# Run with HTML report
k6 run --out csv=tests/performance/results/$(date +%Y%m%d)_baseline.csv \
  tests/performance/baseline.js ...

# Run full suite
for scenario in baseline toss_spike portfolio_load; do
  k6 run tests/performance/${scenario}.js ...
done
```

---

## Acceptance Criteria for Release

All 4 scenarios must pass their thresholds before a production release is approved.

| Scenario | Status |
|----------|--------|
| Baseline | 🔲 |
| Toss Spike | 🔲 |
| Portfolio | 🔲 |
| WebSocket | 🔲 |
