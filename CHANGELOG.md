# Changelog

All notable changes to XithSense are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Live match WebSocket feed
- Telegram / WhatsApp notification delivery
- Payment gateway integration (Razorpay)
- React frontend SPA
- Multi-format model specialization (T20 vs ODI vs Test)

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
