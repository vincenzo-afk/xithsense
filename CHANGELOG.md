# Changelog

All notable changes to XithSense are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Telegram / WhatsApp notification delivery
- Official-squad auto-refresh for every tracked fixture (currently only when a side has no history)

---

## [1.0.0] - 2026-10-21

### Added
- Full Cricsheet ingestion (23k+ matches, 11.7M deliveries) with registry-id player identity and canonical Dream11 scoring
- Leakage-free feature store: rolling form, P90/P10 ceiling & floor, venue, pace/spin matchups, context; inferred bowling styles and venue character
- Per-format ensembles (T20 / ODI / Test): XGBoost + LightGBM + CatBoost with quantile ceiling/floor models, model registry, backtesting harness
- Integer-LP team optimizer with captain/vice-captain variables, multi-team diversity and Grand League ownership constraint; captain engine
- Live data from CricketData: fixture sync, probable squads from real line-ups, role-relative credit pricing, quota-guarded client, live WebSocket feed with scorecard fantasy points
- Cricket-only AI assistant: tool-calling agent (Groq / Anthropic / OpenAI / Gemini) with projection, team-building, captaincy, differential, profile, web-search and page-fetch tools; grounded fallback engine
- React SPA: match centre with pitch view, player profiles, live centre, chat, account, subscription, admin console (jobs, models, rules, users, fixtures, live-data quota, audit)
- Auth with refresh rotation, plan gating, rate limits, Razorpay checkout & idempotent webhooks, notifications, CI, Vitest and pytest suites

### Changed
- Fantasy points aligned with the AC-03 / TC-01 reference values (no SR/economy bonuses)
- Human-rules engine matches strictly (unknown context never fires a rule)
- Captain scoring is projection-led (backtested against the spec formula)

### Removed
- Match simulator, demo seeding, simulated checkout and bundled test accounts — real data only

---

## [0.5.0] - 2026-06-01

### Added
- LLM explainability engine: generates plain-English player selection rationale via Claude/GPT/Gemini
- AI chat assistant endpoint (`POST /api/v1/chat`) supporting natural language fantasy queries
- Human rules JSON engine with condition/impact/confidence scoring
- Rule validation CLI (`python human_rules/validate_rules.py`)

### Changed
- Ensemble weights re-calibrated: ML 40%, Human Rules 30%, Recent Form 20%, Live Context 10%
- Captain engine now produces Safe, Risk, and Grand League captain variants

### Fixed
- Duplicate delivery parsing issue for wide balls with wickets in Cricsheet v1.2.0
- Feature cache invalidation on player team transfers

---

## [0.4.0] - 2026-04-15

### Added
- Team optimizer: generates Safe, Grand League, Aggressive, and Small League squads via PuLP + DEAP
- Differential pick engine: ranks low-ownership high-ceiling candidates
- Backtesting harness supporting replay across 10,000+ historical matches
- `POST /api/v1/admin/retrain` endpoint for on-demand model retraining

### Changed
- Model ensemble upgraded from single XGBoost to XGBoost + LightGBM + CatBoost tri-model
- Feature engineering pipeline now runs incrementally (new matches only)

---

## [0.3.0] - 2026-02-28

### Added
- Player performance prediction models (runs, wickets, economy, fantasy points)
- Rolling form features: last-3, last-5, last-10 match windows
- Venue feature layer: average runs, wickets, spin/pace assistance, boundary size
- Matchup features: batter vs spin, batter vs pace, left-arm vs right-arm splits

### Changed
- Raw Cricsheet delivery schema normalized into `deliveries`, `innings`, `matches` relational tables
- Redis caching layer added for feature lookups (TTL: 6 hours)

---

## [0.2.0] - 2026-01-10

### Added
- FastAPI backend skeleton with `/health`, `/api/v1/players`, `/api/v1/matches` routes
- Supabase PostgreSQL schema and Alembic migration framework
- Cricsheet ingestion pipeline: parses 22,062 ball-by-ball JSON files into relational tables
- Feature engineering pipeline: initial feature set (career averages, venue averages)

### Changed
- Switched from SQLite to Supabase PostgreSQL for production scalability

---

## [0.1.0] - 2025-12-01

### Added
- Project scaffolding: directory structure, Docker Compose, pre-commit hooks
- Cricsheet data download and extraction scripts
- Initial data exploration notebooks
- .env.example, Makefile, requirements files
