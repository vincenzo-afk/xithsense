# Development Environment Setup

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Git | 2.40+ | [git-scm.com](https://git-scm.com) |
| Docker | 24+ | [docker.com](https://docker.com) |
| Docker Compose | 2.x | Bundled with Docker Desktop |

## Step-by-Step Setup

```bash
# 1. Clone
git clone https://github.com/your-org/xithsense.git
cd xithsense

# 2. Python virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 4. Install pre-commit hooks
pre-commit install

# 5. Copy env file
cp .env.example .env
# Edit .env — fill in DATABASE_URL, REDIS_URL, LLM API key at minimum

# 6. Start Docker services (Redis + Qdrant)
docker compose up redis qdrant -d

# 7. Apply database migrations
alembic upgrade head

# 8. Download Cricsheet data
mkdir -p data/raw
# Download all_json.zip from https://cricsheet.org/downloads/all_json.zip
# Save to data/raw/all_json.zip

# 9. Ingest data (takes ~25 minutes first time)
python scripts/ingest_cricsheet.py --source data/raw/all_json.zip

# 10. Build features
python scripts/build_features.py

# 11. Train models
python training/train_ensemble.py --format T20

# 12. Start API server
make run-dev
```

API available at: http://localhost:8000  
Swagger docs: http://localhost:8000/docs

## Useful Dev Commands

```bash
make run-dev              # API with hot reload
make worker               # Start Celery worker (separate terminal)
make test-unit            # Fast unit tests only
make lint                 # Lint check
make format               # Auto-format code
docker compose logs -f    # All service logs
```

## Minimum Setup (No Data, No Models)

To run just the API for frontend development:

```bash
docker compose up redis qdrant -d
alembic upgrade head
ENV=development SKIP_MODEL_LOAD=true make run-dev
```

This starts the API with stub prediction responses.

## IDE Setup (VS Code)

Recommended extensions: `ms-python.python`, `ms-python.vscode-pylance`, `charliermarsh.ruff`, `tamasfe.even-better-toml`

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "charliermarsh.ruff",
  "[python]": { "editor.defaultFormatter": "ms-python.black-formatter" }
}
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `alembic upgrade head` fails | Check `DATABASE_URL` in `.env` |
| Redis connection refused | Run `docker compose up redis -d` |
| Model not found error | Run `python training/train_ensemble.py` |
| LLM timeout | Check LLM API key; set `LLM_PROVIDER=anthropic` in `.env` |
| Import errors | Ensure `.venv` is activated |
