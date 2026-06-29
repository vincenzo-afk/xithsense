# Task Breakdown — Complete Implementation Roadmap

**Format:** Phase → Epic → Task  
**Status keys:** 🔲 Not started | 🔄 In progress | ✅ Done | ⏸ Blocked

---

## Phase 1 — Foundation

### Epic 1.1: Repository Setup
| # | Task | Owner | Est. |
|---|------|-------|------|
| 1.1.1 | Create GitHub repository, branch protection rules | Infra | 1h |
| 1.1.2 | Set up directory structure per `docs/PROJECT_STRUCTURE.md` | Infra | 1h |
| 1.1.3 | Configure pre-commit hooks (ruff, black, isort) | Infra | 1h |
| 1.1.4 | Write `Makefile` with all standard commands | Infra | 2h |
| 1.1.5 | Create `.env.example` with all required variables | Infra | 1h |
| 1.1.6 | Set up GitHub Actions CI pipeline (lint + test) | Infra | 3h |

### Epic 1.2: Docker Environment
| # | Task | Owner | Est. |
|---|------|-------|------|
| 1.2.1 | Write `Dockerfile` (multi-stage: base, dev, production) | Infra | 2h |
| 1.2.2 | Write `docker-compose.yml` (API, Redis, Qdrant, worker, scheduler) | Infra | 2h |
| 1.2.3 | Verify full stack starts with `docker compose up` | Infra | 1h |

### Epic 1.3: Database Setup
| # | Task | Owner | Est. |
|---|------|-------|------|
| 1.3.1 | Create Supabase project, configure connection pooling | Backend | 2h |
| 1.3.2 | Set up SQLAlchemy models matching `docs/DATABASE_SCHEMA.md` | Backend | 8h |
| 1.3.3 | Write Alembic initial migration (all tables) | Backend | 4h |
| 1.3.4 | Verify `make migrate` runs clean | Backend | 1h |
| 1.3.5 | Add database indexes per schema spec | Backend | 2h |
| 1.3.6 | Write `conftest.py` test database fixtures | Backend | 3h |

---

## Phase 2 — Data Ingestion Pipeline

### Epic 2.1: Cricsheet Parser
| # | Task | Owner | Est. |
|---|------|-------|------|
| 2.1.1 | Write Cricsheet v1.2.0 JSON schema validator | Data | 3h |
| 2.1.2 | Write `parse_match_info()` — extract match metadata | Data | 4h |
| 2.1.3 | Write `parse_innings()` — extract innings and overs | Data | 3h |
| 2.1.4 | Write `parse_delivery()` — extract ball-by-ball data | Data | 5h |
| 2.1.5 | Handle edge cases: missing player_of_match, no-result matches | Data | 3h |
| 2.1.6 | Handle wide balls with wickets (dual event) | Data | 2h |
| 2.1.7 | Write unit tests for parser with real sample JSON files | Data | 4h |

### Epic 2.2: Ingestion Pipeline
| # | Task | Owner | Est. |
|---|------|-------|------|
| 2.2.1 | Write `scripts/ingest_cricsheet.py` CLI with `--source`, `--incremental` flags | Data | 4h |
| 2.2.2 | Implement upsert logic for match and delivery records | Data | 3h |
| 2.2.3 | Implement player deduplication using Cricsheet registry key | Data | 3h |
| 2.2.4 | Implement venue normalisation (map aliases to canonical names) | Data | 4h |
| 2.2.5 | Add progress bar and per-file error logging | Data | 2h |
| 2.2.6 | Benchmark ingestion: target < 30 minutes for 22,062 files | Data | 2h |
| 2.2.7 | Write integration test: ingest 100 sample matches, verify counts | Data | 3h |

### Epic 2.3: Fantasy Points Computation
| # | Task | Owner | Est. |
|---|------|-------|------|
| 2.3.1 | Implement `compute_fantasy_points()` per Dream11 scoring rules | Data | 4h |
| 2.3.2 | Verify against known match results (manual check 10 matches) | Data | 3h |
| 2.3.3 | Populate `player_match_performance` table for all ingested matches | Data | 2h |
| 2.3.4 | Write tests: assert FP = 0 for missing player, FP > 0 for century | Data | 2h |

---

## Phase 3 — Feature Engineering

### Epic 3.1: Rolling Features
| # | Task | Owner | Est. |
|---|------|-------|------|
| 3.1.1 | Implement `compute_rolling_batting_features(player_id, window, match_type)` | ML | 5h |
| 3.1.2 | Implement `compute_rolling_bowling_features(player_id, window, match_type)` | ML | 4h |
| 3.1.3 | Implement `compute_fantasy_features(player_id, window)` (avg, ceiling, floor, consistency) | ML | 4h |
| 3.1.4 | Store results in `rolling_feature` table | ML | 2h |
| 3.1.5 | Implement incremental update (only new matches) | ML | 4h |
| 3.1.6 | Benchmark: target < 10 min for full feature rebuild | ML | 2h |
| 3.1.7 | Write unit tests for rolling computations | ML | 4h |

