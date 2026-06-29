# Product Requirements Document (PRD)

**Project:** XithSense  
**Version:** 1.0  
**Status:** Active  
**Last Updated:** 2026-06-24  

---

## 1. Overview

XithSense is an AI-powered fantasy cricket intelligence platform. It ingests ball-by-ball match data, applies machine learning and human-encoded rules, and produces explainable team recommendations for Dream11-style contests.

---

## 2. Functional Requirements

### FR-01: Data Ingestion

| ID | Requirement |
|----|------------|
| FR-01-01 | System SHALL ingest all Cricsheet JSON v1.2.0 files (22,062 matches) from a local zip or directory |
| FR-01-02 | System SHALL parse all delivery fields: batter, bowler, non_striker, runs, wickets, extras, reviews, powerplays |
| FR-01-03 | System SHALL store match metadata: teams, venue, toss, outcome, season, event, player_of_match, gender, team_type |
| FR-01-04 | System SHALL support incremental ingestion (new matches only) without re-processing existing records |
| FR-01-05 | System SHALL validate each JSON file against the Cricsheet v1.2.0 schema before inserting |
| FR-01-06 | System SHALL log ingestion errors per file and continue processing remaining files |
| FR-01-07 | System SHALL support the following match types: T20, ODI, Test, IT20, IPL, BBL, PSL, CPL, WPL, NTB, CCH, WOD, MDM |
| FR-01-08 | System SHALL handle duplicate match IDs by updating (upsert) existing records |

### FR-02: Feature Engineering

| ID | Requirement |
|----|------------|
| FR-02-01 | System SHALL compute rolling batting features for windows of last 3, 5, and 10 matches |
| FR-02-02 | System SHALL compute rolling bowling features for windows of last 3, 5, and 10 matches |
| FR-02-03 | System SHALL compute venue-specific batting and bowling averages per player |
| FR-02-04 | System SHALL compute batter-vs-bowler-type matchup stats (spin, pace, left-arm pace, left-arm spin) |
| FR-02-05 | System SHALL compute powerplay, middle-overs, and death-overs splits for all players |
| FR-02-06 | System SHALL compute chasing vs. setting performance splits per player |
| FR-02-07 | System SHALL compute fantasy points ceiling, floor, consistency, and average per rolling window |
| FR-02-08 | System SHALL recompute features incrementally when new match data is ingested |
| FR-02-09 | System SHALL cache all computed features in Redis with a 6-hour TTL |
| FR-02-10 | System SHALL store all features in the `rolling_features` and `venue_stats` tables |

### FR-03: Human Intelligence Rules Engine

| ID | Requirement |
|----|------------|
| FR-03-01 | System SHALL load rules from JSON files in `human_rules/` at startup |
| FR-03-02 | Each rule SHALL contain: player (or wildcard), condition, impact_score (-100 to +100), confidence (0.0–1.0), source |
| FR-03-03 | System SHALL evaluate all applicable rules for each player before generating predictions |
| FR-03-04 | System SHALL apply rules as additive adjustments to the ML base score |
| FR-03-05 | System SHALL log which rules fired for each player and match (rule_triggers table) |
| FR-03-06 | Rules SHALL support conditions on: match_type, venue, toss_decision, pitch_type, opposition_bowling_type, batting_position |
| FR-03-07 | System SHALL support rule confidence weighting: impact = impact_score × confidence |
| FR-03-08 | Admin SHALL be able to add, edit, deactivate, and delete rules via the admin API |

### FR-04: Prediction Models

| ID | Requirement |
|----|------------|
| FR-04-01 | System SHALL train separate models for batting (runs, balls, boundaries) and bowling (wickets, economy, maidens) |
| FR-04-02 | System SHALL train a direct fantasy-points model as the primary prediction target |
| FR-04-03 | System SHALL train models for each major format: T20, ODI, Test |
| FR-04-04 | System SHALL support XGBoost, LightGBM, and CatBoost as model backends |
| FR-04-05 | Every prediction SHALL include a confidence score (0–100) |
| FR-04-06 | System SHALL predict fantasy ceiling (90th percentile) and floor (10th percentile) per player |
| FR-04-07 | System SHALL version and store all trained model artifacts in `models/artifacts/` |
| FR-04-08 | System SHALL expose model performance metrics (MAE, RMSE, accuracy) via the admin API |

### FR-05: Ensemble Engine

| ID | Requirement |
|----|------------|
| FR-05-01 | Final player score SHALL combine: ML (40%), Human Rules (30%), Recent Form (20%), Live Context (10%) |
| FR-05-02 | Weights SHALL be configurable via environment variables without code changes |
| FR-05-03 | System SHALL produce a final ranked player list for every match within 3 seconds |
| FR-05-04 | Live context weight SHALL only apply when live match data is available |
| FR-05-05 | System SHALL store the ensemble breakdown per player per prediction for audit purposes |

### FR-06: Team Optimizer

| ID | Requirement |
|----|------------|
| FR-06-01 | System SHALL generate 4 team variants: Safe, Grand League, Aggressive, Small League |
| FR-06-02 | Every generated team SHALL satisfy Dream11 constraints (see BUSINESS_RULES.md) |
| FR-06-03 | System SHALL use Linear Programming (PuLP) as the primary optimizer |
| FR-06-04 | System SHALL fall back to Genetic Algorithm (DEAP) when LP produces no feasible solution |
| FR-06-05 | Grand League teams SHALL prioritise players with ownership < 20% and high ceiling scores |
| FR-06-06 | System SHALL generate up to 20 unique team combinations per request on Premium plan |
| FR-06-07 | Each team SHALL include 11 players: WK, BAT, AR, BOWL within Dream11 role limits |
| FR-06-08 | System SHALL respect the 100-credit budget constraint with exact precision |

