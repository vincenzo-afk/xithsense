# Assumptions and Constraints

---

## PART 1 — SYSTEM ASSUMPTIONS

### Data Assumptions

| ID | Assumption | Evidence | Risk Level | Mitigation |
|----|-----------|---------|-----------|-----------|
| DA-01 | Cricsheet data is accurate for ball-by-ball records | Cross-checked 100 matches vs ESPNcricinfo | Low | Spot-check 10 random matches per month |
| DA-02 | Cricsheet v1.2.0 format remains stable | No breaking changes since 2022 | Low | Schema validation on every ingestion; monitor Cricsheet changelog |
| DA-03 | Historical ball-by-ball data (2010–2024) is representative of modern T20 cricket | Feature importance validates recency; recent form outweighs old history | Medium | Rolling features weight recent form more heavily (window 3 > window 10) |
| DA-04 | Player roles (BAT/BOWL/AR/WK) are stable within a season | Occasional mid-season role changes observed | Medium | Human rules capture known role changes; admin can override |
| DA-05 | 22,062 historical matches provide sufficient training signal | Val MAE 11.94 confirms learning | Low | If new format added with < 200 matches, use T20 model as proxy |
| DA-06 | Weather data from OpenWeatherMap is accurate enough for pitch impact estimation | API accuracy ±2°C temperature, ±10% humidity | Medium | Used as soft signal only; venue historical patterns dominate |
| DA-07 | Cricsheet new match data lags by 24–48 hours after match completion | Observed delay in Cricsheet updates | Medium | Incremental ingestion daily; live predictions not dependent on latest match |

---

### Model Assumptions

| ID | Assumption | Validated By | Risk Level |
|----|-----------|-------------|-----------|
| MA-01 | Gradient-boosted trees outperform simpler baselines for this tabular task | EXP-001: ensemble val MAE 11.94 vs linear regression ~18.2 | Low |
| MA-02 | Ensemble of 3 models (XGB+LGB+CAT) improves over best single model | EXP-001: +1.2pp CPR vs LightGBM alone | Low |
| MA-03 | Short rolling windows (3, 5 matches) predict better than career stats | Feature importance: fp_avg_5 ranks #2 globally | Low |
| MA-04 | Dream11 fantasy points can be accurately computed from Cricsheet raw data | Verified on 10 known matches; all within 0.5 pts | Low |
| MA-05 | One T20 model covering IPL, BBL, PSL, CPL, IT20 is sufficient | IPL-specific backtest within 1 MAE pt of global T20 | Medium |
| MA-06 | Captain accuracy of 40%+ is achievable with structured tabular features | EXP-001 achieves 40.1% on 2025 held-out data | Low |

---

### Infrastructure Assumptions

| ID | Assumption | Risk Level | Mitigation |
|----|-----------|-----------|-----------|
| IA-01 | Supabase PostgreSQL SLA 99.9% sufficient | Low | Redis cache serves during outages |
| IA-02 | Single Redis instance sufficient for MVP | Low | Upgrade to cluster at 10k DAU |
| IA-03 | PuLP CBC solver finds feasible Dream11 team in < 10 seconds for valid inputs | Low | DEAP fallback for edge cases |
| IA-04 | Anthropic Claude API latency < 5 seconds per explanation | Medium | Caching reduces 80% of calls; fallback templates available |
| IA-05 | Railway/Render can handle IPL toss spike (300 concurrent users) | Medium | Pre-scale before peak; load test confirmed p95 < 2s at 300 concurrent |

---

## PART 2 — SYSTEM CONSTRAINTS

### Technical Constraints

| ID | Constraint | Value | Reason |
|----|-----------|-------|--------|
| TC-01 | Maximum team size | 11 players | Dream11 rule |
| TC-02 | Total credit budget | 100.0 credits | Dream11 rule |
| TC-03 | Maximum players from one real team | 7 | Dream11 rule |
| TC-04 | Wicketkeeper slots | Min 1, Max 4 | Dream11 rule |
| TC-05 | Batter slots | Min 3, Max 6 | Dream11 rule |
| TC-06 | All-rounder slots | Min 1, Max 4 | Dream11 rule |
| TC-07 | Bowler slots | Min 3, Max 6 | Dream11 rule |
| TC-08 | Feature vector size | 47 dimensions | Fixed by FEATURE_LIST.yaml v1.2 |
| TC-09 | LP solver timeout | 10 seconds | Response time SLA |
| TC-10 | LLM max output tokens | 200 per explanation | Cost and response time |
| TC-11 | Redis max memory | 512 MB (MVP) | Railway starter plan |
| TC-12 | API request body size limit | 1 MB | DoS prevention |
| TC-13 | API request timeout | 30 seconds | Uvicorn default |
| TC-14 | WebSocket ping interval | 30 seconds | Connection health |
| TC-15 | Chat message max length | 500 characters | Token budget |
| TC-16 | Max concurrent WebSocket connections per user | 5 | Resource fairness |

