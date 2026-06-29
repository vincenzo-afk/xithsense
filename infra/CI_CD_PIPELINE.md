# CI/CD Pipeline

## Pipeline Overview

```
Code pushed to GitHub
        │
        ▼
GitHub Actions: CI Pipeline
  ├── lint (ruff + mypy)
  ├── test-unit (pytest, no DB needed)
  ├── test-integration (pytest, ephemeral PG + Redis)
  └── build Docker image
        │
  (all pass?)
        │ Yes
        ▼
  Branch = develop?
        ├── Yes → Deploy to Staging (auto)
        └── No

  Branch = main (tagged release)?
        └── Yes → Deploy to Production (auto)
```

## GitHub Actions Workflows

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ruff mypy
      - run: ruff check .
      - run: mypy backend/ training/ optimizer/ --ignore-missing-imports

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: xithsense_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: |
          export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/xithsense_test
          export REDIS_URL=redis://localhost:6379/0
          export ENV=test
          alembic upgrade head
          pytest tests/unit/ tests/integration/ -v --cov=backend --cov-report=xml
      - uses: codecov/codecov-action@v4

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: .
          target: production
          push: false
          tags: xithsense/api:${{ github.sha }}
```

### `.github/workflows/deploy-staging.yml`

```yaml
name: Deploy Staging

on:
  push:
    branches: [develop]

jobs:
  deploy:
    needs: [ci]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Railway (staging)
        run: railway up --environment staging
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN_STAGING }}
```

### `.github/workflows/deploy-production.yml`

```yaml
name: Deploy Production

on:
  push:
    tags: ["v*.*.*"]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Railway (production)
        run: railway up --environment production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN_PRODUCTION }}
      - name: Notify Sentry of release
        run: |
          sentry-cli releases new ${{ github.ref_name }}
          sentry-cli releases finalize ${{ github.ref_name }}
```

## Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `RAILWAY_TOKEN_STAGING` | Railway deploy token for staging |
| `RAILWAY_TOKEN_PRODUCTION` | Railway deploy token for production |
| `CODECOV_TOKEN` | Codecov.io upload token |
| `SENTRY_AUTH_TOKEN` | Sentry CLI authentication |
| `SENTRY_ORG` | Sentry organisation slug |
| `SENTRY_PROJECT` | Sentry project slug |

## Branch Protection Rules

- `main`: Require 1 approving review, require CI to pass, no force-push
- `develop`: Require CI to pass, no force-push
- All feature branches: CI runs on PR only
