.PHONY: help install install-dev lint format test test-unit test-integration test-cov \
        run run-dev docker-up docker-down ingest features train backtest migrate clean

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo "XithSense Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo "  make setup            Full dev environment setup"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run ruff + mypy"
	@echo "  make format           Auto-format with black + isort"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo ""
	@echo "Running:"
	@echo "  make run              Start API (production mode)"
	@echo "  make run-dev          Start API (development mode with reload)"
	@echo "  make worker           Start Celery worker"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up        Start all Docker services"
	@echo "  make docker-down      Stop all Docker services"
	@echo "  make docker-build     Rebuild Docker images"
	@echo "  make docker-logs      Tail API logs"
	@echo ""
	@echo "Data & ML:"
	@echo "  make ingest           Ingest Cricsheet data"
	@echo "  make features         Build feature store"
	@echo "  make train            Train ensemble models"
	@echo "  make train-t20        Train T20-specific models"
	@echo "  make train-odi        Train ODI-specific models"
	@echo "  make backtest         Run backtesting (10k matches)"
	@echo "  make validate-rules   Validate human intelligence rules"
	@echo ""
	@echo "Database:"
	@echo "  make migrate          Run Alembic migrations"
	@echo "  make migrate-create   Create a new migration"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Remove caches and build artifacts"

# ── Setup ─────────────────────────────────────────────────────────────────────
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

setup: install-dev
	pre-commit install
	cp -n .env.example .env || true
	@echo "Done. Edit .env with your credentials."

# ── Code Quality ──────────────────────────────────────────────────────────────
lint:
	ruff check .
	mypy backend/ training/ optimizer/ human_rules/ --ignore-missing-imports

format:
	black .
	isort .
	ruff check . --fix

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short

test-unit:
	pytest tests/unit/ -v --tb=short

test-integration:
	pytest tests/integration/ -v --tb=short

test-cov:
	pytest tests/ --cov=backend --cov=training --cov=optimizer --cov=human_rules \
	       --cov-report=term-missing --cov-report=html --cov-fail-under=75

test-backtest:
	pytest tests/backtesting/ -v -k "accuracy"

# ── Running ───────────────────────────────────────────────────────────────────
run:
	gunicorn backend.main:app --workers 4 \
	    --worker-class uvicorn.workers.UvicornWorker \
	    --bind 0.0.0.0:8000 --timeout 120

run-dev:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

worker:
	python -m celery -A backend.worker worker --loglevel=info --concurrency=4

scheduler:
	python -m celery -A backend.worker beat --loglevel=info

flower:
	python -m celery -A backend.worker flower --port=5555

# ── Docker ────────────────────────────────────────────────────────────────────
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-build:
	docker compose build --no-cache

docker-logs:
	docker compose logs -f api

docker-shell:
	docker compose exec api /bin/bash

# ── Data & ML ─────────────────────────────────────────────────────────────────
ingest:
	python scripts/ingest_cricsheet.py --source data/raw/all_json.zip

ingest-incremental:
	python scripts/ingest_cricsheet.py --source data/raw/all_json.zip --incremental

features:
	python scripts/build_features.py

features-from:
	python scripts/build_features.py --from $(FROM)

train:
	python training/train_ensemble.py

train-t20:
	python training/train_ensemble.py --format T20

train-odi:
	python training/train_ensemble.py --format ODI

train-test:
	python training/train_ensemble.py --format Test

backtest:
	python backtesting/run_backtest.py --n 10000

backtest-ipl:
	python backtesting/run_backtest.py --format IPL --n 1000

validate-rules:
	python human_rules/validate_rules.py

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(MSG)"

migrate-down:
	alembic downgrade -1

# ── Maintenance ───────────────────────────────────────────────────────────────
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage coverage.xml
	@echo "Cleaned."