---

### Business Constraints

| ID | Constraint | Value | Reason |
|----|-----------|-------|--------|
| BC-01 | Free tier teams per match | 1 (Safe mode only) | Conversion incentive |
| BC-02 | Free tier AI chat messages | 0 | Premium differentiation |
| BC-03 | Premium tier teams per match | 20 | Technical feasibility |
| BC-04 | Free plan rate limit | 30 RPM | Infrastructure cost |
| BC-05 | Premium plan rate limit | 300 RPM | Infrastructure cost |
| BC-06 | Minimum subscription price | ₹299/month | Market positioning |
| BC-07 | Refund window (Annual plan) | 7 days, no predictions accessed | Policy |
| BC-08 | Data residency | India (ap-south-1) | DPDP Act compliance |
| BC-09 | No automated contest entry | Prohibited | Dream11 ToS |
| BC-10 | No real-money gambling facilitation | Prohibited | Legal requirement |
| BC-11 | User PII retention | Max account duration + 30 days | DPDP Act |
| BC-12 | Payment records retention | 7 years | GST compliance |

---

### ML Constraints

| ID | Constraint | Value | Reason |
|----|-----------|-------|--------|
| MC-01 | Training data time split | Train ends 2024-12-31; Val starts 2025-01-01 | No data leakage |
| MC-02 | Minimum matches for rolling features | 1 (flag low_data if < 3) | Feature completeness |
| MC-03 | Minimum balls for matchup stats | 30 | Statistical significance |
| MC-04 | Maximum model age before forced retrain | 90 days | Model freshness |
| MC-05 | Minimum captain accuracy for production | 35% | Quality floor |
| MC-06 | Feature vector dimension | Exactly 47 | Model compatibility |
| MC-07 | Prediction range | [-10, 500] fantasy points | Valid Dream11 range |
| MC-08 | Confidence score range | [1, 100] | User communication |
| MC-09 | Ensemble weight sum | Must equal 1.0 | Mathematical validity |

---

### Operational Constraints

| ID | Constraint | Value | Reason |
|----|-----------|-------|--------|
| OC-01 | API uptime target | ≥ 99.5% during match windows | SLA |
| OC-02 | Prediction response time | < 3 seconds (4-mode portfolio) | UX requirement |
| OC-03 | Notification delivery time | < 2 minutes for toss events | User value |
| OC-04 | Ingestion pipeline frequency | Daily at 2 AM IST | Data freshness |
| OC-05 | Model retraining minimum frequency | Monthly | Accuracy maintenance |
| OC-06 | Audit log retention | Permanent | Compliance |
| OC-07 | Prediction cache TTL | 30–60 minutes | Freshness vs cost |
| OC-08 | Feature cache TTL | 6 hours | Freshness vs cost |
| OC-09 | Backtest minimum before promotion | 2,000 matches | Statistical confidence |
| OC-10 | Test coverage minimum | 75% overall | Code quality |

---

## PART 3 — OUT-OF-SCOPE CONSTRAINTS

The following are explicitly out of scope and must not be implemented:

| What | Why Out of Scope |
|------|-----------------|
| Automated contest entry on Dream11 | Violates Dream11 Terms of Service |
| Recommendations for non-cricket sports | Focus and expertise |
| Real-money gambling facilitation | Legal requirement (India) |
| Accessing user Dream11 accounts | Privacy and ToS |
| Sharing user prediction data with third parties | DPDP Act |
| Predictions without explainability | Core product principle |
| Generating teams without Dream11 constraint validation | Integrity requirement |
| Production deployments without CI passing | Code quality rule |
| Database schema changes without Alembic migration | Data integrity rule |