### Epic 3.2: Venue & Matchup Features
| # | Task | Owner | Est. |
|---|------|-------|------|
| 3.2.1 | Implement `compute_venue_stats(venue_id, match_type)` | ML | 4h |
| 3.2.2 | Implement bowler type classification from `bowling_style` field | ML | 3h |
| 3.2.3 | Implement `compute_matchup_stats(player_id, bowler_type, match_type)` | ML | 5h |
| 3.2.4 | Populate all venue and matchup tables | ML | 2h |
| 3.2.5 | Implement missing value fallbacks (global averages as prior) | ML | 3h |

### Epic 3.3: Feature Pipeline Script
| # | Task | Owner | Est. |
|---|------|-------|------|
| 3.3.1 | Write `scripts/build_features.py` orchestrating all feature computation | ML | 4h |
| 3.3.2 | Add `--from DATE` flag for incremental rebuilds | ML | 2h |
| 3.3.3 | Add Redis caching for computed feature vectors | ML | 3h |
| 3.3.4 | Write `build_feature_vector(player_id, match_context)` assembling the full input array | ML | 4h |

---

## Phase 4 — ML Models

### Epic 4.1: Model Training
| # | Task | Owner | Est. |
|---|------|-------|------|
| 4.1.1 | Write `training/data_loader.py` — time-split train/val/test sets | ML | 4h |
| 4.1.2 | Train XGBoost fantasy points model (M-01) for T20 | ML | 4h |
| 4.1.3 | Train LightGBM fantasy points model (M-02) for T20 | ML | 3h |
| 4.1.4 | Train CatBoost fantasy points model (M-03) for T20 | ML | 3h |
| 4.1.5 | Train batting runs model (M-04) | ML | 4h |
| 4.1.6 | Train bowling wickets model (M-05) | ML | 4h |
| 4.1.7 | Train fp_ceiling model (M-06) | ML | 3h |
| 4.1.8 | Evaluate all models on held-out 2025 test set | ML | 4h |

### Epic 4.2: Model Registry & Versioning
| # | Task | Owner | Est. |
|---|------|-------|------|
| 4.2.1 | Implement `ModelRegistry` class (load/save/activate) | ML | 4h |
| 4.2.2 | Write artifact serialisation (pkl for XGB/LGB, cbm for CatBoost) | ML | 2h |
| 4.2.3 | Implement version promotion logic | ML | 3h |

---

## Phase 5 — Human Rules Engine

### Epic 5.1: Rule Engine
| # | Task | Owner | Est. |
|---|------|-------|------|
| 5.1.1 | Write `human_rules/rule_engine.py` — load, validate, evaluate | Rules | 5h |
| 5.1.2 | Implement `evaluate_condition()` supporting all condition keys | Rules | 6h |
| 5.1.3 | Implement `log_rule_triggers()` to `rule_trigger` table | Rules | 2h |
| 5.1.4 | Write `validate_rules.py` CLI | Rules | 3h |
| 5.1.5 | Write 50+ player rules in `PLAYER_RULES.json` | Rules | 8h |
| 5.1.6 | Write 30+ venue rules in `VENUE_RULES.json` | Rules | 5h |
| 5.1.7 | Write 20+ matchup rules in `MATCHUP_RULES.json` | Rules | 4h |
| 5.1.8 | Write 20+ context rules in `CONTEXT_RULES.json` | Rules | 4h |
| 5.1.9 | Write unit tests for rule evaluation | Rules | 4h |

---

## Phase 6 — Ensemble Engine

### Epic 6.1: Ensemble
| # | Task | Owner | Est. |
|---|------|-------|------|
| 6.1.1 | Write `training/ensemble.py` — weighted score combiner | ML | 4h |
| 6.1.2 | Implement weight configuration via env vars | ML | 1h |
| 6.1.3 | Implement `predict_match(match_id)` end-to-end pipeline | ML | 6h |
| 6.1.4 | Write unit tests for ensemble output shape and ranges | ML | 3h |

---

## Phase 7 — Team Optimizer

### Epic 7.1: LP Optimizer
| # | Task | Owner | Est. |
|---|------|-------|------|
| 7.1.1 | Write `optimizer/lp_optimizer.py` with PuLP formulation | ML | 8h |
| 7.1.2 | Implement all 4 mode score modifiers | ML | 4h |
| 7.1.3 | Implement diversity constraint for multi-team generation | ML | 4h |
| 7.1.4 | Write DEAP genetic algorithm fallback | ML | 8h |
| 7.1.5 | Write unit tests: assert every generated team passes Dream11 constraints | ML | 4h |
| 7.1.6 | Benchmark: assert 4-mode portfolio < 3 seconds | ML | 2h |

