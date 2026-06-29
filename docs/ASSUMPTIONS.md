# Assumptions

All decisions in XithSense rest on these assumptions. If any assumption proves false, the affected components must be revisited.

---

## Data Assumptions

| ID | Assumption | Risk if Wrong | Verification |
|----|-----------|--------------|-------------|
| DA-01 | Cricsheet data is accurate and complete for all listed matches | Prediction quality degrades; model trains on wrong labels | Spot-check 100 random matches against ESPNcricinfo scorecard |
| DA-02 | Cricsheet v1.2.0 format is stable and won't change without notice | Parser breaks on schema changes | Monitor Cricsheet release notes; validate schema on every ingestion |
| DA-03 | Historical ball-by-ball patterns predict future player performance | ML models underperform; accuracy below target | Monthly backtesting validates this assumption |
| DA-04 | Player roles (BAT/BOWL/AR/WK) are stable per player | Optimizer generates invalid teams | Admin can override role per player; human rules capture role changes |
| DA-05 | Venue names in Cricsheet are consistent enough to map to canonical venues | Feature computation errors | Venue alias mapping table; manual review on ingestion errors |
| DA-06 | 22,062 matches provide sufficient training signal for T20/IPL | MAE > 14 pts; poor rank correlation | Train/val split shows clear learning; if not, augment with synthetic data |

---

## Model Assumptions

| ID | Assumption | Risk if Wrong | Mitigation |
|----|-----------|--------------|-----------|
| MA-01 | Gradient-boosted trees outperform neural networks for this tabular task | Accuracy below neural baseline | Benchmark against MLP/TabNet quarterly |
| MA-02 | Ensemble of 3 GBT models improves over any single model | Ensemble adds overhead with no benefit | Ablation study confirms ensemble > best single model by >0.5% |
| MA-03 | Feature importance is stable across seasons | Key features lose signal; accuracy drops | Re-evaluate feature importance after each annual training run |
| MA-04 | Recency (short windows) matters more than career stats | Long-window features should dominate | Feature importance shows fp_avg_3 and fp_avg_5 as top features |
| MA-05 | A single model per format (T20, ODI, Test) is sufficient | Different sub-formats (IPL vs IT20) need separate models | Evaluate IPL vs generic T20 accuracy separately; split if >3pp diff |

---

## Business Assumptions

| ID | Assumption | Risk if Wrong | Mitigation |
|----|-----------|--------------|-----------|
| BA-01 | ₹299/month is an acceptable price for Premium | Low conversion rate | A/B test pricing at ₹199 and ₹399 |
| BA-02 | Telegram is the primary notification channel for Indian fantasy players | Low notification engagement | Add WhatsApp in Phase 2 |
| BA-03 | Dream11 remains the dominant fantasy platform in India | Platform pivot needed | Platform-agnostic scoring formula; parameterise per platform |
| BA-04 | Captain accuracy >40% is sufficient for word-of-mouth growth | Slow user acquisition | Track NPS; if <50, investigate what users care most about |
| BA-05 | Indian cricket fans are willing to pay for analytical edge | Revenue targets missed | Freemium model retains free users; upgrade prompts on key moments |

---

## Technical Assumptions

| ID | Assumption | Risk if Wrong | Mitigation |
|----|-----------|--------------|-----------|
| TA-01 | Supabase PostgreSQL is stable enough for production | Database outages; data loss | Supabase SLA 99.9%; daily backups; read replica for heavy queries |
| TA-02 | Redis can handle feature cache at peak load | Cache evictions; slow predictions | Monitor memory; scale to Redis Cluster at >10k DAU |
| TA-03 | PuLP CBC solver finds feasible Dream11 team in <10 seconds | Slow predictions; LP fallback needed | DEAP fallback proven; <2% infeasibility in testing |
| TA-04 | LLM API costs are manageable at scale | Cost overrun | Cache explanations aggressively; set token limits per request |
| TA-05 | Railway/Render auto-scaling handles IPL match traffic spikes | API failures at peak | Pre-warm cache; manually scale before peak windows |

---

## Domain Assumptions

| ID | Assumption |
|----|-----------|
| DOA-01 | Fantasy cricket is a skill game (not gambling) under Indian law — unchanged from current legal status |
| DOA-02 | Cricsheet continues to be maintained and updated by the community |
| DOA-03 | Dream11 does not change its scoring system without announcement |
| DOA-04 | Player injury information is available via public channels (news, Twitter) within 30 minutes of announcement |
| DOA-05 | Toss advantage is a statistically significant predictor in T20 cricket at dew-prone venues |