### FR-07: Captain Engine

| ID | Requirement |
|----|------------|
| FR-07-01 | System SHALL recommend Best Captain, Best Vice-Captain, Safe Captain, and Risk Captain |
| FR-07-02 | Captain recommendations SHALL be based on: ceiling score, consistency, explosiveness, opposition weakness |
| FR-07-03 | Each captain recommendation SHALL include a confidence percentage |
| FR-07-04 | System SHALL differentiate captain recommendations by team mode (Safe vs GL) |

### FR-08: Explainability Engine

| ID | Requirement |
|----|------------|
| FR-08-01 | Every recommended player SHALL have a plain-English explanation generated by LLM |
| FR-08-02 | Explanations SHALL include: recent form summary, venue average, matchup assessment, confidence level |
| FR-08-03 | System SHALL support Anthropic Claude, OpenAI GPT, and Google Gemini as LLM backends |
| FR-08-04 | LLM backend SHALL be switchable via `LLM_PROVIDER` environment variable without code changes |
| FR-08-05 | Explanations SHALL be cached (Redis, 1-hour TTL) to avoid redundant LLM calls |
| FR-08-06 | System SHALL generate explanations in under 5 seconds per player |

### FR-09: AI Chat Assistant

| ID | Requirement |
|----|------------|
| FR-09-01 | System SHALL expose a chat endpoint: `POST /api/v1/chat` |
| FR-09-02 | Chat assistant SHALL answer questions about: player picks, captain selection, differential picks, match context |
| FR-09-03 | Chat assistant SHALL have access to current match prediction data and player feature store |
| FR-09-04 | Chat history SHALL be stored per user session |
| FR-09-05 | Free users SHALL be limited to 5 chat messages per match; Premium users unlimited |

### FR-10: Live Match Intelligence

| ID | Requirement |
|----|------------|
| FR-10-01 | System SHALL provide a WebSocket endpoint for live match updates |
| FR-10-02 | Live feed SHALL push: win probability, per-player live fantasy points, captain success rate |
| FR-10-03 | System SHALL update live predictions after each over if live score data is available |
| FR-10-04 | Live context weight SHALL increase from 10% to 25% once the match is live |

### FR-11: User Management

| ID | Requirement |
|----|------------|
| FR-11-01 | System SHALL support user registration via email and Google OAuth |
| FR-11-02 | System SHALL implement JWT-based authentication with 24-hour token expiry |
| FR-11-03 | Free users SHALL be limited to: 1 team per match, basic insights, no AI chat |
| FR-11-04 | Premium users SHALL have: unlimited teams, AI chat, detailed insights, live alerts, GL teams |
| FR-11-05 | System SHALL track usage quotas per user per match per day |

### FR-12: Notifications

| ID | Requirement |
|----|------------|
| FR-12-01 | System SHALL send alerts for: Playing XI announced, Toss completed, Last-minute injury, Team changes |
| FR-12-02 | Supported channels: Telegram, WhatsApp, Push notifications, Email |
| FR-12-03 | Users SHALL be able to configure which events trigger notifications |
| FR-12-04 | Notifications SHALL be delivered within 2 minutes of the triggering event |

### FR-13: Backtesting System

| ID | Requirement |
|----|------------|
| FR-13-01 | System SHALL replay predictions against any historical date range |
| FR-13-02 | Backtest metrics SHALL include: correct-player rate, captain accuracy, avg fantasy points error, simulated ROI |
| FR-13-03 | System SHALL support filtering backtests by match format, venue, season |
| FR-13-04 | Backtest results SHALL be stored in the `backtest_runs` and `backtest_results` tables |
| FR-13-05 | Admin SHALL be able to trigger a backtest run via the admin API |

### FR-14: Admin Dashboard

| ID | Requirement |
|----|------------|
| FR-14-01 | Admin SHALL be able to view: prediction accuracy metrics, user counts, subscription revenue, system health |
| FR-14-02 | Admin SHALL be able to retrain models, trigger data ingestion, push notifications |
| FR-14-03 | Admin SHALL be able to manage human rules (add, edit, deactivate) |
| FR-14-04 | Admin panel SHALL require a separate admin JWT with role=admin |

### FR-15: Payments

| ID | Requirement |
|----|------------|
| FR-15-01 | System SHALL integrate Razorpay for INR subscription billing |
| FR-15-02 | Plans: Free (₹0), Premium Monthly (₹299), Premium Annual (₹2,499) |
| FR-15-03 | System SHALL handle: new subscription, renewal, cancellation, refund webhooks |
| FR-15-04 | Premium status SHALL activate within 60 seconds of successful payment |

---

## 3. Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|------------|
| NFR-01 | Performance | Full team generation (4 modes) in < 3 seconds on standard hardware |
| NFR-02 | Performance | API p95 response time < 500ms for prediction endpoints |
| NFR-03 | Scalability | API SHALL handle 1,000 concurrent users during peak match windows |
| NFR-04 | Reliability | API uptime ≥ 99.5% during active match windows (6 AM – midnight IST) |
| NFR-05 | Security | All API endpoints require authentication except `/health` and `/api/v1/auth/*` |
| NFR-06 | Security | No sensitive data (API keys, passwords) in version control |
| NFR-07 | Security | All user passwords hashed with bcrypt (cost factor ≥ 12) |
| NFR-08 | Security | Rate limiting enforced: Free 30 RPM, Premium 300 RPM, Admin 1000 RPM |
| NFR-09 | Data Integrity | No duplicate deliveries in the `deliveries` table |
| NFR-10 | Maintainability | Test coverage ≥ 75% across all modules |
| NFR-11 | Observability | All prediction requests logged with input features and output scores |
| NFR-12 | Portability | Full system deployable via `docker compose up` in a single command |
