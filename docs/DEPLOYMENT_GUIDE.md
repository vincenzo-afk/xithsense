# Deployment Guide

## Environments

| Environment | Purpose | URL |
|------------|---------|-----|
| `development` | Local developer machines | http://localhost:8000 |
| `staging` | Pre-production testing | https://staging-api.xithsense.com |
| `production` | Live platform | https://api.xithsense.com |

---

## Docker Compose (Self-Hosted / Railway / Render)

### Prerequisites on the server
- Docker 24+, Docker Compose 2+
- 2 vCPU, 4 GB RAM minimum
- 20 GB disk for data and model artifacts

### Deploy Steps

```bash
# 1. Clone repository
git clone https://github.com/your-org/xithsense.git
cd xithsense

# 2. Set environment variables
cp .env.example .env
nano .env   # Fill in all required values

# 3. Build images
docker compose build --no-cache

# 4. Run database migrations
docker compose run --rm api alembic upgrade head

# 5. Ingest data (first time only, ~30 min)
docker compose run --rm ingest

# 6. Build features
docker compose run --rm api python scripts/build_features.py

# 7. Train models (first time only, ~60 min)
docker compose run --rm api python training/train_ensemble.py

# 8. Start all services
docker compose up -d

# 9. Verify
curl https://api.xithsense.com/health
```

---

## Railway Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link project
railway login
railway link

# Set environment variables (once)
railway variables set --from .env

# Deploy
railway up
```

Railway reads `docker-compose.yml` and deploys each service automatically.  
Set `RAILWAY_DOCKERFILE_PATH=Dockerfile` in Railway project settings.

---

## Render Deployment

1. Connect GitHub repository to Render
2. Create a new **Web Service** (Docker)
3. Set Environment Variables from `.env.example`
4. Add a **Redis** service from Render marketplace
5. Add Qdrant via Docker service or Qdrant Cloud

---

## Zero-Downtime Updates

```bash
# Pull latest code
git pull origin main

# Rebuild API image
docker compose build api

# Restart API with zero-downtime rolling restart
docker compose up -d --no-deps api

# Verify health before removing old container
curl http://localhost:8000/health
```

---

## Post-Deployment Checklist

- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `GET /docs` loads Swagger UI
- [ ] `POST /api/v1/auth/register` creates a test user
- [ ] `POST /api/v1/predict/team` returns a valid team for a known match
- [ ] Redis is reachable: `docker compose exec redis redis-cli ping`
- [ ] Qdrant is reachable: `curl http://localhost:6333/readyz`
- [ ] Sentry is receiving events (trigger a test error)
- [ ] Celery workers processing tasks: `docker compose logs worker`

---

## Rollback Procedure

```bash
# Identify last stable image tag
docker images | grep xithsense_api

# Roll back to previous image
docker compose stop api
docker tag xithsense_api:<previous_tag> xithsense_api:latest
docker compose up -d api

# If DB migration needs rollback
docker compose run --rm api alembic downgrade -1
```

---

## Environment Variable Checklist for Production

- [ ] `SECRET_KEY` — 64+ character random string (not default)
- [ ] `SUPABASE_SERVICE_KEY` — production service key
- [ ] `REDIS_URL` — production Redis URL with auth
- [ ] `QDRANT_URL` — production Qdrant URL
- [ ] `LLM_PROVIDER` and corresponding API key
- [ ] `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` — live keys (not test)
- [ ] `SENTRY_DSN` — production Sentry DSN
- [ ] `ENV=production`
- [ ] `DEBUG=false`
- [ ] `ALLOWED_ORIGINS` — production frontend domain only