---

## Phase 8 — Captain Engine

| # | Task | Owner | Est. |
|---|------|-------|------|
| 8.1 | Write `optimizer/captain_engine.py` | ML | 4h |
| 8.2 | Implement Best, Safe, Risk, GL captain selection logic | ML | 4h |
| 8.3 | Write unit tests | ML | 2h |

---

## Phase 9 — Backtesting

| # | Task | Owner | Est. |
|---|------|-------|------|
| 9.1 | Write `backtesting/run_backtest.py` | ML | 6h |
| 9.2 | Implement correct_player_rate, captain_accuracy, fp_error metrics | ML | 4h |
| 9.3 | Store results in `backtest_run` and `backtest_result` tables | ML | 3h |
| 9.4 | Add `--format`, `--n`, `--from`, `--to` CLI flags | ML | 2h |
| 9.5 | Run initial backtest on 10,000 matches; document baseline | ML | 4h |

---

## Phase 10 — FastAPI Backend

### Epic 10.1: API Skeleton
| # | Task | Owner | Est. |
|---|------|-------|------|
| 10.1.1 | Write `backend/main.py` — FastAPI app with CORS, middleware | Backend | 3h |
| 10.1.2 | Write `backend/auth/` — JWT register, login, refresh | Backend | 6h |
| 10.1.3 | Write `backend/dependencies.py` — DB session, current user, rate limiter | Backend | 3h |
| 10.1.4 | Implement rate limiting middleware per plan | Backend | 4h |

### Epic 10.2: API Routes
| # | Task | Owner | Est. |
|---|------|-------|------|
| 10.2.1 | Implement `GET /api/v1/matches/*` routes | Backend | 4h |
| 10.2.2 | Implement `GET /api/v1/players/*` routes | Backend | 4h |
| 10.2.3 | Implement `POST /api/v1/predict/*` routes | Backend | 8h |
| 10.2.4 | Implement `POST /api/v1/chat` route | Backend | 4h |
| 10.2.5 | Implement `GET /api/v1/explain/*` route | Backend | 3h |
| 10.2.6 | Implement `GET /api/v1/live/{match_id}` WebSocket route | Backend | 5h |
| 10.2.7 | Implement admin routes | Backend | 6h |

---

## Phase 11 — LLM Explainability & Chat

| # | Task | Owner | Est. |
|---|------|-------|------|
| 11.1 | Write `llm/explainer.py` — generate player explanation via LLM | LLM | 5h |
| 11.2 | Write `llm/chat_assistant.py` — conversational fantasy assistant | LLM | 6h |
| 11.3 | Implement provider switching (Anthropic / OpenAI / Google) | LLM | 4h |
| 11.4 | Implement explanation caching (Redis 1h TTL) | LLM | 2h |
| 11.5 | Write system prompts and guardrails | LLM | 4h |
| 11.6 | Write unit tests with mocked LLM responses | LLM | 3h |

---

## Phase 12 — Notifications

| # | Task | Owner | Est. |
|---|------|-------|------|
| 12.1 | Write `notifications/telegram_sender.py` | Notif | 4h |
| 12.2 | Implement notification event triggers via Celery tasks | Notif | 4h |
| 12.3 | Write user notification preference model and API | Notif | 3h |

---

## Phase 13 — Payments

| # | Task | Owner | Est. |
|---|------|-------|------|
| 13.1 | Implement Razorpay subscription creation flow | Backend | 5h |
| 13.2 | Implement Razorpay webhook handler (payment.captured, subscription.cancelled) | Backend | 5h |
| 13.3 | Implement subscription status check on protected endpoints | Backend | 3h |
| 13.4 | Test with Razorpay sandbox; document test card numbers | Backend | 3h |

---

## Phase 14 — Frontend (Post-MVP)

| # | Task | Owner | Est. |
|---|------|-------|------|
| 14.1 | Scaffold React + Vite project | Frontend | 3h |
| 14.2 | Implement design system from `frontend/DESIGN_TOKENS.json` | Frontend | 6h |
| 14.3 | Build Match List page | Frontend | 6h |
| 14.4 | Build Team Prediction page with 4-mode tabs | Frontend | 10h |
| 14.5 | Build Player Detail page | Frontend | 6h |
| 14.6 | Build AI Chat widget | Frontend | 6h |
| 14.7 | Build Auth pages (login, register) | Frontend | 5h |
| 14.8 | Build subscription/payment flow | Frontend | 6h |

---

## Total Estimated Effort

| Phase | Estimate |
|-------|---------|
| 1–3 (Foundation + Data + Features) | ~120h |
| 4–6 (Models + Rules + Ensemble) | ~90h |
| 7–9 (Optimizer + Captain + Backtest) | ~55h |
| 10–13 (API + LLM + Notif + Payments) | ~95h |
| 14 (Frontend) | ~48h |
| **Total MVP** | **~408h** |
