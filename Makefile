.PHONY: help install install-dev setup bootstrap fixtures run run-dev web web-build lint format test test-unit \
        test-integration test-cov docker-up docker-down docker-seed ingest features train backtest \
        validate-rules migrate clean

PY ?= python

help:
	@echo "XithSense"
	@echo ""
	@echo "  make setup            Install Python + frontend dependencies, copy .env"
	@echo "  make bootstrap        Features, models, backtest, live fixtures, admin account (real data)"
	@echo "  make run-dev          API with auto-reload on :8000"
	@echo "  make web              Frontend dev server on :5173 (proxies the API)"
	@echo "  make web-build        Build the SPA (then 'make run' serves it on :8000)"
	@echo "  make test             Unit + integration tests"
	@echo "  make ingest SRC=...   Ingest Cricsheet JSON (zip or directory)"
	@echo "  make features | train | backtest | validate-rules"
	@echo "  make docker-up        Postgres + Redis + API (with built SPA) via Docker Compose"

install:
	$(PY) -m pip install -r requirements.txt

install-dev:
	$(PY) -m pip install -r requirements-dev.txt

setup: install
	cd frontend && npm install
	@test -f .env || cp .env.example .env

bootstrap:
	$(PY) -m scripts.bootstrap --test-users

fixtures:
	$(PY) -m scripts.sync_fixtures

run:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000

run-dev:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

web:
	cd frontend && npm run dev

web-build:
	cd frontend && npm run build

worker:
	celery -A backend.worker worker --loglevel=info

lint:
	ruff check backend training optimizer human_rules ingestion feature_engineering evaluation integrations

format:
	black backend training optimizer human_rules ingestion feature_engineering evaluation integrations

test:
	$(PY) -m pytest tests -q

test-unit:
	$(PY) -m pytest tests/unit -q

test-integration:
	$(PY) -m pytest tests/integration -q

test-cov:
	$(PY) -m pytest tests --cov=backend --cov=optimizer --cov=human_rules --cov=ingestion --cov=feature_engineering --cov-report=term-missing

SRC ?= data/raw/all_json.zip
ingest:
	$(PY) -m scripts.ingest_cricsheet --source $(SRC)

features:
	$(PY) -m scripts.build_features

train:
	$(PY) -m training.train

backtest:
	$(PY) -m scripts.run_backtest --n 10000

validate-rules:
	$(PY) -m human_rules.validate_rules

migrate:
	$(PY) -m scripts.db_migrate

docker-up:
	docker compose up --build -d db redis api

docker-seed:
	docker compose run --rm seed   # ingest data/raw/all_json.zip + bootstrap

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache frontend/dist
